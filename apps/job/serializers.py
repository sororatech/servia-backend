from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Job
from apps.users.serializers import RecruiterUserSerializer


class JobBasicSerializer(serializers.ModelSerializer):
    """
    Minimal job serializer for nested display.
    Only includes essential fields to avoid circular dependencies.
    """
    class Meta:
        model = Job
        fields = ['id', 'title', 'department', 'location']
        read_only_fields = ['id']


class JobSerializer(serializers.ModelSerializer):
    """Standard job serializer for list/retrieve"""
    candidate_count = serializers.IntegerField(read_only=True, default=0)
    openings_remaining = serializers.ReadOnlyField()
    salary_range = serializers.ReadOnlyField()
    posted_by = RecruiterUserSerializer(read_only=True)
    department_display = serializers.CharField(source='get_department_display', read_only=True)
    shift_type_display = serializers.CharField(source='get_shift_type_display', read_only=True)
    employment_type_display = serializers.CharField(source='get_employment_type_display', read_only=True)
    shortlisted_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Job
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_core_skills(self, value):
        """Validate that core_skills is a list of strings"""
        if not isinstance(value, list):
            raise serializers.ValidationError("core_skills must be a list")
        if not all(isinstance(skill, str) for skill in value):
            raise serializers.ValidationError("Each skill must be a string")
        return value
    
    def validate(self, data):
        """Validate salary range logic"""
        salary_min = data.get('salary_min')
        salary_max = data.get('salary_max')
        
        if salary_min is not None and salary_max is not None:
            if salary_min > salary_max:
                raise serializers.ValidationError({
                    'salary_min': 'Minimum salary cannot be greater than maximum salary.'
                })
        
        return data


class JobCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating jobs with duplicate detection.
    """
    warning = serializers.SerializerMethodField(read_only=True)
    similar_jobs = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Job
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_core_skills(self, value):
        """Validate that core_skills is a list of strings"""
        if not isinstance(value, list):
            raise serializers.ValidationError("core_skills must be a list")
        if not all(isinstance(skill, str) for skill in value):
            raise serializers.ValidationError("Each skill must be a string")
        return value
    
    def get_warning(self, obj):
        return self.context.get('warning', None)
    
    def get_similar_jobs(self, obj):
        return self.context.get('similar_jobs', [])
    
    def _normalize_location(self, location: str) -> str:
        """Normalize location for comparison: 'Addis Ababa, Ethiopia' -> 'addis ababa'"""
        if not location:
            return ""
        return location.split(',')[0].strip().lower()
    
    def _is_duplicate_job(self, job: Job, new_data: dict) -> bool:
        """
        Check if a job is a duplicate (OPTION B: global blocking).
        Blocks if title+location+department match, regardless of recruiter.
        """
        if job.title.lower().strip() != new_data['title'].lower().strip():
            return False
        if self._normalize_location(job.location) != self._normalize_location(new_data['location']):
            return False
        if job.department != new_data['department']:
            return False
        return True 
    
    def validate(self, data):
        """
        Validate job creation with duplicate detection (OPTION B: global blocking).
        Raises ValidationError for exact duplicates by ANY recruiter.
        """
        request = self.context.get('request')
        
        recent_jobs = Job.objects.filter(
            is_active=True,
            deleted_at__isnull=True,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('posted_by__user')
        
        for job in recent_jobs:
            if self._is_duplicate_job(job, data):  
                raise serializers.ValidationError({
                    'title': 'A job with this title and location already exists.',
                    'non_field_errors': [
                        f'A job titled "{data["title"]}" at location "{data["location"]}" '
                        f'was posted on {job.created_at.date()}. '
                        f'Please contact support if you believe this is an error.'
                    ]
                })
        
        if request and hasattr(request.user, 'recruiter_profile'):
            recruiter_user = request.user.recruiter_profile
            
            other_similar = Job.objects.filter(
                title__iexact=data['title'].strip(),
                location__iexact=data['location'].strip(),
                department=data['department'],
                is_active=True,
                deleted_at__isnull=True,
                created_at__gte=timezone.now() - timedelta(days=30)
            ).exclude(posted_by=recruiter_user)[:3]
            
            if other_similar.exists():
                self.context['warning'] = (
                    f"Note: {other_similar.count()} similar job(s) exist from other recruiters."
                )
                self.context['similar_jobs'] = [
                    {
                        'id': str(j.id),
                        'title': j.title,
                        'location': j.location,
                        'posted_by': j.posted_by.user.email if j.posted_by else 'Unknown',
                    }
                    for j in other_similar
                ]
        
        salary_min = data.get('salary_min')
        salary_max = data.get('salary_max')
        
        if salary_min is not None and salary_max is not None:
            if salary_min > salary_max:
                raise serializers.ValidationError({
                    'salary_min': 'Minimum salary cannot be greater than maximum salary.'
                })
        
        return data