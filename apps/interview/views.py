"""
Interview and conversation views.
Candidates can only view their own interviews; recruiters can view all and manage.
"""
import os
from django.db.models import Case, IntegerField, Value, When
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsRecruiter
from apps.users.tasks import send_interview_invite_email

from .models import Interview, InterviewConversation
from .serializers import InterviewSerializer, InterviewConversationSerializer


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

    @action(detail=False, methods=['get'], url_path='resolve-active')
    def resolve_active(self, request):
        candidate_id = request.query_params.get('candidate_id')
        if not candidate_id:
            return Response(
                {'detail': 'candidate_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        priority_order = Case(
            When(status=Interview.Status.IN_PROGRESS, then=Value(0)),
            When(status=Interview.Status.CONFIRMED, then=Value(1)),
            When(status=Interview.Status.SCHEDULED, then=Value(2)),
            default=Value(99),
            output_field=IntegerField(),
        )

        interview = (
            Interview.objects.filter(
                candidate_id=candidate_id,
                status__in=[
                    Interview.Status.IN_PROGRESS,
                    Interview.Status.CONFIRMED,
                    Interview.Status.SCHEDULED,
                ],
            )
            .annotate(status_priority=priority_order)
            .order_by('status_priority', 'scheduled_time', '-created_at')
            .first()
        )

        if interview is None:
            return Response(
                {'detail': 'No active interview found for this candidate'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                'interview_id': str(interview.id),
                'candidate_id': str(interview.candidate_id),
                'status': interview.status,
                'scheduled_time': interview.scheduled_time.isoformat() if interview.scheduled_time else None,
                'meet_link': interview.meet_link,
                'ws_path': f'/ws/interview/{interview.id}/',
            }
        )

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
