# Generated by Django 4.2.3 on 2024-01-26 09:55

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0058_inventorydescription_quotation_id_eventexpense"),
    ]

    operations = [
        migrations.CreateModel(
            name="CashAndBank",
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
                (
                    "type",
                    models.CharField(
                        choices=[("cash", "CASH"), ("net_banking", "NET BANKING")],
                        default="cash",
                        max_length=15,
                    ),
                ),
                ("amount", models.FloatField(default=0.0, max_length=10)),
                ("date", models.DateField(blank=True, null=True)),
                (
                    "user_id",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
