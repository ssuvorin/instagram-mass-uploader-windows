"""
Django management command for cleaning up expired task locks.

Usage:
    python manage.py cleanup_locks
    python manage.py cleanup_locks --worker-id worker_1 --force
    python manage.py cleanup_locks --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
import logging

from dashboard.models import TaskLock

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up expired task locks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--worker-id',
            type=str,
            help='Clean locks for specific worker ID'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup even if locks are not expired'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without actually doing it'
        )
        parser.add_argument(
            '--max-age',
            type=int,
            default=3600,
            help='Maximum age of locks in seconds (default: 3600)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of locks to process in each batch (default: 100)'
        )
    
    def handle(self, *args, **options):
        """Execute the cleanup command."""
        try:
            if options['worker_id']:
                self.cleanup_worker_locks(options)
            else:
                self.cleanup_expired_locks(options)
                
        except Exception as e:
            logger.error(f"Lock cleanup failed: {e}")
            raise CommandError(f"Lock cleanup failed: {e}")
    
    def cleanup_worker_locks(self, options):
        """Clean up locks for a specific worker."""
        worker_id = options['worker_id']
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(f"Cleaning locks for worker: {worker_id}")
        
        # Get locks for the worker
        worker_locks = TaskLock.objects.filter(worker_id=worker_id)
        
        if not force:
            # Only clean expired locks
            cutoff_time = timezone.now() - timedelta(seconds=options['max_age'])
            worker_locks = worker_locks.filter(expires_at__lte=timezone.now())
        
        count = worker_locks.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"Would clean {count} locks for worker {worker_id}")
            )
            
            # Show details of locks that would be cleaned
            for lock in worker_locks[:10]:  # Show first 10
                expiry_status = "EXPIRED" if hasattr(lock, 'is_expired') and lock.is_expired() else "ACTIVE"
                self.stdout.write(f"  - {lock.kind}:{lock.task_id} ({expiry_status})")
            
            if count > 10:
                self.stdout.write(f"  ... and {count - 10} more")
        else:
            # Actually delete the locks
            deleted_count, _ = worker_locks.delete()
            
            if deleted_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"Cleaned {deleted_count} locks for worker {worker_id}")
                )
                logger.info(f"Cleaned {deleted_count} locks for worker {worker_id}")
            else:
                self.stdout.write(f"No locks found for worker {worker_id}")
    
    def cleanup_expired_locks(self, options):
        """Clean up expired locks."""
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        max_age = options['max_age']
        
        self.stdout.write("Cleaning expired task locks...")
        
        total_cleaned = 0
        
        # Method 1: Use expires_at field if available
        if hasattr(TaskLock, 'expires_at'):
            expired_locks = TaskLock.objects.filter(expires_at__lte=timezone.now())
            count = expired_locks.count()
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"Would clean {count} expired locks (expires_at)")
                )
                
                # Show sample of expired locks
                for lock in expired_locks[:5]:
                    time_expired = timezone.now() - lock.expires_at
                    self.stdout.write(
                        f"  - {lock.kind}:{lock.task_id} by {lock.worker_id} "
                        f"(expired {time_expired.total_seconds():.0f}s ago)"
                    )
            else:
                # Delete in batches to avoid large transactions
                while True:
                    batch = list(expired_locks[:batch_size])
                    if not batch:
                        break
                    
                    batch_ids = [lock.id for lock in batch]
                    deleted_count, _ = TaskLock.objects.filter(id__in=batch_ids).delete()
                    total_cleaned += deleted_count
                    
                    self.stdout.write(f"Cleaned batch of {deleted_count} locks...")
        
        # Method 2: Fallback using created_at field for older models
        else:
            cutoff_time = timezone.now() - timedelta(seconds=max_age)
            old_locks = TaskLock.objects.filter(created_at__lte=cutoff_time)
            count = old_locks.count()
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"Would clean {count} old locks (created_at > {max_age}s)")
                )
                
                for lock in old_locks[:5]:
                    age = timezone.now() - lock.created_at
                    self.stdout.write(
                        f"  - {lock.kind}:{lock.task_id} "
                        f"(age: {age.total_seconds():.0f}s)"
                    )
            else:
                # Delete in batches
                while True:
                    batch = list(old_locks[:batch_size])
                    if not batch:
                        break
                    
                    batch_ids = [lock.id for lock in batch]
                    deleted_count, _ = TaskLock.objects.filter(id__in=batch_ids).delete()
                    total_cleaned += deleted_count
                    
                    self.stdout.write(f"Cleaned batch of {deleted_count} locks...")
        
        if not dry_run and total_cleaned > 0:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully cleaned {total_cleaned} expired locks")
            )
            logger.info(f"Cleaned {total_cleaned} expired task locks")
        elif not dry_run:
            self.stdout.write("No expired locks found")
    
    def get_lock_statistics(self):
        """Get current lock statistics."""
        total_locks = TaskLock.objects.count()
        
        stats = {
            'total_locks': total_locks,
            'by_kind': {},
            'by_worker': {},
            'expired_count': 0
        }
        
        # Count by kind
        for choice in TaskLock.KIND_CHOICES:
            kind = choice[0]
            count = TaskLock.objects.filter(kind=kind).count()
            if count > 0:
                stats['by_kind'][kind] = count
        
        # Count by worker (if field exists)
        if hasattr(TaskLock, 'worker_id'):
            workers = TaskLock.objects.values_list('worker_id', flat=True).distinct()
            for worker_id in workers:
                if worker_id:
                    count = TaskLock.objects.filter(worker_id=worker_id).count()
                    stats['by_worker'][worker_id] = count
        
        # Count expired (if field exists)
        if hasattr(TaskLock, 'expires_at'):
            stats['expired_count'] = TaskLock.objects.filter(
                expires_at__lte=timezone.now()
            ).count()
        
        return stats
    
    def show_statistics(self):
        """Show current lock statistics."""
        stats = self.get_lock_statistics()
        
        self.stdout.write(f"Total locks: {stats['total_locks']}")
        
        if stats['by_kind']:
            self.stdout.write("By task type:")
            for kind, count in stats['by_kind'].items():
                self.stdout.write(f"  {kind}: {count}")
        
        if stats['by_worker']:
            self.stdout.write("By worker:")
            for worker_id, count in stats['by_worker'].items():
                self.stdout.write(f"  {worker_id}: {count}")
        
        if stats['expired_count'] > 0:
            self.stdout.write(
                self.style.WARNING(f"Expired locks: {stats['expired_count']}")
            )