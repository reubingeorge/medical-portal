"""
Application configuration for the audit app.
"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    verbose_name = _('Audit Trail')

    def ready(self):
        """
        Import signal handlers when the app is ready.
        """
        import apps.audit.signals