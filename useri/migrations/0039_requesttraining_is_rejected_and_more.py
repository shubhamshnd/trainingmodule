# Generated by Django 5.0.1 on 2024-06-08 07:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0038_approval_action'),
    ]

    operations = [
        migrations.AddField(
            model_name='requesttraining',
            name='is_rejected',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='superiorassignedtraining',
            name='is_rejected',
            field=models.BooleanField(default=False),
        ),
    ]
