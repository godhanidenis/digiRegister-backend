# Generated by Django 4.2.3 on 2023-07-24 11:25

import django.contrib.auth.validators
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
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
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={
                            "unique": "A user with that username already exists."
                        },
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        validators=[
                            django.contrib.auth.validators.UnicodeUsernameValidator()
                        ],
                        verbose_name="username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="first name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="last name"
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date joined"
                    ),
                ),
                ("shop_name", models.CharField(blank=True, max_length=200, null=True)),
                ("full_name", models.CharField(blank=True, max_length=100, null=True)),
                ("mobile_no", models.CharField(blank=True, max_length=15, null=True)),
                ("email", models.EmailField(max_length=100, unique=True)),
                ("password", models.CharField(blank=True, max_length=10, null=True)),
                (
                    "type_of_user",
                    models.CharField(
                        choices=[
                            ("super_admin", "SUPER_ADMIN"),
                            ("company_owner", "COMANY_OWNER"),
                        ],
                        default="SUPER ADMIN",
                        max_length=20,
                    ),
                ),
                ("address", models.CharField(blank=True, max_length=200, null=True)),
                ("is_active", models.BooleanField(default=False)),
                (
                    "instagram_id",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("you_tube", models.CharField(blank=True, max_length=100, null=True)),
                (
                    "facebook_id",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "profile_pic",
                    models.CharField(blank=True, max_length=150, null=True),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "User",
                "verbose_name_plural": "Users",
            },
        ),
    ]
