# Generated by Django 5.0.1 on 2024-05-30 04:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0020_trainingsession_online_training_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingsession',
            name='online_training_file',
            field=models.FileField(blank=True, null=True, upload_to='training_files/'),
        ),
    ]
