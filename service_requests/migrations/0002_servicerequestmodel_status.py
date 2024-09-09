# Generated by Django 5.1 on 2024-09-09 12:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('service_requests', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicerequestmodel',
            name='status',
            field=models.CharField(choices=[('requested', 'Requested'), ('accepted', 'Accepted'), ('declined', 'Declined')], default='requested', max_length=20),
        ),
    ]
