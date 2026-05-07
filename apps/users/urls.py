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
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('verify-email/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification/', views.ResendVerificationView.as_view(), name='resend-verification'),
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('', include(router.urls))
]