from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'reports', views.AIReportViewSet)
router.register(r'temp', views.TemporaryAIResponseViewSet)

urlpatterns = [
    path('', include(router.urls)),
]