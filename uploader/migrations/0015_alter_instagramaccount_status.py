# Generated by Django 5.1.5 on 2025-05-28 15:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('uploader', '0014_alter_bulkuploadaccount_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instagramaccount',
            name='status',
            field=models.CharField(choices=[('ACTIVE', 'Active'), ('BLOCKED', 'Blocked'), ('LIMITED', 'Limited'), ('INACTIVE', 'Inactive'), ('PHONE_VERIFICATION_REQUIRED', 'Phone Verification Required')], default='ACTIVE', max_length=30),
        ),
    ]
