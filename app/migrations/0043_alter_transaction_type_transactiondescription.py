# Generated by Django 4.2.3 on 2023-09-04 05:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0042_transaction_exposuredetails_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="type",
            field=models.CharField(
                choices=[
                    ("sale", "SALE"),
                    ("purchase", "PURCHASE"),
                    ("payment_in", "PAYMENT IN"),
                    ("payment_out", "PAYMENT OUT"),
                    ("sale_order", "SALE ORDER"),
                    ("purchase_order", "PURCHASE ORDER"),
                    ("estimate", "ESTIMATE"),
                    ("expense", "EXPENSE"),
                    ("event_sale", "EVENT SALE"),
                    ("event_purchase", "EVENT PURCHASE"),
                ],
                default="payment_in",
                max_length=15,
            ),
        ),
        migrations.CreateModel(
            name="TransactionDescription",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("qty", models.IntegerField(default=0)),
                ("price", models.FloatField(default=0.0, max_length=10)),
                (
                    "inventory_id",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="app.inventory",
                    ),
                ),
                (
                    "transaction_id",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="app.transaction",
                    ),
                ),
            ],
        ),
    ]
