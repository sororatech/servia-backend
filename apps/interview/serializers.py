from rest_framework import serializers
from .models import Interview, InterviewConversation

class InterviewSerializer(serializers.ModelSerializer):
    recruiter_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Interview
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'calendar_event_id']
    
    def get_recruiter_name(self, obj):
        if obj.recruiter and obj.recruiter.user:
            return f"{obj.recruiter.user.first_name} {obj.recruiter.user.last_name}".strip()
        return "Unknown"

class InterviewConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewConversation
        fields = '__all__'
        read_only_fields = ['id']