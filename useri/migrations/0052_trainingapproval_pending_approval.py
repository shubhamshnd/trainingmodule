# Generated by Django 5.0.1 on 2024-06-18 06:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0051_trainingsession_approvals'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingapproval',
            name='pending_approval',
            field=models.BooleanField(default=True),
        ),
    ]