import uuid
from django.db import models
from django.core.validators import MinValueValidator
from apps.users.models import RecruiterUser


class Job(models.Model):
    class Department(models.TextChoices):
        # Front of House (Guest-Facing)
        FRONT_OFFICE = 'front_office', 'Front Office / Reception'
        CONCIERGE = 'concierge', 'Concierge'
        GUEST_RELATIONS = 'guest_relations', 'Guest Relations'
        
        # Housekeeping
        HOUSEKEEPING = 'housekeeping', 'Housekeeping'
        LAUNDRY = 'laundry', 'Laundry'
        
        # Food & Beverage
        FOOD_BEVERAGE = 'food_beverage', 'Food & Beverage'
        RESTAURANT = 'restaurant', 'Restaurant'
        BAR_LOUNGE = 'bar_lounge', 'Bar / Lounge'
        ROOM_SERVICE = 'room_service', 'Room Service'
        BANQUET_EVENTS = 'banquet_events', 'Banquet & Events'
        
        # Kitchen
        KITCHEN = 'kitchen', 'Kitchen'
        EXECUTIVE_CHEF = 'executive_chef', 'Executive Chef'
        SOUS_CHEF = 'sous_chef', 'Sous Chef'
        LINE_COOK = 'line_cook', 'Line Cook'
        
        # Operations
        MAINTENANCE = 'maintenance', 'Maintenance / Engineering'
        SECURITY = 'security', 'Security'
        SAFETY = 'safety', 'Health & Safety'
        
        # Management
        MANAGEMENT = 'management', 'Management'
        GENERAL_MANAGER = 'general_manager', 'General Manager'
        DEPARTMENT_MANAGER = 'department_manager', 'Department Manager'
        
        # Administrative
        HUMAN_RESOURCES = 'human_resources', 'Human Resources'
        FINANCE_ACCOUNTING = 'finance_accounting', 'Finance & Accounting'
        SALES_MARKETING = 'sales_marketing', 'Sales & Marketing'
        PROCUREMENT = 'procurement', 'Procurement / Purchasing'
        
        # Wellness & Recreation
        SPA_WELLNESS = 'spa_wellness', 'Spa & Wellness'
        FITNESS_CENTER = 'fitness_center', 'Fitness Center'
        RECREATION = 'recreation', 'Recreation / Activities'
        
        # Other
        OTHER = 'other', 'Other'

    class ShiftType(models.TextChoices):
        MORNING = 'morning', 'Morning (6:00 AM - 2:00 PM)'
        AFTERNOON = 'afternoon', 'Afternoon (2:00 PM - 10:00 PM)'
        EVENING = 'evening', 'Evening (4:00 PM - 12:00 AM)'
        NIGHT = 'night', 'Night (10:00 PM - 6:00 AM)'
        ROTATING = 'rotating', 'Rotating Shifts'
        FLEXIBLE = 'flexible', 'Flexible Hours'
        ON_CALL = 'on_call', 'On-Call'
        SPLIT = 'split', 'Split Shift'

    class EmploymentType(models.TextChoices):
        FULL_TIME = 'full_time', 'Full-Time'
        PART_TIME = 'part_time', 'Part-Time'
        CONTRACT = 'contract', 'Contract'
        TEMPORARY = 'temporary', 'Temporary'
        SEASONAL = 'seasonal', 'Seasonal'
        INTERNSHIP = 'internship', 'Internship'
        APPRENTICESHIP = 'apprenticeship', 'Apprenticeship'


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    requirements = models.TextField()
    department = models.CharField(max_length=50, choices=Department.choices, db_index=True)
    shift_type = models.CharField(max_length=20, choices=ShiftType.choices, db_index=True)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices, db_index=True)
    location = models.CharField(max_length=200, db_index=True)
    openings_count = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of positions available for this job"
    )
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(
        max_length=3,
        default='ETB',
        choices=[
            ('ETB', 'Ethiopian Birr'),
            ('USD', 'US Dollar'),
            ('EUR', 'Euro'),
            ('GBP', 'British Pound'),
            ('AED', 'UAE Dirham'),
        ]
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
        ]
    )
    is_active = models.BooleanField(default=True, db_index=True)
    posted_by = models.ForeignKey(RecruiterUser, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'job'
        indexes = [
            models.Index(fields=['is_active', 'deleted_at']),
            models.Index(fields=['department', 'is_active']),
            models.Index(fields=['employment_type', 'is_active']),
            models.Index(fields=['location', 'is_active']),
            models.Index(fields=['title', 'is_active']),
            models.Index(fields=['created_at']),
            models.Index(fields=['posted_by', 'is_active']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} at {self.location}"
    
    @property
    def salary_range(self):
        """
        Return formatted salary range for display.
        Examples:
        - "15,000 - 25,000 ETB/monthly"
        - "From 20,000 ETB/monthly"
        - "Up to 30,000 USD/yearly"
        - "Competitive / Based on Experience"
        """
        if self.salary_min and self.salary_max:
            return f"{self.salary_min:,.0f} - {self.salary_max:,.0f} {self.salary_currency}/{self.salary_period}"
        elif self.salary_min:
            return f"From {self.salary_min:,.0f} {self.salary_currency}/{self.salary_period}"
        elif self.salary_max:
            return f"Up to {self.salary_max:,.0f} {self.salary_currency}/{self.salary_period}"
        return "Competitive / Based on Experience"
    
    @property
    def applications_count(self):
        """Return number of applications for this job"""
        return Candidate.objects.filter(job=self, deleted_at__isnull=True).count()
    
    @property
    def openings_remaining(self):
        """Return number of openings still available"""
        return max(0, self.openings_count - self.applications_count)