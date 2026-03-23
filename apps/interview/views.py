"""
Interview and conversation views.
Candidates can only view their own interviews; recruiters can view all and manage.
"""
from rest_framework import viewsets, permissions
from .models import Interview, InterviewConversation
from .serializers import InterviewSerializer, InterviewConversationSerializer
from apps.users.permissions import IsRecruiter

class InterviewViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Interview.objects.none()          # required for router

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsRecruiter()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'recruiter_profile'):
            return Interview.objects.all()
        elif hasattr(user, 'candidate_profile'):
            return Interview.objects.filter(candidate__user=user)
        return Interview.objects.none()


class InterviewConversationViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get']
    queryset = InterviewConversation.objects.none()   # required for router

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'recruiter_profile'):
            return InterviewConversation.objects.all()
        elif hasattr(user, 'candidate_profile'):
            return InterviewConversation.objects.filter(interview__candidate__user=user)
        return InterviewConversation.objects.none()