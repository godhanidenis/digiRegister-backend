# Generated by Django 4.2.3 on 2023-08-08 04:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0015_alter_quotation_final_amount"),
    ]

    operations = [
        migrations.AddField(
            model_name="staff",
            name="social_media",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]