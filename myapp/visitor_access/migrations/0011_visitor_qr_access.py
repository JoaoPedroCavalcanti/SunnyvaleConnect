from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("visitor_access", "0010_visitor_access_status_choices"),
    ]

    operations = [
        migrations.AddField(
            model_name="visitoraccessmodel",
            name="qr_access_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="visitoraccessmodel",
            name="access_token",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=64,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="visitoraccessmodel",
            name="access_code",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=10,
                null=True,
                unique=True,
            ),
        ),
        migrations.RemoveField(
            model_name="visitoraccessmodel",
            name="link_checkin",
        ),
        migrations.RemoveField(
            model_name="visitoraccessmodel",
            name="link_checkout",
        ),
    ]
