# Generated by Django 5.0.1 on 2024-06-14 09:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('useri', '0048_customuser_card_validity'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainingsession',
            name='finalized',
            field=models.BooleanField(default=False),
        ),
    ]
