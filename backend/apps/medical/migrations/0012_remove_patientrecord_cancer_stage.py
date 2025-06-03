from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('medical', '0011_patientrecord_cancer_stage'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='patientrecord',
            name='cancer_stage',
        ),
    ]