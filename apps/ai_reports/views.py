"""
AI report views.
Candidates can view only their own reports; recruiters can view reports for
candidates who applied to jobs they posted.
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
            queryset = AIReport.objects.filter(
                candidate__job__posted_by=user.recruiter_profile
            ).select_related('candidate__user')
        elif hasattr(user, 'candidate_profile'):
            queryset = AIReport.objects.filter(candidate__user=user).select_related('candidate__user')
        else:
            queryset = AIReport.objects.none()

        interview_id = self.request.query_params.get('interview')
        if interview_id:
            queryset = queryset.filter(interview_id=interview_id)

        report_type = self.request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        return queryset


class TemporaryAIResponseViewSet(viewsets.ModelViewSet):
    queryset = TemporaryAIResponse.objects.all()
    serializer_class = TemporaryAIResponseSerializer
    permission_classes = [IsAdminRecruiter]
    http_method_names = ['get', 'delete']
