"""
Create Role and Language models for the User model.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[('patient', 'Patient'), ('clinician', 'Clinician'), ('administrator', 'Administrator')], max_length=50, unique=True, verbose_name='Role name')),
            ],
            options={
                'verbose_name': 'Role',
                'verbose_name_plural': 'Roles',
            },
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(choices=[('en', 'English'), ('es', 'Spanish'), ('fr', 'French'), ('ar', 'Arabic'), ('hi', 'Hindi')], max_length=10, unique=True, verbose_name='Language code')),
            ],
            options={
                'verbose_name': 'Language',
                'verbose_name_plural': 'Languages',
            },
        ),
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='users', to='accounts.role', verbose_name='Role'),
        ),
        migrations.AddField(
            model_name='user',
            name='language',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='users', to='accounts.language', verbose_name='Preferred language'),
        ),
        migrations.AddField(
            model_name='user',
            name='assigned_doctor',
            field=models.ForeignKey(blank=True, limit_choices_to={'role__name': 'clinician'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='patients', to='accounts.user', verbose_name='Assigned doctor'),
        ),
    ]