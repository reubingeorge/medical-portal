"""
Signal handlers for the audit app.
"""
import json
import logging
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.serializers.json import DjangoJSONEncoder
from django.apps import apps
from django.contrib.auth import user_logged_in, user_logged_out
from django.conf import settings
from django.db import connection
from datetime import datetime

from .models import AuditLog
from .middleware import get_current_user, get_client_ip, get_user_agent
from .utils import get_changed_fields

logger = logging.getLogger(__name__)


def is_audit_log_table_ready():
    """
    Check if the AuditLog table exists in the database.
    This helps prevent errors during migrations.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_auditlog'"
            )
            return bool(cursor.fetchone())
    except Exception as e:
        logger.error(f"Error checking if audit_auditlog table exists: {e}")
        return False


def json_serialize(obj):
    """
    Custom JSON serializer for objects not serializable by default.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


@receiver(pre_save)
def log_pre_save(sender, instance, **kwargs):
    """
    Store the original state of an object before it is saved.
    """
    # Skip audit logs themselves to prevent infinite recursion
    if sender == AuditLog:
        return

    # Skip models that should not be audited
    excluded_models = getattr(settings, 'AUDIT_EXCLUDED_MODELS', [])
    if sender._meta.label in excluded_models:
        return
        
    # Skip if the audit log table doesn't exist yet (during migrations)
    if not is_audit_log_table_ready():
        return
        
    # Skip if we're already in a transaction that had an error
    from django.db import transaction
    if transaction.get_connection().needs_rollback:
        return

    # Store the original state in the instance for post_save comparison
    if instance.pk:
        try:
            # Use a separate connection to avoid transaction issues
            old_instance = sender.objects.using('default').get(pk=instance.pk)
            instance._original_state = {
                field.name: getattr(old_instance, field.name)
                for field in old_instance._meta.fields
            }
        except (sender.DoesNotExist, Exception) as e:
            # Log the error but don't break the operation
            logger.warning(f"Couldn't fetch original state for {sender.__name__} (pk={instance.pk}): {e}")
            instance._original_state = {}
    else:
        instance._original_state = {}


@receiver(post_save)
def log_changes(sender, instance, created, **kwargs):
    """
    Log object creation and modifications.
    """
    # Skip audit logs themselves to prevent infinite recursion
    if sender == AuditLog:
        return

    # Skip models that should not be audited
    excluded_models = getattr(settings, 'AUDIT_EXCLUDED_MODELS', [])
    if sender._meta.label in excluded_models:
        return
        
    # Skip if the audit log table doesn't exist yet (during migrations)
    if not is_audit_log_table_ready():
        return
        
    # Skip if we're in a transaction that had an error
    from django.db import transaction
    if transaction.get_connection().needs_rollback:
        return
        
    # Skip if we're already handling an audit log
    if getattr(instance, '_is_creating_audit_log', False):
        return

    try:
        # Determine action (create or update)
        action = AuditLog.CREATE if created else AuditLog.UPDATE

        # Get current state
        current_state = {
            field.name: getattr(instance, field.name)
            for field in instance._meta.fields
        }

        # For updates, get the changed fields
        changes = None
        if not created and hasattr(instance, '_original_state'):
            changed_fields = get_changed_fields(instance._original_state, current_state)
            if not changed_fields:  # Skip if no changes
                return

            changes = {
                'original': {k: instance._original_state.get(k) for k in changed_fields},
                'new': {k: current_state.get(k) for k in changed_fields}
            }
        else:
            # For creates, record the entire object
            changes = {'new': current_state}
            
        # Prepare JSON data
        json_data = json.loads(json.dumps(changes, default=json_serialize, cls=DjangoJSONEncoder))
            
        # Create audit log entry using a direct database query to avoid triggering signals again
        # Set a flag that we're creating an audit log
        try:
            # Try to get the user from middleware context
            current_user = get_current_user()
            
            # If instance is a User model, we can use it directly
            if sender._meta.label == 'accounts.User' and instance.is_authenticated:
                current_user = instance
                
            # Log debug info
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Creating audit log with user: {current_user}")
            
            audit_log = AuditLog(
                user=current_user,
                action=action,
                model_name=sender._meta.label,
                object_id=str(instance.pk),
                changes=json_data,
                ip_address=get_client_ip(),
                user_agent=get_user_agent()
            )
            audit_log._is_creating_audit_log = True
            audit_log.save()
        except Exception as e:
            logger.error(f"Error saving audit log record: {e}", exc_info=True)
            
    except Exception as e:
        # Log error but don't prevent the save operation
        logger.error(f"Error creating audit log: {e}", exc_info=True)


@receiver(post_delete)
def log_deletion(sender, instance, **kwargs):
    """
    Log object deletion.
    """
    # Skip audit logs themselves to prevent infinite recursion
    if sender == AuditLog:
        return

    # Skip models that should not be audited
    excluded_models = getattr(settings, 'AUDIT_EXCLUDED_MODELS', [])
    if sender._meta.label in excluded_models:
        return
        
    # Skip if the audit log table doesn't exist yet (during migrations)
    if not is_audit_log_table_ready():
        return
        
    # Skip if we're in a transaction that had an error
    from django.db import transaction
    if transaction.get_connection().needs_rollback:
        return
        
    # Skip if we're already handling an audit log
    if getattr(instance, '_is_creating_audit_log', False):
        return

    try:
        # Get object state before deletion
        final_state = {
            field.name: getattr(instance, field.name)
            for field in instance._meta.fields
        }
        
        # Prepare JSON data
        json_data = json.loads(json.dumps({'deleted': final_state}, default=json_serialize, cls=DjangoJSONEncoder))

        # Create audit log entry
        try:
            audit_log = AuditLog(
                user=get_current_user(),
                action=AuditLog.DELETE,
                model_name=sender._meta.label,
                object_id=str(instance.pk),
                changes=json_data,
                ip_address=get_client_ip(),
                user_agent=get_user_agent()
            )
            audit_log._is_creating_audit_log = True
            audit_log.save()
        except Exception as e:
            logger.error(f"Error saving deletion audit log: {e}", exc_info=True)
            
    except Exception as e:
        # Log error but don't prevent the delete operation
        logger.error(f"Error creating deletion audit log: {e}", exc_info=True)


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Log user login events.
    """
    # Skip if the audit log table doesn't exist yet (during migrations)
    if not is_audit_log_table_ready():
        return
        
    try:
        AuditLog.objects.create(
            user=user,
            action=AuditLog.LOGIN,
            model_name=user._meta.label,
            object_id=str(user.pk),
            changes=None,
            ip_address=get_client_ip() or (request.META.get('REMOTE_ADDR') if request else None),
            user_agent=get_user_agent() or (request.META.get('HTTP_USER_AGENT') if request else None)
        )
    except Exception as e:
        logger.error(f"Error creating login audit log: {e}", exc_info=True)


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """
    Log user logout events.
    """
    if not user:
        return
        
    # Skip if the audit log table doesn't exist yet (during migrations)
    if not is_audit_log_table_ready():
        return

    try:
        AuditLog.objects.create(
            user=user,
            action=AuditLog.LOGOUT,
            model_name=user._meta.label,
            object_id=str(user.pk),
            changes=None,
            ip_address=get_client_ip() or (request.META.get('REMOTE_ADDR') if request else None),
            user_agent=get_user_agent() or (request.META.get('HTTP_USER_AGENT') if request else None)
        )
    except Exception as e:
        logger.error(f"Error creating logout audit log: {e}", exc_info=True)