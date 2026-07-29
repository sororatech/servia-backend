import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.candidate.models import Candidate
from apps.interview.models import Interview

class AIReport(models.Model):
    class ReportType(models.TextChoices):
        CV_SCREENING = 'cv_screening', 'CV Screening'
        INTERVIEW_ANALYSIS = 'interview_analysis', 'Interview Analysis'

    class Recommendation(models.TextChoices):
        HIRE = 'hire', 'Hire'
        HOLD = 'hold', 'Hold'
        REJECT = 'reject', 'Reject'

    class Confidence(models.TextChoices):
        HIGH = 'high', 'High'
        MEDIUM = 'medium', 'Medium'
        LOW = 'low', 'Low'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, db_index=True)
    interview = models.ForeignKey(Interview, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    report_type = models.CharField(max_length=20, choices=ReportType.choices, db_index=True)

    fit_score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    summary = models.TextField()
    strengths = models.JSONField()
    weaknesses = models.JSONField()
    feedback = models.TextField()
    extracted_skills = models.JSONField(default=list)
    skills_match_details = models.JSONField(blank=True, null=True)
    education_match = models.JSONField(blank=True, null=True)
    recommendation = models.CharField(max_length=20, choices=Recommendation.choices, blank=True, null=True)
    confidence = models.CharField(max_length=10, choices=Confidence.choices, blank=True, null=True)
    raw_response = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_report'
        indexes = [
            models.Index(fields=['candidate', 'report_type']),
            models.Index(fields=['candidate', 'interview']),
            models.Index(fields=['report_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.candidate} - {self.report_type} - Score: {self.fit_score}"


class TemporaryAIResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, db_index=True)
    raw_response = models.JSONField()
    attempt_count = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'temporary_ai_response'
        indexes = [
            models.Index(fields=['candidate', 'created_at']),
            models.Index(fields=['expires_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Temp response for {self.candidate} - {self.created_at}"