import uuid
from django.db import models
from apps.users.models import RecruiterUser

class Job(models.Model):
    class Department(models.TextChoices):
        FRONT_DESK = 'front_desk', 'Front Desk'
        HOUSEKEEPING = 'housekeeping', 'Housekeeping'
        FOOD_BEVERAGE = 'food_beverage', 'Food & Beverage'
        MAINTENANCE = 'maintenance', 'Maintenance'
        OTHER = 'other', 'Other'

    class ShiftType(models.TextChoices):
        MORNING = 'morning', 'Morning'
        EVENING = 'evening', 'Evening'
        NIGHT = 'night', 'Night'
        ROTATING = 'rotating', 'Rotating'

    class EmploymentType(models.TextChoices):
        FULL_TIME = 'full_time', 'Full Time'
        PART_TIME = 'part_time', 'Part Time'
        SEASONAL = 'seasonal', 'Seasonal'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.TextField()
    department = models.CharField(max_length=50, choices=Department.choices)
    shift_type = models.CharField(max_length=20, choices=ShiftType.choices)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices)
    location = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    posted_by = models.ForeignKey(RecruiterUser, on_delete=models.SET_NULL, null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'job'
        unique_together = [['title', 'location', 'department']] 
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['department', 'is_active']),
        ]

    def __str__(self):
        return self.title