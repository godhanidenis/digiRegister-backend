# Generated by Django 4.2.3 on 2023-10-05 05:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0053_termsandconditions"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="advance_amount",
            field=models.FloatField(default=0.0, max_length=10),
        ),
    ]
