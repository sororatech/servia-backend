from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db.models import Count, Q
from django.utils import timezone
import logging
from .models import Job
from .serializers import JobListSerializer, JobCreateSerializer, JobDetailSerializer, JobUpdateSerializer

logger = logging.getLogger(__name__)

class JobViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        queryset = Job.objects.annotate(
            candidate_count=Count('candidate', filter=Q(candidate__deleted_at__isnull=True))
        ).select_related('posted_by__user').order_by('-created_at')
        
        if not hasattr(user, 'recruiteruser'):
            return queryset.filter(is_active=True, deleted_at__isnull=True)
        
        return queryset.filter(
            Q(posted_by__user=user) | Q(is_active=True, deleted_at__isnull=True)
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return JobListSerializer
        elif self.action == 'create':
            return JobCreateSerializer
        elif self.action == 'retrieve':
            return JobDetailSerializer
        elif self.action in ['update', 'partial_update']:
            return JobUpdateSerializer
        return JobListSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Create a new job with duplicate detection.
        
        Returns 201 Created with job data + optional warning.
        Returns 400 Bad Request if duplicate detected.
        """
        logger.info(f"Job creation request from user: {request.user.email if request.user.is_authenticated else 'anonymous'}")
        
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}  # ← Critical: pass request for duplicate check
        )
        
        # Validate (runs validate() which may raise ValidationError for duplicates)
        serializer.is_valid(raise_exception=True)
        
        # Capture optional warning BEFORE saving (context may be lost after save)
        warning = serializer.context.get('warning')
        similar_jobs = serializer.context.get('similar_jobs', [])
        
        if warning:
            logger.warning(f"Duplicate warning for job creation: {warning}")
        
        # Save the job
        self.perform_create(serializer)
        
        # Build response with warnings explicitly included
        headers = self.get_success_headers(serializer.data)
        response_data = dict(serializer.data)
        
        # Add warning fields to response (they won't be in serializer.data after save)
        if warning:
            response_data['warning'] = warning
            response_data['similar_jobs'] = similar_jobs
        
        logger.info(f"Job created: id={response_data.get('id')}, title={response_data.get('title')}")
        
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
    def perform_create(self, serializer):
        if hasattr(self.request.user, 'recruiteruser'):
            recruiter = self.request.user.recruiteruser
            logger.info(f"Saving job with posted_by={recruiter.id} (user={recruiter.user.email})")
            serializer.save(posted_by=recruiter)
        else:
            logger.warning("Job created by non-recruiter user – posted_by will be null")
            serializer.save()
    
    def perform_destroy(self, instance):
        """Soft delete instead of hard delete"""
        instance.deleted_at = timezone.now()
        instance.is_active = False
        instance.save(update_fields=['deleted_at', 'is_active'])