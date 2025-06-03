"""
Admin configuration for the accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import (
    User, Role, Language, EmailVerification,
    LoginAttempt, PasswordReset
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Admin configuration for the User model.
    """
    list_display = (
        'email', 'username', 'first_name', 'last_name',
        'role', 'language', 'is_active', 'is_email_verified',
        'date_joined'
    )
    list_filter = (
        'is_active', 'is_email_verified', 'role', 'language',
        'date_joined', 'gender'
    )
    search_fields = (
        'email', 'username', 'first_name', 'last_name',
        'numerical_identifier'
    )
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {
            'fields': (
                'first_name', 'last_name', 'date_of_birth',
                'gender', 'phone_number'
            )
        }),
        (_('System info'), {
            'fields': (
                'numerical_identifier', 'role', 'language',
                'assigned_doctor'
            )
        }),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_email_verified',
                'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            )
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'password1', 'password2',
                'first_name', 'last_name', 'date_of_birth',
                'gender', 'phone_number', 'role', 'language',
                'is_active', 'is_email_verified'
            ),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Role model.
    """
    list_display = ('name', 'get_users_count')
    search_fields = ('name',)

    def get_users_count(self, obj):
        """
        Return the number of users with this role.
        """
        return obj.users.count()

    get_users_count.short_description = _('Users')


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Language model.
    """
    list_display = ('code', 'get_users_count')
    search_fields = ('code',)

    def get_users_count(self, obj):
        """
        Return the number of users with this language.
        """
        return obj.users.count()

    get_users_count.short_description = _('Users')


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """
    Admin configuration for the EmailVerification model.
    """
    list_display = ('user', 'created_at', 'expires_at', 'verified')
    list_filter = ('verified', 'created_at')
    search_fields = ('user__email', 'user__username', 'token')
    readonly_fields = ('token', 'created_at')
    ordering = ('-created_at',)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """
    Admin configuration for the LoginAttempt model.
    """
    list_display = ('email', 'ip_address', 'successful', 'timestamp')
    list_filter = ('successful', 'timestamp')
    search_fields = ('email', 'ip_address')
    readonly_fields = ('email', 'ip_address', 'user_agent', 'successful', 'timestamp')
    ordering = ('-timestamp',)


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    """
    Admin configuration for the PasswordReset model.
    """
    list_display = ('user', 'created_at', 'expires_at', 'used')
    list_filter = ('used', 'created_at')
    search_fields = ('user__email', 'user__username', 'token')
    readonly_fields = ('token', 'created_at')
    ordering = ('-created_at',)