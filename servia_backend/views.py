from django.http import HttpResponse
from django.conf import settings
import os
import requests
from django.utils import timezone
from django.db import connection
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from django.db.models import Sum
from apps.users.models import SystemMetric

def home(request):
    return HttpResponse("Hello Servia AI")

def trigger_test_error(request):
    """Test endpoint for Sentry verification - REMOVE AFTER TESTING"""
    if settings.DEBUG: 
        raise Exception("Test error from ServiaAI - Sentry verification")
    return HttpResponse("Not available in production", status=403)
def health(request):
    return HttpResponse("ok")

class SystemHealthDashboard(APIView):
    """
    Fetches real data from Sentry API for the Health Dashboard
    Uses DRF token authentication (not session auth)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = os.getenv('SENTRY_ORG')
        project = os.getenv('SENTRY_PROJECT')
        auth_token = os.getenv('SENTRY_AUTH_TOKEN')

        if not all([org, project, auth_token]):
            return Response({'error': 'Sentry not configured'}, status=500)

        headers = {'Authorization': f'Bearer {auth_token}'}
        issues_url = f"https://sentry.io/api/0/projects/{org}/{project}/issues/"
        params = {
            'query': '',                   
            'per_page': 100,
            'sort': 'date',                
            'statsPeriod': '24h',          
}
        error_count = 0
        recent_errors = []

        try:
            res = requests.get(issues_url, headers=headers, params=params, timeout=10)
            if res.status_code == 200:
                issues = res.json()
                error_count = sum([int(issue.get('count', 0) or 0) for issue in issues])
                recent_errors = [
                    {
                        'id': issue['id'],
                        'title': issue['title'],
                        'level': issue.get('level', 'error'),
                        'culprit': issue.get('culprit', ''),
                        'count': int(issue.get('count', 1) or 1),
                        'url': f"https://sentry.io/organizations/{org}/issues/{issue['id']}/",
                        'first_seen': issue.get('firstSeen', ''),
                    }
                    for issue in issues[:5]
                ]
        except Exception as e:
            import traceback
            traceback.print_exc()

        services = {}
        try:
            connection.ensure_connection()
            services['database'] = 'ok'
        except Exception as e:
            services['database'] = 'error'
        try:
            from django.core.cache import cache
            cache.set('_health', 'ok', 10)
            services['cache'] = 'ok' if cache.get('_health') == 'ok' else 'error'
        except Exception as e:
            services['cache'] = 'error'

        now = timezone.now()
        month_key = f"gemini_usage_{now.strftime('%Y-%m')}"
        current_usage = (SystemMetric.objects.filter(key=month_key).values_list('value', flat=True).first() or 0)
        monthly_limit = 10000
        percentage = (current_usage / monthly_limit * 100) if monthly_limit > 0 else 0
        resets_on = now.replace(year=now.year + 1, month=1, day=1) if now.month == 12 else now.replace(month=now.month + 1, day=1)

        ok = SystemMetric.objects.filter(key__startswith='health_ok_').aggregate(Sum('value'))['value__sum'] or 0
        fail = SystemMetric.objects.filter(key__startswith='health_fail_').aggregate(Sum('value'))['value__sum'] or 0
        total_checks = ok + fail
        uptime_percentage = round((ok / total_checks * 100), 2) if total_checks > 0 else 99.98

        system_status = 'healthy'
        if error_count > 50 or any(v == 'error' for v in services.values()):
            system_status = 'degraded'

        return Response({
            'status': system_status,
            'error_count_24h': error_count,
            'uptime_percentage': uptime_percentage, 
            'services': services,
            'api_usage': {
                'current': current_usage,        
                'limit': monthly_limit,
                'percentage': round(percentage, 1),
                'resets_on': resets_on.strftime('%Y-%m-%d'),
            },
            'recent_errors': recent_errors,
            'sentry': {
                'configured': True,
                'org': org,
                'project': project,
                'project_url': f"https://sentry.io/organizations/{org}/projects/{project}/",
            }
        })

