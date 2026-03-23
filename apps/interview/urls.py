from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'interviews', views.InterviewViewSet)
router.register(r'conversations', views.InterviewConversationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]