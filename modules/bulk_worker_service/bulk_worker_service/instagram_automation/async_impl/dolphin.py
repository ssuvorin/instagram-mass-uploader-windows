"""Auto-refactored module: dolphin"""
from .logging import logger

from .services import perform_instagram_operations_async
from .services import update_account_last_used_async
from .services import update_account_status_async
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


async def run_dolphin_browser_async(account_details: Dict, videos: List, video_files_to_upload: List[str],
                                   task_id, account_task_id):
    """Run browser automation for Instagram - exact copy of sync version with proper error handling"""
    dolphin = None
    dolphin_browser = None
    page = None
    dolphin_profile_id = None
    # Preserve upload UI state when no videos were uploaded (to allow manual recovery)
    preserve_state = False
    
    try:
        username = account_details['username']
        log_info(f"🐬 [ASYNC_DOLPHIN_START] Starting Dolphin Anty browser for account: {username}")
        
        # Pre-flight checks
        if not video_files_to_upload:
            error_msg = "No video files provided for upload"
            log_error(f"[FAIL] [ASYNC_DOLPHIN_ERROR] {error_msg}")
            return ("ERROR", 0, 1)
        
        # Initialize Dolphin with enhanced error handling
        dolphin_token = os.environ.get("DOLPHIN_API_TOKEN")
        if not dolphin_token:
            error_msg = "No Dolphin API token found in environment variables"
            log_error(f"[FAIL] [ASYNC_DOLPHIN_ERROR] {error_msg}")
            return ("DOLPHIN_ERROR", 0, 1)
        
        from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
        
        # Get Dolphin API host from environment (critical for Docker Windows deployment)
        dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
        if not dolphin_api_host.endswith("/v1.0"):
            dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
        
        log_info(f"🐬 [ASYNC_DOLPHIN_CONFIG] Using Dolphin API host: {dolphin_api_host}")
        
        dolphin = DolphinAnty(api_key=dolphin_token, local_api_base=dolphin_api_host)
        
        # Enhanced authentication with retry logic
        log_info(f"🔐 [ASYNC_DOLPHIN_AUTH] Authenticating with Dolphin Anty API...")
        auth_attempts = 0
        max_auth_attempts = 3
        
        while auth_attempts < max_auth_attempts:
            if await authenticate_dolphin_async(dolphin):
                log_info(f"[OK] [ASYNC_DOLPHIN_AUTH] Authentication successful on attempt {auth_attempts + 1}")
                break
            else:
                auth_attempts += 1
                if auth_attempts < max_auth_attempts:
                    log_warning(f"[WARN] [ASYNC_DOLPHIN_AUTH] Authentication failed, retrying... (attempt {auth_attempts}/{max_auth_attempts})")
                    await asyncio.sleep(random.uniform(2, 5))
                else:
                    error_msg = "Failed to authenticate with Dolphin Anty API after multiple attempts"
                    log_error(f"[FAIL] [ASYNC_DOLPHIN_AUTH] {error_msg}")
                    return ("DOLPHIN_ERROR", 0, 1)
        
        # Get profile with validation
        log_info(f"[CLIPBOARD] [ASYNC_DOLPHIN_PROFILE] Retrieving Dolphin profile for account: {username}")
        dolphin_profile_id = await get_dolphin_profile_id_async(username)
        if not dolphin_profile_id:
            error_msg = f"No Dolphin profile found for account: {username}"
            log_error(f"[FAIL] [ASYNC_DOLPHIN_PROFILE] {error_msg}")
            return ("PROFILE_ERROR", 0, 1)
        
        log_info(f"🔗 [ASYNC_DOLPHIN_PROFILE] Found profile ID: {dolphin_profile_id}")
        
        # Connect to browser profile
        log_info("🌐 [ASYNC_DOLPHIN_BROWSER] Connecting to browser profile...")
        dolphin_browser = AsyncDolphinBrowser(dolphin_token)
        page = await dolphin_browser.connect_to_profile_async(dolphin_profile_id, headless=False)
        
        if not page:
            error_msg = "Failed to connect to browser profile"
            log_error(f"[FAIL] [ASYNC_DOLPHIN_BROWSER] {error_msg}")
            return ("BROWSER_ERROR", 0, 1)
        
        log_info("[OK] [ASYNC_DOLPHIN_BROWSER] Successfully connected to profile: " + str(dolphin_profile_id))
        
        # Perform Instagram operations
        log_debug(f"[SEARCH] [ASYNC_INSTAGRAM_PREP] Preparing Instagram operations for {len(videos)} videos")
        result = await perform_instagram_operations_async(page, account_details, videos, video_files_to_upload)
        
        # IMPORTANT: result is an int (uploaded_videos) or False on hard error
        if result is not False:
            uploaded_count = int(result)
            failed_count = len(videos) - uploaded_count
            
            if uploaded_count > 0:
                preserve_state = False
                log_info(f"[OK] [ASYNC_SUCCESS] Successfully uploaded {uploaded_count}/{len(videos)} videos")
                
                # ENHANCED: Update last_used for successful uploads
                try:
                    await update_account_last_used_async(username)
                    log_info(f"[OK] [ASYNC_SUCCESS] Updated last_used for account: {username}")
                except Exception as last_used_error:
                    log_warning(f"[WARN] [ASYNC_SUCCESS] Failed to update last_used: {str(last_used_error)}")
                
                return ("SUCCESS", uploaded_count, failed_count)
            else:
                # No videos uploaded -> by default do NOT preserve UI state; can override via env
                preserve_state = os.environ.get("PRESERVE_BROWSER_ON_FAIL", "0").lower() in ("1", "true", "yes", "y")
                log_error(f"[FAIL] [ASYNC_FAIL] No videos were uploaded despite successful operations")
                return ("ERROR", 0, len(videos))
        else:
            log_error(f"[FAIL] [ASYNC_FAIL] Instagram operations failed")
            
            # ENHANCED: Update last_used even for failed operations (account was used)
            try:
                await update_account_last_used_async(username)
                log_info(f"[OK] [ASYNC_FAIL] Updated last_used for failed account: {username}")
            except Exception as last_used_error:
                log_warning(f"[WARN] [ASYNC_FAIL] Failed to update last_used: {str(last_used_error)}")
            
            return ("ERROR", 0, len(videos))
    
    except Exception as e:
        error_message = str(e)
        log_info(f"[EXPLODE] [ASYNC_DOLPHIN_EXCEPTION] Critical error in Dolphin browser for account {username}: {error_message}")
        
        # Handle different error types with proper account status updates
        if "PHONE_VERIFICATION_REQUIRED" in error_message:
            log_info(f"[PHONE] [ASYNC_VERIFICATION_PHONE] Phone verification required for account: {username}")
            await update_account_status_async(username, 'PHONE_VERIFICATION_REQUIRED', account_task_id)
            return ("PHONE_VERIFICATION_REQUIRED", 0, 1)
            
        elif "HUMAN_VERIFICATION_REQUIRED" in error_message:
            log_info(f"[BOT] [ASYNC_VERIFICATION_HUMAN] Human verification required for account: {username}")
            await update_account_status_async(username, 'HUMAN_VERIFICATION_REQUIRED', account_task_id)
            return ("HUMAN_VERIFICATION_REQUIRED", 0, 1)
            
        elif "SUSPENDED" in error_message:
            log_info(f"[BLOCK] [ASYNC_VERIFICATION_SUSPENDED] Account suspended for account: {username}")
            await update_account_status_async(username, 'SUSPENDED', account_task_id)
            return ("SUSPENDED", 0, 1)
            
        elif "CAPTCHA" in error_message:
            log_info(f"[BOT] [ASYNC_VERIFICATION_CAPTCHA] CAPTCHA solving failed for account: {username}")
            await update_account_status_async(username, 'CAPTCHA', account_task_id)
            return ("CAPTCHA", 0, 1)
            
        else:
            log_info(f"[ASYNC_FAIL] Browser error: {error_message}")
            return ("BROWSER_ERROR", 0, 1)
    
    finally:
        # Persist latest cookies in DB regardless of outcome
        try:
            if dolphin and dolphin_profile_id:
                from asgiref.sync import sync_to_async
                # Prefer Remote API cookies; fallback to page context if needed
                get_cookies_async = sync_to_async(dolphin.get_cookies)
                cookies_list = await get_cookies_async(dolphin_profile_id)
                if (not cookies_list) and page:
                    try:
                        cookies_list = await page.context.cookies()
                    except Exception:
                        cookies_list = []
                if cookies_list:
                    from uploader.models import InstagramAccount, InstagramCookies
                    @sync_to_async
                    def _save():
                        acc = InstagramAccount.objects.get(username=username)
                        InstagramCookies.objects.update_or_create(
                            account=acc,
                            defaults={'cookies_data': cookies_list, 'is_valid': True}
                        )
                    await _save()
                    log_info(f"[COOKIES] [ASYNC] Saved {len(cookies_list)} cookies for {username}")
        except Exception as cookie_err:
            log_warning(f"[COOKIES] [ASYNC] Failed to persist cookies: {cookie_err}")
        # Cleanup browser session
        if preserve_state:
            log_info("[ASYNC_CLEANUP] Skipping browser cleanup to preserve upload state (no videos were uploaded)")
        else:
            log_info("[ASYNC_CLEANUP] Starting comprehensive browser cleanup")
            try:
                if dolphin_browser:
                    await dolphin_browser.cleanup_async()
                    log_info("[ASYNC_CLEANUP] Browser cleanup completed")
                else:
                    log_info("[ASYNC_CLEANUP] Browser objects not initialized, skipping cleanup")
            except Exception as cleanup_error:
                log_info(f"[ASYNC_CLEANUP] Error during cleanup: {str(cleanup_error)}")

async def authenticate_dolphin_async(dolphin) -> bool:
    """Authenticate with Dolphin Anty API - exact copy from sync version"""
    try:
        from asgiref.sync import sync_to_async
        
        log_info("🔐 [ASYNC_DOLPHIN_AUTH] Authenticating with Dolphin Anty API...")
        
        # Use sync dolphin.authenticate() method which calls get_profiles(limit=1)
        authenticate_sync = sync_to_async(dolphin.authenticate)
        auth_result = await authenticate_sync()
        
        if not auth_result:
            log_info("[FAIL] [ASYNC_DOLPHIN_AUTH] Failed to authenticate with Dolphin Anty API")
            return False
        
        log_info("[OK] [ASYNC_DOLPHIN_AUTH] Successfully authenticated with Dolphin Anty API")
        
        # Check application status - exact copy from sync
        log_info("[SEARCH] [ASYNC_DOLPHIN_AUTH] Checking Dolphin Anty application status...")
        check_status_sync = sync_to_async(dolphin.check_dolphin_status)
        dolphin_status = await check_status_sync()
        
        if not dolphin_status["app_running"]:
            error_msg = dolphin_status.get("error", "Unknown error")
            log_error(f"[FAIL] [ASYNC_DOLPHIN_AUTH] Dolphin Anty application is not running: {error_msg}")
            return False
        
        log_info("[OK] [ASYNC_DOLPHIN_AUTH] Dolphin Anty application is running and ready")
        return True
        
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_DOLPHIN_AUTH] Authentication error: {str(e)}")
        return False

async def get_dolphin_profile_id_async(username: str) -> str:
    """Get Dolphin profile ID for account - exact copy from sync version"""
    try:
        from asgiref.sync import sync_to_async
        from uploader.models import InstagramAccount
        
        get_account = sync_to_async(InstagramAccount.objects.get)
        account = await get_account(username=username)
        return account.dolphin_profile_id
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_DOLPHIN_PROFILE] Error getting dolphin profile ID for {username}: {str(e)}")
        return None

async def cleanup_browser_session_async(page, dolphin_browser, dolphin_profile_id, dolphin):
    """Clean up browser session safely - async version with comprehensive cleanup"""
    try:
        log_info("[ASYNC_CLEANUP] Starting comprehensive browser cleanup")
        
        # First try to cleanup through dolphin_browser if available
        if dolphin_browser:
            try:
                await dolphin_browser.cleanup_async()
                log_info("[ASYNC_CLEANUP] [OK] Dolphin browser cleanup completed")
            except Exception as cleanup_error:
                log_info(f"[ASYNC_CLEANUP] [WARN] Dolphin browser cleanup error: {str(cleanup_error)}")
        
        # Additional cleanup for page if still available
        if page and not dolphin_browser:
            try:
                await page.close()
                log_info("[ASYNC_CLEANUP] [OK] Page closed directly")
            except Exception as page_error:
                log_info(f"[ASYNC_CLEANUP] [WARN] Direct page cleanup error: {str(page_error)}")
        
        # Try to stop Dolphin profile if we have dolphin instance and profile_id
        if dolphin and dolphin_profile_id:
            try:
                from asgiref.sync import sync_to_async
                stop_profile_sync = sync_to_async(dolphin.stop_profile)  
                await stop_profile_sync(dolphin_profile_id)
                log_info(f"[ASYNC_CLEANUP] [OK] Stopped Dolphin profile: {dolphin_profile_id}")
            except Exception as dolphin_error:
                log_info(f"[ASYNC_CLEANUP] [WARN] Dolphin profile stop error: {str(dolphin_error)}")
        
        log_info("[ASYNC_CLEANUP] [OK] Comprehensive cleanup completed")
        
    except Exception as cleanup_error:
        log_info(f"[ASYNC_CLEANUP] [FAIL] Critical cleanup error: {str(cleanup_error)}")
        
        # Emergency cleanup - force close everything
        try:
            log_info("[ASYNC_CLEANUP] [ALERT] Attempting emergency cleanup...")
            
            # Try to force close page
            if page:
                try:
                    await page.close()
                except:
                    pass
            
            # Try to force cleanup browser
            if dolphin_browser:
                try:
                    await dolphin_browser.cleanup_async()
                except:
                    pass
            
            log_info("[ASYNC_CLEANUP] [ALERT] Emergency cleanup completed")
            
        except Exception as emergency_error:
            log_info(f"[ASYNC_CLEANUP] [EXPLODE] Emergency cleanup also failed: {str(emergency_error)}")

class AsyncDolphinBrowser:
    """Async version of DolphinBrowser - exact copy of sync logic"""
    
    def __init__(self, dolphin_api_token: str = None):
        if dolphin_api_token:
            log_info(f"[OK] [ASYNC_DOLPHIN_INIT] Initializing Dolphin Anty with API token")
        
            # Get Dolphin API host from environment (critical for Docker Windows deployment)
        dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
        if not dolphin_api_host.endswith("/v1.0"):
            dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
        
            log_info(f"🐬 [ASYNC_DOLPHIN_INIT] Using Dolphin API host: {dolphin_api_host}")
            
            from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
            self.dolphin = DolphinAnty(api_key=dolphin_api_token, local_api_base=dolphin_api_host)
        else:
            log_error(f"[FAIL] [ASYNC_DOLPHIN_INIT] No Dolphin API token provided - cannot initialize DolphinAnty")
            raise ValueError("Dolphin API token is required")
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.dolphin_profile_id = None
        self.automation_data = None
    
    async def connect_to_profile_async(self, profile_id: str, headless: bool = False):
        """Connect to an existing Dolphin Anty profile using Playwright - exact copy of sync logic"""
        try:
            from asgiref.sync import sync_to_async
            from playwright.async_api import async_playwright
            import os
            
            self.dolphin_profile_id = profile_id
            
            # Start the Dolphin profile using sync method
            log_info(f"[RETRY] [ASYNC_BROWSER] [Step 1/5] Starting Dolphin Anty profile: {profile_id} (headless: {headless})")
            start_profile_sync = sync_to_async(self.dolphin.start_profile)
            success, automation_data = await start_profile_sync(profile_id, headless=headless)
            
            if not success or not automation_data:
                log_error(f"[FAIL] [ASYNC_BROWSER] Failed to start Dolphin profile: {profile_id}")
                return None
                
            self.automation_data = automation_data
            port = automation_data.get("port")
            ws_endpoint = automation_data.get("wsEndpoint")
            
            # Validate automation data
            if not port or not ws_endpoint:
                log_error(f"[FAIL] [ASYNC_BROWSER] Invalid automation data from Dolphin API:")
                log_info(f"   Port: {port}")
                log_info(f"   WS Endpoint: {ws_endpoint}")
                log_info(f"   Full data: {automation_data}")
                return None
                            
            # Construct WebSocket URL
            # В Docker контейнере используем host.docker.internal, иначе localhost
            docker_container = os.environ.get("DOCKER_CONTAINER", "0") == "1"
            host = "host.docker.internal" if docker_container else "127.0.0.1"
            ws_url = f"ws://{host}:{port}{ws_endpoint}"
            log_info(f"🔗 [ASYNC_BROWSER] WebSocket URL: {ws_url}")
                            
            # Initialize Playwright
            log_info(f"[RETRY] [ASYNC_BROWSER] [Step 2/5] Initializing Playwright...")
            self.playwright = await async_playwright().start()
                            
            # Connect to browser
            log_info(f"[RETRY] [ASYNC_BROWSER] [Step 3/5] Connecting to Dolphin browser via WebSocket...")
            try:
                self.browser = await self.playwright.chromium.connect_over_cdp(ws_url)
                log_info(f"[OK] [ASYNC_BROWSER] Successfully connected to browser using CDP")
            except Exception as connect_error:
                log_error(f"[FAIL] [ASYNC_BROWSER] Failed to connect via CDP: {connect_error}")
                log_info(f"   Make sure Dolphin profile {profile_id} is running")
                log_info(f"   WebSocket URL: {ws_url}")
                return None
                            
            # Use the default context (using contexts property like in working code)
            log_info(f"[RETRY] [ASYNC_BROWSER] [Step 4/5] Getting browser context...")
            if self.browser.contexts:
                self.context = self.browser.contexts[0]
                log_info(f"[OK] [ASYNC_BROWSER] Using existing browser context")
            else:
                log_error(f"[FAIL] [ASYNC_BROWSER] No browser contexts available")
                return None
            
            # Get the page
            log_info(f"[RETRY] [ASYNC_BROWSER] [Step 5/5] Getting page...")
            if self.context.pages:
                self.page = self.context.pages[0]
                log_info(f"[OK] [ASYNC_BROWSER] Using existing page")
            else:
                self.page = await self.context.new_page()
                log_info(f"[OK] [ASYNC_BROWSER] Created new page")
            
            log_info(f"[OK] [ASYNC_BROWSER] Successfully connected to Dolphin profile: {profile_id}")
            return self.page
        
        except Exception as e:
            log_error(f"[FAIL] [ASYNC_BROWSER] Error connecting to profile {profile_id}: {str(e)}")
            await self.cleanup_async()
            return None
    
    async def cleanup_async(self):
        """Clean up browser resources"""
        try:
            import platform
            is_windows = platform.system().lower() == 'windows'
            
            log_info("🔒 [ASYNC_BROWSER_CLEANUP] Starting browser cleanup...")
            
            # Close page first
            if self.page:
                try:
                    # На Windows добавляем небольшую задержку перед закрытием
                    if is_windows:
                        await asyncio.sleep(0.5)
                    await self.page.close()
                    log_info("[OK] [ASYNC_BROWSER_CLEANUP] Page closed")
                except Exception as e:
                    log_warning(f"[WARN] [ASYNC_BROWSER_CLEANUP] Error closing page: {str(e)}")
                finally:
                    self.page = None
            
            # Close browser
            if self.browser:
                try:
                    # На Windows добавляем задержку перед закрытием браузера
                    if is_windows:
                        await asyncio.sleep(1.0)
                    await self.browser.close()
                    log_info("[OK] [ASYNC_BROWSER_CLEANUP] Browser closed")
                except Exception as e:
                    log_warning(f"[WARN] [ASYNC_BROWSER_CLEANUP] Error closing browser: {str(e)}")
                finally:
                    self.browser = None
            
            # Stop playwright
            if self.playwright:
                try:
                    # На Windows добавляем задержку перед остановкой Playwright
                    if is_windows:
                        await asyncio.sleep(0.5)
                    await self.playwright.stop()
                    log_info("[OK] [ASYNC_BROWSER_CLEANUP] Playwright stopped")
                except Exception as e:
                    log_warning(f"[WARN] [ASYNC_BROWSER_CLEANUP] Error stopping playwright: {str(e)}")
                finally:
                    self.playwright = None
                
            # Stop Dolphin profile if needed
            if self.dolphin and self.dolphin_profile_id:
                try:
                    from asgiref.sync import sync_to_async
                    # На Windows добавляем задержку перед остановкой профиля
                    if is_windows:
                        await asyncio.sleep(0.5)
                    stop_profile_sync = sync_to_async(self.dolphin.stop_profile)
                    await stop_profile_sync(self.dolphin_profile_id)
                    log_info("[OK] [ASYNC_BROWSER_CLEANUP] Dolphin profile stopped")
                except Exception as e:
                    log_warning(f"[WARN] [ASYNC_BROWSER_CLEANUP] Error stopping Dolphin profile: {str(e)}")
            
            # Clear references
            self.browser = None
            self.context = None  
            self.page = None
            self.playwright = None
            self.dolphin_profile_id = None
            self.automation_data = None
            
            # На Windows добавляем финальную задержку для полной очистки
            if is_windows:
                await asyncio.sleep(1.0)
            
            log_info("[OK] [ASYNC_BROWSER_CLEANUP] Cleanup completed successfully")
            
        except Exception as e:
            log_error(f"[FAIL] [ASYNC_BROWSER_CLEANUP] Critical cleanup error: {str(e)}")
            
            # Force clear all references even if cleanup failed
            self.browser = None
            self.context = None  
            self.page = None
            self.playwright = None
            self.dolphin_profile_id = None
            self.automation_data = None
    
    async def close_async(self):
        """Alias for cleanup_async for compatibility"""
        await self.cleanup_async()

__all__ = ['run_dolphin_browser_async', 'authenticate_dolphin_async', 'get_dolphin_profile_id_async', 'cleanup_browser_session_async', 'AsyncDolphinBrowser']
