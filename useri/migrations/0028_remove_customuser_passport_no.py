# Generated by Django 5.0.1 on 2024-06-07 07:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0027_remove_requesttraining_checker_approval_timestamp_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customuser',
            name='passport_no',
        ),
    ]
