import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delivery_notification", "0003_household_instead_of_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="deliverynotificationmodel",
            name="notified_holder_email",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
        migrations.AddField(
            model_name="deliverynotificationmodel",
            name="notified_holder_name",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
    ]
