# Generated by Django 4.2.3 on 2023-08-02 11:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0011_quotation_converted_on_quotation_created_on"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="staff",
            unique_together={("user_id", "mobile_no", "skill_id")},
        ),
        migrations.AddField(
            model_name="quotation",
            name="final_amount",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="staff",
            name="charges",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
