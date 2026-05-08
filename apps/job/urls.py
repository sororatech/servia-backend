from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'jobs', views.JobViewSet, basename='job')

urlpatterns = [
    path('departments/categories/', views.department_categories, name='department-categories'),
    path('', include(router.urls)),
]