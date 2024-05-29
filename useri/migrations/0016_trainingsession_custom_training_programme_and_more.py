# Generated by Django 5.0.1 on 2024-05-29 06:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0015_alter_trainermaster_city_alter_trainermaster_email_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingsession',
            name='custom_training_programme',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='trainingsession',
            name='training_programme',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='useri.trainingprogramme'),
        ),
    ]
