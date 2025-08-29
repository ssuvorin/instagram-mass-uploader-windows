"""Auto-refactored module: runner"""
from .logging import logger

from .dolphin import run_dolphin_browser_async
from .utils_dom import get_account_details_async
from .utils_dom import get_assigned_videos_async
from .utils_dom import prepare_unique_videos_async
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


async def process_account_batch_async(account_tasks, task, batch_num):
    """Process a batch of accounts with controlled concurrency"""
    try:
        log_info(f"[RETRY] [BATCH_{batch_num}] Starting batch processing with {len(account_tasks)} accounts")
        
        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(PARALLEL_CONFIG['MAX_CONCURRENT_ACCOUNTS'])
        
        # Create tasks for all accounts in batch
        account_coroutines = []
        for account_task in account_tasks:
            coro = process_single_account_with_semaphore_async(
                semaphore, account_task, task, batch_num
            )
            account_coroutines.append(coro)
        
        # Execute all accounts concurrently with controlled concurrency
        log_info(f"⚡ [BATCH_{batch_num}] Executing {len(account_coroutines)} account tasks concurrently...")
        account_results = await asyncio.gather(*account_coroutines, return_exceptions=True)
        
        # Process results
        batch_results = {
            'successful': 0,
            'failed': 0,
            'phone_verification': 0,
            'human_verification': 0,
            'suspended': 0,
            'total_uploaded': 0,
            'total_failed_uploads': 0
        }
        
        for i, result in enumerate(account_results):
            if isinstance(result, Exception):
                log_info(f"[EXPLODE] [BATCH_{batch_num}] Account {i+1} failed with exception: {str(result)}")
                batch_results['failed'] += 1
            elif isinstance(result, tuple) and len(result) >= 3:
                status, uploaded, failed = result[0], result[1], result[2]
                
                if status == "SUCCESS":
                    batch_results['successful'] += 1
                    batch_results['total_uploaded'] += uploaded
                elif status == "PHONE_VERIFICATION_REQUIRED":
                    batch_results['phone_verification'] += 1
                elif status == "HUMAN_VERIFICATION_REQUIRED":
                    batch_results['human_verification'] += 1
                elif status == "SUSPENDED":
                    batch_results['suspended'] += 1
                else:
                    batch_results['failed'] += 1
                
                batch_results['total_failed_uploads'] += failed
            else:
                batch_results['failed'] += 1
        
        log_info(f"[OK] [BATCH_{batch_num}] Completed: {batch_results['successful']} successful, {batch_results['failed']} failed")
        return batch_results
        
    except Exception as e:
        log_info(f"[EXPLODE] [BATCH_{batch_num}] Batch processing error: {str(e)}")
        return {'failed': len(account_tasks)}

async def process_single_account_with_semaphore_async(semaphore, account_task, task, batch_num):
    """Process single account with semaphore for concurrency control"""
    async with semaphore:
        try:
            # Get account details
            account_details = await get_account_details_async(account_task.account_id)
            if not account_details:
                log_error(f"[FAIL] [BATCH_{batch_num}] Account {account_task.account_id} details not found")
                return ("ERROR", 0, 1)
            
            username = account_details['username']
            log_info(f"[TARGET] [BATCH_{batch_num}] Starting account: {username}")
            
            # Add random delay to avoid simultaneous starts
            start_delay = random.uniform(*PARALLEL_CONFIG['ACCOUNT_START_DELAY'])
            log_info(f"[WAIT] [BATCH_{batch_num}] Account {username} waiting {start_delay:.1f}s before start...")
            await asyncio.sleep(start_delay)
            
            # Get videos for this account
            videos = await get_assigned_videos_async(account_task.id)
            if not videos:
                log_warning(f"[WARN] [BATCH_{batch_num}] No videos assigned to account {username}")
                return ("SUCCESS", 0, 0)
            
            # Prepare uniquified videos
            video_files = await prepare_unique_videos_async(account_task, videos)
            if not video_files:
                log_error(f"[FAIL] [BATCH_{batch_num}] Failed to prepare videos for account {username}")
                return ("ERROR", 0, 1)
            
            # Process account with retries
            for attempt in range(1, PARALLEL_CONFIG['MAX_RETRIES_PER_ACCOUNT'] + 1):
                try:
                    log_info(f"[RETRY] [BATCH_{batch_num}] Account {username} attempt {attempt}/{PARALLEL_CONFIG['MAX_RETRIES_PER_ACCOUNT']}")
                    
                    result = await run_dolphin_browser_async(
                        account_details, videos, video_files, task.id, account_task.id
                    )
                    
                    # If successful or permanent failure, don't retry
                    if result[0] in ["SUCCESS", "SUSPENDED", "PHONE_VERIFICATION_REQUIRED", "HUMAN_VERIFICATION_REQUIRED"]:
                        log_info(f"[OK] [BATCH_{batch_num}] Account {username} completed: {result[0]}")
                        return result
                    
                    # If temporary failure and not last attempt, retry
                    if attempt < PARALLEL_CONFIG['MAX_RETRIES_PER_ACCOUNT']:
                        retry_delay = random.uniform(60, 120)  # 1-2 minutes between retries
                        log_warning(f"[WARN] [BATCH_{batch_num}] Account {username} failed, retrying in {retry_delay:.1f}s...")
                        await asyncio.sleep(retry_delay)
                    
                except Exception as e:
                    log_info(f"[EXPLODE] [BATCH_{batch_num}] Account {username} attempt {attempt} exception: {str(e)}")
                    if attempt >= PARALLEL_CONFIG['MAX_RETRIES_PER_ACCOUNT']:
                        return ("ERROR", 0, 1)
                    await asyncio.sleep(random.uniform(30, 60))
            
            # All retries exhausted
            log_error(f"[FAIL] [BATCH_{batch_num}] Account {username} failed after all retries")
            return ("ERROR", 0, 1)
            
        except Exception as e:
            log_info(f"[EXPLODE] [BATCH_{batch_num}] Critical error processing account: {str(e)}")
            return ("ERROR", 0, 1)

async def get_task_with_accounts_async(task_id):
    """Get task with associated accounts - async version"""
    try:
        from asgiref.sync import sync_to_async
        from uploader.models import BulkUploadTask, BulkUploadAccount
        
        @sync_to_async
        def get_task_data():
            try:
                task = BulkUploadTask.objects.get(id=task_id)
                account_tasks = list(BulkUploadAccount.objects.filter(task=task))
                return task, account_tasks
            except BulkUploadTask.DoesNotExist:
                return None
        
        return await get_task_data()
        
    except Exception as e:
        log_error(f"[FAIL] [DATABASE] Error getting task data: {str(e)}")
        return None

__all__ = ['process_account_batch_async', 'process_single_account_with_semaphore_async', 'get_task_with_accounts_async']


# === PASS 7 SAFE SHIMS RUNNER (non-breaking) ===
from .logging import logger
from .metrics import metrics
import inspect, asyncio
try:
    _orig_process_account_batch_async = process_account_batch_async
except Exception:
    _orig_process_account_batch_async = None
async def process_account_batch_async(*args, **kwargs):
    """Auto-wrapped RUNNER function. Behavior unchanged; adds logs and metrics."""
    logger.info('RUNNER:process_account_batch_async start')
    metrics.inc('RUNNER:process_account_batch_async:start')
    try:
        if _orig_process_account_batch_async is None:
            logger.warning('RUNNER:process_account_batch_async original missing; no-op')
            metrics.inc('RUNNER:process_account_batch_async:missing')
            return None
        if inspect.iscoroutinefunction(_orig_process_account_batch_async):
            res = await _orig_process_account_batch_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_process_account_batch_async(*args, **kwargs))
        logger.info('RUNNER:process_account_batch_async ok')
        metrics.inc('RUNNER:process_account_batch_async:ok')
        return res
    except Exception as e:
        logger.error('RUNNER:process_account_batch_async error: ' + repr(e))
        metrics.inc('RUNNER:process_account_batch_async:error')
        raise
try:
    _orig_process_single_account_with_semaphore_async = process_single_account_with_semaphore_async
except Exception:
    _orig_process_single_account_with_semaphore_async = None
async def process_single_account_with_semaphore_async(*args, **kwargs):
    """Auto-wrapped RUNNER function. Behavior unchanged; adds logs and metrics."""
    logger.info('RUNNER:process_single_account_with_semaphore_async start')
    metrics.inc('RUNNER:process_single_account_with_semaphore_async:start')
    try:
        if _orig_process_single_account_with_semaphore_async is None:
            logger.warning('RUNNER:process_single_account_with_semaphore_async original missing; no-op')
            metrics.inc('RUNNER:process_single_account_with_semaphore_async:missing')
            return None
        if inspect.iscoroutinefunction(_orig_process_single_account_with_semaphore_async):
            res = await _orig_process_single_account_with_semaphore_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_process_single_account_with_semaphore_async(*args, **kwargs))
        logger.info('RUNNER:process_single_account_with_semaphore_async ok')
        metrics.inc('RUNNER:process_single_account_with_semaphore_async:ok')
        return res
    except Exception as e:
        logger.error('RUNNER:process_single_account_with_semaphore_async error: ' + repr(e))
        metrics.inc('RUNNER:process_single_account_with_semaphore_async:error')
        raise
try:
    _orig_get_task_with_accounts_async = get_task_with_accounts_async
except Exception:
    _orig_get_task_with_accounts_async = None
async def get_task_with_accounts_async(*args, **kwargs):
    """Auto-wrapped RUNNER function. Behavior unchanged; adds logs and metrics."""
    logger.info('RUNNER:get_task_with_accounts_async start')
    metrics.inc('RUNNER:get_task_with_accounts_async:start')
    try:
        if _orig_get_task_with_accounts_async is None:
            logger.warning('RUNNER:get_task_with_accounts_async original missing; no-op')
            metrics.inc('RUNNER:get_task_with_accounts_async:missing')
            return None
        if inspect.iscoroutinefunction(_orig_get_task_with_accounts_async):
            res = await _orig_get_task_with_accounts_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_get_task_with_accounts_async(*args, **kwargs))
        logger.info('RUNNER:get_task_with_accounts_async ok')
        metrics.inc('RUNNER:get_task_with_accounts_async:ok')
        return res
    except Exception as e:
        logger.error('RUNNER:get_task_with_accounts_async error: ' + repr(e))
        metrics.inc('RUNNER:get_task_with_accounts_async:error')
        raise