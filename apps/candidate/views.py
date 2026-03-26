import uuid
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Candidate, ActivityLog
from .serializers import CandidateSerializer, ActivityLogSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from .services.storage import generate_signed_url
from apps.users.tasks import send_html_email

class CandidateViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Candidate.objects.none()          # required for router

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'recruiter_profile'):
            return Candidate.objects.all()
        elif hasattr(user, 'candidate_profile'):
            return Candidate.objects.filter(user=user)
        return Candidate.objects.none()
    
    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'candidate_profile'):
            serializer.save(user=user)
        else:
            raise PermissionDenied("Only candidates can create applications.")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        old_status = instance.status
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        new_status = instance.status
        if old_status != new_status:
            from apps.candidate.services.email_notifications import send_status_email
            send_status_email(instance, new_status, old_status)
        return Response(serializer.data)


class ActivityLogViewSet(viewsets.ModelViewSet):
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get']
    queryset = ActivityLog.objects.none()        # required for router

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'recruiter_profile'):
            return ActivityLog.objects.all()
        elif hasattr(user, 'candidate_profile'):
            return ActivityLog.objects.filter(candidate__user=user)
        return ActivityLog.objects.none()


class VideoUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, candidate_id):
        # Ensure the candidate belongs to the logged‑in user
        candidate = Candidate.objects.get(id=candidate_id)
        if hasattr(request.user, 'candidate_profile'):
            if candidate.user != request.user:
                return Response({'error': 'Not your application.'}, status=403)
        else:
            return Response({'error': 'Only candidates can upload videos.'}, status=403)

        # Check if video already uploaded successfully
        if candidate.video_intro_url:
            return Response({'error': 'Video already uploaded.'}, status=400)

        # Cooldown check (5 failed attempts = 1 hour lock)
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        
        if candidate.video_attempts >= 5:
            if candidate.video_last_failed_attempt and candidate.video_last_failed_attempt > one_hour_ago:
                # Still in cooldown
                wait_minutes = 60 - ((timezone.now() - candidate.video_last_failed_attempt).seconds // 60)
                return Response(
                    {'error': f'Too many failed attempts. Please try again in {wait_minutes} minutes.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            else:
                # Cooldown period passed, reset attempts
                candidate.video_attempts = 0
                candidate.video_last_failed_attempt = None
                candidate.save(update_fields=['video_attempts', 'video_last_failed_attempt'])

        upload_success = True  
        
        if upload_success:
            # Success: store video info and reset attempts
            candidate.video_intro_url = "https://stream.example.com/video-id"  # Replace with actual URL
            candidate.video_uploaded_at = timezone.now()
            candidate.video_attempts = 0
            candidate.video_last_failed_attempt = None
            candidate.save()
            
            # Create activity log
            ActivityLog.objects.create(
                candidate=candidate,
                event_type=ActivityLog.EventType.VIDEO_UPLOADED,
                note="Video uploaded successfully",
                created_by_type=ActivityLog.CreatedByType.CANDIDATE,
                created_by_id=request.user.id
            )
            
            return Response({'message': 'Video uploaded successfully'}, status=200)
        else:
            # Failure: increment attempts and record time
            candidate.video_attempts += 1
            candidate.video_last_failed_attempt = timezone.now()
            candidate.save(update_fields=['video_attempts', 'video_last_failed_attempt'])
            
            remaining = 5 - candidate.video_attempts
            return Response(
                {'error': f'Upload failed. {remaining} attempts remaining.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class CVUploadURLView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, candidate_id):
        candidate = Candidate.objects.get(id=candidate_id)
        if candidate.user != request.user and not hasattr(request.user, 'recruiter_profile'):
            return Response({'error': 'Not authorized'}, status=403)
        
        file_extension = request.data.get('file_extension', 'pdf').lower()
        if file_extension not in ['pdf', 'docx']:
            return Response({'error': 'Only PDF and DOCX files are supported.'}, status=400)

        # Map extension to MIME type
        content_type_map = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        content_type = content_type_map.get(file_extension, 'application/octet-stream')

        file_key = f'cv/{candidate_id}/{uuid.uuid4()}.{file_extension}'
        
        # Pass content_type to generate_signed_url
        signed_url = generate_signed_url(
            file_key, 
            method='put_object', 
            expires_in=900,  # 15 minutes
            content_type=content_type 
        )
        
        return Response({
            'upload_url': signed_url, 
            'file_key': file_key,
            'content_type': content_type,  # Return this for frontend to use
        })

class CVUploadConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, candidate_id):
        candidate = Candidate.objects.get(id=candidate_id)
        file_key = request.data.get('file_key')
        filename = request.data.get('filename', '')
        if not file_key:
            return Response({'error': 'file_key required'}, status=400)

        candidate.cv_file = file_key
        candidate.cv_filename = filename
        candidate.cv_uploaded_at = timezone.now()
        candidate.cv_status = 'uploaded'
        candidate.save()      
        return Response({'status': 'CV uploaded successfully'})