from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('uploader', '0010_remove_uploadtask_completed_at_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='BrowserFingerprint',
        ),
        migrations.RemoveField(
            model_name='instagramaccount',
            name='fingerprint',
        ),
    ]
