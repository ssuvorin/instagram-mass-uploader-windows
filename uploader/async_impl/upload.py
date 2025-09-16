"""Auto-refactored module: upload"""
from .logging import logger

from .crop import handle_crop_async
from .file_input import check_for_file_dialog_async
from .file_input import find_file_input_adaptive_async
from .human import _type_like_human_async
from .human import click_element_with_behavior_async
from .human import simulate_page_scan_async
from .human import simulate_random_browsing_async
from .runner import get_task_with_accounts_async
from .runner import process_account_batch_async
from .services import update_task_status_async
from .utils_dom import add_video_location_async
from .utils_dom import add_video_mentions_async
from .utils_dom import check_for_dropdown_menu_async
from .utils_dom import check_video_posted_successfully_async
from .utils_dom import cleanup_original_video_files_async
from .utils_dom import handle_anti_automation_warning_async
from .utils_dom import click_post_option_async
from .utils_dom import click_share_button_async
from .utils_dom import find_element_with_selectors_async
from .utils_dom import retry_navigation_async
from .utils_dom import wait_for_page_ready_async
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
from ..multilingual_selector_provider import get_multilingual_selector_provider, LocaleResolver
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

# Fallback PARALLEL_CONFIG: import from legacy config if available, else use sane defaults
try:
    from ..bulk_tasks_playwright_async import PARALLEL_CONFIG as _GLOBAL_PARALLEL_CONFIG
except Exception:
    _GLOBAL_PARALLEL_CONFIG = None

PARALLEL_CONFIG = _GLOBAL_PARALLEL_CONFIG or {
    'MAX_CONCURRENT_ACCOUNTS': 3,
    'MAX_RETRIES_PER_ACCOUNT': 2,
    'ACCOUNT_START_DELAY': (5, 15),
    'BATCH_SIZE': 5,
}


async def navigate_to_upload_with_human_behavior_async(page, account_details=None):
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
            # NEW: Dismiss anti-automation warning if it appears post-login
            try:
                await handle_anti_automation_warning_async(page)
            except Exception:
                pass
            
            # Additional verification - check for file input immediately (ПОЛНАЯ КОПИЯ из sync)
            try:
                final_url = page.url
                log_info(f"[ASYNC_UPLOAD] [LOCATION] Final URL: {final_url}")
                
                # Check if we can see file input elements immediately (ПОЛНАЯ КОПИЯ из sync)
                file_inputs = await page.query_selector_all('input[type="file"]')
                log_info(f"[ASYNC_UPLOAD] [FOLDER] Found {len(file_inputs)} file input elements")
                
                # Also check for semantic file input selectors (ПОЛНАЯ КОПИЯ из sync)
                semantic_file_inputs = []
                semantic_selectors = SelectorConfig.FILE_INPUT
                
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

async def navigate_to_upload_core_async(page, account=None):
    """Navigate to upload page with human behavior - OPTIMIZED VERSION with multilingual support"""
    try:
        log_info("[ASYNC_UPLOAD] [BRAIN] Starting navigation to upload page")
        
        # Resolve account locale for multilingual selectors
        locale = 'ru'  # default
        if account:
            locale = LocaleResolver.resolve_account_locale(account)
            log_info(f"[ASYNC_UPLOAD] [LOCALE] Using locale: {locale} for account")
        
        # Get multilingual selector provider
        provider = get_multilingual_selector_provider()
        
        # Quick page readiness check
        page_ready = await wait_for_page_ready_async(page, max_wait_time=10.0)  # Reduced timeout
        if not page_ready:
            log_info("[ASYNC_UPLOAD] [WARN] Page not ready, but proceeding with navigation...")
        
        # Simulate page assessment
        await simulate_page_scan_async(page)
        
        # Find upload button with multilingual selectors
        upload_button_selectors = provider.get_upload_button_selectors(locale)
        upload_button = await find_element_with_selectors_async(page, upload_button_selectors)
        
        if not upload_button:
            log_info("[ASYNC_UPLOAD] [WARN] Upload button not found, trying broader detection...")
            broader = await try_broader_upload_detection_async(page)
            if not broader:
                log_info("[ASYNC_UPLOAD] [RETRY] Broader detection failed, retrying with page refresh...")
                return await retry_upload_with_page_refresh_async(page)
            return True
        
        # Quick check upload button readiness
        try:
            is_visible = await upload_button.is_visible()
            if not is_visible:
                log_info("[ASYNC_UPLOAD] [WARN] Upload button not visible, waiting briefly...")
                await asyncio.sleep(2.0 + random.uniform(-0.5, 0.5))
                
                # Try to find the button again
                upload_button = await find_element_with_selectors_async(page, SelectorConfig.UPLOAD_BUTTON)
                if not upload_button:
                    log_info("[ASYNC_UPLOAD] [FAIL] Upload button still not found after retry; using broader detection")
                    broader = await try_broader_upload_detection_async(page)
                    if not broader:
                        return await retry_upload_with_page_refresh_async(page)
                    return True
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
            log_info("[ASYNC_UPLOAD] [WARN] Standard navigation failed; trying broader detection then refresh...")
            broader = await try_broader_upload_detection_async(page)
            if not broader:
                return await retry_upload_with_page_refresh_async(page)
            return True
        
        return success
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Navigation failed: {str(e)}")
        log_info("[ASYNC_UPLOAD] [RETRY] Trying broader detection then refresh...")
        broader = await try_broader_upload_detection_async(page)
        if not broader:
            return await retry_upload_with_page_refresh_async(page)
        return True

async def handle_post_upload_click_async(page, account=None) -> bool:
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
            return await click_post_option_async(page, account)
        
        # ENHANCED: Longer additional wait and check again
        additional_wait = 5.0 + random.uniform(-1.0, 1.0)  # Increased from 2.0 to 5.0 seconds
        log_info(f"[ASYNC_UPLOAD] [WAIT] Waiting additional {additional_wait:.1f}s (enhanced timeout)...")
        await asyncio.sleep(additional_wait)
        
        if await check_for_file_dialog_async(page):
            log_info("[ASYNC_UPLOAD] [FOLDER] File dialog appeared after enhanced delay")
            return True
        
        if await check_for_dropdown_menu_async(page):
            log_info("[ASYNC_UPLOAD] [CLIPBOARD] Menu appeared after enhanced delay")
            return await click_post_option_async(page, account)
        
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
        upload_button = await find_element_with_selectors_async(page, SelectorConfig.UPLOAD_BUTTON)
        
        if not upload_button:
            log_info("[ASYNC_UPLOAD] [WARN] Upload button not found after refresh; trying broader detection...")
            broader = await try_broader_upload_detection_async(page)
            if not broader:
                log_info("[ASYNC_UPLOAD] [FAIL] Broader detection after refresh failed")
                return False
            return True
        
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
            return await click_post_option_async(page, account)
        
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

async def try_broader_upload_detection_async(page) -> bool:
    """Try broader detection methods - ENHANCED with additional wait and more robust detection"""
    try:
        log_info("[ASYNC_UPLOAD] [RETRY] Attempting enhanced broader upload interface detection...")
        
        # ENHANCED: Additional wait before broader detection
        broader_wait = 3.0 + random.uniform(-1.0, 1.0)
        log_info(f"[ASYNC_UPLOAD] [WAIT] Waiting {broader_wait:.1f}s before broader detection...")
        await asyncio.sleep(broader_wait)
        
        # Enhanced upload indicators with more comprehensive selectors (centralized)
        upload_indicators = SelectorConfig.UPLOAD_BROAD_INDICATORS
        
        for indicator in upload_indicators:
            try:
                element = await page.query_selector(indicator)
                if element and await element.is_visible():
                    log_info(f"[ASYNC_UPLOAD] [TARGET] Found upload indicator: {indicator}")
                    
                    # ENHANCED: Click behavior for buttons and interactive elements
                    if any(keyword in indicator.lower() for keyword in ['button', 'div[role="button"]', 'a[role="link"]']):
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
            upload_keywords = SelectorConfig.UPLOAD_KEYWORDS
            
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

# Removed deprecated direct URL navigation to /create/select/ per latest IG behavior changes.

# Compatibility fallback for legacy callers expecting navigate_to_upload_alternative_async
async def navigate_to_upload_alternative_async(page) -> bool:
    """Fallback alternative navigation: delegate to core navigation logic."""
    try:
        return await navigate_to_upload_core_async(page)
    except Exception:
        return False

async def upload_video_with_human_behavior_async(page, video_file_path, video_obj, account=None):
    """Upload video with advanced human behavior and multilingual support"""
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
        return await upload_video_core_async(page, video_file_path, video_obj, account)
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Upload failed: {str(e)}")
        return False

async def upload_video_core_async(page, video_file_path, video_obj, account=None):
    """Core video upload logic - FULL ADAPTIVE SEARCH with multilingual support"""
    try:
        log_info(f"[ASYNC_UPLOAD] [FOLDER] Starting adaptive file input search for: {os.path.basename(video_file_path)}")
        
        # Resolve account locale for multilingual selectors
        locale = 'ru'  # default
        if account:
            locale = LocaleResolver.resolve_account_locale(account)
            log_info(f"[ASYNC_UPLOAD] [LOCALE] Using locale: {locale} for account")
        
        # Get multilingual selector provider
        provider = get_multilingual_selector_provider()
        
        # Initialize advanced human behavior for this session
        from ..advanced_human_behavior import init_advanced_human_behavior
        init_advanced_human_behavior(page)
        
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
        await handle_reels_dialog_async(page, account)
        
        # Handle crop (FULL ADAPTIVE VERSION)
        if not await handle_crop_async(page, account):
            log_info("[ASYNC_UPLOAD] [FAIL] Failed to handle crop")
            return False
        
        # 🔥 ИСПРАВЛЕННАЯ ЛОГИКА: Click Next buttons FIRST (like sync version)
        # В sync версии: for i in range(2): _click_next_button(i + 1)
        log_info("[ASYNC_UPLOAD] [RETRY] Clicking Next buttons (like sync version)...")
        for step in range(2):  # Click Next twice like sync version
            next_success = await click_next_button_async(page, step + 1, account)
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
            caption_success = await add_video_caption_async(page, caption_text, account)
            if not caption_success:
                log_info(f"[ASYNC_UPLOAD] [WARN] Failed to add caption, but continuing...")
        else:
            log_info(f"[ASYNC_UPLOAD] [WARN] No caption text to add")
        
        # Add location if available (like sync _set_location_selenium_style)
        log_info(f"[ASYNC_UPLOAD] [LOCATION] Adding location for video_obj: {type(video_obj)}")
        await add_video_location_async(page, video_obj, account)
        
        # Add mentions if available (like sync _set_mentions_selenium_style)
        log_info(f"[ASYNC_UPLOAD] [USERS] Adding mentions for video_obj: {type(video_obj)}")
        await add_video_mentions_async(page, video_obj, account)
        
        # Click Share button (like sync _post_video_selenium_style)
        log_info("[ASYNC_UPLOAD] [START] Clicking Share button...")
        share_success = await click_share_button_async(page, account)
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

async def click_next_button_async(page, step_number, account=None):
    """Click next button with human-like behavior - ENHANCED with multilingual support"""
    try:
        log_info(f"[ASYNC_UPLOAD] Clicking next button for step {step_number}...")
        
        # Resolve account locale for multilingual selectors
        locale = 'ru'  # default
        if account:
            locale = LocaleResolver.resolve_account_locale(account)
            log_info(f"[ASYNC_UPLOAD] [LOCALE] Using locale: {locale} for account")
        
        # Get multilingual selector provider
        provider = get_multilingual_selector_provider()
        
        # Human-like delay before clicking (ПОЛНАЯ КОПИЯ из sync)
        await asyncio.sleep(random.uniform(3, 5))
        
        # Look for next button with multilingual selectors
        next_button_selectors = provider.get_next_button_selectors(locale)
        
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
                    if any(keyword in button_text.lower() for keyword in SelectorConfig.NEXT_BUTTON_KEYWORDS):
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

async def add_video_caption_async(page, caption_text, account=None):
    """Add video caption - FULL VERSION with multilingual support"""
    try:
        if not caption_text:
            log_info("[ASYNC_UPLOAD] No caption text provided")
            return True
        
        log_info(f"[ASYNC_UPLOAD] Setting caption: {caption_text[:50]}...")
        
        # Resolve account locale for multilingual selectors
        locale = 'ru'  # default
        if account:
            locale = LocaleResolver.resolve_account_locale(account)
            log_info(f"[ASYNC_UPLOAD] [LOCALE] Using locale: {locale} for account")
        
        # Get multilingual selector provider
        provider = get_multilingual_selector_provider()
        
        # Wait a bit before caption
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        # Find caption field with multilingual selectors
        caption_field_selectors = provider.get_caption_textarea_selectors(locale)
        
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
            # Debug: log all available textbox elements
            try:
                all_textboxes = await page.query_selector_all('[role="textbox"]')
                log_info(f"[ASYNC_UPLOAD] [DEBUG] Found {len(all_textboxes)} textbox elements")
                
                contenteditable_divs = await page.query_selector_all('div[contenteditable="true"]')
                log_info(f"[ASYNC_UPLOAD] [DEBUG] Found {len(contenteditable_divs)} contenteditable divs")
                
                if contenteditable_divs:
                    for i, div in enumerate(contenteditable_divs[:3]):  # Check first 3
                        aria_label = await div.get_attribute('aria-label') or 'no aria-label'
                        placeholder = await div.get_attribute('aria-placeholder') or 'no placeholder'
                        log_info(f"[ASYNC_UPLOAD] [DEBUG] Div {i}: aria-label='{aria_label}', placeholder='{placeholder}'")
            except Exception as debug_error:
                log_info(f"[ASYNC_UPLOAD] [DEBUG] Debug failed: {str(debug_error)}")
            
            return False
        
        # Click field and wait (like sync version)
        await caption_field.click()
        await asyncio.sleep(random.uniform(0.8, 1.5))
        
        # Check if it's a contenteditable element
        is_contenteditable = await caption_field.get_attribute('contenteditable')
        
        # Decide typing strategy
        from ..advanced_human_behavior import get_advanced_human_behavior
        human_behavior = get_advanced_human_behavior()

        # For contenteditable fields we ENFORCE strict char-by-char (avoid any paste/fill)
        if is_contenteditable == 'true':
            log_info("[ASYNC_UPLOAD] [CONTENTEDITABLE] Humanized typing mode")
            from .human import _type_human_contenteditable
            await _type_human_contenteditable(page, caption_field, caption_text)
        else:
            # Non-contenteditable inputs: prefer advanced behavior, else our human typing
            if human_behavior:
                success = await human_behavior.human_type(caption_field, caption_text, "caption_input")
                if success:
                    log_info("[ASYNC_UPLOAD] [OK] Caption added with advanced human behavior")
                else:
                    log_info("[ASYNC_UPLOAD] [FALLBACK] Advanced typing failed, using basic approach")
                    await _type_like_human_async(page, caption_field, caption_text)
            else:
                log_info("[ASYNC_UPLOAD] [TEXTAREA] Using textarea approach")
                try:
                    await caption_field.fill('')
                except Exception:
                    pass
                await asyncio.sleep(random.uniform(0.5, 1.0))
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
        
        # Update task status using business rule: all -> COMPLETED; some -> PARTIALLY_COMPLETED; none -> FAILED
        if results['successful'] == 0:
            final_status = 'FAILED'
            status_marker = '[FAIL]'
        elif results['successful'] == total_accounts:
            final_status = 'COMPLETED'
            status_marker = '[OK]'
        else:
            final_status = 'PARTIALLY_COMPLETED'
            status_marker = '[WARN]'
        log_info(f"{status_marker} [PARALLEL_ASYNC] Final status: {final_status} ({results['successful']}/{total_accounts} accounts succeeded)")
        
        # Persist task status with results payload
        await update_task_status_async(task_id, final_status, results)
        
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

async def run_bulk_upload_task_async(task_id):
    """
    Main async bulk upload task - now with parallel processing!
    This is the improved version that processes multiple accounts simultaneously
    """
    return await run_bulk_upload_task_parallel_async(task_id)

async def handle_reels_dialog_async(page, account=None):
    """Handle Reels dialog that may appear after file upload with multilingual support"""
    try:
        log_info("[ASYNC_REELS_DIALOG] [SEARCH] Checking for Reels dialog...")
        
        # Resolve account locale for multilingual selectors
        locale = 'ru'  # default
        if account:
            locale = LocaleResolver.resolve_account_locale(account)
            log_info(f"[ASYNC_REELS_DIALOG] [LOCALE] Using locale: {locale} for account")
        
        # Get multilingual selector provider
        provider = get_multilingual_selector_provider()
        
        # Ждем немного для появления диалога
        await asyncio.sleep(random.uniform(1, 2))
        
        # Надежные селекторы для диалога Reels (без динамических классов)
        reels_dialog_selectors = SelectorConfig.REELS_DIALOG_SELECTORS
        
        # Ищем диалог
        dialog_found = False
        dialog_element = None
        
        for selector in reels_dialog_selectors:
            try:
                dialog_element = await page.query_selector(selector)
                if dialog_element and await dialog_element.is_visible():
                    # Дополнительная проверка содержимого (мультиязычная)
                    dialog_text = await dialog_element.text_content()
                    if dialog_text and any(keyword in dialog_text for keyword in SelectorConfig.REELS_DIALOG_KEYWORDS):
                        log_info(f"[ASYNC_REELS_DIALOG] [OK] Found Reels dialog with selector: {selector}")
                        log_info(f"[ASYNC_REELS_DIALOG] [TEXT] Dialog text preview: {dialog_text[:100]}...")
                        dialog_found = True
                        break
            except Exception as e:
                continue
        
        if not dialog_found:
            log_info("[ASYNC_REELS_DIALOG] [WARN] No Reels dialog found, continuing...")
            return True
        
        # Используем централизованные селекторы из SelectorConfig
        ok_button_selectors = SelectorConfig.REELS_DIALOG_ACCEPT_BUTTONS
        
        ok_button = None
        for selector in ok_button_selectors:
            try:
                # Ищем кнопку внутри диалога
                ok_button = await page.query_selector(f'{selector}')
                if ok_button and await ok_button.is_visible():
                    # Проверяем, что кнопка действительно подходящая
                    button_text = await ok_button.text_content()
                    if button_text and any(keyword.upper() in button_text.upper() for keyword in SelectorConfig.ACCEPT_BUTTON_KEYWORDS):
                        log_info(f"[ASYNC_REELS_DIALOG] [OK] Found accept button with selector: {selector} (text: {button_text})")
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

__all__ = ['navigate_to_upload_with_human_behavior_async', 'navigate_to_upload_core_async', 'handle_post_upload_click_async', 'retry_upload_with_page_refresh_async', 'try_broader_upload_detection_async', 'navigate_to_upload_alternative_async', 'upload_video_with_human_behavior_async', 'upload_video_core_async', 'click_next_button_async', 'add_video_caption_async', 'add_human_delay_between_uploads_async', 'run_bulk_upload_task_parallel_async', 'run_bulk_upload_task_async', 'handle_reels_dialog_async']


# === PASS 5 SAFE SHIMS UPLOAD (non-breaking) ===
from .logging import logger
import inspect, asyncio
try:
    _orig_navigate_to_upload_with_human_behavior_async = navigate_to_upload_with_human_behavior_async
except Exception:
    _orig_navigate_to_upload_with_human_behavior_async = None
async def navigate_to_upload_with_human_behavior_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:navigate_to_upload_with_human_behavior_async start')
    try:
        if _orig_navigate_to_upload_with_human_behavior_async is None:
            logger.warning('UPLOAD:navigate_to_upload_with_human_behavior_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_navigate_to_upload_with_human_behavior_async):
            res = await _orig_navigate_to_upload_with_human_behavior_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_navigate_to_upload_with_human_behavior_async(*args, **kwargs))
        logger.info('UPLOAD:navigate_to_upload_with_human_behavior_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:navigate_to_upload_with_human_behavior_async error: ' + repr(e))
        raise
try:
    _orig_navigate_to_upload_core_async = navigate_to_upload_core_async
except Exception:
    _orig_navigate_to_upload_core_async = None
async def navigate_to_upload_core_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:navigate_to_upload_core_async start')
    try:
        if _orig_navigate_to_upload_core_async is None:
            logger.warning('UPLOAD:navigate_to_upload_core_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_navigate_to_upload_core_async):
            res = await _orig_navigate_to_upload_core_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_navigate_to_upload_core_async(*args, **kwargs))
        logger.info('UPLOAD:navigate_to_upload_core_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:navigate_to_upload_core_async error: ' + repr(e))
        raise
try:
    _orig_handle_post_upload_click_async = handle_post_upload_click_async
except Exception:
    _orig_handle_post_upload_click_async = None
async def handle_post_upload_click_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:handle_post_upload_click_async start')
    try:
        if _orig_handle_post_upload_click_async is None:
            logger.warning('UPLOAD:handle_post_upload_click_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_handle_post_upload_click_async):
            res = await _orig_handle_post_upload_click_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_handle_post_upload_click_async(*args, **kwargs))
        logger.info('UPLOAD:handle_post_upload_click_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:handle_post_upload_click_async error: ' + repr(e))
        raise
try:
    _orig_retry_upload_with_page_refresh_async = retry_upload_with_page_refresh_async
except Exception:
    _orig_retry_upload_with_page_refresh_async = None
async def retry_upload_with_page_refresh_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:retry_upload_with_page_refresh_async start')
    try:
        if _orig_retry_upload_with_page_refresh_async is None:
            logger.warning('UPLOAD:retry_upload_with_page_refresh_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_retry_upload_with_page_refresh_async):
            res = await _orig_retry_upload_with_page_refresh_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_retry_upload_with_page_refresh_async(*args, **kwargs))
        logger.info('UPLOAD:retry_upload_with_page_refresh_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:retry_upload_with_page_refresh_async error: ' + repr(e))
        raise
try:
    _orig_try_broader_upload_detection_async = try_broader_upload_detection_async
except Exception:
    _orig_try_broader_upload_detection_async = None
async def try_broader_upload_detection_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:try_broader_upload_detection_async start')
    try:
        if _orig_try_broader_upload_detection_async is None:
            logger.warning('UPLOAD:try_broader_upload_detection_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_try_broader_upload_detection_async):
            res = await _orig_try_broader_upload_detection_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_try_broader_upload_detection_async(*args, **kwargs))
        logger.info('UPLOAD:try_broader_upload_detection_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:try_broader_upload_detection_async error: ' + repr(e))
        raise
try:
    _orig_navigate_to_upload_alternative_async = navigate_to_upload_alternative_async
except Exception:
    _orig_navigate_to_upload_alternative_async = None
async def navigate_to_upload_alternative_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:navigate_to_upload_alternative_async start')
    try:
        if _orig_navigate_to_upload_alternative_async is None:
            logger.warning('UPLOAD:navigate_to_upload_alternative_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_navigate_to_upload_alternative_async):
            res = await _orig_navigate_to_upload_alternative_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_navigate_to_upload_alternative_async(*args, **kwargs))
        logger.info('UPLOAD:navigate_to_upload_alternative_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:navigate_to_upload_alternative_async error: ' + repr(e))
        raise
try:
    _orig_upload_video_with_human_behavior_async = upload_video_with_human_behavior_async
except Exception:
    _orig_upload_video_with_human_behavior_async = None
async def upload_video_with_human_behavior_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:upload_video_with_human_behavior_async start')
    try:
        if _orig_upload_video_with_human_behavior_async is None:
            logger.warning('UPLOAD:upload_video_with_human_behavior_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_upload_video_with_human_behavior_async):
            res = await _orig_upload_video_with_human_behavior_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_upload_video_with_human_behavior_async(*args, **kwargs))
        logger.info('UPLOAD:upload_video_with_human_behavior_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:upload_video_with_human_behavior_async error: ' + repr(e))
        raise
try:
    _orig_upload_video_core_async = upload_video_core_async
except Exception:
    _orig_upload_video_core_async = None
async def upload_video_core_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:upload_video_core_async start')
    try:
        if _orig_upload_video_core_async is None:
            logger.warning('UPLOAD:upload_video_core_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_upload_video_core_async):
            res = await _orig_upload_video_core_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_upload_video_core_async(*args, **kwargs))
        logger.info('UPLOAD:upload_video_core_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:upload_video_core_async error: ' + repr(e))
        raise
try:
    _orig_click_next_button_async = click_next_button_async
except Exception:
    _orig_click_next_button_async = None
async def click_next_button_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:click_next_button_async start')
    try:
        if _orig_click_next_button_async is None:
            logger.warning('UPLOAD:click_next_button_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_click_next_button_async):
            res = await _orig_click_next_button_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_click_next_button_async(*args, **kwargs))
        logger.info('UPLOAD:click_next_button_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:click_next_button_async error: ' + repr(e))
        raise
try:
    _orig_add_video_caption_async = add_video_caption_async
except Exception:
    _orig_add_video_caption_async = None
async def add_video_caption_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:add_video_caption_async start')
    try:
        if _orig_add_video_caption_async is None:
            logger.warning('UPLOAD:add_video_caption_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_add_video_caption_async):
            res = await _orig_add_video_caption_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_add_video_caption_async(*args, **kwargs))
        logger.info('UPLOAD:add_video_caption_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:add_video_caption_async error: ' + repr(e))
        raise
try:
    _orig_add_human_delay_between_uploads_async = add_human_delay_between_uploads_async
except Exception:
    _orig_add_human_delay_between_uploads_async = None
async def add_human_delay_between_uploads_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:add_human_delay_between_uploads_async start')
    try:
        if _orig_add_human_delay_between_uploads_async is None:
            logger.warning('UPLOAD:add_human_delay_between_uploads_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_add_human_delay_between_uploads_async):
            res = await _orig_add_human_delay_between_uploads_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_add_human_delay_between_uploads_async(*args, **kwargs))
        logger.info('UPLOAD:add_human_delay_between_uploads_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:add_human_delay_between_uploads_async error: ' + repr(e))
        raise
try:
    _orig_run_bulk_upload_task_parallel_async = run_bulk_upload_task_parallel_async
except Exception:
    _orig_run_bulk_upload_task_parallel_async = None
async def run_bulk_upload_task_parallel_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:run_bulk_upload_task_parallel_async start')
    try:
        if _orig_run_bulk_upload_task_parallel_async is None:
            logger.warning('UPLOAD:run_bulk_upload_task_parallel_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_run_bulk_upload_task_parallel_async):
            res = await _orig_run_bulk_upload_task_parallel_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_run_bulk_upload_task_parallel_async(*args, **kwargs))
        logger.info('UPLOAD:run_bulk_upload_task_parallel_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:run_bulk_upload_task_parallel_async error: ' + repr(e))
        raise
try:
    _orig_run_bulk_upload_task_async = run_bulk_upload_task_async
except Exception:
    _orig_run_bulk_upload_task_async = None
async def run_bulk_upload_task_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:run_bulk_upload_task_async start')
    try:
        if _orig_run_bulk_upload_task_async is None:
            logger.warning('UPLOAD:run_bulk_upload_task_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_run_bulk_upload_task_async):
            res = await _orig_run_bulk_upload_task_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_run_bulk_upload_task_async(*args, **kwargs))
        logger.info('UPLOAD:run_bulk_upload_task_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:run_bulk_upload_task_async error: ' + repr(e))
        raise
try:
    _orig_handle_reels_dialog_async = handle_reels_dialog_async
except Exception:
    _orig_handle_reels_dialog_async = None
async def handle_reels_dialog_async(*args, **kwargs):
    """Auto-wrapped function (UPLOAD). Behavior unchanged; adds structured logs."""
    logger.info('UPLOAD:handle_reels_dialog_async start')
    try:
        if _orig_handle_reels_dialog_async is None:
            logger.warning('UPLOAD:handle_reels_dialog_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_handle_reels_dialog_async):
            res = await _orig_handle_reels_dialog_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_handle_reels_dialog_async(*args, **kwargs))
        logger.info('UPLOAD:handle_reels_dialog_async ok')
        return res
    except Exception as e:
        logger.error('UPLOAD:handle_reels_dialog_async error: ' + repr(e))
        raise