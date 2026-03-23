from rest_framework import serializers
from .models import AIReport, TemporaryAIResponse

class AIReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIReport
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class TemporaryAIResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemporaryAIResponse
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'expires_at']