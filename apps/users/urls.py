from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'candidates', views.CandidateUserViewSet)
router.register(r'recruiters', views.RecruiterUserViewSet)

urlpatterns = [
    path('login/', views.CustomAuthToken.as_view(), name='login'),
    path('register/', views.CandidateRegistrationView.as_view(), name='register'), 
    path('recruiters/create/', views.RecruiterCreateView.as_view(), name='create_recruiter'),
    path('', include(router.urls))
]