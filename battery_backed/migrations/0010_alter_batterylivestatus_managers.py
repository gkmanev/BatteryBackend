# Generated by Django 4.2.11 on 2024-09-03 09:08

from django.db import migrations
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('battery_backed', '0009_alter_batterylivestatus_timestamp'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='batterylivestatus',
            managers=[
                ('today', django.db.models.manager.Manager()),
            ],
        ),
    ]
