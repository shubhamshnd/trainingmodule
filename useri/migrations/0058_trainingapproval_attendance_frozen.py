# Generated by Django 5.0.1 on 2024-07-03 04:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0057_departmentcount'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingapproval',
            name='attendance_frozen',
            field=models.BooleanField(default=False),
        ),
    ]
