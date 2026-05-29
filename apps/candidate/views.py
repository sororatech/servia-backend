import uuid
import logging
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Candidate, ActivityLog
from .serializers import CandidateSerializer, ActivityLogSerializer, MyApplicationSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import models
from django.db.models import Q 
from django.utils import timezone
from .services.storage import generate_signed_url
from apps.users.tasks import send_html_email
logger = logging.getLogger(__name__)

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
        candidate = Candidate.objects.get(id=candidate_id)
        if hasattr(request.user, 'candidate_profile'):
            if candidate.user != request.user:
                return Response({'error': 'Not your application.'}, status=403)
        else:
            return Response({'error': 'Only candidates can upload videos.'}, status=403)

        if candidate.video_intro_url:
            return Response({'error': 'Video already uploaded.'}, status=400)

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
            
            ActivityLog.objects.create(
                candidate=candidate,
                event_type=ActivityLog.EventType.VIDEO_UPLOADED,
                note="Video uploaded successfully",
                created_by_type=ActivityLog.CreatedByType.CANDIDATE,
                created_by_id=request.user.id
            )
            
            return Response({'message': 'Video uploaded successfully'}, status=200)
        else:
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
        
        allowed_formats = ['pdf', 'docx', 'png', 'jpg', 'jpeg']
        if file_extension not in allowed_formats:
            return Response({'error': 'Only PDF, DOCX, PNG, and JPG files are supported.'}, status=400)

        content_type_map = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
        }
        content_type = content_type_map.get(file_extension, 'application/octet-stream')

        file_key = f'cv/{candidate_id}/{uuid.uuid4()}.{file_extension}'
        
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
        import tempfile
        import requests
        import os
        import magic  
        
        candidate = Candidate.objects.get(id=candidate_id)
        file_key = request.data.get('file_key')
        filename = request.data.get('filename', '')  
        if not file_key:
            return Response({'error': 'file_key required'}, status=400)

        download_url = generate_signed_url(file_key, method='get_object', expires_in=300)
        response = requests.get(download_url)
        
        file_ext = filename.split('.')[-1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        
        try:
            mime = magic.from_file(tmp_path, mime=True)
            
            ALLOWED_MIMES = {
                'pdf': 'application/pdf',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'doc': 'application/msword',
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
            }
            
            expected_mime = ALLOWED_MIMES.get(file_ext)
            if not expected_mime:
                os.unlink(tmp_path)
                return Response(
                    {'error': f'File extension .{file_ext} not supported'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if mime != expected_mime:
                os.unlink(tmp_path)
                return Response(
                    {'error': f'File content does not match extension. Expected {expected_mime}, got {mime}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from apps.candidate.services.text_extraction import extract_cv_text
            extracted_text = extract_cv_text(tmp_path, file_ext)
            
            if not extracted_text:
                candidate.cv_status = 'error'
                candidate.save()
                os.unlink(tmp_path)
                return Response(
                    {'error': 'Could not extract text from CV. Please upload a text-based PDF or DOCX.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            candidate.cv_file = file_key
            candidate.cv_filename = filename
            candidate.cv_uploaded_at = timezone.now()
            candidate.cv_text = extracted_text
            candidate.cv_status = 'processing'
            candidate.save()

            
            from apps.ai_reports.tasks import analyze_cv_task
            task = analyze_cv_task.delay(
                candidate_id=str(candidate.id),
                cv_text=extracted_text,  # Already extracted above
                job_description=candidate.job.description if candidate.job else ""
            )


            os.unlink(tmp_path)


        except magic.MagicException:
            os.unlink(tmp_path)
            return Response(
                {'error': 'Could not validate file format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            candidate.cv_status = 'error'
            candidate.save()
            if 'tmp_path' in locals():
                os.unlink(tmp_path)
            # Log error for monitoring
            logger.error(f"CV upload error for candidate {candidate_id}: {str(e)}")
            return Response(
                {'error': 'Server error during CV processing'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({'status': 'CV uploaded successfully', 'cv_status': 'processing'})
        
class MyApplicationsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for candidates to view their own applications.
    Candidates can only see their own applications.
    Recruiters cannot access this endpoint.
    """
    serializer_class = MyApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'head', 'options']
    def get_queryset(self):
        user = self.request.user
        # Only candidates can access their applications
        if hasattr(user, 'candidate_profile'):
            return Candidate.objects.filter(
                user=user,
                deleted_at__isnull=True
            ).select_related('job__posted_by__user').order_by('-applied_at')
        return Candidate.objects.none()
    
    def get_permissions(self):
        """Only candidates can access this endpoint"""
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
class MyApplicationsStatsViewSet(viewsets.ViewSet):
    """
    ViewSet for candidate application statistics.
    Returns aggregated stats for candidate dashboard.
    """
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get']
    
    def list(self, request):
        user = request.user
        
        # Only candidates can access their stats
        if not hasattr(user, 'candidate_profile'):
            return Response({
                'total_applications': 0,
                'status_breakdown': {},
                'avg_ai_score': None,
                'cv_uploaded': 0,
                'video_uploaded': 0,
                'pending_actions': 0
            })
        
        applications = Candidate.objects.filter(
            user=user,
            deleted_at__isnull=True
        )
        
        total = applications.count()
        
        status_breakdown = applications.values('status').annotate(
            count=models.Count('id')
        )
        status_dict = {item['status']: item['count'] for item in status_breakdown}
        
        avg_score = applications.filter(
            ai_score__isnull=False
        ).aggregate(
            avg=models.Avg('ai_score')
        )['avg']
        
        cv_uploaded = applications.filter(
            cv_uploaded_at__isnull=False
        ).count()
        
        video_uploaded = applications.filter(
            video_uploaded_at__isnull=False
        ).count()
        
        pending_actions = applications.filter(
            Q(cv_uploaded_at__isnull=True) |
            Q(status='screened')
        ).count()
        
        stats = {
            'total_applications': total,
            'status_breakdown': status_dict,
            'avg_ai_score': round(avg_score, 1) if avg_score else None,
            'cv_uploaded': cv_uploaded,
            'video_uploaded': video_uploaded,
            'pending_actions': pending_actions
        }
        
        return Response(stats)