"""
Custom exception handler for consistent API error responses.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    
    Returns:
        Response with standardized error format:
        {
            "error": "Error message",
            "detail": "Detailed error information",
            "status_code": 400
        }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # Log the exception
    view = context.get('view')
    request = context.get('request')
    
    if response is not None:
        # Standardize the error response format
        error_data = {
            'error': str(exc),
            'status_code': response.status_code
        }
        
        # Add detail if available
        if hasattr(response, 'data'):
            if isinstance(response.data, dict):
                error_data['detail'] = response.data
            else:
                error_data['detail'] = {'message': response.data}
        
        response.data = error_data
        
        # Log error
        logger.error(
            f"API Error: {error_data['error']} | "
            f"View: {view.__class__.__name__} | "
            f"Path: {request.path if request else 'N/A'}"
        )
    else:
        # Handle non-DRF exceptions
        error_data = {
            'error': 'Internal server error',
            'detail': str(exc),
            'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
        }
        
        response = Response(
            error_data,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
        # Log critical error
        logger.critical(
            f"Unhandled Exception: {str(exc)} | "
            f"View: {view.__class__.__name__ if view else 'N/A'} | "
            f"Path: {request.path if request else 'N/A'}",
            exc_info=True
        )
    
    return response