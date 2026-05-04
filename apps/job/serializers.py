from rest_framework import serializers
from .models import Job

class JobSerializer(serializers.ModelSerializer):
    candidate_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Job
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'posted_by']