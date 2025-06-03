from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _


def get_user_language(request):
    """
    Get the language for the current user.
    
    Priority:
    1. User profile setting (if authenticated)
    2. Session language
    3. Accept-Language header
    4. Default language from settings
    
    Args:
        request: Django request object
    
    Returns:
        str: Language code (e.g., 'en', 'es')
    """
    # Check user profile if authenticated
    if request.user.is_authenticated:
        try:
            # Attempt to get language from user profile if available
            user_language = getattr(request.user, 'language', None)
            if user_language:
                return user_language
        except AttributeError:
            pass
    
    # Check session language
    session_language = request.session.get('django_language')
    if session_language:
        return session_language
    
    # Check Accept-Language header
    accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
    if accept_language:
        # Parse the Accept-Language header and return the highest priority language
        # that is supported by our application
        supported_languages = [lang[0] for lang in settings.LANGUAGES]
        
        for lang in accept_language.split(','):
            lang_code = lang.split(';')[0].strip()
            if lang_code in supported_languages:
                return lang_code
            # Check for language without region code (e.g., 'en' from 'en-US')
            base_lang = lang_code.split('-')[0]
            if base_lang in supported_languages:
                return base_lang
    
    # Default to the settings default language
    return settings.LANGUAGE_CODE


def set_user_language(request, language_code):
    """
    Set the language for the current user.
    
    Args:
        request: Django request object
        language_code: Language code to set (e.g., 'en', 'es')
    
    Returns:
        bool: True if language was set successfully
    """
    # Validate language code
    valid_languages = [lang[0] for lang in settings.LANGUAGES]
    if language_code not in valid_languages:
        return False
    
    # Set in session
    translation.activate(language_code)
    request.session[translation.LANGUAGE_SESSION_KEY] = language_code
    
    # Also set in user profile if authenticated
    if request.user.is_authenticated:
        try:
            # Attempt to set language in user profile if the field exists
            setattr(request.user, 'language', language_code)
            request.user.save(update_fields=['language'])
        except AttributeError:
            pass
    
    return True


def get_translated_text(text_key, default=None):
    """
    Get a translated text using Django's translation system.
    
    Args:
        text_key: Key for the translation
        default: Default value if translation is missing
    
    Returns:
        str: Translated text
    """
    translated = _(text_key)
    
    # If no translation was found and the returned value equals the input key
    if translated == text_key and default is not None:
        return default
    
    return translated