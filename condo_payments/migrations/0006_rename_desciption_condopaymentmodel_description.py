# Generated by Django 5.1 on 2024-09-10 13:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('condo_payments', '0005_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='condopaymentmodel',
            old_name='desciption',
            new_name='description',
        ),
    ]