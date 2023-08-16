# Generated by Django 4.2.3 on 2023-08-16 05:19

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0017_customer_social_media_quotation_couple_name"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="staff",
            name="studio_name",
        ),
        migrations.AddField(
            model_name="staff",
            name="is_eposure",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.CreateModel(
            name="StudioDetails",
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
                ("name", models.CharField(blank=True, max_length=200, null=True)),
                ("email", models.EmailField(blank=True, max_length=254, null=True)),
                ("phone", models.CharField(blank=True, null=True)),
                ("address", models.CharField(blank=True, max_length=200, null=True)),
                (
                    "social_media",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
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
        migrations.AddField(
            model_name="staff",
            name="studio_id",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="app.studiodetails",
            ),
        ),
    ]
