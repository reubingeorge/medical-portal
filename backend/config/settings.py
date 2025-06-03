"""
Django settings for medical portal project.
"""
import os
from datetime import timedelta
from pathlib import Path
from django.utils.translation import gettext_lazy as _

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-development-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'axes',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'django_htmx',

    # Local apps
    'apps.accounts',
    'apps.medical',
    'apps.chat',
    'apps.audit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Internationalization
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.accounts.middleware.JWTAuthenticationMiddleware',  # JWT middleware
    'apps.accounts.middleware.UserLanguageMiddleware',  # User language preference middleware
    'apps.chat.middleware.SecureTokenMiddleware',  # Security middleware
    'apps.chat.middleware.ChatSecurityMiddleware',  # Chat security
    'django_htmx.middleware.HtmxMiddleware',  # HTMX middleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.AuditMiddleware',  # Audit trail middleware
    'allauth.account.middleware.AccountMiddleware',  # AllAuth middleware
    'axes.middleware.AxesMiddleware',  # Login throttling - must be last
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / '../frontend/templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',  # For translations
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'medical_portal'),
        'USER': os.environ.get('POSTGRES_USER', 'medical_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'medical_password'),
        'HOST': 'db',  # Service name in docker-compose
        'PORT': '5432',
        'OPTIONS': {
            'isolation_level': 3,  # READ COMMITTED isolation level
            'connect_timeout': 10,
        },
    }
}

# Redis cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.environ.get('REDIS_HOST', 'redis')}:{os.environ.get('REDIS_PORT', '6379')}/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 10,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Password Hashing
# https://docs.djangoproject.com/en/4.2/topics/auth/passwords/#using-argon2-with-django
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

LANGUAGES = [
    ('en', _('English')),
    ('es', _('Spanish')),
    ('fr', _('French')),
    ('ar', _('Arabic')),
    ('hi', _('Hindi')),
]

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Store language selection in session
LANGUAGE_SESSION_KEY = 'django_language'
LANGUAGE_COOKIE_NAME = 'django_language'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / '../frontend/static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User model
AUTH_USER_MODEL = 'accounts.User'

# Authentication settings
AUTHENTICATION_BACKENDS = [
    # Django ModelBackend is the default that lets you login with username and password
    'django.contrib.auth.backends.ModelBackend',
    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
    # AxesBackend should be the last backend in the AUTHENTICATION_BACKENDS list
    'axes.backends.AxesBackend',
]

# JWT Authentication settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
}

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# django-allauth settings
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1
ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/300s',
}

# Email settings
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')

# Django-axes settings
AXES_FAILURE_LIMIT = 5  # Number of login attempts before lockout
AXES_LOCKOUT_TIME = 30  # Minutes to lockout after failure limit
AXES_COOLOFF_TIME = 60  # Minutes before login failures are forgotten

# Login and redirect settings
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/accounts/redirect/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Security settings for production
if os.environ.get('DJANGO_ENV') == 'production':
    # HTTPS settings
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True

    # Cookie settings
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True

    # Content security policy
    CSP_DEFAULT_SRC = ("'self'",)
    CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com")
    CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "'unsafe-eval'", "cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com")
    CSP_IMG_SRC = ("'self'", "data:")
    CSP_FONT_SRC = ("'self'", "cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com")
    CSP_CONNECT_SRC = ("'self'",)

# OpenAI API configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Vector search connection string
# Using psycopg (v3) instead of psycopg2 for langchain_postgres compatibility
PGVECTOR_CONNECTION_STRING = os.environ.get(
    'PGVECTOR_CONNECTION_STRING',
    'postgresql+psycopg://medical_user:medical_password@db:5432/medical_portal'
)

# Whitenoise for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# CORS settings
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080",
] if DEBUG else [
    "https://medical-portal.example.com",
]

# CSRF settings
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript access for debugging
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080",
]

# X-Frame-Options settings
X_FRAME_OPTIONS = 'SAMEORIGIN'  # Allow iframes from the same origin

# Disable CSRF for development environment
if DEBUG:
    CSRF_USE_SESSIONS = True  # Store CSRF token in session instead of cookie
    CSRF_FAILURE_VIEW = 'django.views.csrf.csrf_failure'

# Test settings
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
TEST_DISCOVER_PATTERN = "test*.py"
TEST_DISCOVER_TOP_LEVEL = BASE_DIR

# Audit settings
# Models that should be excluded from audit logging to prevent transaction issues
AUDIT_EXCLUDED_MODELS = [
    'accounts.User',  # Exclude User model changes from being audited to prevent transaction issues
    'admin.LogEntry',  # Exclude Django admin log entries
    'sessions.Session',  # Exclude session changes
    'contenttypes.ContentType',  # Exclude content type changes
]