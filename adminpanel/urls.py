from django.urls import path
from .views import (
    AdminStatsView,
    RecruiterListView,
    RecruiterCreateView,
    RecruiterToggleStatusView,
    LoginView,
    RegisterRecruiterView,
    RecruiterUpdateView,
    RecruiterDeleteView,
    CandidateListView,
    CandidateDetailView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterRecruiterView.as_view(), name="register"),

    path("stats/", AdminStatsView.as_view(), name="stats"),

    path("recruiters/", RecruiterListView.as_view(), name="recruiter-list"),
    path("recruiters/create/", RecruiterCreateView.as_view(), name="recruiter-create"),

    path(
        "recruiters/<uuid:pk>/toggle/",
        RecruiterToggleStatusView.as_view(),
        name="recruiter-toggle"
    ),

    path(
        "recruiters/<uuid:pk>/",
        RecruiterUpdateView.as_view(),
        name="recruiter-update"
    ),

    path(
        "recruiters/<uuid:pk>/delete/",
        RecruiterDeleteView.as_view(),
        name="recruiter-delete"
    ),

    path("candidates/", CandidateListView.as_view(), name="candidate-list"),

    path(
        "candidates/<uuid:pk>/",
        CandidateDetailView.as_view(),
        name="candidate-detail"
    ),
]