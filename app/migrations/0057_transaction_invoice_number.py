# Generated by Django 4.2.3 on 2023-11-22 07:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0056_transaction_exposuredetails_ids_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="invoice_number",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
