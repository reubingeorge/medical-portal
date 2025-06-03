"""
Initial migration for the medical app.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Appointment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('appointment_date', models.DateField(verbose_name='Appointment Date')),
                ('appointment_time', models.TimeField(verbose_name='Appointment Time')),
                ('appointment_type', models.CharField(choices=[('consultation', 'Consultation'), ('follow_up', 'Follow-up'), ('examination', 'Examination'), ('procedure', 'Procedure'), ('other', 'Other')], default='consultation', max_length=50, verbose_name='Appointment Type')),
                ('status', models.CharField(choices=[('scheduled', 'Scheduled'), ('confirmed', 'Confirmed'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('no_show', 'No Show')], default='scheduled', max_length=20, verbose_name='Status')),
                ('reason', models.TextField(blank=True, null=True, verbose_name='Reason for Visit')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='Notes')),
                ('created_at', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, default=django.utils.timezone.now, verbose_name='Updated At')),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='doctor_appointments', to=settings.AUTH_USER_MODEL, verbose_name='Doctor')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='patient_appointments', to=settings.AUTH_USER_MODEL, verbose_name='Patient')),
            ],
            options={
                'verbose_name': 'Appointment',
                'verbose_name_plural': 'Appointments',
                'ordering': ['appointment_date', 'appointment_time'],
            },
        ),
        migrations.CreateModel(
            name='MedicalRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('record_date', models.DateField(verbose_name='Record Date')),
                ('record_type', models.CharField(choices=[('visit_note', 'Visit Note'), ('lab_result', 'Lab Result'), ('diagnostic_image', 'Diagnostic Image'), ('prescription', 'Prescription'), ('procedure', 'Procedure'), ('immunization', 'Immunization'), ('other', 'Other')], max_length=50, verbose_name='Record Type')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('content', models.TextField(verbose_name='Content')),
                ('created_at', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, default=django.utils.timezone.now, verbose_name='Updated At')),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_records', to=settings.AUTH_USER_MODEL, verbose_name='Doctor')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='medical_records', to=settings.AUTH_USER_MODEL, verbose_name='Patient')),
            ],
            options={
                'verbose_name': 'Medical Record',
                'verbose_name_plural': 'Medical Records',
                'ordering': ['-record_date'],
            },
        ),
        migrations.CreateModel(
            name='Medication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Medication Name')),
                ('dosage', models.CharField(max_length=100, verbose_name='Dosage')),
                ('frequency', models.CharField(max_length=100, verbose_name='Frequency')),
                ('start_date', models.DateField(verbose_name='Start Date')),
                ('end_date', models.DateField(blank=True, null=True, verbose_name='End Date')),
                ('instructions', models.TextField(blank=True, null=True, verbose_name='Instructions')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is Active')),
                ('created_at', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, default=django.utils.timezone.now, verbose_name='Updated At')),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prescribed_medications', to=settings.AUTH_USER_MODEL, verbose_name='Doctor')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='medications', to=settings.AUTH_USER_MODEL, verbose_name='Patient')),
            ],
            options={
                'verbose_name': 'Medication',
                'verbose_name_plural': 'Medications',
                'ordering': ['-is_active', '-start_date'],
            },
        ),
    ]