# Generated manually to replace problematic Windows migration

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('uploader', '0043_merge_20251007_0130'),
    ]

    operations = [
        # Empty migration to replace 0046_merge_20251006_2342
        # This fixes the dependency issue on Windows
    ]
