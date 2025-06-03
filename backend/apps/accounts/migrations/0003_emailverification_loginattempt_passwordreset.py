"""
Migration for the EmailVerification, LoginAttempt, and PasswordReset models.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_role_language'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailVerification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=100, unique=True, verbose_name='Verification token')),
                ('created_at', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Created at')),
                ('expires_at', models.DateTimeField(verbose_name='Expires at')),
                ('verified', models.BooleanField(default=False, verbose_name='Verified')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='email_verifications', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Email verification',
                'verbose_name_plural': 'Email verifications',
            },
        ),
        migrations.CreateModel(
            name='LoginAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, verbose_name='Email address')),
                ('ip_address', models.GenericIPAddressField(verbose_name='IP address')),
                ('user_agent', models.CharField(blank=True, max_length=255, null=True, verbose_name='User agent')),
                ('successful', models.BooleanField(default=False, verbose_name='Successful')),
                ('timestamp', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Timestamp')),
            ],
            options={
                'verbose_name': 'Login attempt',
                'verbose_name_plural': 'Login attempts',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='PasswordReset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=100, unique=True, verbose_name='Reset token')),
                ('created_at', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Created at')),
                ('expires_at', models.DateTimeField(verbose_name='Expires at')),
                ('used', models.BooleanField(default=False, verbose_name='Used')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='password_resets', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Password reset',
                'verbose_name_plural': 'Password resets',
            },
        ),
    ]