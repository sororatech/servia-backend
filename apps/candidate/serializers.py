from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Candidate, ActivityLog
import boto3
from django.conf import settings


class UserBasicSerializer(serializers.ModelSerializer):
    """
    Simplified user serializer for nested display.
    """
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']


class CandidateSerializer(serializers.ModelSerializer):
    """
    Candidate serializer with signed download URLs for CV and video.
    """
    user = UserBasicSerializer(read_only=True)
    cv_download_url = serializers.SerializerMethodField()
    video_download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidate
        fields = '__all__'
        read_only_fields = ['id', 'applied_at', 'updated_at', 'user']
    
    def get_cv_download_url(self, obj):
        """Generate signed R2 URL for CV download (1-hour expiry)"""
        if not obj.cv_file:
            return None
        
        try:
            r2_client = boto3.client(
                's3',
                endpoint_url=settings.CLOUDFLARE_R2_ENDPOINT,
                aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY,
                aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_KEY,
            )
            
            url = r2_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.CLOUDFLARE_R2_BUCKET,
                    'Key': obj.cv_file,
                    'ResponseContentDisposition': f'attachment; filename="{obj.cv_filename}"'
                },
                ExpiresIn=3600  # 1 hour
            )
            return url
        except Exception as e:
            # Log error but don't break the response
            print(f"Error generating CV download URL: {e}")
            return None
    
    def get_video_download_url(self, obj):
        """Generate signed URL for video download"""
        if not obj.video_intro_url:
            return None
        
        # If using Cloudflare Stream, return the playback URL
        # If using R2, generate signed URL similar to CV
        return obj.video_intro_url


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = '__all__'
        read_only_fields = ['id', 'timestamp']