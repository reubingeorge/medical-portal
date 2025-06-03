"""
Models for the audit app.

This module defines the data models for the audit and security logging system, including:
- AuditLog for tracking database changes and user actions
- AuditLogArchive for storing older audit records for long-term retention

The audit system captures and stores detailed information about all significant
actions in the application, such as data creation, updates, deletions, and
authentication events. This provides a comprehensive audit trail for security,
compliance, and debugging purposes.
"""
import uuid
from typing import Dict, Any, Optional, List, Tuple

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    """
    Model to track all database changes and user actions for audit purposes.

    This model captures detailed information about significant actions in the application,
    providing a comprehensive audit trail for security monitoring, compliance reporting,
    and troubleshooting. It records who performed an action, what action was taken,
    what data was affected, and contextual information like IP address.

    Each log entry includes:
    - The user who performed the action (if authenticated)
    - The type of action (create, update, delete, login, logout)
    - The affected model and object identifier
    - Detailed changes made (for updates)
    - Timestamp and request context (IP, user agent)

    The logs are optimized for efficient querying with multiple indexes.

    Attributes:
        id (UUIDField): Primary key for the log entry
        user (ForeignKey): The user who performed the action
        action (CharField): The type of action performed
        model_name (CharField): The model/entity that was affected
        object_id (CharField): The ID of the affected object
        changes (JSONField): Detailed before/after data for updates
        timestamp (DateTimeField): When the action occurred
        ip_address (GenericIPAddressField): IP address of the request
        user_agent (TextField): Browser/client user agent
    """
    # Audit log action constants
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'

    ACTION_CHOICES = [
        (CREATE, _('Create')),
        (UPDATE, _('Update')),
        (DELETE, _('Delete')),
        (LOGIN, _('Login')),
        (LOGOUT, _('Logout')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,  # Preserve audit logs even if user is deleted
        related_name='audit_logs',
        verbose_name=_('User')
    )
    action = models.CharField(
        max_length=10,
        choices=ACTION_CHOICES,
        verbose_name=_('Action')
    )
    model_name = models.CharField(
        max_length=255,
        verbose_name=_('Model name')
    )
    object_id = models.CharField(
        max_length=255,
        verbose_name=_('Object ID')
    )
    changes = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Changes')
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Timestamp')
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP address')
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('User agent')
    )

    class Meta:
        """
        Metadata for the AuditLog model, including indexes for efficient queries.
        """
        verbose_name = _('Audit log')
        verbose_name_plural = _('Audit logs')
        ordering = ['-timestamp']  # Most recent logs first
        indexes = [
            models.Index(fields=['model_name']),
            models.Index(fields=['action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['user']),
            models.Index(fields=['object_id']),
        ]

    def __str__(self) -> str:
        """
        Return a string representation of the audit log entry.

        Returns:
            str: Description with action, model, and timestamp
        """
        return f"{self.get_action_display()} - {self.model_name} - {self.timestamp}"

    @property
    def user_info(self) -> str:
        """
        Get user information for display purposes.

        Returns:
            str: User's full name and email, or 'System' if no user
        """
        if self.user:
            return f"{self.user.get_full_name()} ({self.user.email})"
        return "System"

    def get_changes_summary(self) -> str:
        """
        Get a human-readable summary of changes.

        Returns:
            str: Summary of the changes or appropriate message
        """
        if not self.changes:
            return "No detailed changes recorded"

        if self.action == self.CREATE:
            return "New record created"

        if self.action == self.DELETE:
            return "Record deleted"

        # For updates, show field changes
        if self.action == self.UPDATE and isinstance(self.changes, dict):
            fields_changed = list(self.changes.keys())
            return f"Updated fields: {', '.join(fields_changed)}"

        return "Changes recorded"


class AuditLogArchive(models.Model):
    """
    Archive of audit logs for long-term storage and compliance.

    This model mirrors the AuditLog structure but is designed for storing older
    logs that have been archived from the main AuditLog table. It supports
    regulatory compliance requirements for long-term data retention while
    helping maintain performance of the active audit log table.

    Key differences from AuditLog:
    1. Uses string fields for user information instead of foreign keys
    2. Does not use auto_now_add for timestamp (preserves original time)
    3. May be stored in a different database or tablespace for efficient storage

    The archiving process typically moves logs older than a certain threshold
    (e.g., 90 days) from AuditLog to this table, ensuring that historical audit
    data remains accessible for compliance reporting without impacting performance.

    Attributes:
        id (UUIDField): Primary key for the log entry (preserved from original)
        user_id (CharField): The ID of the user who performed the action
        user_email (EmailField): The email of the user for reference
        action (CharField): The type of action performed
        model_name (CharField): The model/entity that was affected
        object_id (CharField): The ID of the affected object
        changes (JSONField): Detailed before/after data for updates
        timestamp (DateTimeField): When the action occurred (preserved from original)
        ip_address (GenericIPAddressField): IP address of the request
        user_agent (TextField): Browser/client user agent
    """
    # Audit log action constants (duplicated to avoid dependencies)
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'

    ACTION_CHOICES = [
        (CREATE, _('Create')),
        (UPDATE, _('Update')),
        (DELETE, _('Delete')),
        (LOGIN, _('Login')),
        (LOGOUT, _('Logout')),
    ]

    id = models.UUIDField(
        primary_key=True,
        editable=False,
        verbose_name=_('ID')
    )
    user_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('User ID')
    )
    user_email = models.EmailField(
        null=True,
        blank=True,
        verbose_name=_('User email')
    )
    action = models.CharField(
        max_length=10,
        choices=ACTION_CHOICES,
        verbose_name=_('Action')
    )
    model_name = models.CharField(
        max_length=255,
        verbose_name=_('Model name')
    )
    object_id = models.CharField(
        max_length=255,
        verbose_name=_('Object ID')
    )
    changes = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Changes')
    )
    timestamp = models.DateTimeField(
        verbose_name=_('Timestamp')
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP address')
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('User agent')
    )

    class Meta:
        """
        Metadata for the AuditLogArchive model, including indexes for efficient queries.
        """
        verbose_name = _('Audit log archive')
        verbose_name_plural = _('Audit log archives')
        ordering = ['-timestamp']  # Most recent logs first
        indexes = [
            models.Index(fields=['model_name']),
            models.Index(fields=['action']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['user_id']),
            models.Index(fields=['user_email']),
            models.Index(fields=['object_id']),
        ]

    def __str__(self) -> str:
        """
        Return a string representation of the archived audit log entry.

        Returns:
            str: Description with action, model, and timestamp
        """
        return f"{self.get_action_display()} - {self.model_name} - {self.timestamp}"

    @property
    def user_info(self) -> str:
        """
        Get user information for display purposes.

        Returns:
            str: User email or ID, or 'System' if no user information
        """
        if self.user_email:
            return self.user_email
        if self.user_id:
            return f"User ID: {self.user_id}"
        return "System"

    @classmethod
    def from_audit_log(cls, audit_log: AuditLog) -> 'AuditLogArchive':
        """
        Create an archive entry from an existing AuditLog entry.

        This factory method makes it easier to correctly transfer data
        from the active audit log to the archive.

        Args:
            audit_log: The source AuditLog entry to archive

        Returns:
            AuditLogArchive: A new archive entry with data from the source
        """
        user_id = str(audit_log.user.id) if audit_log.user else None
        user_email = audit_log.user.email if audit_log.user else None

        return cls(
            id=audit_log.id,
            user_id=user_id,
            user_email=user_email,
            action=audit_log.action,
            model_name=audit_log.model_name,
            object_id=audit_log.object_id,
            changes=audit_log.changes,
            timestamp=audit_log.timestamp,
            ip_address=audit_log.ip_address,
            user_agent=audit_log.user_agent
        )