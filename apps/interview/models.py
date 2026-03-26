import uuid
from django.db import models
from apps.candidate.models import Candidate
from apps.job.models import Job
from apps.users.models import RecruiterUser

class Interview(models.Model):
    class Stage(models.TextChoices):
        STAGE_1 = 'stage_1', 'Stage 1'
        STAGE_2 = 'stage_2', 'Stage 2'
        STAGE_3 = 'stage_3', 'Stage 3'

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        CONFIRMED = 'confirmed', 'Confirmed'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No Show'

    class BotJoinStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        JOINED = 'joined', 'Joined'
        FAILED = 'failed', 'Failed'
        NOT_ENABLED = 'not_enabled', 'Not Enabled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, db_index=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, db_index=True)
    recruiter = models.ForeignKey(RecruiterUser, on_delete=models.SET_NULL, null=True, blank=True)

    scheduled_time = models.DateTimeField(db_index=True)
    duration_minutes = models.IntegerField(default=30)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.STAGE_1)

    meet_link = models.CharField(max_length=500)
    calendar_event_id = models.CharField(max_length=255, blank=True, null=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED, db_index=True)
    bot_join_status = models.CharField(max_length=20, choices=BotJoinStatus.choices, default=BotJoinStatus.PENDING)

    cancelled_at = models.DateTimeField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    confirmation_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'interview'
        indexes = [
            models.Index(fields=['status', 'scheduled_time']),
            models.Index(fields=['candidate', 'status']),
            models.Index(fields=['recruiter', 'scheduled_time']),
        ]

    def __str__(self):
        return f"Interview {self.candidate} - {self.scheduled_time}"


class InterviewConversation(models.Model):
    class Speaker(models.TextChoices):
        RECRUITER = 'recruiter', 'Recruiter'
        CANDIDATE = 'candidate', 'Candidate'
        UNKNOWN = 'unknown', 'Unknown'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, db_index=True)
    speaker = models.CharField(max_length=20, choices=Speaker.choices, default=Speaker.UNKNOWN)
    text = models.TextField()
    timestamp = models.DateTimeField()
    confidence = models.FloatField(blank=True, null=True)

    class Meta:
        db_table = 'interview_conversation'
        indexes = [
            models.Index(fields=['interview', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.interview} - {self.speaker}: {self.text[:50]}"