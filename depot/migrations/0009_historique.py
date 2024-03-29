# Generated by Django 4.1.1 on 2024-01-20 14:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('depot', '0008_rename_mt_encaisse_jour_payement_mt_recu_client_type_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Historique',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=30)),
                ('table', models.CharField(max_length=30)),
                ('contenu', models.TextField()),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('date_modification', models.DateTimeField(auto_now=True)),
                ('auteur', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'GESTION DES HISTORIQUES',
            },
        ),
    ]
