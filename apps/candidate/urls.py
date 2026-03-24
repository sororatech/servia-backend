from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'candidates', views.CandidateViewSet)
router.register(r'activities', views.ActivityLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('candidates/<uuid:candidate_id>/upload-video/', views.VideoUploadView.as_view(), name='upload-video'),
]