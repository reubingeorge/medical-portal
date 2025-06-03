"""
URL Configuration for the chat app.
"""
from django.urls import path
from . import views, views_new

app_name = 'chat'

urlpatterns = [
    # User chat interface
    path('', views.chat_interface, name='chat_interface'),
    path('message/', views.chat_message, name='chat_message'),

    # New simplified version
    path('new/', views_new.chat_interface, name='chat_interface_new'),
    path('new/message/', views_new.chat_message, name='chat_message_new'),
    path('test/', views.test_chat, name='test_chat'),
    path('test-page/', views.test_chat_page, name='test_chat_page'),
    path('feedback/', views.chat_feedback, name='chat_feedback'),
    path('history/', views.chat_history, name='chat_history'),
    path('session/<uuid:session_id>/', views.view_session, name='view_session'),
    path('session/create/', views.create_session, name='create_session'),
    path('session/<uuid:session_id>/update/', views.update_session, name='update_session'),
    path('session/<uuid:session_id>/delete/', views.delete_session, name='delete_session'),

    # Admin views
    path('admin/documents/', views.admin_chat_documents, name='admin_chat_documents'),
    path('admin/documents/<uuid:document_id>/delete/', views.delete_chat_document, name='delete_chat_document'),
    path('admin/documents/<uuid:document_id>/edit/', views.edit_chat_document, name='edit_chat_document'),
    path('admin/analytics/', views.admin_chat_analytics, name='admin_chat_analytics'),
    path('admin/feedback/', views.admin_chat_feedback, name='admin_chat_feedback'),
]