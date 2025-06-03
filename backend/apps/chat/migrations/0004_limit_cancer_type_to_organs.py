"""
Migration to limit cancer_type to only organ-level types.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('medical', '0003_hierarchical_cancer_types'),
        ('chat', '0003_chatdocument_file_hash'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatdocument',
            name='cancer_type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='chat_documents',
                to='medical.cancertype',
                limit_choices_to={'is_organ': True},
                verbose_name='Cancer type'
            ),
        ),
    ]