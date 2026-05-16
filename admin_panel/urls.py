from django.urls import path
from .views import AdminStatsView

urlpatterns = [
    path('stats/', AdminStatsView.as_view(), name='admin-stats'),
]