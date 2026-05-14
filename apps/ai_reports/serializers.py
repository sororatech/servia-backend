from rest_framework import serializers
from .models import AIReport, TemporaryAIResponse

class AIReportModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIReport
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class TemporaryAIResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemporaryAIResponse
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'expires_at']
class SkillsMatchDetailsSerializer(serializers.Serializer):
    """Nested serializer for skills_match_details validation"""
    matched_skills = serializers.ListField(child=serializers.CharField(), required=True)
    missing_skills = serializers.ListField(child=serializers.CharField(), required=True)
    match_explanation = serializers.CharField(required=True)

class AIReportSerializer(serializers.Serializer):
    fit_score = serializers.IntegerField(min_value=0, max_value=100)
    summary = serializers.CharField()
    strengths = serializers.ListField(child=serializers.CharField())
    weaknesses = serializers.ListField(child=serializers.CharField())
    feedback = serializers.CharField()
    extracted_skills = serializers.ListField(child=serializers.CharField(), default=list)
    skills_match_details = SkillsMatchDetailsSerializer(required=False, allow_null=True)
    education_match = serializers.JSONField(required=False, allow_null=True) 
    
    def validate_fit_score(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("fit_score must be between 0 and 100")
        return value

    def validate_strengths(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("strengths must be a list")
        if len(value) == 0:
            raise serializers.ValidationError("strengths cannot be empty")
        return value

    def validate_weaknesses(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("weaknesses must be a list")
        return value

    def validate_extracted_skills(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("extracted_skills must be a list")
        return value
    
    def validate_skills_match_details(self, value):
        """Validate the nested skills match structure"""
        if not value:
            return value
        if not isinstance(value, dict):
            raise serializers.ValidationError("skills_match_details must be an object")
        required = ['matched_skills', 'missing_skills', 'match_explanation']
        for field in required:
            if field not in value:
                raise serializers.ValidationError(f"skills_match_details missing: {field}")
        # Validate nested lists
        if not isinstance(value.get('matched_skills'), list):
            raise serializers.ValidationError("matched_skills must be a list")
        if not isinstance(value.get('missing_skills'), list):
            raise serializers.ValidationError("missing_skills must be a list")
        return value