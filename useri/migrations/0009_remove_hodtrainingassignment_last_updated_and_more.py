# Generated by Django 5.0.1 on 2024-05-22 10:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0008_hodtrainingassignment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='hodtrainingassignment',
            name='last_updated',
        ),
        migrations.AlterField(
            model_name='hodtrainingassignment',
            name='hod_user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments_by_hod', to='useri.customuser'),
        ),
    ]
