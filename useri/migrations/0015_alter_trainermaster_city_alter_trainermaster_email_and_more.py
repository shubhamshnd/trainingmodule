# Generated by Django 5.0.1 on 2024-05-29 05:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0014_trainingsession'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trainermaster',
            name='city',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='trainermaster',
            name='email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AlterField(
            model_name='trainermaster',
            name='phone_number',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
