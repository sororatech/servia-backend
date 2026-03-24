"""
Interview and conversation views.
Candidates can only view their own interviews; recruiters can view all and manage.
"""
import os
from rest_framework import viewsets, permissions
from .models import Interview, InterviewConversation
from .serializers import InterviewSerializer, InterviewConversationSerializer
from apps.users.permissions import IsRecruiter
from apps.users.tasks import send_interview_invite_email
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework.views import APIView
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
    def perform_create(self, serializer):
        interview = serializer.save()
        base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        confirm_url = f"{base_url}/interview/confirm/{interview.confirmation_token}"
        decline_url = f"{base_url}/interview/decline/{interview.confirmation_token}"

        send_interview_invite_email.delay(interview.id)

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

class InterviewConfirmView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, token):
        interview = get_object_or_404(Interview, confirmation_token=token)
        if interview.status == 'scheduled':
            interview.status = 'confirmed'
            interview.save()
            return HttpResponse("Your interview has been confirmed. Thank you.")
        else:
            return HttpResponse("This interview has already been processed.", status=400)

class InterviewDeclineView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, token):
        interview = get_object_or_404(Interview, confirmation_token=token)
        if interview.status == 'scheduled':
            interview.status = 'cancelled'
            interview.save()
            # Optionally send notification to recruiter
            return HttpResponse("Your interview has been declined. You may reschedule later.")
        else:
            return HttpResponse("This interview has already been processed.", status=400)