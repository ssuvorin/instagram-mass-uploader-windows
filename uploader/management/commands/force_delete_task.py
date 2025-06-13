from django.core.management.base import BaseCommand, CommandError
from uploader.models import BulkUploadTask
import sys

class Command(BaseCommand):
    help = 'Force delete a bulk upload task regardless of its status'

    def add_arguments(self, parser):
        parser.add_argument('task_id', type=int, help='ID of the task to delete')
        parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')

    def handle(self, *args, **options):
        task_id = options['task_id']
        confirm = options['confirm']
        
        try:
            task = BulkUploadTask.objects.get(id=task_id)
        except BulkUploadTask.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Task with ID {task_id} does not exist'))
            return
        
        self.stdout.write(f'Found task: {task.id} - {task.name} (Status: {task.status})')
        
        if not confirm:
            self.stdout.write(f'Are you sure you want to delete this task? [y/N] ', ending='')
            sys.stdout.flush()
            confirmation = input().lower()
            if confirmation != 'y':
                self.stdout.write(self.style.WARNING('Deletion cancelled'))
                return
        
        # Force delete all related objects first to avoid foreign key issues
        self.stdout.write('Deleting associated videos...')
        video_count = task.videos.all().count()
        task.videos.all().delete()
        
        self.stdout.write('Deleting associated account tasks...')
        account_count = task.accounts.all().count()
        task.accounts.all().delete()
        
        self.stdout.write('Deleting associated titles...')
        title_count = getattr(task, 'titles', []).count() if hasattr(task, 'titles') else 0
        if hasattr(task, 'titles'):
            task.titles.all().delete()
        
        # Finally delete the task itself
        task_name = task.name
        task.delete()
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully deleted bulk upload task "{task_name}" along with:'
            f'\n- {video_count} videos'
            f'\n- {account_count} account tasks'
            f'\n- {title_count} titles'
        )) 