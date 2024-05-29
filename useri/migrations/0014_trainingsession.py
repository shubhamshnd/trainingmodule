# Generated by Django 5.0.1 on 2024-05-29 04:47

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0013_trainermaster'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrainingSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='useri.customuser')),
                ('trainer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='useri.trainermaster')),
                ('training_programme', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='useri.trainingprogramme')),
                ('venue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='useri.venuemaster')),
            ],
        ),
    ]
