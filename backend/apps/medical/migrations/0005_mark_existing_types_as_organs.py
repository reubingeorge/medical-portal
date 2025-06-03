"""
Data migration to mark existing cancer types as organ types.
"""
from django.db import migrations


def mark_existing_types_as_organs(apps, schema_editor):
    """
    Mark all existing cancer types as organ-level types.
    This ensures backward compatibility with existing data.
    """
    CancerType = apps.get_model('medical', 'CancerType')
    # Update all existing cancer types to be organ types (is_organ=True)
    CancerType.objects.all().update(is_organ=True)


class Migration(migrations.Migration):
    dependencies = [
        ('medical', '0004_limit_cancer_type_to_organs'),
    ]

    operations = [
        migrations.RunPython(mark_existing_types_as_organs),
    ]