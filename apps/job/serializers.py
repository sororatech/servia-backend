from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
import logging
from .models import Job
from apps.users.serializers import RecruiterUserSerializer

logger = logging.getLogger(__name__)


class JobListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for job list views.
    Includes computed fields for display.
    """
    candidate_count = serializers.SerializerMethodField()
    salary_range = serializers.ReadOnlyField()
    openings_remaining = serializers.ReadOnlyField()
    posted_by = RecruiterUserSerializer(read_only=True)
    department_display = serializers.CharField(source='get_department_display', read_only=True)
    shift_type_display = serializers.CharField(source='get_shift_type_display', read_only=True)
    employment_type_display = serializers.CharField(source='get_employment_type_display', read_only=True)
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'department', 'department_display',
            'shift_type', 'shift_type_display',
            'employment_type', 'employment_type_display',
            'location', 'is_active', 'openings_count', 'openings_remaining',
            'salary_min', 'salary_max', 'salary_currency',
            'salary_period', 'salary_range',
            'candidate_count', 'posted_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'posted_by']
    
    def get_candidate_count(self, obj):
        """Get number of applications for this job"""
        if hasattr(obj, 'candidate_count'):
            return obj.candidate_count
        return obj.applications_count


class JobCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating jobs with robust duplicate detection.
    
    Duplicate logic:
    - BLOCK exact duplicates by same recruiter (flexible location/dept matching)
    - WARN about similar jobs from other recruiters (doesn't block)
    """
    warning = serializers.SerializerMethodField(read_only=True)
    similar_jobs = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Job
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_warning(self, obj):
        return self.context.get('warning', None)
    
    def get_similar_jobs(self, obj):
        return self.context.get('similar_jobs', [])
    
    def _normalize_location(self, location: str) -> str:
        """
        Normalize location for comparison.
        Examples:
        - "Addis Ababa, Ethiopia" → "addis ababa"
        - "addis ababa" → "addis ababa"
        """
        if not location:
            return ""
        # Take first part before comma, lowercase, strip whitespace
        return location.split(',')[0].strip().lower()
    
    def _normalize_department(self, department: str) -> str:
        """
        Normalize department for comparison.
        Maps legacy values to current values.
        """
        # Map old/legacy values to current canonical values
        dept_mapping = {
            'front_desk': 'front_office',
            'frontdesk': 'front_office',
            'front-office': 'front_office',
            'house_keeping': 'housekeeping',
            'housekeeping': 'housekeeping',
            'food_beverage': 'food_beverage',
            'food-beverage': 'food_beverage',
            'food & beverage': 'food_beverage',
        }
        return dept_mapping.get(department.lower().replace('-', '_').replace(' ', '_'), department.lower())
    
    def _is_duplicate_job(self, job: Job, new_data: dict, recruiter_user) -> bool:
        """
        Check if a job is a duplicate of the one being created.
        Uses flexible matching for location and department.
        """
        # Must be same recruiter
        if not job.posted_by or job.posted_by != recruiter_user:
            return False
        
        # Must have same title (case-insensitive)
        if job.title.lower().strip() != new_data['title'].lower().strip():
            return False
        
        # Must have similar location (flexible matching)
        if self._normalize_location(job.location) != self._normalize_location(new_data['location']):
            return False
        
        # Must have same/similar department (with legacy mapping)
        if self._normalize_department(job.department) != self._normalize_department(new_data['department']):
            return False
        
        return True
    
    def validate(self, data):
        """
        Validate job creation with duplicate detection.
        
        Raises ValidationError for exact duplicates by same recruiter.
        Stores warning for similar jobs by other recruiters.
        """
        request = self.context.get('request')
        
        if request and hasattr(request.user, 'recruiteruser'):
            recruiter_user = request.user.recruiteruser
            
            # Get all active jobs by this recruiter in last 30 days
            recent_jobs = Job.objects.filter(
                posted_by=recruiter_user,
                is_active=True,
                deleted_at__isnull=True,
                created_at__gte=timezone.now() - timedelta(days=30)
            )
            # .select_related('posted_by__user')
            # Check each job for duplicate (flexible matching)
            for job in recent_jobs:
                if self._is_duplicate_job(job, data, recruiter_user):
                    logger.warning(
                        f"Duplicate job blocked: recruiter={recruiter_user.user.email}, "
                        f"title='{data['title']}', location='{data['location']}', "
                        f"existing_job_id={job.id}"
                    )
                    raise serializers.ValidationError({
                        'title': 'You already have an active job with this title and location.',
                        'non_field_errors': [
                            f'A job titled "{data["title"]}" at location "{data["location"]}" '
                            f'was posted on {job.created_at.date()}. '
                            f'Please update the existing posting\'s openings_count instead of creating a duplicate.'
                        ]
                    })
            
            # Optional: Warn about similar jobs from OTHER recruiters
            other_similar = Job.objects.filter(
                title__iexact=data['title'].strip(),
                is_active=True,
                deleted_at__isnull=True,
                created_at__gte=timezone.now() - timedelta(days=30)
            ).exclude(
                posted_by=recruiter_user
            )[:3]
            
            if other_similar.exists():
                self.context['warning'] = (
                    f"Note: {other_similar.count()} similar job(s) exist from other recruiters. "
                    f"Please verify this is not a duplicate posting."
                )
                self.context['similar_jobs'] = [
                    {
                        'id': str(j.id),
                        'title': j.title,
                        'location': j.location,
                        'department': j.get_department_display(),
                        'posted_by': j.posted_by.user.email if j.posted_by else 'Unknown',
                        'created_at': j.created_at.isoformat(),
                    }
                    for j in other_similar
                ]
        
        # Validate salary range
        if data.get('salary_min') is not None and data.get('salary_max') is not None:
            if data['salary_min'] > data['salary_max']:
                raise serializers.ValidationError({
                    'salary_min': 'Minimum salary cannot be greater than maximum salary.',
                    'salary_max': 'Maximum salary cannot be less than minimum salary.'
                })
        
        return data


class JobDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for job detail views.
    Includes all fields plus computed properties.
    """
    candidate_count = serializers.SerializerMethodField()
    salary_range = serializers.ReadOnlyField()
    openings_remaining = serializers.ReadOnlyField()
    posted_by = RecruiterUserSerializer(read_only=True)
    department_display = serializers.CharField(source='get_department_display', read_only=True)
    shift_type_display = serializers.CharField(source='get_shift_type_display', read_only=True)
    employment_type_display = serializers.CharField(source='get_employment_type_display', read_only=True)
    
    class Meta:
        model = Job
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'posted_by']
    
    def get_candidate_count(self, obj):
        if hasattr(obj, 'candidate_count'):
            return obj.candidate_count
        return obj.applications_count


class JobUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating jobs.
    Allows updating all fields except posted_by.
    """
    class Meta:
        model = Job
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'posted_by']
    
    def validate(self, data):
        """Validate salary range on update"""
        salary_min = data.get('salary_min', self.instance.salary_min if self.instance else None)
        salary_max = data.get('salary_max', self.instance.salary_max if self.instance else None)
        
        if salary_min is not None and salary_max is not None:
            if salary_min > salary_max:
                raise serializers.ValidationError({
                    'salary_min': 'Minimum salary cannot be greater than maximum salary.'
                })
        
        return data