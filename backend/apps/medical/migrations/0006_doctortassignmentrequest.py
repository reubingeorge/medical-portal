"""
Migration for creating the DoctorAssignmentRequest model.
"""
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_alter_user_language'),
        ('medical', '0005_mark_existing_types_as_organs'),
    ]

    operations = [
        migrations.CreateModel(
            name='DoctorAssignmentRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=10, verbose_name='Status')),
                ('requested_at', models.DateTimeField(auto_now_add=True, verbose_name='Requested at')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='Processed at')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='patient_requests', to='accounts.user', verbose_name='Requested Doctor')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='doctor_requests', to='accounts.user', verbose_name='Patient')),
                ('processed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_requests', to='accounts.user', verbose_name='Processed by')),
            ],
            options={
                'verbose_name': 'Doctor assignment request',
                'verbose_name_plural': 'Doctor assignment requests',
                'ordering': ['-requested_at'],
            },
        ),
    ]