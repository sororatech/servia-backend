from rest_framework import viewsets, permissions
from .models import Job
from .serializers import JobSerializer
from apps.users.permissions import IsRecruiter

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer

    def get_permissions(self):
        """ 
        Public read-only; write actions require recruiter authentication 
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsRecruiter()]
        return [permissions.AllowAny()]