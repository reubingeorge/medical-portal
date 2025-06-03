"""
Middleware for JWT authentication and user language preferences.
"""
from django.contrib.auth.models import AnonymousUser
from django.utils.translation import gettext_lazy as _
from django.utils import translation
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class JWTAuthenticationMiddleware:
    """
    Middleware that authenticates users via JWT stored in cookies.

    This provides a seamless authentication experience for clients
    that don't include Bearer tokens in headers, particularly for
    regular browser sessions.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        Process the request to attach the user if a valid JWT token is in cookies.
        """
        # Check if the user is already authenticated through session
        if not request.user.is_authenticated:
            # Try to authenticate using JWT from cookie
            token = request.COOKIES.get('access_token')
            if token:
                try:
                    # Validate the token
                    jwt_auth = JWTAuthentication()
                    validated_token = jwt_auth.get_validated_token(token)
                    user = jwt_auth.get_user(validated_token)

                    # Attach the user to the request
                    request.user = user
                except (InvalidToken, TokenError):
                    # Invalid token, keep the user as anonymous
                    request.user = AnonymousUser()

        # Continue processing the request
        response = self.get_response(request)
        return response


class UserLanguageMiddleware:
    """
    Middleware to set the language preference based on user's profile settings.
    
    This middleware checks if the user is authenticated and has a language
    preference set in their profile. If so, it activates that language for
    the current request, ensuring all translations are displayed correctly.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        """
        Process the request to set the language based on user preference.
        """
        # Check if user is authenticated and has a language preference
        if request.user.is_authenticated and hasattr(request.user, 'language') and request.user.language:
            # Activate the user's preferred language
            user_language = request.user.language.code
            translation.activate(user_language)
            
            # Store the language preference in the session
            if hasattr(request, 'session'):
                request.session[settings.LANGUAGE_SESSION_KEY] = user_language
        
        # Continue processing the request
        response = self.get_response(request)
        
        # If the user's language was set, make sure the cookie is set as well
        if request.user.is_authenticated and hasattr(request.user, 'language') and request.user.language:
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                request.user.language.code,
                max_age=365 * 24 * 60 * 60  # 1 year
            )
        
        return response