# Generated by Django 4.2.3 on 2023-08-23 08:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0026_remove_transaction_category_id"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="item",
            name="category_id",
        ),
        migrations.DeleteModel(
            name="Category",
        ),
        migrations.DeleteModel(
            name="Item",
        ),
    ]
