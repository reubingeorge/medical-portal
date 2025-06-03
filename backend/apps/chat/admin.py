"""
Admin configuration for the chat app.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    ChatDocument, ChatDocumentChunk, ChatSession,
    ChatMessage, ChatFeedback
)


@admin.register(ChatDocument)
class ChatDocumentAdmin(admin.ModelAdmin):
    """
    Admin interface for ChatDocument model.
    """
    list_display = (
        'title', 'document_type', 'cancer_type',
        'indexed', 'indexed_at', 'has_hash', 'uploaded_by', 'created_at'
    )
    list_filter = ('indexed', 'document_type', 'cancer_type', 'created_at')
    search_fields = ('title', 'description', 'file_hash')
    readonly_fields = ('indexed', 'indexed_at', 'file_hash', 'uploaded_by', 'created_at', 'updated_at')
    
    def has_hash(self, obj):
        """Return whether the document has a hash."""
        return bool(obj.file_hash)
        
    has_hash.boolean = True
    has_hash.short_description = _('Hash')
    fieldsets = (
        (None, {
            'fields': ('title', 'document_type', 'description')
        }),
        (_('Document Files'), {
            'fields': ('file', 'cancer_type', 'file_hash')
        }),
        (_('Indexing Information'), {
            'fields': ('indexed', 'indexed_at')
        }),
        (_('Metadata'), {
            'fields': ('uploaded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class ChatDocumentChunkInline(admin.TabularInline):
    """
    Inline admin for document chunks.
    """
    model = ChatDocumentChunk
    extra = 0
    readonly_fields = ('chunk_index', 'embedding_id')
    fields = ('chunk_index', 'content', 'metadata', 'embedding_id')
    can_delete = False
    max_num = 10  # Limit the number of displayed chunks

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatDocumentChunk)
class ChatDocumentChunkAdmin(admin.ModelAdmin):
    """
    Admin interface for ChatDocumentChunk model.
    """
    list_display = ('document', 'chunk_index', 'truncated_content', 'embedding_id')
    list_filter = ('document',)
    search_fields = ('content',)
    readonly_fields = ('document', 'chunk_index', 'content', 'metadata', 'embedding_id')

    def truncated_content(self, obj):
        """Return truncated content."""
        if len(obj.content) > 50:
            return f"{obj.content[:50]}..."
        return obj.content

    truncated_content.short_description = _('Content')


class ChatMessageInline(admin.TabularInline):
    """
    Inline admin for chat messages.
    """
    model = ChatMessage
    extra = 0
    readonly_fields = ('role', 'content', 'created_at')
    fields = ('role', 'truncated_content', 'created_at')
    can_delete = False
    max_num = 20  # Limit the number of displayed messages

    def truncated_content(self, obj):
        """Return truncated content."""
        if len(obj.content) > 100:
            return f"{obj.content[:100]}..."
        return obj.content

    truncated_content.short_description = _('Content')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for ChatSession model.
    """
    list_display = ('title', 'user', 'message_count', 'active', 'created_at', 'updated_at')
    list_filter = ('active', 'created_at', 'updated_at')
    search_fields = ('title', 'user__first_name', 'user__last_name', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ChatMessageInline]

    def message_count(self, obj):
        """Return the number of messages in the session."""
        return obj.messages.count()

    message_count.short_description = _('Messages')


class ChatFeedbackInline(admin.TabularInline):
    """
    Inline admin for chat feedback.
    """
    model = ChatFeedback
    extra = 0
    readonly_fields = ('helpful', 'comment', 'created_at')
    fields = ('helpful', 'comment', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """
    Admin interface for ChatMessage model.
    """
    list_display = ('session_user', 'role', 'truncated_content', 'has_feedback', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content', 'session__user__email')
    readonly_fields = ('session', 'role', 'content', 'created_at')
    inlines = [ChatFeedbackInline]

    def truncated_content(self, obj):
        """Return truncated content."""
        if len(obj.content) > 100:
            return f"{obj.content[:100]}..."
        return obj.content

    truncated_content.short_description = _('Content')

    def has_feedback(self, obj):
        """Return whether the message has feedback."""
        return hasattr(obj, 'feedback') and obj.feedback.exists()

    has_feedback.boolean = True
    has_feedback.short_description = _('Has Feedback')

    def session_user(self, obj):
        """Return the user of the session."""
        return obj.session.user.get_full_name()

    session_user.short_description = _('User')

    def has_add_permission(self, request):
        return False


@admin.register(ChatFeedback)
class ChatFeedbackAdmin(admin.ModelAdmin):
    """
    Admin interface for ChatFeedback model.
    """
    list_display = ('message_user', 'helpful', 'truncated_comment', 'created_at')
    list_filter = ('helpful', 'created_at')
    search_fields = ('comment', 'message__content', 'message__session__user__email')
    readonly_fields = ('message', 'helpful', 'comment', 'created_at')

    def truncated_comment(self, obj):
        """Return truncated comment."""
        if not obj.comment:
            return _('No comment')
        if len(obj.comment) > 100:
            return f"{obj.comment[:100]}..."
        return obj.comment

    truncated_comment.short_description = _('Comment')

    def message_user(self, obj):
        """Return the user of the message."""
        return obj.message.session.user.get_full_name()

    message_user.short_description = _('User')

    def has_add_permission(self, request):
        return False