# Generated by Django 4.2.3 on 2023-08-23 09:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("expense", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="item",
            name="category_id",
        ),
    ]
