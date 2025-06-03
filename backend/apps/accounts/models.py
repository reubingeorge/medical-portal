"""
Models for the accounts app.

This module defines the data models for the accounts application, including:
- User roles (patient, clinician, administrator)
- Language preferences
- Custom User model (extending Django's AbstractUser)
- Authentication and security related models (email verification, login attempts, password resets)

The User model serves as the core model for authentication and authorization, while other
models provide support for various account-related features.
"""
from typing import Optional, List, Any
from datetime import datetime, timedelta

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .managers import UserManager


class Role(models.Model):
    """
    User roles within the system.

    This model defines the different roles a user can have in the medical portal.
    Each role has specific permissions and access levels:

    - PATIENT: Regular users who can view their own medical records and documents
    - CLINICIAN: Medical professionals who can manage patients and their records
    - ADMINISTRATOR: System administrators with full access to all features

    Attributes:
        name (CharField): The role identifier, chosen from predefined choices
            (PATIENT, CLINICIAN, ADMINISTRATOR)
    """
    # Role type constants
    PATIENT = 'patient'
    CLINICIAN = 'clinician'
    ADMINISTRATOR = 'administrator'

    # Role choices for the name field
    ROLE_CHOICES = [
        (PATIENT, _('Patient')),
        (CLINICIAN, _('Clinician')),
        (ADMINISTRATOR, _('Administrator')),
    ]

    name = models.CharField(
        max_length=50,
        unique=True,
        choices=ROLE_CHOICES,
        verbose_name=_('Role name')
    )

    class Meta:
        """
        Metadata for the Role model.
        """
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')

    def __str__(self) -> str:
        """
        Return a string representation of the role.

        Returns:
            str: The human-readable name of the role
        """
        return self.get_name_display()


class Language(models.Model):
    """
    Languages supported by the system.

    This model represents the languages available for user selection in the system.
    Each language is identified by its ISO 639-1 language code (e.g., 'en' for English).

    The supported languages are:
    - English (en)
    - Spanish (es)
    - French (fr)
    - Arabic (ar)
    - Hindi (hi)

    These language preferences affect the user interface language and localization settings.

    Attributes:
        code (CharField): The ISO 639-1 language code for the language
    """
    # Language code constants
    ENGLISH = 'en'
    SPANISH = 'es'
    FRENCH = 'fr'
    ARABIC = 'ar'
    HINDI = 'hi'

    # Language choices for the code field
    LANGUAGE_CHOICES = [
        (ENGLISH, _('English')),
        (SPANISH, _('Spanish')),
        (FRENCH, _('French')),
        (ARABIC, _('Arabic')),
        (HINDI, _('Hindi')),
    ]

    code = models.CharField(
        max_length=10,
        unique=True,
        choices=LANGUAGE_CHOICES,
        verbose_name=_('Language code')
    )

    class Meta:
        """
        Metadata for the Language model.
        """
        verbose_name = _('Language')
        verbose_name_plural = _('Languages')

    def __str__(self) -> str:
        """
        Return a string representation of the language.

        Returns:
            str: The human-readable name of the language
        """
        return self.get_code_display()


class User(AbstractUser):
    """
    Custom user model for the medical portal.

    This model extends Django's AbstractUser to add medical portal specific fields
    and functionality. It uses email as the primary identifier for authentication
    instead of username, and adds profile information like date of birth, gender,
    phone number, as well as medical-specific fields like role and assigned doctor.

    The model supports three main roles:
    - Patient: Regular users who can view their own medical information
    - Clinician: Medical professionals who can view and manage patient records
    - Administrator: System administrators with full access to the portal

    Attributes:
        email (EmailField): The user's email address, used as the login identifier
        date_of_birth (DateField): The user's date of birth
        gender (CharField): The user's gender (male, female, other)
        phone_number (CharField): The user's contact phone number
        numerical_identifier (CharField): An optional identifier (e.g., patient ID)
        role (ForeignKey): The user's role in the system (patient, clinician, administrator)
        language (ForeignKey): The user's preferred language for the interface
        assigned_doctor (ForeignKey): For patients, their assigned clinician
        specialty_name (CharField): For clinicians, their medical specialty
        is_email_verified (BooleanField): Whether the user's email has been verified
        email_verification_token (CharField): Token for email verification process
    """
    # Gender constants and choices
    GENDER_MALE = 'male'
    GENDER_FEMALE = 'female'
    GENDER_OTHER = 'other'

    GENDER_CHOICES = [
        (GENDER_MALE, _('Male')),
        (GENDER_FEMALE, _('Female')),
        (GENDER_OTHER, _('Other')),
    ]

    # User profile fields
    email = models.EmailField(
        unique=True,
        verbose_name=_('Email address')
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Date of birth')
    )
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default=GENDER_OTHER,
        verbose_name=_('Gender')
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Phone number')
    )
    numerical_identifier = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_('Numerical identifier')
    )

    # Role and relationship fields
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('Role')
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('Preferred language'),
        limit_choices_to={'code': 'en'},  # Default to English
        default=Language.ENGLISH
    )
    assigned_doctor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patients',
        limit_choices_to={'role__name': 'clinician'},
        verbose_name=_('Assigned doctor')
    )
    specialty_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Specialty')
    )

    # Authentication and verification fields
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name=_('Email verified')
    )
    email_verification_token = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Email verification token')
    )

    # Use custom user manager
    objects = UserManager()

    # Set email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        """
        Metadata for the User model.
        """
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self) -> str:
        """
        Return a string representation of the user.

        Returns:
            str: The user's full name and email address
        """
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self) -> str:
        """
        Return the first_name plus the last_name, with a space in between.

        Returns:
            str: The user's full name
        """
        return f"{self.first_name} {self.last_name}"

    def get_role_display(self) -> str:
        """
        Return the human-readable role.

        Returns:
            str: The user's role name or 'No role assigned' if no role
        """
        if self.role:
            return str(self.role)
        return _('No role assigned')

    @property
    def age(self) -> int:
        """
        Calculate the user's age based on date of birth.

        Returns:
            int: The user's age in years or 0 if date of birth is not set
        """
        if not self.date_of_birth:
            return 0

        today = timezone.now().date()
        born = self.date_of_birth

        # Calculate age
        age = today.year - born.year

        # Adjust age if birthday hasn't occurred yet this year
        if (today.month, today.day) < (born.month, born.day):
            age -= 1

        return age

    def is_patient(self) -> bool:
        """
        Check if the user is a patient.

        Returns:
            bool: True if the user has the patient role, False otherwise
        """
        return self.role and self.role.name == Role.PATIENT

    def is_clinician(self) -> bool:
        """
        Check if the user is a clinician.

        Returns:
            bool: True if the user has the clinician role, False otherwise
        """
        return self.role and self.role.name == Role.CLINICIAN

    def is_administrator(self) -> bool:
        """
        Check if the user is an administrator.

        Returns:
            bool: True if the user has the administrator role, False otherwise
        """
        return self.role and self.role.name == Role.ADMINISTRATOR


class EmailVerification(models.Model):
    """
    Email verification tokens.

    This model stores tokens sent to users for email verification purposes.
    Each token has an expiration time and tracks whether it has been used.

    The email verification process works as follows:
    1. When a user registers, a verification token is generated and stored
    2. An email with the token is sent to the user's email address
    3. When the user clicks the verification link, the token is validated
    4. If valid, the user's email is marked as verified

    Attributes:
        user (ForeignKey): The user this verification token belongs to
        token (CharField): The unique verification token
        created_at (DateTimeField): When the token was created
        expires_at (DateTimeField): When the token expires
        verified (BooleanField): Whether the token has been used for verification
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_verifications',
        verbose_name=_('User')
    )
    token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Verification token')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    expires_at = models.DateTimeField(
        verbose_name=_('Expires at')
    )
    verified = models.BooleanField(
        default=False,
        verbose_name=_('Verified')
    )

    class Meta:
        """
        Metadata for the EmailVerification model.
        """
        verbose_name = _('Email verification')
        verbose_name_plural = _('Email verifications')

    def __str__(self) -> str:
        """
        Return a string representation of the email verification.

        Returns:
            str: A description of the verification with the associated email
        """
        return f"Verification for {self.user.email}"

    def is_valid(self) -> bool:
        """
        Check if the verification token is still valid.

        A token is valid if:
        1. It has not been used (verified=False)
        2. It has not expired (current time < expires_at)

        Returns:
            bool: True if the token is valid, False otherwise
        """
        # Note: We import timezone here to avoid circular imports
        return not self.verified and timezone.now() < self.expires_at


class LoginAttempt(models.Model):
    """
    Track login attempts for additional security.

    This model logs all login attempts to the system, both successful and failed.
    It records details about each attempt, including the email address used, the
    IP address of the request, the user agent, and whether the attempt was successful.

    This information is valuable for:
    1. Security monitoring and detecting brute force attacks
    2. Analyzing login patterns and potential unauthorized access attempts
    3. Providing audit trails for security investigations
    4. Implementing account lockout mechanisms after multiple failed attempts

    Attributes:
        email (EmailField): The email address used in the login attempt
        ip_address (GenericIPAddressField): The IP address from which the attempt originated
        user_agent (CharField): The browser/client user agent string
        successful (BooleanField): Whether the login attempt was successful
        timestamp (DateTimeField): When the login attempt occurred
    """
    email = models.EmailField(
        verbose_name=_('Email address')
    )
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP address')
    )
    user_agent = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('User agent')
    )
    successful = models.BooleanField(
        default=False,
        verbose_name=_('Successful')
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Timestamp')
    )

    class Meta:
        """
        Metadata for the LoginAttempt model.
        """
        verbose_name = _('Login attempt')
        verbose_name_plural = _('Login attempts')
        ordering = ['-timestamp']  # Most recent attempts first

    def __str__(self) -> str:
        """
        Return a string representation of the login attempt.

        Returns:
            str: A description of the attempt with status, email and timestamp
        """
        status = _('successful') if self.successful else _('failed')
        return f"{status} login for {self.email} at {self.timestamp}"


class PasswordReset(models.Model):
    """
    Password reset tokens for user account recovery.

    This model stores password reset tokens that are generated when users request
    to reset their password after forgetting it. Each token is associated with a
    specific user and has an expiration time for security purposes.

    The password reset process works as follows:
    1. User requests a password reset by providing their email address
    2. A reset token is generated and stored in this model
    3. An email with the token is sent to the user's email address
    4. When the user clicks the reset link, the token is validated
    5. If valid, the user can set a new password and the token is marked as used

    Attributes:
        user (ForeignKey): The user this reset token belongs to
        token (CharField): The unique reset token
        created_at (DateTimeField): When the token was created
        expires_at (DateTimeField): When the token expires (typically 24-48 hours after creation)
        used (BooleanField): Whether the token has been used for a password reset
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_resets',
        verbose_name=_('User')
    )
    token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Reset token')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    expires_at = models.DateTimeField(
        verbose_name=_('Expires at')
    )
    used = models.BooleanField(
        default=False,
        verbose_name=_('Used')
    )

    class Meta:
        """
        Metadata for the PasswordReset model.
        """
        verbose_name = _('Password reset')
        verbose_name_plural = _('Password resets')

    def __str__(self) -> str:
        """
        Return a string representation of the password reset.

        Returns:
            str: A description of the reset with the associated user's email
        """
        return f"Password reset for {self.user.email}"

    def is_valid(self) -> bool:
        """
        Check if the password reset token is still valid.

        A token is valid if:
        1. It has not been used (used=False)
        2. It has not expired (current time < expires_at)

        Returns:
            bool: True if the token is valid, False otherwise
        """
        from django.utils import timezone
        return not self.used and timezone.now() < self.expires_at