from django.contrib.auth import authenticate, get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token

from apps.users.models import RecruiterUser

User = get_user_model()


# -------------------------
# LOGIN
# -------------------------
class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(username=email, password=password)

        if user is None:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        })


# -------------------------
# REGISTER (Recruiter)
# -------------------------
class RegisterRecruiterView(APIView):
    permission_classes = []

    def post(self, request):
        data = request.data

        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        password = data.get("password")
        department = data.get("department")
        role = data.get("role")

        if not email or not password:
            return Response(
                {"error": "Email and password required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=email).exists():
            return Response(
                {"error": "User already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # create user
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # create recruiter profile
        recruiter = RecruiterUser.objects.create(
            user=user,
            department=department,
            role=role
        )

        return Response({
            "message": "Recruiter created successfully",
            "user_id": user.id,
            "recruiter_id": recruiter.id
        }, status=status.HTTP_201_CREATED)