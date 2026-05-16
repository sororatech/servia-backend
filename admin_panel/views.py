from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response

from recruiters.models import Recruiter
from candidates.models import CandidateUser


class AdminStatsView(APIView):
    def get(self, request):
        one_week_ago = timezone.now() - timedelta(days=7)

        total_recruiters = Recruiter.objects.count()
        active_recruiters = Recruiter.objects.filter(is_active=True).count()
        disabled_recruiters = Recruiter.objects.filter(is_active=False).count()

        total_candidates = CandidateUser.objects.count()
        new_users_this_week = CandidateUser.objects.filter(
            date_joined__gte=one_week_ago
        ).count()

        return Response({
            "total_recruiters": total_recruiters,
            "active_recruiters": active_recruiters,
            "disabled_recruiters": disabled_recruiters,
            "total_candidates": total_candidates,
            "new_users_this_week": new_users_this_week
        })