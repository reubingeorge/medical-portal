"""
Initial migration for the audit app.
"""
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('CREATE', 'Create'), ('UPDATE', 'Update'), ('DELETE', 'Delete'), ('LOGIN', 'Login'), ('LOGOUT', 'Logout')], max_length=10, verbose_name='Action')),
                ('model_name', models.CharField(max_length=255, verbose_name='Model name')),
                ('object_id', models.CharField(max_length=255, verbose_name='Object ID')),
                ('changes', models.JSONField(blank=True, null=True, verbose_name='Changes')),
                ('timestamp', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Timestamp')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP address')),
                ('user_agent', models.TextField(blank=True, null=True, verbose_name='User agent')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Audit log',
                'verbose_name_plural': 'Audit logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='AuditLogArchive',
            fields=[
                ('id', models.UUIDField(editable=False, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(blank=True, max_length=255, null=True, verbose_name='User ID')),
                ('user_email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='User email')),
                ('action', models.CharField(choices=[('CREATE', 'Create'), ('UPDATE', 'Update'), ('DELETE', 'Delete'), ('LOGIN', 'Login'), ('LOGOUT', 'Logout')], max_length=10, verbose_name='Action')),
                ('model_name', models.CharField(max_length=255, verbose_name='Model name')),
                ('object_id', models.CharField(max_length=255, verbose_name='Object ID')),
                ('changes', models.JSONField(blank=True, null=True, verbose_name='Changes')),
                ('timestamp', models.DateTimeField(verbose_name='Timestamp')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP address')),
                ('user_agent', models.TextField(blank=True, null=True, verbose_name='User agent')),
            ],
            options={
                'verbose_name': 'Audit log archive',
                'verbose_name_plural': 'Audit log archives',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlogarchive',
            index=models.Index(fields=['model_name'], name='audit_audit_model_n_ec11a5_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlogarchive',
            index=models.Index(fields=['action'], name='audit_audit_action_c51515_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlogarchive',
            index=models.Index(fields=['timestamp'], name='audit_audit_timesta_1b7686_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlogarchive',
            index=models.Index(fields=['user_id'], name='audit_audit_user_id_9b9a36_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlogarchive',
            index=models.Index(fields=['user_email'], name='audit_audit_user_em_d4c3b7_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlogarchive',
            index=models.Index(fields=['object_id'], name='audit_audit_object__6db1d1_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['model_name'], name='audit_audit_model_n_d78a34_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action'], name='audit_audit_action_6a83da_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['timestamp'], name='audit_audit_timesta_5be65c_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['user'], name='audit_audit_user_id_2d811d_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['object_id'], name='audit_audit_object__9d7cc9_idx'),
        ),
    ]