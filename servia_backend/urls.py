"""
URL configuration for servia_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings  
from .views import home, health, trigger_test_error
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('health/', health),
    path('admin/', admin.site.urls),
    path('users/', include('apps.users.urls')),
    path('jobs/', include('apps.job.urls')),
    path('candidates/', include('apps.candidate.urls')),
    path('interviews/', include('apps.interview.urls')),
    path('ai-reports/', include('apps.ai_reports.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path("api/admin/", include("adminpanel.urls")),
]

# ONLY add dev-only endpoints when DEBUG=True
if settings.DEBUG:
    urlpatterns += [
        path('sentry-debug/', trigger_test_error, name='sentry-debug'),

    ]