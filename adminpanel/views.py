from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.generics import (
    ListAPIView,
    CreateAPIView,
    UpdateAPIView,
    RetrieveAPIView
)
from rest_framework.authtoken.models import Token

from apps.users.models import RecruiterUser, CandidateUser
from .serializers import (
    RecruiterSerializer,
    RecruiterCreateSerializer,
    CandidateSerializer
)

User = get_user_model()


class AdminStatsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        one_week_ago = timezone.now() - timedelta(days=7)

        return Response({
            "total_recruiters": RecruiterUser.objects.count(),
            "active_recruiters": RecruiterUser.objects.filter(is_active=True).count(),
            "total_candidates": CandidateUser.objects.count(),
            "users_this_week": (
                RecruiterUser.objects.filter(created_at__gte=one_week_ago).count()
                + CandidateUser.objects.filter(created_at__gte=one_week_ago).count()
            ),
        })


class RecruiterListView(ListAPIView):
    serializer_class = RecruiterSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = RecruiterUser.objects.select_related("user")

        search = self.request.GET.get("search")
        department = self.request.GET.get("department")
        role = self.request.GET.get("role")
        status_param = self.request.GET.get("status")

        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search)
            )

        if department:
            queryset = queryset.filter(department=department)

        if role:
            queryset = queryset.filter(role=role)

        if status_param == "active":
            queryset = queryset.filter(is_active=True)

        if status_param == "disabled":
            queryset = queryset.filter(is_active=False)

        return queryset.order_by("-created_at")


class RecruiterCreateView(CreateAPIView):
    queryset = RecruiterUser.objects.all()
    serializer_class = RecruiterCreateSerializer
    permission_classes = [AllowAny]


class RecruiterToggleStatusView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request, pk):
        try:
            recruiter = RecruiterUser.objects.get(pk=pk)
        except RecruiterUser.DoesNotExist:
            return Response(
                {"error": "Recruiter not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        recruiter.is_active = not recruiter.is_active
        recruiter.save()

        return Response({
            "message": "Recruiter status updated",
            "is_active": recruiter.is_active
        })


class RecruiterUpdateView(UpdateAPIView):
    queryset = RecruiterUser.objects.all()
    serializer_class = RecruiterSerializer
    permission_classes = [AllowAny]


class RecruiterDeleteView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, pk):
        try:
            recruiter = RecruiterUser.objects.get(pk=pk)
        except RecruiterUser.DoesNotExist:
            return Response(
                {"error": "Recruiter not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        recruiter.is_active = False
        recruiter.save()

        return Response({
            "message": "Recruiter disabled successfully"
        })


class RecruiterBulkActionView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request):
        ids = request.data.get("ids", [])
        action = request.data.get("action")

        recruiters = RecruiterUser.objects.filter(id__in=ids)

        if action == "disable":
            recruiters.update(is_active=False)

        elif action == "enable":
            recruiters.update(is_active=True)

        elif action == "delete":
            recruiters.update(is_active=False)

        else:
            return Response(
                {"error": "Invalid action"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "message": f"{action} action completed successfully"
        })


class CandidateListView(ListAPIView):
    queryset = CandidateUser.objects.all().order_by("-created_at")
    serializer_class = CandidateSerializer
    permission_classes = [AllowAny]


class CandidateDetailView(RetrieveAPIView):
    queryset = CandidateUser.objects.all()
    serializer_class = CandidateSerializer
    permission_classes = [AllowAny]


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email and password required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.check_password(password):
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "user_id": user.id,
            "email": user.email
        })


class RegisterRecruiterView(CreateAPIView):
    queryset = RecruiterUser.objects.all()
    serializer_class = RecruiterCreateSerializer
    permission_classes = [AllowAny]