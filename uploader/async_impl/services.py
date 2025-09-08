"""Auto-refactored module: services"""
from .logging import logger

from .human import init_human_behavior_async
from .login import check_post_login_verifications_async
from .login import handle_login_flow_async
from .utils_dom import handle_cookie_consent_async
from .utils_dom import log_video_info_async
from .utils_dom import retry_navigation_async
import os
import asyncio
import time
import traceback
import logging
import random
import math
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional, Callable, Awaitable
from pathlib import Path
import aiohttp
from ..constants import (
    TimeConstants, InstagramTexts, BrowserConfig, Limits, TaskStatus, LogCategories, FilePaths,
    VerboseFilters, InstagramSelectors, APIConstants
)
from ..selectors_config import InstagramSelectors as SelectorConfig, SelectorUtils
from ..task_utils import (
    update_task_log, update_account_task, update_task_status, get_account_username,
    get_account_from_task, mark_account_as_used, get_task_with_accounts, 
    get_account_tasks, get_assigned_videos, get_all_task_videos, get_all_task_titles,
    handle_verification_error, handle_task_completion, handle_emergency_cleanup,
    process_browser_result, handle_account_task_error, handle_critical_task_error
)
from ..account_utils import (
    get_account_details, get_proxy_details, get_account_proxy,
    get_account_dolphin_profile_id, save_dolphin_profile_id
)
from ..browser_support import (
    cleanup_hanging_browser_processes, safely_close_all_windows,
    simulate_human_rest_behavior, simulate_normal_browsing_behavior,
    simulate_extended_human_rest_behavior
)
from ..instagram_automation import InstagramNavigator, InstagramUploader, InstagramLoginHandler
from ..browser_utils import BrowserManager, PageUtils, ErrorHandler, NetworkUtils, FileUtils, DebugUtils
from ..crop_handler import CropHandler, handle_crop_and_aspect_ratio
from ..logging_utils import log_info, log_error, log_debug, log_warning
from ..human_behavior import AdvancedHumanBehavior, init_human_behavior, get_human_behavior
from ..captcha_solver import solve_recaptcha_if_present, detect_recaptcha_on_page, solve_recaptcha_if_present_sync
from ..email_verification_async import (
    get_email_verification_code_async,
    get_2fa_code_async,
    determine_verification_type_async
)
import django
from ..models import InstagramAccount, BulkUploadAccount


async def update_account_status_async(username: str, status: str, account_task_id: int):
    """Update account status in database - async version"""
    try:
        from asgiref.sync import sync_to_async
        from uploader.models import InstagramAccount, BulkUploadAccount
        
        log_info(f"💾 [ASYNC_DATABASE] Updating account {username} status to {status}")
        
        # Update Instagram account status
        @sync_to_async
        def update_instagram_account():
            try:
                instagram_account = InstagramAccount.objects.get(username=username)
                instagram_account.status = status
                instagram_account.save(update_fields=['status'])
                return True
            except InstagramAccount.DoesNotExist:
                log_info(f"💾 [ASYNC_DATABASE] Instagram account {username} not found")
                return False
        
        # Update BulkUploadAccount status for dashboard display
        @sync_to_async  
        def update_bulk_account():
            try:
                bulk_account = BulkUploadAccount.objects.get(id=account_task_id)
                bulk_account.status = status
                bulk_account.save(update_fields=['status'])
                return True
            except BulkUploadAccount.DoesNotExist:
                log_info(f"💾 [ASYNC_DATABASE] BulkUploadAccount with ID {account_task_id} not found")
                return False
        
        # Execute both updates
        instagram_updated = await update_instagram_account()
        bulk_updated = await update_bulk_account()
        
        if instagram_updated:
            log_info(f"💾 [ASYNC_DATABASE] Updated Instagram account {username} status to {status}")
        if bulk_updated:
            log_info(f"💾 [ASYNC_DATABASE] Updated bulk account task {account_task_id} status to {status}")
            
    except Exception as db_error:
        log_info(f"💾 [ASYNC_DATABASE_ERROR] Failed to update account status: {str(db_error)}")

async def perform_instagram_operations_async(page, account_details: Dict, videos: List, video_files_to_upload: List[str]) -> bool:
    """Perform Instagram operations with enhanced error handling and monitoring - async version"""
    try:
        log_info("[SEARCH] [ASYNC_NAVIGATION] Starting Instagram navigation with retry mechanism")
        
        # Use retry mechanism for navigation (ensure Accept-Language already set by browser layer)
        navigation_success = await retry_navigation_async(page, "https://www.instagram.com/", max_attempts=3)
        
        if not navigation_success:
            log_info("[FAIL] [ASYNC_NAVIGATION] Failed to navigate to Instagram.com after all retry attempts")
            return False
        
        log_info("[OK] [ASYNC_NAVIGATION] Successfully loaded Instagram.com")
        
        # Initialize human behavior after page is fully loaded
        await init_human_behavior_async(page)
        log_info("Human behavior initialized")
        
        # Handle cookie consent modal before login
        await handle_cookie_consent_async(page)
        
        # Check login status and login if needed
        if not await handle_login_flow_async(page, account_details):
            return False
        
        # ВАЖНО: Проверяем статусы аккаунта после логина
        log_info("[SEARCH] [ASYNC_VERIFICATION] Checking account status after login...")
        try:
            await check_post_login_verifications_async(page, account_details)
            log_info("[OK] [ASYNC_VERIFICATION] Account status check completed - no issues detected")
        except Exception as verification_error:
            error_message = str(verification_error)
            log_error(f"[FAIL] [ASYNC_VERIFICATION] Account status issue detected: {error_message}")
            
            # Перебрасываем исключения для верификации и блокировок
            if ("PHONE_VERIFICATION_REQUIRED:" in error_message or 
                "HUMAN_VERIFICATION_REQUIRED:" in error_message or 
                "SUSPENDED:" in error_message):
                raise verification_error
            else:
                log_warning(f"[WARN] [ASYNC_VERIFICATION] Non-critical verification error: {error_message}")
        
        # Upload videos
        uploaded_videos = 0
        
        # ENHANCED: Verify that we have matching lists
        if len(videos) != len(video_files_to_upload):
            log_info(f"[ASYNC_UPLOAD] [WARN] Mismatch: {len(videos)} videos vs {len(video_files_to_upload)} files")
            log_info(f"[ASYNC_UPLOAD] [SEARCH] Videos: {[getattr(v, 'video_file', 'NO_FILE').name if hasattr(v, 'video_file') else 'NO_ATTR' for v in videos]}")
            log_info(f"[ASYNC_UPLOAD] [SEARCH] Files: {[os.path.basename(f) for f in video_files_to_upload]}")
        
        for i, video_file_path in enumerate(video_files_to_upload, 1):
            try:
                # ENHANCED: Safe access to video object
                if i <= len(videos):
                    video_obj = videos[i-1]
                else:
                    log_info(f"[ASYNC_UPLOAD] [WARN] No video object for file {i}, using None")
                    video_obj = None
                
                # Log upload info
                await log_video_info_async(i, len(video_files_to_upload), video_file_path, video_obj)
                
                # Navigate to upload page
                # Lazy import to avoid circular dependency with .upload
                from .upload import navigate_to_upload_with_human_behavior_async as _navigate_to_upload_with_human_behavior_async
                if not await _navigate_to_upload_with_human_behavior_async(page, account_details):
                    log_info(f"[ASYNC_FAIL] Could not navigate to upload page for video {i}")
                    continue
                
                # Upload video
                from .upload import upload_video_with_human_behavior_async as _upload_video_with_human_behavior_async
                if await _upload_video_with_human_behavior_async(page, video_file_path, video_obj):
                    uploaded_videos += 1
                    log_info(f"[ASYNC_SUCCESS] Video {i}/{len(video_files_to_upload)} uploaded successfully")
                    if video_obj and hasattr(video_obj, 'uploaded'):
                        video_obj.uploaded = True
                else:
                    log_info(f"[ASYNC_FAIL] Failed to upload video {i}/{len(video_files_to_upload)}")
                
                # Human delay between uploads
                if i < len(video_files_to_upload):
                    from .upload import add_human_delay_between_uploads_async as _add_human_delay_between_uploads_async
                    await _add_human_delay_between_uploads_async(page, i)
                    
            except Exception as e:
                log_info(f"[ASYNC_FAIL] Error uploading video {i}: {str(e)}")
                import traceback
                log_info(f"[ASYNC_FAIL] [SEARCH] Traceback: {traceback.format_exc()}")
                continue
        
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Навигация только после подтверждения успешной загрузки
        if uploaded_videos > 0:
            log_info(f"[ASYNC_SUCCESS] [OK] {uploaded_videos} videos uploaded successfully, performing cleanup")
            # Final cleanup только после успешной загрузки
            await perform_final_cleanup_async(page, account_details['username'])
        else:
            log_info(f"[ASYNC_FAIL] [FAIL] No videos were uploaded, skipping cleanup to preserve upload state")
        
        return uploaded_videos  # ← Возвращаем количество загруженных видео вместо True/False
        
    except Exception as e:
        error_message = str(e)
        # Re-raise verification-related exceptions
        if "PHONE_VERIFICATION_REQUIRED" in error_message:
            log_info(f"Phone verification required: {error_message}")
            raise e  # Re-raise to be caught by run_dolphin_browser_async
        elif "HUMAN_VERIFICATION_REQUIRED" in error_message:
            log_info(f"Human verification required: {error_message}")
            raise e  # Re-raise to be caught by run_dolphin_browser_async
        elif "SUSPENDED" in error_message:
            log_info(f"Account suspended: {error_message}")
            raise e  # Re-raise to be caught by run_dolphin_browser_async
        else:
            log_info(f"Error in Instagram operations: {error_message}")
            return False

async def perform_final_cleanup_async(page, username):
    """Perform final cleanup after operations - async version"""
    try:
        log_info(f"[ASYNC_CLEANUP] Performing final cleanup for account: {username}")
        
        # Navigate to home page to clear any upload state
        try:
            await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(random.uniform(2, 4))
            log_info("[ASYNC_CLEANUP] [OK] Navigated to home page")
        except Exception as nav_error:
            log_info(f"[ASYNC_CLEANUP] Navigation error: {str(nav_error)}")
        
        # Clear any temporary state
        try:
            await page.evaluate("localStorage.clear(); sessionStorage.clear();")
            log_info("[ASYNC_CLEANUP] [OK] Cleared browser storage")
        except Exception as storage_error:
            log_info(f"[ASYNC_CLEANUP] Storage cleanup error: {str(storage_error)}")
        
    except Exception as e:
        log_info(f"[ASYNC_CLEANUP] Final cleanup error: {str(e)}")

async def update_task_status_async(task_id, status, results=None):
    """Update task status - async version"""
    try:
        from asgiref.sync import sync_to_async
        from uploader.models import BulkUploadTask
        
        @sync_to_async
        def update_task():
            try:
                task = BulkUploadTask.objects.get(id=task_id)
                task.status = status
                if results:
                    task.results = results
                task.save()
                return True
            except:
                return False
        
        return await update_task()
        
    except Exception as e:
        log_error(f"[FAIL] [DATABASE] Error updating task status: {str(e)}")
        return False

async def update_account_last_used_async(username: str):
    """Update account last_used timestamp - async version"""
    try:
        from asgiref.sync import sync_to_async
        from django.utils import timezone
        from uploader.models import InstagramAccount
        
        @sync_to_async(thread_sensitive=False)
        def update_last_used():
            from django.db import connections
            try:
                account = InstagramAccount.objects.get(username=username)
                account.last_used = timezone.now()
                account.save(update_fields=['last_used'])
                return True
            except InstagramAccount.DoesNotExist:
                log_error(f"[FAIL] [DATABASE] Account not found: {username}")
                return False
            except Exception as e:
                # retry once with connection refresh
                try:
                    for conn in connections.all():
                        if conn.connection is not None:
                            conn.close_if_unusable_or_obsolete()
                            conn.close()
                    account = InstagramAccount.objects.get(username=username)
                    account.last_used = timezone.now()
                    account.save(update_fields=['last_used'])
                    return True
                except Exception as e2:
                    log_error(f"[FAIL] [DATABASE] Error updating last_used after retry: {str(e2)}")
                    return False
        
        return await update_last_used()
        
    except Exception as e:
        log_error(f"[FAIL] [DATABASE] Error in update_account_last_used_async: {str(e)}")
        return False

__all__ = ['update_account_status_async', 'perform_instagram_operations_async', 'perform_final_cleanup_async', 'update_task_status_async', 'update_account_last_used_async']


# === PASS 7 SAFE SHIMS SERVICES (non-breaking) ===
from .logging import logger
from .metrics import metrics
import inspect, asyncio
try:
    _orig_update_account_status_async = update_account_status_async
except Exception:
    _orig_update_account_status_async = None
async def update_account_status_async(*args, **kwargs):
    """Auto-wrapped SERVICES function. Behavior unchanged; adds logs and metrics."""
    logger.info('SERVICES:update_account_status_async start')
    metrics.inc('SERVICES:update_account_status_async:start')
    try:
        if _orig_update_account_status_async is None:
            logger.warning('SERVICES:update_account_status_async original missing; no-op')
            metrics.inc('SERVICES:update_account_status_async:missing')
            return None
        if inspect.iscoroutinefunction(_orig_update_account_status_async):
            res = await _orig_update_account_status_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_update_account_status_async(*args, **kwargs))
        logger.info('SERVICES:update_account_status_async ok')
        metrics.inc('SERVICES:update_account_status_async:ok')
        return res
    except Exception as e:
        logger.error('SERVICES:update_account_status_async error: ' + repr(e))
        metrics.inc('SERVICES:update_account_status_async:error')
        raise
try:
    _orig_perform_instagram_operations_async = perform_instagram_operations_async
except Exception:
    _orig_perform_instagram_operations_async = None
async def perform_instagram_operations_async(*args, **kwargs):
    """Auto-wrapped SERVICES function. Behavior unchanged; adds logs and metrics."""
    logger.info('SERVICES:perform_instagram_operations_async start')
    metrics.inc('SERVICES:perform_instagram_operations_async:start')
    try:
        if _orig_perform_instagram_operations_async is None:
            logger.warning('SERVICES:perform_instagram_operations_async original missing; no-op')
            metrics.inc('SERVICES:perform_instagram_operations_async:missing')
            return None
        if inspect.iscoroutinefunction(_orig_perform_instagram_operations_async):
            res = await _orig_perform_instagram_operations_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_perform_instagram_operations_async(*args, **kwargs))
        logger.info('SERVICES:perform_instagram_operations_async ok')
        metrics.inc('SERVICES:perform_instagram_operations_async:ok')
        return res
    except Exception as e:
        logger.error('SERVICES:perform_instagram_operations_async error: ' + repr(e))
        metrics.inc('SERVICES:perform_instagram_operations_async:error')
        raise
try:
    _orig_perform_final_cleanup_async = perform_final_cleanup_async
except Exception:
    _orig_perform_final_cleanup_async = None
async def perform_final_cleanup_async(*args, **kwargs):
    """Auto-wrapped SERVICES function. Behavior unchanged; adds logs and metrics."""
    logger.info('SERVICES:perform_final_cleanup_async start')
    metrics.inc('SERVICES:perform_final_cleanup_async:start')
    try:
        if _orig_perform_final_cleanup_async is None:
            logger.warning('SERVICES:perform_final_cleanup_async original missing; no-op')
            metrics.inc('SERVICES:perform_final_cleanup_async:missing')
            return None
        if inspect.iscoroutinefunction(_orig_perform_final_cleanup_async):
            res = await _orig_perform_final_cleanup_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_perform_final_cleanup_async(*args, **kwargs))
        logger.info('SERVICES:perform_final_cleanup_async ok')
        metrics.inc('SERVICES:perform_final_cleanup_async:ok')
        return res
    except Exception as e:
        logger.error('SERVICES:perform_final_cleanup_async error: ' + repr(e))
        metrics.inc('SERVICES:perform_final_cleanup_async:error')
        raise
try:
    _orig_update_task_status_async = update_task_status_async
except Exception:
    _orig_update_task_status_async = None
async def update_task_status_async(*args, **kwargs):
    """Auto-wrapped SERVICES function. Behavior unchanged; adds logs and metrics."""
    logger.info('SERVICES:update_task_status_async start')
    metrics.inc('SERVICES:update_task_status_async:start')
    try:
        if _orig_update_task_status_async is None:
            logger.warning('SERVICES:update_task_status_async original missing; no-op')
            metrics.inc('SERVICES:update_task_status_async:missing')
            return None
        if inspect.iscoroutinefunction(_orig_update_task_status_async):
            res = await _orig_update_task_status_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_update_task_status_async(*args, **kwargs))
        logger.info('SERVICES:update_task_status_async ok')
        metrics.inc('SERVICES:update_task_status_async:ok')
        return res
    except Exception as e:
        logger.error('SERVICES:update_task_status_async error: ' + repr(e))
        metrics.inc('SERVICES:update_task_status_async:error')
        raise
try:
    _orig_update_account_last_used_async = update_account_last_used_async
except Exception:
    _orig_update_account_last_used_async = None
async def update_account_last_used_async(*args, **kwargs):
    """Auto-wrapped SERVICES function. Behavior unchanged; adds logs and metrics."""
    logger.info('SERVICES:update_account_last_used_async start')
    metrics.inc('SERVICES:update_account_last_used_async:start')
    try:
        if _orig_update_account_last_used_async is None:
            logger.warning('SERVICES:update_account_last_used_async original missing; no-op')
            metrics.inc('SERVICES:update_account_last_used_async:missing')
            return None
        if inspect.iscoroutinefunction(_orig_update_account_last_used_async):
            res = await _orig_update_account_last_used_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_update_account_last_used_async(*args, **kwargs))
        logger.info('SERVICES:update_account_last_used_async ok')
        metrics.inc('SERVICES:update_account_last_used_async:ok')
        return res
    except Exception as e:
        logger.error('SERVICES:update_account_last_used_async error: ' + repr(e))
        metrics.inc('SERVICES:update_account_last_used_async:error')
        raise