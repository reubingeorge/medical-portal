from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medical', '0006_doctortassignmentrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicaldocument',
            name='patient_notes',
            field=models.TextField(blank=True, help_text='Additional notes that will be visible to the patient', verbose_name='Notes for patient'),
        ),
        migrations.AddField(
            model_name='medicaldocument',
            name='file_hash',
            field=models.CharField(blank=True, max_length=64, verbose_name='File hash'),
        ),
    ]