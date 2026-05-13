from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'candidates', views.CandidateViewSet)
router.register(r'activities', views.ActivityLogViewSet)
router.register(r'my-applications', views.MyApplicationsViewSet, basename='my-applications')
router.register(r'my-applications-stats', views.MyApplicationsStatsViewSet, basename='my-applications-stats')

urlpatterns = [
    path('candidates/<uuid:candidate_id>/upload-cv/', views.CVUploadURLView.as_view(), name='upload-cv-url'),
    path('candidates/<uuid:candidate_id>/confirm-cv/', views.CVUploadConfirmView.as_view(), name='confirm-cv'),
    path('candidates/<uuid:candidate_id>/upload-video/', views.VideoUploadView.as_view(), name='upload-video'),
    path('bulk-update-status/', views.bulk_update_status, name='bulk-update-status'),
    path('', include(router.urls)),
]