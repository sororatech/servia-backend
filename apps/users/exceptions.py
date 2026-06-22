from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
import redis
from django.db import OperationalError
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """Return friendly messages instead of technical errors"""
    
    if isinstance(exc, redis.exceptions.ConnectionError):
        logger.error(f"Redis connection error: {exc}", exc_info=True)
        return Response(
            {'error': 'Service temporarily unavailable. Please try again later.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    if isinstance(exc, OperationalError):
        logger.error(f"Database operational error: {exc}", exc_info=True)
        return Response(
            {'error': 'Unable to process your request. Please try again later.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    return exception_handler(exc, context)