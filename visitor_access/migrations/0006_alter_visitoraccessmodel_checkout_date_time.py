# Generated by Django 5.1 on 2024-09-04 13:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visitor_access', '0005_alter_visitoraccessmodel_checkin_date_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visitoraccessmodel',
            name='checkout_date_time',
            field=models.DateTimeField(blank=True, default='', null=True),
        ),
    ]
