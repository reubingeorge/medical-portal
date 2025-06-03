"""
Admin configuration for the audit app.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import json

from .models import AuditLog, AuditLogArchive
from .utils import format_changes_for_display


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin configuration for AuditLog model.
    """
    list_display = (
        'timestamp', 'user_display', 'action_display',
        'model_name', 'object_id', 'ip_address'
    )
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('user__email', 'user__username', 'model_name', 'object_id', 'ip_address')
    readonly_fields = (
        'id', 'user', 'action', 'model_name', 'object_id',
        'formatted_changes', 'timestamp', 'ip_address', 'user_agent'
    )
    date_hierarchy = 'timestamp'
    fieldsets = (
        (None, {
            'fields': ('id', 'timestamp', 'user', 'action', 'model_name', 'object_id')
        }),
        (_('Changes'), {
            'fields': ('formatted_changes',),
            'classes': ('collapse',)
        }),
        (_('Request Details'), {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """Disable manual creation of audit logs."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing of audit logs."""
        return False

    def user_display(self, obj):
        """Format user display in list view."""
        if obj.user:
            return f"{obj.user.get_full_name()} ({obj.user.email})"
        return _("System or Anonymous")

    user_display.short_description = _("User")

    def action_display(self, obj):
        """Format action display with colored badge."""
        action_colors = {
            AuditLog.CREATE: 'success',
            AuditLog.UPDATE: 'primary',
            AuditLog.DELETE: 'danger',
            AuditLog.LOGIN: 'info',
            AuditLog.LOGOUT: 'secondary'
        }

        color = action_colors.get(obj.action, 'secondary')
        badge_class = f"badge badge-{color}"

        return format_html(
            '<span class="{}">{}</span>',
            badge_class,
            obj.get_action_display()
        )

    action_display.short_description = _("Action")

    def formatted_changes(self, obj):
        """
        Format changes as a readable HTML display.
        """
        if not obj.changes:
            return _("No changes recorded")

        try:
            # Convert from pretty format to an actual Python dictionary
            changes_dict = obj.changes

            # Format for display
            formatted = format_changes_for_display(changes_dict)

            # Convert newlines to HTML breaks for display
            html_formatted = formatted.replace('\n', '<br>').replace('  • ', '&nbsp;&nbsp;• ')

            return format_html(
                '<div style="max-height: 300px; overflow-y: auto;">{}</div>'
                '<div style="margin-top: 10px;"><strong>Raw JSON:</strong><br>'
                '<pre style="max-height: 200px; overflow-y: auto;">{}</pre></div>',
                html_formatted,
                json.dumps(changes_dict, indent=2)
            )
        except Exception as e:
            return format_html(
                '<div class="error">Error formatting changes: {}</div>'
                '<pre>{}</pre>',
                str(e),
                obj.changes
            )

    formatted_changes.short_description = _("Changes")


@admin.register(AuditLogArchive)
class AuditLogArchiveAdmin(admin.ModelAdmin):
    """
    Admin configuration for AuditLogArchive model.
    """
    list_display = (
        'timestamp', 'user_email', 'action_display',
        'model_name', 'object_id', 'ip_address'
    )
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('user_email', 'model_name', 'object_id', 'ip_address')
    readonly_fields = (
        'id', 'user_id', 'user_email', 'action', 'model_name', 'object_id',
        'formatted_changes', 'timestamp', 'ip_address', 'user_agent'
    )
    date_hierarchy = 'timestamp'
    fieldsets = (
        (None, {
            'fields': ('id', 'timestamp', 'user_id', 'user_email', 'action', 'model_name', 'object_id')
        }),
        (_('Changes'), {
            'fields': ('formatted_changes',),
            'classes': ('collapse',)
        }),
        (_('Request Details'), {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """Disable manual creation of audit log archives."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing of audit log archives."""
        return False

    def action_display(self, obj):
        """Format action display with colored badge."""
        action_colors = {
            AuditLogArchive.CREATE: 'success',
            AuditLogArchive.UPDATE: 'primary',
            AuditLogArchive.DELETE: 'danger',
            AuditLogArchive.LOGIN: 'info',
            AuditLogArchive.LOGOUT: 'secondary'
        }

        color = action_colors.get(obj.action, 'secondary')
        badge_class = f"badge badge-{color}"

        return format_html(
            '<span class="{}">{}</span>',
            badge_class,
            obj.get_action_display()
        )

    action_display.short_description = _("Action")

    def formatted_changes(self, obj):
        """
        Format changes as a readable HTML display.
        """
        if not obj.changes:
            return _("No changes recorded")

        try:
            # Convert from pretty format to an actual Python dictionary
            changes_dict = obj.changes

            # Format for display
            formatted = format_changes_for_display(changes_dict)

            # Convert newlines to HTML breaks for display
            html_formatted = formatted.replace('\n', '<br>').replace('  • ', '&nbsp;&nbsp;• ')

            return format_html(
                '<div style="max-height: 300px; overflow-y: auto;">{}</div>'
                '<div style="margin-top: 10px;"><strong>Raw JSON:</strong><br>'
                '<pre style="max-height: 200px; overflow-y: auto;">{}</pre></div>',
                html_formatted,
                json.dumps(changes_dict, indent=2)
            )
        except Exception as e:
            return format_html(
                '<div class="error">Error formatting changes: {}</div>'
                '<pre>{}</pre>',
                str(e),
                obj.changes
            )

    formatted_changes.short_description = _("Changes")