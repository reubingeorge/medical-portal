"""
Migration to add specialty_name field to User model.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_alter_user_language'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='specialty_name',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name='Specialty'
            ),
        ),
    ]