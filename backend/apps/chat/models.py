"""
Models for the chat app.

This module defines the data models for the chat application, including:
- Chat documents used for RAG (Retrieval-Augmented Generation)
- Chat sessions between users and the AI assistant
- Individual chat messages within sessions
- Chunked document content for vector embedding
- User feedback on AI responses

These models support a conversational AI interface where users can discuss
medical documents and receive AI-generated responses based on document content.
The system uses retrieval-augmented generation to provide accurate, context-aware
responses by searching through document chunks in a vector database.
"""
import uuid
import hashlib
from typing import Optional, Dict, Any, Iterator

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.files.storage import default_storage


class ChatDocument(models.Model):
    """
    Model for documents used in the RAG (Retrieval-Augmented Generation) chatbot.

    This model stores medical documents that the AI assistant can reference when
    answering user questions. The documents are processed into chunks and indexed
    in a vector database for efficient semantic retrieval. Each document has
    metadata like title, description, document type, and associated cancer type.

    The system also tracks file integrity with SHA-256 hashing to detect
    duplicates and prevent redundant storage/indexing.

    Attributes:
        id (UUIDField): Primary key for the document
        title (CharField): Title of the document
        description (TextField): Summary or description of the document content
        document_type (CharField): Type of document (e.g., "Pathology Report", "Clinical Guidelines")
        file (FileField): The actual document file, stored in 'chat_documents/' directory
        cancer_type (ForeignKey): Reference to CancerType, limited to organ-level types
        indexed (BooleanField): Whether the document has been indexed in the vector store
        indexed_at (DateTimeField): When the document was last indexed
        file_hash (CharField): SHA-256 hash of the file content for integrity verification
        uploaded_by (ForeignKey): User who uploaded the document
        created_at (DateTimeField): When the document was created
        updated_at (DateTimeField): When the document was last updated
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_('Document title')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    document_type = models.CharField(
        max_length=100,
        verbose_name=_('Document type')
    )
    file = models.FileField(
        upload_to='chat_documents/',
        verbose_name=_('File')
    )
    cancer_type = models.ForeignKey(
        'medical.CancerType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_documents',
        verbose_name=_('Cancer type'),
        limit_choices_to={'is_organ': True}  # Only allow organ-level cancer types
    )
    indexed = models.BooleanField(
        default=False,
        verbose_name=_('Indexed in vector store')
    )
    indexed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Indexed at')
    )
    file_hash = models.CharField(
        max_length=64,  # SHA-256 hash is 64 characters
        blank=True,
        null=True,
        verbose_name=_('File hash'),
        help_text=_('SHA-256 hash of the document content')
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_chat_documents',
        verbose_name=_('Uploaded by')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )

    class Meta:
        """
        Metadata for the ChatDocument model.
        """
        verbose_name = _('Chat document')
        verbose_name_plural = _('Chat documents')
        ordering = ['-created_at']  # Most recent documents first

    def __str__(self) -> str:
        """
        Return a string representation of the document.

        Returns:
            str: The document title
        """
        return self.title

    def calculate_hash(self) -> Optional[str]:
        """
        Calculate SHA-256 hash of file content.

        This method efficiently reads the file in chunks to generate a hash,
        which is used for integrity verification and duplicate detection.

        Returns:
            Optional[str]: Hexadecimal SHA-256 hash of the file content, or None if no file
        """
        if not self.file:
            return None

        hash_obj = hashlib.sha256()
        self.file.seek(0)

        # Read file in chunks to handle large files efficiently
        for chunk in iter(lambda: self.file.read(4096), b''):
            hash_obj.update(chunk)

        # Reset file pointer
        self.file.seek(0)
        return hash_obj.hexdigest()

    def verify_hash(self) -> bool:
        """
        Verify file integrity by comparing stored hash with calculated hash.

        This method is useful for checking if a file has been modified
        after upload, or for validating file integrity during operations.

        Returns:
            bool: True if the stored hash matches the calculated hash, False otherwise
        """
        if not self.file_hash:
            return False

        calculated_hash = self.calculate_hash()
        return calculated_hash == self.file_hash

    def delete(self, *args: Any, **kwargs: Any) -> None:
        """
        Override delete method to efficiently delete chunks first.

        This custom delete method ensures proper cleanup by:
        1. Deleting all related document chunks in a single operation
        2. Removing the physical file from storage
        3. Performing the standard model deletion

        This approach prevents "Couldn't fetch original state" warnings by
        properly handling the deletion of related objects.

        Args:
            *args: Variable length argument list passed to super().delete()
            **kwargs: Arbitrary keyword arguments passed to super().delete()
        """
        # Use a bulk delete for chunks to avoid individual delete operations
        self.chunks.all().delete()

        # Delete the file from storage if it exists
        if self.file:
            storage = self.file.storage
            if storage.exists(self.file.name):
                storage.delete(self.file.name)

        # Call the "real" delete method
        super().delete(*args, **kwargs)


class ChatSession(models.Model):
    """
    Model for chat sessions between users and the AI assistant.

    A chat session represents a conversation thread between a user and the AI.
    Each session contains multiple messages (ChatMessage objects) and maintains
    metadata such as when the session was created and last updated.

    Sessions can be active or archived, with active sessions appearing in the
    user's dashboard for easy access. Users can have multiple sessions, each
    focused on different topics or documents.

    Attributes:
        id (UUIDField): Primary key for the session
        user (ForeignKey): The user who owns this chat session
        title (CharField): Title/name for the session
        created_at (DateTimeField): When the session was created
        updated_at (DateTimeField): When the session was last updated
        active (BooleanField): Whether the session is active or archived
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        verbose_name=_('User')
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_('Session title')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )
    active = models.BooleanField(
        default=True,
        verbose_name=_('Active')
    )

    class Meta:
        """
        Metadata for the ChatSession model.
        """
        verbose_name = _('Chat session')
        verbose_name_plural = _('Chat sessions')
        ordering = ['-updated_at']  # Most recently updated sessions first

    def __str__(self) -> str:
        """
        Return a string representation of the chat session.

        Returns:
            str: The session title and user's name
        """
        return f"{self.title} - {self.user.get_full_name()}"


class ChatMessage(models.Model):
    """
    Model for individual chat messages within a session.

    Each message represents a single utterance in a conversation, with a specified
    role (user, assistant, or system) and content. Messages are ordered chronologically
    within a session to maintain the conversation flow.

    The system uses these messages to:
    1. Display the conversation history to the user
    2. Provide context to the AI model for generating responses
    3. Support feedback collection and conversation analysis

    Attributes:
        id (UUIDField): Primary key for the message
        session (ForeignKey): The chat session this message belongs to
        role (CharField): Who sent the message - user, assistant, or system
        content (TextField): The actual message text
        created_at (DateTimeField): When the message was created
    """
    # Role constants
    ROLE_USER = 'user'
    ROLE_ASSISTANT = 'assistant'
    ROLE_SYSTEM = 'system'

    ROLE_CHOICES = [
        (ROLE_USER, _('User')),
        (ROLE_ASSISTANT, _('Assistant')),
        (ROLE_SYSTEM, _('System')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Chat session')
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name=_('Role')
    )
    content = models.TextField(
        verbose_name=_('Message content')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )

    class Meta:
        """
        Metadata for the ChatMessage model.
        """
        verbose_name = _('Chat message')
        verbose_name_plural = _('Chat messages')
        ordering = ['created_at']  # Chronological order within a session

    def __str__(self) -> str:
        """
        Return a string representation of the message.

        Returns:
            str: The role and a truncated version of the message content
        """
        return f"{self.get_role_display()}: {self.content[:50]}"

    @property
    def is_user_message(self) -> bool:
        """
        Check if this is a user message.

        Returns:
            bool: True if the message is from the user, False otherwise
        """
        return self.role == self.ROLE_USER

    @property
    def is_assistant_message(self) -> bool:
        """
        Check if this is an assistant message.

        Returns:
            bool: True if the message is from the assistant, False otherwise
        """
        return self.role == self.ROLE_ASSISTANT


class ChatDocumentChunk(models.Model):
    """
    Model for storing chunks of processed documents for vector embedding.

    Documents are broken down into smaller chunks for more efficient retrieval
    in the RAG (Retrieval-Augmented Generation) system. Each chunk represents a
    segment of text with its corresponding vector embedding for semantic search.

    The system uses these chunks to:
    1. Store document content in manageable pieces
    2. Create and maintain vector embeddings in the vector database
    3. Retrieve relevant context when answering user questions
    4. Track metadata about each chunk for enhanced retrieval

    Attributes:
        id (UUIDField): Primary key for the chunk
        document (ForeignKey): The document this chunk belongs to
        chunk_index (IntegerField): The sequential position of this chunk in the document
        content (TextField): The actual text content of this chunk
        metadata (JSONField): Additional information about the chunk (page number, etc.)
        embedding_id (CharField): Reference ID for this chunk's vector embedding
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    document = models.ForeignKey(
        ChatDocument,
        on_delete=models.CASCADE,
        related_name='chunks',
        verbose_name=_('Document')
    )
    chunk_index = models.IntegerField(
        verbose_name=_('Chunk index')
    )
    content = models.TextField(
        verbose_name=_('Chunk content')
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Metadata')
    )
    embedding_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Embedding ID in vector store')
    )

    class Meta:
        """
        Metadata for the ChatDocumentChunk model.
        """
        verbose_name = _('Document chunk')
        verbose_name_plural = _('Document chunks')
        ordering = ['document', 'chunk_index']  # Order by document and then by position
        unique_together = ['document', 'chunk_index']  # Each document/index pair must be unique

    def __str__(self) -> str:
        """
        Return a string representation of the document chunk.

        Returns:
            str: The document title and chunk index
        """
        return f"{self.document.title} - Chunk {self.chunk_index}"

    def has_embedding(self) -> bool:
        """
        Check if this chunk has an associated vector embedding.

        Returns:
            bool: True if an embedding ID exists, False otherwise
        """
        return bool(self.embedding_id)

    def get_context_str(self) -> str:
        """
        Get a string representation with metadata for context retrieval.

        Returns:
            str: Formatted content with source information
        """
        doc_title = self.document.title
        metadata_str = ""

        if self.metadata:
            if 'page' in self.metadata:
                metadata_str = f" (Page {self.metadata['page']})"

        return f"[Source: {doc_title}{metadata_str}]\n\n{self.content}"


class ChatFeedback(models.Model):
    """
    Model for collecting user feedback on AI assistant responses.

    This model stores user ratings and comments on AI-generated responses,
    which can be used to:
    1. Monitor the quality and helpfulness of AI responses
    2. Identify areas for improvement in the AI system
    3. Track user satisfaction metrics
    4. Collect specific comments or concerns from users

    Each feedback entry is connected to a specific assistant message
    and includes whether the user found it helpful and any additional comments.

    Attributes:
        id (UUIDField): Primary key for the feedback
        message (ForeignKey): The assistant message being rated
        helpful (BooleanField): Whether the user found the response helpful
        comment (TextField): Additional feedback from the user
        created_at (DateTimeField): When the feedback was submitted
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='feedback',
        verbose_name=_('Message')
    )
    helpful = models.BooleanField(
        verbose_name=_('Was this response helpful?')
    )
    comment = models.TextField(
        blank=True,
        verbose_name=_('Comment')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )

    class Meta:
        """
        Metadata for the ChatFeedback model.
        """
        verbose_name = _('Chat feedback')
        verbose_name_plural = _('Chat feedback')
        ordering = ['-created_at']  # Most recent feedback first

    def __str__(self) -> str:
        """
        Return a string representation of the feedback.

        Returns:
            str: A description including the message ID and helpfulness rating
        """
        return f"Feedback on {self.message.id} - {'Helpful' if self.helpful else 'Not helpful'}"