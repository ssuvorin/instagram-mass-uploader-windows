from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
import sys

class Command(BaseCommand):
    help = 'Delete a superuser by username'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the superuser to delete')
        parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')

    def handle(self, *args, **options):
        username = options['username']
        confirm = options['confirm']
        
        User = get_user_model()
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'User with username "{username}" does not exist'))
            return
        
        # Check if user is actually a superuser
        if not user.is_superuser:
            self.stderr.write(self.style.ERROR(f'User "{username}" is not a superuser'))
            return
        
        self.stdout.write(f'Found superuser: {user.username} (ID: {user.id})')
        self.stdout.write(f'Email: {user.email}')
        self.stdout.write(f'Date joined: {user.date_joined}')
        self.stdout.write(f'Last login: {user.last_login}')
        
        if not confirm:
            self.stdout.write(f'Are you sure you want to delete superuser "{username}"? [y/N] ', ending='')
            sys.stdout.flush()
            confirmation = input().lower()
            if confirmation != 'y':
                self.stdout.write(self.style.WARNING('Deletion cancelled'))
                return
        
        # Delete the user
        user.delete()
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully deleted superuser "{username}"'
        ))
