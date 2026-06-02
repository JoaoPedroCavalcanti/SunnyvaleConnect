"""Add User.role and backfill existing staff users to role=ADMIN.

Keeps `is_staff` as the underlying source of truth for `IsAdminUser` and
the Django Admin; from now on the service layer keeps both in sync
(role==ADMIN <=> is_staff=True).
"""

from django.db import migrations, models


def backfill_admin_role(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(is_staff=True).update(role="ADMIN")


def revert_admin_role(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(role="ADMIN").update(role="RESIDENT")


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_alter_user_apartment"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("RESIDENT", "Resident"),
                    ("ADMIN", "Admin"),
                    ("EMPLOYEE", "Employee"),
                ],
                default="RESIDENT",
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_admin_role, revert_admin_role),
    ]
