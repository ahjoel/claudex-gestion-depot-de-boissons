# Generated by Django 4.2 on 2023-12-31 16:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('depot', '0004_payement'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='payement',
            name='mt_facture',
        ),
        migrations.RemoveField(
            model_name='payement',
            name='mt_reglee',
        ),
    ]
