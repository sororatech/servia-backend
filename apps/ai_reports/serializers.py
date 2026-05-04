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


class AIReportSerializer(serializers.Serializer):
    fit_score = serializers.IntegerField(min_value=0, max_value=100)
    summary = serializers.CharField()
    strengths = serializers.ListField(child=serializers.CharField())
    weaknesses = serializers.ListField(child=serializers.CharField())
    feedback = serializers.CharField()
    extracted_skills = serializers.ListField(child=serializers.CharField(), default=list)

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
