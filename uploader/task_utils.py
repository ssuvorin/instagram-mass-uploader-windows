# -*- coding: utf-8 -*-
"""
Utility functions for bulk upload task management
"""

import time
import traceback
from django.utils import timezone
from .constants import TaskStatus, LogCategories
from .logging_utils import log_info, log_error, log_success, log_warning
from .models import BulkUploadTask, InstagramAccount, BulkUploadAccount


def update_task_log(task, log_message):
    """Update task log with new message"""
    if hasattr(task, 'log') and task.log:
        task.log += log_message
    else:
        task.log = log_message
    task.save()


def update_account_task(account_task, status=None, log_message=None, started_at=None, completed_at=None):
    """Update account task with new status and/or log message"""
    if status:
        account_task.status = status
    if log_message:
        if hasattr(account_task, 'log') and account_task.log:
            account_task.log += log_message
        else:
            account_task.log = log_message
    if started_at:
        # If string is passed, parse it to datetime with timezone
        if isinstance(started_at, str):
            account_task.started_at = timezone.now()
        else:
            account_task.started_at = started_at
    if completed_at:
        # If string is passed, parse it to datetime with timezone
        if isinstance(completed_at, str):
            account_task.completed_at = timezone.now()
        else:
            account_task.completed_at = completed_at
    # Optional counters if provided via kwargs for backward compatibility
    try:
        # Some callers may pass these as attributes on the function (kwargs not explicit here),
        # so fetch from a dict attached temporarily if present
        extra = getattr(update_account_task, "_extra_fields", None)
        if isinstance(extra, dict):
            if 'uploaded_success_count' in extra:
                account_task.uploaded_success_count = int(extra['uploaded_success_count'])
            if 'uploaded_failed_count' in extra:
                account_task.uploaded_failed_count = int(extra['uploaded_failed_count'])
            # reset after use
            setattr(update_account_task, "_extra_fields", None)
    except Exception:
        pass
    account_task.save()


def update_task_status(task, status, log_message):
    """Update main task status and log"""
    task.status = status
    update_task_log(task, log_message)


def get_account_username(account_task):
    """Get username from account task safely"""
    account = get_account_from_task(account_task)
    return getattr(account, 'username', getattr(account, 'email', 'Unknown')) if account else "Unknown"


def get_account_from_task(account_task):
    """Get Instagram account from account task"""
    return account_task.account


def mark_account_as_used(account):
    """Mark Instagram account as used"""
    account.last_used = timezone.now()
    account.save()


def get_task_with_accounts(task_id):
    """Get task with related accounts"""
    return BulkUploadTask.objects.prefetch_related('accounts__account').get(id=task_id)


def get_account_tasks(task):
    """Get all account tasks for a bulk upload task"""
    return task.accounts.all()


def get_assigned_videos(account_task):
    """Get videos assigned to an account task"""
    return account_task.assigned_videos.all()


def get_all_task_videos(task):
    """Get all videos for a task"""
    return task.videos.all()


def get_all_task_titles(task):
    """Get all video titles for a task"""
    return task.titles.all()


def handle_verification_error(account_task, account_details, error_type, error_message):
    """Handle phone or human verification errors"""
    timestamp_str = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Map error types to status
    status_map = {
        'PHONE': TaskStatus.PHONE_VERIFICATION_REQUIRED,
        'HUMAN': TaskStatus.HUMAN_VERIFICATION_REQUIRED,
        'SUSPENDED': TaskStatus.SUSPENDED
    }
    
    # Map error types to emoji and messages
    display_map = {
        'PHONE': ('[PHONE]', 'Phone verification required'),
        'HUMAN': ('[BOT]', 'Human verification required'),
        'SUSPENDED': ('[BLOCK]', 'Account suspended by Instagram')
    }
    
    status = status_map.get(error_type, TaskStatus.FAILED)
    emoji, display_message = display_map.get(error_type, ('[FAIL]', 'Verification required'))
    
    # Update account task
    update_account_task(
        account_task,
        status=status,
        completed_at=timezone.now(),
        log_message=f"[{timestamp_str}] {emoji} {error_message}\n"
    )
    
    # Update Instagram account status
    try:
        instagram_account = InstagramAccount.objects.get(username=account_details['username'])
        instagram_account.status = status
        instagram_account.save()
        log_info(f"Marked account {account_details['username']} as {status}", LogCategories.LOGIN)
    except InstagramAccount.DoesNotExist:
        log_error(f"Could not find Instagram account {account_details['username']} to update status", LogCategories.LOGIN)
    except Exception as status_error:
        log_error(f"Error updating account status: {str(status_error)}", LogCategories.LOGIN)
    
    log_error(f"{display_message}: {error_message}", LogCategories.LOGIN)
    return status, error_message


def handle_task_completion(task, completed_count, failed_count, total_count):
    """Handle final task status based on completion results"""
    timestamp_str = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if failed_count == 0 and completed_count == total_count:
        log_info(f"All uploads completed successfully! Task: {task.name}")
        update_task_status(task, TaskStatus.COMPLETED, f"[{timestamp_str}] [PARTY] All uploads completed successfully!\n")
        return TaskStatus.COMPLETED
    elif completed_count > 0:
        log_info(f"Some uploads completed. Completed: {completed_count}, Failed: {failed_count}")
        update_task_status(task, TaskStatus.PARTIALLY_COMPLETED,
                          f"[{timestamp_str}] [WARN] Some uploads completed. Completed: {completed_count}, Failed: {failed_count}\n")
        return TaskStatus.PARTIALLY_COMPLETED
    else:
        log_error(f"All uploads failed for task: {task.name}")
        update_task_status(task, TaskStatus.FAILED, f"[{timestamp_str}] [FAIL] All uploads failed\n")
        return TaskStatus.FAILED


def handle_emergency_cleanup(account_task, dolphin=None):
    """Handle emergency cleanup when browser operations fail"""
    timestamp_str = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    log_info("[EMERGENCY_CLEANUP] Browser thread timed out, attempting emergency cleanup...")
    
    try:
        # Try to stop Dolphin profile if we have the ID
        account = get_account_from_task(account_task)
        dolphin_profile_id = getattr(account, 'dolphin_profile_id', None)
        
        if dolphin_profile_id and dolphin:
            log_info(f"[EMERGENCY_CLEANUP] Stopping Dolphin profile: {dolphin_profile_id}")
            try:
                dolphin.stop_profile(dolphin_profile_id)
                log_info(f"[EMERGENCY_CLEANUP] [OK] Dolphin profile {dolphin_profile_id} stopped successfully")
            except Exception as e:
                log_warning(f"[EMERGENCY_CLEANUP] [WARN] Error stopping Dolphin profile: {str(e)}")
        else:
            log_warning(f"[EMERGENCY_CLEANUP] [WARN] Dolphin client not available for profile cleanup")
        
        log_info("[EMERGENCY_CLEANUP] Emergency cleanup completed")
        
    except Exception as emergency_cleanup_error:
        log_error(f"[EMERGENCY_CLEANUP] Emergency cleanup failed: {str(emergency_cleanup_error)}")
    
    # Update account task as failed
    update_account_task(
        account_task,
        status=TaskStatus.FAILED,
        completed_at=timezone.now(),
        log_message=f"[{timestamp_str}] [FAIL] Browser operation timed out or failed\n"
    )


def process_browser_result(result, account_task, task):
    """Process result from browser thread"""
    timestamp_str = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if isinstance(result, tuple) and len(result) == 2:
        status, message = result
        
        if status == "SUCCESS":
            log_info(f"Task completed successfully: {message}")
            update_account_task(
                account_task,
                status=TaskStatus.COMPLETED,
                completed_at=timezone.now(),
                log_message=f"[{timestamp_str}] [OK] {message}\n"
            )
            return 'completed', 1, 0
        
        elif status in ["PHONE_VERIFICATION_REQUIRED", "HUMAN_VERIFICATION_REQUIRED"]:
            emoji = '[PHONE]' if status == "PHONE_VERIFICATION_REQUIRED" else '[BOT]'
            update_account_task(
                account_task,
                status=status,
                completed_at=timezone.now(),
                log_message=f"[{timestamp_str}] {emoji} {message}\n"
            )
            
            # Update Instagram account status in database
            try:
                account = get_account_from_task(account_task)
                if account:
                    account.status = status
                    account.save(update_fields=['status'])
                    log_info(f"Updated Instagram account {account.username} status to {status}")
                else:
                    log_error("Could not get account from account_task to update status")
            except Exception as e:
                log_error(f"Error updating Instagram account status: {str(e)}")
            
            return 'verification_required', 0, 1
        
        elif status == "SUSPENDED":
            update_account_task(
                account_task,
                status=TaskStatus.SUSPENDED,
                completed_at=timezone.now(),
                log_message=f"[{timestamp_str}] [BLOCK] Account suspended by Instagram\n"
            )
            
            # Update Instagram account status in database
            try:
                account = get_account_from_task(account_task)
                if account:
                    account.status = TaskStatus.SUSPENDED
                    account.save(update_fields=['status'])
                    log_info(f"Updated Instagram account {account.username} status to SUSPENDED")
                else:
                    log_error("Could not get account from account_task to update status")
            except Exception as e:
                log_error(f"Error updating Instagram account status: {str(e)}")
            
            return 'suspended', 0, 1
    
    # Default case - failed
    update_account_task(
        account_task,
        status=TaskStatus.FAILED,
        completed_at=timezone.now(),
        log_message=f"[{timestamp_str}] [FAIL] Unknown error occurred\n"
    )
    return 'failed', 0, 1


# New helper: clear human verification badge after successful login
def clear_human_verification_badge(username: str) -> None:
    """Clear HUMAN_VERIFICATION_REQUIRED badge for the given Instagram account if present.
    Sets account status back to ACTIVE after a successful login.
    """
    try:
        account = InstagramAccount.objects.get(username=username)
        if account.status == 'HUMAN_VERIFICATION_REQUIRED':
            account.status = 'ACTIVE'
            account.save(update_fields=['status'])
            log_info(f"[DATABASE] Cleared human verification badge for {username}", LogCategories.LOGIN)
    except InstagramAccount.DoesNotExist:
        log_warning(f"[DATABASE] Instagram account {username} not found when clearing human verification", LogCategories.LOGIN)
    except Exception as e:
        log_warning(f"[DATABASE] Error clearing human verification for {username}: {str(e)}", LogCategories.LOGIN)


async def clear_human_verification_badge_async(username: str) -> None:
    """Async wrapper to clear HUMAN_VERIFICATION_REQUIRED badge without blocking the event loop."""
    try:
        from asgiref.sync import sync_to_async

        @sync_to_async
        def _fetch_account():
            try:
                return InstagramAccount.objects.get(username=username)
            except InstagramAccount.DoesNotExist:
                return None

        @sync_to_async
        def _save_active(account):
            account.status = 'ACTIVE'
            account.save(update_fields=['status'])

        account = await _fetch_account()
        if account is None:
            log_warning(f"[DATABASE] Instagram account {username} not found when clearing human verification", LogCategories.LOGIN)
            return
        if account.status == 'HUMAN_VERIFICATION_REQUIRED':
            await _save_active(account)
            log_info(f"[DATABASE] Cleared human verification badge for {username}", LogCategories.LOGIN)
    except Exception as e:
        log_warning(f"[DATABASE] Error clearing human verification for {username}: {str(e)}", LogCategories.LOGIN)


def handle_account_task_error(account_task, task, error):
    """Handle errors that occur during account task processing"""
    error_trace = traceback.format_exc()
    timestamp_str = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    
    log_error(f"Error processing account task: {str(error)}\n{error_trace}")
    update_account_task(
        account_task,
        status=TaskStatus.FAILED,
        completed_at=timezone.now(),
        log_message=f"[{timestamp_str}] [FAIL] Error: {str(error)}\n[{timestamp_str}] [FAIL] Traceback: {error_trace}\n"
    )
    
    # Get username safely and update task log
    try:
        username = get_account_username(account_task)
        log_error(f"Error processing account {username}: {str(error)}")
        update_task_log(task, f"[{timestamp_str}] [FAIL] Error processing account {username}: {str(error)}\n")
    except Exception:
        log_error(f"Error processing unnamed account: {str(error)}")
        update_task_log(task, f"[{timestamp_str}] [FAIL] Error processing account: {str(error)}\n")


def handle_critical_task_error(task, task_id, error):
    """Handle critical errors that affect the entire task"""
    error_trace = traceback.format_exc()
    timestamp_str = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    
    log_error(f"Critical error processing bulk upload task {task_id}: {str(error)}\n{error_trace}")
    update_task_status(task, TaskStatus.FAILED,
                      f"[{timestamp_str}] [FAIL] Critical error: {str(error)}\n[{timestamp_str}] [FAIL] Traceback: {error_trace}\n") 