"""
Migration for adding AI analysis fields to MedicalDocument model.
"""
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('medical', '0007_add_patient_notes_to_document'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicaldocument',
            name='ai_analysis_json',
            field=models.JSONField(
                blank=True,
                help_text='Results of AI analysis of the document',
                null=True,
                verbose_name='AI analysis results'
            ),
        ),
        migrations.AddField(
            model_name='medicaldocument',
            name='analysis_timestamp',
            field=models.DateTimeField(
                blank=True,
                help_text='When the document was last analyzed by AI',
                null=True,
                verbose_name='Analysis timestamp'
            ),
        ),
        migrations.AddField(
            model_name='medicaldocument',
            name='extracted_text',
            field=models.TextField(
                blank=True,
                help_text='Text extracted from the document using OCR',
                verbose_name='Extracted text'
            ),
        ),
        migrations.AddField(
            model_name='medicaldocument',
            name='is_pathology_report',
            field=models.BooleanField(
                default=False,
                help_text='Indicates if the document was detected as a pathology report',
                verbose_name='Is pathology report'
            ),
        ),
    ]