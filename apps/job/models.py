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
    
    core_skills = models.JSONField(
        default=list,
        blank=True,
        help_text="List of required skills for this job, e.g. ['customer service', 'communication']"
    )
    
    department = models.CharField(max_length=50, choices=Department.choices)
    shift_type = models.CharField(max_length=20, choices=ShiftType.choices)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices)
    location = models.CharField(max_length=200)
    
    openings_count = models.IntegerField(
        default=1,
        help_text="Number of positions available for this job"
    )
    
    # Salary fields
    salary_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum salary for this position"
    )
    salary_max = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum salary for this position"
    )
    salary_currency = models.CharField(
        max_length=3,
        default='ETB',
        choices=[
            ('ETB', 'Ethiopian Birr'),
            ('USD', 'US Dollar'),
            ('EUR', 'Euro'),
            ('GBP', 'British Pound'),
            ('AED', 'UAE Dirham'),
        ],
        help_text="Currency code for salary"
    )
    salary_period = models.CharField(
        max_length=20,
        default='monthly',
        choices=[
            ('hourly', 'Per Hour'),
            ('daily', 'Per Day'),
            ('weekly', 'Per Week'),
            ('monthly', 'Per Month'),
            ('yearly', 'Per Year'),
        ],
        help_text="Period for salary (hourly, monthly, etc.)"
    )
    
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
    
    @property
    def salary_range(self):
        """Return formatted salary range for display"""
        if self.salary_min and self.salary_max:
            return f"{self.salary_min:,.0f} - {self.salary_max:,.0f} {self.salary_currency}/{self.salary_period}"
        elif self.salary_min:
            return f"From {self.salary_min:,.0f} {self.salary_currency}/{self.salary_period}"
        elif self.salary_max:
            return f"Up to {self.salary_max:,.0f} {self.salary_currency}/{self.salary_period}"
        return "Competitive / Based on Experience"