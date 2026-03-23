# apps/candidate/views.py

from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Candidate, ActivityLog
from .serializers import CandidateSerializer, ActivityLogSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
class CandidateViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Candidate.objects.none()          # required for router

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'recruiter_profile'):
            return Candidate.objects.all()
        elif hasattr(user, 'candidate_profile'):
            return Candidate.objects.filter(user=user)
        return Candidate.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'candidate_profile'):
            serializer.save(user=user)
        else:
            raise PermissionDenied("Only candidates can create applications.")


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
    permission_classes = [permissions.IsAuthenticated]  # or allow candidates only

    def post(self, request, candidate_id):
        # Ensure the candidate belongs to the logged‑in user
        candidate = Candidate.objects.get(id=candidate_id)
        if hasattr(request.user, 'candidate_profile'):
            if candidate.user != request.user:
                return Response({'error': 'Not your application.'}, status=403)
        else:
            return Response({'error': 'Only candidates can upload videos.'}, status=403)

        # Enforce max 3 attempts
        if candidate.video_attempts >= 3:
            return Response(
                {'error': 'Maximum 3 upload attempts reached.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process the video upload (e.g., get signed URL from Cloudflare, save the URL)

        # After successful upload:
        candidate.video_attempts += 1
        candidate.video_uploaded_at = timezone.now()
        candidate.save()

        return Response({'message': 'Video uploaded successfully'}, status=200)