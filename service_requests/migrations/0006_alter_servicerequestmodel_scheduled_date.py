# Generated by Django 5.1 on 2024-09-09 13:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('service_requests', '0005_alter_servicerequestmodel_scheduled_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicerequestmodel',
            name='scheduled_date',
            field=models.DateField(),
        ),
    ]