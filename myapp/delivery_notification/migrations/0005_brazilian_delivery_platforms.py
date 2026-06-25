from django.db import migrations, models

_LEGACY_PLATFORMS = {"uber eats", "doordash", "just eat", "Other"}


def migrate_legacy_platforms(apps, schema_editor):
    DeliveryNotificationModel = apps.get_model(
        "delivery_notification", "DeliveryNotificationModel"
    )
    DeliveryNotificationModel.objects.filter(
        delivery_platform__in=_LEGACY_PLATFORMS
    ).update(delivery_platform="other")


class Migration(migrations.Migration):

    dependencies = [
        ("delivery_notification", "0004_deliverynotificationmodel_notified_holder"),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_platforms, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="deliverynotificationmodel",
            name="delivery_platform",
            field=models.CharField(
                choices=[
                    ("ifood", "iFood"),
                    ("rappi", "Rappi"),
                    ("amazon", "Amazon"),
                    ("mercado_livre", "Mercado Livre"),
                    ("magalu", "Magalu"),
                    ("shopee", "Shopee"),
                    ("correios", "Correios"),
                    ("other", "Outro"),
                ],
                default="other",
                max_length=20,
            ),
        ),
    ]
