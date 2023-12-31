# Generated by Django 4.2.3 on 2023-08-03 09:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0012_alter_staff_unique_together_quotation_final_amount_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="quotation",
            name="event_venue",
            field=models.CharField(blank=True, null=True),
        ),
        migrations.AlterUniqueTogether(
            name="staff",
            unique_together={("user_id", "mobile_no")},
        ),
        migrations.CreateModel(
            name="StaffSkill",
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
                ("price", models.FloatField(max_length=10)),
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
                    "staff_id",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="app.staff",
                    ),
                ),
            ],
        ),
        migrations.RemoveField(
            model_name="staff",
            name="charges",
        ),
        migrations.RemoveField(
            model_name="staff",
            name="skill_id",
        ),
        migrations.DeleteModel(
            name="Skill",
        ),
    ]
