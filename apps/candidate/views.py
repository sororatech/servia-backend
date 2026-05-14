import uuid
import logging
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Candidate, ActivityLog
from .serializers import CandidateSerializer, ActivityLogSerializer, MyApplicationSerializer, VALID_TRANSITIONS
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import models
from django.db.models import Q 
from django.utils import timezone
from django.conf import settings
from apps.job.models import Job 
from .services.storage import generate_signed_url
from apps.users.tasks import send_html_email
from rest_framework.decorators import api_view, permission_classes

logger = logging.getLogger(__name__)
def _check_upload_permission(candidate, user):
    """
    Validate that user has permission to upload CV for this candidate.
    Returns (is_allowed: bool, error_message: str|None)
    """
    if hasattr(user, 'candidate_profile'):
        if candidate.user != user:
            return False, 'You can only modify your own applications.'
        return True, None
    
    elif hasattr(user, 'recruiter_profile'):
        if candidate.job.posted_by != user.recruiter_profile:
            return False, 'You do not have permission for this application.'
        return True, None
    
    elif user.is_superuser:
        return True, None
    
    return False, 'Unauthorized.'
class CandidateViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Candidate.objects.none()

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'recruiter_profile'):
            return Candidate.objects.filter(
                job__posted_by=user.recruiter_profile,
                deleted_at__isnull=True
            ).select_related('user', 'job__posted_by__user')
        elif hasattr(user, 'candidate_profile'):
            return Candidate.objects.filter(user=user, deleted_at__isnull=True)
        return Candidate.objects.none()

    def create(self, request, *args, **kwargs):
        user = request.user
        job_id = request.data.get('job')

        # Only check duplicates for authenticated candidates
        if hasattr(user, 'candidate_profile') and job_id:
            try:
                job = Job.objects.get(id=job_id)
            except Job.DoesNotExist:
                return Response({'job': ['Job not found.']}, status=status.HTTP_400_BAD_REQUEST)

            now = timezone.now()
            if not job.is_active:
                return Response({'job': ['This job is no longer accepting applications.']}, status=status.HTTP_400_BAD_REQUEST)
            if job.deleted_at:
                return Response({'job': ['This job has been removed.']}, status=status.HTTP_400_BAD_REQUEST)
            if job.application_deadline and job.application_deadline < now:
                return Response({'job': ['Application deadline has passed.']}, status=status.HTTP_400_BAD_REQUEST)

            existing = Candidate.objects.filter(user=user, job=job, deleted_at__isnull=True).first()

            if existing:
                # Gracefully return existing application instead of creating duplicate
                serializer = self.get_serializer(existing)
                return Response({
                    'id': serializer.data['id'],
                    'already_exists': True,
                    'message': 'You have already applied to this job.',
                    'status': existing.status
                }, status=status.HTTP_200_OK)

        # Proceed with normal creation if no duplicate found
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'candidate_profile'):
            serializer.save(user=user)
        else:
            raise PermissionDenied("Only candidates can create applications.")

    def update(self, request, *args, **kwargs):
        if not hasattr(request.user, 'recruiter_profile'):
            raise PermissionDenied("Only recruiters can update application status.")

        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        old_status = instance.status
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        new_status = instance.status
        
        # Send email notification if status changed
        if old_status != new_status:
            from apps.candidate.services.email_notifications import send_status_email
            send_status_email(instance, new_status, old_status)
            
            # Create ActivityLog for the status change
            from apps.candidate.models import ActivityLog
            ActivityLog.objects.create(
                candidate=instance,
                event_type=ActivityLog.EventType.SHORTLISTED if new_status == 'shortlisted'
                           else ActivityLog.EventType.HOLD if new_status == 'hold'
                           else ActivityLog.EventType.OFFERED if new_status == 'offered'
                           else ActivityLog.EventType.REJECTED_CV if new_status == 'rejected_cv'
                           else ActivityLog.EventType.REJECTED_INTERVIEW if new_status == 'rejected_interview'
                           else None,
                note=f"Status changed from {old_status} to {new_status}",
                created_by_type=ActivityLog.CreatedByType.RECRUITER,
                created_by_id=None,
                visibility=ActivityLog.Visibility.BOTH,
            )
        
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
                created_by_id=None,
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
        try:
            candidate = Candidate.objects.select_related('user', 'job__posted_by').get(id=candidate_id)
        except Candidate.DoesNotExist:
            return Response({'error': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)

        is_allowed, error_msg = _check_upload_permission(candidate, request.user)
        if not is_allowed:
            return Response({'error': error_msg}, status=status.HTTP_403_FORBIDDEN)

        file_extension = request.data.get('file_extension', 'pdf').lower()
        
        allowed_formats = ['pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg']
        if file_extension not in allowed_formats:
            return Response({'error': 'Only PDF, DOCX, DOC, PNG, and JPG files are supported.'}, status=400)

        content_type_map = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
        }
        content_type = content_type_map.get(file_extension)

        file_key = f'cv/{candidate_id}/{uuid.uuid4()}.{file_extension}'
        file_size = request.data.get('file_size', 0)
        max_size = getattr(settings, 'MAX_CV_SIZE_MB', 10) * 1024 * 1024

        if file_size and file_size > max_size:
            return Response({
                'error': f'File size exceeds {max_size // (1024*1024)}MB limit.'
            }, status=status.HTTP_400_BAD_REQUEST)

        signed_url = generate_signed_url(
            file_key,
            method='put_object',
            expires_in=900,          # 15 minutes
            content_type=content_type
        )
        return Response({
            'upload_url': signed_url,
            'file_key': file_key,
            'content_type': content_type,
        })
class CVUploadConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, candidate_id):
        import tempfile
        import requests
        import os
        import magic
        try:
            candidate = Candidate.objects.select_related('user', 'job__posted_by').get(id=candidate_id)
        except Candidate.DoesNotExist:
            return Response({'error': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)

        is_allowed, error_msg = _check_upload_permission(candidate, request.user)
        if not is_allowed:
            return Response({'error': error_msg}, status=status.HTTP_403_FORBIDDEN)

        file_key = request.data.get('file_key')
        client_filename = request.data.get('filename', '')
        if not file_key:
            return Response({'error': 'file_key required'}, status=400)

        # Prevent duplicate confirmation
        if candidate.cv_file == file_key:
            return Response({'error': 'This CV has already been confirmed.'}, status=400)

        # Store file reference (text not yet extracted)
        candidate.cv_file = file_key
        candidate.cv_filename = client_filename
        candidate.cv_uploaded_at = timezone.now()
        candidate.save(update_fields=['cv_file', 'cv_filename', 'cv_uploaded_at'])

        try:
            # 1. Download the file from R2
            download_url = generate_signed_url(file_key, method='get_object', expires_in=300)
            logger.info(f"Downloading CV from {download_url}")
            resp = requests.get(download_url, timeout=30)
            if resp.status_code != 200:
                candidate.cv_status = 'error'
                candidate.save(update_fields=['cv_status'])
                return Response({'error': f'Failed to download CV (HTTP {resp.status_code})'}, status=400)

            # 2. Save to temporary file for MIME detection & extraction
            # Use a safe extension from the file_key (not from client)
            ext = file_key.split('.')[-1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{ext}') as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name

            # 3. Validate MIME type (magic bytes)
            mime = magic.from_file(tmp_path, mime=True)
            logger.info(f"Detected MIME type: {mime}")

            ALLOWED_MIMES = {
                'application/pdf': 'pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
                'application/msword': 'doc', 
                'image/png': 'png',
                'image/jpeg': 'jpg',
            }
            if mime not in ALLOWED_MIMES:
                os.unlink(tmp_path)
                candidate.cv_status = 'error'
                candidate.save(update_fields=['cv_status'])
                return Response(
                    {'error': f'Invalid file type: {mime}. Allowed: PDF, DOCX, PNG, JPEG.'},
                    status=400
                )

            # Optional: Warn if extension mismatches actual MIME
            detected_ext = ALLOWED_MIMES[mime]
            if detected_ext != ext:
                logger.warning(f"MIME extension mismatch: file_key says {ext}, but content is {detected_ext}")

            # 4. Extract text using the detected extension
            from apps.candidate.services.text_extraction import extract_cv_text
            extracted_text = extract_cv_text(tmp_path, detected_ext)
            os.unlink(tmp_path)

            if not extracted_text:
                candidate.cv_status = 'error'
                candidate.save(update_fields=['cv_status'])
                return Response(
                    {'error': 'Could not extract text from CV. Please upload a text‑based PDF or DOCX.'},
                    status=400
                )

            # 5. Store extracted text
            candidate.cv_text = extracted_text
            candidate.save(update_fields=['cv_text'])

            # 6. QUEUE AI ANALYSIS (BEFORE setting cv_status)
            job = candidate.job
            core_skills_list = job.core_skills if job.core_skills else []
            core_skills_str = ", ".join(core_skills_list) if core_skills_list else "None specified"
            education_level_display = job.get_education_level_display()
            job_description = (
                f"Job Title: {job.title}\n\n"
                f"Description:\n{job.description or ''}\n\n"
                f"Requirements:\n{job.requirements or ''}\n\n"
                f"Minimum Education Level Required:\n{education_level_display}\n\n"
                f"Core Skills Required:\n{core_skills_str}"
            )
            from apps.ai_reports.tasks import analyze_cv_task
            analyze_cv_task.delay(str(candidate.id), extracted_text, job_description, core_skills_list, education_level_display)

            # 7. Mark as processing
            candidate.cv_status = Candidate.CVStatus.PROCESSING
            candidate.save(update_fields=['cv_status'])

            # 8. Create activity log
            ActivityLog.objects.create(
                candidate=candidate,
                event_type=ActivityLog.EventType.AI_ANALYSIS_QUEUED,  # ensure this choice exists
                note="AI analysis queued",
                created_by_type=ActivityLog.CreatedByType.CANDIDATE,
                created_by_id=None,
                visibility=ActivityLog.Visibility.BOTH,
            )

            logger.info(f"CV confirmed & queued for candidate {candidate_id}")
            return Response({'status': 'CV uploaded successfully', 'cv_status': 'processing'})

        except Exception as e:
            logger.error(f"CV confirm failed for candidate {candidate_id}: {e}", exc_info=True)
            candidate.cv_status = 'error'
            candidate.save(update_fields=['cv_status'])
            return Response(
                {'error': 'Failed to process CV. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
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
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_update_status(request):
    """
    Bulk update status for multiple candidates.
    Only recruiters can use this endpoint.
    """
    if not hasattr(request.user, 'recruiter_profile'):
        return Response({'error': 'Only recruiters can bulk update statuses.'}, status=403)
    
    candidate_ids = request.data.get('candidate_ids', [])
    new_status = request.data.get('status')
    
    if not candidate_ids or not new_status:
        return Response({'error': 'candidate_ids and status are required.'}, status=400)
    
    # Validate status is a valid choice
    if new_status not in Candidate.Status.values:
        return Response({'error': f'Invalid status. Choices: {Candidate.Status.values}'}, status=400)
    
    # Scope to recruiter's candidates only
    candidates = Candidate.objects.filter(
        id__in=candidate_ids,
        job__posted_by=request.user.recruiter_profile,
        deleted_at__isnull=True
    ).select_related('job__posted_by')
    
    updated_count = 0
    errors = []
    
    for candidate in candidates:
        old_status = candidate.status
        if new_status not in VALID_TRANSITIONS.get(old_status, []):
            errors.append({
                'candidate_id': str(candidate.id),
                'error': f"Cannot transition from '{old_status}' to '{new_status}'"
            })
            continue
        
        candidate.status = new_status
        candidate.save(update_fields=['status', 'updated_at'])
        
        # Send email notification
        from apps.candidate.services.email_notifications import send_status_email
        send_status_email(candidate, new_status, old_status)
        user_uuid = str(request.user.pk) if request.user.pk else None
        if user_uuid and isinstance(user_uuid, uuid.UUID):
            created_by_uuid = str(user_uuid)
        else:
            created_by_uuid = None  

        ActivityLog.objects.create(
            candidate=candidate,
            event_type=ActivityLog.EventType.SHORTLISTED if new_status == Candidate.Status.SHORTLISTED else ActivityLog.EventType.HOLD,
            note=f"Status changed from {old_status} to {new_status} via bulk update",
            created_by_type=ActivityLog.CreatedByType.RECRUITER,
            created_by_id=None, 
            visibility=ActivityLog.Visibility.BOTH,
        )
        updated_count += 1
    
    return Response({
        'updated_count': updated_count,
        'errors': errors,
        'message': f'Successfully updated {updated_count} candidates.'
    })