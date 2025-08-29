"""
Enhanced Instagram Automation Runner for Worker Service

This module provides comprehensive Instagram automation capabilities using
all the copied modules from the main project, including full task execution,
human behavior simulation, and advanced error handling.
"""

from __future__ import annotations
import os
import time
import random
import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path

# Initialize Django for database access
from . import django_init

# Import Instagram automation modules
from .instagram_automation import (
    InstagramAutomationBase, InstagramNavigator, InstagramUploader, InstagramLoginHandler,
    perform_instagram_login_optimized, AdvancedHumanBehavior, init_human_behavior
)
from .instagram_automation.bulk_tasks_playwright import (
    run_dolphin_browser, prepare_video_files, handle_cookie_consent, handle_login_flow
)
from .instagram_automation.async_bulk_tasks import (
    run_bulk_upload_task_parallel_async, run_account_upload_with_metadata_async
)
from .instagram_automation.task_utils import (
    update_task_log, update_account_task, update_task_status, handle_verification_error,
    handle_task_completion, handle_emergency_cleanup
)
from .instagram_automation.account_utils import (
    get_account_details, get_proxy_details, get_account_proxy
)
from .instagram_automation.logging_utils import log_info, log_error, log_success, log_warning
from .instagram_automation.constants import TaskStatus, LogCategories
from .instagram_automation.async_video_uniquifier import AsyncVideoUniquifier
from .instagram_automation.human_behavior import init_human_behavior, get_human_behavior
from .instagram_automation.browser_support import cleanup_hanging_browser_processes

# Import bot classes for browser automation
from bot.src.instagram_uploader.browser_dolphin import get_browser, get_page, close_browser
from bot.src.instagram_uploader.auth_playwright import Auth
from bot.src.instagram_uploader.upload_playwright import Upload
from bot.src.instagram_uploader.dolphin_anty import DolphinAnty

# Import Django models
from uploader.models import (
    BulkUploadTask, InstagramAccount, BulkUploadAccount, VideoFile,
    WarmupTask, WarmupTaskAccount, BulkLoginTask, BulkLoginTaskAccount,
    AvatarTask, AvatarTaskAccount, BioTask, BioTaskAccount,
    FollowTask, FollowTaskAccount
)

from .config import settings
from .domain import BulkVideo, BulkUploadAccountTask
from .ui_client import UiClient


@dataclass
class TaskExecutionResult:
    """Result of task execution"""
    success_count: int
    failed_count: int
    stdout: str
    stderr: str
    status: str


class ComprehensiveInstagramRunner:
    """Comprehensive Instagram automation runner with full feature support"""
    
    def __init__(self):
        self.uniquifier = AsyncVideoUniquifier()
        
    async def execute_bulk_upload_task(
        self, 
        ui: UiClient, 
        task_id: int, 
        account_task: BulkUploadAccountTask, 
        videos: List[BulkVideo], 
        default_location: Optional[str] = None,
        default_mentions_text: Optional[str] = None,
        headless: bool = True,
        visible: bool = False
    ) -> TaskExecutionResult:
        """Execute bulk upload task with comprehensive automation"""
        
        log_info(f"[RUNNER] Starting comprehensive bulk upload for account: {account_task.account.username}")
        
        try:
            # Use the async parallel implementation from copied modules
            success, failed, stdout, stderr = await run_account_upload_with_metadata_async(
                ui=ui,
                task_id=task_id,
                account_task=account_task,
                videos=videos,
                default_location=default_location,
                default_mentions_text=default_mentions_text,
                headless=headless,
                visible=visible
            )
            
            # Determine final status
            if failed == 0 and success > 0:
                status = "COMPLETED"
            elif success > 0:
                status = "PARTIALLY_COMPLETED"  
            else:
                status = "FAILED"
                
            return TaskExecutionResult(
                success_count=success,
                failed_count=failed,
                stdout=stdout,
                stderr=stderr,
                status=status
            )
            
        except Exception as e:
            log_error(f"[RUNNER] Critical error in bulk upload execution: {str(e)}")
            await ui.update_account_status(account_task.account_task_id, "FAILED", 
                                         log_append=f"[CRITICAL] Execution failed: {str(e)}\n")
            
            return TaskExecutionResult(
                success_count=0,
                failed_count=len(videos),
                stdout="",
                stderr=str(e),
                status="FAILED"
            )
    
    async def execute_warmup_task(
        self,
        ui: UiClient,
        task_id: int,
        account_task_id: int,
        account_data: Dict[str, Any]
    ) -> TaskExecutionResult:
        """Execute Instagram account warmup task"""
        
        log_info(f"[RUNNER] Starting warmup for account: {account_data.get('username')}")
        
        try:
            # Get Django model for warmup task
            warmup_task = WarmupTask.objects.get(id=task_id)
            account_task = WarmupTaskAccount.objects.get(id=account_task_id)
            
            await ui.update_account_status(account_task_id, "RUNNING", 
                                         log_append=f"[START] Warmup for {account_data['username']}\n")
            
            # Use imported warmup functions from the main project
            from .instagram_automation.views_warmup import perform_warmup_actions
            
            result = await perform_warmup_actions(
                account_data=account_data,
                warmup_config={
                    'feed_scroll_count': random.randint(warmup_task.feed_scroll_min_count, warmup_task.feed_scroll_max_count),
                    'like_count': random.randint(warmup_task.like_min_count, warmup_task.like_max_count),
                    'story_view_count': random.randint(warmup_task.view_stories_min_count, warmup_task.view_stories_max_count),
                    'follow_count': random.randint(warmup_task.follow_min_count, warmup_task.follow_max_count),
                }
            )
            
            status = "COMPLETED" if result else "FAILED"
            await ui.update_account_status(account_task_id, status)
            
            return TaskExecutionResult(
                success_count=1 if result else 0,
                failed_count=0 if result else 1,
                stdout=f"Warmup {'successful' if result else 'failed'}",
                stderr="",
                status=status
            )
            
        except Exception as e:
            log_error(f"[RUNNER] Warmup execution failed: {str(e)}")
            await ui.update_account_status(account_task_id, "FAILED", 
                                         log_append=f"[FAIL] Warmup error: {str(e)}\n")
            
            return TaskExecutionResult(
                success_count=0,
                failed_count=1,
                stdout="",
                stderr=str(e),
                status="FAILED"
            )
    
    async def execute_login_task(
        self,
        ui: UiClient,
        task_id: int,
        account_task_id: int,
        account_data: Dict[str, Any]
    ) -> TaskExecutionResult:
        """Execute Instagram login task"""
        
        log_info(f"[RUNNER] Starting login for account: {account_data.get('username')}")
        
        try:
            # Get Django model
            login_task = BulkLoginTask.objects.get(id=task_id)
            account_task = BulkLoginTaskAccount.objects.get(id=account_task_id)
            
            await ui.update_account_status(account_task_id, "RUNNING", 
                                         log_append=f"[START] Login for {account_data['username']}\n")
            
            # Initialize browser and perform login
            proxy_data = account_data.get('proxy')
            browser = get_browser(
                headless=True,
                proxy=proxy_data,
                api_token=settings.dolphin_api_token,
                profile_id=account_data.get('dolphin_profile_id')
            )
            
            if not browser:
                raise Exception("Failed to initialize browser")
            
            page = get_page(browser)
            if not page:
                raise Exception("Failed to get browser page")
            
            try:
                # Navigate to Instagram
                await page.goto("https://www.instagram.com/")
                
                # Handle cookie consent
                handle_cookie_consent(page)
                
                # Perform login using copied modules
                login_result = perform_instagram_login_optimized(page, account_data)
                
                if login_result is True:
                    await ui.update_account_status(account_task_id, "COMPLETED", 
                                                 log_append=f"[SUCCESS] Login successful\n")
                    status = "COMPLETED"
                    success = 1
                    failed = 0
                elif login_result == "SUSPENDED":
                    await ui.update_account_status(account_task_id, "FAILED", 
                                                 log_append=f"[SUSPENDED] Account suspended\n")
                    status = "FAILED"
                    success = 0
                    failed = 1
                else:
                    await ui.update_account_status(account_task_id, "FAILED", 
                                                 log_append=f"[FAIL] Login failed\n")
                    status = "FAILED"
                    success = 0
                    failed = 1
                
            finally:
                close_browser(browser)
            
            return TaskExecutionResult(
                success_count=success,
                failed_count=failed,
                stdout=f"Login {'successful' if success else 'failed'}",
                stderr="",
                status=status
            )
            
        except Exception as e:
            log_error(f"[RUNNER] Login execution failed: {str(e)}")
            await ui.update_account_status(account_task_id, "FAILED", 
                                         log_append=f"[FAIL] Login error: {str(e)}\n")
            
            return TaskExecutionResult(
                success_count=0,
                failed_count=1,
                stdout="",
                stderr=str(e),
                status="FAILED"
            )
    
    async def execute_avatar_task(
        self,
        ui: UiClient,
        task_id: int,
        account_task_id: int,
        account_data: Dict[str, Any]
    ) -> TaskExecutionResult:
        """Execute avatar update task"""
        
        log_info(f"[RUNNER] Starting avatar update for account: {account_data.get('username')}")
        
        try:
            # Get Django models
            avatar_task = AvatarTask.objects.get(id=task_id)
            account_task = AvatarTaskAccount.objects.get(id=account_task_id)
            
            await ui.update_account_status(account_task_id, "RUNNING", 
                                         log_append=f"[START] Avatar update for {account_data['username']}\n")
            
            # Download avatar image
            avatar_file_path = await ui.download_avatar_image(avatar_task.image.id)
            
            # Use avatar automation from copied modules
            from .instagram_automation.views_avatar import perform_avatar_update
            
            result = await perform_avatar_update(
                account_data=account_data,
                avatar_file_path=avatar_file_path
            )
            
            status = "COMPLETED" if result else "FAILED"
            await ui.update_account_status(account_task_id, status)
            
            return TaskExecutionResult(
                success_count=1 if result else 0,
                failed_count=0 if result else 1,
                stdout=f"Avatar update {'successful' if result else 'failed'}",
                stderr="",
                status=status
            )
            
        except Exception as e:
            log_error(f"[RUNNER] Avatar update failed: {str(e)}")
            await ui.update_account_status(account_task_id, "FAILED", 
                                         log_append=f"[FAIL] Avatar error: {str(e)}\n")
            
            return TaskExecutionResult(
                success_count=0,
                failed_count=1,
                stdout="",
                stderr=str(e),
                status="FAILED"
            )
    
    async def execute_bio_task(
        self,
        ui: UiClient,
        task_id: int,
        account_task_id: int,
        account_data: Dict[str, Any]
    ) -> TaskExecutionResult:
        """Execute bio update task"""
        
        log_info(f"[RUNNER] Starting bio update for account: {account_data.get('username')}")
        
        try:
            # Get Django models  
            bio_task = BioTask.objects.get(id=task_id)
            account_task = BioTaskAccount.objects.get(id=account_task_id)
            
            await ui.update_account_status(account_task_id, "RUNNING", 
                                         log_append=f"[START] Bio update for {account_data['username']}\n")
            
            # Use bio automation from copied modules
            from .instagram_automation.views_bio import perform_bio_update
            
            result = await perform_bio_update(
                account_data=account_data,
                bio_text=bio_task.bio_text
            )
            
            status = "COMPLETED" if result else "FAILED"
            await ui.update_account_status(account_task_id, status)
            
            return TaskExecutionResult(
                success_count=1 if result else 0,
                failed_count=0 if result else 1,
                stdout=f"Bio update {'successful' if result else 'failed'}",
                stderr="",
                status=status
            )
            
        except Exception as e:
            log_error(f"[RUNNER] Bio update failed: {str(e)}")
            await ui.update_account_status(account_task_id, "FAILED", 
                                         log_append=f"[FAIL] Bio error: {str(e)}\n")
            
            return TaskExecutionResult(
                success_count=0,
                failed_count=1,
                stdout="",
                stderr=str(e),
                status="FAILED"
            )
    
    async def execute_follow_task(
        self,
        ui: UiClient,
        task_id: int,
        account_task_id: int,
        account_data: Dict[str, Any]
    ) -> TaskExecutionResult:
        """Execute follow task"""
        
        log_info(f"[RUNNER] Starting follow task for account: {account_data.get('username')}")
        
        try:
            # Get Django models
            follow_task = FollowTask.objects.get(id=task_id)
            account_task = FollowTaskAccount.objects.get(id=account_task_id)
            
            await ui.update_account_status(account_task_id, "RUNNING", 
                                         log_append=f"[START] Follow task for {account_data['username']}\n")
            
            # Use follow automation from copied modules
            from .instagram_automation.views_follow import perform_follow_actions
            
            result = await perform_follow_actions(
                account_data=account_data,
                follow_config={
                    'follow_count': random.randint(follow_task.follow_min_count, follow_task.follow_max_count),
                    'category': follow_task.category,
                    'delay_range': [follow_task.delay_min_sec, follow_task.delay_max_sec]
                }
            )
            
            status = "COMPLETED" if result else "FAILED"
            await ui.update_account_status(account_task_id, status)
            
            return TaskExecutionResult(
                success_count=1 if result else 0,
                failed_count=0 if result else 1,
                stdout=f"Follow task {'successful' if result else 'failed'}",
                stderr="",
                status=status
            )
            
        except Exception as e:
            log_error(f"[RUNNER] Follow task failed: {str(e)}")
            await ui.update_account_status(account_task_id, "FAILED", 
                                         log_append=f"[FAIL] Follow error: {str(e)}\n")
            
            return TaskExecutionResult(
                success_count=0,
                failed_count=1,
                stdout="",
                stderr=str(e),
                status="FAILED"
            )
    
    async def cleanup_browser_processes(self):
        """Clean up hanging browser processes"""
        try:
            cleanup_hanging_browser_processes()
            log_info("[RUNNER] Browser cleanup completed")
        except Exception as e:
            log_warning(f"[RUNNER] Browser cleanup warning: {str(e)}")


# Create singleton instance
instagram_runner = ComprehensiveInstagramRunner()