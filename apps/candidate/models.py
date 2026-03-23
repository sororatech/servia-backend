import uuid
from django.conf import settings                      # <-- import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.job.models import Job

class Candidate(models.Model):
    class Status(models.TextChoices):
        APPLIED = 'applied', 'Applied'
        SCREENED = 'screened', 'Screened'
        SHORTLISTED = 'shortlisted', 'Shortlisted'
        VIDEO_SUBMITTED = 'video_submitted', 'Video Submitted'
        INTERVIEW_SCHEDULED = 'interview_scheduled', 'Interview Scheduled'
        INTERVIEWED = 'interviewed', 'Interviewed'
        OFFERED = 'offered', 'Offered'
        REJECTED_CV = 'rejected_cv', 'Rejected CV'
        REJECTED_INTERVIEW = 'rejected_interview', 'Rejected Interview'
        HOLD = 'hold', 'Hold'

    class CVStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        UPLOADED = 'uploaded', 'Uploaded'
        PROCESSING = 'processing', 'Processing'
        ANALYZED = 'analyzed', 'Analyzed'
        ERROR = 'error', 'Error'

    class Confidence(models.TextChoices):
        HIGH = 'high', 'High'
        MEDIUM = 'medium', 'Medium'
        LOW = 'low', 'Low'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)   # use settings.AUTH_USER_MODEL
    job = models.ForeignKey(Job, on_delete=models.CASCADE, db_index=True)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.APPLIED, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    cv_file = models.CharField(max_length=500, blank=True, null=True)
    cv_filename = models.CharField(max_length=255, blank=True, null=True)
    cv_text = models.TextField(blank=True, null=True)
    cv_uploaded_at = models.DateTimeField(blank=True, null=True)
    cv_status = models.CharField(max_length=20, choices=CVStatus.choices, default=CVStatus.PENDING, db_index=True)

    video_intro_url = models.CharField(max_length=500, blank=True, null=True)
    video_uploaded_at = models.DateTimeField(blank=True, null=True)
    video_attempts = models.IntegerField(default=0, validators=[MaxValueValidator(3)])

    ai_score = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)], db_index=True)
    ai_summary = models.TextField(blank=True, null=True)
    ai_strengths = models.JSONField(default=list)
    ai_weaknesses = models.JSONField(default=list)
    ai_feedback = models.TextField(blank=True, null=True)
    ai_confidence = models.CharField(max_length=10, choices=Confidence.choices, blank=True, null=True)

    applied_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'candidate'
        unique_together = [['user', 'job']]
        indexes = [
            models.Index(fields=['job', 'status', 'ai_score']),
            models.Index(fields=['job', 'applied_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.job.title}"


class ActivityLog(models.Model):
    class EventType(models.TextChoices):
        ACCOUNT_CREATED = 'account_created', 'Account Created'
        APPLICATION_SUBMITTED = 'application_submitted', 'Application Submitted'
        CV_UPLOADED = 'cv_uploaded', 'CV Uploaded'
        AI_ANALYSIS_COMPLETE = 'ai_analysis_complete', 'AI Analysis Complete'
        SHORTLISTED = 'shortlisted', 'Shortlisted'
        REJECTED_CV = 'rejected_cv', 'Rejected CV'
        VIDEO_UPLOADED = 'video_uploaded', 'Video Uploaded'
        INTERVIEW_SCHEDULED = 'interview_scheduled', 'Interview Scheduled'
        INTERVIEW_CONFIRMED = 'interview_confirmed', 'Interview Confirmed'
        INTERVIEW_COMPLETED = 'interview_completed', 'Interview Completed'
        INTERVIEW_REPORT_GENERATED = 'interview_report_generated', 'Interview Report Generated'
        OFFERED = 'offered', 'Offered'
        REJECTED_INTERVIEW = 'rejected_interview', 'Rejected Interview'
        HOLD = 'hold', 'Hold'

    class Visibility(models.TextChoices):
        CANDIDATE = 'candidate', 'Candidate'
        RECRUITER = 'recruiter', 'Recruiter'
        BOTH = 'both', 'Both'

    class CreatedByType(models.TextChoices):
        CANDIDATE = 'candidate', 'Candidate'
        RECRUITER = 'recruiter', 'Recruiter'
        SYSTEM = 'system', 'System'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, db_index=True)
    event_type = models.CharField(max_length=50, choices=EventType.choices, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    note = models.TextField(blank=True, null=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.BOTH)
    created_by_type = models.CharField(max_length=20, choices=CreatedByType.choices, blank=True, null=True)
    created_by_id = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'activity_log'
        indexes = [
            models.Index(fields=['candidate', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.candidate} - {self.event_type} at {self.timestamp}"