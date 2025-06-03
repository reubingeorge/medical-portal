"""
Migration to limit cancer_type to only organ-level types in PatientRecord and MedicalDocument.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('medical', '0003_hierarchical_cancer_types'),
    ]

    operations = [
        migrations.AlterField(
            model_name='patientrecord',
            name='cancer_type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='patients',
                to='medical.cancertype',
                limit_choices_to={'is_organ': True},
                verbose_name='Cancer type'
            ),
        ),
        migrations.AlterField(
            model_name='medicaldocument',
            name='cancer_type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='documents',
                to='medical.cancertype',
                limit_choices_to={'is_organ': True},
                verbose_name='Cancer type'
            ),
        ),
    ]