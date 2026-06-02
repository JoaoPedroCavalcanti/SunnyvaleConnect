"""Recreate ServiceRequestModel with a richer schema.

The first iteration of the app used loose strings for ``service_type``
and ``status`` and didn't keep the admin's response. The new schema
introduces proper TextChoices, the ``admin_response`` /
``responded_by`` / ``responded_at`` fields and renames
``requester_user`` to ``requester``. Because every column changes at
once, the simplest path is a full drop+create — there are no production
records to preserve.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("service_requests", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.DeleteModel(name="ServiceRequestModel"),
        migrations.CreateModel(
            name="ServiceRequestModel",
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
                ("title", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "service_type",
                    models.CharField(
                        choices=[
                            ("CLEANING", "Extra cleaning"),
                            ("MAINTENANCE", "General maintenance"),
                            ("PLUMBING", "Plumbing"),
                            ("ELECTRICAL", "Electrical"),
                            ("SECURITY", "Security"),
                            ("LANDSCAPING", "Landscaping"),
                            ("PEST_CONTROL", "Pest control"),
                            ("OTHER", "Other"),
                        ],
                        default="OTHER",
                        max_length=20,
                    ),
                ),
                (
                    "location",
                    models.CharField(blank=True, default="", max_length=150),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("LOW", "Low"),
                            ("MEDIUM", "Medium"),
                            ("HIGH", "High"),
                            ("URGENT", "Urgent"),
                        ],
                        default="LOW",
                        max_length=10,
                    ),
                ),
                (
                    "request_scheduled_date",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("ACCEPTED", "Accepted"),
                            ("DECLINED", "Declined"),
                            ("COMPLETED", "Completed"),
                        ],
                        default="PENDING",
                        max_length=10,
                    ),
                ),
                ("admin_response", models.TextField(blank=True, default="")),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "requester",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "responded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="responded_service_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
