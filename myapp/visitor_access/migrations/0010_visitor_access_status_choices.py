"""Convert VisitorAccessModel.status into a choice field.

Old free-text values like ``"Scheduled"`` / ``"Checked-in"`` /
``"Checked-out"`` are migrated to the new uppercase enum values.
Anything unknown collapses to ``SCHEDULED`` so we never crash on
inserting new rows under the new max_length.
"""

from django.db import migrations, models


_LEGACY_TO_NEW = {
    "Scheduled": "SCHEDULED",
    "scheduled": "SCHEDULED",
    "Checked-in": "CHECKED_IN",
    "checked-in": "CHECKED_IN",
    "Checked-out": "CHECKED_OUT",
    "checked-out": "CHECKED_OUT",
    "Cancelled": "CANCELLED",
    "cancelled": "CANCELLED",
}

_VALID_NEW = {"SCHEDULED", "CHECKED_IN", "CHECKED_OUT", "CANCELLED"}


def migrate_status_values(apps, schema_editor):
    Visitor = apps.get_model("visitor_access", "VisitorAccessModel")
    for row in Visitor.objects.all().only("id", "status"):
        current = row.status or ""
        if current in _VALID_NEW:
            continue
        new_value = _LEGACY_TO_NEW.get(current, "SCHEDULED")
        Visitor.objects.filter(pk=row.pk).update(status=new_value)


def noop_reverse(apps, schema_editor):
    # We don't try to restore the old free-text spellings.
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("visitor_access", "0009_visitoraccessmodel_all_day_visitorgroupmodel_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_status_values, noop_reverse),
        migrations.AlterField(
            model_name="visitoraccessmodel",
            name="status",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("SCHEDULED", "Agendado"),
                    ("CHECKED_IN", "Check-in feito"),
                    ("CHECKED_OUT", "Concluído"),
                    ("CANCELLED", "Cancelado"),
                    ("NO_SHOW", "Não compareceu"),
                    ("EXPIRED", "Expirado sem checkout"),
                ],
                default="SCHEDULED",
            ),
        ),
    ]
