"""
Migration to implement hierarchical cancer types.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('medical', '0002_cancerstage_cancertype_faq_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cancertype',
            name='is_organ',
            field=models.BooleanField(
                default=False,
                help_text='If checked, this cancer type represents an organ-level classification',
                verbose_name='Is organ-level type'
            ),
        ),
        migrations.AddField(
            model_name='cancertype',
            name='parent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='subtypes',
                to='medical.cancertype',
                verbose_name='Parent cancer type'
            ),
        ),
        migrations.AlterField(
            model_name='cancertype',
            name='name',
            field=models.CharField(
                max_length=100,
                verbose_name='Cancer type name'
            ),
        ),
        migrations.AddConstraint(
            model_name='cancertype',
            constraint=models.UniqueConstraint(
                fields=('name', 'parent'),
                name='unique_name_parent'
            ),
        ),
    ]