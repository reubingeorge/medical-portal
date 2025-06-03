"""
Migration to create all required language options.
"""
from django.db import migrations


def create_languages(apps, schema_editor):
    """
    Create all supported languages in the database.
    """
    # Get the Language model
    Language = apps.get_model('accounts', 'Language')
    
    # Language codes used in the app
    LANGUAGES = [
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('ar', 'Arabic'),
        ('hi', 'Hindi'),
    ]
    
    # Create all languages if they don't exist
    for code, name in LANGUAGES:
        Language.objects.get_or_create(code=code)


def reverse_languages(apps, schema_editor):
    """
    No reverse operation needed (we don't want to delete languages).
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_default_language'),
    ]

    operations = [
        migrations.RunPython(create_languages, reverse_languages),
    ]