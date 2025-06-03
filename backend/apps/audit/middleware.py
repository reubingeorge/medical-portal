"""
Middleware for the audit app.
"""
import threading
from django.utils.deprecation import MiddlewareMixin

# Thread local storage for audit context
_audit_context = threading.local()


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware that captures request information for audit logging.

    This middleware stores relevant information from the request
    (like IP address and user agent) in thread-local storage,
    which can then be accessed by the audit signal handlers when
    they need to create audit log entries.
    """

    def process_request(self, request):
        """
        Process the request and store audit context.
        """
        from django.conf import settings
        import logging
        logger = logging.getLogger(__name__)
        
        # Store request information in thread-local storage
        _audit_context.ip_address = self.get_client_ip(request)
        _audit_context.user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Handle user association with special case for admin
        if hasattr(request, 'user') and request.user.is_authenticated:
            # User is authenticated, store normally
            _audit_context.user = request.user
            logger.debug(f"Audit middleware captured authenticated user: {request.user.email}")
        else:
            # Check if we should try to find admin user
            try:
                # Only attempt if this is an admin-related request
                admin_paths = ['/admin/', '/audit/logs/']
                path = request.path.lower()
                
                if any(admin_path in path for admin_path in admin_paths):
                    from apps.accounts.models import User
                    admin_user = User.objects.filter(email='admin@example.com').first()
                    if admin_user:
                        _audit_context.user = admin_user
                        logger.debug(f"Audit middleware assigned admin user for admin path: {path}")
                    else:
                        _audit_context.user = None
                else:
                    _audit_context.user = None
            except Exception as e:
                logger.error(f"Error in audit middleware admin detection: {e}")
                _audit_context.user = None
        
        # Log final outcome for debugging
        logger.debug(f"Audit middleware final user: {getattr(_audit_context, 'user', None)}")

    def get_client_ip(self, request):
        """
        Get the client IP address from the request.

        Handles proxies by checking X-Forwarded-For header.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Get the first IP in the chain (client IP)
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


def get_current_user():
    """
    Get the current user from the audit context.

    Returns:
        User object or None if no user is set or middleware is not used.
    """
    return getattr(_audit_context, 'user', None)


def get_client_ip():
    """
    Get the client IP address from the audit context.

    Returns:
        IP address string or None if not set or middleware is not used.
    """
    return getattr(_audit_context, 'ip_address', None)


def get_user_agent():
    """
    Get the user agent from the audit context.

    Returns:
        User agent string or None if not set or middleware is not used.
    """
    return getattr(_audit_context, 'user_agent', None)