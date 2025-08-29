from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('uploader', '0014_alter_bulkuploadaccount_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='uploadtask',
            name='status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('PENDING', 'Pending'),
                    ('RUNNING', 'Running'),
                    ('COMPLETED', 'Completed'),
                    ('FAILED', 'Failed'),
                    ('PARTIALLY_COMPLETED', 'Partially Completed'),
                ],
                default='PENDING',
            ),
        ),
    ] 