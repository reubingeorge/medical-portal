from django.db import migrations, models


def migrate_cancer_stages(apps, schema_editor):
    """
    Migrate data from CancerStage model to cancer_stage_text field in PatientRecord.
    """
    PatientRecord = apps.get_model('medical', 'PatientRecord')
    
    # For each patient record with a cancer_stage, set cancer_stage_text to cancer_stage.name
    for record in PatientRecord.objects.all():
        if record.cancer_stage_id is not None:
            CancerStage = apps.get_model('medical', 'CancerStage')
            try:
                stage = CancerStage.objects.get(id=record.cancer_stage_id)
                record.cancer_stage_text = stage.name
                record.save(update_fields=['cancer_stage_text'])
            except CancerStage.DoesNotExist:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('medical', '0008_add_ai_analysis_fields'),
    ]

    operations = [
        # 1. Add the new cancer_stage_text field
        migrations.AddField(
            model_name='patientrecord',
            name='cancer_stage_text',
            field=models.CharField(blank=True, help_text='Stage of cancer (e.g., Stage I, Stage II, etc.)', max_length=50, verbose_name='Cancer stage'),
        ),
        
        # 2. Migrate data from cancer_stage ForeignKey to cancer_stage_text
        migrations.RunPython(migrate_cancer_stages),
        
        # Note: Temporarily leaving the cancer_stage field for compatibility
        # We'll create another migration to remove it after this one is applied
    ]