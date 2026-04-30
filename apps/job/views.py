from rest_framework import viewsets, permissions
from django.db.models import Count
from .models import Job
from .serializers import JobSerializer
from apps.users.permissions import IsRecruiter

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.annotate(candidate_count=Count('candidate'))
    serializer_class = JobSerializer

    def get_permissions(self):
        """ 
        Public read-only; write actions require recruiter authentication 
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsRecruiter()]
        return [permissions.AllowAny()]