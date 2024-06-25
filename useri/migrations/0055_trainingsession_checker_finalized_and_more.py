# Generated by Django 5.0.1 on 2024-06-25 07:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0054_trainingapproval_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingsession',
            name='checker_finalized',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='trainingsession',
            name='checker_finalized_timestamp',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
