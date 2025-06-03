from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('medical', '0009_convert_cancer_stage_to_char_field'),
    ]

    operations = [
        # Remove the old cancer_stage ForeignKey field 
        migrations.RemoveField(
            model_name='patientrecord',
            name='cancer_stage',
        ),
        
        # Delete the CancerStage model
        migrations.DeleteModel(
            name='CancerStage',
        ),
    ]