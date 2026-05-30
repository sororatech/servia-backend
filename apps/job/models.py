import uuid
from django.db import models
from apps.users.models import RecruiterUser

class Job(models.Model):
    class Department(models.TextChoices):
        # Front of House (Guest-Facing)
        FRONT_OFFICE = 'front_office', 'Front Office / Reception'
        CONCIERGE = 'concierge', 'Concierge'
        GUEST_RELATIONS = 'guest_relations', 'Guest Relations'
        BELL_STAFF = 'bell_staff', 'Bell Staff / Porter'
        
        # Housekeeping
        HOUSEKEEPING = 'housekeeping', 'Housekeeping'
        LAUNDRY = 'laundry', 'Laundry'
        LINEN_ROOM = 'linen_room', 'Linen Room'
        PUBLIC_AREA = 'public_area', 'Public Area Cleaning'
        
        # Food & Beverage
        FOOD_BEVERAGE = 'food_beverage', 'Food & Beverage (General)'
        RESTAURANT = 'restaurant', 'Restaurant'
        BAR_LOUNGE = 'bar_lounge', 'Bar / Lounge'
        ROOM_SERVICE = 'room_service', 'Room Service'
        BANQUET_EVENTS = 'banquet_events', 'Banquet & Events'
        BREAKFAST_ROOM = 'breakfast_room', 'Breakfast Room'
        VIP_LOUNGE = 'vip_lounge', 'VIP Lounge'
        
        # Kitchen
        KITCHEN = 'kitchen', 'Kitchen (General)'
        EXECUTIVE_CHEF = 'executive_chef', 'Executive Chef'
        SOUS_CHEF = 'sous_chef', 'Sous Chef'
        LINE_COOK = 'line_cook', 'Line Cook'
        PASTRY = 'pastry', 'Pastry / Bakery'
        COLD_KITCHEN = 'cold_kitchen', 'Cold Kitchen / Garde Manger'
        STEWARDING = 'stewarding', 'Stewarding / Dishwashing'
        
        # Operations & Maintenance
        MAINTENANCE = 'maintenance', 'Maintenance / Engineering'
        SECURITY = 'security', 'Security'
        SAFETY = 'safety', 'Health & Safety'
        LOSS_PREVENTION = 'loss_prevention', 'Loss Prevention'
        
        # Management
        MANAGEMENT = 'management', 'Management (General)'
        GENERAL_MANAGER = 'general_manager', 'General Manager'
        DEPARTMENT_MANAGER = 'department_manager', 'Department Manager'
        ASSISTANT_MANAGER = 'assistant_manager', 'Assistant Manager'
        FRONT_OFFICE_MANAGER = 'front_office_manager', 'Front Office Manager'
        EXECUTIVE_HOUSEKEEPER = 'executive_housekeeper', 'Executive Housekeeper'
        F_B_MANAGER = 'f_b_manager', 'Food & Beverage Manager'
        
        # Administrative
        HUMAN_RESOURCES = 'human_resources', 'Human Resources'
        FINANCE_ACCOUNTING = 'finance_accounting', 'Finance & Accounting'
        SALES_MARKETING = 'sales_marketing', 'Sales & Marketing'
        PROCUREMENT = 'procurement', 'Procurement / Purchasing'
        IT_SUPPORT = 'it_support', 'IT Support'
        ADMIN_OFFICE = 'admin_office', 'Administrative Office'
        
        # Wellness & Recreation
        SPA_WELLNESS = 'spa_wellness', 'Spa & Wellness'
        FITNESS_CENTER = 'fitness_center', 'Fitness Center / Gym'
        RECREATION = 'recreation', 'Recreation / Activities'
        SWIMMING_POOL = 'swimming_pool', 'Swimming Pool'
        
        # Other
        OTHER = 'other', 'Other'

        @classmethod
        def get_department_categories(cls):
            """Return departments grouped by category for frontend dropdowns."""
            return {
                'Front of House': [
                    cls.FRONT_OFFICE, cls.CONCIERGE, cls.GUEST_RELATIONS, cls.BELL_STAFF,
                ],
                'Housekeeping': [
                    cls.HOUSEKEEPING, cls.LAUNDRY, cls.LINEN_ROOM, cls.PUBLIC_AREA,
                ],
                'Food & Beverage': [
                    cls.FOOD_BEVERAGE, cls.RESTAURANT, cls.BAR_LOUNGE, cls.ROOM_SERVICE,
                    cls.BANQUET_EVENTS, cls.BREAKFAST_ROOM, cls.VIP_LOUNGE,
                ],
                'Kitchen': [
                    cls.KITCHEN, cls.EXECUTIVE_CHEF, cls.SOUS_CHEF, cls.LINE_COOK,
                    cls.PASTRY, cls.COLD_KITCHEN, cls.STEWARDING,
                ],
                'Operations & Maintenance': [
                    cls.MAINTENANCE, cls.SECURITY, cls.SAFETY, cls.LOSS_PREVENTION,
                ],
                'Management': [
                    cls.MANAGEMENT, cls.GENERAL_MANAGER, cls.DEPARTMENT_MANAGER,
                    cls.ASSISTANT_MANAGER, cls.FRONT_OFFICE_MANAGER,
                    cls.EXECUTIVE_HOUSEKEEPER, cls.F_B_MANAGER,
                ],
                'Administrative': [
                    cls.HUMAN_RESOURCES, cls.FINANCE_ACCOUNTING, cls.SALES_MARKETING,
                    cls.PROCUREMENT, cls.IT_SUPPORT, cls.ADMIN_OFFICE,
                ],
                'Wellness & Recreation': [
                    cls.SPA_WELLNESS, cls.FITNESS_CENTER, cls.RECREATION, cls.SWIMMING_POOL,
                ],
                'Other': [cls.OTHER],
            }
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
    
    class EducationLevel(models.TextChoices):
        NONE = 'none', 'No formal education required'
        HIGH_SCHOOL = 'high_school', 'High School / Secondary'
        VOCATIONAL = 'vocational', 'Vocational / Trade Certificate'
        DIPLOMA = 'diploma', 'Diploma (Hospitality / Hotel Management)'
        BACHELOR = 'bachelor', 'Bachelor\'s Degree (Hospitality / Business)'
        MASTER = 'master', 'Master\'s Degree (MBA / Hospitality Management)'
        PROFESSIONAL_CERT = 'professional_cert', 'Professional Certification (e.g., CHA, CHT)'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    requirements = models.TextField()
    
    core_skills = models.JSONField(
        default=list,
        blank=True,
        help_text="List of required skills for this job"
    )
    
    department = models.CharField(max_length=50, choices=Department.choices, db_index=True)
    shift_type = models.CharField(max_length=20, choices=ShiftType.choices, db_index=True)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices, db_index=True)
    location = models.CharField(max_length=200, db_index=True)
    
    openings_count = models.IntegerField(
        default=1,
        help_text="Number of positions available for this job"
    )
    
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
        help_text="Period for salary"
    )
    
    is_active = models.BooleanField(default=True, db_index=True)
    posted_by = models.ForeignKey(RecruiterUser, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    application_deadline = models.DateTimeField(
        null=True, 
        blank=True, 
        db_index=True,
        help_text="Last date candidates can apply. Leave blank for open-ended roles."
    )
    education_level = models.CharField(
        max_length=20,
        choices=EducationLevel.choices,
        default=EducationLevel.NONE,
        db_index=True,
        help_text="Minimum education level required for this job"
    )

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
        """Return formatted salary range for display"""
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
        from apps.candidate.models import Candidate
        return Candidate.objects.filter(job=self, deleted_at__isnull=True).count()
    
    @property
    def openings_remaining(self):
        """Return number of openings still available (only count HIRED candidates)"""
        from apps.candidate.models import Candidate
        hired_count = Candidate.objects.filter(
            job=self,
            status=Candidate.Status.HIRED,
            deleted_at__isnull=True
        ).count()
        return max(0, self.openings_count - hired_count)