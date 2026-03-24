from rest_framework import viewsets, permissions, status, views
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from django.db import IntegrityError
from .models import CandidateUser, RecruiterUser
from .serializers import CandidateUserSerializer, RecruiterUserSerializer
from apps.users.tasks import send_welcome_email, send_password_reset_email
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings

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

        # Determine user type based on which profile exists
        user_type = None
        if hasattr(user, 'candidate_profile'):
            user_type = 'candidate'
        elif hasattr(user, 'recruiter_profile'):
            user_type = 'recruiter'
        else:
            # For superusers without profile, treat as recruiter (or restrict)
            user_type = 'recruiter'

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user_id': user.id,
            'user_type': user_type,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        })

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
                token, _ = Token.objects.get_or_create(user=user)
                # Send welcome email asynchronously
                send_welcome_email.delay(user.id)
                return Response({
                    'token': token.key,
                    'user_id': user.id,
                    'user_type': 'candidate',
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }, status=status.HTTP_201_CREATED)
            except IntegrityError as e:
                if 'duplicate key value violates unique constraint "auth_user_username_key"' in str(e):
                    return Response(
                        {'error': 'A user with this email already exists.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                raise e 
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)

User = get_user_model()

class PasswordResetRequestView(views.APIView):
    """
    Custom password reset request that triggers async email via Celery.
    """
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
            # Return 200 even if user not found (security best practice)
            return Response(
                {'message': 'If an account exists with this email, you will receive a password reset link.'},
                status=status.HTTP_200_OK
            )
        
        # Generate reset token
        token = default_token_generator.make_token(user)
        
        # Build reset URL (use FRONTEND_URL from settings)
        frontend_url = getattr(settings, 'FRONTEND_URL','')
        reset_url = f"{frontend_url}/password-reset/confirm/{user.id}/{token}/"
        
        # Trigger Celery task to send email via Resend
        send_password_reset_email.delay(user.email, reset_url)
        
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
            user = User.objects.get(id=uid)
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid token or user ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate token
        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        return Response(
            {'message': 'Password has been reset successfully'},
            status=status.HTTP_200_OK
        )