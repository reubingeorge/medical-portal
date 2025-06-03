"""
Add file_hash field to ChatDocument model.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_alter_chatdocument_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatdocument',
            name='file_hash',
            field=models.CharField(
                blank=True, 
                help_text='SHA-256 hash of the document content', 
                max_length=64, 
                null=True, 
                verbose_name='File hash'
            ),
        ),
    ]