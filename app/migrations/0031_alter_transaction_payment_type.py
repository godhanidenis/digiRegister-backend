# Generated by Django 4.2.3 on 2023-08-25 04:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0030_alter_transaction_payment_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="payment_type",
            field=models.CharField(
                choices=[
                    ("cash", "CASH"),
                    ("cheque", "CHEQUE"),
                    ("net_banking", "NET BANKING"),
                    ("upi", "UPI"),
                ],
                default="cash",
                max_length=15,
            ),
        ),
    ]