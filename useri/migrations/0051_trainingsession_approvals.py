# Generated by Django 5.0.1 on 2024-06-15 06:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0050_trainingapproval'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingsession',
            name='approvals',
            field=models.ManyToManyField(blank=True, related_name='training_sessions', to='useri.trainingapproval'),
        ),
    ]