import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("households", "0001_initial"),
        ("delivery_notification", "0002_deliverynotificationmodel_description"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="deliverynotificationmodel",
            name="user_to_delivery",
        ),
        migrations.AddField(
            model_name="deliverynotificationmodel",
            name="household",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="households.household",
            ),
            preserve_default=False,
        ),
    ]
