# Generated by Django 4.2.3 on 2023-09-05 06:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0045_rename_transactiondescription_inventorydescription_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="LinkTransaction",
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
                ("date", models.DateField(blank=True, null=True)),
                ("linked_amount", models.FloatField(default=0.0, max_length=10)),
                (
                    "from_transaction_id",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="from_transaction",
                        to="app.transaction",
                    ),
                ),
                (
                    "to_transaction_id",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="to_transaction",
                        to="app.transaction",
                    ),
                ),
            ],
        ),
    ]
