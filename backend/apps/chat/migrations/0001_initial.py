"""
Initial migration for the chat app.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatDocument',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Document title')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('document_type', models.CharField(max_length=100, verbose_name='Document type')),
                ('file', models.FileField(upload_to='chat_documents/', verbose_name='File')),
                ('indexed', models.BooleanField(default=False, verbose_name='Indexed in vector store')),
                ('created_at', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, default=django.utils.timezone.now, verbose_name='Updated at')),
                ('indexed_at', models.DateTimeField(blank=True, null=True, verbose_name='Indexed at')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_chat_documents', to=settings.AUTH_USER_MODEL, verbose_name='Uploaded by')),
            ],
            options={
                'verbose_name': 'Chat document',
                'verbose_name_plural': 'Chat documents',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ChatSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Session title')),
                ('active', models.BooleanField(default=True, verbose_name='Active')),
                ('created_at', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, default=django.utils.timezone.now, verbose_name='Updated at')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_sessions', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Chat session',
                'verbose_name_plural': 'Chat sessions',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('user', 'User'), ('assistant', 'Assistant'), ('system', 'System')], max_length=10, verbose_name='Role')),
                ('content', models.TextField(verbose_name='Message content')),
                ('created_at', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Created at')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chat.chatsession', verbose_name='Chat session')),
            ],
            options={
                'verbose_name': 'Chat message',
                'verbose_name_plural': 'Chat messages',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='ChatDocumentChunk',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='ID')),
                ('chunk_index', models.IntegerField(verbose_name='Chunk index')),
                ('content', models.TextField(verbose_name='Chunk content')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='Metadata')),
                ('embedding_id', models.CharField(blank=True, max_length=255, null=True, verbose_name='Embedding ID in vector store')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='chat.chatdocument', verbose_name='Document')),
            ],
            options={
                'verbose_name': 'Document chunk',
                'verbose_name_plural': 'Document chunks',
                'ordering': ['document', 'chunk_index'],
                'unique_together': [('document', 'chunk_index')],
            },
        ),
        migrations.CreateModel(
            name='ChatFeedback',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='ID')),
                ('helpful', models.BooleanField(verbose_name='Was this response helpful?')),
                ('comment', models.TextField(blank=True, verbose_name='Comment')),
                ('created_at', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Created at')),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedback', to='chat.chatmessage', verbose_name='Message')),
            ],
            options={
                'verbose_name': 'Chat feedback',
                'verbose_name_plural': 'Chat feedback',
                'ordering': ['-created_at'],
            },
        ),
    ]