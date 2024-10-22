# Generated by Django 4.2.11 on 2024-10-22 11:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('battery_backed', '0017_alter_cumulativeyear_unique_together_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Price',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='EUR', max_length=3)),
            ],
        ),
    ]
