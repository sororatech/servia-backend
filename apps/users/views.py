import logging
import random
from datetime import timedelta

from rest_framework import viewsets, permissions, status, views
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.cache import cache
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.utils import timezone

from .models import CandidateUser, RecruiterUser
from .serializers import CandidateUserSerializer, RecruiterUserSerializer
from apps.users.tasks import send_welcome_email, send_password_reset_email, send_verification_email

logger = logging.getLogger(__name__)
User = get_user_model()


class CandidateUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for candidate profiles. Only admin users can list/create.
    """
    queryset = CandidateUser.objects.all()
    serializer_class = CandidateUserSerializer
    permission_classes = [permissions.IsAdminUser]


class RecruiterUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for recruiter profiles. Only admin users can list/create.
    """
    queryset = RecruiterUser.objects.all()
    serializer_class = RecruiterUserSerializer
    permission_classes = [permissions.IsAdminUser]


class CustomAuthToken(APIView):
    """
    Custom login endpoint that accepts email/password and returns a token.
    Uses Django's authenticate with username=email (since we set username to email).
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response(
                {'error': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'Please verify your email first',
                 'code': "EMAIL_NOT_VERIFIED"},
                status=status.HTTP_403_FORBIDDEN
            )

        user_type = None
        if hasattr(user, 'candidate_profile'):
            user_type = 'candidate'
        elif hasattr(user, 'recruiter_profile'):
            user_type = 'recruiter'
        else:
            user_type = 'recruiter'

        token, _ = Token.objects.get_or_create(user=user)

        response = Response({
            'user_id': user.id,
            'user_type': user_type,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }, status=status.HTTP_200_OK)

        response.set_cookie(
            key='auth_token',
            value=token.key,
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
            max_age=60 * 60 * 24 * 7,
            path='/',
        )

        response.set_cookie(
            key='user_role',
            value=user_type,
            httponly=False,
            secure=not settings.DEBUG,
            samesite='Lax',
            max_age=60 * 60 * 24 * 7,
            path='/',
        )

        return response


class CandidateRegistrationView(APIView):
    """
    Allow candidates to register without a username.
    Creates a Django User (with username=email) and a CandidateUser profile.
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        serializer = CandidateUserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                candidate = serializer.save()
                user = candidate.user
                user.is_active = False
                user.save()

                token, _ = Token.objects.get_or_create(user=user)
                
                verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                cache.set(f'verify_email_{user.email}', verification_code, timeout=600)

                # Send verification email
                send_verification_email.delay(user.email, verification_code, user.first_name or user.email)
                
                # Log to console for development
                logger.info(f"Verification code for {user.email}: {verification_code}")
                
                send_welcome_email.delay(user.id)

                response = Response({
                    'user_id': user.id,
                    'user_type': 'candidate',
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'message': 'Please verify your email to activate your account'
                }, status=status.HTTP_201_CREATED)

                response.set_cookie(
                    key='auth_token',
                    value=token.key,
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite='Lax',
                    max_age=60 * 60 * 24 * 7,
                    path='/',
                )
                response.set_cookie(
                    key='user_role',
                    value='candidate',
                    httponly=False,
                    secure=not settings.DEBUG,
                    samesite='Lax',
                    max_age=60 * 60 * 24 * 7,
                    path='/',
                )

                return response

            except IntegrityError as e:
                if 'duplicate key value violates unique constraint "auth_user_username_key"' in str(e):
                    existing_user = User.objects.filter(email=request.data.get('email')).first()
                    if existing_user and not existing_user.is_active:
                        if existing_user.date_joined and (timezone.now() - existing_user.date_joined) > timedelta(hours=2):
                            existing_user.delete()

                            serializer = CandidateUserSerializer(data=request.data)
                            if serializer.is_valid():
                                candidate = serializer.save()
                                user = candidate.user
                                user.is_active = False
                                user.save()

                                verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                                cache.set(f'verify_email_{user.email}', verification_code, timeout=600)

                                # Send verification email (FIXED: use correct variables)
                                send_verification_email.delay(user.email, verification_code, user.first_name or user.email)

                                # Log to console for development
                                logger.info(f"Verification code for {user.email}: {verification_code}")

                                send_welcome_email.delay(user.id)

                                token, _ = Token.objects.get_or_create(user=user)

                                response = Response({
                                    'user_id': user.id,
                                    'user_type': 'candidate',
                                    'email': user.email,
                                    'first_name': user.first_name,
                                    'last_name': user.last_name,
                                    'message': 'Please verify your email to activate your account'
                                }, status=status.HTTP_201_CREATED)

                                response.set_cookie(
                                    key='auth_token',
                                    value=token.key,
                                    httponly=True,
                                    secure=not settings.DEBUG,
                                    samesite='Lax',
                                    max_age=60 * 60 * 24 * 7,
                                    path='/',
                                )
                                response.set_cookie(
                                    key='user_role',
                                    value='candidate',
                                    httponly=False,
                                    secure=not settings.DEBUG,
                                    samesite='Lax',
                                    max_age=60 * 60 * 24 * 7,
                                    path='/',
                                )

                                return response

                    return Response(
                        {'error': 'A user with this email already exists.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                raise e


class RecruiterCreateView(APIView):
    """
    Only admin users can create recruiter accounts.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = RecruiterUserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    Logout endpoint that deletes the auth token and clears cookies.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
        except (AttributeError, Token.DoesNotExist):
            pass

        response = Response({'detail': 'Logged out successfully'}, status=status.HTTP_200_OK)
        response.delete_cookie('auth_token', path='/')
        response.delete_cookie('user_role', path='/')
        return response

    def options(self, request, *args, **kwargs):
        return Response(status=status.HTTP_200_OK)


class PasswordResetRequestView(views.APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'message': 'If an account exists with this email, you will receive a password reset link.'},
                status=status.HTTP_200_OK
            )
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_url = f"{frontend_url}/reset/{uid}/{token}/"
        
        send_password_reset_email(user.email, reset_url)
        
        return Response(
            {'message': 'If an account exists with this email, you will receive a password reset link.'},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(views.APIView):
    """
    Custom password reset confirmation.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        
        if not all([uid, token, new_password]):
            return Response(
                {'error': 'uid, token, and new_password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(id=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response(
                {'error': 'Invalid token or user ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        return Response(
            {'message': 'Password has been reset successfully'},
            status=status.HTTP_200_OK
        )


class VerifyEmailView(APIView):
    """Verify email with OTP code"""
    permission_classes = [AllowAny]
    
    @method_decorator(never_cache)
    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        
        if not email or not code:
            return Response(
                {'error': 'Email and code are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stored_code = cache.get(f'verify_email_{email}')
        
        if not stored_code:
            return Response(
                {'error': 'Code expired or not found. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if stored_code != code:
            return Response(
                {'error': 'Invalid verification code'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            user.is_active = True
            user.save()
            cache.delete(f'verify_email_{email}')
            
            return Response(
                {'message': 'Email verified successfully'},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ResendVerificationView(APIView):
    """Resend verification code"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if user.is_active:
            return Response(
                {'error': 'Email is already verified'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        cache.set(f'verify_email_{email}', code, timeout=600)
        
        # Send verification email
        send_verification_email.delay(email, code, user.first_name or email)
        
        # Log to console for development
        logger.info(f"Verification code for {email}: {code}")
        
        return Response(
            {'message': 'Verification code sent'},
            status=status.HTTP_200_OK
        )


class UserProfileView(APIView):
    """Get current user profile"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        user_type = None
        if hasattr(user, 'candidate_profile'):
            user_type = 'candidate'
            profile = user.candidate_profile
        elif hasattr(user, 'recruiter_profile'):
            user_type = 'recruiter'
            profile = user.recruiter_profile
        else:
            return Response(
                {'error': 'User profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        response_data = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'user_type': user_type,
            'profile_photo': getattr(profile, 'profile_photo', None),
        }
        
        return Response(response_data)