# Generated by Django 4.2.3 on 2023-08-23 05:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0024_alter_quotation_invoice_type"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="transaction",
            name="item_id",
        ),
        migrations.AddField(
            model_name="transaction",
            name="category_id",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="app.category",
            ),
        ),
    ]
