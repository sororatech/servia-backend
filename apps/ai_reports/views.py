"""
AI report views.
Candidates can view only their own reports; recruiters can view all.
Write operations are restricted to admin recruiters (system internal use).
"""
from rest_framework import viewsets, permissions
from .models import AIReport, TemporaryAIResponse
from .serializers import AIReportModelSerializer, TemporaryAIResponseSerializer
from apps.users.permissions import IsRecruiter, IsAdminRecruiter

class AIReportViewSet(viewsets.ModelViewSet):
    serializer_class = AIReportModelSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = AIReport.objects.none()            # required for router

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminRecruiter()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'recruiter_profile'):
            return AIReport.objects.all()
        elif hasattr(user, 'candidate_profile'):
            return AIReport.objects.filter(candidate__user=user)
        return AIReport.objects.none()


class TemporaryAIResponseViewSet(viewsets.ModelViewSet):
    queryset = TemporaryAIResponse.objects.all()
    serializer_class = TemporaryAIResponseSerializer
    permission_classes = [IsAdminRecruiter]
    http_method_names = ['get', 'delete']
