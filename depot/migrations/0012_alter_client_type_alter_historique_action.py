# Generated by Django 4.1.1 on 2024-01-29 11:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('depot', '0011_alter_client_rs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='type',
            field=models.CharField(blank=True, default='DIPI', max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='historique',
            name='action',
            field=models.CharField(max_length=90),
        ),
    ]
