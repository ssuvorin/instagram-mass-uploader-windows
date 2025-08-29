"""
Enhanced task lock manager with TTL support for production deployments.

This module provides thread-safe task locking with automatic expiration
to prevent stuck locks when workers crash unexpectedly.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from django.utils import timezone
from django.db import transaction, connection
from django.core.management.base import BaseCommand

from .models import TaskLock

logger = logging.getLogger(__name__)


class TaskLockManager:
    """Production-ready task lock manager with TTL and cleanup."""
    
    def __init__(self, default_ttl_minutes: int = 60):
        self.default_ttl_minutes = default_ttl_minutes
    
    def acquire_lock(
        self, 
        kind: str, 
        task_id: int, 
        worker_id: str,
        ttl_minutes: Optional[int] = None
    ) -> bool:
        """
        Acquire a task lock with TTL.
        
        Args:
            kind: Type of task (bulk, warmup, etc.)
            task_id: Task ID to lock
            worker_id: Worker acquiring the lock
            ttl_minutes: Lock expiration time in minutes
            
        Returns:
            True if lock acquired, False if already locked
        """
        ttl = ttl_minutes or self.default_ttl_minutes
        expires_at = timezone.now() + timedelta(minutes=ttl)
        
        try:
            with transaction.atomic():
                # Clean up expired locks first
                self._cleanup_expired_locks()
                
                # Try to acquire lock
                existing_lock = TaskLock.objects.filter(
                    kind=kind, 
                    task_id=task_id
                ).first()
                
                if existing_lock:
                    # Check if existing lock is expired
                    if hasattr(existing_lock, 'expires_at') and existing_lock.expires_at <= timezone.now():
                        existing_lock.delete()
                        logger.info(f"Removed expired lock: {kind}:{task_id}")
                    else:
                        logger.warning(f"Lock already exists: {kind}:{task_id} (held by {getattr(existing_lock, 'worker_id', 'unknown')})")
                        return False
                
                # Create new lock
                lock_data = {
                    'kind': kind,
                    'task_id': task_id,
                    'worker_id': worker_id,
                    'acquired_at': timezone.now(),
                    'expires_at': expires_at
                }
                
                # Add TTL fields if model supports them
                if hasattr(TaskLock, 'expires_at'):
                    TaskLock.objects.create(**lock_data)
                else:
                    # Fallback for models without TTL support
                    TaskLock.objects.create(kind=kind, task_id=task_id)
                
                logger.info(f"Lock acquired: {kind}:{task_id} by {worker_id} (expires: {expires_at})")
                return True
                
        except Exception as e:
            logger.error(f"Error acquiring lock {kind}:{task_id}: {e}")
            return False
    
    def release_lock(self, kind: str, task_id: int, worker_id: Optional[str] = None) -> bool:
        """
        Release a task lock.
        
        Args:
            kind: Type of task
            task_id: Task ID to unlock
            worker_id: Worker releasing the lock (for verification)
            
        Returns:
            True if lock released, False if not found
        """
        try:
            with transaction.atomic():
                filters = {'kind': kind, 'task_id': task_id}
                
                # Add worker verification if supported
                if worker_id and hasattr(TaskLock, 'worker_id'):
                    filters['worker_id'] = worker_id
                
                deleted_count, _ = TaskLock.objects.filter(**filters).delete()
                
                if deleted_count > 0:
                    logger.info(f"Lock released: {kind}:{task_id} by {worker_id or 'unknown'}")
                    return True
                else:
                    logger.warning(f"Lock not found for release: {kind}:{task_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error releasing lock {kind}:{task_id}: {e}")
            return False
    
    def refresh_lock(self, kind: str, task_id: int, worker_id: str, ttl_minutes: Optional[int] = None) -> bool:
        """
        Refresh lock expiration time.
        
        Args:
            kind: Type of task
            task_id: Task ID
            worker_id: Worker owning the lock
            ttl_minutes: New expiration time
            
        Returns:
            True if refreshed, False if lock not found or not owned
        """
        if not hasattr(TaskLock, 'expires_at'):
            return True  # No TTL support, nothing to refresh
        
        ttl = ttl_minutes or self.default_ttl_minutes
        new_expires_at = timezone.now() + timedelta(minutes=ttl)
        
        try:
            with transaction.atomic():
                updated = TaskLock.objects.filter(
                    kind=kind,
                    task_id=task_id,
                    worker_id=worker_id
                ).update(expires_at=new_expires_at)
                
                if updated > 0:
                    logger.debug(f"Lock refreshed: {kind}:{task_id} (expires: {new_expires_at})")
                    return True
                else:
                    logger.warning(f"Lock not found for refresh: {kind}:{task_id} by {worker_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error refreshing lock {kind}:{task_id}: {e}")
            return False
    
    def is_locked(self, kind: str, task_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if task is locked.
        
        Returns:
            Tuple of (is_locked, worker_id)
        """
        try:
            self._cleanup_expired_locks()
            
            lock = TaskLock.objects.filter(kind=kind, task_id=task_id).first()
            if lock:
                worker_id = getattr(lock, 'worker_id', 'unknown')
                return True, worker_id
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking lock {kind}:{task_id}: {e}")
            return False, None
    
    def get_locks_by_worker(self, worker_id: str) -> List[Dict]:
        """Get all locks held by a specific worker."""
        if not hasattr(TaskLock, 'worker_id'):
            return []
        
        try:
            self._cleanup_expired_locks()
            
            locks = TaskLock.objects.filter(worker_id=worker_id).values(
                'kind', 'task_id', 'acquired_at', 'expires_at'
            )
            return list(locks)
            
        except Exception as e:
            logger.error(f"Error getting locks for worker {worker_id}: {e}")
            return []
    
    def get_all_active_locks(self) -> List[Dict]:
        """Get all active locks."""
        try:
            self._cleanup_expired_locks()
            
            locks = TaskLock.objects.all()
            result = []
            
            for lock in locks:
                lock_info = {
                    'kind': lock.kind,
                    'task_id': lock.task_id,
                    'worker_id': getattr(lock, 'worker_id', 'unknown'),
                    'acquired_at': getattr(lock, 'acquired_at', None),
                    'expires_at': getattr(lock, 'expires_at', None)
                }
                result.append(lock_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting all locks: {e}")
            return []
    
    def _cleanup_expired_locks(self) -> int:
        """Clean up expired locks."""
        if not hasattr(TaskLock, 'expires_at'):
            return 0  # No TTL support
        
        try:
            with transaction.atomic():
                expired_locks = TaskLock.objects.filter(
                    expires_at__lte=timezone.now()
                )
                
                count = expired_locks.count()
                if count > 0:
                    expired_locks.delete()
                    logger.info(f"Cleaned up {count} expired locks")
                
                return count
                
        except Exception as e:
            logger.error(f"Error cleaning up expired locks: {e}")
            return 0
    
    def force_cleanup_worker_locks(self, worker_id: str) -> int:
        """Force cleanup all locks for a specific worker (for crash recovery)."""
        if not hasattr(TaskLock, 'worker_id'):
            return 0
        
        try:
            with transaction.atomic():
                worker_locks = TaskLock.objects.filter(worker_id=worker_id)
                count = worker_locks.count()
                
                if count > 0:
                    worker_locks.delete()
                    logger.warning(f"Force cleaned {count} locks for crashed worker: {worker_id}")
                
                return count
                
        except Exception as e:
            logger.error(f"Error force cleaning locks for worker {worker_id}: {e}")
            return 0


class Command(BaseCommand):
    """Django management command for lock cleanup."""
    
    help = 'Clean up expired task locks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--worker-id',
            type=str,
            help='Force cleanup locks for specific worker'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without actually doing it'
        )
    
    def handle(self, *args, **options):
        lock_manager = TaskLockManager()
        
        if options['worker_id']:
            # Force cleanup for specific worker
            worker_id = options['worker_id']
            
            if options['dry_run']:
                locks = lock_manager.get_locks_by_worker(worker_id)
                self.stdout.write(f"Would clean {len(locks)} locks for worker {worker_id}")
                for lock in locks:
                    self.stdout.write(f"  - {lock['kind']}:{lock['task_id']}")
            else:
                count = lock_manager.force_cleanup_worker_locks(worker_id)
                self.stdout.write(
                    self.style.WARNING(f"Force cleaned {count} locks for worker {worker_id}")
                )
        else:
            # Regular expired lock cleanup
            if options['dry_run']:
                all_locks = lock_manager.get_all_active_locks()
                expired_count = 0
                
                if hasattr(TaskLock, 'expires_at'):
                    now = timezone.now()
                    for lock in all_locks:
                        if lock['expires_at'] and lock['expires_at'] <= now:
                            expired_count += 1
                
                self.stdout.write(f"Would clean {expired_count} expired locks")
            else:
                count = lock_manager._cleanup_expired_locks()
                self.stdout.write(
                    self.style.SUCCESS(f"Cleaned {count} expired locks")
                )


# Global lock manager instance
_lock_manager = TaskLockManager()


def get_lock_manager() -> TaskLockManager:
    """Get the global lock manager instance."""
    return _lock_manager