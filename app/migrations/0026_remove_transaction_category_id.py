# Generated by Django 4.2.3 on 2023-08-23 08:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0025_remove_transaction_item_id_transaction_category_id"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="transaction",
            name="category_id",
        ),
    ]
