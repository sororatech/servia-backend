from rest_framework import serializers
from .models import Interview, InterviewConversation

class InterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'meet_link', 'calendar_event_id']

class InterviewConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewConversation
        fields = '__all__'
        read_only_fields = ['id']