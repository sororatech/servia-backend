from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Q
from django.utils import timezone
from .models import Job
from .serializers import JobSerializer, JobCreateSerializer
from apps.users.permissions import IsRecruiter


class JobViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing job postings.
    """
    def get_queryset(self):
        user = self.request.user
        queryset = Job.objects.annotate(
            candidate_count=Count('candidate')
        ).select_related('posted_by__user').order_by('-created_at')
        
        if not hasattr(user, 'recruiter_profile'):
            return queryset.filter(is_active=True, deleted_at__isnull=True)
        
        return queryset.filter(
            Q(posted_by__user__id=user.id) | Q(is_active=True, deleted_at__isnull=True)
        )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return JobCreateSerializer
        return JobSerializer
    
    def get_permissions(self):
        """ 
        Public read-only; write actions require recruiter authentication 
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsRecruiter()]
        return [AllowAny()]
    
    def perform_create(self, serializer):
        """
        CRITICAL FIX: Set posted_by using correct attribute name.
        Model uses related_name='recruiter_profile', not 'recruiteruser'.
        """
        if hasattr(self.request.user, 'recruiter_profile'): 
            serializer.save(posted_by=self.request.user.recruiter_profile)  
        else:
            serializer.save()
    
    def create(self, request, *args, **kwargs):
        """
        Override create to capture warnings BEFORE saving.
        """
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        warning = serializer.context.get('warning')
        similar_jobs = serializer.context.get('similar_jobs', [])
        
        self.perform_create(serializer)
        
        headers = self.get_success_headers(serializer.data)
        response_data = dict(serializer.data)
        
        if warning:
            response_data['warning'] = warning
            response_data['similar_jobs'] = similar_jobs
        
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_destroy(self, instance):
        """Soft delete instead of hard delete"""
        instance.deleted_at = timezone.now()
        instance.is_active = False
        instance.save(update_fields=['deleted_at', 'is_active'])


@api_view(['GET'])
@permission_classes([AllowAny])
def department_categories(request):
    """Return departments grouped by category for frontend dropdowns."""
    categories = Job.Department.get_department_categories()
    
    formatted = {
        category: [
            {'value': dept.value, 'label': dept.label}
            for dept in depts
        ]
        for category, depts in categories.items()
    }
    
    return Response(formatted)