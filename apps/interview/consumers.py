import json
import logging
import re
import uuid
import asyncio
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.interview.models import Interview, InterviewConversation
from apps.ai_reports.services.gemini_client import (
    analyze_interview,
    generate_follow_up_questions,
)

logger = logging.getLogger(__name__)

FOLLOW_UP_CACHE_TTL = 60 * 60 * 24


def follow_up_cache_key(interview_id) -> str:
    return f"interview_followups:{interview_id}"


class InterviewConsumer(AsyncWebsocketConsumer):
    MIN_FOLLOW_UP_WORDS = 5
    MIN_NEW_WORDS_FOR_REFRESH = 5

    async def connect(self):
        from apps.ai_reports.models import AIReport

        # Browser clients (recruiter/candidate live pages) authenticate by passing
        # the token as a WebSocket subprotocol: ["auth", "<token>"]. The browser
        # aborts the handshake (close code 1006) unless the server echoes one of
        # the offered subprotocols, so we capture and echo it on every accept().
        self.offered_subprotocols = list(self.scope.get("subprotocols") or [])
        self.accept_subprotocol = (
            self.offered_subprotocols[0] if self.offered_subprotocols else None
        )

        raw_interview_id = self.scope["url_route"]["kwargs"]["interview_id"]
        try:
            self.interview_id = str(uuid.UUID(str(raw_interview_id)))
        except (TypeError, ValueError):
            logger.warning("Rejected websocket connection with invalid interview ID: %s", raw_interview_id)
            await self._accept()
            await self.close(code=4400)
            return

        self.group_name = f"interview_{self.interview_id}"
        self.candidate_live_buffer = ""
        self.last_follow_up_buffer = ""

        # The user is resolved by TokenAuthMiddleware (cookie / query / subprotocol).
        self.user = self.scope.get("user")

        if self.user is None or not self.user.is_authenticated:
            await self._accept()
            await self.close(code=4003)
            return

        # Complete the HTTP upgrade immediately so slow DB lookups cannot cause
        # browser-side handshake timeouts (close code 1006).
        await self._accept()

        # Authorize: only the interview's candidate, the recruiter who posted the
        # job, or staff may connect to this interview's stream.
        if not await self._user_can_access(self.user):
            logger.warning(
                "User %s denied access to interview %s",
                getattr(self.user, "id", None),
                self.interview_id,
            )
            await self.close(code=4003)
            return

        self.joined_group = False
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        self.joined_group = True
        await self.send(text_data=json.dumps({
            "type": "interview_status",
            "status": "connected",
            "interview_id": str(self.interview_id),
        }))

    async def _accept(self):
        """Accept the connection, echoing the offered subprotocol when present.

        Browsers require the server to select one of the subprotocols they
        offered; without this the handshake fails with close code 1006.
        """
        if self.accept_subprotocol:
            await self.accept(subprotocol=self.accept_subprotocol)
        else:
            await self.accept()

    async def disconnect(self, close_code):
        if getattr(self, "joined_group", False):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        from apps.interview.models import Interview, InterviewConversation
        try:
            data = json.loads(text_data)
        except Exception:
            data = {"type": "transcript", "text": text_data}

        event_type = data.get("type", "transcript")
        speaker = (data.get("speaker") or "unknown").strip().lower()
        timestamp = data.get("timestamp", "")

        if event_type == "transcript":
            text = (data.get("text") or data.get("message") or "").strip()
            if not text:
                return

            start = data.get("start")
            end = data.get("end")
            await self._save_transcript(speaker, text, timestamp)

            await self._broadcast_event(
                event_type="transcript",
                payload={
                    "message": text,
                    "text": text,
                    "speaker": speaker,
                    "timestamp": timestamp,
                    "start": start,
                    "end": end,
                    "interview_id": str(self.interview_id),
                },
            )

            if speaker == InterviewConversation.Speaker.CANDIDATE:
                self.candidate_live_buffer, reset_follow_up_state = self._merge_candidate_chunk(
                    self.candidate_live_buffer,
                    text,
                )
                if reset_follow_up_state:
                    self.last_follow_up_buffer = ""
                await self._try_emit_follow_ups(timestamp)
            else:
                # Recruiter spoke — treat that as end-of-turn and flush any pending
                # candidate answer before clearing the live buffer.
                await self._try_emit_follow_ups(timestamp)
                self.candidate_live_buffer = ""
                self.last_follow_up_buffer = ""

        elif event_type == "generate_followup":
            candidate_text = (data.get("candidate_text") or "").strip()
            context = data.get("context") or []
            if not candidate_text:
                return

            questions = await self._generate_follow_ups(candidate_text, context)
            if questions:
                await self._publish_follow_up_questions(
                    questions=questions,
                    candidate_text=candidate_text,
                    context=context,
                    timestamp=timestamp,
                    automatic=False,
                    trigger="manual",
                )

        elif event_type == "bot_status":
            status = (data.get("status") or "").strip().lower()
            if status == "joined" and data.get("session_start"):
                cleared = await self._start_live_session()
                logger.info(
                    "Started live session for interview %s (cleared %s transcript rows)",
                    self.interview_id,
                    cleared,
                )
                self.candidate_live_buffer = ""
                self.last_follow_up_buffer = ""
                await self._broadcast_event(
                    event_type="session_started",
                    payload={
                        "interview_id": str(self.interview_id),
                        "timestamp": timestamp,
                        "cleared_transcript_rows": cleared,
                    },
                )
            elif status == "joined":
                await self._mark_bot_joined()

            await self._broadcast_event(
                event_type="bot_status",
                payload={
                    "status": status,
                    "interview_id": str(self.interview_id),
                    "timestamp": timestamp,
                },
            )

        elif event_type == "meeting_ended":
            await self._update_interview_status(Interview.Status.COMPLETED)
            await self._broadcast_event(
                event_type="interview_status",
                payload={
                    "status": "analyzing",
                    "interview_id": str(self.interview_id),
                    "timestamp": timestamp,
                },
            )

            transcripts = await self._get_transcripts()
            analysis = await self._analyze_interview(transcripts)

            if analysis:
                await self._save_interview_analysis(analysis)
                await self._broadcast_event(
                    event_type="interview_analysis_ready",
                    payload={
                        "analysis": analysis,
                        "interview_id": str(self.interview_id),
                        "timestamp": timestamp,
                    },
                )
                await self._broadcast_event(
                    event_type="interview_status",
                    payload={
                        "status": "completed",
                        "interview_id": str(self.interview_id),
                        "timestamp": timestamp,
                    },
                )
            else:
                await self._broadcast_event(
                    event_type="interview_status",
                    payload={
                        "status": "analysis_failed",
                        "interview_id": str(self.interview_id),
                        "timestamp": timestamp,
                    },
                )

        else:
            await self._broadcast_event(
                event_type=event_type,
                payload={
                    "message": data.get("message", ""),
                    "speaker": speaker,
                    "timestamp": timestamp,
                    "interview_id": str(self.interview_id),
                },
            )

    def _merge_candidate_chunk(self, current_text, incoming_text):
        current = (current_text or "").strip()
        incoming = (incoming_text or "").strip()
        if not incoming:
            return current, False
        if not current:
            return incoming, False
        if incoming == current or incoming in current:
            return current, False
        if incoming.startswith(current):
            return incoming, False
        if current.startswith(incoming):
            return current, False

        overlap = self._suffix_prefix_overlap(current, incoming)
        if overlap:
            merged = f"{current}{incoming[overlap:]}".strip()
            return merged, False

        return incoming, True

    def _suffix_prefix_overlap(self, left, right):
        max_overlap = min(len(left), len(right))
        for size in range(max_overlap, 0, -1):
            if left[-size:] == right[:size]:
                return size
        return 0

    def _should_generate_follow_up(self, candidate_text):
        candidate_words = self._word_count(candidate_text)
        if candidate_words < self.MIN_FOLLOW_UP_WORDS:
            return False
        if not self.last_follow_up_buffer:
            return True
        return candidate_words >= self._word_count(self.last_follow_up_buffer) + self.MIN_NEW_WORDS_FOR_REFRESH

    def _word_count(self, text):
        return len(re.findall(r"\b\w+\b", text or ""))

    def _compress_candidate_context(self, texts):
        compressed = []
        for text in texts:
            cleaned = (text or "").strip()
            if not cleaned:
                continue
            if not compressed:
                compressed.append(cleaned)
                continue

            previous = compressed[-1]
            if cleaned == previous:
                continue
            if cleaned.startswith(previous):
                compressed[-1] = cleaned
                continue
            if previous.startswith(cleaned):
                continue
            compressed.append(cleaned)

        return compressed[-5:]

    async def interview_event(self, event):
        payload = dict(event["payload"])
        payload["type"] = event["event_type"]
        await self.send(text_data=json.dumps(payload))

    async def _broadcast_event(self, event_type, payload):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "interview_event",
                "event_type": event_type,
                "payload": payload,
            },
        )

    async def _try_emit_follow_ups(self, timestamp):
        candidate_text = (self.candidate_live_buffer or "").strip()
        if not candidate_text or not self._should_generate_follow_up(candidate_text):
            return

        context = await self._get_candidate_context(candidate_text)
        questions = await self._generate_follow_ups(candidate_text, context)
        if not questions:
            return

        self.last_follow_up_buffer = candidate_text
        await self._publish_follow_up_questions(
            questions=questions,
            candidate_text=candidate_text,
            context=context,
            timestamp=timestamp,
            automatic=True,
            trigger="live_chunk_threshold",
        )

    async def _publish_follow_up_questions(
        self,
        *,
        questions,
        candidate_text,
        context,
        timestamp,
        automatic,
        trigger,
    ):
        logger.info(
            "Emitting follow-up questions for interview %s: %s",
            self.interview_id,
            questions,
        )
        cache.set(
            follow_up_cache_key(self.interview_id),
            {
                "questions": questions,
                "candidate_text": candidate_text,
                "timestamp": timestamp,
            },
            FOLLOW_UP_CACHE_TTL,
        )
        await self._broadcast_event(
            event_type="follow_up_questions",
            payload={
                "questions": questions,
                "candidate_text": candidate_text,
                "context": context,
                "interview_id": str(self.interview_id),
                "timestamp": timestamp,
                "automatic": automatic,
                "trigger": trigger,
            },
        )

    @database_sync_to_async
    def _user_can_access(self, user):
        from apps.interview.models import Interview

        interview = (
            Interview.objects
            .select_related("candidate__user", "job__posted_by__user")
            .filter(pk=self.interview_id)
            .first()
        )
        if interview is None:
            return False

        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            return True

        candidate = interview.candidate
        if candidate and candidate.user_id == user.id:
            return True

        job = interview.job
        if job and job.posted_by and job.posted_by.user_id == user.id:
            return True

        return False

    @database_sync_to_async
    def _start_live_session(self):
        from apps.interview.models import Interview, InterviewConversation

        interview = Interview.objects.filter(pk=self.interview_id).first()
        if interview is None:
            logger.warning("Interview %s not found while starting live session", self.interview_id)
            return 0

        deleted_count, _ = InterviewConversation.objects.filter(
            interview_id=self.interview_id,
        ).delete()
        cache.delete(follow_up_cache_key(self.interview_id))

        interview.status = Interview.Status.IN_PROGRESS
        interview.bot_join_status = Interview.BotJoinStatus.JOINED
        interview.save(update_fields=["status", "bot_join_status", "updated_at"])
        return deleted_count

    @database_sync_to_async
    def _mark_bot_joined(self):
        from apps.interview.models import Interview

        interview = Interview.objects.filter(pk=self.interview_id).first()
        if interview is None:
            return
        interview.bot_join_status = Interview.BotJoinStatus.JOINED
        if interview.status != Interview.Status.IN_PROGRESS:
            interview.status = Interview.Status.IN_PROGRESS
            interview.save(update_fields=["status", "bot_join_status", "updated_at"])
        else:
            interview.save(update_fields=["bot_join_status", "updated_at"])

    @database_sync_to_async
    def _save_transcript(self, speaker, text, timestamp):
        from apps.interview.models import Interview, InterviewConversation
        interview = Interview.objects.filter(pk=self.interview_id).first()
        if interview is None:
            logger.warning("Interview %s not found while saving transcript", self.interview_id)
            return

        speaker_value = speaker
        valid_speakers = {choice[0] for choice in InterviewConversation.Speaker.choices}
        if speaker_value not in valid_speakers:
            speaker_value = InterviewConversation.Speaker.UNKNOWN

        parsed_timestamp = parse_datetime(timestamp) if timestamp else None
        if parsed_timestamp is None:
            parsed_timestamp = timezone.now()

        InterviewConversation.objects.create(
            interview=interview,
            speaker=speaker_value,
            text=text,
            timestamp=parsed_timestamp,
        )

        if interview.status != Interview.Status.IN_PROGRESS:
            interview.status = Interview.Status.IN_PROGRESS
            interview.save(update_fields=["status", "updated_at"])

    @database_sync_to_async
    def _update_interview_status(self, status):
        from apps.interview.models import Interview
        interview = Interview.objects.filter(pk=self.interview_id).first()
        if interview is None:
            logger.warning("Interview %s not found while updating status", self.interview_id)
            return
        interview.status = status
        interview.save(update_fields=["status", "updated_at"])

    @database_sync_to_async
    def _get_transcripts(self):
        from apps.interview.models import InterviewConversation
        rows = (
            InterviewConversation.objects.filter(interview_id=self.interview_id)
            .order_by("timestamp")
            .values("speaker", "text", "timestamp")
        )
        return [
            {
                "speaker": row["speaker"],
                "text": row["text"],
                "start_time": row["timestamp"].isoformat() if row["timestamp"] else "",
                "end_time": row["timestamp"].isoformat() if row["timestamp"] else "",
            }
            for row in rows
        ]

    @database_sync_to_async
    def _get_candidate_context(self, current_text=""):
        from apps.interview.models import InterviewConversation
        rows = (
            InterviewConversation.objects.filter(
                interview_id=self.interview_id,
                speaker=InterviewConversation.Speaker.CANDIDATE,
            )
            .order_by("timestamp")
            .values_list("text", flat=True)
        )
        texts = [text.strip() for text in rows if text and text.strip()]
        if current_text:
            texts.append(current_text.strip())
        return self._compress_candidate_context(texts)

    @database_sync_to_async
    def _save_interview_analysis(self, analysis):
        from apps.interview.models import Interview 
        from apps.ai_reports.models import AIReport 
        interview = (
            Interview.objects.select_related("candidate")
            .filter(pk=self.interview_id)
            .first()
        )
        if interview is None:
            logger.warning("Interview %s not found while saving analysis", self.interview_id)
            return

        AIReport.objects.update_or_create(
            candidate=interview.candidate,
            interview=interview,
            report_type=AIReport.ReportType.INTERVIEW_ANALYSIS,
            defaults={
                "fit_score": analysis.get("fit_score", 0),
                "summary": analysis.get("summary", ""),
                "strengths": analysis.get("strengths", []),
                "weaknesses": analysis.get("weaknesses", []),
                "feedback": analysis.get("feedback", ""),
                "extracted_skills": analysis.get("extracted_skills", []),
                "recommendation": analysis.get("recommendation"),
                "confidence": analysis.get("confidence"),
                "raw_response": analysis,
            },
        )

    async def _generate_follow_ups(self, candidate_text, context):
        return await asyncio.to_thread(
            generate_follow_up_questions,
            candidate_text,
            context,
        )

    @database_sync_to_async
    def _analyze_interview(self, transcripts):
        return analyze_interview(transcripts)
