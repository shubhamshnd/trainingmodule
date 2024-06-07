# Generated by Django 5.0.1 on 2024-06-07 07:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0026_trainingsession_selected_participants'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='requesttraining',
            name='checker_approval_timestamp',
        ),
        migrations.RemoveField(
            model_name='requesttraining',
            name='checker_comment',
        ),
        migrations.RemoveField(
            model_name='requesttraining',
            name='hod_approval_timestamp',
        ),
        migrations.RemoveField(
            model_name='requesttraining',
            name='hod_comment',
        ),
        migrations.AddField(
            model_name='customuser',
            name='passport_no',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='requesttraining',
            name='is_final_approver',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='hodtrainingassignment',
            name='assigned_user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assigned_trainings_hod', to='useri.customuser'),
        ),
        migrations.CreateModel(
            name='Approval',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment', models.TextField(blank=True)),
                ('approval_timestamp', models.DateTimeField(auto_now_add=True)),
                ('approver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='useri.customuser')),
                ('request_training', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approvals', to='useri.requesttraining')),
            ],
        ),
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('head', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='headed_departments', to='useri.customuser')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sub_departments', to='useri.department')),
            ],
        ),
        migrations.AddField(
            model_name='customuser',
            name='departments',
            field=models.ManyToManyField(blank=True, related_name='members', to='useri.department'),
        ),
        migrations.CreateModel(
            name='SuperiorAssignedTraining',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('can_assign_trainings', models.BooleanField(default=False)),
                ('assigned_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='superior_assigned_trainings', to='useri.customuser')),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='superior_assigned_trainings', to='useri.department')),
                ('training_programme', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='superior_assigned_trainings', to='useri.trainingprogramme')),
            ],
        ),
    ]
