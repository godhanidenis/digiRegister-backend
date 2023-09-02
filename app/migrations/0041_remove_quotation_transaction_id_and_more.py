# Generated by Django 4.2.3 on 2023-09-02 06:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0040_transaction_staff_id_alter_transaction_type"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="quotation",
            name="transaction_id",
        ),
        migrations.RemoveField(
            model_name="transaction",
            name="amount",
        ),
        migrations.AddField(
            model_name="transaction",
            name="quotation_id",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="app.quotation",
            ),
        ),
    ]
