# Generated migration for enhanced TaskLock model

from django.db import migrations, models
from django.utils import timezone
from datetime import timedelta


def set_default_expiry(apps, schema_editor):
    """Set default expiry for existing locks."""
    TaskLock = apps.get_model('dashboard', 'TaskLock')
    default_expiry = timezone.now() + timedelta(hours=1)
    
    TaskLock.objects.filter(expires_at__isnull=True).update(
        expires_at=default_expiry,
        worker_id='legacy'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        # Add new fields
        migrations.AddField(
            model_name='tasklock',
            name='worker_id',
            field=models.CharField(blank=True, default='', help_text='Worker that acquired the lock', max_length=120),
        ),
        migrations.AddField(
            model_name='tasklock',
            name='acquired_at',
            field=models.DateTimeField(auto_now_add=True, help_text='When the lock was acquired', null=True),
        ),
        migrations.AddField(
            model_name='tasklock',
            name='expires_at',
            field=models.DateTimeField(help_text='When the lock expires', null=True),
        ),
        migrations.AddField(
            model_name='tasklock',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        
        # Add cookie_robot choice
        migrations.AlterField(
            model_name='tasklock',
            name='kind',
            field=models.CharField(choices=[
                ('bulk', 'Bulk Upload'), 
                ('bulk_login', 'Bulk Login'), 
                ('warmup', 'Warmup'), 
                ('avatar', 'Avatar'), 
                ('bio', 'Bio'), 
                ('follow', 'Follow'), 
                ('proxy_diag', 'Proxy Diagnostics'), 
                ('media_uniq', 'Media Uniq'), 
                ('cookie_robot', 'Cookie Robot')
            ], max_length=32),
        ),
        
        # Set default values for existing records
        migrations.RunPython(set_default_expiry, migrations.RunPython.noop),
        
        # Make expires_at non-nullable
        migrations.AlterField(
            model_name='tasklock',
            name='expires_at',
            field=models.DateTimeField(help_text='When the lock expires'),
        ),
        migrations.AlterField(
            model_name='tasklock',
            name='acquired_at',
            field=models.DateTimeField(auto_now_add=True, help_text='When the lock was acquired'),
        ),
        migrations.AlterField(
            model_name='tasklock',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        
        # Add new indexes
        migrations.AddIndex(
            model_name='tasklock',
            index=models.Index(fields=['expires_at'], name='dashboard_tasklock_expires_at_idx'),
        ),
        migrations.AddIndex(
            model_name='tasklock',
            index=models.Index(fields=['worker_id'], name='dashboard_tasklock_worker_id_idx'),
        ),
        migrations.AddIndex(
            model_name='tasklock',
            index=models.Index(fields=['acquired_at'], name='dashboard_tasklock_acquired_at_idx'),
        ),
        
        # Update Meta options
        migrations.AlterModelOptions(
            name='tasklock',
            options={'ordering': ['-acquired_at']},
        ),
    ]