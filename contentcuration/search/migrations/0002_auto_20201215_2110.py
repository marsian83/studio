# Generated by Django 3.1.4 on 2020-12-15 21:10
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('search', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='savedsearch',
            name='params',
            field=models.JSONField(default=dict),
        ),
    ]
