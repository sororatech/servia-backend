from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
import redis
from django.db import OperationalError

def custom_exception_handler(exc, context):
    """Return friendly messages instead of technical errors"""
    
    if isinstance(exc, redis.exceptions.ConnectionError):
        return Response(
            {'error': 'Service temporarily unavailable. Please try again later.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    if isinstance(exc, OperationalError):
        return Response(
            {'error': 'Unable to process your request. Please try again later.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    return exception_handler(exc, context)