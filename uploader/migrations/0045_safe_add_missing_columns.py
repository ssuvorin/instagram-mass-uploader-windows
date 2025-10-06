# Generated manually to safely handle existing columns

from django.db import migrations, models


def safe_add_columns(apps, schema_editor):
    """Safely add columns if they don't exist"""
    db_alias = schema_editor.connection.alias
    
    with schema_editor.connection.cursor() as cursor:
        # Check if updated_at column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='uploader_hashtaganalytics' 
            AND column_name='updated_at'
        """)
        updated_at_exists = cursor.fetchone() is not None
        
        # Check if notes column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='uploader_hashtaganalytics' 
            AND column_name='notes'
        """)
        notes_exists = cursor.fetchone() is not None
    
    # Add updated_at if it doesn't exist
    if not updated_at_exists:
        schema_editor.add_field(
            apps.get_model('uploader', 'HashtagAnalytics'),
            models.DateTimeField(auto_now=True, name='updated_at')
        )
        print("Added updated_at column to HashtagAnalytics")
    else:
        print("updated_at column already exists in HashtagAnalytics")
    
    # Add notes if it doesn't exist
    if not notes_exists:
        schema_editor.add_field(
            apps.get_model('uploader', 'HashtagAnalytics'),
            models.TextField(blank=True, default="", help_text="Additional notes about the analytics", name='notes')
        )
        print("Added notes column to HashtagAnalytics")
    else:
        print("notes column already exists in HashtagAnalytics")


def reverse_safe_add_columns(apps, schema_editor):
    """Remove columns if they exist"""
    db_alias = schema_editor.connection.alias
    
    with schema_editor.connection.cursor() as cursor:
        # Check if updated_at column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='uploader_hashtaganalytics' 
            AND column_name='updated_at'
        """)
        updated_at_exists = cursor.fetchone() is not None
        
        # Check if notes column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='uploader_hashtaganalytics' 
            AND column_name='notes'
        """)
        notes_exists = cursor.fetchone() is not None
    
    # Remove updated_at if it exists
    if updated_at_exists:
        schema_editor.remove_field(
            apps.get_model('uploader', 'HashtagAnalytics'),
            models.DateTimeField(auto_now=True, name='updated_at')
        )
        print("Removed updated_at column from HashtagAnalytics")
    
    # Remove notes if it exists
    if notes_exists:
        schema_editor.remove_field(
            apps.get_model('uploader', 'HashtagAnalytics'),
            models.TextField(blank=True, default="", help_text="Additional notes about the analytics", name='notes')
        )
        print("Removed notes column from HashtagAnalytics")


class Migration(migrations.Migration):

    dependencies = [
        ('uploader', '0043_merge_20251007_0130'),
    ]

    operations = [
        migrations.RunPython(
            safe_add_columns,
            reverse_safe_add_columns,
        ),
    ]
