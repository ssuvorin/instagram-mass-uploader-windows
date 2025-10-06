# Generated manually to make created_at field editable

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('uploader', '0032_remove_dolphincookierobottask_account_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hashtaganalytics',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Date and time when analytics data was collected'),
        ),
    ]
