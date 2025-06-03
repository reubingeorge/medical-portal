"""
Migration to set English as the default language for all users.
"""
from django.db import migrations
from django.db.models import F


def set_default_language(apps, schema_editor):
    """
    Set English as the default language for all users.
    """
    # Get the models
    User = apps.get_model('accounts', 'User')
    Language = apps.get_model('accounts', 'Language')
    
    # Create the English language if it doesn't exist
    english_lang, created = Language.objects.get_or_create(
        code='en',
        defaults={'code': 'en'}
    )
    
    # Set English as the default for all users without a language
    User.objects.filter(language__isnull=True).update(language=english_lang)


def reverse_default_language(apps, schema_editor):
    """
    No reverse operation needed.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_alter_user_options_alter_user_managers_and_more'),
    ]

    operations = [
        migrations.RunPython(set_default_language, reverse_default_language),
    ]