# Generated migration for RAG metrics model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chat', '0002_alter_chatdocument_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='RAGMetrics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query_id', models.CharField(max_length=255, unique=True)),
                ('query_text', models.TextField()),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('total_duration', models.FloatField()),
                ('retrieval_duration', models.FloatField()),
                ('reranking_duration', models.FloatField(default=0)),
                ('generation_duration', models.FloatField()),
                ('retrieval_count', models.IntegerField()),
                ('rerank_count', models.IntegerField(default=0)),
                ('confidence_score', models.FloatField()),
                ('fallback_used', models.BooleanField(default=False)),
                ('cache_hit', models.BooleanField(default=False)),
                ('cache_type', models.CharField(blank=True, max_length=20, null=True)),
                ('response_length', models.IntegerField()),
                ('tokens_used', models.IntegerField(default=0)),
                ('user_rating', models.IntegerField(blank=True, null=True)),
                ('user_feedback', models.TextField(blank=True, null=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rag_metrics', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-timestamp'],
                'indexes': [
                    models.Index(fields=['timestamp'], name='chat_ragmet_timesta_0b8f92_idx'),
                    models.Index(fields=['user', 'timestamp'], name='chat_ragmet_user_id_f3dc90_idx'),
                    models.Index(fields=['confidence_score'], name='chat_ragmet_confide_e7f3a9_idx'),
                ],
            },
        ),
    ]