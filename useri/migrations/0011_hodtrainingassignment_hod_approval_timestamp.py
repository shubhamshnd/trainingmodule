# Generated by Django 5.0.1 on 2024-05-27 04:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0010_requesttraining_hod_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='hodtrainingassignment',
            name='hod_approval_timestamp',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
