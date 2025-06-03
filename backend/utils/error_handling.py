"""
Error handling utilities.

This module provides standardized error handling utilities for use across the application.
It centralizes error handling patterns to ensure consistent error handling and logging.
"""
import logging
import traceback
import functools
from typing import Callable, Any, Dict, Optional, Union, List, Tuple

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


def log_exception(exc: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an exception with optional context information.
    
    Args:
        exc: The exception to log
        context: Optional dictionary of context information
    """
    exc_traceback = traceback.format_exc()
    
    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        logger.error(f"Exception: {str(exc)}, Context: {context_str}\n{exc_traceback}")
    else:
        logger.error(f"Exception: {str(exc)}\n{exc_traceback}")


def safe_execution(default_return: Any = None, log_error: bool = True) -> Callable:
    """
    Decorator for safely executing a function and handling exceptions.
    
    Args:
        default_return: Value to return if an exception occurs
        log_error: Whether to log the exception
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    context = {
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": str(kwargs)
                    }
                    log_exception(e, context)
                return default_return
        return wrapper
    return decorator


def handle_view_exception(request: HttpRequest, 
                          exc: Exception, 
                          error_template: str = "error.html",
                          default_message: str = None,
                          status_code: int = 500) -> HttpResponse:
    """
    Handle an exception in a view and return an appropriate response.
    
    Args:
        request: The HTTP request object
        exc: The exception that occurred
        error_template: Template to render for HTML requests
        default_message: Default error message if none is provided
        status_code: HTTP status code to return
        
    Returns:
        HttpResponse with appropriate error information
    """
    if default_message is None:
        default_message = _("An error occurred while processing your request. Please try again later.")
    
    # Log the exception
    log_exception(exc, {"request_path": request.path, "user": getattr(request, "user", None)})
    
    # Check if it's an AJAX request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            "status": "error",
            "message": str(exc) if str(exc) else default_message
        }, status=status_code)
    
    # Render error template for regular requests
    context = {
        "error_message": str(exc) if str(exc) else default_message,
        "status_code": status_code
    }
    return render(request, error_template, context, status=status_code)


def api_exception_handler(func: Callable) -> Callable:
    """
    Decorator for handling exceptions in API views and returning appropriate JSON responses.
    
    Args:
        func: The view function to decorate
        
    Returns:
        Decorated function that handles exceptions
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception as e:
            log_exception(e, {"request_path": request.path, "user": getattr(request, "user", None)})
            
            # Determine status code based on exception type
            status_code = 500
            if hasattr(e, "status_code"):
                status_code = e.status_code
                
            return JsonResponse({
                "status": "error",
                "message": str(e) if str(e) else _("An error occurred while processing your request."),
                "error_type": e.__class__.__name__
            }, status=status_code)
    
    return wrapper