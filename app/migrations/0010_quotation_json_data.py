# Generated by Django 4.2.3 on 2023-08-02 08:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0009_rename_nots_transaction_notes"),
    ]

    operations = [
        migrations.AddField(
            model_name="quotation",
            name="json_data",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
