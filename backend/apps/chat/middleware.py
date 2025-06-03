"""
Security middleware for chat application
"""
import logging
import re
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from urllib.parse import urlparse, parse_qs, urlencode

logger = logging.getLogger(__name__)


class SecureTokenMiddleware:
    """
    Middleware to prevent sensitive tokens from appearing in URLs
    """
    
    SENSITIVE_PARAMS = [
        'csrfmiddlewaretoken',
        'csrf_token',
        'token',
        'sessionid',
        'api_key',
        'password',
        'secret'
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if the request has sensitive parameters in the URL
        if request.method == 'GET':
            query_params = request.GET.copy()
            has_sensitive = False
            
            for param in self.SENSITIVE_PARAMS:
                if param in query_params:
                    has_sensitive = True
                    query_params.pop(param)
                    logger.warning(
                        f"Removed sensitive parameter '{param}' from URL: {request.path}"
                    )
            
            # If sensitive params were found, redirect to clean URL
            if has_sensitive:
                # Build clean URL
                clean_query = urlencode(query_params)
                clean_path = request.path
                if clean_query:
                    clean_path += '?' + clean_query
                
                # Log security incident
                logger.error(
                    f"SECURITY: Sensitive parameters in URL from {request.META.get('REMOTE_ADDR')}"
                )
                
                # For chat interface, return error instead of redirect
                if request.path.startswith('/chat/'):
                    return HttpResponseBadRequest(
                        "Security Error: Invalid request parameters. "
                        "Please refresh the page and try again."
                    )
                
                # For other paths, redirect to clean URL
                return HttpResponseRedirect(clean_path)
        
        response = self.get_response(request)
        
        # Add security headers
        response['X-Frame-Options'] = 'DENY'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response


class ChatSecurityMiddleware:
    """
    Additional security measures for chat functionality
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Ensure chat messages are only sent via POST
        if request.path == reverse('chat:chat_message') and request.method != 'POST':
            logger.warning(
                f"Attempted to access chat message endpoint with {request.method}"
            )
            return HttpResponseBadRequest(
                "Chat messages must be sent via POST request"
            )
        
        response = self.get_response(request)
        
        # For chat pages, add additional security headers
        if request.path.startswith('/chat/'):
            # Prevent caching of sensitive chat data
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response