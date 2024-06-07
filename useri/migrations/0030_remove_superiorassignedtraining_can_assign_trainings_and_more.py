# Generated by Django 5.0.1 on 2024-06-07 09:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0029_remove_customuser_card_active_status_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='superiorassignedtraining',
            name='can_assign_trainings',
        ),
        migrations.AddField(
            model_name='customuser',
            name='can_assign_trainings',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='customuser',
            name='is_checker',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='customuser',
            name='is_maker',
            field=models.BooleanField(default=False),
        ),
    ]
