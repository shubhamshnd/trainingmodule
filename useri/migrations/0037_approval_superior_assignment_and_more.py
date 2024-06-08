# Generated by Django 5.0.1 on 2024-06-08 06:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0036_alter_approval_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='approval',
            name='superior_assignment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='approvals', to='useri.superiorassignedtraining'),
        ),
        migrations.AlterField(
            model_name='approval',
            name='request_training',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='approvals', to='useri.requesttraining'),
        ),
    ]
