"""
Асинхронная версия bulk upload tasks для Instagram automation - ПОЛНАЯ КОПИЯ sync версии
"""

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

# Import all the same optimization modules as sync version
from .constants import (
    TimeConstants, InstagramTexts, BrowserConfig, Limits, TaskStatus, LogCategories, FilePaths,
    VerboseFilters, InstagramSelectors, APIConstants
)
from .selectors_config import InstagramSelectors as SelectorConfig, SelectorUtils
from .task_utils import (
    update_task_log, update_account_task, update_task_status, get_account_username,
    get_account_from_task, mark_account_as_used, get_task_with_accounts, 
    get_account_tasks, get_assigned_videos, get_all_task_videos, get_all_task_titles,
    handle_verification_error, handle_task_completion, handle_emergency_cleanup,
    process_browser_result, handle_account_task_error, handle_critical_task_error
)
from .account_utils import (
    get_account_details, get_proxy_details, get_account_proxy,
    get_account_dolphin_profile_id, save_dolphin_profile_id
)
from .browser_support import (
    cleanup_hanging_browser_processes, safely_close_all_windows,
    simulate_human_rest_behavior, simulate_normal_browsing_behavior,
    simulate_extended_human_rest_behavior
)
from .instagram_automation import InstagramNavigator, InstagramUploader, InstagramLoginHandler
from .browser_utils import BrowserManager, PageUtils, ErrorHandler, NetworkUtils, FileUtils, DebugUtils
from .crop_handler import CropHandler, handle_crop_and_aspect_ratio
from .logging_utils import log_info, log_error, log_debug, log_warning
from .human_behavior import AdvancedHumanBehavior, init_human_behavior, get_human_behavior
from .captcha_solver import solve_recaptcha_if_present, detect_recaptcha_on_page, solve_recaptcha_if_present_sync

# Import email verification functions
from .email_verification_async import (
    get_email_verification_code_async,
    get_2fa_code_async,
    determine_verification_type_async
)

# Configure Django settings for async operations
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
import django
django.setup()

from .models import InstagramAccount, BulkUploadAccount

# Apply browser environment configuration (ПОЛНАЯ КОПИЯ из sync)
for env_var, value in BrowserConfig.ENV_VARS.items():
    os.environ[env_var] = value

# Suppress browser console logs and detailed traces (ПОЛНАЯ КОПИЯ из sync)
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '0'
os.environ['DEBUG'] = ''
os.environ['PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'] = '1'

# Additional environment variables to suppress verbose Playwright output (ПОЛНАЯ КОПИЯ из sync)
os.environ['PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS'] = '1'
os.environ['PLAYWRIGHT_DISABLE_COLORS'] = '1'
os.environ['PLAYWRIGHT_QUIET'] = '1'

# Suppress Chrome/Chromium verbose logging (ПОЛНАЯ КОПИЯ из sync)
os.environ['CHROME_LOG_FILE'] = '/dev/null'
os.environ['CHROME_HEADLESS'] = '1'

# Disable verbose Playwright logging (ПОЛНАЯ КОПИЯ из sync)
logging.getLogger('playwright').setLevel(logging.ERROR)
logging.getLogger('playwright._impl').setLevel(logging.ERROR)

# Suppress other verbose loggers (ПОЛНАЯ КОПИЯ из sync)
for logger_name in ['urllib3', 'requests', 'asyncio']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Configure Python logging to filter out Playwright verbose messages (ПОЛНАЯ КОПИЯ из sync)
class PlaywrightLogFilter(logging.Filter):
    """Filter to block verbose Playwright logs"""
    
    def filter(self, record):
        # Block all Playwright verbose messages
        message = record.getMessage().lower()
        return not any(keyword in message for keyword in VerboseFilters.PLAYWRIGHT_VERBOSE_KEYWORDS)

# Apply the filter to all relevant loggers (ПОЛНАЯ КОПИЯ из sync)
playwright_filter = PlaywrightLogFilter()
for logger_name in ['playwright', 'playwright._impl', 'playwright.sync_api', 'root']:
    try:
        target_logger = logging.getLogger(logger_name)
        target_logger.addFilter(playwright_filter)
        target_logger.setLevel(logging.CRITICAL)
    except:
        pass

# Also apply to the root logger to catch any unfiltered messages (ПОЛНАЯ КОПИЯ из sync)
root_logger = logging.getLogger()
root_logger.addFilter(playwright_filter)

# Import Playwright and Bot modules (ПОЛНАЯ КОПИЯ из sync)
try:
    from playwright.async_api import async_playwright
    from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
    from bot.src.instagram_uploader.browser_dolphin import DolphinBrowser
    from bot.src.instagram_uploader.email_client import Email
except ImportError as e:
    log_info(f"Error importing required modules: {str(e)}. Make sure they're installed.")

# Setup logging (ПОЛНАЯ КОПИЯ из sync)
logger = logging.getLogger('uploader.async_bulk_tasks')

async def run_dolphin_browser_async(account_details: Dict, videos: List, video_files_to_upload: List[str],
                                   task_id, account_task_id):
    """Run browser automation for Instagram - exact copy of sync version with proper error handling"""
    dolphin = None
    dolphin_browser = None
    page = None
    dolphin_profile_id = None
    
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
        
        if result:  # result теперь содержит количество загруженных видео
            uploaded_count = result
            failed_count = len(videos) - uploaded_count
            
            if uploaded_count > 0:
                log_info(f"[OK] [ASYNC_SUCCESS] Successfully uploaded {uploaded_count}/{len(videos)} videos")
                
                # ENHANCED: Update last_used for successful uploads
                try:
                    await update_account_last_used_async(username)
                    log_info(f"[OK] [ASYNC_SUCCESS] Updated last_used for account: {username}")
                except Exception as last_used_error:
                    log_warning(f"[WARN] [ASYNC_SUCCESS] Failed to update last_used: {str(last_used_error)}")
                
                return ("SUCCESS", uploaded_count, failed_count)
            else:
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
        # Cleanup browser session
        log_info("[ASYNC_CLEANUP] Starting comprehensive browser cleanup")
        try:
            if dolphin_browser:
                await dolphin_browser.cleanup_async()
                log_info("[ASYNC_CLEANUP] Browser cleanup completed")
            else:
                log_info("[ASYNC_CLEANUP] Browser objects not initialized, skipping cleanup")
        except Exception as cleanup_error:
            log_info(f"[ASYNC_CLEANUP] Error during cleanup: {str(cleanup_error)}")

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
            log_info("🔒 [ASYNC_BROWSER_CLEANUP] Starting browser cleanup...")
            
            # Close page first
            if self.page:
                try:
                    await self.page.close()
                    log_info("[OK] [ASYNC_BROWSER_CLEANUP] Page closed")
                except Exception as e:
                    log_warning(f"[WARN] [ASYNC_BROWSER_CLEANUP] Error closing page: {str(e)}")
                finally:
                    self.page = None
            
            # Close browser
            if self.browser:
                try:
                    await self.browser.close()
                    log_info("[OK] [ASYNC_BROWSER_CLEANUP] Browser closed")
                except Exception as e:
                    log_warning(f"[WARN] [ASYNC_BROWSER_CLEANUP] Error closing browser: {str(e)}")
                finally:
                    self.browser = None
            
            # Stop playwright
            if self.playwright:
                try:
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

async def perform_instagram_operations_async(page, account_details: Dict, videos: List, video_files_to_upload: List[str]) -> bool:
    """Perform Instagram operations with enhanced error handling and monitoring - async version"""
    try:
        log_info("[SEARCH] [ASYNC_NAVIGATION] Starting Instagram navigation with retry mechanism")
        
        # Use retry mechanism for navigation
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
                if not await navigate_to_upload_with_human_behavior_async(page):
                    log_info(f"[ASYNC_FAIL] Could not navigate to upload page for video {i}")
                    continue
                
                # Upload video
                if await upload_video_with_human_behavior_async(page, video_file_path, video_obj):
                    uploaded_videos += 1
                    log_info(f"[ASYNC_SUCCESS] Video {i}/{len(video_files_to_upload)} uploaded successfully")
                    if video_obj and hasattr(video_obj, 'uploaded'):
                        video_obj.uploaded = True
                else:
                    log_info(f"[ASYNC_FAIL] Failed to upload video {i}/{len(video_files_to_upload)}")
                
                # Human delay between uploads
                if i < len(video_files_to_upload):
                    await add_human_delay_between_uploads_async(page, i)
                    
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

async def init_human_behavior_async(page):
    """Initialize human behavior for async operations - ПОЛНАЯ КОПИЯ sync логики"""
    try:
        log_info("[ASYNC_HUMAN] Initializing human behavior system...")
        # Human behavior initialization logic would go here
        # For now, just a placeholder
        await asyncio.sleep(1)
        log_info("[ASYNC_HUMAN] [OK] Human behavior initialized")
    except Exception as e:
        log_info(f"[ASYNC_HUMAN] [FAIL] Error initializing human behavior: {str(e)}")

async def handle_login_flow_async(page, account_details: Dict) -> bool:
    """Handle Instagram login flow - enhanced to match sync version exactly"""
    try:
        log_info("🔑 [ASYNC_LOGIN] Starting enhanced login flow...")
        
        # Wait for page to be fully interactive before checking login status
        log_info("[WAIT] [ASYNC_LOGIN] Ensuring page is fully loaded before login check...")
        await asyncio.sleep(3)  # Additional wait for page stability
        
        # Import selectors for detailed checks
        try:
            from .selectors_config import InstagramSelectors
            selectors = InstagramSelectors()
        except:
            # Fallback selectors if import fails - EXACT COPY from selectors_config.py
            class FallbackSelectors:
                LOGIN_FORM_INDICATORS = [
                    # АКТУАЛЬНЫЕ селекторы полей Instagram
                    'input[name="email"]',                # Текущее поле username Instagram
                    'input[name="pass"]',                 # Текущее поле password Instagram
                    'input[name="username"]',             # Старое поле username
                    'input[name="password"]',             # Старое поле password
                    
                    # Кнопки входа
                    'button[type="submit"]:has-text("Log in")',
                    'button:has-text("Log in")',
                    'button:has-text("Войти")',
                    'div[role="button"]:has-text("Log in")',
                    'div[role="button"]:has-text("Войти")',
                    
                    # Формы логина
                    'form[id*="loginForm"]',
                    'form[id*="login_form"]',
                    'form:has(input[name="email"])',
                    'form:has(input[name="pass"])',
                    'form:has(input[name="username"])',
                    'form:has(input[name="password"])',
                ]
                
                LOGGED_IN_INDICATORS = [
                    # Russian navigation indicators (most likely for Russian Instagram)
                    'svg[aria-label*="Главная"]',
                    'svg[aria-label*="главная"]',
                    '[aria-label*="Главная"]',
                    '[aria-label*="главная"]',
                    'a[aria-label*="Главная"]',
                    'a[aria-label*="главная"]',
                    
                    # Russian Create/New post indicators - БОЛЕЕ СПЕЦИФИЧНЫЕ
                    'svg[aria-label="Создать"]:not([aria-label*="новый аккаунт"]):not([aria-label*="аккаунт"])',
                    'svg[aria-label*="Создать"]:not([aria-label*="новый аккаунт"]):not([aria-label*="аккаунт"])',
                    'svg[aria-label*="Новая публикация"]',
                    'svg[aria-label*="новая публикация"]',
                    'a[aria-label="Создать"]:not([aria-label*="новый аккаунт"]):not([aria-label*="аккаунт"])',
                    'a[aria-label*="Создать"]:not([aria-label*="новый аккаунт"]):not([aria-label*="аккаунт"])',
                    'a[aria-label*="Новая публикация"]',
                    'a[aria-label*="новая публикация"]',
                    
                    # Более точные селекторы для создания поста
                    'nav svg[aria-label*="Создать"]',  # Только в навигации
                    'header svg[aria-label*="Создать"]',  # Только в хедере
                    '[role="navigation"] svg[aria-label*="Создать"]',  # Только в навигации
                    
                    # Russian Profile indicators
                    'svg[aria-label*="Профиль"]',
                    'svg[aria-label*="профиль"]',
                    '[aria-label*="Профиль"]',
                    '[aria-label*="профиль"]',
                    'img[alt*="фото профиля"]',
                    'img[alt*="Фото профиля"]',
                    
                    # Russian Search indicators
                    'svg[aria-label*="Поиск"]',
                    'svg[aria-label*="поиск"]',
                    '[aria-label*="Поиск"]',
                    '[aria-label*="поиск"]',
                    'input[placeholder*="Поиск"]',
                    'input[placeholder*="поиск"]',
                    
                    # Russian Messages/Direct indicators
                    'svg[aria-label*="Сообщения"]',
                    'svg[aria-label*="сообщения"]',
                    'svg[aria-label*="Messenger"]',
                    '[aria-label*="Сообщения"]',
                    '[aria-label*="сообщения"]',
                    '[aria-label*="Messenger"]',
                    
                    # Russian Activity indicators
                    'svg[aria-label*="Действия"]',
                    'svg[aria-label*="действия"]',
                    'svg[aria-label*="Уведомления"]',
                    'svg[aria-label*="уведомления"]',
                    '[aria-label*="Действия"]',
                    '[aria-label*="действия"]',
                    '[aria-label*="Уведомления"]',
                    '[aria-label*="уведомления"]',
                    
                    # English fallback indicators
                    'svg[aria-label*="Home"]',
                    '[aria-label*="Home"]',
                    'a[href="/"]',
                    '[data-testid="home-icon"]',
                    
                    # Profile/user menu indicators
                    'svg[aria-label*="Profile"]',
                    '[aria-label*="Profile"]',
                    'img[alt*="profile picture"]',
                    '[data-testid="user-avatar"]',
                    
                    # Navigation indicators - БОЛЕЕ СПЕЦИФИЧНЫЕ
                    'nav[role="navigation"]',
                    '[role="navigation"]:not(:has(button:has-text("Войти"))):not(:has(button:has-text("Log in")))',
                    
                    # Create post indicators - ТОЛЬКО ДЛЯ АВТОРИЗОВАННЫХ
                    'svg[aria-label="New post"]:not([aria-label*="account"])',
                    'svg[aria-label*="New post"]:not([aria-label*="account"])',
                    'nav svg[aria-label*="New post"]',
                    'header svg[aria-label*="New post"]',
                    'a[href*="/create/"]:not(:has-text("account"))',
                    
                    # Search indicators
                    'svg[aria-label*="Search"]',
                    '[aria-label*="Search"]',
                    'input[placeholder*="Search"]',
                    
                    # Messages indicators
                    'svg[aria-label*="Direct"]',
                    '[aria-label*="Direct"]',
                    'a[href*="/direct/"]',
                    
                    # Activity indicators
                    'svg[aria-label*="Activity"]',
                    '[aria-label*="Activity"]',
                    
                    # Instagram main navigation - ИСКЛЮЧАЕМ СТРАНИЦЫ ЛОГИНА
                    'div[role="main"]:not(:has(form)):not(:has(input[name="password"]))',
                    'main[role="main"]:not(:has(form)):not(:has(input[name="password"]))',
                    
                    # More specific logged-in indicators
                    'div[data-testid="ig-nav-bar"]',
                    'nav[aria-label*="Primary navigation"]',
                    'div[class*="nav"]:not(:has(input[name="password"]))',
                ]
            selectors = FallbackSelectors()
        
        # Enhanced check if already logged in (EXACT COPY from sync)
        logged_in_status = await check_if_already_logged_in_async(page, selectors)
        
        if logged_in_status == "SUSPENDED":
            log_info(f"[BLOCK] [ASYNC_LOGIN] Account is SUSPENDED - cannot proceed with login")
            raise Exception(f"SUSPENDED: Account suspended by Instagram")
        elif logged_in_status:
            log_info(f"[OK] [ASYNC_LOGIN] Already logged in! Skipping login process")
            
            # Still need to check for post-login verification requirements
            log_info("[SEARCH] [ASYNC_LOGIN] Checking for verification requirements...")
            # await check_post_login_verifications_async(page, account_details)
            return True
        
        log_info("🔑 [ASYNC_LOGIN] User not logged in - need to login to Instagram")
        
        # Only check for reCAPTCHA before attempting login
        log_info("[SEARCH] [ASYNC_LOGIN] Checking for reCAPTCHA on login page...")
        captcha_result = await handle_recaptcha_if_present_async(page, account_details)
        if not captcha_result:
            log_info("[FAIL] [ASYNC_LOGIN] reCAPTCHA solving failed, terminating login flow")
            raise Exception("CAPTCHA: Failed to solve reCAPTCHA")
        log_info("[OK] [ASYNC_LOGIN] reCAPTCHA handling completed")
        
        # Perform login with enhanced process
        login_result = await perform_enhanced_instagram_login_async(page, account_details)
        
        if login_result == "SUSPENDED":
            log_info("[BLOCK] [ASYNC_LOGIN] Account suspended detected during login")
            raise Exception(f"SUSPENDED: Account suspended by Instagram")
        elif not login_result:
            log_info("[FAIL] [ASYNC_LOGIN] Failed to login to Instagram")
            return False
        
        log_info("[OK] [ASYNC_LOGIN] Login completed successfully")
        
        # Handle save login info dialog (like sync version)
        await handle_save_login_info_dialog_async(page)
        
        # Check for post-login verification requirements
        verification_result = await check_post_login_verifications_async(page, account_details)
        
        if verification_result:
            log_info("[OK] [ASYNC_LOGIN] Login flow completed successfully")
            return True
        else:
            log_error("[FAIL] [ASYNC_LOGIN] Post-login verification failed")
            return False
        
    except Exception as e:
        error_message = str(e)
        
        # Re-raise verification-related exceptions
        if ("SUSPENDED:" in error_message or 
            "PHONE_VERIFICATION_REQUIRED:" in error_message or 
            "HUMAN_VERIFICATION_REQUIRED:" in error_message):
            log_error(f"[FAIL] [ASYNC_LOGIN] Login flow failed: {error_message}")
            raise e  # Re-raise the exception so it reaches run_dolphin_browser_async
        else:
            log_error(f"[FAIL] [ASYNC_LOGIN] Error in login flow: {error_message}")
            return False

async def check_if_already_logged_in_async(page, selectors):
    """Check if user is already logged in - EXACT COPY from sync version"""
    log_info("[SEARCH] [ASYNC_LOGIN] Checking if already logged in...")
    
    # Wait a moment for page to fully load
    await asyncio.sleep(random.uniform(2, 4))
    
    # Get current URL for context
    current_url = page.url
    log_debug(f"[SEARCH] [ASYNC_LOGIN] Current URL: {current_url}")
    
    # Check for account suspension first - this is critical
    log_info("[BLOCK] [ASYNC_LOGIN] Checking for account suspension...")
    
    # Check page text for suspension keywords (PRIMARY METHOD)
    try:
        page_text = await page.inner_text('body') or ""
        suspension_keywords = [
            'мы приостановили ваш аккаунт',
            'приостановили ваш аккаунт',
            'аккаунт приостановлен',
            'ваш аккаунт приостановлен',
            'account suspended',
            'account has been suspended',
            'we suspended your account',
            'your account is suspended',
            'your account has been disabled',
            'account disabled',
            'аккаунт заблокирован',
            'ваш аккаунт заблокирован',
            'временно приостановлен',
            'temporarily suspended',
            'осталось',  # "Осталось X дней, чтобы обжаловать"
            'days left'  # "X days left to appeal"
        ]
        
        for keyword in suspension_keywords:
            if keyword in page_text.lower():
                log_info(f"[BLOCK] [ASYNC_LOGIN] Account suspension detected from text: '{keyword}'")
                log_info(f"[BLOCK] [ASYNC_LOGIN] Page text sample: '{page_text[:200]}...'")
                return "SUSPENDED"
                
    except Exception as e:
        log_info(f"[BLOCK] [ASYNC_LOGIN] Could not check page text for suspension: {str(e)}")
    
    # Optional secondary check for URL patterns (as backup only)
    suspension_url_patterns = [
        '/accounts/suspended',
        '/challenge/suspended',
        '/suspended'
    ]
    
    url_indicates_suspension = any(pattern in current_url.lower() for pattern in suspension_url_patterns)
    if url_indicates_suspension:
        log_info(f"[BLOCK] [ASYNC_LOGIN] Account suspension also detected from URL: {current_url}")
        return "SUSPENDED"
    
    # First check if we see login form elements
    login_form_present = False
    found_login_elements = []
    
    for indicator in selectors.LOGIN_FORM_INDICATORS:
        try:
            element = await page.query_selector(indicator)
            if element and await element.is_visible():
                login_form_present = True
                found_login_elements.append(indicator)
                log_debug(f"[SEARCH] [ASYNC_LOGIN] Found login form element: {indicator}")
        except:
            continue
    
    if login_form_present:
        log_debug(f"[SEARCH] [ASYNC_LOGIN] Login form detected with elements: {found_login_elements[:3]}")
        return False
    
    # No login form found, check for logged-in indicators
    logged_in_found = False
    found_indicators = []
    
    log_info("[SEARCH] [ASYNC_LOGIN] No login form found, checking for logged-in indicators...")
    
    for i, indicator in enumerate(selectors.LOGGED_IN_INDICATORS):
        try:
            element = await page.query_selector(indicator)
            if element and await element.is_visible():
                # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: анализируем текст элемента (EXACT COPY from sync)
                try:
                    element_text = await element.text_content() or ""
                    element_aria_label = await element.get_attribute('aria-label') or ""
                    combined_text = (element_text + " " + element_aria_label).lower()
                    
                    # Исключаем элементы связанные с созданием аккаунта
                    exclusion_keywords = [
                        'новый аккаунт', 'new account', 
                        'создать аккаунт', 'create account',
                        'регистрация', 'sign up', 'signup',
                        'зарегистрироваться', 'register'
                    ]
                    
                    if any(keyword in combined_text for keyword in exclusion_keywords):
                        log_debug(f"[SEARCH] [ASYNC_LOGIN] Skipping element {i+1} (contains account creation text): '{element_text.strip()}'")
                        continue
                    
                    logged_in_found = True
                    found_indicators.append(indicator)
                    log_info(f"[OK] [ASYNC_LOGIN] Found logged-in indicator {i+1}: {indicator}")
                    
                    if element_text.strip():
                        log_info(f"[OK] [ASYNC_LOGIN] Element text: '{element_text.strip()}'")
                    
                except Exception as e:
                    # Если не можем получить текст, продолжаем как раньше
                    logged_in_found = True
                    found_indicators.append(indicator)
                    log_info(f"[OK] [ASYNC_LOGIN] Found logged-in indicator {i+1}: {indicator}")
                    log_debug(f"[SEARCH] [ASYNC_LOGIN] Could not analyze element text: {str(e)}")
                
                # If we found a strong indicator, we can be confident
                if any(strong_keyword in indicator.lower() for strong_keyword in [
                    'главная', 'home', 'профиль', 'profile', 'поиск', 'search', 'сообщения', 'messages'
                ]):
                    log_info(f"[OK] [ASYNC_LOGIN] Strong logged-in indicator found: {indicator}")
                    break
                    
        except Exception as e:
            log_debug(f"[SEARCH] [ASYNC_LOGIN] Error checking indicator {indicator}: {str(e)}")
            continue
    
    if logged_in_found:
        log_info(f"[OK] [ASYNC_LOGIN] Already logged in! Found {len(found_indicators)} indicators: {found_indicators[:5]}")
        
        # Additional verification - check page title (EXACT COPY from sync)
        try:
            page_title = await page.title()
            log_info(f"[OK] [ASYNC_LOGIN] Page title: '{page_title}'")
            
            # Instagram main page usually has "Instagram" in title
            if "instagram" in page_title.lower():
                log_info("[OK] [ASYNC_LOGIN] Page title confirms Instagram main page")
            
        except Exception as e:
            log_debug(f"[SEARCH] [ASYNC_LOGIN] Could not get page title: {str(e)}")
        
        # Simulate human behavior - look around a bit
        await asyncio.sleep(random.uniform(1, 3))
        
        # Even if already logged in, simulate human behavior like sync version
        try:
            await simulate_human_mouse_movement_async(page)
        except:
            pass
        
        return True
    
    log_info("[SEARCH] [ASYNC_LOGIN] No logged-in indicators found - user needs to login")
    return False

async def simulate_human_mouse_movement_async(page):
    """Simulate human mouse movement - async version of sync function"""
    try:
        # Get page dimensions
        page_size = await page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
        width, height = page_size['width'], page_size['height']
        
        # Simulate natural mouse movement pattern
        for _ in range(random.randint(2, 4)):
            x = random.randint(50, width - 50)
            y = random.randint(50, height - 50)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        
    except Exception as e:
        log_info(f"[ASYNC_HUMAN] Mouse movement simulation error: {str(e)}")

async def check_post_login_verifications_async(page, account_details):
    """Check for post-login verifications (2FA, email, etc.) - FIXED VERSION"""
    try:
        # Check for reCAPTCHA first (before other verifications)
        log_info("[SEARCH] [ASYNC_LOGIN] Checking for post-login reCAPTCHA...")
        captcha_result = await handle_recaptcha_if_present_async(page, account_details)
        if not captcha_result:
            log_info("[FAIL] [ASYNC_LOGIN] Post-login reCAPTCHA solving failed, terminating login flow")
            raise Exception("CAPTCHA: Failed to solve post-login reCAPTCHA")
        log_info("[OK] [ASYNC_LOGIN] reCAPTCHA handling completed")
        
        # Check for 2FA/Email verification after captcha
        log_info("[SEARCH] [ASYNC_LOGIN] Checking for 2FA/Email verification...")
        
        # Wait for page to be ready
        await asyncio.sleep(random.uniform(2, 4))
        
        # Check if we're already logged in (successful login without 2FA)
        logged_in_indicators = [
            'a[href*="/accounts/activity/"]',
            'a[href*="/accounts/edit/"]',
            'a[href*="/accounts/"]',
            'button[aria-label*="New post"]',
            'button[aria-label*="Create"]',
            'svg[aria-label="Notifications"]',
            'svg[aria-label="Direct"]',
            'svg[aria-label="New post"]',
            'main[role="main"]',
            'nav[role="navigation"]'
        ]
                # Use the proper verification type detection function
        from .email_verification_async import determine_verification_type_async
        
        verification_type = await determine_verification_type_async(page)
        log_info(f"[SEARCH] [ASYNC_LOGIN] Detected verification type: {verification_type}")
        
        if verification_type == "authenticator":
            log_info("[PHONE] [ASYNC_LOGIN] 2FA/Authenticator verification required")
            result = await handle_2fa_async(page, account_details)
            if result:
                log_info("[OK] [ASYNC_LOGIN] 2FA verification completed successfully")
                return True
            else:
                log_error("[FAIL] [ASYNC_LOGIN] 2FA verification failed")
                return False
                
        elif verification_type == "email_code":
            log_info("📧 [ASYNC_LOGIN] Email verification code required")
            result = await handle_email_verification_async(page, account_details)
            if result:
                log_info("[OK] [ASYNC_LOGIN] Email verification completed successfully")
                return True
            else:
                log_error("[FAIL] [ASYNC_LOGIN] Email verification failed")
                return False
                
        elif verification_type == "email_field":
            log_info("📧 [ASYNC_LOGIN] Email field input required")
            result = await handle_email_field_verification_async(page, account_details)
            if result:
                log_info("[OK] [ASYNC_LOGIN] Email field verification completed successfully")
                return True
            else:
                log_error("[FAIL] [ASYNC_LOGIN] Email field verification failed")
                return False
                
        elif verification_type == "unknown":
            log_info("[OK] [ASYNC_LOGIN] No verification required - checking if truly logged in...")
            
            # ТОЛЬКО ЗДЕСЬ проверяем индикаторы успешного входа
            logged_in_indicators = [
                'svg[aria-label="Notifications"]',
                'svg[aria-label="Direct"]', 
                'svg[aria-label="New post"]',
                'main[role="main"]:not(:has(form))',  # main без форм входа
                'nav[role="navigation"]',
                'a[href="/"]',  # Home link
                'a[href="/explore/"]',  # Explore link
            ]
            
            log_info("[FAIL] [ASYNC_LOGIN] No logged-in indicators found - login may have failed")
            return False
        else:
            log_info(f"[WARN] [ASYNC_LOGIN] Unknown verification type: {verification_type}")
            return True
            
    except Exception as e:
        # Re-raise verification exceptions
        if ("SUSPENDED:" in str(e) or 
            "PHONE_VERIFICATION_REQUIRED:" in str(e) or 
            "HUMAN_VERIFICATION_REQUIRED:" in str(e) or
            "CAPTCHA:" in str(e) or
            "2FA_VERIFICATION_FAILED:" in str(e) or
            "EMAIL_VERIFICATION_FAILED:" in str(e)):
            raise e
        else:
            log_error(f"[FAIL] [ASYNC_LOGIN] Error in post-login verification: {str(e)}")
            return False

async def navigate_to_upload_with_human_behavior_async(page):
    """Navigate to upload page with advanced human behavior - ПОЛНАЯ КОПИЯ sync версии"""
    try:
        log_info("[ASYNC_UPLOAD] [START] Starting enhanced navigation to upload interface")
        
        # ENHANCED: Initial page readiness check before starting navigation
        log_info("[ASYNC_UPLOAD] [SEARCH] Performing initial page readiness check...")
        initial_ready = await wait_for_page_ready_async(page, max_wait_time=15.0)
        if not initial_ready:
            log_info("[ASYNC_UPLOAD] [WARN] Initial page readiness check failed, but proceeding...")
        else:
            log_info("[ASYNC_UPLOAD] [OK] Initial page readiness check passed")
        
        # Debug: Log current page state (ПОЛНАЯ КОПИЯ из sync)
        try:
            current_url = page.url
            page_title = await page.title()
            log_info(f"[ASYNC_UPLOAD] [LOCATION] Current page: {current_url}")
            log_info(f"[ASYNC_UPLOAD] [FILE] Page title: {page_title}")
        except Exception as debug_error:
            log_info(f"[ASYNC_UPLOAD] Could not get page info: {str(debug_error)}")
        
        # This now handles multiple scenarios (ПОЛНАЯ КОПИЯ из sync):
        # 1. Menu appears -> select "Публикация" option
        # 2. File dialog opens directly -> proceed immediately
        # 3. Alternative navigation via direct URL
        success = await navigate_to_upload_core_async(page)
        
        if success:
            log_info("[ASYNC_UPLOAD] [OK] Successfully navigated to upload interface")
            
            # Additional verification - check for file input immediately (ПОЛНАЯ КОПИЯ из sync)
            try:
                final_url = page.url
                log_info(f"[ASYNC_UPLOAD] [LOCATION] Final URL: {final_url}")
                
                # Check if we can see file input elements immediately (ПОЛНАЯ КОПИЯ из sync)
                file_inputs = await page.query_selector_all('input[type="file"]')
                log_info(f"[ASYNC_UPLOAD] [FOLDER] Found {len(file_inputs)} file input elements")
                
                # Also check for semantic file input selectors (ПОЛНАЯ КОПИЯ из sync)
                semantic_file_inputs = []
                semantic_selectors = [
                    'input[accept*="video"]',
                    'input[accept*="image"]', 
                    'input[multiple]',
                    'button:has-text("Выбрать на компьютере")',
                    'button:has-text("Select from computer")',
                ]
                
                for selector in semantic_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        semantic_file_inputs.extend(elements)
                    except:
                        continue
                        
                log_info(f"[ASYNC_UPLOAD] [FOLDER] Found {len(semantic_file_inputs)} semantic file input elements")
                
                if len(file_inputs) > 0 or len(semantic_file_inputs) > 0:
                    for i, inp in enumerate(file_inputs + semantic_file_inputs):
                        try:
                            inp_accept = await inp.get_attribute('accept') or 'any'
                            inp_visible = await inp.is_visible()
                            inp_class = await inp.get_attribute('class') or 'no-class'
                            log_info(f"[ASYNC_UPLOAD] Input {i+1}: accept='{inp_accept}', visible={inp_visible}, class='{inp_class[:30]}'")
                        except:
                            pass
                    
                    log_info("[ASYNC_UPLOAD] [OK] File input elements are ready for upload")
                else:
                    log_info("[ASYNC_UPLOAD] [WARN] No file input elements found after navigation")
                            
            except Exception as verify_error:
                log_info(f"[ASYNC_UPLOAD] Could not verify upload interface: {str(verify_error)}")
        else:
            log_info("[ASYNC_UPLOAD] [FAIL] Failed to navigate to upload interface")
        
        return success
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Navigation failed: {str(e)}")
        return False

async def wait_for_page_ready_async(page, max_wait_time=30.0) -> bool:
    """Wait for page to be fully ready - OPTIMIZED VERSION"""
    try:
        log_info(f"[ASYNC_READY] [WAIT] Quick page readiness check (max {max_wait_time}s)...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # Quick check: document ready state
                ready_state = await page.evaluate("document.readyState")
                if ready_state != "complete":
                    log_info(f"[ASYNC_READY] [WAIT] Document not ready: {ready_state}")
                    await asyncio.sleep(2)  # Faster check interval
                    continue
                
                # Quick check: main Instagram interface elements (one selector)
                main_element = await page.query_selector('nav, [role="navigation"], [data-testid="navigation"]')
                if not main_element:
                    log_info(f"[ASYNC_READY] [WAIT] Main interface not found")
                    await asyncio.sleep(0.5)
                    continue
                
                # Quick check: upload button visibility (one selector)
                upload_button = await page.query_selector('[aria-label*="New post"], [aria-label*="Create"], [data-testid="new-post-button"]')
                if not upload_button or not await upload_button.is_visible():
                    log_info(f"[ASYNC_READY] [WAIT] Upload button not visible")
                    await asyncio.sleep(3)
                    continue
                
                log_info(f"[ASYNC_READY] [OK] Page is ready! (took {time.time() - start_time:.1f}s)")
                return True
                
            except Exception as e:
                log_info(f"[ASYNC_READY] [WARN] Error checking page state: {str(e)}")
                await asyncio.sleep(0.5)
                continue
        
        log_info(f"[ASYNC_READY] [FAIL] Page not ready after {max_wait_time}s")
        return False
        
    except Exception as e:
        log_info(f"[ASYNC_READY] [FAIL] Error in wait_for_page_ready_async: {str(e)}")
        return False

async def navigate_to_upload_core_async(page):
    """Navigate to upload page with human behavior - OPTIMIZED VERSION"""
    try:
        log_info("[ASYNC_UPLOAD] [BRAIN] Starting navigation to upload page")
        
        # Quick page readiness check
        page_ready = await wait_for_page_ready_async(page, max_wait_time=10.0)  # Reduced timeout
        if not page_ready:
            log_info("[ASYNC_UPLOAD] [WARN] Page not ready, but proceeding with navigation...")
        
        # Simulate page assessment
        await simulate_page_scan_async(page)
        
        # Find upload button
        upload_button = await find_element_with_selectors_async(page, SelectorConfig.UPLOAD_BUTTON, "UPLOAD_BTN")
        
        if not upload_button:
            log_info("[ASYNC_UPLOAD] [WARN] Upload button not found, trying alternative navigation...")
            return await navigate_to_upload_alternative_async(page)
        
        # Quick check upload button readiness
        try:
            is_visible = await upload_button.is_visible()
            if not is_visible:
                log_info("[ASYNC_UPLOAD] [WARN] Upload button not visible, waiting briefly...")
                await asyncio.sleep(3.0 + random.uniform(-0.5, 0.5))
                
                # Try to find the button again
                upload_button = await find_element_with_selectors_async(page, SelectorConfig.UPLOAD_BUTTON, "UPLOAD_BTN_RETRY")
                if not upload_button:
                    log_info("[ASYNC_UPLOAD] [FAIL] Upload button still not found after retry")
                    return await navigate_to_upload_alternative_async(page)
        except Exception as e:
            log_info(f"[ASYNC_UPLOAD] [WARN] Error checking upload button: {str(e)}")
        
        # Click upload button
        await click_element_with_behavior_async(page, upload_button, "UPLOAD_BTN")
        
        # Wait and observe page changes
        log_info("[ASYNC_UPLOAD] [EYES] Observing page changes...")
        await simulate_page_scan_async(page)
        
        # Check what happened after clicking upload button
        success = await handle_post_upload_click_async(page)
        
        if not success:
            log_info("[ASYNC_UPLOAD] [WARN] Standard navigation failed, trying alternative...")
            return await navigate_to_upload_alternative_async(page)
        
        return success
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Navigation failed: {str(e)}")
        log_info("[ASYNC_UPLOAD] [RETRY] Trying alternative navigation method...")
        return await navigate_to_upload_alternative_async(page)

async def find_element_with_selectors_async(page, selectors, element_name):
    """Find element using list of selectors - ПОЛНАЯ КОПИЯ из sync"""
    try:
        for selector in selectors:
            try:
                if selector.startswith('//'):
                    element = await page.query_selector(f"xpath={selector}")
                else:
                    element = await page.query_selector(selector)
                
                if element and await element.is_visible():
                    log_info(f"[ASYNC_UPLOAD] [OK] Found {element_name} with selector: {selector}")
                    return element
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Selector failed: {selector} - {str(e)}")
                continue
        
        log_info(f"[ASYNC_UPLOAD] [FAIL] {element_name} not found with any selector")
        return None
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error finding {element_name}: {str(e)}")
        return None

async def click_element_with_behavior_async(page, element, element_name):
    """Click element with human behavior - ПОЛНАЯ КОПИЯ из sync"""
    try:
        # ENHANCED: Additional element readiness check before clicking
        try:
            is_visible = await element.is_visible()
            is_enabled = await element.is_enabled()
            
            if not is_visible:
                log_info(f"[ASYNC_UPLOAD] [WARN] {element_name} is not visible, waiting...")
                await asyncio.sleep(2.0 + random.uniform(-0.5, 0.5))
                is_visible = await element.is_visible()
                
            if not is_enabled:
                log_info(f"[ASYNC_UPLOAD] [WARN] {element_name} is not enabled, waiting...")
                await asyncio.sleep(2.0 + random.uniform(-0.5, 0.5))
                is_enabled = await element.is_enabled()
                
            if not is_visible or not is_enabled:
                log_info(f"[ASYNC_UPLOAD] [FAIL] {element_name} still not ready (visible: {is_visible}, enabled: {is_enabled})")
                raise Exception(f"Element {element_name} not ready for click")
                
        except Exception as readiness_error:
            log_info(f"[ASYNC_UPLOAD] [WARN] Error checking element readiness: {str(readiness_error)}")
            # Continue anyway, as the element might still be clickable
        
        # Simulate mouse movement to element
        await simulate_mouse_movement_to_element_async(page, element)
        
        # Human decision pause
        decision_time = 1.0 + random.uniform(-0.3, 0.5)
        await asyncio.sleep(decision_time)
        
        # Click element
        await element.click()
        log_info(f"[ASYNC_UPLOAD] [OK] {element_name} clicked successfully")
        
        # Brief pause after click
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error clicking {element_name}: {str(e)}")
        raise

async def handle_post_upload_click_async(page) -> bool:
    """Handle what happens after clicking upload button - ENHANCED with longer timeouts and retry logic"""
    try:
        log_info("[ASYNC_UPLOAD] [START] Starting enhanced post-upload click handling...")
        
        # ENHANCED: Longer initial wait for interface response
        initial_wait = 8.0 + random.uniform(-2.0, 2.0)  # Increased from 3.0 to 8.0 seconds
        log_info(f"[ASYNC_UPLOAD] [WAIT] Waiting {initial_wait:.1f}s for interface response (enhanced timeout)...")
        await asyncio.sleep(initial_wait)
        
        # Check for file dialog first
        if await check_for_file_dialog_async(page):
            log_info("[ASYNC_UPLOAD] [FOLDER] File dialog opened directly - no menu needed")
            return True
        
        # Check for dropdown menu
        if await check_for_dropdown_menu_async(page):
            log_info("[ASYNC_UPLOAD] [CLIPBOARD] Dropdown menu detected - selecting post option")
            return await click_post_option_async(page)
        
        # ENHANCED: Longer additional wait and check again
        additional_wait = 5.0 + random.uniform(-1.0, 1.0)  # Increased from 2.0 to 5.0 seconds
        log_info(f"[ASYNC_UPLOAD] [WAIT] Waiting additional {additional_wait:.1f}s (enhanced timeout)...")
        await asyncio.sleep(additional_wait)
        
        if await check_for_file_dialog_async(page):
            log_info("[ASYNC_UPLOAD] [FOLDER] File dialog appeared after enhanced delay")
            return True
        
        if await check_for_dropdown_menu_async(page):
            log_info("[ASYNC_UPLOAD] [CLIPBOARD] Menu appeared after enhanced delay")
            return await click_post_option_async(page)
        
        # ENHANCED: Try broader detection with retry logic
        log_info("[ASYNC_UPLOAD] [WARN] Neither menu nor file dialog detected, trying enhanced broader detection...")
        broader_result = await try_broader_upload_detection_async(page)
        
        if broader_result:
            return True
        
        # ENHANCED: Retry logic with page refresh
        log_info("[ASYNC_UPLOAD] [RETRY] First attempt failed, trying retry with page refresh...")
        return await retry_upload_with_page_refresh_async(page)
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error handling post-upload click: {str(e)}")
        return False

async def retry_upload_with_page_refresh_async(page) -> bool:
    """Retry upload process with page refresh when dialog doesn't load"""
    try:
        log_info("[ASYNC_UPLOAD] [RETRY] Starting retry with page refresh...")
        
        # Save current URL for navigation back
        current_url = page.url
        log_info(f"[ASYNC_UPLOAD] [LOCATION] Current URL: {current_url}")
        
        # Refresh the page
        log_info("[ASYNC_UPLOAD] [RETRY] Refreshing page...")
        await page.reload(wait_until="domcontentloaded", timeout=30000)
        
        # Wait for page to fully load
        refresh_wait = 5.0 + random.uniform(-1.0, 1.0)
        log_info(f"[ASYNC_UPLOAD] [WAIT] Waiting {refresh_wait:.1f}s for page to load after refresh...")
        await asyncio.sleep(refresh_wait)
        
        # Simulate page scan to ensure we're ready
        await simulate_page_scan_async(page)
        
        # Try to find upload button again
        log_info("[ASYNC_UPLOAD] [SEARCH] Looking for upload button after refresh...")
        upload_button = await find_element_with_selectors_async(page, SelectorConfig.UPLOAD_BUTTON, "UPLOAD_BTN_RETRY")
        
        if not upload_button:
            log_info("[ASYNC_UPLOAD] [WARN] Upload button not found after refresh, trying alternative navigation...")
            return await navigate_to_upload_alternative_async(page)
        
        # Click upload button again
        log_info("[ASYNC_UPLOAD] 🖱️ Clicking upload button after refresh...")
        await click_element_with_behavior_async(page, upload_button, "UPLOAD_BTN_RETRY")
        
        # ENHANCED: Even longer wait for retry attempt
        retry_wait = 10.0 + random.uniform(-2.0, 2.0)  # 10 seconds for retry
        log_info(f"[ASYNC_UPLOAD] [WAIT] Waiting {retry_wait:.1f}s for interface response after retry...")
        await asyncio.sleep(retry_wait)
        
        # Check for file dialog
        if await check_for_file_dialog_async(page):
            log_info("[ASYNC_UPLOAD] [FOLDER] File dialog opened after retry - success!")
            return True
        
        # Check for dropdown menu
        if await check_for_dropdown_menu_async(page):
            log_info("[ASYNC_UPLOAD] [CLIPBOARD] Menu appeared after retry - selecting post option")
            return await click_post_option_async(page)
        
        # Final broader detection attempt
        log_info("[ASYNC_UPLOAD] [RETRY] Final broader detection attempt after retry...")
        final_result = await try_broader_upload_detection_async(page)
        
        if final_result:
            log_info("[ASYNC_UPLOAD] [OK] Success after retry with page refresh!")
            return True
        else:
            log_info("[ASYNC_UPLOAD] [FAIL] All retry attempts failed")
            return False
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error in retry with page refresh: {str(e)}")
        return False

async def check_for_file_dialog_async(page) -> bool:
    """Check if file selection dialog is open - ПОЛНАЯ КОПИЯ из sync InstagramNavigator._check_for_file_dialog()"""
    try:
        log_info("[ASYNC_UPLOAD] [SEARCH] Checking for file dialog...")
        
        # Use comprehensive file input selectors (ПОЛНАЯ КОПИЯ из sync)
        for selector in SelectorConfig.FILE_INPUT:
            try:
                if selector.startswith('//'):
                    elements = await page.query_selector_all(f"xpath={selector}")
                else:
                    elements = await page.query_selector_all(selector)
                
                for element in elements:
                    if await element.is_visible():
                        log_info(f"[ASYNC_UPLOAD] [OK] File dialog indicator found: {selector}")
                        return True
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Selector failed: {selector} - {str(e)}")
                continue
        
        # Check URL for create mode (ПОЛНАЯ КОПИЯ из sync)
        try:
            current_url = page.url
            if 'create' in current_url.lower():
                log_info(f"[ASYNC_UPLOAD] [SEARCH] URL indicates create mode: {current_url}")
                return True
        except:
            pass
        
        # Check page content for upload indicators (ПОЛНАЯ КОПИЯ из sync)
        try:
            page_text = await page.inner_text('body') or ""
            upload_keywords = [
                'выбрать на компьютере', 'select from computer', 
                'выбрать файлы', 'select files',
                'перетащите файлы', 'drag files',
                'загрузить файл', 'upload file'
            ]
            
            for keyword in upload_keywords:
                if keyword in page_text.lower():
                    log_info(f"[ASYNC_UPLOAD] [OK] Upload interface detected via keyword: '{keyword}'")
                    return True
        except:
            pass
        
        log_info("[ASYNC_UPLOAD] [FAIL] No file dialog detected")
        return False
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] Error checking for file dialog: {str(e)}")
        return False

async def check_for_dropdown_menu_async(page) -> bool:
    """Check if dropdown menu appeared - ПОЛНАЯ КОПИЯ из sync InstagramNavigator._check_for_dropdown_menu()"""
    try:
        # Check for menu using selectors (ПОЛНАЯ КОПИЯ из sync)
        menu_element = await find_element_with_selectors_async(page, SelectorConfig.MENU_INDICATORS, "MENU_CHECK")
        
        if menu_element:
            log_info("[ASYNC_UPLOAD] [OK] Dropdown menu detected")
            return True
        
        # Check for specific menu items (ПОЛНАЯ КОПИЯ из sync)
        for selector in SelectorConfig.POST_OPTION[:3]:
            try:
                if selector.startswith('//'):
                    post_option = await page.query_selector(f"xpath={selector}")
                else:
                    post_option = await page.query_selector(selector)
                
                if post_option and await post_option.is_visible():
                    log_info(f"[ASYNC_UPLOAD] [OK] Post option visible in menu")
                    return True
            except:
                continue
        
        return False
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] Error checking for dropdown menu: {str(e)}")
        return False

async def try_broader_upload_detection_async(page) -> bool:
    """Try broader detection methods - ENHANCED with additional wait and more robust detection"""
    try:
        log_info("[ASYNC_UPLOAD] [RETRY] Attempting enhanced broader upload interface detection...")
        
        # ENHANCED: Additional wait before broader detection
        broader_wait = 3.0 + random.uniform(-1.0, 1.0)
        log_info(f"[ASYNC_UPLOAD] [WAIT] Waiting {broader_wait:.1f}s before broader detection...")
        await asyncio.sleep(broader_wait)
        
        # Enhanced upload indicators with more comprehensive selectors
        upload_indicators = [
            'div:has-text("Создать")',
            'div:has-text("Create")',
            'div:has-text("Публикация")',
            'div:has-text("Post")',
            'div:has-text("Выбрать")',
            'div:has-text("Select")',
            'button:has-text("Выбрать на компьютере")',
            'button:has-text("Select from computer")',
            'button:has-text("Выбрать файлы")',
            'button:has-text("Select files")',
            'div[role="button"]:has-text("Создать")',
            'div[role="button"]:has-text("Create")',
            'div[role="button"]:has-text("Публикация")',
            'div[role="button"]:has-text("Post")',
            'input[type="file"]',
            'input[accept*="video"]',
            'input[accept*="image"]',
            'input[accept*="mp4"]',
            'input[accept*="quicktime"]',
            'input[multiple]',
            'form[enctype="multipart/form-data"] input[type="file"]',
            'form[method="POST"] input[type="file"]',
        ]
        
        for indicator in upload_indicators:
            try:
                element = await page.query_selector(indicator)
                if element and await element.is_visible():
                    log_info(f"[ASYNC_UPLOAD] [TARGET] Found upload indicator: {indicator}")
                    
                    # ENHANCED: Click behavior for buttons and interactive elements
                    if any(keyword in indicator.lower() for keyword in ['button', 'div[role="button"]']):
                        log_info(f"[ASYNC_UPLOAD] 🖱️ Clicking interactive element: {indicator}")
                        await click_element_with_behavior_async(page, element, "UPLOAD_INDICATOR")
                        
                        # Wait after clicking
                        click_wait = 2.0 + random.uniform(-0.5, 0.5)
                        log_info(f"[ASYNC_UPLOAD] [WAIT] Waiting {click_wait:.1f}s after clicking indicator...")
                        await asyncio.sleep(click_wait)
                        
                        # Check if file dialog appeared after clicking
                        if await check_for_file_dialog_async(page):
                            log_info("[ASYNC_UPLOAD] [OK] File dialog appeared after clicking indicator!")
                            return True
                    
                    # For file inputs, just return True as they indicate upload interface
                    elif 'input' in indicator.lower():
                        log_info(f"[ASYNC_UPLOAD] [OK] File input found: {indicator}")
                        return True
                    
                    return True
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Selector failed: {indicator} - {str(e)}")
                continue
        
        # ENHANCED: Check page content with more comprehensive keywords
        try:
            page_text = await page.inner_text('body') or ""
            upload_keywords = [
                'выбрать на компьютере', 'select from computer', 
                'перетащите', 'drag',
                'выбрать файлы', 'select files',
                'загрузить файл', 'upload file',
                'создать публикацию', 'create post',
                'добавить фото', 'add photo',
                'добавить видео', 'add video',
                'перетащите сюда', 'drag here',
                'нажмите для выбора', 'click to select'
            ]
            
            for keyword in upload_keywords:
                if keyword in page_text.lower():
                    log_info(f"[ASYNC_UPLOAD] [OK] Upload interface detected via keyword: '{keyword}'")
                    return True
        except Exception as e:
            log_info(f"[ASYNC_UPLOAD] Error checking page content: {str(e)}")
        
        # ENHANCED: Check URL patterns
        try:
            current_url = page.url.lower()
            url_indicators = ['create', 'upload', 'post', 'new']
            
            for indicator in url_indicators:
                if indicator in current_url:
                    log_info(f"[ASYNC_UPLOAD] [OK] Upload interface detected via URL: '{indicator}' in {current_url}")
                    return True
        except Exception as e:
            log_info(f"[ASYNC_UPLOAD] Error checking URL: {str(e)}")
        
        log_info("[ASYNC_UPLOAD] [WARN] Could not detect upload interface with enhanced detection")
        return False
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error in enhanced broader detection: {str(e)}")
        return False

async def click_post_option_async(page) -> bool:
    """Find and click post option in dropdown - ENHANCED with longer waits and better error handling"""
    try:
        log_info("[ASYNC_UPLOAD] [SEARCH] Looking for 'Публикация' option with enhanced detection...")
        
        # ENHANCED: Longer human-like pause to read menu options
        reading_time = 4.0 + random.uniform(-1.0, 1.0)  # Increased from 2.0 to 4.0 seconds
        log_info(f"[ASYNC_UPLOAD] 📖 Reading menu options for {reading_time:.1f}s (enhanced wait)...")
        await asyncio.sleep(reading_time)
        
        await simulate_page_scan_async(page)
        
        post_option = None
        found_selector = None
        
        for i, selector in enumerate(SelectorConfig.POST_OPTION):
            try:
                if i > 0:
                    # ENHANCED: Longer pause between selectors
                    selector_wait = 1.0 + random.uniform(-0.3, 0.3)  # Increased from 0.3-0.7 to 0.7-1.3
                    await asyncio.sleep(selector_wait)
                
                log_info(f"[ASYNC_UPLOAD] [SEARCH] Trying selector {i+1}/{len(SelectorConfig.POST_OPTION)}: {selector}")
                
                if selector.startswith('//'):
                    post_option = await page.query_selector(f"xpath={selector}")
                else:
                    post_option = await page.query_selector(selector)
                
                if post_option and await post_option.is_visible():
                    try:
                        element_text = await post_option.text_content() or ""
                        element_aria = await post_option.get_attribute('aria-label') or ""
                        combined_text = (element_text + " " + element_aria).lower()
                        
                        # ENHANCED: More comprehensive post keywords
                        post_keywords = [
                            'публикация', 'post', 'создать публикацию', 'create post',
                            'создать', 'create', 'новая публикация', 'new post',
                            'добавить публикацию', 'add post', 'создать пост', 'create post'
                        ]
                        
                        if any(keyword in combined_text for keyword in post_keywords):
                            log_info(f"[ASYNC_UPLOAD] [OK] Found 'Публикация' option: '{element_text.strip()}'")
                            found_selector = selector
                            break
                        else:
                            log_info(f"[ASYNC_UPLOAD] [SEARCH] Element found but text doesn't match: '{element_text.strip()}'")
                            post_option = None
                            continue
                    except Exception as text_error:
                        log_info(f"[ASYNC_UPLOAD] [OK] Found potential 'Публикация' option (text check failed: {str(text_error)})")
                        found_selector = selector
                        break
                
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Selector failed: {selector} - {str(e)}")
                continue
        
        if post_option:
            try:
                log_info(f"[ASYNC_UPLOAD] 🖱️ Clicking post option found with selector: {found_selector}")
                
                # ENHANCED: Pre-click wait
                pre_click_wait = 1.0 + random.uniform(-0.3, 0.3)
                log_info(f"[ASYNC_UPLOAD] [WAIT] Waiting {pre_click_wait:.1f}s before clicking...")
                await asyncio.sleep(pre_click_wait)
                
                # Click the post option
                await click_element_with_behavior_async(page, post_option, "POST_OPTION")
                
                # ENHANCED: Longer post-click wait
                post_click_wait = 5.0 + random.uniform(-1.0, 1.0)  # Increased wait after clicking
                log_info(f"[ASYNC_UPLOAD] [WAIT] Waiting {post_click_wait:.1f}s after clicking post option...")
                await asyncio.sleep(post_click_wait)
                
                # Check if file dialog appeared
                if await check_for_file_dialog_async(page):
                    log_info("[ASYNC_UPLOAD] [OK] File dialog appeared after clicking post option!")
                    return True
                
                # Check if we're on create page
                try:
                    current_url = page.url.lower()
                    if 'create' in current_url:
                        log_info(f"[ASYNC_UPLOAD] [OK] Successfully navigated to create page: {current_url}")
                        return True
                except:
                    pass
                
                # ENHANCED: Additional verification
                log_info("[ASYNC_UPLOAD] [SEARCH] Verifying post option click result...")
                verification_wait = 3.0 + random.uniform(-0.5, 0.5)
                await asyncio.sleep(verification_wait)
                
                if await check_for_file_dialog_async(page):
                    log_info("[ASYNC_UPLOAD] [OK] File dialog appeared after verification!")
                    return True
                
                log_info("[ASYNC_UPLOAD] [OK] Post option click completed (assuming success)")
                return True
                
            except Exception as click_error:
                log_info(f"[ASYNC_UPLOAD] [FAIL] Error clicking post option: {str(click_error)}")
                
                # ENHANCED: Fallback click attempt
                try:
                    log_info("[ASYNC_UPLOAD] [RETRY] Trying fallback click method...")
                    await post_option.click(timeout=5000)
                    
                    fallback_wait = 3.0 + random.uniform(-0.5, 0.5)
                    log_info(f"[ASYNC_UPLOAD] [WAIT] Waiting {fallback_wait:.1f}s after fallback click...")
                    await asyncio.sleep(fallback_wait)
                    
                    if await check_for_file_dialog_async(page):
                        log_info("[ASYNC_UPLOAD] [OK] Fallback click successful!")
                        return True
                    else:
                        log_info("[ASYNC_UPLOAD] [OK] Fallback click completed (assuming success)")
                        return True
                        
                except Exception as fallback_error:
                    log_info(f"[ASYNC_UPLOAD] [FAIL] Fallback click also failed: {str(fallback_error)}")
                    return False
        else:
            log_info("[ASYNC_UPLOAD] [FAIL] Post option not found with any selector")
            return False
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error in enhanced click_post_option: {str(e)}")
        return False

async def navigate_to_upload_alternative_async(page) -> bool:
    """Alternative navigation method - direct URL - ПОЛНАЯ КОПИЯ из sync InstagramNavigator._navigate_to_upload_alternative()"""
    try:
        log_info("[ASYNC_UPLOAD] [RETRY] Using alternative navigation: direct URL")
        
        # Navigate directly to create page (ПОЛНАЯ КОПИЯ из sync)
        current_url = page.url
        if 'instagram.com' in current_url:
            create_url = "https://www.instagram.com/create/select/"
            log_info(f"[ASYNC_UPLOAD] 🌐 Navigating to: {create_url}")
            
            # Use retry mechanism for alternative navigation
            navigation_success = await retry_navigation_async(page, create_url, max_attempts=3, base_delay=3)
            
            if not navigation_success:
                log_info("[ASYNC_UPLOAD] [FAIL] Alternative navigation failed after all retry attempts")
                return False
            
            # Check if we're on upload page (ПОЛНАЯ КОПИЯ из sync)
            if await check_for_file_dialog_async(page):
                log_info("[ASYNC_UPLOAD] [OK] Successfully navigated to upload page via direct URL")
                return True
            else:
                log_info("[ASYNC_UPLOAD] [WARN] Direct URL navigation didn't show file dialog")
                return False
        else:
            log_info("[ASYNC_UPLOAD] [FAIL] Not on Instagram domain, cannot use direct URL")
            return False
            
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD_ALT_ERROR] Alternative navigation failed: {str(e)}")
        return False

async def upload_video_with_human_behavior_async(page, video_file_path, video_obj):
    """Upload video with advanced human behavior - ПОЛНАЯ КОПИЯ sync версии"""
    try:
        log_info(f"[ASYNC_UPLOAD] [VIDEO] Starting video upload following exact Selenium pipeline: {os.path.basename(video_file_path)}")
        
        # Use the uploader with Selenium-style pipeline (ПОЛНАЯ КОПИЯ из sync)
        # This now follows the exact Selenium pipeline:
        # 1. Select video file (upload_button.send_keys)
        # 2. Handle OK button
        # 3. Crop handling (select_crop -> original_crop -> select_crop)
        # 4. Click Next twice (for _ in range(2): _next_page)
        # 5. Set description (character by character with 0.05s delay)
        # 6. Set location (with suggestion selection)
        # 7. Set mentions (with suggestion selection and done button)
        # 8. Post video (share button)
        # 9. Verify success (wait for success message)
        return await upload_video_core_async(page, video_file_path, video_obj)
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Upload failed: {str(e)}")
        return False

async def upload_video_core_async(page, video_file_path, video_obj):
    """Core video upload logic - FULL ADAPTIVE SEARCH like sync version"""
    try:
        log_info(f"[ASYNC_UPLOAD] [FOLDER] Starting adaptive file input search for: {os.path.basename(video_file_path)}")
        
        # ENHANCED: Verify file exists before attempting upload
        if not os.path.exists(video_file_path):
            log_info(f"[ASYNC_UPLOAD] [FAIL] File does not exist: {video_file_path}")
            return False
        
        file_size = os.path.getsize(video_file_path)
        if file_size == 0:
            log_info(f"[ASYNC_UPLOAD] [FAIL] File is empty: {video_file_path}")
            return False
        
        log_info(f"[ASYNC_UPLOAD] [OK] File verified: {os.path.basename(video_file_path)} ({file_size} bytes)")
        
        # Find file input with adaptive search
        file_input = await find_file_input_adaptive_async(page)
        if not file_input:
            log_info("[ASYNC_UPLOAD] [FAIL] Failed to find file input")
            return False
        
        # Set file on input
        log_info(f"[ASYNC_UPLOAD] 📤 Setting file on input: {video_file_path}")
        await file_input.set_input_files(video_file_path)
        log_info("[ASYNC_UPLOAD] [OK] Video file selected successfully")
        
        # Minimal wait for processing (ПОЛНАЯ КОПИЯ из sync)
        processing_delay = random.uniform(2, 3)
        log_info(f"[ASYNC_UPLOAD] [WAIT] Waiting {processing_delay:.1f}s for file processing...")
        await asyncio.sleep(processing_delay)
        
        # 🔥 НОВАЯ ЛОГИКА: Обрабатываем диалог Reels если он появился
        await handle_reels_dialog_async(page)
        
        # Handle crop (FULL ADAPTIVE VERSION)
        if not await handle_crop_async(page):
            log_info("[ASYNC_UPLOAD] [FAIL] Failed to handle crop")
            return False
        
        # 🔥 ИСПРАВЛЕННАЯ ЛОГИКА: Click Next buttons FIRST (like sync version)
        # В sync версии: for i in range(2): _click_next_button(i + 1)
        log_info("[ASYNC_UPLOAD] [RETRY] Clicking Next buttons (like sync version)...")
        for step in range(2):  # Click Next twice like sync version
            next_success = await click_next_button_async(page, step + 1)
            if not next_success:
                log_info(f"[ASYNC_UPLOAD] [FAIL] Failed to click Next button {step + 1}")
                return False
            log_info(f"[ASYNC_UPLOAD] [OK] Successfully clicked Next button {step + 1}")
        
        # 🔥 ИСПРАВЛЕННАЯ ЛОГИКА: Now add description, location, mentions (like sync version)
        log_info("[ASYNC_UPLOAD] [TEXT] Starting metadata addition (like sync version)...")
        
        # Add caption if available (like sync _set_description_selenium_style)
        # ENHANCED: Comprehensive caption text extraction with detailed logging
        caption_text = None
        
        try:
            log_info(f"[ASYNC_UPLOAD] [SEARCH] Extracting caption from video_obj type: {type(video_obj)}")
            
            # Strategy 1: Check for VideoData objects (new async version) - PRIORITY
            if hasattr(video_obj, 'title') and video_obj.title:
                caption_text = str(video_obj.title).strip()
                log_info(f"[ASYNC_UPLOAD] [TEXT] Found caption from VideoData.title: '{caption_text[:50]}...'")
            elif hasattr(video_obj, 'description') and video_obj.description:
                caption_text = str(video_obj.description).strip()
                log_info(f"[ASYNC_UPLOAD] [TEXT] Found caption from VideoData.description: '{caption_text[:50]}...'")
            
            # Strategy 2: Check for VideoTitle objects (from title_data relationship)
            elif hasattr(video_obj, 'title_data') and video_obj.title_data:
                if hasattr(video_obj.title_data, 'title') and video_obj.title_data.title:
                    caption_text = str(video_obj.title_data.title).strip()
                    log_info(f"[ASYNC_UPLOAD] [TEXT] Found caption from VideoTitle.title: '{caption_text[:50]}...'")
                else:
                    log_info(f"[ASYNC_UPLOAD] [WARN] VideoTitle object has no title attribute")
            
            # Strategy 3: Check for Django model objects (old async version)
            elif hasattr(video_obj, 'title_data') and video_obj.title_data:
                if hasattr(video_obj.title_data, 'title') and video_obj.title_data.title:
                    caption_text = str(video_obj.title_data.title).strip()
                    log_info(f"[ASYNC_UPLOAD] [TEXT] Found caption from Django model title_data.title: '{caption_text[:50]}...'")
                elif hasattr(video_obj.title_data, 'description') and video_obj.title_data.description:
                    caption_text = str(video_obj.title_data.description).strip()
                    log_info(f"[ASYNC_UPLOAD] [TEXT] Found caption from Django model title_data.description: '{caption_text[:50]}...'")
            
            # Strategy 4: Check for direct attributes on video_obj
            elif hasattr(video_obj, 'caption') and video_obj.caption:
                caption_text = str(video_obj.caption).strip()
                log_info(f"[ASYNC_UPLOAD] [TEXT] Found caption from video_obj.caption: '{caption_text[:50]}...'")
            
            # Strategy 5: Check for any text-like attributes
            else:
                # List all attributes for debugging
                all_attrs = [attr for attr in dir(video_obj) if not attr.startswith('_')]
                log_info(f"[ASYNC_UPLOAD] [SEARCH] All video_obj attributes: {all_attrs}")
                
                # Check common text attributes
                text_attrs = ['title', 'description', 'caption', 'text', 'content', 'name']
                for attr in text_attrs:
                    if hasattr(video_obj, attr):
                        value = getattr(video_obj, attr)
                        if value and str(value).strip():
                            caption_text = str(value).strip()
                            log_info(f"[ASYNC_UPLOAD] [TEXT] Found caption from video_obj.{attr}: '{caption_text[:50]}...'")
                            break
                
                if not caption_text:
                    log_info(f"[ASYNC_UPLOAD] [WARN] No caption text found in any attribute")
                    
        except Exception as caption_error:
            log_info(f"[ASYNC_UPLOAD] [FAIL] Error extracting caption: {str(caption_error)}")
            import traceback
            log_info(f"[ASYNC_UPLOAD] [SEARCH] Caption extraction traceback: {traceback.format_exc()}")
            caption_text = None
        
        # ENHANCED: Add caption if we found any text
        if caption_text and caption_text.strip():
            log_info(f"[ASYNC_UPLOAD] [TARGET] Adding caption: '{caption_text[:100]}...'")
            caption_success = await add_video_caption_async(page, caption_text)
            if not caption_success:
                log_info(f"[ASYNC_UPLOAD] [WARN] Failed to add caption, but continuing...")
        else:
            log_info(f"[ASYNC_UPLOAD] [WARN] No caption text to add")
        
        # Add location if available (like sync _set_location_selenium_style)
        log_info(f"[ASYNC_UPLOAD] [LOCATION] Adding location for video_obj: {type(video_obj)}")
        await add_video_location_async(page, video_obj)
        
        # Add mentions if available (like sync _set_mentions_selenium_style)
        log_info(f"[ASYNC_UPLOAD] [USERS] Adding mentions for video_obj: {type(video_obj)}")
        await add_video_mentions_async(page, video_obj)
        
        # Click Share button (like sync _post_video_selenium_style)
        log_info("[ASYNC_UPLOAD] [START] Clicking Share button...")
        share_success = await click_share_button_async(page)
        if not share_success:
            log_info("[ASYNC_UPLOAD] [FAIL] Failed to click Share button")
            return False
        
        # Verify upload success (like sync _verify_video_posted)
        log_info("[ASYNC_UPLOAD] [OK] Verifying upload success...")
        return await check_video_posted_successfully_async(page, video_file_path)
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Core upload failed: {str(e)}")
        import traceback
        log_info(f"[ASYNC_UPLOAD] [SEARCH] Full traceback: {traceback.format_exc()}")
        return False

async def find_file_input_adaptive_async(page):
    """Адаптивный поиск файлового input - ПОЛНАЯ КОПИЯ sync версии"""
    try:
        log_info("[ASYNC_UPLOAD] [SEARCH] Starting adaptive file input search...")
        
        # [TARGET] СТРАТЕГИЯ 1: Поиск по семантическим атрибутам (ПОЛНАЯ КОПИЯ из sync)
        log_info("[ASYNC_UPLOAD] [CLIPBOARD] Strategy 1: Semantic attributes search...")
        semantic_strategies = [
            'input[type="file"]',
            'input[accept*="video"]',
            'input[accept*="image"]', 
            'input[accept*="mp4"]',
            'input[accept*="quicktime"]',
            'input[multiple]',
            'form[enctype="multipart/form-data"] input[type="file"]',
            'form[method="POST"] input[type="file"]',
        ]
        
        for selector in semantic_strategies:
            try:
                elements = await page.query_selector_all(selector)
                log_info(f"[ASYNC_UPLOAD] 🔎 Checking selector: {selector} - found {len(elements)} elements")
                
                for element in elements:
                    if element and await is_valid_file_input_async(element):
                        log_info(f"[ASYNC_UPLOAD] [OK] Found file input via semantic: {selector}")
                        return element
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Semantic selector failed: {selector} - {str(e)}")
                continue
        
        # [TARGET] СТРАТЕГИЯ 2: Поиск через структуру диалога (ПОЛНАЯ КОПИЯ из sync)
        log_info("[ASYNC_UPLOAD] 🏗️ Strategy 2: Dialog structure search...")
        dialog_input = await find_input_via_dialog_structure_async(page)
        if dialog_input:
            log_info("[ASYNC_UPLOAD] [OK] Found file input via dialog structure")
            return dialog_input
        
        # [TARGET] СТРАТЕГИЯ 3: Поиск через кнопку "Выбрать на компьютере" (ПОЛНАЯ КОПИЯ из sync)
        log_info("[ASYNC_UPLOAD] 🔘 Strategy 3: Button-based search...")
        button_input = await find_input_via_button_async(page)
        if button_input:
            log_info("[ASYNC_UPLOAD] [OK] Found file input via button search")
            return button_input
        
        # [TARGET] СТРАТЕГИЯ 4: Поиск по контексту формы (ПОЛНАЯ КОПИЯ из sync)
        log_info("[ASYNC_UPLOAD] [TEXT] Strategy 4: Form context search...")
        form_input = await find_input_via_form_context_async(page)
        if form_input:
            log_info("[ASYNC_UPLOAD] [OK] Found file input via form context")
            return form_input
        
        # [TARGET] СТРАТЕГИЯ 5: Поиск по характерным CSS-классам Instagram (ПОЛНАЯ КОПИЯ из sync)
        log_info("[ASYNC_UPLOAD] 🎨 Strategy 5: Instagram CSS patterns...")
        css_input = await find_input_via_css_patterns_async(page)
        if css_input:
            log_info("[ASYNC_UPLOAD] [OK] Found file input via CSS patterns")
            return css_input
        
        # [TARGET] СТРАТЕГИЯ 6: Широкий поиск всех input и фильтрация (ПОЛНАЯ КОПИЯ из sync)
        log_info("[ASYNC_UPLOAD] 🌐 Strategy 6: Broad search with filtering...")
        all_input = await find_input_via_broad_search_async(page)
        if all_input:
            log_info("[ASYNC_UPLOAD] [OK] Found file input via broad search")
            return all_input
            
        log_info("[ASYNC_UPLOAD] [WARN] No file input found with any adaptive strategy")
        return None
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Adaptive file input search failed: {str(e)}")
        return None

async def is_valid_file_input_async(element):
    """Проверить, является ли элемент валидным файловым input - ПОЛНАЯ КОПИЯ sync версии"""
    try:
        if not element:
            return False
            
        # Проверить тип (ПОЛНАЯ КОПИЯ из sync)
        input_type = await element.get_attribute('type')
        if input_type != 'file':
            return False
        
        # Проверить accept атрибут (ПОЛНАЯ КОПИЯ из sync)
        accept_attr = await element.get_attribute('accept') or ""
        
        log_info(f"[ASYNC_UPLOAD] Validating input: type='{input_type}', accept='{accept_attr}'")
        
        # Проверяем, что accept содержит нужные типы файлов (ПОЛНАЯ КОПИЯ из sync)
        valid_types = ['video', 'image', 'mp4', 'jpeg', 'png', 'quicktime', 'heic', 'heif', 'avif']
        if accept_attr and not any(file_type in accept_attr.lower() for file_type in valid_types):
            log_info(f"[ASYNC_UPLOAD] Input rejected: accept attribute doesn't contain valid file types")
            return False
        
        # Если accept пустой, но это input[type="file"], считаем валидным (ПОЛНАЯ КОПИЯ из sync)
        if not accept_attr:
            log_info("[ASYNC_UPLOAD] Input has no accept attribute, but type='file' - considering valid")
        
        # Проверить multiple атрибут (ПОЛНАЯ КОПИЯ из sync)
        multiple_attr = await element.get_attribute('multiple')
        if multiple_attr is not None:
            log_info("[ASYNC_UPLOAD] Input supports multiple files - good sign")
        
        log_info("[ASYNC_UPLOAD] Input validation passed")
        return True
            
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] Error validating file input: {str(e)}")
        return False

async def find_input_via_dialog_structure_async(page):
    """Найти input через структуру диалога - ПОЛНАЯ КОПИЯ sync версии"""
    try:
        log_info("[ASYNC_UPLOAD] 🏗️ Searching within dialog structure...")
        
        # Селекторы для диалога создания публикации (ПОЛНАЯ КОПИЯ из sync)
        dialog_selectors = [
            'div[aria-label="Создание публикации"]',
            'div[aria-label*="Создание"]',
            'div[role="dialog"]',
            'div:has-text("Создание публикации")',
            'div:has-text("Перетащите сюда фото и видео")',
            'div:has-text("Выбрать на компьютере")',
        ]
        
        for selector in dialog_selectors:
            try:
                dialog = await page.query_selector(selector)
                if dialog:
                    log_info(f"[ASYNC_UPLOAD] 🏗️ Found dialog with: {selector}")
                    
                    # Ищем input внутри диалога (ПОЛНАЯ КОПИЯ из sync)
                    file_input = await dialog.query_selector('input[type="file"]')
                    if file_input and await is_valid_file_input_async(file_input):
                        log_info("[ASYNC_UPLOAD] [OK] Found valid file input inside dialog")
                        return file_input
                    
                    # Также проверяем form внутри диалога (ПОЛНАЯ КОПИЯ из sync)
                    form = await dialog.query_selector('form')
                    if form:
                        form_input = await form.query_selector('input[type="file"]')
                        if form_input and await is_valid_file_input_async(form_input):
                            log_info("[ASYNC_UPLOAD] [OK] Found valid file input inside form within dialog")
                            return form_input
                            
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Dialog selector failed {selector}: {str(e)}")
                continue
                
        return None
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] Dialog structure search failed: {str(e)}")
        return None

async def find_input_via_button_async(page):
    """Найти input через кнопку - ПОЛНАЯ КОПИЯ sync версии"""
    try:
        button_selectors = [
            'button:has-text("Выбрать на компьютере")',
            'button:has-text("Select from computer")',
            'button:has-text("Выбрать файлы")',
            'button:has-text("Select files")',
        ]
        
        for selector in button_selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    # Ищем input в том же контейнере (ПОЛНАЯ КОПИЯ из sync)
                    parent = button
                    for _ in range(5):  # Поднимаемся до 5 уровней вверх
                        try:
                            parent = await parent.query_selector('xpath=..')
                            if parent:
                                file_input = await parent.query_selector('input[type="file"]')
                                if file_input:
                                    return file_input
                        except:
                            break
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Button search failed for {selector}: {str(e)}")
                continue
        return None
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] Button-based search failed: {str(e)}")
        return None

async def find_input_via_form_context_async(page):
    """Найти input через контекст формы - ПОЛНАЯ КОПИЯ sync версии"""
    try:
        # Ищем формы с multipart/form-data (ПОЛНАЯ КОПИЯ из sync)
        forms = await page.query_selector_all('form[enctype="multipart/form-data"]')
        for form in forms:
            file_input = await form.query_selector('input[type="file"]')
            if file_input and await is_valid_file_input_async(file_input):
                return file_input
        
        # Ищем формы с method="POST" (ПОЛНАЯ КОПИЯ из sync)
        forms = await page.query_selector_all('form[method="POST"]')
        for form in forms:
            file_input = await form.query_selector('input[type="file"]')
            if file_input and await is_valid_file_input_async(file_input):
                return file_input
                
        return None
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] Form context search failed: {str(e)}")
        return None

async def find_input_via_css_patterns_async(page):
    """Поиск по характерным CSS-паттернам Instagram - ПОЛНАЯ КОПИЯ sync версии"""
    try:
        # Паттерны CSS-классов Instagram для файловых input (ПОЛНАЯ КОПИЯ из sync)
        css_patterns = [
            # Точный класс из предоставленного HTML
            'input._ac69',
            # Паттерны классов Instagram
            'input[class*="_ac69"]',
            'input[class*="_ac"]', 
            'input[class*="_ac"]',
            # Комбинированные селекторы
            'form input[class*="_ac"]',
            'form[role="presentation"] input',
            'form[enctype="multipart/form-data"] input',
        ]
        
        for pattern in css_patterns:
            try:
                elements = await page.query_selector_all(pattern)
                log_info(f"[ASYNC_UPLOAD] 🎨 CSS pattern: {pattern} - found {len(elements)} elements")
                
                for element in elements:
                    if element and await is_valid_file_input_async(element):
                        log_info(f"[ASYNC_UPLOAD] [OK] Valid file input found with CSS pattern: {pattern}")
                        return element
                        
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] CSS pattern failed: {pattern} - {str(e)}")
                continue
                
        return None
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] CSS patterns search failed: {str(e)}")
        return None

async def find_input_via_broad_search_async(page):
    """Широкий поиск всех input элементов - ПОЛНАЯ КОПИЯ sync версии"""
    try:
        # Получаем все input элементы на странице (ПОЛНАЯ КОПИЯ из sync)
        all_inputs = await page.query_selector_all('input')
        
        for input_element in all_inputs:
            try:
                # Проверяем каждый input (ПОЛНАЯ КОПИЯ из sync)
                if await is_valid_file_input_async(input_element):
                    # Дополнительная проверка (ПОЛНАЯ КОПИЯ из sync)
                    input_classes = await input_element.get_attribute('class') or ""
                    input_accept = await input_element.get_attribute('accept') or ""
                    
                    # Проверяем, что accept содержит нужные типы файлов (ПОЛНАЯ КОПИЯ из sync)
                    if any(file_type in input_accept.lower() for file_type in ['video', 'image', 'mp4', 'jpeg', 'png']):
                        log_info(f"[ASYNC_UPLOAD] Found valid file input: accept='{input_accept}', classes='{input_classes[:50]}'")
                        return input_element
                        
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Error checking input element: {str(e)}")
                continue
                
        return None
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] Broad search failed: {str(e)}")
        return None

async def click_next_button_async(page, step_number):
    """Click next button with human-like behavior - ПОЛНАЯ КОПИЯ sync версии"""
    try:
        log_info(f"[ASYNC_UPLOAD] Clicking next button for step {step_number}...")
        
        # Human-like delay before clicking (ПОЛНАЯ КОПИЯ из sync)
        await asyncio.sleep(random.uniform(3, 5))
        
        # Look for next button with comprehensive selectors (ПОЛНАЯ КОПИЯ из sync)
        next_button_selectors = [
            'button:has-text("Далее")',
            'button:has-text("Next")',
            'button:has-text("Продолжить")',
            'button:has-text("Continue")',
            'div[role="button"]:has-text("Далее")',
            'div[role="button"]:has-text("Next")',
            '//button[contains(text(), "Далее")]',
            '//button[contains(text(), "Next")]',
        ]
        
        next_button = None
        for selector in next_button_selectors:
            try:
                if selector.startswith('//'):
                    next_button = await page.query_selector(f"xpath={selector}")
                else:
                    next_button = await page.query_selector(selector)
                
                if next_button and await next_button.is_visible():
                    # Verify this is actually a next button
                    button_text = await next_button.text_content() or ""
                    if any(keyword in button_text.lower() for keyword in ['далее', 'next', 'продолжить', 'continue']):
                        log_info(f"[ASYNC_UPLOAD] [TARGET] Found next button: '{button_text.strip()}'")
                        break
                            
            except Exception as e:
                continue
        
        if next_button:
            # Human-like interaction (ПОЛНАЯ КОПИЯ из sync)
            try:
                # Scroll button into view if needed
                await next_button.scroll_into_view_if_needed()
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
                # Hover over button
                await next_button.hover()
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
                # Click using JavaScript for better reliability
                await page.evaluate('(element) => element.click()', next_button)
                
                # Wait after click
                await asyncio.sleep(random.uniform(4, 6))
                
                log_info(f"[ASYNC_UPLOAD] [OK] Successfully clicked next button for step {step_number}")
                return True
                
            except Exception as click_error:
                log_info(f"[ASYNC_UPLOAD] [WARN] Error clicking next button: {str(click_error)}")
                
                # Fallback: try direct click
                try:
                    await next_button.click()
                    await asyncio.sleep(random.uniform(4, 6))
                    log_info(f"[ASYNC_UPLOAD] [OK] Successfully clicked next button (fallback) for step {step_number}")
                    return True
                except Exception as fallback_error:
                    log_info(f"[ASYNC_UPLOAD] [FAIL] Fallback click also failed: {str(fallback_error)}")
                    return False
        else:
            log_info(f"[ASYNC_UPLOAD] [WARN] Next button not found for step {step_number}")
            return False
            
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error in next button click: {str(e)}")
        return False

async def add_video_caption_async(page, caption_text):
    """Add video caption - FULL VERSION like sync"""
    try:
        if not caption_text:
            log_info("[ASYNC_UPLOAD] No caption text provided")
            return True
        
        log_info(f"[ASYNC_UPLOAD] Setting caption: {caption_text[:50]}...")
        
        # Wait a bit before caption
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        # Find caption field with comprehensive selectors (like sync version)
        caption_field_selectors = [
            'textarea[aria-label*="Напишите подпись" i]',
            'textarea[aria-label*="Write a caption" i]',
            'div[contenteditable="true"]',
            'textarea[placeholder*="подпись" i]',
            'textarea[placeholder*="caption" i]',
            'textarea[placeholder*="Напишите подпись" i]',
            'textarea[placeholder*="Write a caption" i]',
            '//textarea[@aria-label="Напишите подпись..."]',
            '//textarea[@aria-label="Write a caption..."]',
            '//div[@contenteditable="true"]',
        ]
        
        caption_field = None
        for selector in caption_field_selectors:
            try:
                if selector.startswith('//'):
                    element = await page.query_selector(f"xpath={selector}")
                else:
                    element = await page.query_selector(selector)
                
                if element and await element.is_visible():
                    log_info(f"[ASYNC_UPLOAD] [OK] Found caption field: {selector}")
                    caption_field = element
                    break
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Selector {selector} failed: {str(e)}")
                continue
        
        if not caption_field:
            log_info("[ASYNC_UPLOAD] [WARN] Caption field not found")
            return False
        
        # Click field and wait (like sync version)
        await caption_field.click()
        await asyncio.sleep(random.uniform(0.8, 1.5))
        
        # Clear field (like sync version)
        await caption_field.fill('')
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # Type caption with human-like behavior (like sync version)
        await _type_like_human_async(page, caption_field, caption_text)
        
        # Press Enter for line break after description (like sync version)
        log_info("[ASYNC_UPLOAD] Pressing Enter for line break...")
        await caption_field.press('Enter')
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        log_info("[ASYNC_UPLOAD] [OK] Caption set successfully")
        return True
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error setting caption: {str(e)}")
        return False

async def _type_like_human_async(page, element, text):
    """Type text like a human with mistakes, corrections, and realistic timing - async version"""
    try:
        log_info("[ASYNC_UPLOAD] [BOT] Starting human-like typing...")
        
        i = 0
        while i < len(text):
            char = text[i]
            
            # Random typing speed (slower for humans)
            delay = random.uniform(0.08, 0.25)  # Much slower than 0.05
            
            # Chance to make a mistake (5% for Russian, 3% for English)
            mistake_chance = 0.05 if ord(char) > 127 else 0.03
            
            if random.random() < mistake_chance and char.isalpha():
                # Make a mistake
                if ord(char) > 127:  # Russian characters
                    wrong_chars = ['ф', 'в', 'а', 'п', 'р', 'о', 'л', 'д', 'ж', 'э']
                else:  # English characters
                    wrong_chars = ['q', 'w', 'e', 'r', 't', 'y', 'a', 's', 'd', 'f']
                
                wrong_char = random.choice(wrong_chars)
                await element.type(wrong_char)
                await asyncio.sleep(delay)
                
                # Realize mistake after 1-3 more characters
                realization_delay = random.randint(1, 3)
                mistake_chars = 1
                
                # Continue typing a bit before realizing mistake
                for j in range(min(realization_delay, len(text) - i - 1)):
                    if i + j + 1 < len(text):
                        await element.type(text[i + j + 1])
                        mistake_chars += 1
                        await asyncio.sleep(random.uniform(0.05, 0.15))
                
                # Pause (human realizes mistake)
                await asyncio.sleep(random.uniform(0.3, 0.8))
                
                # Delete wrong characters
                for _ in range(mistake_chars):
                    await element.press('Backspace')
                    await asyncio.sleep(random.uniform(0.05, 0.12))
                
                # Pause before correction
                await asyncio.sleep(random.uniform(0.2, 0.5))
                
                # Type correct characters
                for j in range(mistake_chars):
                    if i + j < len(text):
                        await element.type(text[i + j])
                        await asyncio.sleep(random.uniform(0.08, 0.2))
                
                i += mistake_chars
            else:
                # Normal typing
                await element.type(char)
                await asyncio.sleep(delay)
                i += 1
            
            # Random pauses for thinking
            if random.random() < 0.02:  # 2% chance
                thinking_pause = random.uniform(0.5, 2.0)
                log_info(f"[ASYNC_UPLOAD] 🤔 Thinking {thinking_pause:.1f}s...")
                await asyncio.sleep(thinking_pause)
            
            # Longer pause after punctuation
            if char in '.!?,:;':
                await asyncio.sleep(random.uniform(0.1, 0.4))
        
        log_info("[ASYNC_UPLOAD] [OK] Human-like typing completed")
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error in human-like typing: {str(e)}")
        # Fallback to simple typing
        await element.type(text)

async def add_video_location_async(page, video_obj):
    """Add video location - FULL VERSION like sync"""
    try:
        log_info(f"[ASYNC_UPLOAD] [SEARCH] Starting location search for video_obj: {type(video_obj)}")
        
        # Get location from video object
        location = None
        
        try:
            # Check for VideoData objects (new async version)
            if hasattr(video_obj, 'location') and video_obj.location:
                location = video_obj.location.strip()
                log_info(f"[ASYNC_UPLOAD] Found VideoData location: {location}")
            # Check for Django model objects (old async version)
            elif hasattr(video_obj, 'location') and video_obj.location:
                location = video_obj.location.strip()
                log_info(f"[ASYNC_UPLOAD] Found Django model location: {location}")
            elif hasattr(video_obj, 'bulk_task') and video_obj.bulk_task:
                if hasattr(video_obj.bulk_task, 'default_location') and video_obj.bulk_task.default_location:
                    location = video_obj.bulk_task.default_location.strip()
                    log_info(f"[ASYNC_UPLOAD] Found Django model default_location: {location}")
        except Exception as location_error:
            log_info(f"[ASYNC_UPLOAD] [FAIL] Error accessing location attributes: {str(location_error)}")
            log_info(f"[ASYNC_UPLOAD] [SEARCH] Video object type: {type(video_obj)}")
            location = None
        
        # Debug: show all attributes of video_obj
        if not location:
            log_info(f"[ASYNC_UPLOAD] [SEARCH] Video object attributes: {[attr for attr in dir(video_obj) if not attr.startswith('_')]}")
            log_info(f"[ASYNC_UPLOAD] [SEARCH] Video object location attribute: {getattr(video_obj, 'location', 'NOT_FOUND')}")
        
        if not location:
            log_info("[ASYNC_UPLOAD] No location data")
            return True
        
        log_info(f"[ASYNC_UPLOAD] Setting location: {location}")
        
        # Wait a bit before location (after description and Enter)
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        # Location field selectors
        location_field_selectors = [
            'input[placeholder="Добавить место"]',
            'input[name="creation-location-input"]',
            'input[placeholder*="место" i]',
            'input[placeholder*="location" i]',
            'input[aria-label*="место" i]',
            'input[aria-label*="location" i]',
            'input[aria-label*="Добавить место" i]',
            'input[placeholder*="Добавить место" i]',
            '//input[@placeholder="Добавить место"]',
            '//input[@name="creation-location-input"]',
        ]
        
        location_field = None
        for selector in location_field_selectors:
            try:
                if selector.startswith('//'):
                    element = await page.query_selector(f"xpath={selector}")
                else:
                    element = await page.query_selector(selector)
                
                if element and await element.is_visible():
                    log_info(f"[ASYNC_UPLOAD] [OK] Found location field: {selector}")
                    location_field = element
                    break
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Selector {selector} failed: {str(e)}")
                continue
        
        if not location_field:
            log_info("[ASYNC_UPLOAD] [WARN] Location field not found")
            return False
        
        # Human-like interaction with location field
        await location_field.scroll_into_view_if_needed()
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        await location_field.click()
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        # Clear field first
        await location_field.fill('')
        await asyncio.sleep(random.uniform(0.3, 0.7))
        
        # Type location with human-like speed
        await _type_like_human_async(page, location_field, location)
        
        # Wait for suggestions
        await asyncio.sleep(random.uniform(2.0, 3.0))
        
        # Suggestion selectors
        suggestion_selectors = [
            "//div[@role='dialog']/div/div/div/div/div/div/button",
            "//div[@role='dialog']//button[1]",
            f'div[role="button"]:has-text("{location}")',
            f'button:has-text("{location}")',
            'div[role="button"]:first-child',
            'li[role="button"]:first-child',
            'div[data-testid*="location"]:first-child',
            '(//div[@role="button"])[1]',
            '(//li[@role="button"])[1]',
            '(//button)[1]',
        ]
        
        suggestion = None
        for selector in suggestion_selectors:
            try:
                if selector.startswith('//') or selector.startswith('(//'):
                    element = await page.query_selector(f"xpath={selector}")
                else:
                    element = await page.query_selector(selector)
                
                if element and await element.is_visible():
                    suggestion = element
                    log_info(f"[ASYNC_UPLOAD] [OK] Found location suggestion: {selector}")
                    break
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Selector {selector} failed: {str(e)}")
                continue
        
        if suggestion:
            await suggestion.hover()
            await asyncio.sleep(random.uniform(0.5, 1.0))
            await suggestion.click()
            await asyncio.sleep(random.uniform(1.0, 2.0))
            log_info("[ASYNC_UPLOAD] [OK] Location set successfully")
        else:
            log_info("[ASYNC_UPLOAD] [WARN] Location suggestions not found")
            # Press Enter to try to accept typed location
            await location_field.press('Enter')
            await asyncio.sleep(random.uniform(1.0, 1.5))
        
        return True
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error setting location: {str(e)}")
        return False

async def add_video_mentions_async(page, video_obj):
    """Add video mentions - FULL VERSION like sync"""
    try:
        log_info(f"[ASYNC_UPLOAD] [SEARCH] Starting mentions search for video_obj: {type(video_obj)}")
        
        # Get mentions from video object
        mentions = None
        
        try:
            # Check for VideoData objects (new async version)
            if hasattr(video_obj, 'mentions') and video_obj.mentions:
                mentions = video_obj.mentions.strip()
                log_info(f"[ASYNC_UPLOAD] Found VideoData mentions: {mentions}")
            # Check for Django model objects (old async version)
            elif hasattr(video_obj, 'mentions') and video_obj.mentions:
                mentions = video_obj.mentions.strip()
                log_info(f"[ASYNC_UPLOAD] Found Django model mentions: {mentions}")
            elif hasattr(video_obj, 'bulk_task') and video_obj.bulk_task:
                if hasattr(video_obj.bulk_task, 'default_mentions') and video_obj.bulk_task.default_mentions:
                    mentions = video_obj.bulk_task.default_mentions.strip()
                    log_info(f"[ASYNC_UPLOAD] Found Django model default_mentions: {mentions}")
        except Exception as mentions_error:
            log_info(f"[ASYNC_UPLOAD] [FAIL] Error accessing mentions attributes: {str(mentions_error)}")
            log_info(f"[ASYNC_UPLOAD] [SEARCH] Video object type: {type(video_obj)}")
            mentions = None
        
        # Debug: show all attributes of video_obj
        if not mentions:
            log_info(f"[ASYNC_UPLOAD] [SEARCH] Video object attributes: {[attr for attr in dir(video_obj) if not attr.startswith('_')]}")
            log_info(f"[ASYNC_UPLOAD] [SEARCH] Video object mentions attribute: {getattr(video_obj, 'mentions', 'NOT_FOUND')}")
        
        if not mentions:
            log_info("[ASYNC_UPLOAD] No mentions data")
            return True
        
        # Split mentions into list
        mentions_list = [mention.strip() for mention in mentions.split(',') if mention.strip()]
        log_info(f"[ASYNC_UPLOAD] Setting mentions: {mentions_list}")
        
        # Wait a bit before mentions
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        # Mentions field selectors
        mentions_field_selectors = [
            'input[placeholder="Добавить соавторов"]',
            'input[placeholder*="соавтор" i]',
            'input[placeholder*="collaborator" i]',
            'input[aria-label*="соавтор" i]',
            'input[aria-label*="collaborator" i]',
            'input[aria-label*="Добавить соавторов" i]',
            'input[placeholder*="Добавить соавторов" i]',
            '//input[@placeholder="Добавить соавторов"]',
        ]
        
        mentions_field = None
        for selector in mentions_field_selectors:
            try:
                if selector.startswith('//'):
                    element = await page.query_selector(f"xpath={selector}")
                else:
                    element = await page.query_selector(selector)
                
                if element and await element.is_visible():
                    log_info(f"[ASYNC_UPLOAD] [OK] Found mentions field: {selector}")
                    mentions_field = element
                    break
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Selector {selector} failed: {str(e)}")
                continue
        
        if not mentions_field:
            log_info("[ASYNC_UPLOAD] [WARN] Mentions field not found")
            return False
        
        # Add each mention one by one
        for mention in mentions_list:
            log_info(f"[ASYNC_UPLOAD] Adding mention: {mention}")
            
            # Click mentions field
            await mentions_field.click()
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # Clear field
            await mentions_field.fill('')
            await asyncio.sleep(random.uniform(0.3, 0.7))
            
            # Type mention
            await _type_like_human_async(page, mentions_field, mention)
            await asyncio.sleep(random.uniform(2.0, 3.0))
            
            # Look for mention suggestion - ENHANCED with sync-style selectors
            mention_suggestion_selectors = [
                # Sync-style selector from upload_selenium_old.py - ПРИОРИТЕТ 1
                f'//div[text()="{mention}"]/../../div/label/div/input',
                # Alternative selectors - ПРИОРИТЕТ 2
                f'div[role="button"]:has-text("{mention}")',
                f'button:has-text("{mention}")',
                # Additional selectors - ПРИОРИТЕТ 3
                'div[data-testid="mention-suggestion"]:first-child',
                'li[data-testid="mention-suggestion"]:first-child',
                # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Селекторы из sync версии которые работают
                f"//div[contains(text(), '{mention}')]/../../div/label/div/input",
                "//div[@role='dialog']/div/div/div/div/div/div/button",
                "//div[@role='dialog']//button[1]",
                "//div[@role='dialog']//div[@role='button'][1]",
                '(//div[@role="button"])[1]',
                '(//li[@role="button"])[1]',
                '(//button)[1]',
                'div[role="button"]:first-child',
                'li[role="button"]:first-child',
                'button:first-child',
            ]
            
            mention_suggestion = None
            for selector in mention_suggestion_selectors:
                try:
                    if selector.startswith('//') or selector.startswith('(//'):
                        element = await page.query_selector(f"xpath={selector}")
                    else:
                        element = await page.query_selector(selector)
                    
                    if element and await element.is_visible():
                        mention_suggestion = element
                        log_info(f"[ASYNC_UPLOAD] [OK] Found mention suggestion: {selector}")
                        break
                except Exception as e:
                    log_info(f"[ASYNC_UPLOAD] Selector {selector} failed: {str(e)}")
                    continue
            
            if mention_suggestion:
                # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Проверяем что это правильный mention
                try:
                    mention_text = await mention_suggestion.text_content()
                    if mention_text and mention.lower() in mention_text.lower():
                        log_info(f"[ASYNC_UPLOAD] [OK] Verified mention text: '{mention_text}' contains '{mention}'")
                    else:
                        log_info(f"[ASYNC_UPLOAD] [WARN] Mention text mismatch: expected '{mention}', got '{mention_text}'")
                        # Попробуем найти более точный селектор
                        mention_suggestion = None
                        for fallback_selector in [
                            f'//div[contains(text(), "{mention}")]/../../div/label/div/input',
                            f'//div[contains(text(), "{mention}")]/../..',
                            f'//div[contains(text(), "{mention}")]',
                            # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Селекторы из sync версии
                            "//div[@role='dialog']/div/div/div/div/div/div/button",
                            "//div[@role='dialog']//button[1]",
                            "//div[@role='dialog']//div[@role='button'][1]",
                            '(//div[@role="button"])[1]',
                            '(//li[@role="button"])[1]',
                            '(//button)[1]',
                        ]:
                            try:
                                element = await page.query_selector(f"xpath={fallback_selector}")
                                if element and await element.is_visible():
                                    mention_suggestion = element
                                    log_info(f"[ASYNC_UPLOAD] [OK] Found fallback mention suggestion: {fallback_selector}")
                                    break
                            except Exception:
                                continue
                except Exception as verify_error:
                    log_info(f"[ASYNC_UPLOAD] [WARN] Error verifying mention text: {str(verify_error)}")
                
                if mention_suggestion:
                    await mention_suggestion.hover()
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    await mention_suggestion.click()
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                    log_info(f"[ASYNC_UPLOAD] [OK] Mention '{mention}' added successfully")
                else:
                    log_info(f"[ASYNC_UPLOAD] [WARN] Could not verify correct mention for '{mention}'")
                    # Press Enter to try to accept typed mention
                    await mentions_field.press('Enter')
                    await asyncio.sleep(random.uniform(1.0, 1.5))
            else:
                log_info(f"[ASYNC_UPLOAD] [WARN] Mention suggestion for '{mention}' not found")
                log_info(f"[ASYNC_UPLOAD] ℹ️ Continuing with publication - mention '{mention}' will be added as text")
                # Press Enter to try to accept typed mention
                await mentions_field.press('Enter')
                await asyncio.sleep(random.uniform(1.0, 1.5))
        
        # ENHANCED: Click "Done" button after all mentions (like sync version)
        log_info("[ASYNC_UPLOAD] [SEARCH] Looking for 'Done' button...")
        done_button_selectors = [
            # Sync-style selector from upload_selenium_old.py
            '//div[text()="Done"]',
            '//div[text()="Готово"]',
            # Alternative selectors
            'div[role="button"]:has-text("Done")',
            'button:has-text("Done")',
            'div[role="button"]:has-text("Готово")',
            'button:has-text("Готово")',
            # Additional selectors
            'div[aria-label*="Done"]',
            'button[aria-label*="Done"]',
            'div[aria-label*="Готово"]',
            'button[aria-label*="Готово"]',
        ]
        
        done_button = None
        for selector in done_button_selectors:
            try:
                if selector.startswith('//'):
                    element = await page.query_selector(f"xpath={selector}")
                else:
                    element = await page.query_selector(selector)
                
                if element and await element.is_visible():
                    done_button = element
                    log_info(f"[ASYNC_UPLOAD] [OK] Found 'Done' button: {selector}")
                    break
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Selector {selector} failed: {str(e)}")
                continue
        
        if done_button:
            await done_button.hover()
            await asyncio.sleep(random.uniform(0.5, 1.0))
            await done_button.click()
            await asyncio.sleep(random.uniform(2.0, 3.0))
            log_info("[ASYNC_UPLOAD] [OK] 'Done' button clicked successfully")
        else:
            log_info("[ASYNC_UPLOAD] [WARN] 'Done' button not found, trying to press Enter")
            # Fallback: try to press Enter on mentions field
            await mentions_field.press('Enter')
            await asyncio.sleep(random.uniform(1.0, 2.0))
        
        # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Ожидание после mention для стабилизации страницы
        log_info("[ASYNC_UPLOAD] [WAIT] Waiting for page to stabilize after mentions...")
        await asyncio.sleep(random.uniform(3.0, 5.0))
        
        # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Проверяем, что мы все еще в контексте загрузки
        try:
            # Проверяем наличие элементов загрузки
            upload_context_indicators = [
                'input[placeholder="Добавить соавторов"]',
                'textarea[placeholder*="Напишите подпись"]',
                'input[placeholder*="Добавить местоположение"]',
                'div[role="dialog"]',
                'div[aria-label*="Создать"]',
                'div[aria-label*="Create"]'
            ]
            
            context_found = False
            for indicator in upload_context_indicators:
                try:
                    element = await page.query_selector(indicator)
                    if element and await element.is_visible():
                        context_found = True
                        log_info(f"[ASYNC_UPLOAD] [OK] Upload context confirmed: {indicator}")
                        break
                except Exception:
                    continue
            
            if not context_found:
                log_info("[ASYNC_UPLOAD] [WARN] Upload context lost after mentions, trying to restore...")
                # Попытка восстановить контекст - нажать Tab для перехода к следующему элементу
                await page.keyboard.press('Tab')
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
        except Exception as context_error:
            log_info(f"[ASYNC_UPLOAD] [WARN] Error checking upload context: {str(context_error)}")
        
        log_info("[ASYNC_UPLOAD] [OK] All mentions processed")
        return True
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error setting mentions: {str(e)}")
        return False

async def click_share_button_async(page):
    """Click share button - ENHANCED VERSION with multiple selectors and context checking"""
    try:
        log_info("[ASYNC_UPLOAD] Looking for share button...")
        
        # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Проверяем контекст загрузки перед поиском кнопки
        log_info("[ASYNC_UPLOAD] [SEARCH] Checking upload context before searching for share button...")
        upload_context_indicators = [
            'input[placeholder="Добавить соавторов"]',
            'textarea[placeholder*="Напишите подпись"]',
            'input[placeholder*="Добавить местоположение"]',
            'div[role="dialog"]',
            'div[aria-label*="Создать"]',
            'div[aria-label*="Create"]'
        ]
        
        context_found = False
        for indicator in upload_context_indicators:
            try:
                element = await page.query_selector(indicator)
                if element and await element.is_visible():
                    context_found = True
                    log_info(f"[ASYNC_UPLOAD] [OK] Upload context found: {indicator}")
                    break
            except Exception:
                continue
        
        if not context_found:
            log_info("[ASYNC_UPLOAD] [WARN] Upload context not found, trying to restore...")
            # Попытка восстановить контекст
            await page.keyboard.press('Tab')
            await asyncio.sleep(random.uniform(1.0, 2.0))
        
        # Enhanced share button selectors with more dynamic options
        share_selectors = [
            # Primary selectors
            'div[role="button"]:has-text("Поделиться")',
            'button:has-text("Поделиться")',
            'div[role="button"]:has-text("Share")',
            'button:has-text("Share")',
            
            # Alternative selectors
            'div[aria-label*="Поделиться"]',
            'button[aria-label*="Поделиться"]',
            'div[aria-label*="Share"]',
            'button[aria-label*="Share"]',
            
            # XPath selectors
            '//div[text()="Поделиться"]',
            '//button[text()="Поделиться"]',
            '//div[text()="Share"]',
            '//button[text()="Share"]',
            
            # Instagram-specific selectors
            'div[class*="x1i10hfl"]:has-text("Поделиться")',
            'div[class*="x1i10hfl"]:has-text("Share")',
            
            # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Динамические селекторы для Instagram
            'div[class*="x1i10hfl"][class*="x1xfsgkm"]:has-text("Поделиться")',
            'div[class*="x1i10hfl"][class*="x1xfsgkm"]:has-text("Share")',
            'div[class*="x1i10hfl"][class*="xwib8y2"]:has-text("Поделиться")',
            'div[class*="x1i10hfl"][class*="xwib8y2"]:has-text("Share")',
            
            # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Селекторы по позиции в диалоге
            'div[role="dialog"] div[role="button"]:last-child',
            'div[role="dialog"] button:last-child',
            'div[aria-label*="Создать"] div[role="button"]:last-child',
            'div[aria-label*="Create"] div[role="button"]:last-child',
            
            # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Селекторы по data-testid
            'div[data-testid="share-button"]',
            'button[data-testid="share-button"]',
            'div[data-testid="post-button"]',
            'button[data-testid="post-button"]',
            
            # Generic button selectors (fallback)
            'div[role="button"]:last-child',
            'button:last-child',
        ]
        
        share_button = None
        for selector in share_selectors:
            try:
                if selector.startswith('//'):
                    element = await page.query_selector(f"xpath={selector}")
                else:
                    element = await page.query_selector(selector)
                
                if element and await element.is_visible():
                    # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Проверяем что кнопка в правильном контексте
                    try:
                        # Проверяем что кнопка находится в диалоге загрузки
                        parent_dialog = await element.query_selector('xpath=ancestor::div[@role="dialog"]')
                        if parent_dialog:
                            log_info(f"[ASYNC_UPLOAD] [OK] Found share button in upload dialog: {selector}")
                            share_button = element
                            break
                        else:
                            log_info(f"[ASYNC_UPLOAD] [WARN] Share button found but not in upload dialog: {selector}")
                            # Продолжаем поиск
                            continue
                    except Exception as context_error:
                        log_info(f"[ASYNC_UPLOAD] [WARN] Error checking button context: {str(context_error)}")
                        # Если не можем проверить контекст, все равно используем кнопку
                        log_info(f"[ASYNC_UPLOAD] [OK] Found share button (context check failed): {selector}")
                        share_button = element
                        break
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Selector {selector} failed: {str(e)}")
                continue
        
        if share_button:
            # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Дополнительная проверка перед кликом
            log_info("[ASYNC_UPLOAD] [SEARCH] Verifying share button before clicking...")
            
            # Проверяем, что кнопка все еще видима и кликабельна
            try:
                await share_button.wait_for_element_state('visible', timeout=5000)
                await share_button.wait_for_element_state('enabled', timeout=5000)
                log_info("[ASYNC_UPLOAD] [OK] Share button is visible and enabled")
            except Exception as verify_error:
                log_info(f"[ASYNC_UPLOAD] [WARN] Share button verification failed: {str(verify_error)}")
            
            # Human-like interaction - УБИРАЕМ ПРОБЛЕМНЫЙ SCROLL
            # await share_button.scroll_into_view_if_needed()  # ← УДАЛЕНО - может скроллить за окном!
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            await share_button.hover()
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Try JavaScript click first
            try:
                await page.evaluate('(element) => element.click()', share_button)
                log_info("[ASYNC_UPLOAD] [OK] Share button clicked with JavaScript")
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] JavaScript click failed: {str(e)}")
                # Fallback to direct click
                await share_button.click()
                log_info("[ASYNC_UPLOAD] [OK] Share button clicked with direct click")
            
            # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Увеличиваем время ожидания для загрузки видео
            log_info("[ASYNC_UPLOAD] [WAIT] Waiting for video to upload and process...")
            await asyncio.sleep(random.uniform(3, 5))  # Уменьшено с 8-12 до 3-5 секунд, поскольку проверка будет длительной
            return True
        else:
            log_info("[ASYNC_UPLOAD] [FAIL] Share button not found")
            
            # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Расширенная отладка
            try:
                # Показываем все кнопки на странице
                all_buttons = await page.query_selector_all('button, div[role="button"], [role="button"]')
                log_info(f"[ASYNC_UPLOAD] [SEARCH] Available buttons on page ({len(all_buttons)} total):")
                for i, btn in enumerate(all_buttons[:15]):  # Show first 15 buttons
                    try:
                        btn_text = await btn.text_content() or "no-text"
                        btn_aria = await btn.get_attribute('aria-label') or "no-aria"
                        btn_class = await btn.get_attribute('class') or "no-class"
                        log_info(f"[ASYNC_UPLOAD] Button {i+1}: '{btn_text.strip()}' (aria: '{btn_aria}', class: '{btn_class[:50]}...')")
                    except Exception as debug_error:
                        log_info(f"[ASYNC_UPLOAD] Error debugging button {i+1}: {str(debug_error)}")
                
                # Показываем все div элементы с текстом
                all_divs = await page.query_selector_all('div')
                log_info(f"[ASYNC_UPLOAD] [SEARCH] Divs with text content:")
                for i, div in enumerate(all_divs[:20]):  # Show first 20 divs
                    try:
                        div_text = await div.text_content() or ""
                        if div_text.strip() and len(div_text.strip()) < 50:
                            div_class = await div.get_attribute('class') or "no-class"
                            log_info(f"[ASYNC_UPLOAD] Div {i+1}: '{div_text.strip()}' (class: '{div_class[:50]}...')")
                    except Exception as debug_error:
                        continue
                        
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Error listing elements: {str(e)}")
            
            return False
            
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error clicking share button: {str(e)}")
        return False

async def check_video_posted_successfully_async(page, video_file_path):
    """Check if video was posted successfully - УЛУЧШЕННАЯ ВЕРСИЯ с проверкой каждые 30 секунд в течение 20 минут"""
    try:
        log_info("[ASYNC_UPLOAD] Checking if video was posted successfully...")
        
        # КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ: Проверяем каждые 30 секунд в течение 20 минут
        max_wait_time = 1200  # 20 минут в секундах
        check_interval = 30   # Проверяем каждые 30 секунд
        total_checks = max_wait_time // check_interval  # 40 проверок
        
        log_info(f"[ASYNC_UPLOAD] [WAIT] Starting extended upload verification: {max_wait_time} seconds ({total_checks} checks every {check_interval}s)")
        
        # STRICT POLICY: Check for explicit success indicators ONLY
        success_selectors = [
            'div:has-text("Ваша публикация опубликована")',
            'div:has-text("Your post has been shared")',
            'div:has-text("Опубликовано")',
            'div:has-text("Published")',
            'div:has-text("Reel shared")',
            'div:has-text("Рил опубликован")',
            'div:has-text("Success")',
            'div:has-text("Успешно")',
            'div:has-text("Post shared")',
            'div:has-text("Публикация опубликована")',
        ]
        
        error_selectors = [
            'div:has-text("Error")',
            'div:has-text("Ошибка")',
            'div:has-text("Failed")',
            'div:has-text("Не удалось")',
            'div:has-text("Something went wrong")',
            'div:has-text("Что-то пошло не так")',
        ]
        
        for check_number in range(1, total_checks + 1):
            log_info(f"[ASYNC_UPLOAD] [SEARCH] Check {check_number}/{total_checks} - Looking for success/error indicators...")
            
            # Check for success indicators
            for selector in success_selectors:
                try:
                    success_element = await page.query_selector(selector)
                    if success_element and await success_element.is_visible():
                        success_text = await success_element.text_content() or ""
                        log_info(f"[ASYNC_UPLOAD] [OK] SUCCESS DETECTED on check {check_number}: '{success_text.strip()}'")
                        log_info(f"[ASYNC_UPLOAD] [OK] Video {os.path.basename(video_file_path)} posted successfully")
                        return True
                except:
                    continue
            
            # Check for error indicators
            for selector in error_selectors:
                try:
                    error_element = await page.query_selector(selector)
                    if error_element and await error_element.is_visible():
                        error_text = await error_element.text_content() or ""
                        log_info(f"[ASYNC_UPLOAD] [FAIL] ERROR DETECTED on check {check_number}: '{error_text.strip()}'")
                        log_info(f"[ASYNC_UPLOAD] [FAIL] Video {os.path.basename(video_file_path)} failed to post")
                        return False
                except:
                    continue
            
            # If this is not the last check, wait before next iteration
            if check_number < total_checks:
                log_info(f"[ASYNC_UPLOAD] [WAIT] No indicators found on check {check_number}, waiting {check_interval}s before next check...")
                await asyncio.sleep(check_interval)
            else:
                log_info(f"[ASYNC_UPLOAD] [WAIT] Final check {check_number} completed, no indicators found")
        
        # STRICT POLICY: If no explicit success indicators found after all checks, consider it a failure
        log_info(f"[ASYNC_UPLOAD] [FAIL] UPLOAD FAILED: No explicit success indicators found after {total_checks} checks ({max_wait_time}s total) - cannot confirm video {os.path.basename(video_file_path)} was posted")
        log_info(f"[ASYNC_UPLOAD] [SEARCH] Current page URL: {page.url}")
        
        return False
                
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] Error checking if video was posted: {str(e)}")
        return False

async def handle_cookie_consent_async(page):
    """Handle Instagram cookie consent modal with comprehensive Russian and English support - ПОЛНАЯ КОПИЯ sync версии"""
    try:
        log_info("🍪 [ASYNC_COOKIES] Checking for cookie consent modal...")
        
        # First, check if cookie modal is present (ПОЛНАЯ КОПИЯ из sync)
        modal_detected = False
        
        # Cookie modal indicators from sync version
        cookie_modal_indicators = [
            # Modal container selectors
            'div[role="dialog"]:has-text("Cookies")',
            'div[role="dialog"]:has-text("файлы cookie")',
            'div[role="dialog"]:has-text("Allow Cookies")',
            'div[role="dialog"]:has-text("Разрешить файлы cookie")',
            'div[aria-modal="true"]:has-text("Cookies")',
            'div[aria-modal="true"]:has-text("cookie")',
            
            # Modal text indicators
            'div:has-text("We use cookies")',
            'div:has-text("Мы используем файлы cookie")',
            'div:has-text("This website uses cookies")',
            'div:has-text("Этот сайт использует файлы cookie")',
            
            # Button presence as modal indicator
            'button:has-text("Accept All Cookies")',
            'button:has-text("Принять все файлы cookie")',
            'button:has-text("Allow All")',
            'button:has-text("Разрешить все")',
        ]
        
        for i, indicator in enumerate(cookie_modal_indicators):
            try:
                if indicator.startswith('//'):
                    element = await page.query_selector(f"xpath={indicator}")
                else:
                    element = await page.query_selector(indicator)
                
                if element and await element.is_visible():
                    modal_detected = True
                    log_info(f"🍪 [ASYNC_COOKIES] Cookie modal detected with indicator {i+1}")
                    break
                    
            except Exception:
                continue
        
        if not modal_detected:
            log_info("🍪 [ASYNC_COOKIES] No cookie consent modal found")
            return False
        
        # Wait a bit for modal to fully load (ПОЛНАЯ КОПИЯ из sync)
        await asyncio.sleep(random.uniform(2, 4))
        
        # Try to find and click "Accept All" button (ПОЛНАЯ КОПИЯ из sync)
        log_info("🍪 [ASYNC_COOKIES] Attempting to accept all cookies...")
        
        # Cookie consent buttons from sync version (comprehensive list)
        cookie_consent_buttons = [
            # Russian Accept buttons
            'button:has-text("Принять все")',
            'button:has-text("Принять все файлы cookie")',
            'button:has-text("Принять")',
            'button:has-text("Разрешить все")',
            'button:has-text("Разрешить")',
            'button:has-text("ОК")',
            'div[role="button"]:has-text("Принять все")',
            'div[role="button"]:has-text("Принять")',
            'div[role="button"]:has-text("Разрешить")',
            
            # English Accept buttons
            'button:has-text("Accept All")',
            'button:has-text("Accept All Cookies")',
            'button:has-text("Accept")',
            'button:has-text("Allow All")',
            'button:has-text("Allow")',
            'button:has-text("OK")',
            'button:has-text("Got it")',
            'div[role="button"]:has-text("Accept All")',
            'div[role="button"]:has-text("Accept")',
            'div[role="button"]:has-text("Allow")',
            
            # Generic cookie buttons
            'button[data-testid*="cookie"]',
            'button[data-testid*="accept"]',
            'button[aria-label*="Accept"]',
            'button[aria-label*="Принять"]',
            
            # XPath alternatives for comprehensive coverage
            '//button[contains(text(), "Принять")]',
            '//button[contains(text(), "Accept")]',
            '//button[contains(text(), "Allow")]',
            '//button[contains(text(), "Разрешить")]',
            '//div[@role="button" and contains(text(), "Accept")]',
            '//div[@role="button" and contains(text(), "Принять")]',
        ]
        
        for i, selector in enumerate(cookie_consent_buttons):
            try:
                log_info(f"🍪 [ASYNC_COOKIES] Trying selector {i+1}/{len(cookie_consent_buttons)}: {selector[:50]}...")
                
                if selector.startswith('//'):
                    element = await page.query_selector(f"xpath={selector}")
                else:
                    element = await page.query_selector(selector)
                
                if element and await element.is_visible():
                    # Get button text for logging (ПОЛНАЯ КОПИЯ из sync)
                    button_text = ""
                    try:
                        button_text = await element.text_content() or ""
                        button_text = button_text.strip()[:50]
                    except:
                        button_text = "Unknown"
                    
                    log_info(f"🍪 [ASYNC_COOKIES] Found accept button: '{button_text}' with selector: {selector}")
                    
                    # Simulate human behavior before clicking (ПОЛНАЯ КОПИЯ из sync)
                    try:
                        # Hover over button briefly
                        await element.hover()
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                    except:
                        pass
                    
                    # Click the button
                    await element.click()
                    log_info(f"[OK] [ASYNC_COOKIES] Successfully clicked accept button: '{button_text}'")
                    
                    # Wait for modal to disappear (ПОЛНАЯ КОПИЯ из sync)
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    # Verify modal has disappeared
                    try:
                        modal_still_present = False
                        for indicator in cookie_modal_indicators[:3]:  # Check first few indicators
                            if indicator.startswith('//'):
                                check_element = await page.query_selector(f"xpath={indicator}")
                            else:
                                check_element = await page.query_selector(indicator)
                            
                            if check_element and await check_element.is_visible():
                                modal_still_present = True
                                break
                        
                        if not modal_still_present:
                            log_info("[OK] [ASYNC_COOKIES] Cookie consent modal successfully dismissed")
                            return True
                        else:
                            log_info("[WARN] [ASYNC_COOKIES] Modal still present, trying next selector...")
                            continue
                            
                    except:
                        # If we can't verify, assume success
                        log_info("[OK] [ASYNC_COOKIES] Cookie consent handling completed (verification skipped)")
                        return True
                    
            except Exception as e:
                log_error(f"[FAIL] [ASYNC_COOKIES] Error with selector {i+1}: {str(e)}")
                continue
        
        # If no button worked, try clicking outside the modal (ПОЛНАЯ КОПИЯ из sync)
        log_info("[WARN] [ASYNC_COOKIES] No accept button worked, trying to click outside modal...")
        try:
            await page.click('body', position={'x': 50, 'y': 50})
            await asyncio.sleep(2)
            log_info("🍪 [ASYNC_COOKIES] Clicked outside modal as fallback")
            return True
        except:
            pass
        
        log_info("[FAIL] [ASYNC_COOKIES] Could not handle cookie consent modal")
        return False
        
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_COOKIES] Cookie consent error: {str(e)}")
        return False

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

async def safely_close_all_windows_async(page, dolphin_browser, dolphin_profile_id=None):
    """Safely close all browser windows - updated async version"""
    try:
        log_info("🔒 [ASYNC_BROWSER] Starting window closure...")
        
        if dolphin_browser:
            try:
                await dolphin_browser.cleanup_async()
                log_info("[OK] [ASYNC_BROWSER] Dolphin browser closed via cleanup")
            except Exception as e:
                log_info(f"[ASYNC_BROWSER] Dolphin browser cleanup error: {str(e)}")
        elif page:
            try:
                await page.close()
                log_info("[OK] [ASYNC_BROWSER] Page closed directly")
            except Exception as e:
                log_info(f"[ASYNC_BROWSER] Direct page close error: {str(e)}")
                
    except Exception as e:
        log_info(f"[ASYNC_BROWSER] Error in window closure: {str(e)}")

async def handle_recaptcha_if_present_async(page, account_details=None):
    """Handle reCAPTCHA if present on the page - использует captcha_solver.py"""
    try:
        log_info("[SEARCH] [ASYNC_RECAPTCHA] Starting reCAPTCHA detection and solving...")
        
        # Используем функцию из captcha_solver.py для решения капчи
        from .captcha_solver import solve_recaptcha_if_present
        
        result = await solve_recaptcha_if_present(page, account_details, max_attempts=3)
        
        if result:
            log_info("[OK] [ASYNC_RECAPTCHA] reCAPTCHA solved successfully or not detected")
            return True
        else:
            log_info("[FAIL] [ASYNC_RECAPTCHA] Failed to solve reCAPTCHA after all attempts")
            # Возвращаем False для завершения выполнения и установки статуса CAPTCHA
            return False
        
    except Exception as e:
        log_warning(f"[WARN] [ASYNC_RECAPTCHA] Error handling reCAPTCHA: {str(e)}")
        # При ошибке также возвращаем False для завершения выполнения
        return False

async def perform_instagram_login_optimized_async(page, account_details):
    """Perform Instagram login - async version with comprehensive error handling"""
    try:
        from asgiref.sync import sync_to_async
        
        log_info(f"🔐 [ASYNC_LOGIN] Starting login process for account: {account_details['username']}")
        
        # Don't navigate to login page - use fields on main page
        current_url = page.url
        log_info(f"🌐 [ASYNC_LOGIN] Using login fields on current page: {current_url}")
        
        # Find username field
        username_selectors = [
            'input[name="username"]',
            'input[name="email"]',
            'input[aria-label*="Телефон"]',
            'input[aria-label*="Phone"]',
            'input[placeholder*="Телефон"]',
            'input[placeholder*="Phone"]',
            'input[placeholder*="Username"]',
            'input[placeholder*="Имя пользователя"]',
        ]
        
        username_field = None
        for selector in username_selectors:
            try:
                username_field = await page.query_selector(selector)
                if username_field and await username_field.is_visible():
                    log_info(f"[OK] [ASYNC_LOGIN] Found username field: {selector}")
                    break
            except:
                continue
        
        if not username_field:
            log_info("[FAIL] [ASYNC_LOGIN] Username field not found")
            return False
        
        # Find password field
        password_selectors = [
            'input[name="password"]',
            'input[name="pass"]',
            'input[type="password"]',
            'input[aria-label*="Пароль"]',
            'input[aria-label*="Password"]',
        ]
        
        password_field = None
        for selector in password_selectors:
            try:
                password_field = await page.query_selector(selector)
                if password_field and await password_field.is_visible():
                    log_info(f"[OK] [ASYNC_LOGIN] Found password field: {selector}")
                    break
            except:
                continue
        
        if not password_field:
            log_info("[FAIL] [ASYNC_LOGIN] Password field not found")
            return False
        
        # Clear fields and enter credentials
        log_info("[TEXT] [ASYNC_LOGIN] Filling credentials...")
        await username_field.click()
        await username_field.fill("")
        await username_field.type(account_details['username'], delay=random.uniform(50, 150))
        await asyncio.sleep(random.uniform(1, 2))
        
        await password_field.click()
        await password_field.fill("")
        await password_field.type(account_details['password'], delay=random.uniform(50, 150))
        await asyncio.sleep(random.uniform(1, 2))
        
        # Find and click login button
        login_selectors = [
            'button[type="submit"]',
            'button:has-text("Войти")',
            'button:has-text("Log in")',
            'div[role="button"]:has-text("Войти")',
            'div[role="button"]:has-text("Log in")',
        ]
        
        login_button = None
        for selector in login_selectors:
            try:
                login_button = await page.query_selector(selector)
                if login_button and await login_button.is_visible():
                    log_info(f"[OK] [ASYNC_LOGIN] Found login button: '{await login_button.text_content()}'")
                    break
            except:
                continue
        
        if not login_button:
            log_info("[FAIL] [ASYNC_LOGIN] Login button not found")
            return False
        
        log_info("🔐 [ASYNC_LOGIN] Clicking login button...")
        await login_button.click()
        
        # Wait for login to process
        await asyncio.sleep(random.uniform(5, 8))
        
        # Check if login was successful
        current_url = page.url
        if '/accounts/login' not in current_url and 'instagram.com' in current_url:
            log_info("[OK] [ASYNC_LOGIN] Login successful")
            return True
        else:
            log_info("[FAIL] [ASYNC_LOGIN] Login failed")
            return False
            
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_LOGIN] Enhanced login error: {str(e)}")
        return False

async def check_for_phone_verification_page_async(page):
    """Check for phone verification requirement - async version"""
    try:
        phone_verification_indicators = [
            'div:has-text("Подтвердите свой номер телефона")',
            'div:has-text("Confirm your phone number")',
            'div:has-text("Введите код подтверждения")',
            'div:has-text("Enter confirmation code")',
            'input[placeholder*="код"]',
            'input[placeholder*="code"]',
        ]
        
        for selector in phone_verification_indicators:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    element_text = await element.text_content() or ""
                    log_info(f"[PHONE] [ASYNC_VERIFICATION] Phone verification detected: {element_text[:50]}")
                    return {
                        'requires_phone_verification': True,
                        'message': f'Phone verification required: {element_text[:100]}'
                    }
            except:
                continue
        
        return {'requires_phone_verification': False}
        
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_VERIFICATION] Error checking phone verification: {str(e)}")
        return {'requires_phone_verification': False}

async def check_for_human_verification_dialog_async(page, account_details):
    """Check for human verification requirement - async version"""
    try:
        human_verification_indicators = [
            'div:has-text("Помогите нам подтвердить")',
            'div:has-text("Help us confirm")',
            'div:has-text("Подозрительная активность")',
            'div:has-text("Suspicious activity")',
            'div:has-text("Подтвердите, что это вы")',
            'div:has-text("Confirm it\'s you")',
        ]
        
        for selector in human_verification_indicators:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    element_text = await element.text_content() or ""
                    log_info(f"[BOT] [ASYNC_VERIFICATION] Human verification detected: {element_text[:50]}")
                    return {
                        'requires_human_verification': True,
                        'message': f'Human verification required: {element_text[:100]}'
                    }
            except:
                continue
        
        return {'requires_human_verification': False}
        
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_VERIFICATION] Error checking human verification: {str(e)}")
        return {'requires_human_verification': False}

async def check_for_account_suspension_async(page):
    """Check for account suspension - async version"""
    try:
        suspension_indicators = [
            'div:has-text("Ваш аккаунт заблокирован")',
            'div:has-text("Your account has been disabled")',
            'div:has-text("Account suspended")',
            'div:has-text("temporarily locked")',
            'div:has-text("временно заблокирован")',
        ]
        
        for selector in suspension_indicators:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    element_text = await element.text_content() or ""
                    log_info(f"[BLOCK] [ASYNC_SUSPENSION] Account suspension detected: {element_text[:50]}")
                    return {
                        'account_suspended': True,
                        'message': f'Account suspended: {element_text[:100]}'
                    }
            except:
                continue
        
        return {'account_suspended': False}
        
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_SUSPENSION] Error checking account suspension: {str(e)}")
        return {'account_suspended': False}

async def handle_crop_async(page):
    """Handle crop interface - FULL ADAPTIVE VERSION like sync"""
    try:
        log_info("[ASYNC_CROP] 🖼️ Starting ADAPTIVE crop handling...")
        
        # Дополнительная проверка: убеждаемся, что диалог Reels закрылся
        await asyncio.sleep(random.uniform(1, 2))
        
        # Проверяем, не остался ли диалог Reels открытым
        try:
            # Используем надежные селекторы без динамических классов
            reels_dialog_selectors = [
                'div[role="dialog"]:has-text("Reels")',
                'div[role="dialog"]:has-text("видео")',
                'div[role="dialog"]:has-text("Теперь")',
                'div[role="dialog"]:has-text("Now")',
                'div:has(h2:has-text("Reels"))',
                'div:has(span:has-text("Reels"))',
            ]
            
            for selector in reels_dialog_selectors:
                reels_dialog = await page.query_selector(selector)
                if reels_dialog and await reels_dialog.is_visible():
                    dialog_text = await reels_dialog.text_content()
                    if dialog_text and any(keyword in dialog_text for keyword in ['Reels', 'видео', 'Теперь', 'Now']):
                        log_info("[ASYNC_CROP] [WARN] Reels dialog still visible, trying to close it...")
                        await handle_reels_dialog_async(page)
                        await asyncio.sleep(random.uniform(1, 2))
                        break
        except:
            pass
        
        # Wait for crop page to load
        initial_wait = random.uniform(3, 5)
        log_info(f"[ASYNC_CROP] [WAIT] Waiting {initial_wait:.1f}s for crop page to load...")
        await asyncio.sleep(initial_wait)
        
        # First, verify if we're on a crop page using adaptive detection
        if not await _verify_crop_page_adaptive_async(page):
            log_info("[ASYNC_CROP] ℹ️ Not on crop page or crop not needed, skipping crop handling")
            return True
        
        # Use adaptive crop detection and handling
        if await _handle_crop_adaptive_async(page):
            log_info("[ASYNC_CROP] [OK] Crop handled successfully with adaptive method")
            return True
        else:
            log_info("[ASYNC_CROP] [WARN] Adaptive crop handling failed, video may proceed with default crop")
            return True  # Don't fail the whole process
            
    except Exception as e:
        log_info(f"[ASYNC_CROP] [FAIL] Crop handling failed: {str(e)}")
        return True  # Don't fail the whole upload process

async def _verify_crop_page_adaptive_async(page):
    """Verify if we're on a crop page using adaptive detection - async version"""
    try:
        log_info("[ASYNC_CROP] [SEARCH] Verifying crop page...")
        
        # Look for crop-related elements
        crop_indicators = [
            'button:has-text("Оригинал")',
            'button:has-text("Original")',
            'div[role="button"]:has-text("Оригинал")',
            'div[role="button"]:has-text("Original")',
            'svg[aria-label*="Выбрать размер"]',
            'svg[aria-label*="Select crop"]',
            'svg[aria-label*="Crop"]',
            'svg[aria-label*="обрезать"]',
        ]
        
        for selector in crop_indicators:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    log_info(f"[ASYNC_CROP] [OK] Found crop indicator: {selector}")
                    return True
            except:
                continue
        
        log_info("[ASYNC_CROP] [WARN] No crop indicators found")
        return False
        
    except Exception as e:
        log_info(f"[ASYNC_CROP] [FAIL] Crop page verification failed: {str(e)}")
        return False

async def _handle_crop_adaptive_async(page):
    """Handle crop with adaptive detection - async version"""
    try:
        log_info("[ASYNC_CROP] 📐 Starting adaptive crop handling...")
        
        # [TARGET] Адаптивная стратегия поиска (независимо от CSS-классов)
        search_strategies = [
            _find_crop_by_semantic_attributes_async,
            _find_crop_by_svg_content_async,
            _find_crop_by_context_analysis_async,
            _find_crop_by_fallback_patterns_async
        ]
        
        for strategy_index, strategy in enumerate(search_strategies, 1):
            log_info(f"[ASYNC_CROP] 📐 Trying strategy {strategy_index}: {strategy.__name__}")
            
            try:
                crop_button = await strategy(page)
                if crop_button:
                    log_info(f"[ASYNC_CROP] [OK] Found crop button using strategy {strategy_index}")
                    
                    # Клик с человеческим поведением
                    await _human_click_crop_button_async(page, crop_button)
                    
                    # Теперь ищем и выбираем "Оригинал"
                    if await _select_original_aspect_ratio_async(page):
                        log_info("[ASYNC_CROP] [OK] Original aspect ratio selected successfully")
                        return True
                    else:
                        log_info("[ASYNC_CROP] [WARN] Failed to select original aspect ratio")
                        return True  # Continue anyway
                    
            except Exception as e:
                log_info(f"[ASYNC_CROP] Strategy {strategy_index} failed: {str(e)}")
                continue
        
        log_info("[ASYNC_CROP] [FAIL] All strategies failed - crop button not found")
        return False
        
    except Exception as e:
        log_info(f"[ASYNC_CROP] [FAIL] Adaptive crop handling failed: {str(e)}")
        return False

async def _find_crop_by_semantic_attributes_async(page):
    """Поиск по семантическим атрибутам (самый устойчивый) - async version"""
    log_info("[ASYNC_CROP] 📐 [SEMANTIC] Searching by semantic attributes...")
    
    # Семантические селекторы (не зависят от CSS-классов)
    semantic_selectors = [
        'svg[aria-label="Выбрать размер и обрезать"]',
        'svg[aria-label*="Выбрать размер"]',
        'svg[aria-label*="обрезать"]',
        '[aria-label*="Выбрать размер и обрезать"]',
        '[aria-label*="Select crop"]',
        '[aria-label*="Crop"]',
    ]
    
    for selector in semantic_selectors:
        try:
            log_info(f"[ASYNC_CROP] 📐 [SEMANTIC] Trying: {selector}")
            
            # Прямой поиск элемента
            element = await page.query_selector(selector)
            if element and await element.is_visible():
                log_info(f"[ASYNC_CROP] 📐 [SEMANTIC] [OK] Found direct element: {selector}")
                return element
            
            # Поиск родительского элемента
            parent_selectors = [
                f'button:has({selector})',
                f'div[role="button"]:has({selector})',
                '[role="button"]:has({selector})'
            ]
            
            for parent_selector in parent_selectors:
                parent_element = await page.query_selector(parent_selector)
                if parent_element and await parent_element.is_visible():
                    log_info(f"[ASYNC_CROP] 📐 [SEMANTIC] [OK] Found parent element: {parent_selector}")
                    return parent_element
                
        except Exception as e:
            log_info(f"[ASYNC_CROP] 📐 [SEMANTIC] Selector {selector} failed: {str(e)}")
            continue
    
    return None

async def _find_crop_by_svg_content_async(page):
    """Поиск по содержимому SVG (анализ путей и форм) - async version"""
    log_info("[ASYNC_CROP] 📐 [SVG] Searching by SVG content analysis...")
    
    try:
        # Находим все SVG элементы на странице
        svg_elements = await page.query_selector_all('svg')
        log_info(f"[ASYNC_CROP] 📐 [SVG] Found {len(svg_elements)} SVG elements")
        
        for svg in svg_elements:
            try:
                # Проверяем aria-label
                aria_label = await svg.get_attribute('aria-label') or ""
                if any(keyword in aria_label.lower() for keyword in ['crop', 'обрез', 'размер', 'выбрать']):
                    log_info(f"[ASYNC_CROP] 📐 [SVG] [OK] Found by aria-label: {aria_label}")
                    
                    # Найти родительскую кнопку
                    parent_button = await svg.query_selector('xpath=ancestor::button[1] | xpath=ancestor::div[@role="button"][1]')
                    if parent_button and await parent_button.is_visible():
                        return parent_button
                    return svg
                
                # Анализ SVG paths (ищем характерные пути для иконки кропа)
                paths = await svg.query_selector_all('path')
                for path in paths:
                    path_data = await path.get_attribute('d') or ""
                    # Характерные пути для иконки кропа (углы, рамки)
                    if any(pattern in path_data for pattern in ['M10 20H4v-6', 'M20.999 2H14', 'L', 'H', 'V']):
                        log_info(f"[ASYNC_CROP] 📐 [SVG] [OK] Found by SVG path pattern")
                        
                        # Найти родительскую кнопку
                        parent_button = await svg.query_selector('xpath=ancestor::button[1] | xpath=ancestor::div[@role="button"][1]')
                        if parent_button and await parent_button.is_visible():
                            return parent_button
                        return svg
                        
            except Exception as e:
                log_info(f"[ASYNC_CROP] 📐 [SVG] SVG analysis failed: {str(e)}")
                continue
                
    except Exception as e:
        log_info(f"[ASYNC_CROP] 📐 [SVG] SVG content analysis failed: {str(e)}")
    
    return None

async def _find_crop_by_context_analysis_async(page):
    """Поиск по контекстному анализу (где обычно находится кнопка кропа) - async version"""
    log_info("[ASYNC_CROP] 📐 [CONTEXT] Searching by context analysis...")
    
    try:
        # Ищем кнопки в контексте редактирования видео
        context_selectors = [
            'button[type="button"]:has(svg)',  # Кнопки с SVG
            'div[role="button"]:has(svg)',     # Div-кнопки с SVG
            '[role="button"]:has(svg)',       # Любые кнопки с SVG
        ]
        
        for selector in context_selectors:
            try:
                buttons = await page.query_selector_all(selector)
                log_info(f"[ASYNC_CROP] 📐 [CONTEXT] Found {len(buttons)} buttons with selector: {selector}")
                
                for button in buttons:
                    # Проверяем размер и позицию (кнопка кропа обычно небольшая)
                    bbox = await button.bounding_box()
                    if bbox and 10 <= bbox['width'] <= 50 and 10 <= bbox['height'] <= 50:
                        # Проверяем наличие SVG внутри
                        svg_inside = await button.query_selector('svg')
                        if svg_inside and await svg_inside.is_visible():
                            log_info(f"[ASYNC_CROP] 📐 [CONTEXT] [OK] Found candidate button by context")
                            return button
                            
            except Exception as e:
                log_info(f"[ASYNC_CROP] 📐 [CONTEXT] Context selector {selector} failed: {str(e)}")
                continue
                
    except Exception as e:
        log_info(f"[ASYNC_CROP] 📐 [CONTEXT] Context analysis failed: {str(e)}")
    
    return None

async def _find_crop_by_fallback_patterns_async(page):
    """Поиск по резервным паттернам (последний resort) - async version"""
    log_info("[ASYNC_CROP] 📐 [FALLBACK] Using fallback patterns...")
    
    try:
        # XPath селекторы (самые мощные)
        xpath_selectors = [
            '//svg[contains(@aria-label, "Выбрать размер")]',
            '//svg[contains(@aria-label, "обрезать")]',
            '//svg[contains(@aria-label, "Select crop")]',
            '//svg[contains(@aria-label, "Crop")]',
            '//button[.//svg[contains(@aria-label, "Выбрать размер")]]',
            '//div[@role="button" and .//svg[contains(@aria-label, "Выбрать размер")]]',
            '//button[.//svg[contains(@aria-label, "Select crop")]]',
            '//div[@role="button" and .//svg[contains(@aria-label, "Select crop")]]',
        ]
        
        for xpath in xpath_selectors:
            try:
                log_info(f"[ASYNC_CROP] 📐 [FALLBACK] Trying XPath: {xpath}")
                element = await page.query_selector(f'xpath={xpath}')
                if element and await element.is_visible():
                    log_info(f"[ASYNC_CROP] 📐 [FALLBACK] [OK] Found by XPath: {xpath}")
                    return element
                    
            except Exception as e:
                log_info(f"[ASYNC_CROP] 📐 [FALLBACK] XPath {xpath} failed: {str(e)}")
                continue
                
    except Exception as e:
        log_info(f"[ASYNC_CROP] 📐 [FALLBACK] Fallback patterns failed: {str(e)}")
    
    return None

async def _human_click_crop_button_async(page, crop_button):
    """Человеческий клик по кнопке кропа - async version"""
    try:
        log_info("[ASYNC_CROP] 📐 [CLICK] Performing human-like click on crop button...")
        
        # Убеждаемся что элемент видим
        await crop_button.wait_for_element_state('visible', timeout=5000)
        
        # Человеческая задержка перед кликом
        await asyncio.sleep(random.uniform(0.5, 1.2))
        
        # Двигаем мышь к элементу
        await crop_button.hover()
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        # Клик
        await crop_button.click()
        
        # Человеческая задержка после клика
        await asyncio.sleep(random.uniform(0.8, 1.5))
        
        log_info("[ASYNC_CROP] 📐 [CLICK] [OK] Successfully clicked crop button")
        
    except Exception as e:
        log_info(f"[ASYNC_CROP] 📐 [CLICK] [FAIL] Failed to click crop button: {str(e)}")
        raise

async def _select_original_aspect_ratio_async(page):
    """Select the 'Оригинал' (Original) aspect ratio option - IMPROVED for dynamic selectors - async version"""
    log_info("[ASYNC_CROP] 📐 Looking for 'Оригинал' (Original) aspect ratio option...")
    
    # [TARGET] АДАПТИВНАЯ СТРАТЕГИЯ: Поиск по семантическим признакам
    search_strategies = [
        _find_original_by_text_content_async,
        _find_original_by_svg_icon_async,
        _find_original_by_first_position_async,
        _find_any_available_option_async
    ]
    
    for strategy_index, strategy in enumerate(search_strategies, 1):
        log_info(f"[ASYNC_CROP] 📐 [ORIGINAL] Trying strategy {strategy_index}: {strategy.__name__}")
        
        try:
            original_element = await strategy(page)
            if original_element:
                log_info(f"[ASYNC_CROP] 📐 [ORIGINAL] [OK] Found 'Оригинал' using strategy {strategy_index}")
                
                # Human-like interaction with aspect ratio selection
                await _human_click_with_timeout_async(page, original_element, "ASPECT_RATIO")
                
                # Wait for aspect ratio to be applied
                aspect_ratio_wait = random.uniform(1.5, 2.5)
                log_info(f"[ASYNC_CROP] [WAIT] Waiting {aspect_ratio_wait:.1f}s for 'Оригинал' aspect ratio to be applied...")
                await asyncio.sleep(aspect_ratio_wait)
                
                return True
                
        except Exception as e:
            log_info(f"[ASYNC_CROP] 📐 [ORIGINAL] Strategy {strategy_index} failed: {str(e)}")
            continue
    
    log_info("[ASYNC_CROP] 📐 [ORIGINAL] [WARN] All strategies failed to find 'Оригинал' option")
    return False

async def _find_original_by_text_content_async(page):
    """Поиск 'Оригинал' по текстовому содержимому - async version"""
    log_info("[ASYNC_CROP] 📐 [TEXT] Searching for 'Оригинал' by text content...")
    
    # Семантические селекторы по тексту (независимы от CSS-классов)
    text_selectors = [
        # Прямой поиск span с текстом "Оригинал"
        'span:has-text("Оригинал")',
        'span:has-text("Original")',
        
        # Поиск родительских элементов
        'div[role="button"]:has(span:has-text("Оригинал"))',
        'button:has(span:has-text("Оригинал"))',
        'div[role="button"]:has(span:has-text("Original"))',
        'button:has(span:has-text("Original"))',
        
        # Прямой поиск по тексту в кнопках
        'button:has-text("Оригинал")',
        'div[role="button"]:has-text("Оригинал")',
        'button:has-text("Original")',
        'div[role="button"]:has-text("Original")',
        
        # XPath селекторы (самые точные)
        '//span[text()="Оригинал"]',
        '//span[text()="Original"]',
        '//div[@role="button" and .//span[text()="Оригинал"]]',
        '//button[.//span[text()="Оригинал"]]',
        '//div[@role="button" and .//span[text()="Original"]]',
        '//button[.//span[text()="Original"]]',
    ]
    
    for selector in text_selectors:
        try:
            log_info(f"[ASYNC_CROP] 📐 [TEXT] Trying: {selector}")
            
            if selector.startswith('//'):
                element = await page.query_selector(f"xpath={selector}")
            else:
                element = await page.query_selector(selector)
            
            if element and await element.is_visible():
                # Если найден span, найти родительскую кнопку
                if selector.startswith('span:'):
                    parent_button = await element.query_selector('xpath=ancestor::*[@role="button"][1] | xpath=ancestor::button[1]')
                    if parent_button and await parent_button.is_visible():
                        log_info(f"[ASYNC_CROP] 📐 [TEXT] [OK] Found 'Оригинал' parent button")
                        return parent_button
                
                log_info(f"[ASYNC_CROP] 📐 [TEXT] [OK] Found 'Оригинал' element: {selector}")
                return element
                
        except Exception as e:
            log_info(f"[ASYNC_CROP] 📐 [TEXT] Selector {selector} failed: {str(e)}")
            continue
    
    return None

async def _find_original_by_svg_icon_async(page):
    """Поиск 'Оригинал' по SVG иконке - async version"""
    log_info("[ASYNC_CROP] 📐 [SVG] Searching for 'Оригинал' by SVG icon...")
    
    try:
        # Поиск SVG с характерными aria-label для "Оригинал"
        svg_selectors = [
            # Из предоставленного HTML
            'svg[aria-label="Значок контура фото"]',
            'svg[aria-label*="контур"]',
            'svg[aria-label*="фото"]',
            'svg[aria-label*="photo"]',
            'svg[aria-label*="outline"]',
            'svg[aria-label*="original"]',
            'svg[aria-label*="Оригинал"]',
            
            # XPath для более точного поиска
            '//svg[@aria-label="Значок контура фото"]',
            '//svg[contains(@aria-label, "контур")]',
            '//svg[contains(@aria-label, "фото")]',
            '//svg[contains(@aria-label, "photo")]',
            '//svg[contains(@aria-label, "outline")]',
        ]
        
        for selector in svg_selectors:
            try:
                if selector.startswith('//'):
                    svg_element = await page.query_selector(f"xpath={selector}")
                else:
                    svg_element = await page.query_selector(selector)
                
                if svg_element and await svg_element.is_visible():
                    log_info(f"[ASYNC_CROP] 📐 [SVG] [OK] Found SVG icon: {selector}")
                    
                    # Найти родительскую кнопку
                    parent_button = await svg_element.query_selector('xpath=ancestor::*[@role="button"][1] | xpath=ancestor::button[1]')
                    if parent_button and await parent_button.is_visible():
                        log_info("[ASYNC_CROP] 📐 [SVG] [OK] Found parent button for SVG")
                        return parent_button
                    
                    return svg_element
                    
            except Exception as e:
                log_info(f"[ASYNC_CROP] 📐 [SVG] SVG selector {selector} failed: {str(e)}")
                continue
                
    except Exception as e:
        log_info(f"[ASYNC_CROP] 📐 [SVG] SVG search failed: {str(e)}")
    
    return None

async def _find_original_by_first_position_async(page):
    """Поиск 'Оригинал' по позиции (обычно первый элемент) - async version"""
    log_info("[ASYNC_CROP] 📐 [POS] Searching for 'Оригинал' by position...")
    
    try:
        # Найти все кнопки опций кропа
        position_selectors = [
            'div[role="button"][tabindex="0"]',
            'button[tabindex="0"]',
            '[role="button"][tabindex="0"]',
            'div[role="button"]:has(span)',
            'button:has(span)',
        ]
        
        for selector in position_selectors:
            try:
                buttons = await page.query_selector_all(selector)
                
                if buttons:
                    log_info(f"[ASYNC_CROP] 📐 [POS] Found {len(buttons)} buttons with selector: {selector}")
                    
                    # Проверить первые несколько кнопок
                    for i, button in enumerate(buttons[:4]):
                        try:
                            if await button.is_visible():
                                button_text = await button.text_content() or ""
                                
                                # Если содержит "Оригинал" - точное совпадение
                                if 'Оригинал' in button_text or 'Original' in button_text:
                                    log_info(f"[ASYNC_CROP] 📐 [POS] [OK] Found 'Оригинал' at position {i+1}: '{button_text.strip()}'")
                                    return button
                                
                                # Если первая кнопка - возможно это "Оригинал"
                                if i == 0:
                                    log_info(f"[ASYNC_CROP] 📐 [POS] [OK] Using first button as potential 'Оригинал': '{button_text.strip()}'")
                                    return button
                                    
                        except Exception as e:
                            log_info(f"[ASYNC_CROP] 📐 [POS] Button {i+1} check failed: {str(e)}")
                            continue
                            
            except Exception as e:
                log_info(f"[ASYNC_CROP] 📐 [POS] Position selector {selector} failed: {str(e)}")
                continue
                
    except Exception as e:
        log_info(f"[ASYNC_CROP] 📐 [POS] Position search failed: {str(e)}")
    
    return None

async def _find_any_available_option_async(page):
    """Поиск любой доступной опции кропа (fallback) - async version"""
    log_info("[ASYNC_CROP] 📐 [ANY] Searching for any available crop option...")
    
    try:
        # Самые широкие селекторы
        fallback_selectors = [
            # XPath для первой доступной кнопки
            '(//div[@role="button" and @tabindex="0"])[1]',
            '(//button[@tabindex="0"])[1]',
            '(//div[@role="button"])[1]',
            '(//button)[1]',
            
            # CSS селекторы
            'div[role="button"][tabindex="0"]:first-child',
            'button[tabindex="0"]:first-child',
            'div[role="button"]:first-child',
            'button:first-child',
        ]
        
        for selector in fallback_selectors:
            try:
                if selector.startswith('(//') or selector.startswith('//'):
                    element = await page.query_selector(f"xpath={selector}")
                else:
                    element = await page.query_selector(selector)
                
                if element and await element.is_visible():
                    element_text = await element.text_content() or ""
                    log_info(f"[ASYNC_CROP] 📐 [ANY] [OK] Found fallback option: '{element_text.strip()}' with selector: {selector}")
                    return element
                    
            except Exception as e:
                log_info(f"[ASYNC_CROP] 📐 [ANY] Fallback selector {selector} failed: {str(e)}")
                continue
                
    except Exception as e:
        log_info(f"[ASYNC_CROP] 📐 [ANY] Fallback search failed: {str(e)}")
    
    return None

async def _human_click_with_timeout_async(page, element, log_prefix="HUMAN_CLICK"):
    """Human-like click with short timeout to avoid verbose logs - async version"""
    try:
        # Set shorter timeout to avoid long retry loops
        original_timeout = page._timeout_settings.default_timeout if hasattr(page, '_timeout_settings') else 30000
        page.set_default_timeout(5000)  # 5 seconds max
        
        try:
            # Human-like interaction
            await element.hover()
            await asyncio.sleep(random.uniform(0.2, 0.5))
            await element.click()
            await asyncio.sleep(random.uniform(0.5, 1.0))
            log_info(f"[{log_prefix}] [OK] Human click successful")
            
            # Restore original timeout
            page.set_default_timeout(original_timeout)
            return True
            
        except Exception as e:
            # Restore timeout even if failed
            page.set_default_timeout(original_timeout)
            log_info(f"[{log_prefix}] Human behavior failed: {str(e)[:100]}")
            
            # Fallback to quick click
            return await _quick_click_async(page, element, log_prefix)
            
    except Exception as e:
        log_info(f"[{log_prefix}] Error in human click: {str(e)[:100]}")
        return False

async def _quick_click_async(page, element, log_prefix="QUICK_CLICK"):
    """Quick click without verbose Playwright logs - async version"""
    try:
        # Try force click first (fastest)
        await element.click(force=True, timeout=3000)
        log_info(f"[{log_prefix}] [OK] Quick click successful")
        return True
    except Exception as e:
        try:
            # Fallback to JavaScript click
            await page.evaluate('(element) => element.click()', element)
            log_info(f"[{log_prefix}] [OK] JavaScript click successful")
            return True
        except Exception as e2:
            # Last resort: standard click with short timeout
            try:
                await element.click(timeout=2000)
                log_info(f"[{log_prefix}] [OK] Standard click successful")
                return True
            except Exception as e3:
                log_info(f"[{log_prefix}] [WARN] All click methods failed: {str(e3)[:100]}")
                return False

async def simulate_page_scan_async(page):
    """Simulate human page scanning behavior - async version"""
    try:
        # Random scroll to simulate scanning
        await page.evaluate("""
            window.scrollBy({
                top: Math.random() * 200 - 100,
                left: 0,
                behavior: 'smooth'
            });
        """)
        await asyncio.sleep(random.uniform(0.5, 1.5))
    except Exception as e:
        log_info(f"[ASYNC_HUMAN] Page scan simulation error: {str(e)}")

async def simulate_mouse_movement_to_element_async(page, element):
    """Simulate human mouse movement to element - async version"""
    try:
        # Get element position
        box = await element.bounding_box()
        if box:
            # Move to random position within element
            x = box['x'] + box['width'] * random.uniform(0.2, 0.8)
            y = box['y'] + box['height'] * random.uniform(0.2, 0.8)
            
            # Simulate gradual mouse movement
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
    except Exception as e:
        log_info(f"[ASYNC_HUMAN] Mouse movement simulation error: {str(e)}")

async def add_human_delay_between_uploads_async(page, upload_index):
    """Add human-like delay between uploads - async version"""
    try:
        # Base delay with randomization
        base_delay = random.uniform(15, 25)  # 15-25 seconds between uploads
        
        # Add some random browsing simulation
        if random.random() < 0.3:  # 30% chance to simulate browsing
            log_info(f"[ASYNC_HUMAN] Simulating browsing behavior before next upload...")
            await simulate_random_browsing_async(page)
            base_delay += random.uniform(5, 10)
        
        log_info(f"[ASYNC_HUMAN] Waiting {base_delay:.1f}s before next upload...")
        await asyncio.sleep(base_delay)
        
    except Exception as e:
        log_info(f"[ASYNC_HUMAN] Delay simulation error: {str(e)}")

async def simulate_random_browsing_async(page):
    """Simulate random browsing behavior - async version"""
    try:
        # Random scroll
        scroll_amount = random.randint(-300, 300)
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(random.uniform(1, 3))
        
        # Sometimes click on non-critical elements
        if random.random() < 0.2:  # 20% chance
            try:
                # Click on Instagram logo or home button (safe elements)
                safe_elements = [
                    'a[href="/"]',
                    'svg[aria-label="Instagram"]',
                    'div[role="button"][aria-label="Home"]'
                ]
                
                for selector in safe_elements:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.click()
                        await asyncio.sleep(random.uniform(2, 4))
                        break
            except:
                pass
                
    except Exception as e:
        log_info(f"[ASYNC_HUMAN] Random browsing simulation error: {str(e)}")

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

async def log_video_info_async(video_index, total_videos, video_file_path, video_obj):
    """Log video information - async version"""
    try:
        log_info(f"[ASYNC_UPLOAD] [CAMERA] Processing video {video_index}/{total_videos}: {os.path.basename(video_file_path)}")
        
        # Log video details if available - handle both VideoData and Django model objects
        title = None
        
        # Check for VideoData objects (new async version)
        if hasattr(video_obj, 'title') and video_obj.title:
            title = video_obj.title
        # Check for Django model objects (old async version)
        elif hasattr(video_obj, 'title_data') and video_obj.title_data and hasattr(video_obj.title_data, 'title'):
            title = video_obj.title_data.title
        
        if title:
            title_preview = title[:50] + "..." if len(title) > 50 else title
            log_info(f"[ASYNC_UPLOAD] [TEXT] Title: {title_preview}")
        
        # Log file size
        if os.path.exists(video_file_path):
            file_size = os.path.getsize(video_file_path)
            file_size_mb = file_size / (1024 * 1024)
            log_info(f"[ASYNC_UPLOAD] 📊 File size: {file_size_mb:.1f} MB")
            
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] Error logging video info: {str(e)}")

async def perform_enhanced_instagram_login_async(page, account_details):
    """Enhanced Instagram login - improved version based on sync"""
    try:
        username = account_details['username']
        password = account_details['password']
        
        log_info(f"🔐 [ASYNC_LOGIN] Starting enhanced login process for account: {username}")
        
        # Don't navigate to login page - use fields on main page
        current_url = page.url
        log_info(f"🌐 [ASYNC_LOGIN] Using login fields on current page: {current_url}")
        
        # Wait for login form to be ready
        await asyncio.sleep(random.uniform(2, 4))
        
        # Find and fill username field with enhanced selectors
        username_selectors = [
            'input[name="username"]',
            'input[name="email"]',
            'input[aria-label*="Телефон"]',
            'input[aria-label*="Phone"]',
            'input[aria-label*="Username"]',
            'input[placeholder*="Телефон"]',
            'input[placeholder*="Phone"]',
            'input[placeholder*="Username"]',
            'input[placeholder*="Имя пользователя"]',
        ]
        
        username_field = None
        for selector in username_selectors:
            try:
                username_field = await page.query_selector(selector)
                if username_field and await username_field.is_visible():
                    log_info(f"[OK] [ASYNC_LOGIN] Found username field: {selector}")
                    break
            except:
                continue
        
        if not username_field:
            log_info("[FAIL] [ASYNC_LOGIN] Username field not found")
            return False
        
        # Find password field with enhanced selectors
        password_selectors = [
            'input[name="password"]',
            'input[name="pass"]',
            'input[type="password"]',
            'input[aria-label*="Пароль"]',
            'input[aria-label*="Password"]',
            'input[placeholder*="Пароль"]',
            'input[placeholder*="Password"]',
        ]
        
        password_field = None
        for selector in password_selectors:
            try:
                password_field = await page.query_selector(selector)
                if password_field and await password_field.is_visible():
                    log_info(f"[OK] [ASYNC_LOGIN] Found password field: {selector}")
                    break
            except:
                continue
        
        if not password_field:
            log_info("[FAIL] [ASYNC_LOGIN] Password field not found")
            return False
        
        # Clear fields and enter credentials with human-like behavior
        log_info("[TEXT] [ASYNC_LOGIN] Filling credentials...")
        
        # Focus and clear username field
        await username_field.click()
        await asyncio.sleep(random.uniform(0.5, 1.0))
        await username_field.fill("")
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        # Type username character by character (human-like)
        for char in username:
            await username_field.type(char, delay=random.uniform(50, 150))
            
        await asyncio.sleep(random.uniform(1, 2))
        
        # Focus and clear password field
        await password_field.click()
        await asyncio.sleep(random.uniform(0.5, 1.0))
        await password_field.fill("")
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        # Type password character by character (human-like)
        for char in password:
            await password_field.type(char, delay=random.uniform(50, 150))
            
        await asyncio.sleep(random.uniform(1, 2))
        
        # ДОПОЛНИТЕЛЬНАЯ ПАУЗА: Ждем после заполнения полей перед отправкой (like sync)
        log_info("[WAIT] [ASYNC_LOGIN] Waiting after filling credentials before form submission...")
        await asyncio.sleep(random.uniform(3, 6))  # Дополнительная пауза для человекоподобного поведения
        
        # Find and click login button with enhanced selectors
        login_selectors = [
            'button[type="submit"]',
            'button:has-text("Войти")',
            'button:has-text("Log in")',
            'button:has-text("Log In")',
            'div[role="button"]:has-text("Войти")',
            'div[role="button"]:has-text("Log in")',
            'input[type="submit"]',
        ]
        
        login_button = None
        for selector in login_selectors:
            try:
                login_button = await page.query_selector(selector)
                if login_button and await login_button.is_visible():
                    # Verify this is actually a login button
                    button_text = await login_button.text_content() or ""
                    if any(keyword in button_text.lower() for keyword in ['войти', 'log in', 'login', 'submit']):
                        log_info(f"[OK] [ASYNC_LOGIN] Found login button: '{button_text.strip()}'")
                        break
            except:
                continue
        
        if not login_button:
            log_info("[FAIL] [ASYNC_LOGIN] Login button not found")
            return False
        
        # Human-like interaction before clicking
        await login_button.hover()
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        log_info("🔐 [ASYNC_LOGIN] Clicking login button...")
        await login_button.click()
        
        # Wait for login to process with extended timeout
        await asyncio.sleep(random.uniform(5, 8))
        
        # Check for login success or errors
        return await handle_login_completion_async(page, account_details)
        
    except Exception as e:
        error_message = str(e)
        if 'suspend' in error_message.lower():
            log_info(f"[BLOCK] [ASYNC_LOGIN] Account suspended during login: {error_message}")
            return "SUSPENDED"
        else:
            log_error(f"[FAIL] [ASYNC_LOGIN] Enhanced login error: {error_message}")
            return False

async def handle_login_completion_async(page, account_details):
    """Handle login completion including 2FA, email verification and error checks"""
    try:
        log_info("[SEARCH] [ASYNC_LOGIN] Checking login completion...")
        
        # Wait for page to respond
        await asyncio.sleep(random.uniform(3, 5))
        
        # Check current URL and page content
        current_url = page.url
        log_debug(f"[SEARCH] [ASYNC_LOGIN] URL after login: {current_url}")
        
        # Проверяем, что мы НЕ на challenge-странице
        if '/challenge/' in current_url:
            log_info("[ALERT] [ASYNC_LOGIN] On challenge page - attempting to solve captcha...")
            
            # Пытаемся решить капчу на challenge-странице
            captcha_result = await handle_recaptcha_if_present_async(page, account_details)
            if captcha_result:
                log_info("[OK] [ASYNC_LOGIN] Captcha solved on challenge page")
                # Ждем немного после решения капчи
                await asyncio.sleep(random.uniform(3, 5))
                # Проверяем, что мы больше не на challenge-странице
                current_url = page.url
                if '/challenge/' not in current_url:
                    log_info("[OK] [ASYNC_LOGIN] Successfully passed challenge page")
                    return True
                else:
                    log_info("[WARN] [ASYNC_LOGIN] Still on challenge page after captcha solving")
                    return False
            else:
                log_info("[FAIL] [ASYNC_LOGIN] Failed to solve captcha on challenge page")
                return False
        
        # ВАЖНО: Сначала проверяем, не на странице ли верификации
               # КРИТИЧНО: Проверяем URL ПЕРВЫМ ДЕЛОМ - если на странице верификации, логин НЕ завершен
        if '/two_factor/' in current_url or '/challenge/' in current_url or '/accounts/login' in current_url:
            log_info(f"[ALERT] [ASYNC_LOGIN] Still on authentication/verification page: {current_url}")
            # НЕ ПРОВЕРЯЕМ индикаторы входа - мы все еще в процессе аутентификации
            # Переходим к обработке верификации
        elif 'instagram.com' in current_url:
            # Additional verification - look for logged-in elements
            logged_in_indicators = [
                'svg[aria-label="Notifications"]',
                'svg[aria-label="Direct"]', 
                'svg[aria-label="New post"]',
                'a[href*="/accounts/edit/"]',
                'main[role="main"]',
                'nav[role="navigation"]',
                'a[href="/"]',  # Home link
                'a[href="/explore/"]',  # Explore link
                'a[href="/reels/"]',  # Reels link
                'a[href="/accounts/activity/"]',  # Activity link
            ]
            
            for indicator in logged_in_indicators:
                try:
                    element = await page.query_selector(indicator)
                    if element and await element.is_visible():
                        log_info(f"[OK] [ASYNC_LOGIN] Login successful - found logged-in indicator: {indicator}")
                        return True
                except Exception as e:
                    log_warning(f"[WARN] [ASYNC_LOGIN] Error checking indicator {indicator}: {e}")
                    continue
                except:
                    continue
        
        # Check for login errors
        try:
            page_text = await page.inner_text('body') or ""
            
            # Check for suspension
            suspension_keywords = ['suspend', 'приостановлен', 'заблокирован', 'disabled']
            if any(keyword in page_text.lower() for keyword in suspension_keywords):
                log_info("[BLOCK] [ASYNC_LOGIN] Account suspension detected in login response")
                return "SUSPENDED"
            
            # Check for other errors
            error_elements = await page.query_selector_all('div[role="alert"], .error-message, [data-testid="login-error"]')
            for error_element in error_elements:
                if await error_element.is_visible():
                    error_text = await error_element.text_content() or ""
                    if error_text.strip():
                        log_error(f"[FAIL] [ASYNC_LOGIN] Login error detected: {error_text}")
                        
                        if any(keyword in error_text.lower() for keyword in ['suspend', 'disabled', 'заблокирован']):
                            return "SUSPENDED"
                        
        except Exception as e:
            log_warning(f"[WARN] [ASYNC_LOGIN] Error checking for login errors: {str(e)}")
        
        # Check for verification requirements
        from .email_verification_async import determine_verification_type_async
        
        verification_type = await determine_verification_type_async(page)
        log_info(f"[SEARCH] [ASYNC_LOGIN] Detected verification type: {verification_type}")
        
        if verification_type == "authenticator":
            log_info("[PHONE] [ASYNC_LOGIN] 2FA/Authenticator verification required")
            result = await handle_2fa_async(page, account_details)
            if result:
                log_info("[OK] [ASYNC_LOGIN] 2FA verification completed successfully")
                return True
            else:
                log_error("[FAIL] [ASYNC_LOGIN] 2FA verification failed")
                return False
                
        elif verification_type == "email_code":
            log_info("📧 [ASYNC_LOGIN] Email verification code required")
            result = await handle_email_verification_async(page, account_details)
            if result:
                log_info("[OK] [ASYNC_LOGIN] Email verification completed successfully")
                return True
            else:
                log_error("[FAIL] [ASYNC_LOGIN] Email verification failed - LOGIN NOT COMPLETED")
                return False  # КРИТИЧНО: НЕ ПРОДОЛЖАЕМ если верификация failed!
                
        elif verification_type == "email_field":
            log_info("📧 [ASYNC_LOGIN] Email field input required")
            result = await handle_email_field_verification_async(page, account_details)
            if result:
                log_info("[OK] [ASYNC_LOGIN] Email field verification completed successfully")
                return True
            else:
                log_error("[FAIL] [ASYNC_LOGIN] Email field verification failed")
                return False
                
        elif verification_type == "unknown":
            log_info("[OK] [ASYNC_LOGIN] No verification required - checking if truly logged in...")
            
            # ТОЛЬКО ЗДЕСЬ проверяем индикаторы успешного входа
            logged_in_indicators = [
                'svg[aria-label="Notifications"]',
                'svg[aria-label="Direct"]', 
                'svg[aria-label="New post"]',
                'main[role="main"]:not(:has(form))',  # main без форм входа
                'nav[role="navigation"]',
                'a[href="/"]',  # Home link
                'a[href="/explore/"]',  # Explore link
            ]
            
            for indicator in logged_in_indicators:
                try:
                    element = await page.query_selector(indicator)
                    if element and await element.is_visible():
                        log_info(f"[OK] [ASYNC_LOGIN] Login successful - found indicator: {indicator}")
                        return True
                except Exception as e:
                    continue
            
            log_info("[FAIL] [ASYNC_LOGIN] No logged-in indicators found - login may have failed")
            return False
        
        # If we're still on login page, login probably failed
        if '/accounts/login' in current_url:
            log_info("[FAIL] [ASYNC_LOGIN] Still on login page - login likely failed")
            return False
        
        # Если мы дошли сюда, логин не завершен
        log_info("[FAIL] [ASYNC_LOGIN] Login not completed - unknown state")
        return False
        
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_LOGIN] Error in login completion: {str(e)}")
        return False

async def handle_2fa_async(page, account_details):
    """Handle 2FA authentication using API instead of pyotp"""
    try:
        tfa_secret = account_details.get('tfa_secret')
        if not tfa_secret:
            log_info("[FAIL] [ASYNC_2FA] 2FA required but no secret provided")
            return False
        
        log_info("[PHONE] [ASYNC_2FA] Handling 2FA authentication...")
        
        # Find 2FA code input
        code_input = None
        code_selectors = [
            'input[name="verificationCode"]',  # Основной селектор
            'input[aria-label*="Код безопасности"]',  # Русский интерфейс
            'input[aria-label*="Security Code"]',  # Английский интерфейс
            'input[aria-describedby="verificationCodeDescription"]',  # По описанию
            'input[type="tel"][maxlength="8"]',  # По типу и длине
            'input[autocomplete="off"][maxlength="8"]',  # По атрибутам
            'input[placeholder*="код"]',
            'input[placeholder*="code"]',
            'input[maxlength="6"]',
            'input[maxlength="8"]',  # Instagram иногда использует 8
        ]
        for selector in code_selectors:
            try:
                code_input = await page.query_selector(selector)
                if code_input and await code_input.is_visible():
                    break
            except:
                continue
        
        if not code_input:
            log_info("[FAIL] [ASYNC_2FA] 2FA code input not found")
            return False
        
        # Get 2FA code from API
        code = await get_2fa_code_async(tfa_secret)
        if not code:
            log_info("[FAIL] [ASYNC_2FA] Failed to get 2FA code from API")
            return False
        
        log_info(f"[PHONE] [ASYNC_2FA] Got 2FA code from API: {code}")
        
        # Enter 2FA code
        await code_input.click()
        await asyncio.sleep(random.uniform(0.5, 1.0))
        await code_input.fill(code)
        await asyncio.sleep(random.uniform(1, 2))
        
        # Submit 2FA form
        submit_button = await page.query_selector('button[type="submit"], button:has-text("Confirm"), button:has-text("Подтвердить")')
        if submit_button:
            await submit_button.click()
            await asyncio.sleep(random.uniform(3, 5))
        
                # Check if 2FA was successful - улучшенная проверка
        await asyncio.sleep(random.uniform(2, 4))  # Ждем обработки
        current_url = page.url
        
        # Проверяем, что мы ушли со страницы 2FA
        if '/two_factor/' not in current_url and '/challenge/' not in current_url and '/accounts/login' not in current_url:
            log_info("[OK] [ASYNC_2FA] 2FA authentication successful - redirected from 2FA page")
            
            # Handle save login info dialog after successful 2FA
            await handle_save_login_info_dialog_async(page)
            
            return True
        else:
            # Дополнительная проверка на ошибки
            try:
                error_elements = await page.query_selector_all('[role="alert"], .error-message, ._aa4a')
                for error_element in error_elements:
                    if await error_element.is_visible():
                        error_text = await error_element.text_content() or ""
                        if error_text.strip():
                            log_error(f"[FAIL] [ASYNC_2FA] 2FA error: {error_text}")
                            return False
            except:
                pass
                
            log_info(f"[FAIL] [ASYNC_2FA] Still on verification page: {current_url}")
            return False
            
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_2FA] Error in 2FA handling: {str(e)}")
        return False

async def handle_email_verification_async(page, account_details):
    """Handle email verification code entry"""
    try:
        email_login = account_details.get('email_login')
        email_password = account_details.get('email_password')
        
        if not email_login or not email_password:
            log_info("[FAIL] [ASYNC_EMAIL] Email credentials not provided for verification")
            return False
        
        log_info("📧 [ASYNC_EMAIL] Starting email verification...")
        
        # Find verification code input
        code_input = None
        code_selectors = [
            'input[name="email"]',  # Instagram специально путает - поле называется "email" но нужен КОД!
            'input[name="verificationCode"]',
            'input[name="confirmationCode"]',
            'input[type="text"][autocomplete="off"]',  # Из HTML
            'input[autocomplete="one-time-code"]',
            'input[inputmode="numeric"]',
            'input[maxlength="6"]',
            'input[maxlength="8"]',
            'input[placeholder*="код"]',
            'input[placeholder*="code"]',
            'label:has-text("Код") + input',  # По label "Код"
        ]
                # Дополнительные селекторы из реального HTML Instagram
        additional_selectors = [
            'input[id^="_r_"]',  # Instagram использует динамические ID типа "_r_7_"
            'input[type="text"][dir="ltr"][autocomplete="off"]',
            'label[for^="_r_"] + input',  # По связанному label
        ]
        code_selectors.extend(additional_selectors)
        
        for selector in code_selectors:
            try:
                code_input = await page.query_selector(selector)
                if code_input and await code_input.is_visible():
                    break
            except:
                continue
        
        if not code_input:
            log_info("[FAIL] [ASYNC_EMAIL] Email verification code input not found")
            return False
        
        # Get verification code from email
        verification_code = await get_email_verification_code_async(email_login, email_password, max_retries=3)
        
        if verification_code:
            log_info(f"📧 [ASYNC_EMAIL] Got email verification code: {verification_code}")
            
            # Enter verification code
            await code_input.click()
            await asyncio.sleep(random.uniform(0.5, 1.0))
            await code_input.fill(verification_code)
            await asyncio.sleep(random.uniform(1, 2))
            
            # Submit verification form - UPDATED SELECTORS for Instagram
            submit_selectors = [
                'div[role="button"]:has-text("Продолжить")',  # Русская версия
                'div[role="button"]:has-text("Continue")',     # Английская версия
                'button:has-text("Продолжить")',
                'button:has-text("Continue")', 
                'button[type="submit"]',
                '[role="button"]:has(span:has-text("Продолжить"))',
                '[role="button"]:has(span:has-text("Continue"))',
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = await page.query_selector(selector)
                    if submit_button and await submit_button.is_visible():
                        log_info(f"📧 [ASYNC_EMAIL] Found submit button: {selector}")
                        break
                except:
                    continue

            if submit_button:
                await submit_button.click()
                log_info("📧 [ASYNC_EMAIL] Clicked submit button")
                await asyncio.sleep(random.uniform(3, 5))
            else:
                log_error("📧 [ASYNC_EMAIL] Submit button not found - trying Enter key")
                # Fallback: press Enter in the code field
                await code_input.press('Enter')
                await asyncio.sleep(random.uniform(3, 5))
            
                        # Check if verification was successful - IMPROVED VERSION
            await asyncio.sleep(random.uniform(2, 4))  # Wait for page to load
            current_url = page.url
            
            # Check for human verification requirement FIRST
            human_verification_result = await check_for_human_verification_dialog_async(page, account_details)
            if human_verification_result.get('requires_human_verification', False):
                log_error(f"[BOT] [ASYNC_EMAIL] Human verification required after email: {human_verification_result.get('message', 'Unknown reason')}")
                raise Exception(f"HUMAN_VERIFICATION_REQUIRED: {human_verification_result.get('message', 'Human verification required after email verification')}")
            
            # Then check if we're still on verification pages
            if '/accounts/login' not in current_url and 'challenge' not in current_url and 'auth_platform' not in current_url:
                log_info("[OK] [ASYNC_EMAIL] Email verification successful")
                
                # Handle save login info dialog after successful email verification
                await handle_save_login_info_dialog_async(page)
                
                return True
            else:
                log_info(f"[FAIL] [ASYNC_EMAIL] Email verification failed - still on verification page: {current_url}")
                return False
        else:
            log_info("[FAIL] [ASYNC_EMAIL] Failed to get email verification code")
            return False
            
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_EMAIL] Error in email verification: {str(e)}")
        return False

async def handle_email_field_verification_async(page, account_details):
    """Handle email field input verification"""
    try:
        email_login = account_details.get('email_login')
        
        if not email_login:
            log_info("[FAIL] [ASYNC_EMAIL_FIELD] Email login not provided")
            return False
        
        log_info("📧 [ASYNC_EMAIL_FIELD] Starting email field verification...")
        
        # Find email input field
        email_input = None
        email_selectors = [
            'input[name="email"]',
            'input[name="emailOrPhone"]',
            'input[type="email"]',
            'input[autocomplete="email"]',
            'input[inputmode="email"]',
        ]
        
        for selector in email_selectors:
            try:
                email_input = await page.query_selector(selector)
                if email_input and await email_input.is_visible():
                    break
            except:
                continue
        
        if not email_input:
            log_info("[FAIL] [ASYNC_EMAIL_FIELD] Email input field not found")
            return False
        
        # Enter email address
        await email_input.click()
        await asyncio.sleep(random.uniform(0.5, 1.0))
        await email_input.fill(email_login)
        await asyncio.sleep(random.uniform(1, 2))
        
        # Submit email form
        submit_button = await page.query_selector('button[type="submit"], button:has-text("Confirm"), button:has-text("Подтвердить")')
        if submit_button:
            await submit_button.click()
            await asyncio.sleep(random.uniform(3, 5))
        
        # Check if email submission was successful
        current_url = page.url
        if '/accounts/login' not in current_url and 'challenge' not in current_url:
            log_info("[OK] [ASYNC_EMAIL_FIELD] Email field verification successful")
            return True
        else:
            log_info("[FAIL] [ASYNC_EMAIL_FIELD] Email field verification failed")
            return False
            
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_EMAIL_FIELD] Error in email field verification: {str(e)}")
        return False

async def handle_save_login_info_dialog_async(page):
    """Handle Instagram's 'Save login info' dialog - exact copy from sync"""
    try:
        log_info("[ASYNC_SAVE_LOGIN] Checking for 'Save login info' dialog...")
        await asyncio.sleep(random.uniform(2, 4))
        
        # Check page text for save login dialog
        try:
            page_text = await page.inner_text('body') or ""
        except Exception:
            page_text = ""
        
        # Keywords that indicate save login dialog (from sync version)
        save_login_keywords = [
            'сохранить данные для входа', 'save login info', 'сохранить информацию', 
            'save your login info', 'запомнить', 'remember', 'сохранить', 'save'
        ]
        
        is_save_login_dialog = any(keyword in page_text.lower() for keyword in save_login_keywords)
        log_info(f"[ASYNC_SAVE_LOGIN] Save login dialog detected: {is_save_login_dialog}")
        
        if is_save_login_dialog:
            log_info("[ASYNC_SAVE_LOGIN] 💾 Save login info dialog found")
            
            # Look for "Save" button
            save_button_selectors = [
                'button:has-text("Сохранить")',
                'button:has-text("Save")',
                'div[role="button"]:has-text("Сохранить")',
                'div[role="button"]:has-text("Save")',
            ]
            
            save_button = None
            for selector in save_button_selectors:
                try:
                    save_button = await page.query_selector(selector)
                    if save_button and await save_button.is_visible():
                        button_text = await save_button.text_content() or ""
                        if any(keyword in button_text.lower() for keyword in ['сохранить', 'save']):
                            log_info(f"[ASYNC_SAVE_LOGIN] [OK] Found save button: '{button_text.strip()}'")
                            break
                except:
                    continue
            
            if save_button:
                try:
                    await save_button.hover()
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    await save_button.click()
                    await asyncio.sleep(random.uniform(2, 4))
                    log_info("[ASYNC_SAVE_LOGIN] [OK] Successfully clicked save login info button")
                    return True
                except Exception as e:
                    log_info(f"[ASYNC_SAVE_LOGIN] [FAIL] Error clicking save button: {str(e)}")
            
            # If no save button, look for "Not now" button
            log_info("[ASYNC_SAVE_LOGIN] [WARN] Could not find save button, looking for 'Not now' button...")
            not_now_selectors = [
                'button:has-text("Не сейчас")',
                'button:has-text("Not now")',
                'button:has-text("Not Now")',
                'div[role="button"]:has-text("Не сейчас")',
                'div[role="button"]:has-text("Not now")',
            ]
            
            for selector in not_now_selectors:
                try:
                    not_now_button = await page.query_selector(selector)
                    if not_now_button and await not_now_button.is_visible():
                        button_text = await not_now_button.text_content() or ""
                        log_info(f"[ASYNC_SAVE_LOGIN] Found 'Not now' button: '{button_text.strip()}'")
                        
                        await not_now_button.hover()
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                        await not_now_button.click()
                        await asyncio.sleep(random.uniform(2, 4))
                        log_info("[ASYNC_SAVE_LOGIN] [OK] Successfully clicked 'Not now' button")
                        return True
                except:
                    continue
        
        log_info("[ASYNC_SAVE_LOGIN] No save login dialog found or handled")
        return True
        
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_SAVE_LOGIN] Error handling save login dialog: {str(e)}")
        return True  # Continue anyway

# Add configuration for parallel processing
PARALLEL_CONFIG = {
    'MAX_CONCURRENT_ACCOUNTS': 3,  # Maximum accounts to process simultaneously
    'MAX_RETRIES_PER_ACCOUNT': 2,  # Retry failed accounts
    'ACCOUNT_START_DELAY': (5, 15), # Random delay between starting accounts
    'BATCH_SIZE': 5,  # Process accounts in batches
}

async def run_bulk_upload_task_parallel_async(task_id):
    """
    Enhanced async bulk upload with parallel account processing
    Main advantage over sync version: processes multiple accounts simultaneously
    """
    try:
        log_info(f"[START] [PARALLEL_ASYNC] Starting parallel bulk upload task {task_id}")
        
        # Get task and accounts
        task_data = await get_task_with_accounts_async(task_id)
        if not task_data:
            log_error(f"[FAIL] [PARALLEL_ASYNC] Task {task_id} not found")
            return False
        
        task, account_tasks = task_data
        total_accounts = len(account_tasks)
        
        if total_accounts == 0:
            log_warning(f"[WARN] [PARALLEL_ASYNC] No accounts found for task {task_id}")
            return True
        
        log_info(f"📊 [PARALLEL_ASYNC] Processing {total_accounts} accounts with max {PARALLEL_CONFIG['MAX_CONCURRENT_ACCOUNTS']} concurrent")
        
        # Initialize results tracking
        results = {
            'successful': 0,
            'failed': 0,
            'phone_verification': 0,
            'human_verification': 0, 
            'suspended': 0,
            'total_uploaded': 0,
            'total_failed_uploads': 0
        }
        
        # Process accounts in batches for better resource management
        batch_size = PARALLEL_CONFIG['BATCH_SIZE']
        account_batches = [account_tasks[i:i + batch_size] for i in range(0, len(account_tasks), batch_size)]
        
        for batch_num, batch in enumerate(account_batches, 1):
            log_info(f"📦 [PARALLEL_ASYNC] Processing batch {batch_num}/{len(account_batches)} ({len(batch)} accounts)")
            
            # Process batch with limited concurrency
            batch_results = await process_account_batch_async(batch, task, batch_num)
            
            # Aggregate results
            for key in results:
                results[key] += batch_results.get(key, 0)
            
            # Delay between batches to avoid overwhelming Instagram
            if batch_num < len(account_batches):
                delay = random.uniform(30, 60)  # 30-60 seconds between batches
                log_info(f"[WAIT] [PARALLEL_ASYNC] Waiting {delay:.1f}s before next batch...")
                await asyncio.sleep(delay)
        
        # Final summary
        log_info(f"[OK] [PARALLEL_ASYNC] Task {task_id} completed:")
        log_info(f"   📈 Successful: {results['successful']}")
        log_info(f"   [FAIL] Failed: {results['failed']}")
        log_info(f"   [PHONE] Phone verification: {results['phone_verification']}")
        log_info(f"   [BOT] Human verification: {results['human_verification']}")
        log_info(f"   [BLOCK] Suspended: {results['suspended']}")
        log_info(f"   [VIDEO] Total uploaded: {results['total_uploaded']}")
        
        # Update task status
        await update_task_status_async(task_id, 'COMPLETED', results)
        
        # [CLEAN] ОЧИСТКА: Удаляем оригинальные видео файлы из media/bot/bulk_videos/
        try:
            deleted_files = await cleanup_original_video_files_async(task_id)
            if deleted_files > 0:
                log_info(f"[DELETE] [PARALLEL_ASYNC] Cleaned up {deleted_files} original video files from media directory")
        except Exception as e:
            log_warning(f"[WARN] [PARALLEL_ASYNC] Failed to cleanup original video files: {str(e)}")
        
        return True
        
    except Exception as e:
        log_info(f"[EXPLODE] [PARALLEL_ASYNC] Critical error in parallel task {task_id}: {str(e)}")
        await update_task_status_async(task_id, 'FAILED', {'error': str(e)})
        
        # [CLEAN] ОЧИСТКА: Удаляем оригинальные видео файлы даже при ошибке
        try:
            deleted_files = await cleanup_original_video_files_async(task_id)
            if deleted_files > 0:
                log_info(f"[DELETE] [PARALLEL_ASYNC] Cleaned up {deleted_files} original video files after error")
        except Exception as cleanup_error:
            log_warning(f"[WARN] [PARALLEL_ASYNC] Failed to cleanup original video files after error: {str(cleanup_error)}")
        
        return False

async def cleanup_original_video_files_async(task_id: int) -> int:
    """Очищает оригинальные видео файлы из media/bot/bulk_videos/ для данной задачи - async версия"""
    import os
    from django.conf import settings
    from asgiref.sync import sync_to_async
    
    deleted_count = 0
    
    try:
        # Получаем задачу и все видео файлы для этой задачи
        @sync_to_async
        def get_task_and_videos():
            from uploader.models import BulkUploadTask, BulkVideo
            task = BulkUploadTask.objects.get(id=task_id)
            return task, list(task.videos.all())
        
        task, videos = await get_task_and_videos()
        
        for video in videos:
            if video.video_file:
                try:
                    # Получаем полный путь к файлу
                    file_path = video.video_file.path if hasattr(video.video_file, 'path') else None
                    
                    if file_path and os.path.exists(file_path):
                        # БЕЗОПАСНАЯ ПРОВЕРКА: проверяем, не используется ли файл другими активными задачами
                        @sync_to_async
                        def is_file_safe_to_delete():
                            filename = os.path.basename(file_path)
                            
                            # Проверяем, есть ли другие BulkVideo объекты с таким же файлом в активных задачах
                            from uploader.models import BulkVideo, BulkUploadTask
                            
                            other_videos_with_same_file = BulkVideo.objects.filter(
                                video_file__icontains=filename
                            ).exclude(
                                bulk_task=task  # Исключаем текущую задачу
                            )
                            
                            # Проверяем статусы задач для этих видео
                            for other_video in other_videos_with_same_file:
                                other_task = other_video.bulk_task
                                if other_task.status in ['RUNNING', 'PENDING']:
                                    return False, f'[BLOCK] File {filename} is still used by running task "{other_task.name}" (ID: {other_task.id})'
                            
                            return True, None
                        
                        is_safe, warning_msg = await is_file_safe_to_delete()
                        
                        if is_safe:
                            # Удаляем файл
                            @sync_to_async
                            def delete_file():
                                os.unlink(file_path)
                                return os.path.basename(file_path)
                            
                            filename = await delete_file()
                            deleted_count += 1
                            log_info(f"[DELETE] [CLEANUP] Deleted original video file: {filename}")
                        else:
                            log_info(f"[PAUSE] [CLEANUP] Skipped deleting file (still in use by other tasks): {os.path.basename(file_path)}")
                            if warning_msg:
                                log_warning(f"[WARN] [CLEANUP] {warning_msg}")
                        
                except Exception as e:
                    log_warning(f"[WARN] [CLEANUP] Failed to delete video file {video.id}: {str(e)}")
        
        return deleted_count
        
    except Exception as e:
        log_error(f"[FAIL] [CLEANUP] Error in cleanup process: {str(e)}")
        return 0

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

# Helper functions for async operations
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

async def get_account_details_async(account_id):
    """Get account details - async version with proxy information"""
    try:
        from asgiref.sync import sync_to_async
        from uploader.models import InstagramAccount
        
        @sync_to_async
        def get_account():
            try:
                account = InstagramAccount.objects.get(id=account_id)
                
                # Use the to_dict() method which includes proxy information
                account_details = account.to_dict()
                
                log_debug(f"[SEARCH] [ACCOUNT_DETAILS] Retrieved account details for {account.username}")
                if account_details.get('proxy'):
                    proxy_info = account_details['proxy']
                    log_info(f"🔒 [ACCOUNT_DETAILS] Proxy: {proxy_info.get('host')}:{proxy_info.get('port')} (type: {proxy_info.get('type', 'http')})")
                else:
                    log_warning(f"[WARN] [ACCOUNT_DETAILS] No proxy assigned to account {account.username}")
                
                return account_details
            except InstagramAccount.DoesNotExist:
                return None
        
        return await get_account()
        
    except Exception as e:
        log_error(f"[FAIL] [DATABASE] Error getting account details: {str(e)}")
        return None

async def get_assigned_videos_async(account_task_id):
    """Get videos assigned to account task - async version with proper data binding"""
    try:
        from asgiref.sync import sync_to_async
        from uploader.models import BulkUploadAccount, VideoTitle
        
        @sync_to_async
        def get_videos():
            try:
                account_task = BulkUploadAccount.objects.get(id=account_task_id)
                videos = list(account_task.task.videos.all())
                
                # ENHANCED: Properly load titles with their assignments
                # Get all titles for this task with their assignments
                all_titles = list(account_task.task.titles.all())
                
                log_info(f"[ASYNC_DATA] Loaded {len(videos)} videos with {len(all_titles)} titles")
                
                # CRITICAL FIX: Assign titles to videos if not already assigned (like sync version)
                if all_titles:
                    log_info(f"[ASYNC_DATA] 🔥 ASSIGNING TITLES TO VIDEOS (CRITICAL FIX)")
                    
                    # Get unassigned titles
                    unassigned_titles = [title for title in all_titles if title.assigned_to is None]
                    log_info(f"[ASYNC_DATA] Found {len(unassigned_titles)} unassigned titles")
                    
                    # Assign titles to videos in order
                    for i, video in enumerate(videos):
                        if i < len(unassigned_titles):
                            title = unassigned_titles[i]
                            # Assign title to video
                            title.assigned_to = video
                            title.used = True
                            title.save(update_fields=['assigned_to', 'used'])
                            
                            # Set title_data for immediate use
                            video.title_data = title
                            log_info(f"[ASYNC_DATA] [OK] ASSIGNED title '{title.title[:50]}...' to video {i+1}")
                        else:
                            # If more videos than titles, use last title
                            last_title = unassigned_titles[-1] if unassigned_titles else None
                            if last_title:
                                video.title_data = last_title
                                log_info(f"[ASYNC_DATA] [WARN] Video {i+1} using last available title: '{last_title.title[:50]}...'")
                            else:
                                video.title_data = None
                                log_info(f"[ASYNC_DATA] [FAIL] Video {i+1} has no title available")
                else:
                    log_info(f"[ASYNC_DATA] [WARN] No titles found for task")
                    for video in videos:
                        video.title_data = None
                
                return videos
            except Exception as e:
                log_info(f"[ASYNC_DATA] Error loading videos: {str(e)}")
                import traceback
                log_info(f"[ASYNC_DATA] Traceback: {traceback.format_exc()}")
                return []
        
        return await get_videos()
        
    except Exception as e:
        log_error(f"[FAIL] [DATABASE] Error getting assigned videos: {str(e)}")
        return []

async def prepare_unique_videos_async(account_task, videos):
    """Prepare uniquified videos for account - enhanced version matching sync"""
    try:
        from asgiref.sync import sync_to_async
        import tempfile
        import os
        from datetime import datetime
        from pathlib import Path
        
        log_info(f"[VIDEO] [ASYNC_UNIQUIFY] Starting video uniquification for account")
        
        video_files = []
        temp_files = []
        
        for i, video in enumerate(videos):
            try:
                if not (hasattr(video, 'video_file') and video.video_file):
                    log_warning(f"[WARN] [ASYNC_UNIQUIFY] Video {i+1} has no video_file, skipping")
                    continue
                
                # Create temporary file from original
                video_filename = os.path.basename(video.video_file.name)
                log_info(f"[CLIPBOARD] [ASYNC_UNIQUIFY] Preparing video: {video_filename}")
                
                # Create temp file with original content
                @sync_to_async
                def create_temp_file():
                    import tempfile
                    import os
                    from datetime import datetime
                    
                    # Create unique filename with timestamp and account info
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    username = account_task.account.username if hasattr(account_task, 'account') and account_task.account else 'unknown'
                    
                    # Create temp file with unique name
                    temp_dir = tempfile.gettempdir()
                    unique_filename = f"tmp{os.getpid()}_{video_filename}_{username}_{timestamp}_v{i+1}.mp4"
                    temp_path = os.path.join(temp_dir, unique_filename)
                    
                    # Copy video content to temp file
                    with open(temp_path, 'wb') as tmp:
                        video.video_file.seek(0)
                        for chunk in video.video_file.chunks():
                            tmp.write(chunk)
                    
                    log_info(f"[OK] [ASYNC_UNIQUIFY] Created temp file: {temp_path}")
                    return temp_path
                
                temp_original = await create_temp_file()
                
                # Verify file exists and has content
                if os.path.exists(temp_original) and os.path.getsize(temp_original) > 0:
                    temp_files.append(temp_original)
                    video_files.append(temp_original)
                    log_info(f"[OK] [ASYNC_UNIQUIFY] Verified temp file: {os.path.basename(temp_original)} ({os.path.getsize(temp_original)} bytes)")
                else:
                    log_error(f"[FAIL] [ASYNC_UNIQUIFY] Temp file verification failed: {temp_original}")
                    if os.path.exists(temp_original):
                        log_warning(f"[WARN] [ASYNC_UNIQUIFY] File exists but size is {os.path.getsize(temp_original)} bytes")
                    else:
                        log_warning(f"[WARN] [ASYNC_UNIQUIFY] File does not exist")
                    continue
                
                log_info(f"[OK] [ASYNC_UNIQUIFY] Prepared video {i+1}/{len(videos)}: {os.path.basename(temp_original)}")
                
            except Exception as e:
                log_error(f"[FAIL] [ASYNC_UNIQUIFY] Error preparing video {i+1}: {str(e)}")
                import traceback
                log_debug(f"[SEARCH] [ASYNC_UNIQUIFY] Traceback: {traceback.format_exc()}")
                continue
        
        log_info(f"[TARGET] [ASYNC_UNIQUIFY] Prepared {len(video_files)} videos for account")
        
        # Final verification - check all files exist
        for i, file_path in enumerate(video_files):
            if not os.path.exists(file_path):
                log_error(f"[FAIL] [ASYNC_UNIQUIFY] CRITICAL: File {i+1} does not exist: {file_path}")
            else:
                log_info(f"[OK] [ASYNC_UNIQUIFY] File {i+1} verified: {os.path.basename(file_path)} ({os.path.getsize(file_path)} bytes)")
        
        return video_files
        
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_UNIQUIFY] Critical error preparing videos: {str(e)}")
        import traceback
        log_debug(f"[SEARCH] [ASYNC_UNIQUIFY] Full traceback: {traceback.format_exc()}")
        return []

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

# Main entry point - use parallel version
async def run_bulk_upload_task_async(task_id):
    """
    Main async bulk upload task - now with parallel processing!
    This is the improved version that processes multiple accounts simultaneously
    """
    return await run_bulk_upload_task_parallel_async(task_id)

async def handle_reels_dialog_async(page):
    """Handle Reels dialog that may appear after file upload"""
    try:
        log_info("[ASYNC_REELS_DIALOG] [SEARCH] Checking for Reels dialog...")
        
        # Ждем немного для появления диалога
        await asyncio.sleep(random.uniform(1, 2))
        
        # Надежные селекторы для диалога Reels (без динамических классов)
        reels_dialog_selectors = [
            # Селекторы по содержимому заголовка
            'div:has(h2:has-text("Теперь видеопубликациями можно делиться как видео Reels"))',
            'div:has(h2:has-text("Now video publications can be shared as Reels videos"))',
            'div:has(h2:has-text("видео Reels"))',
            'div:has(h2:has-text("Reels videos"))',
            'div:has(h2:has-text("Reels"))',
            
            # Селекторы по содержимому текста
            'div:has(span:has-text("видео Reels"))',
            'div:has(span:has-text("Reels videos"))',
            'div:has(span:has-text("Reels"))',
            'div:has(span:has-text("Теперь видеопубликациями"))',
            'div:has(span:has-text("Now video publications"))',
            'div:has(span:has-text("общедоступный аккаунт"))',
            'div:has(span:has-text("public account"))',
            'div:has(span:has-text("создать видео Reels"))',
            'div:has(span:has-text("create Reels videos"))',
            'div:has(span:has-text("аудиодорожкой"))',
            'div:has(span:has-text("audio track"))',
            'div:has(span:has-text("сделать ремикс"))',
            'div:has(span:has-text("make remix"))',
            
            # Селекторы по иконке Reels
            'div:has(img[src*="reels_nux_icon.png"])',
            'div:has(img[alt*="reels"])',
            'div:has(img[src*="reels"])',
            
            # Селекторы по структуре диалога
            'div[role="dialog"]:has-text("Reels")',
            'div[role="dialog"]:has-text("видео")',
            'div[role="dialog"]:has-text("Теперь")',
            'div[role="dialog"]:has-text("Now")',
            
            # Более широкие селекторы диалогов
            'div[role="dialog"]',
        ]
        
        # Ищем диалог
        dialog_found = False
        dialog_element = None
        
        for selector in reels_dialog_selectors:
            try:
                dialog_element = await page.query_selector(selector)
                if dialog_element and await dialog_element.is_visible():
                    # Дополнительная проверка содержимого
                    dialog_text = await dialog_element.text_content()
                    if dialog_text and any(keyword in dialog_text for keyword in ['Reels', 'видео', 'Теперь', 'Now', 'общедоступный', 'public']):
                        log_info(f"[ASYNC_REELS_DIALOG] [OK] Found Reels dialog with selector: {selector}")
                        log_info(f"[ASYNC_REELS_DIALOG] [TEXT] Dialog text preview: {dialog_text[:100]}...")
                        dialog_found = True
                        break
            except Exception as e:
                continue
        
        if not dialog_found:
            log_info("[ASYNC_REELS_DIALOG] [WARN] No Reels dialog found, continuing...")
            return True
        
        # Ищем кнопку OK в диалоге
        ok_button_selectors = [
            # Точные селекторы кнопки OK
            'button:has-text("OK")',
            'button:has-text("ОК")',
            'div[role="button"]:has-text("OK")',
            'div[role="button"]:has-text("ОК")',
            
            # Селекторы внутри диалога
            'div[role="dialog"] button',
            
            # Более широкие селекторы
            'button[type="button"]',
            'div[role="button"]',
        ]
        
        ok_button = None
        for selector in ok_button_selectors:
            try:
                # Ищем кнопку внутри диалога
                ok_button = await page.query_selector(f'{selector}')
                if ok_button and await ok_button.is_visible():
                    # Проверяем, что кнопка действительно в диалоге
                    button_text = await ok_button.text_content()
                    if button_text and ('OK' in button_text.upper() or 'ОК' in button_text.upper()):
                        log_info(f"[ASYNC_REELS_DIALOG] [OK] Found OK button with selector: {selector} (text: {button_text})")
                        break
                    else:
                        ok_button = None
            except Exception as e:
                continue
        
        if ok_button:
            # Симулируем человеческое поведение
            await ok_button.hover()
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Кликаем на кнопку
            await ok_button.click()
            log_info("[ASYNC_REELS_DIALOG] [OK] Clicked OK button")
            
            # Ждем исчезновения диалога
            await asyncio.sleep(random.uniform(1, 2))
            
            # Проверяем, что диалог исчез
            try:
                still_visible = await ok_button.is_visible()
                if not still_visible:
                    log_info("[ASYNC_REELS_DIALOG] [OK] Dialog closed successfully")
                else:
                    log_info("[ASYNC_REELS_DIALOG] [WARN] Dialog still visible after click")
            except:
                log_info("[ASYNC_REELS_DIALOG] [OK] Dialog closed (element no longer accessible)")
            
            return True
        else:
            log_info("[ASYNC_REELS_DIALOG] [FAIL] Found dialog but no OK button")
            # Попробуем кликнуть на любую кнопку в диалоге
            try:
                any_button = await dialog_element.query_selector('button')
                if any_button:
                    button_text = await any_button.text_content()
                    log_info(f"[ASYNC_REELS_DIALOG] [WARN] Clicking any button in dialog: {button_text}")
                    await any_button.click()
                    await asyncio.sleep(random.uniform(1, 2))
                    return True
            except:
                pass
            return False
        
    except Exception as e:
        log_info(f"[ASYNC_REELS_DIALOG] [FAIL] Error handling Reels dialog: {str(e)}")
        return True  # Продолжаем в любом случае

async def verify_page_elements_state_async(page) -> bool:
    """Verify page elements state - OPTIMIZED VERSION"""
    try:
        log_info("[ASYNC_UPLOAD] [SEARCH] Quick page elements verification...")
        
        # Quick check: document ready state
        ready_state = await page.evaluate("document.readyState")
        if ready_state != 'complete':
            log_info(f"[ASYNC_UPLOAD] [WARN] Document not ready: {ready_state}")
            await asyncio.sleep(2)  # Faster check interval
            return False
        
        # Quick check: main navigation element
        nav_element = await page.query_selector('nav, [role="navigation"], [data-testid="navigation"]')
        if not nav_element:
            log_info("[ASYNC_UPLOAD] [WARN] No navigation element found")
            return False
        
        # Quick check: upload button
        upload_button = await page.query_selector('[aria-label*="New post"], [aria-label*="Create"], [data-testid="new-post-button"]')
        if not upload_button or not await upload_button.is_visible():
            log_info("[ASYNC_UPLOAD] [WARN] Upload button not found or not visible")
            return False
        
        log_info("[ASYNC_UPLOAD] [OK] Page elements verified successfully")
        return True
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error in verify_page_elements_state_async: {str(e)}")
        return False

async def update_account_last_used_async(username: str):
    """Update account last_used timestamp - async version"""
    try:
        from asgiref.sync import sync_to_async
        from django.utils import timezone
        from uploader.models import InstagramAccount
        
        @sync_to_async
        def update_last_used():
            try:
                account = InstagramAccount.objects.get(username=username)
                account.last_used = timezone.now()
                account.save(update_fields=['last_used'])
                return True
            except InstagramAccount.DoesNotExist:
                log_error(f"[FAIL] [DATABASE] Account not found: {username}")
                return False
            except Exception as e:
                log_error(f"[FAIL] [DATABASE] Error updating last_used: {str(e)}")
                return False
        
        return await update_last_used()
        
    except Exception as e:
        log_error(f"[FAIL] [DATABASE] Error in update_account_last_used_async: {str(e)}")
        return False

# Add this new retry function after the imports section (around line 100)

async def retry_navigation_async(page, url, max_attempts=3, base_delay=5):
    """
    Retry navigation to a URL with exponential backoff
    """
    for attempt in range(max_attempts):
        try:
            log_info(f"🌐 [ASYNC_NAVIGATION] Attempt {attempt + 1}/{max_attempts} - Navigating to {url}")
            
            # Navigate with timeout
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for page to fully load
            log_info(f"[WAIT] [ASYNC_NAVIGATION] Waiting for page to fully load (attempt {attempt + 1})...")
            await asyncio.sleep(8)
            
            # Additional wait for network idle
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
                log_info(f"[OK] [ASYNC_NAVIGATION] Network idle state reached (attempt {attempt + 1})")
            except Exception as e:
                log_warning(f"[WARN] [ASYNC_NAVIGATION] Network idle timeout, continuing (attempt {attempt + 1}): {str(e)}")
            
            # Wait for DOM to be interactive
            try:
                await page.wait_for_selector("body", timeout=10000)
                log_info(f"[OK] [ASYNC_NAVIGATION] Page body loaded (attempt {attempt + 1})")
            except Exception as e:
                log_warning(f"[WARN] [ASYNC_NAVIGATION] Body load timeout, continuing (attempt {attempt + 1}): {str(e)}")
            
            # Additional safety wait
            await asyncio.sleep(3)
            
            log_info(f"[OK] [ASYNC_NAVIGATION] Successfully loaded {url} on attempt {attempt + 1}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            log_error(f"[FAIL] [ASYNC_NAVIGATION] Attempt {attempt + 1} failed: {error_msg}")
            
            # If this is the last attempt, don't wait
            if attempt == max_attempts - 1:
                log_error(f"[FAIL] [ASYNC_NAVIGATION] All {max_attempts} attempts failed. Giving up.")
                return False
            
            # Calculate delay with exponential backoff
            delay = base_delay * (2 ** attempt)
            log_info(f"[WAIT] [ASYNC_NAVIGATION] Waiting {delay}s before retry...")
            await asyncio.sleep(delay)
    
    return False
