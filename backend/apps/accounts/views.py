"""
Views for the accounts app.

This module contains view functions for user account management including:
- User registration and email verification
- Authentication (login, logout)
- Password reset
- User profile management
- Role-based access control and dashboard redirection
- Administrative user management

Each view handles specific aspects of user account lifecycle, from creation
to authentication to profile management, with appropriate permissions and
security measures applied.
"""
import uuid
import logging
from datetime import timedelta
from typing import Optional, Dict, Any, Union, Tuple

# Django imports - organized by category
# Core Django
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.conf import settings
from django.db.models import Q

# Authentication
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator

# Security
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie, csrf_exempt

# Utilities
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

# Third-party imports
from rest_framework_simplejwt.tokens import RefreshToken

# Local imports
from .models import Role, EmailVerification, PasswordReset, LoginAttempt, Language
from .forms import (
    SignupForm, LoginForm, PasswordResetForm,
    PasswordResetConfirmForm, ProfileUpdateForm
)
from .decorators import role_required

# Initialize logger and User model
User = get_user_model()
logger = logging.getLogger(__name__)


def get_client_ip(request) -> str:
    """
    Extract the client IP address from the request.

    This function safely extracts the client's IP address from various headers,
    handling cases where the request might be coming through proxies or load balancers.

    Args:
        request: The Django HttpRequest object

    Returns:
        str: The client's IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # The HTTP_X_FORWARDED_FOR header can contain a comma-separated list of IPs
        # The first one is the original client IP
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        # Fallback to REMOTE_ADDR if HTTP_X_FORWARDED_FOR is not present
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


@csrf_protect
def signup_view(request) -> HttpResponse:
    """
    User registration view.

    Handles the user registration process with email verification. This view:
    1. Displays the signup form to unauthenticated users
    2. Processes form submission and creates a new user account
    3. Generates and sends an email verification token
    4. Sets language preferences if provided
    5. Handles error cases with appropriate responses

    Args:
        request: The Django HttpRequest object

    Returns:
        HttpResponse: The appropriate response based on the request type and result
    """
    # Redirect authenticated users to their dashboard
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            # Create user with email verification pending
            user = form.save(commit=False)
            user.is_active = True
            user.is_email_verified = False
            user.save()

            # Create verification token and record
            token = _create_email_verification(user)

            # Send verification email
            verification_url = request.build_absolute_uri(
                reverse('accounts:verify_email', kwargs={'token': token})
            )

            email_sent = _send_verification_email(user, verification_url)

            if email_sent:
                # Log verification URL in debug mode
                if settings.DEBUG:
                    logger.info(f"Verification URL: {verification_url}")

                # Set language preference and return success response
                return _create_signup_success_response(request, form)
            else:
                # Handle email sending failure
                user.delete()  # Clean up user if email fails
                error_message = _('Failed to send verification email. Please try again later.')
                return _create_signup_error_response(request, form, error_message)
    else:
        # GET request - display empty form
        form = SignupForm()

    # Render appropriate template based on request type
    context = {'form': form}

    if request.htmx:
        return render(request, 'partials/signup_form.html', context)

    return render(request, 'auth/signup.html', context)


def _create_email_verification(user) -> str:
    """
    Create an email verification record for a user.

    Args:
        user: The User object to create verification for

    Returns:
        str: The generated verification token
    """
    # Generate verification token
    token = uuid.uuid4().hex

    # Create and save email verification with 24-hour expiration
    expires_at = timezone.now() + timedelta(days=1)
    EmailVerification.objects.create(
        user=user,
        token=token,
        expires_at=expires_at
    )

    return token


def _send_verification_email(user, verification_url) -> bool:
    """
    Send a verification email to the user.

    Args:
        user: The User object to send verification to
        verification_url: The URL for email verification

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = _('Verify your email address')
    message = _(
        'Please click the link below to verify your email address: \n{}'
    ).format(verification_url)

    html_message = render_to_string('email/verify_email.html', {
        'verification_url': verification_url,
        'user': user,
    })

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        return False


def _create_signup_success_response(request, form) -> HttpResponse:
    """
    Create a success response for signup with language preferences.

    Args:
        request: The Django HttpRequest object
        form: The validated form with user data

    Returns:
        HttpResponse: Response with appropriate template and cookies
    """
    # Prepare the context for the template
    context = {'debug': settings.DEBUG}

    # Create response with appropriate template
    if request.htmx:
        response = render(request, 'partials/signup_success.html', context)
    else:
        response = render(request, 'auth/signup_success.html', context)

    # Set language cookie if language code is provided
    language_code = form.cleaned_data.get('language_code')
    if language_code:
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            language_code,
            max_age=365 * 24 * 60 * 60  # 1 year
        )

    return response


def _create_signup_error_response(request, form, error_message) -> HttpResponse:
    """
    Create an error response for signup failures.

    Args:
        request: The Django HttpRequest object
        form: The form to add errors to
        error_message: The error message to display

    Returns:
        HttpResponse: Response with error details
    """
    if request.htmx:
        try:
            return render(request, 'partials/signup_error.html', {
                'message': error_message
            }, status=500)
        except Exception as template_error:
            logger.error(f"Failed to render error template: {template_error}")
            # Fallback to plain text response if template rendering fails
            return HttpResponse(error_message, status=500)

    form.add_error(None, error_message)
    return render(request, 'auth/signup.html', {'form': form})


def login_view(request) -> HttpResponse:
    """
    User login view.

    Handles user authentication through:
    1. Displaying login form to unauthenticated users
    2. Processing login credentials and authenticating users
    3. Setting appropriate cookies (JWT token, language preference)
    4. Tracking login attempts for security monitoring
    5. Redirecting users based on their roles
    6. Providing CSRF-handling alternatives when needed

    Args:
        request: The Django HttpRequest object

    Returns:
        HttpResponse: The appropriate response based on authentication result
    """
    # Redirect already authenticated users
    if request.user.is_authenticated:
        return _create_no_cache_redirect('accounts:dashboard_redirect')

    # Alternative simple login form for CSRF issues
    if request.GET.get('simple_form', False):
        return _create_direct_login_response(request)

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)

        # Prepare login attempt tracking data
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        email = request.POST.get('username', '')

        if form.is_valid():
            # Authentication successful
            user = form.get_user()
            login(request, user)

            # Record successful login attempt
            _record_login_attempt(email, ip_address, user_agent, successful=True)

            # Create and configure response
            response = _create_successful_login_response(request, user, form)
            return response
        else:
            # Check for CSRF errors and provide alternative
            if _has_csrf_error(form):
                return redirect(f"{reverse('accounts:login')}?simple_form=true")

            # Record failed login attempt
            _record_login_attempt(email, ip_address, user_agent, successful=False)
    else:
        # GET request - show login form
        form = LoginForm()

    # Render login form with appropriate template
    context = {'form': form}

    if request.htmx:
        response = render(request, 'partials/login_form.html', context)
    else:
        response = render(request, 'auth/login.html', context)

    # Add security headers
    _add_no_cache_headers(response)
    return response


def _create_no_cache_redirect(url_name: str) -> HttpResponse:
    """
    Create a redirect response with security headers.

    Args:
        url_name: The URL name to redirect to

    Returns:
        HttpResponse: Redirect response with security headers
    """
    response = redirect(url_name)
    _add_no_cache_headers(response)
    return response


def _create_direct_login_response(request) -> HttpResponse:
    """
    Create a response with the direct login page.

    Args:
        request: The Django HttpRequest object

    Returns:
        HttpResponse: Response with the direct login template and security headers
    """
    response = render(request, 'auth/direct_login.html')
    _add_no_cache_headers(response)
    return response


def _record_login_attempt(email: str, ip_address: str, user_agent: str, successful: bool) -> None:
    """
    Record a login attempt for security tracking.

    Args:
        email: The email address used in the login attempt
        ip_address: The IP address of the request
        user_agent: The user agent string from the request
        successful: Whether the login was successful
    """
    LoginAttempt.objects.create(
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
        successful=successful
    )


def _create_successful_login_response(request, user, form) -> HttpResponse:
    """
    Create response for successful login with appropriate cookies and settings.

    Args:
        request: The Django HttpRequest object
        user: The authenticated User object
        form: The validated login form

    Returns:
        HttpResponse: Redirect to dashboard with JWT and preference cookies
    """
    # Create response redirecting to appropriate dashboard
    response = redirect('accounts:dashboard_redirect')

    # Generate and set JWT token
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    response.set_cookie(
        'access_token',
        access_token,
        max_age=3600 * 24,  # 1 day
        httponly=True,
        secure=not settings.DEBUG,  # Secure in production
        samesite='Lax'
    )

    # Set language preference cookie if available
    if user.language:
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            user.language.code,
            max_age=365 * 24 * 60 * 60  # 1 year
        )

    # Set session expiry based on "remember me" choice
    if form.cleaned_data.get('remember_me'):
        request.session.set_expiry(3600 * 24 * 14)  # 2 weeks
    else:
        request.session.set_expiry(0)  # Until browser closes

    # Add security headers
    _add_no_cache_headers(response)
    return response


def _has_csrf_error(form) -> bool:
    """
    Check if form has CSRF-related errors.

    Args:
        form: The form to check for errors

    Returns:
        bool: True if CSRF errors are found, False otherwise
    """
    for error in form.non_field_errors():
        if "CSRF" in str(error):
            return True
    return False


def _add_no_cache_headers(response) -> None:
    """
    Add security headers to prevent response caching.

    Args:
        response: The HttpResponse object to modify
    """
    response['Cache-Control'] = 'no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'


@login_required
def logout_view(request) -> HttpResponse:
    """
    User logout view.

    Logs out the authenticated user and cleans up their session.
    This view removes authentication tokens, cookies, and session data.

    Args:
        request: The Django HttpRequest object

    Returns:
        HttpResponse: Redirect to login page
    """
    # Log out the user
    logout(request)

    # Create redirect response and clean up cookies
    response = redirect('accounts:login')
    response.delete_cookie('access_token')
    _add_no_cache_headers(response)

    return response


def verify_email(request, token: str) -> HttpResponse:
    """
    Email verification view.

    Validates an email verification token and updates the user's verification status.
    The flow handles various cases:
    1. Token is valid and unused: Mark email as verified
    2. Token is already used: Show already verified message
    3. Token is expired: Show expired token message

    Args:
        request: The Django HttpRequest object
        token: The verification token to validate

    Returns:
        HttpResponse: The appropriate verification result template
    """
    # Get the verification record or return 404
    verification = get_object_or_404(EmailVerification, token=token)

    # Handle already verified case
    if verification.verified:
        return render(request, 'auth/verification_already_done.html')

    # Handle expired token case
    if not verification.is_valid():
        return render(request, 'auth/verification_expired.html')

    # Valid token - mark as verified
    verification.verified = True
    verification.save()

    # Update user's email verification status
    user = verification.user
    user.is_email_verified = True
    user.save(update_fields=['is_email_verified'])

    return render(request, 'auth/verification_success.html')


@login_required
def dashboard_redirect(request) -> HttpResponse:
    """
    Redirect to the appropriate dashboard based on user role.

    This view determines which dashboard to show based on the user's role
    (patient, clinician, or administrator) and redirects accordingly.
    If the user has no valid role, they are logged out for security.

    Args:
        request: The Django HttpRequest object

    Returns:
        HttpResponse: Redirect to the appropriate role-based dashboard
    """
    user = request.user

    # Route to the correct dashboard based on role
    if user.is_administrator():
        return redirect('medical:admin_dashboard')
    elif user.is_clinician():
        return redirect('medical:doctor_dashboard')
    elif user.is_patient():
        return redirect('medical:patient_dashboard')
    else:
        # Security measure - log out users with no valid role
        logger.warning(f"User {user.id} ({user.email}) has no valid role, logging out.")
        logout(request)
        return redirect('accounts:login')


@csrf_protect
def password_reset_request(request) -> HttpResponse:
    """
    Password reset request view.

    Handles the initial password reset request where the user provides their email.
    This view:
    1. Displays a form to collect the user's email
    2. Validates the email and finds the associated user
    3. Generates a password reset token
    4. Sends a password reset email with the token
    5. Shows a confirmation page after successful request

    Args:
        request: The Django HttpRequest object

    Returns:
        HttpResponse: The appropriate response based on request state
    """
    # Redirect authenticated users to their dashboard
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')

            try:
                # Find the user with this email
                user = User.objects.get(email=email)

                # Create reset token and record
                token = _create_password_reset_token(user)

                # Send reset email
                reset_url = request.build_absolute_uri(
                    reverse('accounts:password_reset_confirm', kwargs={'token': token})
                )

                email_sent = _send_password_reset_email(user, reset_url)

                if email_sent:
                    # Log reset URL in debug mode
                    if settings.DEBUG:
                        logger.info(f"Password reset URL: {reset_url}")

                    return render(request, 'auth/password_reset_sent.html')
                else:
                    form.add_error(None, _('Failed to send reset email. Please try again later.'))
            except User.DoesNotExist:
                # For security, don't reveal that email doesn't exist
                # Just show the success page anyway
                return render(request, 'auth/password_reset_sent.html')
    else:
        form = PasswordResetForm()

    return render(request, 'auth/password_reset_request.html', {'form': form})


def _create_password_reset_token(user) -> str:
    """
    Create a password reset token for a user.

    Args:
        user: The User object to create reset token for

    Returns:
        str: The generated reset token
    """
    # Generate unique token
    token = uuid.uuid4().hex

    # Create and save password reset record with 24-hour expiration
    expires_at = timezone.now() + timedelta(hours=24)
    PasswordReset.objects.create(
        user=user,
        token=token,
        expires_at=expires_at
    )

    return token


def _send_password_reset_email(user, reset_url) -> bool:
    """
    Send a password reset email to a user.

    Args:
        user: The User object to send the reset email to
        reset_url: The URL for password reset

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = _('Reset your password')
    message = _(
        'Please click the link below to reset your password: \n{}'
    ).format(reset_url)

    html_message = render_to_string('email/password_reset.html', {
        'reset_url': reset_url,
        'user': user,
    })

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        return False


@csrf_protect
def password_reset_confirm(request, token: str) -> HttpResponse:
    """
    Password reset confirmation view.

    Handles the password reset process after a user clicks the reset link:
    1. Validates the reset token for expiration and previous use
    2. Allows the user to set a new password via a form
    3. Updates the password and marks the token as used
    4. Shows appropriate responses for various token states

    Args:
        request: The Django HttpRequest object
        token: The password reset token to validate

    Returns:
        HttpResponse: The appropriate template based on token status and request
    """
    # Get the reset record or return 404
    reset = get_object_or_404(PasswordReset, token=token)

    # Handle already used token
    if reset.used:
        return render(request, 'auth/password_reset_already_used.html')

    # Handle expired token
    if not reset.is_valid():
        return render(request, 'auth/password_reset_expired.html')

    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            # Update password and token status
            _complete_password_reset(reset, form.cleaned_data.get('password1'))
            return render(request, 'auth/password_reset_complete.html')
    else:
        form = PasswordResetConfirmForm()

    return render(request, 'auth/password_reset_confirm.html', {'form': form})


def _complete_password_reset(reset, new_password) -> None:
    """
    Complete the password reset process.

    Updates the user's password and marks the reset token as used.

    Args:
        reset: The PasswordReset object to process
        new_password: The new password to set
    """
    # Update password
    user = reset.user
    user.set_password(new_password)
    user.save(update_fields=['password'])

    # Mark reset as used
    reset.used = True
    reset.save(update_fields=['used'])


@login_required
def profile_view(request) -> HttpResponse:
    """
    User profile view.

    Handles viewing and updating a user's profile information:
    1. Displays the user's current profile information
    2. Processes profile update submissions
    3. Handles specialty information for clinicians (with DB/session fallback)
    4. Returns appropriate responses based on HTMX usage

    Args:
        request: The Django HttpRequest object

    Returns:
        HttpResponse: The appropriate response based on request type
    """
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)

        if form.is_valid():
            # Process and save profile updates
            return _process_profile_update(request, form)
    else:
        # GET request - prepare form with current data
        form = ProfileUpdateForm(instance=request.user)
        _populate_specialty_from_session(request, form)

    # Prepare context with effective specialty information
    context = {
        'form': form,
        'effective_specialty': _get_effective_specialty(request)
    }

    # Return appropriate template based on request type
    if request.htmx:
        return render(request, 'partials/profile_form.html', context)

    return render(request, 'auth/profile.html', context)


def _process_profile_update(request, form) -> HttpResponse:
    """
    Process a profile update form submission.

    Handles saving form data, specialty handling, and appropriate response.

    Args:
        request: The Django HttpRequest object
        form: The validated form with profile data

    Returns:
        HttpResponse: The appropriate response based on request type
    """
    # Extract user instance from form
    user = form.save(commit=False)

    # Handle specialty field with graceful fallback
    if 'specialty_name' in form.cleaned_data and request.user.is_clinician():
        specialty = form.cleaned_data['specialty_name']
        try:
            # Try to save to database field
            user.specialty_name = specialty
            user.save()
        except Exception as e:
            # Fallback to session storage if field doesn't exist
            logger.warning(f"Could not save specialty to database: {e}")
            if specialty:
                request.session['specialty'] = specialty
            user.save(update_fields=['first_name', 'last_name', 'phone_number', 'gender', 'language'])
    else:
        user.save()

    # Return appropriate response based on request type
    if request.htmx:
        return HttpResponse(
            _("Profile updated successfully"),
            headers={"HX-Trigger": "profileUpdated"}
        )

    return redirect('accounts:profile')


def _populate_specialty_from_session(request, form) -> None:
    """
    Populate the specialty field from session for clinicians.

    Args:
        request: The Django HttpRequest object
        form: The form to populate
    """
    if request.user.is_clinician() and not request.user.specialty_name:
        specialty = request.session.get('specialty')
        if specialty and hasattr(form, 'fields') and 'specialty_name' in form.fields:
            form.fields['specialty_name'].initial = specialty


def _get_effective_specialty(request) -> Optional[str]:
    """
    Get the effective specialty for a clinician user.

    Tries to get from database first, then falls back to session.

    Args:
        request: The Django HttpRequest object

    Returns:
        Optional[str]: The specialty name or None if not applicable
    """
    if request.user.is_clinician():
        return request.user.specialty_name or request.session.get('specialty')
    return None


@login_required
@csrf_protect
def update_language(request) -> HttpResponse:
    """
    Update user's preferred language and set language for the current session.

    This view handles:
    1. Changing a user's language preference in their profile
    2. Activating the selected language for the current session
    3. Setting appropriate language cookies
    4. Redirecting to the appropriate page after update

    Args:
        request: The Django HttpRequest object

    Returns:
        HttpResponse: Redirect to appropriate page after update
    """
    if request.method == 'POST':
        language_code = request.POST.get('language')
        next_url = request.POST.get('next', request.META.get('HTTP_REFERER', 'accounts:profile'))

        if language_code:
            language_updated = _set_user_language(request, language_code)

            if language_updated:
                # Create response with language cookie
                from django.utils import translation
                translation.activate(language_code)

                response = redirect(next_url)
                response.set_cookie(
                    settings.LANGUAGE_COOKIE_NAME,
                    language_code,
                    max_age=365 * 24 * 60 * 60  # 1 year
                )

                return response

    # If language update failed, redirect back to profile
    return redirect('accounts:profile')


def _set_user_language(request, language_code: str) -> bool:
    """
    Set a user's language preference.

    Args:
        request: The Django HttpRequest object
        language_code: The language code to set

    Returns:
        bool: Whether the language update succeeded
    """
    try:
        # Get language from database or create if it doesn't exist
        language, created = Language.objects.get_or_create(
            code=language_code,
            defaults={'code': language_code}
        )

        # Update user's preferred language
        user = request.user
        user.language = language
        user.save(update_fields=['language'])

        return True
    except Exception as e:
        logger.error(f"Failed to update language preference: {e}")
        return False


@login_required
@role_required(['administrator'])
def user_list_view(request) -> HttpResponse:
    """
    List all users (admin only).

    This view provides a paginated, filterable list of all users in the system.
    It supports:
    1. Text search by name and email
    2. Role-based filtering
    3. HTMX partial rendering for dynamic updates

    Args:
        request: The Django HttpRequest object

    Returns:
        HttpResponse: Rendered user list with applicable filters
    """
    # Get filter parameters from request
    search_query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')

    # Get user queryset with necessary related objects
    users = _get_filtered_users(search_query, role_filter)

    # Get all roles for filter dropdown
    roles = Role.objects.all()

    # Prepare template context
    context = {
        'users': users,
        'roles': roles,
        'search_query': search_query,
        'role_filter': role_filter
    }

    # Return appropriate template based on request type
    if request.htmx:
        return render(request, 'partials/user_list.html', context)

    return render(request, 'admin/user_list.html', context)


def _get_filtered_users(search_query: str, role_filter: str) -> 'QuerySet':
    """
    Get filtered user queryset based on search and role filters.

    Args:
        search_query: Text to search for in user names and email
        role_filter: Role name to filter by

    Returns:
        QuerySet: Filtered User queryset with related objects
    """
    # Start with all users and include related objects
    users = User.objects.all().select_related('role', 'language')

    # Apply text search filter if provided
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Apply role filter if provided
    if role_filter:
        users = users.filter(role__name=role_filter)

    return users


@login_required
@csrf_protect
@role_required(['administrator'])
def user_edit_view(request, user_id: int) -> HttpResponse:
    """
    Edit user details (admin only).

    Allows administrators to modify user profiles, including:
    1. Basic profile information (name, email, etc.)
    2. Language preferences
    3. Role assignments
    4. Other user-specific settings

    Args:
        request: The Django HttpRequest object
        user_id: The ID of the user to edit

    Returns:
        HttpResponse: The appropriate response based on request type
    """
    # Get the user to edit with related data
    user_to_edit = get_object_or_404(User.objects.select_related('language'), id=user_id)

    # Log current language for debugging
    _log_user_language(user_to_edit)

    if request.method == 'POST':
        # Handle language selection and user updates
        _handle_language_selection(request, user_to_edit)

        # Process form data
        form = ProfileUpdateForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            # Save the form
            user = form.save(commit=False)
            user.save()

            # Return appropriate response based on request type
            if request.htmx:
                return HttpResponse(
                    _("User updated successfully"),
                    headers={"HX-Trigger": "userUpdated"}
                )
            return redirect('accounts:user_list')
    else:
        # Prepare form for GET request
        form = ProfileUpdateForm(instance=user_to_edit)

    # Prepare context for template
    context = {
        'form': form,
        'user_to_edit': user_to_edit,
        'language_choices': Language.LANGUAGE_CHOICES,
    }

    # Return appropriate template based on request type
    if request.htmx:
        return render(request, 'partials/user_edit_form.html', context)

    return render(request, 'admin/user_edit.html', context)


def _log_user_language(user) -> None:
    """
    Log a user's current language preference for debugging.

    Args:
        user: The User object to log language for
    """
    if user.language:
        logger.debug(f"User {user.id} has language: {user.language.code}")
    else:
        logger.debug(f"User {user.id} has no language preference")


def _handle_language_selection(request, user) -> None:
    """
    Process language selection from form data.

    Args:
        request: The Django HttpRequest object
        user: The User object to update
    """
    language_code = request.POST.get('language')
    if language_code:
        try:
            # Try to get existing language
            language = Language.objects.get(code=language_code)
            user.language = language
        except Language.DoesNotExist:
            # Create new language if valid
            if language_code in dict(Language.LANGUAGE_CHOICES):
                language = Language.objects.create(code=language_code)
                user.language = language
    elif 'language' in request.POST and not language_code:
        # Clear language preference if "No preference" selected
        user.language = None


@login_required
@csrf_protect
@role_required(['administrator'])
def assign_doctor_view(request, patient_id: int) -> HttpResponse:
    """
    Assign a doctor to a patient (admin only).

    This view allows administrators to:
    1. View a patient's current assigned doctor
    2. Select a new doctor from available clinicians
    3. Update the patient's assignment

    Args:
        request: The Django HttpRequest object
        patient_id: The ID of the patient to assign a doctor to

    Returns:
        HttpResponse: The appropriate response based on request type
    """
    # Get the patient or return 404
    patient = get_object_or_404(User, id=patient_id, role__name=Role.PATIENT)

    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')

        if doctor_id:
            # Assign the selected doctor
            _assign_doctor_to_patient(patient, doctor_id)

            # Return appropriate response based on request type
            if request.htmx:
                return HttpResponse(
                    _("Doctor assigned successfully"),
                    headers={"HX-Trigger": "doctorAssigned"}
                )

        return redirect('accounts:user_list')

    # Get all available doctors for selection
    doctors = User.objects.filter(role__name=Role.CLINICIAN)

    # Prepare context and render template
    context = {'patient': patient, 'doctors': doctors}

    if request.htmx:
        return render(request, 'partials/assign_doctor_form.html', context)

    return render(request, 'admin/assign_doctor.html', context)


def _assign_doctor_to_patient(patient, doctor_id: int) -> None:
    """
    Assign a doctor to a patient.

    Args:
        patient: The patient User object
        doctor_id: The ID of the doctor to assign
    """
    doctor = get_object_or_404(User, id=doctor_id, role__name=Role.CLINICIAN)
    patient.assigned_doctor = doctor
    patient.save(update_fields=['assigned_doctor'])