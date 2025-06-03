"""
Migration to update the User model's language field with a default value.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_create_languages'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='language',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'code': 'en'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='users',
                to='accounts.language',
                verbose_name='Preferred language'
            ),
        ),
    ]