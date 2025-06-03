"""
URL Configuration for the accounts app.
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('accounts/signup/', views.signup_view, name='signup'),
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/verify-email/<str:token>/', views.verify_email, name='verify_email'),

    # Dashboard redirect
    path('accounts/redirect/', views.dashboard_redirect, name='dashboard_redirect'),

    # Password reset
    path('accounts/password-reset/', views.password_reset_request, name='password_reset'),
    path('accounts/password-reset/confirm/<str:token>/', views.password_reset_confirm, name='password_reset_confirm'),

    # User profile
    path('accounts/profile/', views.profile_view, name='profile'),
    path('accounts/update-language/', views.update_language, name='update_language'),

    # Admin user management
    path('accounts/users/', views.user_list_view, name='user_list'),
    path('accounts/users/<int:user_id>/edit/', views.user_edit_view, name='user_edit'),
    path('accounts/users/<int:patient_id>/assign-doctor/', views.assign_doctor_view, name='assign_doctor'),

    # Default root path redirects to login
    path('', lambda request: views.login_view(request), name='root'),
]