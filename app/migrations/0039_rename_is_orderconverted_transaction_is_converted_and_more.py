# Generated by Django 4.2.3 on 2023-09-01 09:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0038_rename_transaction_quotation_transaction_id"),
    ]

    operations = [
        migrations.RenameField(
            model_name="transaction",
            old_name="is_orderConverted",
            new_name="is_converted",
        ),
        migrations.RemoveField(
            model_name="quotation",
            name="is_converted",
        ),
    ]
