import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class CandidateUser(models.Model):
    """
    Profile for job applicants.
    Linked one-to-one with Django's User model.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='candidate_profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True, null=True)
    profile_photo = models.CharField(max_length=500, blank=True, null=True)  # Cloudflare R2 URL
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'candidate_user'

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"


class RecruiterUser(models.Model):
    """
    Profile for agency staff.
    Linked one-to-one with Django's User model.
    """
    class Role(models.TextChoices):
        RECRUITER = 'recruiter', 'Recruiter'
        ADMIN = 'admin', 'Admin'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='recruiter_profile')
    department = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RECRUITER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recruiter_user'

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class SystemMetric(models.Model):
    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['key', '-updated_at']),
        ]