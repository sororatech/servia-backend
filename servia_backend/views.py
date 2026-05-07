from django.http import HttpResponse
from django.conf import settings

def home(request):
    return HttpResponse("Hello Servia AI")

def trigger_test_error(request):
    """Test endpoint for Sentry verification - REMOVE AFTER TESTING"""
    if settings.DEBUG: 
        raise Exception("Test error from ServiaAI - Sentry verification")
    return HttpResponse("Not available in production", status=403)
def health(request):
    return HttpResponse("ok")
    