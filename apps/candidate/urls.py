from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'candidates', views.CandidateViewSet)
router.register(r'activities', views.ActivityLogViewSet)

urlpatterns = [
    path('candidates/<uuid:candidate_id>/upload-cv/', views.CVUploadURLView.as_view(), name='upload-cv-url'),
    path('candidates/<uuid:candidate_id>/confirm-cv/', views.CVUploadConfirmView.as_view(), name='confirm-cv'),
    path('', include(router.urls)),
]