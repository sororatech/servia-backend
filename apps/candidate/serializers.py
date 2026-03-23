from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Candidate, ActivityLog

class UserBasicSerializer(serializers.ModelSerializer):
    """
    Simplified user serializer for nested display.
    """
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']


class CandidateSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)

    class Meta:
        model = Candidate
        fields = '__all__'
        read_only_fields = ['id', 'applied_at', 'updated_at', 'user']


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = '__all__'
        read_only_fields = ['id', 'timestamp']