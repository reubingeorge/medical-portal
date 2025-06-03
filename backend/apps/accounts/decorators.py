"""
Custom decorators for the accounts app.
"""
from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from django.utils.translation import gettext_lazy as _


def role_required(allowed_roles=None):
    """
    Decorator to restrict access based on user roles.

    Args:
        allowed_roles (list): List of role names allowed to access the view.
                             Example: ['administrator', 'clinician']

    Returns:
        function: Decorated view function.
    """
    if allowed_roles is None:
        allowed_roles = []

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return redirect('login')

            # Check if user has a role
            if not request.user.role:
                return HttpResponseForbidden(_('You do not have permission to access this page.'))

            # Check if user's role is in the allowed roles
            if request.user.role.name not in allowed_roles:
                # Redirect to appropriate dashboard based on role
                if request.user.is_administrator():
                    return redirect('admin_dashboard')
                elif request.user.is_clinician():
                    return redirect('doctor_dashboard')
                elif request.user.is_patient():
                    return redirect('patient_dashboard')
                else:
                    return HttpResponseForbidden(_('You do not have permission to access this page.'))

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def verified_email_required(view_func):
    """
    Decorator to ensure user has verified their email.

    Returns:
        function: Decorated view function.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return redirect('login')

        # Check if email is verified
        if not request.user.is_email_verified:
            return redirect('email_verification_required')

        return view_func(request, *args, **kwargs)

    return wrapper