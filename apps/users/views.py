from rest_framework import viewsets, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from django.db import IntegrityError
from .models import CandidateUser, RecruiterUser
from .serializers import CandidateUserSerializer, RecruiterUserSerializer

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