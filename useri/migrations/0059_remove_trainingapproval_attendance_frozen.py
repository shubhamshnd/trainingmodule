# Generated by Django 5.0.1 on 2024-07-03 04:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0058_trainingapproval_attendance_frozen'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='trainingapproval',
            name='attendance_frozen',
        ),
    ]
