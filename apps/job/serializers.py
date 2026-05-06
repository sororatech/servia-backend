from rest_framework import serializers
from .models import Job

class JobSerializer(serializers.ModelSerializer):
    candidate_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Job
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'posted_by']
    
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