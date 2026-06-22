"""
Interview and conversation views.
Candidates can only view their own interviews; recruiters can view and manage
interviews for jobs they posted.
"""
import os
import subprocess
from uuid import uuid4
from django.conf import settings
from django.core.cache import cache
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsRecruiter
from apps.users.tasks import send_interview_invite_email
from apps.candidate.models import Candidate

from .consumers import follow_up_cache_key
from .models import Interview, InterviewConversation
from .serializers import InterviewSerializer, InterviewConversationSerializer


class InterviewViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Interview.objects.none()          # required for router

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'launch_bot']:
            return [permissions.IsAuthenticated(), IsRecruiter()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'recruiter_profile'):
            return Interview.objects.filter(job__posted_by=user.recruiter_profile)
        elif hasattr(user, 'candidate_profile'):
            return Interview.objects.filter(candidate__user=user)
        return Interview.objects.none()
    def perform_create(self, serializer):
        recruiter = getattr(self.request.user, 'recruiter_profile', None)
        save_kwargs = {'recruiter': recruiter}
        # Use the recruiter-provided Google Meet link; fall back to a placeholder
        # only if none was supplied so the bot can still resolve an interview.
        if not serializer.validated_data.get('meet_link'):
            save_kwargs['meet_link'] = f"https://meet.servia.local/interviews/{uuid4()}"
        interview = serializer.save(**save_kwargs)
        Candidate.objects.filter(id=interview.candidate_id).update(
            status=Candidate.Status.INTERVIEW_SCHEDULED,
        )
        base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        confirm_url = f"{base_url}/interview/confirm/{interview.confirmation_token}"
        decline_url = f"{base_url}/interview/decline/{interview.confirmation_token}"

        send_interview_invite_email.delay(interview.id)

    @action(detail=False, methods=['get'], url_path='resolve-active')
    def resolve_active(self, request):
        candidate_id = request.query_params.get('candidate_id')
        if not candidate_id:
            return Response(
                {'detail': 'candidate_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        priority_order = Case(
            When(status=Interview.Status.IN_PROGRESS, then=Value(0)),
            When(status=Interview.Status.CONFIRMED, then=Value(1)),
            When(status=Interview.Status.SCHEDULED, then=Value(2)),
            default=Value(99),
            output_field=IntegerField(),
        )

        interview = (
            Interview.objects.filter(
                candidate_id=candidate_id,
                status__in=[
                    Interview.Status.IN_PROGRESS,
                    Interview.Status.CONFIRMED,
                    Interview.Status.SCHEDULED,
                ],
            )
            .annotate(status_priority=priority_order)
            .order_by('status_priority', 'scheduled_time', '-created_at')
            .first()
        )

        if interview is None:
            return Response(
                {'detail': 'No active interview found for this candidate'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                'interview_id': str(interview.id),
                'candidate_id': str(interview.candidate_id),
                'status': interview.status,
                'scheduled_time': interview.scheduled_time.isoformat() if interview.scheduled_time else None,
                'meet_link': interview.meet_link,
                'ws_path': f'/ws/interview/{interview.id}/',
            }
        )

    @action(detail=True, methods=['get'], url_path='follow-ups')
    def follow_ups(self, request, pk=None):
        """Return the latest AI follow-up questions for this interview."""
        interview = self.get_object()
        payload = cache.get(follow_up_cache_key(interview.id)) or {"questions": []}
        return Response(payload)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """Cancel a scheduled or confirmed interview (recruiter only)."""
        interview = self.get_object()
        cancellable = {Interview.Status.SCHEDULED, Interview.Status.CONFIRMED}
        if interview.status not in cancellable:
            return Response(
                {
                    'detail': (
                        f'Cannot cancel an interview with status "{interview.status}". '
                        'Only scheduled or confirmed interviews can be cancelled.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        interview.status = Interview.Status.CANCELLED
        interview.cancelled_at = timezone.now()
        reason = (request.data.get('reason') or '').strip()
        if reason:
            interview.cancellation_reason = reason
        interview.save(
            update_fields=['status', 'cancelled_at', 'cancellation_reason', 'updated_at'],
        )
        self._sync_candidate_status_after_cancel(interview)
        cache.delete(follow_up_cache_key(interview.id))
        return Response(InterviewSerializer(interview).data)

    @action(detail=True, methods=['post'], url_path='launch-bot')
    def launch_bot(self, request, pk=None):
        """
        Start the Google Meet bot for this interview via local docker-compose.
        Local/dev only: the backend and servia-bot must be on the same machine.
        """
        if not settings.DEBUG:
            return Response(
                {'detail': 'Bot auto-launch is only available in local/dev environments.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        bot_dir = settings.SERVIA_BOT_DIR
        if not bot_dir or not os.path.isdir(bot_dir):
            return Response(
                {'detail': 'SERVIA_BOT_DIR is not configured or does not exist on this server.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        interview = self.get_object()
        token, _ = Token.objects.get_or_create(user=request.user)

        env = {**os.environ, 'INTERVIEW_ID': str(interview.id), 'AUTH_TOKEN': token.key}
        try:
            subprocess.Popen(
                ['docker-compose', 'up', '-d', '--build'],
                cwd=bot_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            return Response(
                {'detail': 'docker-compose is not installed or not on PATH for this server process.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        interview.bot_join_status = Interview.BotJoinStatus.PENDING
        interview.save(update_fields=['bot_join_status', 'updated_at'])
        return Response(
            {'detail': 'Bot launch initiated.', 'bot_join_status': interview.bot_join_status},
            status=status.HTTP_202_ACCEPTED,
        )

    def _sync_candidate_status_after_cancel(self, interview):
        has_active = Interview.objects.filter(
            candidate_id=interview.candidate_id,
            status__in=[
                Interview.Status.SCHEDULED,
                Interview.Status.CONFIRMED,
                Interview.Status.IN_PROGRESS,
            ],
        ).exists()
        if not has_active:
            Candidate.objects.filter(id=interview.candidate_id).update(
                status=Candidate.Status.SHORTLISTED,
            )

class InterviewConversationViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get']
    queryset = InterviewConversation.objects.none()   # required for router

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'recruiter_profile'):
            return InterviewConversation.objects.filter(
                interview__job__posted_by=user.recruiter_profile
            )
        elif hasattr(user, 'candidate_profile'):
            return InterviewConversation.objects.filter(interview__candidate__user=user)
        return InterviewConversation.objects.none()

class InterviewConfirmView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, token):
        interview = get_object_or_404(Interview, confirmation_token=token)
        if interview.status == 'scheduled':
            interview.status = 'confirmed'
            interview.save()
            return HttpResponse("Your interview has been confirmed. Thank you.")
        else:
            return HttpResponse("This interview has already been processed.", status=400)

class InterviewDeclineView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, token):
        interview = get_object_or_404(Interview, confirmation_token=token)
        if interview.status == 'scheduled':
            interview.status = 'cancelled'
            interview.save()
            # Optionally send notification to recruiter
            return HttpResponse("Your interview has been declined. You may reschedule later.")
        else:
            return HttpResponse("This interview has already been processed.", status=400)
