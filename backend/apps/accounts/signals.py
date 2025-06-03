"""
Signal handlers for the accounts app.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .models import User, Role, Language


@receiver(pre_save, sender=User)
def ensure_user_has_username(sender, instance, **kwargs):
    """
    Ensure that user has a username if email is provided.
    """
    if not instance.username and instance.email:
        instance.username = instance.email


@receiver(post_save, sender=User)
def ensure_default_role_and_language(sender, instance, created, **kwargs):
    """
    Ensure that new users have a default role (patient) and language (English).
    """
    # Check if this is a recursion prevention key
    if getattr(instance, '_in_ensure_defaults', False):
        return
        
    needs_update = False
    update_fields = {}
    
    # Only run for newly created users without a role
    if created and not instance.role:
        # Get or create patient role
        patient_role, _ = Role.objects.get_or_create(name=Role.PATIENT)
        update_fields['role'] = patient_role
        needs_update = True
    
    # Ensure user has a language preference set (default to English)
    if not instance.language:
        # Get or create the English language
        english_language, _ = Language.objects.get_or_create(
            code=Language.ENGLISH,
            defaults={'code': Language.ENGLISH}
        )
        update_fields['language'] = english_language
        needs_update = True
    
    # Apply the updates if needed
    if needs_update:
        try:
            # Set recursion prevention flag
            instance._in_ensure_defaults = True
            
            # Update using a direct update query to avoid triggering signals again
            User.objects.filter(pk=instance.pk).update(**update_fields)
            
            # Update the instance in memory
            instance.refresh_from_db()
        finally:
            # Clear recursion prevention flag
            instance._in_ensure_defaults = False


@receiver(post_save, sender=User)
def create_required_roles_and_languages(sender, instance, **kwargs):
    """
    Ensure that all required roles and languages exist in the database.
    But only run this once at startup or first user creation to avoid
    transaction issues.
    """
    # Check if this has been run already in this process
    if getattr(create_required_roles_and_languages, '_has_run', False):
        return
        
    try:
        # Create roles if they don't exist
        Role.objects.get_or_create(name=Role.PATIENT)
        Role.objects.get_or_create(name=Role.CLINICIAN)
        Role.objects.get_or_create(name=Role.ADMINISTRATOR)
        
        # Create languages if they don't exist
        Language.objects.get_or_create(code=Language.ENGLISH)
        Language.objects.get_or_create(code=Language.SPANISH)
        Language.objects.get_or_create(code=Language.FRENCH)
        Language.objects.get_or_create(code=Language.ARABIC)
        Language.objects.get_or_create(code=Language.HINDI)
        
        # Mark as run
        create_required_roles_and_languages._has_run = True
    except Exception:
        # If there's an error (e.g., during migrations), don't mark as run
        pass