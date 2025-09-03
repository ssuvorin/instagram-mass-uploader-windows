"""
Bulk upload tasks using Playwright for Instagram automation
"""

import os
import psutil
import json
import time
import traceback
import subprocess
import logging
import requests
import threading
import queue
import re
import imaplib
import email
from tempfile import NamedTemporaryFile
from pathlib import Path
from .models import BulkUploadTask, InstagramAccount, VideoFile, BulkUploadAccount
import random
import math
import asyncio
from datetime import datetime, timedelta
import sys
import tempfile
import shutil
import django
from django.db import transaction
from django.utils import timezone

# SSL Configuration - Fix SSL errors with proxies
try:
    import ssl_fix  # Apply SSL fixes immediately
except ImportError:
    # Fallback SSL configuration
    try:
        import ssl
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        ssl._create_default_https_context = ssl._create_unverified_context
        print("[SSL] Fallback SSL configuration applied")
    except Exception as e:
        print(f"[SSL] Warning: Could not configure SSL settings: {e}")

# Import our optimization modules
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
    process_browser_result, handle_account_task_error, handle_critical_task_error,
    clear_human_verification_badge
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
from .login_optimized import perform_instagram_login_optimized, _check_if_already_logged_in, _fill_login_credentials, _submit_login_form, _handle_login_completion, _handle_2fa_verification, _enter_verification_code
from .logging_utils import log_info, log_error, log_debug, log_warning
from .human_behavior import AdvancedHumanBehavior, init_human_behavior, get_human_behavior
from .captcha_solver import solve_recaptcha_if_present, detect_recaptcha_on_page, solve_recaptcha_if_present_sync

# Disable verbose Playwright logging
logging.getLogger('playwright').setLevel(logging.ERROR)
logging.getLogger('playwright._impl').setLevel(logging.ERROR)

# Suppress other verbose loggers
for logger_name in ['urllib3', 'requests', 'asyncio']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Apply browser environment configuration
for env_var, value in BrowserConfig.ENV_VARS.items():
    os.environ[env_var] = value

# Suppress browser console logs and detailed traces
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '0'
os.environ['DEBUG'] = ''
os.environ['PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'] = '1'

# Additional environment variables to suppress verbose Playwright output
os.environ['PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS'] = '1'
os.environ['PLAYWRIGHT_DISABLE_COLORS'] = '1'
os.environ['PLAYWRIGHT_QUIET'] = '1'

# Suppress Chrome/Chromium verbose logging
os.environ['CHROME_LOG_FILE'] = '/dev/null'
os.environ['CHROME_HEADLESS'] = '1'

# Configure Python logging to filter out Playwright verbose messages
class PlaywrightLogFilter(logging.Filter):
    """Filter to block verbose Playwright logs"""
    
    def filter(self, record):
        # Block all Playwright verbose messages
        message = record.getMessage().lower()
        return not any(keyword in message for keyword in VerboseFilters.PLAYWRIGHT_VERBOSE_KEYWORDS)

# Apply the filter to all relevant loggers
playwright_filter = PlaywrightLogFilter()
for logger_name in ['playwright', 'playwright._impl', 'playwright.sync_api', 'root']:
    try:
        target_logger = logging.getLogger(logger_name)
        target_logger.addFilter(playwright_filter)
        target_logger.setLevel(logging.CRITICAL)
    except:
        pass

# Also apply to the root logger to catch any unfiltered messages
root_logger = logging.getLogger()
root_logger.addFilter(playwright_filter)

# Import Playwright and Bot modules
try:
    from playwright.sync_api import sync_playwright
    from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
    from bot.src.instagram_uploader.browser_dolphin import DolphinBrowser
    from bot.src.instagram_uploader.email_client import Email
except ImportError as e:
    print(f"Error importing required modules: {str(e)}. Make sure they're installed.")

# Setup logging
logger = logging.getLogger('uploader.bulk_tasks')

# Enhanced logging system for web interface
import json
from datetime import datetime
from django.core.cache import cache

class WebLogger:
    """Enhanced logger that sends logs to web interface in real-time with improved categorization"""
    
    def __init__(self, task_id, account_id=None):
        self.task_id = task_id
        self.account_id = account_id
        self.log_buffer = []
        self.critical_events = []  # Track critical events separately
        
    def log(self, level, message, category=None):
        """Log message with enhanced formatting for web interface"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Check if message contains any verbose keywords
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in VerboseFilters.PLAYWRIGHT_VERBOSE_KEYWORDS):
            return  # Skip these verbose logs
        
        # Determine if this is a critical event
        is_critical = self._is_critical_event(level, message, category)
        
        # Enhanced formatting based on category and level
        formatted_message = self._format_message(message, level, category)
        
        # Create formatted log entry
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': formatted_message,
            'category': category or 'GENERAL',
            'is_critical': is_critical,
            'task_id': self.task_id,
            'account_id': self.account_id
        }
        
        # Add to buffer
        self.log_buffer.append(log_entry)
        
        # Track critical events
        if is_critical:
            self.critical_events.append(log_entry)
        
        # Store in cache for real-time updates
        # Always append to the main task log collection
        main_cache_key = f"task_logs_{self.task_id}"
        existing_main_logs = cache.get(main_cache_key, [])
        existing_main_logs.append(log_entry)
        if len(existing_main_logs) > Limits.MAX_LOG_ENTRIES:
            existing_main_logs = existing_main_logs[-Limits.MAX_LOG_ENTRIES:]
        cache.set(main_cache_key, existing_main_logs, timeout=3600)
        
        # If logging for a specific account, also write to account-specific cache
        if self.account_id:
            account_cache_key = f"task_logs_{self.task_id}_account_{self.account_id}"
            existing_account_logs = cache.get(account_cache_key, [])
            existing_account_logs.append(log_entry)
            if len(existing_account_logs) > Limits.MAX_LOG_ENTRIES:
                existing_account_logs = existing_account_logs[-Limits.MAX_LOG_ENTRIES:]
            cache.set(account_cache_key, existing_account_logs, timeout=3600)
        
        # Also store summary for critical events
        if is_critical:
            critical_cache_key = f"task_critical_{self.task_id}"
            existing_critical = cache.get(critical_cache_key, [])
            existing_critical.append(log_entry)
            if len(existing_critical) > 50:  # Keep last 50 critical events
                existing_critical = existing_critical[-50:]
            cache.set(critical_cache_key, existing_critical, timeout=7200)  # 2 hours
        
        # Enhanced console output for important events
        if level in ['ERROR', 'WARNING', 'SUCCESS'] or is_critical:
            console_prefix = self._get_console_prefix(level, category)
            print(f"[{timestamp}] {console_prefix} {formatted_message}")

    def _is_critical_event(self, level, message, category):
        """Determine if an event is critical and needs special attention"""
        critical_keywords = [
            'verification', 'верификация', 'phone', 'телефон', 'captcha', 'human',
            'blocked', 'заблокирован', 'suspended', 'disabled', 'failed login',
            'error uploading', 'browser error', 'dolphin error'
        ]
        
        critical_categories = [
            LogCategories.VERIFICATION, LogCategories.CAPTCHA, 
            LogCategories.LOGIN, LogCategories.DOLPHIN
        ]
        
        return (
            level in ['ERROR', 'WARNING'] or 
            category in critical_categories or
            any(keyword in message.lower() for keyword in critical_keywords)
        )

    def _format_message(self, message, level, category):
        """Enhanced message formatting based on category and level"""
        # Add emoji prefixes based on category
        category_emojis = {
            LogCategories.VERIFICATION: '🔐',
            LogCategories.CAPTCHA: '[BOT]',
            LogCategories.LOGIN: '🔑',
            LogCategories.UPLOAD: '📤',
            LogCategories.DOLPHIN: '🐬',
            LogCategories.NAVIGATION: '🧭',
            LogCategories.HUMAN: '👤',
            LogCategories.CLEANUP: '[CLEAN]',
            LogCategories.DATABASE: '💾'
        }
        
        emoji = category_emojis.get(category, '[CLIPBOARD]')
        
        # Add level indicators
        level_indicators = {
            'ERROR': '[FAIL]',
            'WARNING': '[WARN]',
            'SUCCESS': '[OK]',
            'INFO': 'ℹ️'
        }
        
        level_emoji = level_indicators.get(level, 'ℹ️')
        
        return f"{level_emoji} {emoji} {message}"

    def _get_console_prefix(self, level, category):
        """Get console prefix for different log levels and categories"""
        prefixes = {
            'ERROR': '[🔴 ERROR]',
            'WARNING': '[🟡 WARNING]',
            'SUCCESS': '[🟢 SUCCESS]',
            'INFO': '[🔵 INFO]'
        }
        
        prefix = prefixes.get(level, '[INFO]')
        if category:
            prefix += f'[{category}]'
        return prefix

    def get_summary(self):
        """Get summary of logged events"""
        if not self.log_buffer:
            return {'total': 0, 'by_level': {}, 'by_category': {}, 'critical_count': 0}
        
        summary = {
            'total': len(self.log_buffer),
            'by_level': {},
            'by_category': {},
            'critical_count': len(self.critical_events),
            'latest_critical': self.critical_events[-5:] if self.critical_events else []
        }
        
        for entry in self.log_buffer:
            level = entry['level']
            category = entry['category']
            
            summary['by_level'][level] = summary['by_level'].get(level, 0) + 1
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
        
        return summary

# Global web logger instance
web_logger = None

def init_web_logger(task_id, account_id=None):
    """Initialize web logger for task"""
    global web_logger
    web_logger = WebLogger(task_id, account_id)
    return web_logger

def get_web_logger():
    """Get current web logger instance"""
    return web_logger

# Enhanced logging functions that use web logger
def log_info(message, category=None):
    """Log info message to web interface"""
    if web_logger:
        web_logger.log('INFO', message, category)
    else:
        print(f"[INFO] {message}")

def log_success(message, category=None):
    """Log success message to web interface"""
    if web_logger:
        web_logger.log('SUCCESS', message, category)
    else:
        print(f"[SUCCESS] {message}")

def log_warning(message, category=None):
    """Log warning message to web interface"""
    if web_logger:
        web_logger.log('WARNING', message, category)
    else:
        print(f"[WARNING] {message}")

def log_error(message, category=None):
    """Log error message to web interface"""
    if web_logger:
        web_logger.log('ERROR', message, category)
    else:
        print(f"[ERROR] {message}")

def log_debug(message, category=None):
    """Log debug message to web interface (mapped to INFO for visibility)"""
    if web_logger:
        # Use DEBUG level so we can identify them if needed
        web_logger.log('DEBUG', message, category)
    else:
        print(f"[DEBUG] {message}")

def get_2fa_code(tfa_secret):
    """Get 2FA code from API service"""
    if not tfa_secret:
        return None
        
    try:
        log_info(f"Requesting 2FA code for secret ending in: ...{tfa_secret[-4:]}")
        api_url = f"{APIConstants.TFA_API_URL}{tfa_secret}"
        response = requests.get(api_url)
        response_data = response.json()
        
        if response_data.get("ok") and response_data.get("data", {}).get("otp"):
            log_info("Successfully retrieved 2FA code")
            return response_data["data"]["otp"]
        log_warning("Failed to get valid 2FA code from API")
        return None
    except Exception as e:
        log_error(f"Error getting 2FA code: {str(e)}")
        return None

def get_email_verification_code(email_login, email_password, max_retries=3):
    """Get verification code from email using the Email class with enhanced logging and retry logic"""
    if not email_login or not email_password:
        log_warning("📧 Email credentials not provided for verification code retrieval")
        return None
        
    try:
        log_info(f"📧 [EMAIL_CODE] Starting email verification code retrieval")
        log_info(f"📧 [EMAIL_CODE] Email: {email_login}")
        log_info(f"📧 [EMAIL_CODE] Max retries: {max_retries}")
        
        email_client = Email(email_login, email_password)
        log_info(f"📧 [EMAIL_CODE] Email client initialized successfully")
        
        # First test the connection
        log_info(f"📧 [EMAIL_CODE] Testing email connection...")
        connection_test = email_client.test_connection()
        
        if not connection_test:
            log_error(f"📧 [EMAIL_CODE] [FAIL] Email connection test failed")
            log_error(f"📧 [EMAIL_CODE] Please check:")
            log_error(f"📧 [EMAIL_CODE] - Email address: {email_login}")
            log_error(f"📧 [EMAIL_CODE] - Password is correct")
            log_error(f"📧 [EMAIL_CODE] - Email provider supports IMAP/POP3")
            log_error(f"📧 [EMAIL_CODE] - Two-factor authentication is disabled for email")
            return None
        
        log_info(f"📧 [EMAIL_CODE] [OK] Email connection test successful")
        
        # Now try to get verification code with retry logic
        verification_code = email_client.get_verification_code(max_retries=max_retries, retry_delay=30)
        
        if verification_code:
            log_info(f"📧 [EMAIL_CODE] [OK] Successfully retrieved email verification code: {verification_code}")
            
            # Validate the code format (Instagram codes are 6 digits)
            if len(verification_code) == 6 and verification_code.isdigit():
                log_info(f"📧 [EMAIL_CODE] [OK] Code format validation passed")
                return verification_code
            else:
                log_warning(f"📧 [EMAIL_CODE] [WARN] Invalid code format: {verification_code} (expected 6 digits)")
                return None
        else:
            log_warning("📧 [EMAIL_CODE] [FAIL] No verification code found in email after all retries")
            log_warning("📧 [EMAIL_CODE] Possible reasons:")
            log_warning("📧 [EMAIL_CODE] - Email not received yet (Instagram delays)")
            log_warning("📧 [EMAIL_CODE] - Code is in a different email format")
            log_warning("📧 [EMAIL_CODE] - Email was already read/deleted")
            log_warning("📧 [EMAIL_CODE] - Email provider has connectivity issues")
            return None
            
    except Exception as e:
        log_error(f"📧 [EMAIL_CODE] [FAIL] Error getting email verification code: {str(e)}")
        log_error(f"📧 [EMAIL_CODE] Exception type: {type(e).__name__}")
        return None

def navigate_to_upload_with_human_behavior(page):
    """Navigate to upload page with advanced human behavior - Handles both menu and direct file dialog scenarios"""
    try:
        log_info("[UPLOAD] [START] Starting enhanced navigation to upload interface", LogCategories.NAVIGATION)
        
        # Initialize human behavior
        init_human_behavior(page)
        
        # Use the new InstagramNavigator class with improved logic
        navigator = InstagramNavigator(page, get_human_behavior())
        
        # Debug: Log current page state
        try:
            current_url = page.url
            page_title = page.title()
            log_info(f"[UPLOAD] [LOCATION] Current page: {current_url}", LogCategories.NAVIGATION)
            log_info(f"[UPLOAD] [FILE] Page title: {page_title}", LogCategories.NAVIGATION)
        except Exception as debug_error:
            log_warning(f"[UPLOAD] Could not get page info: {str(debug_error)}", LogCategories.NAVIGATION)
        
        # This now handles multiple scenarios:
        # 1. Menu appears -> select "Публикация" option
        # 2. File dialog opens directly -> proceed immediately
        # 3. Alternative navigation via direct URL
        success = navigator.navigate_to_upload()
        
        if success:
            log_success("[UPLOAD] [OK] Successfully navigated to upload interface", LogCategories.NAVIGATION)
            
            # Additional verification - check for file input immediately
            try:
                final_url = page.url
                log_info(f"[UPLOAD] [LOCATION] Final URL: {final_url}", LogCategories.NAVIGATION)
                
                # Check if we can see file input elements immediately
                file_inputs = page.query_selector_all('input[type="file"]')
                log_info(f"[UPLOAD] [FOLDER] Found {len(file_inputs)} file input elements", LogCategories.NAVIGATION)
                
                # Also check for semantic file input selectors (не зависящие от динамических CSS-классов)
                semantic_file_inputs = []
                semantic_selectors = [
                    'input[accept*="video"]',
                    'input[accept*="image"]', 
                    'input[multiple]',
                    'button:has-text("Выбрать на компьютере")',
                    'button:has-text("Select from computer")',
                    'button:has-text("Select from device")',
                ]
                
                for selector in semantic_selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        semantic_file_inputs.extend(elements)
                    except:
                        continue
                        
                log_info(f"[UPLOAD] [FOLDER] Found {len(semantic_file_inputs)} semantic file input elements", LogCategories.NAVIGATION)
                
                if len(file_inputs) > 0 or len(semantic_file_inputs) > 0:
                    for i, inp in enumerate(file_inputs + semantic_file_inputs):
                        try:
                            inp_accept = inp.get_attribute('accept') or 'any'
                            inp_visible = inp.is_visible()
                            inp_class = inp.get_attribute('class') or 'no-class'
                            log_info(f"[UPLOAD] Input {i+1}: accept='{inp_accept}', visible={inp_visible}, class='{inp_class[:30]}'", LogCategories.NAVIGATION)
                        except:
                            pass
                    
                    log_success("[UPLOAD] [OK] File input elements are ready for upload", LogCategories.NAVIGATION)
                else:
                    log_warning("[UPLOAD] [WARN] No file input elements found after navigation", LogCategories.NAVIGATION)
                            
            except Exception as verify_error:
                log_warning(f"[UPLOAD] Could not verify upload interface: {str(verify_error)}", LogCategories.NAVIGATION)
        else:
            log_error("[UPLOAD] [FAIL] Failed to navigate to upload interface", LogCategories.NAVIGATION)
        
        return success
        
    except Exception as e:
        log_error(f"[UPLOAD] [FAIL] Navigation failed: {str(e)}", LogCategories.NAVIGATION)
        return False

def upload_video_with_human_behavior(page, video_file_path, video_obj):
    """Upload video with advanced human behavior - Now follows exact Selenium pipeline"""
    try:
        log_info(f"[UPLOAD] [VIDEO] Starting video upload following exact Selenium pipeline: {os.path.basename(video_file_path)}")
        
        # Ensure human behavior is initialized
        human_behavior = get_human_behavior()
        if not human_behavior:
            init_human_behavior(page)
            human_behavior = get_human_behavior()
        
        # Use the new InstagramUploader class with Selenium-style pipeline
        uploader = InstagramUploader(page, human_behavior)
        
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
        return uploader.upload_video(video_file_path, video_obj)
        
    except Exception as e:
        log_error(f"[UPLOAD] [FAIL] Upload failed: {str(e)}")
        return False

def click_next_button(page, step_number):
    """Click next button with human-like behavior (like Selenium version)"""
    try:
        log_info(f"[UPLOAD] Clicking next button for step {step_number}...")
        
        # Human-like delay before clicking - увеличено
        time.sleep(random.uniform(3, 5))  # Увеличено с 2, 4
        
        # Look for next button with comprehensive Russian localization and Instagram-specific selectors
        next_button = None
        used_selector = None
        
        for selector in InstagramSelectors.NEXT_BUTTONS:
            try:
                if selector.startswith('//'):
                    # XPath selector
                    next_button = page.query_selector(f"xpath={selector}")
                else:
                    # CSS selector
                    next_button = page.query_selector(selector)
                
                if next_button and next_button.is_visible():
                    # Verify this is actually a next/далее button
                    button_text = next_button.text_content() or ""
                    if any(keyword in button_text.lower() for keyword in ['далее', 'next', 'продолжить', 'continue']):
                        log_info(f"[UPLOAD] [TARGET] Found text-based next button: '{button_text.strip()}' with selector: {selector}")
                        used_selector = selector
                        break
                    elif selector.startswith('div[class*="x1i10hfl"]') and button_text.strip():
                        # For Instagram-specific selectors, if we find a button with any text, it might be the next button
                        log_info(f"[UPLOAD] [TARGET] Found potential Instagram next button: '{button_text.strip()}' with selector: {selector}")
                        used_selector = selector
                        break
                            
            except Exception as e:
                log_warning(f"[UPLOAD] Error with selector {selector} for step {step_number}: {str(e)}")
                continue
        
        if next_button:
            # Human-like interaction
            try:
                # Scroll button into view if needed
                next_button.scroll_into_view_if_needed()
                time.sleep(random.uniform(1.0, 2.0))  # Увеличено с 0.5, 1.0
                
                # Hover over button
                next_button.hover()
                time.sleep(random.uniform(1.0, 2.0))  # Увеличено с 0.5, 1.0
                
                # Use JavaScript click like Selenium version for better reliability - FIXED SYNTAX
                page.evaluate('(element) => element.click()', next_button)
                
                # Wait longer after click
                time.sleep(random.uniform(4, 6))  # Увеличено с 2, 3
                
                log_info(f"[UPLOAD] [OK] Successfully clicked next button for step {step_number}")
                return True
                
            except Exception as click_error:
                log_warning(f"[UPLOAD] [WARN] Error clicking next button: {str(click_error)}")
                
                # Fallback: try direct click
                try:
                    next_button.click()
                    time.sleep(random.uniform(4, 6))  # Увеличено с 2, 3
                    log_info(f"[UPLOAD] [OK] Successfully clicked next button (fallback) for step {step_number}")
                    return True
                except Exception as fallback_error:
                    log_error(f"[UPLOAD] [FAIL] Fallback click also failed: {str(fallback_error)}")
                    return False
        else:
            log_warning(f"[UPLOAD] [WARN] Next button not found for step {step_number}")
            
            # Debug: log available buttons with semantic selectors instead of Instagram-specific classes
            try:
                all_buttons = page.query_selector_all('button, div[role="button"], [role="button"], div[tabindex="0"]')
                log_info(f"[UPLOAD] [SEARCH] Available clickable elements on page for step {step_number}:")
                for i, btn in enumerate(all_buttons[:15]):  # Show first 15 elements
                    try:
                        btn_text = btn.text_content() or "no-text"
                        btn_aria = btn.get_attribute('aria-label') or "no-aria"
                        btn_role = btn.get_attribute('role') or "no-role"
                        btn_tabindex = btn.get_attribute('tabindex') or "no-tabindex"
                        
                        # Show only elements that might be buttons (using semantic attributes)
                        if btn_text.strip() or btn_role == "button" or btn_tabindex == "0":
                            log_info(f"[UPLOAD] Element {i+1}: '{btn_text.strip()}' (role: '{btn_role}', aria: '{btn_aria}', tabindex: '{btn_tabindex}')")
                    except Exception as debug_error:
                        log_warning(f"[UPLOAD] Error debugging element {i+1}: {str(debug_error)}")
                        continue
            except Exception as e:
                log_warning(f"[UPLOAD] Could not debug buttons: {str(e)}")
            
            return False
            
    except Exception as e:
        log_error(f"[UPLOAD] [FAIL] Error clicking next button for step {step_number}: {str(e)}")
        return False

def simulate_human_rest_behavior(page, duration):
    """Simulate human rest behavior between actions"""
    try:
        log_info(f"[HUMAN] Simulating rest behavior for {duration:.1f}s")
        
        # Scroll around randomly
        for _ in range(random.randint(1, 3)):
            scroll_amount = random.randint(-200, 200)
            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            time.sleep(random.uniform(1, 2))
        
        # Random mouse movements
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.5, 1.5))
        
        # Wait for remaining time
        remaining = duration - 6  # Approximate time spent on actions above
        if remaining > 0:
            time.sleep(remaining)
            
    except Exception as e:
        log_warning(f"[HUMAN] Rest behavior simulation failed: {str(e)}")
        time.sleep(duration)  # Fallback to simple sleep

def simulate_normal_browsing_behavior(page):
    """Simulate normal browsing behavior before closing"""
    try:
        log_info("[HUMAN] Simulating normal browsing behavior")
        
        # Go to home page
        home_link = page.query_selector('svg[aria-label*="Home"]') or page.query_selector('a[href="/"]')
        if home_link:
            home_link.click()
            time.sleep(random.uniform(2, 4))
        
        # Scroll through feed
        for _ in range(random.randint(3, 6)):
            scroll_amount = random.randint(200, 400)
            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            time.sleep(random.uniform(1, 3))
        
        # Random interactions
        for _ in range(random.randint(1, 3)):
            # Try to hover over posts
            posts = page.query_selector_all('article')
            if posts:
                random_post = random.choice(posts[:5])
                random_post.hover()
                time.sleep(random.uniform(0.5, 1.5))
        
        log_info("[HUMAN] Completed normal browsing simulation")
        
    except Exception as e:
        log_warning(f"[HUMAN] Browsing behavior simulation failed: {str(e)}")
        time.sleep(random.uniform(5, 10))  # Fallback delay

def detect_and_fill_email_field(page, email_login):
    """Detect email verification page and auto-fill email field with improved logic"""
    if not email_login:
        log_warning("📧 [EMAIL_FIELD] No email login provided")
        return False
        
    try:
        log_info(f"📧 [EMAIL_FIELD] Starting email field detection for: {email_login}")
        
        # Get page content for analysis
        try:
            page_text = page.inner_text('body') or ""
            page_html = page.content() or ""
        except Exception:
            page_text = ""
            page_html = ""
        
        log_info(f"📧 [EMAIL_FIELD] Page content length: {len(page_text)} chars")
        
        # Check if this is email verification page using improved logic
        verification_type = determine_verification_type(page)
        log_info(f"📧 [EMAIL_FIELD] Verification type detected: {verification_type}")
        
        if verification_type not in ["email_field", "email_code"]:
            log_info(f"📧 [EMAIL_FIELD] Page is not email verification type: {verification_type}")
            return False
        
        # Enhanced email field selectors - UPDATED
        email_field_selectors = [
            # Current Instagram selectors
            'input[name="email"]',
            'input[name="emailOrPhone"]',
            
            # Type-based selectors
            'input[type="email"]',
            'input[autocomplete="email"]',
            'input[inputmode="email"]',
            
            # Aria-label selectors (excluding code fields)
            'input[aria-label*="email" i]:not([aria-label*="code" i]):not([aria-label*="код" i]):not([aria-label*="verification" i])',
            'input[aria-label*="Email" i]:not([aria-label*="code" i]):not([aria-label*="код" i]):not([aria-label*="verification" i])',
            'input[aria-label*="почт" i]:not([aria-label*="код" i]):not([aria-label*="verification" i])',
            'input[aria-label*="Почт" i]:not([aria-label*="код" i]):not([aria-label*="verification" i])',
            'input[aria-label*="электронная почта" i]:not([aria-label*="код" i])',
            'input[aria-label*="адрес" i]:not([aria-label*="код" i])',
            
            # Placeholder selectors (excluding code fields)
            'input[placeholder*="email" i]:not([placeholder*="code" i]):not([placeholder*="код" i]):not([placeholder*="verification" i])',
            'input[placeholder*="Email" i]:not([placeholder*="code" i]):not([placeholder*="код" i]):not([placeholder*="verification" i])',
            'input[placeholder*="почт" i]:not([placeholder*="код" i]):not([placeholder*="verification" i])',
            'input[placeholder*="Почт" i]:not([placeholder*="код" i]):not([placeholder*="verification" i])',
            'input[placeholder*="электронная почта" i]:not([placeholder*="код" i])',
            'input[placeholder*="укажите email" i]',
            'input[placeholder*="введите email" i]',
            
            # ID selectors (excluding code and verification)
            'input[id*="email"]:not([id*="code"]):not([id*="verification"]):not([id*="confirm"])',
            'input[id*="Email"]:not([id*="code"]):not([id*="verification"]):not([id*="confirm"])',
        ]
        
        email_field = None
        used_selector = None
        
        # Try to find email field
        for selector in email_field_selectors:
            try:
                element = page.query_selector(selector)
                if element and element.is_visible() and not element.is_disabled():
                    # Additional validation - check if this is really an email field
                    field_name = element.get_attribute('name') or ""
                    field_type = element.get_attribute('type') or ""
                    field_aria = element.get_attribute('aria-label') or ""
                    field_placeholder = element.get_attribute('placeholder') or ""
                    
                    log_info(f"📧 [EMAIL_FIELD] Found potential field: name='{field_name}', type='{field_type}'")
                    log_info(f"📧 [EMAIL_FIELD] Field attributes: aria-label='{field_aria}', placeholder='{field_placeholder}'")
                    
                    # Validate it's not a code field
                    is_code_field = any(keyword in (field_name + field_aria + field_placeholder).lower() 
                                      for keyword in ['code', 'код', 'verification', 'верификация', 'confirm'])
                    
                    if not is_code_field:
                        email_field = element
                        used_selector = selector
                        log_info(f"📧 [EMAIL_FIELD] [OK] Selected email field: {selector}")
                        break
                    else:
                        log_info(f"📧 [EMAIL_FIELD] Skipped code/verification field: {selector}")
                        
            except Exception as e:
                log_warning(f"📧 [EMAIL_FIELD] Error checking selector {selector}: {str(e)}")
                continue
        
        if not email_field:
            log_warning("📧 [EMAIL_FIELD] [FAIL] No suitable email field found")
            return False
        
        # Fill the email field
        log_info(f"📧 [EMAIL_FIELD] Filling email field with: {email_login}")
        
        try:
            # Clear field first
            email_field.click()
            time.sleep(random.uniform(0.3, 0.7))
            email_field.fill('')
            time.sleep(random.uniform(0.2, 0.5))
            
            # Type email with human-like behavior
            for char in email_login:
                email_field.type(char)
                time.sleep(random.uniform(0.05, 0.12))
            
            log_info("📧 [EMAIL_FIELD] [OK] Email field filled successfully")
            
            # Try to submit if there's a submit button
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("Continue")',
                'button:has-text("Продолжить")',
                'button:has-text("Submit")',
                'button:has-text("Отправить")',
                'div[role="button"]:has-text("Continue")',
                'div[role="button"]:has-text("Продолжить")',
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = page.query_selector(selector)
                    if submit_button and submit_button.is_visible() and not submit_button.is_disabled():
                        log_info(f"📧 [EMAIL_FIELD] Found submit button: {selector}")
                        break
                except:
                    continue
            
            if submit_button:
                time.sleep(random.uniform(1.0, 2.0))
                submit_button.click()
                log_info("📧 [EMAIL_FIELD] [OK] Submit button clicked")
                time.sleep(random.uniform(2, 4))
            else:
                log_info("📧 [EMAIL_FIELD] No submit button found, trying Enter key")
                email_field.press("Enter")
                time.sleep(random.uniform(2, 4))
            
            return True
            
        except Exception as e:
            log_error(f"📧 [EMAIL_FIELD] [FAIL] Error filling email field: {str(e)}")
            return False
            
    except Exception as e:
        log_error(f"📧 [EMAIL_FIELD] [FAIL] Error in email field detection: {str(e)}")
        return False

def find_submit_button(page):
    """Find submit button using stable selectors"""
    try:
        log_info("[SEARCH] [SUBMIT_BTN] Looking for submit button...")
        
        button = _find_element(page, InstagramSelectors.SUBMIT_BUTTONS)
        if button:
            button_text = button.text_content() or 'no-text'
            button_type = button.get_attribute('type') or 'unknown'
            log_info(f"[OK] [SUBMIT_BTN] Found submit button: '{button_text.strip()}' (type: {button_type})")
            return button
        
        log_warning("[FAIL] [SUBMIT_BTN] No submit button found")
        return None
        
    except Exception as e:
        log_error(f"[FAIL] [SUBMIT_BTN] Error in submit button detection: {str(e)}")
        return None

def find_verification_code_input(page):
    """Find verification code input field"""
    try:
        log_info("[SEARCH] [CODE_INPUT] Looking for verification code input field...")
        time.sleep(random.uniform(1, 2))
        
        try:
            page_text = page.inner_text('body') or ""
        except Exception:
            page_text = ""
            
        is_verification_page = any(keyword in page_text.lower() for keyword in InstagramTexts.VERIFICATION_PAGE_KEYWORDS)
        
        log_info(f"[SEARCH] [CODE_INPUT] Verification page detected: {is_verification_page}")
        
        if is_verification_page:
            input_field = _find_element(page, InstagramSelectors.VERIFICATION_CODE_FIELDS)
            if input_field:
                field_name = input_field.get_attribute('name') or 'unknown'
                field_type = input_field.get_attribute('type') or 'unknown'
                log_info(f"[OK] [CODE_INPUT] Found input field: name={field_name}, type={field_type}")
                return input_field
        else:
            input_field = _find_element(page, InstagramSelectors.VERIFICATION_CODE_FIELDS_RESTRICTIVE)
            if input_field:
                return input_field
        
        log_warning("[FAIL] [CODE_INPUT] No verification code input found")
        return None
        
    except Exception as e:
        log_error(f"[FAIL] [CODE_INPUT] Error in code input detection: {str(e)}")
        return None

def handle_save_login_info_dialog(page):
    """Handle Instagram's 'Save login info' dialog"""
    try:
        log_info("[SAVE_LOGIN] Checking for 'Save login info' dialog...")
        time.sleep(random.uniform(2, 4))
        
        # Check page text for save login dialog
        try:
            page_text = page.inner_text('body') or ""
        except Exception:
            page_text = ""
        
        is_save_login_dialog = any(keyword in page_text.lower() for keyword in InstagramTexts.SAVE_LOGIN_KEYWORDS)
        log_info(f"[SAVE_LOGIN] Save login dialog detected: {is_save_login_dialog}")
        
        if is_save_login_dialog:
            log_info("[SAVE_LOGIN] 💾 Save login info dialog found")
            
            # Look for "Save" button
            save_button = _find_element(page, InstagramSelectors.SAVE_LOGIN_BUTTONS)
            
            if save_button and save_button.is_visible():
                button_text = save_button.text_content() or ""
                if any(keyword in button_text.lower() for keyword in ['сохранить', 'save']):
                    log_info(f"[SAVE_LOGIN] [OK] Found save button: '{button_text.strip()}'")
                    
                    try:
                        save_button.hover()
                        time.sleep(random.uniform(0.5, 1.0))
                        save_button.click()
                        time.sleep(random.uniform(2, 4))
                        log_info("[SAVE_LOGIN] [OK] Successfully clicked save login info button")
                        return True
                    except Exception as e:
                        log_error(f"[SAVE_LOGIN] [FAIL] Error clicking save button: {str(e)}")
            
            # If no save button, look for "Not now" button
            log_warning("[SAVE_LOGIN] [WARN] Could not find save button, looking for 'Not now' button...")
            not_now_button = _find_element(page, InstagramSelectors.NOT_NOW_BUTTONS)
            
            if not_now_button and not_now_button.is_visible():
                log_info(f"[SAVE_LOGIN] Found 'Not now' button, dismissing dialog...")
                not_now_button.hover()
                time.sleep(random.uniform(0.5, 1.0))
                not_now_button.click()
                time.sleep(random.uniform(2, 4))
                log_info("[SAVE_LOGIN] [OK] Dismissed save login dialog with 'Not now'")
                return True
            
            log_warning("[SAVE_LOGIN] [WARN] Could not find any button to handle save login dialog")
            return False
        else:
            log_info("[SAVE_LOGIN] No save login info dialog found")
            return True
            
    except Exception as e:
        log_error(f"[SAVE_LOGIN] [FAIL] Error handling save login dialog: {str(e)}")
        return False

def check_video_posted_successfully(page, video_file_path):
    """Check if video was posted successfully - STRICT verification only"""
    try:
        log_info("[UPLOAD] Checking if video was posted successfully...")
        time.sleep(random.uniform(5, 8))
        
        # Check for explicit success indicators ONLY
        success_element = _find_element(page, InstagramSelectors.SUCCESS_INDICATORS)
        if success_element:
            element_text = success_element.text_content() or ""
            log_success(f"[UPLOAD] [OK] SUCCESS CONFIRMED: Found explicit success indicator: '{element_text.strip()}'")
            log_success(f"[UPLOAD] [OK] Video {os.path.basename(video_file_path)} successfully posted")
            return True
        
        # Additional wait and second check for success indicators
        log_info("[UPLOAD] No immediate success indicators found, waiting and checking again...")
        time.sleep(random.uniform(3, 5))
        
        success_element = _find_element(page, InstagramSelectors.SUCCESS_INDICATORS)
        if success_element:
            element_text = success_element.text_content() or ""
            log_success(f"[UPLOAD] [OK] SUCCESS CONFIRMED (delayed): Found explicit success indicator: '{element_text.strip()}'")
            log_success(f"[UPLOAD] [OK] Video {os.path.basename(video_file_path)} successfully posted")
            return True
        
        # Check for explicit error messages
        error_element = _find_element(page, InstagramSelectors.ERROR_INDICATORS)
        if error_element:
            error_text = error_element.text_content() or ""
            log_error(f"[UPLOAD] [FAIL] ERROR DETECTED: '{error_text.strip()}'")
            log_error(f"[UPLOAD] [FAIL] Video {os.path.basename(video_file_path)} failed to post")
            return False
        
        # Check if still on upload page (indicates failure)
        upload_element = _find_element(page, InstagramSelectors.UPLOAD_PAGE_INDICATORS)
        if upload_element:
            log_error(f"[UPLOAD] [FAIL] UPLOAD FAILED: Still on upload page - video {os.path.basename(video_file_path)} was NOT posted")
            return False
        
        # STRICT POLICY: If no explicit success indicators found, consider it a failure
        # This ensures COMPLETED status is only set when we can CONFIRM successful upload
        log_error(f"[UPLOAD] [FAIL] UPLOAD FAILED: No explicit success indicators found - cannot confirm video {os.path.basename(video_file_path)} was posted")
        log_info(f"[UPLOAD] [SEARCH] Current page URL: {page.url}")
        
        return False
                
    except Exception as e:
        log_error(f"[UPLOAD] Error checking if video was posted: {str(e)}")
        return False

def handle_success_dialog_and_close(page, video_file_path):
    """Handle success dialog after video posting and close it naturally - STRICT verification only"""
    try:
        log_info("[SUCCESS] Looking for success confirmation dialog...")
        time.sleep(random.uniform(3, 5))
        
        # Look for explicit success dialog elements
        success_dialog_selectors = [
            'div[role="dialog"]:has-text("Ваша публикация опубликована")',
            'div[role="dialog"]:has-text("Your post has been shared")',
            'div[role="dialog"]:has-text("Опубликовано")',
            'div[role="dialog"]:has-text("Posted")',
            'div[role="dialog"]:has-text("Shared")',
            '[data-testid="success-dialog"]',
            'div:has-text("Ваша публикация опубликована")',
            'div:has-text("Your post has been shared")',
        ]
        
        success_dialog = None
        for selector in success_dialog_selectors:
            try:
                success_dialog = page.query_selector(selector)
                if success_dialog and success_dialog.is_visible():
                    dialog_text = success_dialog.text_content() or ""
                    log_success(f"[SUCCESS] [OK] SUCCESS CONFIRMED: Found success dialog: '{dialog_text.strip()}'")
                    break
            except:
                continue
        
        # If we found a success dialog, close it naturally
        if success_dialog:
            # Look for close button in dialog
            close_button_selectors = [
                'button[aria-label*="Закрыть" i]',
                'button[aria-label*="Close" i]',
                'svg[aria-label*="Закрыть" i]',
                'svg[aria-label*="Close" i]',
                'button:has-text("OK")',
                'button:has-text("Готово")',
                'button:has-text("Done")',
            ]
            
            close_button = None
            for selector in close_button_selectors:
                try:
                    close_button = success_dialog.query_selector(selector)
                    if not close_button:
                        close_button = page.query_selector(selector)
                    if close_button and close_button.is_visible():
                        break
                except:
                    continue
            
            if close_button:
                log_info("[SUCCESS] Closing success dialog naturally...")
                _human_click_with_timeout(page, close_button, "SUCCESS_CLOSE")
                time.sleep(random.uniform(2, 3))
            else:
                # Try clicking outside the dialog
                log_info("[SUCCESS] No close button found, clicking outside dialog...")
                page.click('body', position={'x': 50, 'y': 50})
                time.sleep(random.uniform(2, 3))
            
            log_success(f"[SUCCESS] [OK] Video {os.path.basename(video_file_path)} posted successfully!")
            return True
        
        # If no success dialog found, check for other success indicators
        success_element = _find_element(page, InstagramSelectors.SUCCESS_INDICATORS)
        if success_element:
            element_text = success_element.text_content() or ""
            log_success(f"[SUCCESS] [OK] SUCCESS CONFIRMED: Found success indicator: '{element_text.strip()}'")
            log_success(f"[SUCCESS] [OK] Video {os.path.basename(video_file_path)} posted successfully!")
            return True
        
        # STRICT POLICY: If no explicit success indicators found, consider it a failure
        log_error(f"[SUCCESS] [FAIL] UPLOAD FAILED: No success dialog or indicators found - cannot confirm video {os.path.basename(video_file_path)} was posted")
        
        # Check if back to main interface (but this alone is not enough for success confirmation)
        main_element = _find_element(page, InstagramSelectors.MAIN_INTERFACE_INDICATORS)
        if main_element:
            log_info("[SUCCESS] ℹ️ Back to main interface, but no explicit success confirmation found")
        
        # Check if still on upload page (indicates failure)
        upload_element = _find_element(page, InstagramSelectors.UPLOAD_PAGE_INDICATORS)
        if upload_element:
            log_error(f"[SUCCESS] [FAIL] UPLOAD FAILED: Still on upload page - video {os.path.basename(video_file_path)} was NOT posted")
            
        return False
            
    except Exception as e:
        log_error(f"[SUCCESS] [FAIL] Error handling success dialog: {str(e)}")
        return False

def cleanup_hanging_browser_processes():
    """Clean up hanging browser processes - Optimized version"""
    BrowserManager.cleanup_hanging_processes()

def safely_close_all_windows(page, dolphin_browser, dolphin_profile_id=None):
    """Safely close all browser windows and processes - Optimized version"""
    return BrowserManager.safely_close_browser(page, dolphin_browser, dolphin_profile_id)

def simulate_extended_human_rest_behavior(page, total_duration):
    """Simulate extended human rest behavior with multiple activities during long breaks"""
    try:
        log_info(f"[EXTENDED_REST] 🛋️ Starting extended rest period: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
        
        # Initialize human behavior if not already done
        human_behavior = get_human_behavior()
        if not human_behavior:
            init_human_behavior(page)
            human_behavior = get_human_behavior()
        
        # Break the total duration into smaller activity chunks
        remaining_time = total_duration
        activity_count = 0
        
        while remaining_time > 30:  # Continue until less than 30 seconds remain
            activity_count += 1
            
            # Choose random activity duration (30 seconds to 2 minutes)
            activity_duration = min(random.uniform(30, 120), remaining_time)
            remaining_time -= activity_duration
            
            # Choose random activity type
            activity_types = [
                'browse_feed', 'check_profile', 'scroll_explore', 'check_notifications',
                'view_stories', 'search_content', 'idle_pause', 'check_messages'
            ]
            
            activity = random.choice(activity_types)
            log_info(f"[EXTENDED_REST] [TARGET] Activity {activity_count}: {activity} for {activity_duration:.1f}s")
            
            # Simplified activity implementation
            if activity == 'idle_pause':
                log_info(f"[EXTENDED_REST] 😴 Idle pause for {activity_duration:.1f}s...")
                time.sleep(activity_duration)
            else:
                # For other activities, just simulate with basic scrolling
                scroll_count = int(activity_duration / 10)
                for _ in range(max(1, scroll_count)):
                    scroll_amount = random.randint(200, 500)
                    page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                    time.sleep(10)
        
        # Handle any remaining time with a final idle period
        if remaining_time > 0:
            log_info(f"[EXTENDED_REST] 😌 Final rest period: {remaining_time:.1f}s...")
            time.sleep(remaining_time)
        
        log_info(f"[EXTENDED_REST] [OK] Extended rest period completed after {activity_count} activities")
        
    except Exception as e:
        log_warning(f"[EXTENDED_REST] Error during extended rest: {str(e)}")
        # Fallback to simple sleep
        time.sleep(total_duration)

def run_bulk_upload_task(task_id):
    """Enhanced bulk upload task with comprehensive monitoring and error recovery"""
    try:
        # Set current task ID for global access
        set_current_task_id(task_id)
        
        # Get task object
        task = BulkUploadTask.objects.get(id=task_id)
        
        # Initialize web logger for this task
        web_logger = init_web_logger(task_id)
        install_web_log_handler()
        
        # Task initialization
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_task_status(task, TaskStatus.RUNNING, f"[{timestamp}] [START] Starting enhanced bulk upload task '{task.name}'\\n")
        
        log_info(f"[CLIPBOARD] [TASK_INFO] Task '{task.name}' - Processing {task.accounts.count()} accounts", LogCategories.TASK_INFO)
        
        # Get all videos and titles for the task
        all_videos = get_all_task_videos(task)  # [OK] ВСЕ видео - будут переданы каждому аккаунту
        all_titles = get_all_task_titles(task)
        
        log_info(f"[CAMERA] [TASK_INFO] Found {len(all_videos)} videos and {len(all_titles)} titles", LogCategories.TASK_INFO)
        
        if not all_videos:
            error_msg = "No videos found for this task"
            log_error(error_msg, LogCategories.TASK_INFO)
            update_task_status(task, TaskStatus.FAILED, f"[{timestamp}] [FAIL] {error_msg}\n")
            return False
        
        # Enhanced account processing with health monitoring
        processed_accounts = 0
        successful_accounts = 0
        failed_accounts = 0
        verification_required_accounts = 0
        account_health_issues = []
        
        # Get accounts sorted by status (ACTIVE accounts first)
        account_tasks = task.accounts.all().order_by('account__status')
        
        for i, account_task in enumerate(account_tasks, 1):
            account = account_task.account
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            log_info(f"[RETRY] [ACCOUNT_PROCESS] Processing account {i}/{len(account_tasks)}: {account.username}", LogCategories.TASK_INFO)
            
            # Pre-flight account health check
            if account.status != 'ACTIVE':
                log_message = f"[{timestamp}] [WARN] Account {account.username} skipped - Status: {account.status} (Only ACTIVE accounts allowed for bulk upload)\n"
                log_warning(f"Account {account.username} has non-ACTIVE status: {account.status}", LogCategories.VERIFICATION)
                update_task_log(task, log_message)
                
                if account.status in ['PHONE_VERIFICATION_REQUIRED', 'HUMAN_VERIFICATION_REQUIRED']:
                    verification_required_accounts += 1
                    account_health_issues.append({
                        'username': account.username,
                        'issue': account.status,
                        'severity': 'HIGH'
                    })
                else:
                    failed_accounts += 1
                
                continue
            
            # # Human-like delay between accounts - УЛУЧШЕННАЯ ВЕРСИЯ
            # if i > 1:  # Skip delay for first account
            #     # Получаем улучшенную задержку с учетом всех факторов
            #     account_delay = get_enhanced_account_delay(i, len(account_tasks), processed_accounts, failed_accounts)
            #     log_info(f"⏰ [ENHANCED_DELAY] Waiting {account_delay:.1f} seconds before processing next account (factors applied)", LogCategories.HUMAN)
            #     update_task_log(task, f"[{timestamp}] ⏰ Enhanced delay: {account_delay:.1f}s with adaptive factors\n")
            #     time.sleep(account_delay)
            
            # Process account with enhanced error handling
            try:
                account_result = process_account_videos(account_task, task, all_videos, all_titles, task_id)
                processed_accounts += 1
                
                if account_result:
                    successful_accounts += 1
                    log_success(f"[OK] [ACCOUNT_SUCCESS] Account {account.username} processed successfully", LogCategories.TASK_INFO)
                else:
                    failed_accounts += 1
                    log_error(f"[FAIL] [ACCOUNT_FAILED] Account {account.username} processing failed", LogCategories.TASK_INFO)
                    
                    # Check if it's a verification issue
                    if account_task.status in ['PHONE_VERIFICATION_REQUIRED', 'HUMAN_VERIFICATION_REQUIRED']:
                        verification_required_accounts += 1
                        account_health_issues.append({
                            'username': account.username,
                            'issue': account_task.status,
                            'severity': 'HIGH'
                        })
            
            except Exception as account_error:
                processed_accounts += 1
                failed_accounts += 1
                error_msg = str(account_error)
                
                log_error(f"[FAIL] [ACCOUNT_ERROR] Exception processing account {account.username}: {error_msg}", LogCategories.TASK_INFO)
                
                # Categorize the error
                if "PHONE_VERIFICATION_REQUIRED" in error_msg:
                    verification_required_accounts += 1
                    account_health_issues.append({
                        'username': account.username,
                        'issue': 'PHONE_VERIFICATION_REQUIRED',
                        'severity': 'HIGH'
                    })
                elif "HUMAN_VERIFICATION_REQUIRED" in error_msg:
                    verification_required_accounts += 1
                    account_health_issues.append({
                        'username': account.username,
                        'issue': 'HUMAN_VERIFICATION_REQUIRED',
                        'severity': 'HIGH'
                    })
                else:
                    account_health_issues.append({
                        'username': account.username,
                        'issue': f"Error: {error_msg[:100]}",
                        'severity': 'MEDIUM'
                    })
                
                # Update account task status
                update_account_task(account_task, TaskStatus.FAILED, error_msg)
                update_task_log(task, f"[{timestamp}] [FAIL] Account {account.username} failed: {error_msg}\n")
        
        # Final task summary and status determination
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Generate comprehensive summary
        summary = {
            'total_accounts': len(account_tasks),
            'processed_accounts': processed_accounts,
            'successful_accounts': successful_accounts,
            'failed_accounts': failed_accounts,
            'verification_required_accounts': verification_required_accounts,
            'health_issues': account_health_issues
        }
        
        log_info(f"📊 [TASK_SUMMARY] Task completion summary:", LogCategories.TASK_INFO)
        log_info(f"📊 [TASK_SUMMARY] Total accounts: {summary['total_accounts']}", LogCategories.TASK_INFO)
        log_info(f"📊 [TASK_SUMMARY] Successful: {summary['successful_accounts']}", LogCategories.TASK_INFO)
        log_info(f"📊 [TASK_SUMMARY] Failed: {summary['failed_accounts']}", LogCategories.TASK_INFO)
        log_info(f"📊 [TASK_SUMMARY] Verification required: {summary['verification_required_accounts']}", LogCategories.TASK_INFO)
        
        # Determine final task status based on results
        if successful_accounts == 0:
            final_status = TaskStatus.FAILED
            status_emoji = "[FAIL]"
            status_message = "All accounts failed"
        elif successful_accounts == len(account_tasks):
            final_status = TaskStatus.COMPLETED
            status_emoji = "[OK]"
            status_message = "All accounts completed successfully"
        else:
            final_status = TaskStatus.PARTIALLY_COMPLETED
            status_emoji = "[WARN]"
            status_message = f"Partial completion: {successful_accounts}/{len(account_tasks)} accounts succeeded"
        
        # Generate health report for critical issues
        if account_health_issues:
            log_warning(f"🏥 [HEALTH_REPORT] Detected {len(account_health_issues)} account health issues:", LogCategories.VERIFICATION)
            for issue in account_health_issues[:5]:  # Show first 5 issues
                log_warning(f"🏥 [HEALTH_REPORT] {issue['username']}: {issue['issue']} (Severity: {issue['severity']})", LogCategories.VERIFICATION)
        
        # Generate final log message first
        final_log_message = (
            f"[{timestamp}] {status_emoji} Task '{task.name}' completed\n"
            f"[{timestamp}] 📊 Summary: {successful_accounts} successful, {failed_accounts} failed, "
            f"{verification_required_accounts} need verification\n"
        )
        
        if account_health_issues:
            final_log_message += f"[{timestamp}] 🏥 Health issues detected in {len(account_health_issues)} accounts\n"
        
        # Update task with final status and log message
        update_task_status(task, final_status, final_log_message)
        
        log_success(f"[PARTY] [TASK_COMPLETE] Task {task_id} completed with status: {final_status}", LogCategories.TASK_INFO)
        
        # Generate web logger summary
        if web_logger:
            logger_summary = web_logger.get_summary()
            log_info(f"📈 [LOG_SUMMARY] Generated {logger_summary['total']} log entries, {logger_summary['critical_count']} critical events", LogCategories.TASK_INFO)
        
        # Cleanup original video files from media directory
        try:
            deleted_files = cleanup_original_video_files_sync(task)
            if deleted_files > 0:
                log_info(f"[DELETE] [CLEANUP] Cleaned up {deleted_files} original video files from media directory", LogCategories.CLEANUP)
        except Exception as cleanup_error:
            log_warning(f"[WARN] [CLEANUP] Failed to cleanup original video files: {str(cleanup_error)}", LogCategories.CLEANUP)
        
        return final_status in [TaskStatus.COMPLETED, TaskStatus.PARTIALLY_COMPLETED]
        
    except Exception as e:
        error_message = str(e)
        error_trace = traceback.format_exc()
        
        log_error(f"[EXPLODE] [TASK_CRITICAL] Critical error in bulk upload task {task_id}: {error_message}", LogCategories.TASK_INFO)
        log_error(f"[EXPLODE] [TASK_CRITICAL] Stack trace: {error_trace}", LogCategories.TASK_INFO)
        
        if task:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_task_status(task, TaskStatus.FAILED, f"[{timestamp}] [EXPLODE] Critical task error: {error_message}\n")
        
        return False
    
    finally:
        # Cleanup any hanging processes
        try:
            cleanup_hanging_browser_processes()
            log_info("[CLEAN] [CLEANUP] Browser cleanup completed", LogCategories.CLEANUP)
        except Exception as cleanup_error:
            log_warning(f"[WARN] [CLEANUP] Browser cleanup had issues: {str(cleanup_error)}", LogCategories.CLEANUP)
        
        # Also cleanup original video files if task exists
        if 'task' in locals() and task:
            try:
                deleted_files = cleanup_original_video_files_sync(task)
                if deleted_files > 0:
                    log_info(f"[DELETE] [CLEANUP] Finally cleanup: removed {deleted_files} original video files", LogCategories.CLEANUP)
            except Exception as cleanup_error:
                log_warning(f"[WARN] [CLEANUP] Finally cleanup failed for original video files: {str(cleanup_error)}", LogCategories.CLEANUP)

def process_account_videos(account_task, task, all_videos, all_titles, task_id):
    """Process videos for a single account"""
    # [OK] ВАЖНО: Каждый аккаунт получает ВСЕ видео задачи, а не только назначенные ему
    # Это означает, что одно видео будет загружено на все аккаунты
    videos_for_account = list(all_videos)
    random.shuffle(videos_for_account)
    
    titles_for_account = list(all_titles) if all_titles else []
    if titles_for_account:
        random.shuffle(titles_for_account)
    
    # Assign random titles to videos
    for i, video in enumerate(videos_for_account):
        if titles_for_account:
            title_index = i % len(titles_for_account)
            video.title_data = titles_for_account[title_index]
        else:
            video.title_data = None
    
    # Get account data
    account = get_account_from_task(account_task)
    proxy = get_account_proxy(account_task, account)
    account_details = get_account_details(account, proxy)
    
    # Prepare video files
    temp_files, video_files_to_upload = prepare_video_files(videos_for_account, account_task)
    
    if not video_files_to_upload:
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        log_error("No valid video files to upload")
        update_account_task(
            account_task,
            status=TaskStatus.FAILED,
            completed_at=timezone.now(),
            log_message=f"[{timestamp}] [FAIL] No valid video files to upload\n"
        )
        return 'failed', 0, 1
    
    # Run browser operation
    result_queue = queue.Queue()
    browser_thread = threading.Thread(
        target=run_dolphin_browser,
        args=(account_details, videos_for_account, video_files_to_upload, result_queue, task_id, account_task.id)
    )
    browser_thread.daemon = True
    browser_thread.start()
    
    # Wait for completion
    browser_thread.join(timeout=TimeConstants.BROWSER_TIMEOUT)
    
    # Process result
    if not result_queue.empty():
        result = result_queue.get()
        result_type, completed, failed = process_browser_result(result, account_task, task)
    else:
        handle_emergency_cleanup(account_task)
        result_type, completed, failed = 'failed', 0, 1
    
    # Clean up temporary files
    cleanup_temp_files(temp_files)
    
    return result_type, completed, failed

def prepare_video_files(videos_for_account, account_task):
    """Prepare video files for upload with uniquification"""
    temp_files = []
    video_files_to_upload = []
    account_username = account_task.account.username
    
    log_info(f"[VIDEO] Starting video uniquification for account {account_username}")
    
    for i, video in enumerate(videos_for_account):
        video_filename = os.path.basename(video.video_file.name)
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        log_info(f"Preparing and uniquifying video: {video_filename}")
        update_account_task(
            account_task,
            log_message=f"[{timestamp}] [CLIPBOARD] Preparing and uniquifying video: {video_filename}\n"
        )
        
        try:
            # Сначала создаем временный файл из оригинала
            with NamedTemporaryFile(delete=False, suffix=f"_original_{video_filename}") as tmp:
                log_debug(f"Creating temporary file: {tmp.name}")
                for chunk in video.video_file.chunks():
                    tmp.write(chunk)
                temp_files.append(tmp.name)
                
                timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                log_info(f"Created temporary file: {tmp.name}")
                update_account_task(
                    account_task,
                    log_message=f"[{timestamp}] [OK] Created temporary file\n"
                )
                
                # Теперь уникализируем видео для этого аккаунта
                try:
                    # Импортируем модуль уникализации
                    from .async_video_uniquifier import AsyncVideoUniquifier, UniqueVideoConfig
                    
                    # Создаем уникальную конфигурацию для аккаунта
                    unique_config = UniqueVideoConfig.create_random_config(account_username)
                    uniquifier = AsyncVideoUniquifier(unique_config)
                    
                    # Создаем уникальное видео синхронно
                    import datetime
                    from pathlib import Path
                    import tempfile
                    
                    input_path_obj = Path(tmp.name)
                    timestamp_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_filename = f"{input_path_obj.stem}_{account_username}_{timestamp_str}_v{i+1}.mp4"
                    
                    temp_dir = tempfile.gettempdir()
                    unique_video_path = os.path.join(temp_dir, output_filename)
                    
                    # Обрабатываем видео синхронно
                    success = uniquifier._process_video_sync(tmp.name, unique_video_path, unique_config, account_username)
                    
                    if success and os.path.exists(unique_video_path):
                        video_files_to_upload.append(unique_video_path)
                        temp_files.append(unique_video_path)
                        
                        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                        log_info(f"[OK] Created unique video for {account_username}: {os.path.basename(unique_video_path)}")
                        update_account_task(
                            account_task,
                            log_message=f"[{timestamp}] [OK] Created unique video: {os.path.basename(unique_video_path)}\n"
                        )
                    else:
                        # Если уникализация не удалась, используем оригинальный файл
                        log_warning(f"[WARN] Video uniquification failed, using original file")
                        video_files_to_upload.append(tmp.name)
                        
                        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                        update_account_task(
                            account_task,
                            log_message=f"[{timestamp}] [WARN] Uniquification failed, using original\n"
                        )
                        
                except Exception as uniquify_error:
                    # Если уникализация не удалась, используем оригинальный файл
                    log_warning(f"[WARN] Video uniquification failed: {str(uniquify_error)}, using original file")
                    video_files_to_upload.append(tmp.name)
                    
                    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                    update_account_task(
                        account_task,
                        log_message=f"[{timestamp}] [WARN] Uniquification error: {str(uniquify_error)}\n"
                    )
                
        except Exception as e:
            log_error(f"[FAIL] Error creating temporary file for {video_filename}: {str(e)}")
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            update_account_task(
                account_task,
                log_message=f"[{timestamp}] [FAIL] Error creating temporary file: {str(e)}\n"
            )
    
    log_info(f"[TARGET] Prepared {len(video_files_to_upload)} unique videos for account {account_username}")
    return temp_files, video_files_to_upload

def cleanup_temp_files(temp_files):
    """Clean up temporary files"""
    log_info(f"Cleaning up {len(temp_files)} temporary files")
    for file_path in temp_files:
        if os.path.exists(file_path):
            try:
                log_debug(f"Deleting temp file: {file_path}")
                os.unlink(file_path)
            except Exception as e:
                log_error(f"Error deleting temporary file {file_path}: {str(e)}")

def run_dolphin_browser(account_details, videos, video_files_to_upload, result_queue, task_id, account_task_id):
    """Enhanced Dolphin browser runner with comprehensive error handling and monitoring"""
    dolphin = None
    dolphin_browser = None
    page = None
    dolphin_profile_id = None
    
    try:
        init_web_logger(task_id, account_task_id)
        install_web_log_handler()
        
        username = account_details['username']
        log_info(f"🐬 [DOLPHIN_START] Starting Dolphin Anty browser for account: {username}", LogCategories.DOLPHIN)
        
        # Pre-flight checks
        if not video_files_to_upload:
            error_msg = "No video files provided for upload"
            log_error(f"[FAIL] [DOLPHIN_ERROR] {error_msg}", LogCategories.DOLPHIN)
            result_queue.put(("ERROR", error_msg))
            return
        
        # Initialize Dolphin with enhanced error handling
        dolphin_token = os.environ.get("DOLPHIN_API_TOKEN")
        if not dolphin_token:
            error_msg = "No Dolphin API token found in environment variables"
            log_error(f"[FAIL] [DOLPHIN_ERROR] {error_msg}", LogCategories.DOLPHIN)
            send_critical_notification(task_id, f"Dolphin API token missing for task {task_id}", 'ERROR')
            result_queue.put(("DOLPHIN_ERROR", error_msg))
            return
            
        from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
        from bot.src.instagram_uploader.browser_dolphin import DolphinBrowser
        
        # Get Dolphin API host from environment (critical for Docker Windows deployment)
        dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
        if not dolphin_api_host.endswith("/v1.0"):
            dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
        
        log_info(f"🐬 [DOLPHIN_CONFIG] Using Dolphin API host: {dolphin_api_host}", LogCategories.DOLPHIN)
        
        dolphin = DolphinAnty(api_key=dolphin_token, local_api_base=dolphin_api_host)
        
        # Enhanced authentication with retry logic
        log_info(f"🔐 [DOLPHIN_AUTH] Authenticating with Dolphin Anty API...", LogCategories.DOLPHIN)
        auth_attempts = 0
        max_auth_attempts = 3
        
        while auth_attempts < max_auth_attempts:
            if authenticate_dolphin(dolphin):
                log_success(f"[OK] [DOLPHIN_AUTH] Authentication successful on attempt {auth_attempts + 1}", LogCategories.DOLPHIN)
                break
            else:
                auth_attempts += 1
                if auth_attempts < max_auth_attempts:
                    log_warning(f"[WARN] [DOLPHIN_AUTH] Authentication failed, retrying... (attempt {auth_attempts}/{max_auth_attempts})", LogCategories.DOLPHIN)
                    time.sleep(random.uniform(2, 5))
                else:
                    error_msg = "Failed to authenticate with Dolphin Anty API after multiple attempts"
                    log_error(f"[FAIL] [DOLPHIN_AUTH] {error_msg}", LogCategories.DOLPHIN)
                    send_critical_notification(task_id, f"Dolphin authentication failed for account {username}", 'ERROR')
                    result_queue.put(("DOLPHIN_ERROR", error_msg))
                    return
        
        # Get profile with validation
        log_info(f"[CLIPBOARD] [DOLPHIN_PROFILE] Retrieving Dolphin profile for account: {username}", LogCategories.DOLPHIN)
        dolphin_profile_id = get_dolphin_profile_id(username)
        if not dolphin_profile_id:
            error_msg = f"No Dolphin profile found for account: {username}"
            log_error(f"[FAIL] [DOLPHIN_PROFILE] {error_msg}", LogCategories.DOLPHIN)
            send_critical_notification(task_id, f"Missing Dolphin profile for account {username}", 'ERROR')
            result_queue.put(("PROFILE_ERROR", error_msg))
            return
        
        log_info(f"🔗 [DOLPHIN_PROFILE] Found profile ID: {dolphin_profile_id}", LogCategories.DOLPHIN)
        
        # Connect to browser with enhanced error handling
        log_info(f"🌐 [DOLPHIN_BROWSER] Connecting to browser profile...", LogCategories.DOLPHIN)
        dolphin_browser = DolphinBrowser(dolphin_api_token=dolphin_token)
        
        # Browser connection with timeout and retry
        connection_attempts = 0
        max_connection_attempts = 2
        
        while connection_attempts < max_connection_attempts:
            try:
                page = dolphin_browser.connect_to_profile(dolphin_profile_id, headless=False)
                if page:
                    log_success(f"[OK] [DOLPHIN_BROWSER] Successfully connected to profile: {dolphin_profile_id}", LogCategories.DOLPHIN)
                    break
                else:
                    raise Exception("Page object is None")
            except Exception as connect_error:
                connection_attempts += 1
                if connection_attempts < max_connection_attempts:
                    log_warning(f"[WARN] [DOLPHIN_BROWSER] Connection failed, retrying... (attempt {connection_attempts}/{max_connection_attempts}): {str(connect_error)}", LogCategories.DOLPHIN)
                    time.sleep(random.uniform(3, 7))
                else:
                    error_msg = f"Failed to connect to profile {dolphin_profile_id} after {max_connection_attempts} attempts: {str(connect_error)}"
                    log_error(f"[FAIL] [DOLPHIN_BROWSER] {error_msg}", LogCategories.DOLPHIN)
                    send_critical_notification(task_id, f"Browser connection failed for account {username}", 'ERROR')
                    result_queue.put(("PROFILE_ERROR", error_msg))
                    return
        
        # Pre-operation validation
        log_info(f"[SEARCH] [INSTAGRAM_PREP] Preparing Instagram operations for {len(video_files_to_upload)} videos", LogCategories.UPLOAD)
        
        # Perform Instagram operations with comprehensive monitoring
        operation_start_time = time.time()
        operation_success = perform_instagram_operations(page, account_details, videos, video_files_to_upload)
        operation_duration = time.time() - operation_start_time
        
        if operation_success:
            # Success metrics
            uploaded_count = len([v for v in videos if getattr(v, 'uploaded', False)])
            success_rate = (uploaded_count / len(video_files_to_upload)) * 100 if video_files_to_upload else 0
            
            success_message = f"Successfully completed operations for account {username}: {uploaded_count}/{len(video_files_to_upload)} videos uploaded ({success_rate:.1f}% success rate) in {operation_duration:.1f}s"
            log_success(f"[PARTY] [INSTAGRAM_SUCCESS] {success_message}", LogCategories.UPLOAD)
            
            result_queue.put(("SUCCESS", success_message))
        else:
            error_msg = f"Instagram operations failed for account {username} after {operation_duration:.1f}s"
            log_error(f"[FAIL] [INSTAGRAM_FAILED] {error_msg}", LogCategories.UPLOAD)
            result_queue.put(("LOGIN_ERROR", error_msg))
        
    except Exception as e:
        error_message = str(e)
        
        log_error(f"[EXPLODE] [DOLPHIN_EXCEPTION] Critical error in Dolphin browser for account {username}: {error_message}", LogCategories.DOLPHIN)
        
        # Enhanced error categorization and handling
        if "PHONE_VERIFICATION_REQUIRED" in error_message:
            log_error(f"[PHONE] [VERIFICATION_PHONE] Phone verification required for account: {username}", LogCategories.VERIFICATION)
            send_critical_notification(task_id, f"Phone verification required for account {username} - manual intervention needed", 'VERIFICATION')
            result_queue.put(("PHONE_VERIFICATION_REQUIRED", f"Phone verification required for account: {username}"))
            
            # Update Instagram account status in database
            try:
                from uploader.models import InstagramAccount, BulkUploadAccount
                instagram_account = InstagramAccount.objects.get(username=username)
                instagram_account.status = 'PHONE_VERIFICATION_REQUIRED'
                instagram_account.save(update_fields=['status'])
                log_info(f"💾 [DATABASE] Updated account {username} status to PHONE_VERIFICATION_REQUIRED", LogCategories.DATABASE)
                
                # Also update BulkUploadAccount status for dashboard display
                try:
                    bulk_account = BulkUploadAccount.objects.get(id=account_task_id)
                    bulk_account.status = 'PHONE_VERIFICATION_REQUIRED'
                    bulk_account.save(update_fields=['status'])
                    log_info(f"💾 [DATABASE] Updated bulk account task {account_task_id} status to PHONE_VERIFICATION_REQUIRED", LogCategories.DATABASE)
                except BulkUploadAccount.DoesNotExist:
                    log_warning(f"💾 [DATABASE] BulkUploadAccount with ID {account_task_id} not found", LogCategories.DATABASE)
                except Exception as bulk_error:
                    log_error(f"💾 [DATABASE_ERROR] Failed to update bulk account status: {str(bulk_error)}", LogCategories.DATABASE)
                    
            except Exception as db_error:
                log_error(f"💾 [DATABASE_ERROR] Failed to update account status: {str(db_error)}", LogCategories.DATABASE)
                
        elif "HUMAN_VERIFICATION_REQUIRED" in error_message:
            log_error(f"[BOT] [VERIFICATION_HUMAN] Human verification required for account: {username}", LogCategories.VERIFICATION)
            send_critical_notification(task_id, f"Human verification required for account {username} - manual intervention needed", 'VERIFICATION')
            result_queue.put(("HUMAN_VERIFICATION_REQUIRED", f"Human verification required for account: {username}"))
            
            # Update Instagram account status in database
            try:
                from uploader.models import InstagramAccount, BulkUploadAccount
                instagram_account = InstagramAccount.objects.get(username=username)
                instagram_account.status = 'HUMAN_VERIFICATION_REQUIRED'
                instagram_account.save(update_fields=['status'])
                log_info(f"💾 [DATABASE] Updated account {username} status to HUMAN_VERIFICATION_REQUIRED", LogCategories.DATABASE)
                
                # Also update BulkUploadAccount status for dashboard display
                try:
                    bulk_account = BulkUploadAccount.objects.get(id=account_task_id)
                    bulk_account.status = 'HUMAN_VERIFICATION_REQUIRED'
                    bulk_account.save(update_fields=['status'])
                    log_info(f"💾 [DATABASE] Updated bulk account task {account_task_id} status to HUMAN_VERIFICATION_REQUIRED", LogCategories.DATABASE)
                except BulkUploadAccount.DoesNotExist:
                    log_warning(f"💾 [DATABASE] BulkUploadAccount with ID {account_task_id} not found", LogCategories.DATABASE)
                except Exception as bulk_error:
                    log_error(f"💾 [DATABASE_ERROR] Failed to update bulk account status: {str(bulk_error)}", LogCategories.DATABASE)
                    
            except Exception as db_error:
                log_error(f"💾 [DATABASE_ERROR] Failed to update account status: {str(db_error)}", LogCategories.DATABASE)
                
        elif "SUSPENDED" in error_message:
            log_error(f"[BLOCK] [VERIFICATION_SUSPENDED] Account suspended for account: {username}", LogCategories.VERIFICATION)
            send_critical_notification(task_id, f"Account {username} has been suspended by Instagram - manual review needed", 'VERIFICATION')
            result_queue.put(("SUSPENDED", f"Account suspended: {username}"))
            
            # Update Instagram account status in database
            try:
                from uploader.models import InstagramAccount, BulkUploadAccount
                instagram_account = InstagramAccount.objects.get(username=username)
                instagram_account.status = 'SUSPENDED'
                instagram_account.save(update_fields=['status'])
                log_info(f"💾 [DATABASE] Updated account {username} status to SUSPENDED", LogCategories.DATABASE)
                
                # Also update BulkUploadAccount status for dashboard display
                try:
                    bulk_account = BulkUploadAccount.objects.get(id=account_task_id)
                    bulk_account.status = 'SUSPENDED'
                    bulk_account.save(update_fields=['status'])
                    log_info(f"💾 [DATABASE] Updated bulk account task {account_task_id} status to SUSPENDED", LogCategories.DATABASE)
                except BulkUploadAccount.DoesNotExist:
                    log_warning(f"💾 [DATABASE] BulkUploadAccount with ID {account_task_id} not found", LogCategories.DATABASE)
                except Exception as bulk_error:
                    log_error(f"💾 [DATABASE_ERROR] Failed to update bulk account status: {str(bulk_error)}", LogCategories.DATABASE)
                    
            except Exception as db_error:
                log_error(f"💾 [DATABASE_ERROR] Failed to update account status: {str(db_error)}", LogCategories.DATABASE)
                
        else:
            log_error(f"[FAIL] Browser error: {error_message}")
            result_queue.put(("BROWSER_ERROR", error_message))
    
    finally:
        cleanup_browser_session(page, dolphin_browser, dolphin_profile_id, dolphin)

def authenticate_dolphin(dolphin):
    """Authenticate with Dolphin Anty API"""
    log_info("Authenticating with Dolphin Anty API", LogCategories.DOLPHIN)
    if not dolphin.authenticate():
        log_error("Failed to authenticate with Dolphin Anty API", LogCategories.DOLPHIN)
        return False
    
    log_success("Successfully authenticated with Dolphin Anty API", LogCategories.DOLPHIN)
    
    # Check application status
    log_info("Checking Dolphin Anty application status", LogCategories.DOLPHIN)
    dolphin_status = dolphin.check_dolphin_status()
    if not dolphin_status["app_running"]:
        error_msg = dolphin_status.get("error", "Unknown error")
        log_error(f"Dolphin Anty application is not running: {error_msg}", LogCategories.DOLPHIN)
        return False
    
    log_success("Dolphin Anty application is running and ready", LogCategories.DOLPHIN)
    return True

def get_dolphin_profile_id(username):
    """Get Dolphin profile ID for account"""
    try:
        from .models import InstagramAccount
        account = InstagramAccount.objects.get(username=username)
        return account.dolphin_profile_id
    except InstagramAccount.DoesNotExist:
        log_error(f"Account {username} not found in database")
        return None
    except Exception as e:
        log_error(f"Error getting dolphin profile ID for {username}: {str(e)}")
        return None

def perform_instagram_operations(page, account_details, videos, video_files_to_upload):
    """Perform Instagram operations with enhanced error handling and monitoring"""
    try:
        log_info("🌐 [NAVIGATION] Navigating to Instagram.com", LogCategories.NAVIGATION)
        
        # Navigate to Instagram with extended timeout
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
        
        # CRITICAL: Wait for page to fully load before proceeding
        log_info("[WAIT] [NAVIGATION] Waiting for page to fully load...", LogCategories.NAVIGATION)
        time.sleep(8)  # Increased from immediate to 8 seconds
        
        # Additional wait for network idle (all resources loaded)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
            log_info("[OK] [NAVIGATION] Network idle state reached", LogCategories.NAVIGATION)
        except Exception as e:
            log_warning(f"[WARN] [NAVIGATION] Network idle timeout, continuing: {str(e)}", LogCategories.NAVIGATION)
        
        # Wait for DOM to be interactive
        try:
            page.wait_for_function("document.readyState === 'complete'", timeout=10000)
            log_info("[OK] [NAVIGATION] Document ready state complete", LogCategories.NAVIGATION)
        except Exception as e:
            log_warning(f"[WARN] [NAVIGATION] Document ready timeout, continuing: {str(e)}", LogCategories.NAVIGATION)
        
        # Additional safety wait
        time.sleep(3)
        
        log_success("[OK] [NAVIGATION] Successfully loaded Instagram.com", LogCategories.NAVIGATION)
        
        # Initialize human behavior after page is fully loaded
        init_human_behavior(page)
        log_info("Human behavior initialized")
        
        # Handle cookie consent modal before login
        handle_cookie_consent(page)
        
        # Check login status and login if needed
        if not handle_login_flow(page, account_details):
            return False, "LOGIN_FAILED"
        
        # Upload videos
        uploaded_videos = 0
        for i, video_file_path in enumerate(video_files_to_upload, 1):
            try:
                video_obj = videos[i-1]
                
                # Log upload info
                log_video_info(i, len(video_files_to_upload), video_file_path, video_obj)
                
                # Navigate to upload page
                if not navigate_to_upload_with_human_behavior(page):
                    log_error(f"[FAIL] Could not navigate to upload page for video {i}")
                    continue
                
                # Upload video
                if upload_video_with_human_behavior(page, video_file_path, video_obj):
                    uploaded_videos += 1
                    log_info(f"[SUCCESS] Video {i}/{len(video_files_to_upload)} uploaded successfully")
                    video_obj.uploaded = True
                else:
                    log_error(f"[FAIL] Failed to upload video {i}/{len(video_files_to_upload)}")
                
                # Human delay between uploads
                if i < len(video_files_to_upload):
                    add_human_delay_between_uploads(page, i)
                    
            except Exception as e:
                log_error(f"[FAIL] Error uploading video {i}: {str(e)}")
                continue
        
        # Final cleanup
        perform_final_cleanup(page, account_details['username'])
        return True, "UPLOAD_SUCCESS"
        
    except Exception as e:
        error_message = str(e)
        if "PHONE_VERIFICATION_REQUIRED" in error_message:
            log_error(f"Phone verification required: {error_message}", LogCategories.VERIFICATION)
            raise e  # Re-raise to be caught by run_dolphin_browser
        elif "HUMAN_VERIFICATION_REQUIRED" in error_message:
            log_error(f"Human verification required: {error_message}", LogCategories.VERIFICATION)
            raise e  # Re-raise to be caught by run_dolphin_browser
        elif "SUSPENDED" in error_message:
            log_error(f"Account suspended: {error_message}", LogCategories.VERIFICATION)
            raise e  # Re-raise to be caught by run_dolphin_browser
        else:
            log_error(f"Error in Instagram operations: {error_message}")
            return False, "UPLOAD_FAILED"

def cleanup_browser_session(page, dolphin_browser, dolphin_profile_id, dolphin):
    """Clean up browser session safely"""
    try:
        log_info("[CLEANUP] Starting comprehensive browser cleanup")
        if page and dolphin_browser:
            BrowserManager.safely_close_browser(page, dolphin_browser, dolphin_profile_id)
            log_info("[CLEANUP] [OK] Browser cleanup completed successfully")
        else:
            log_info("[CLEANUP] Browser objects not initialized, skipping cleanup")
    except Exception as cleanup_error:
        log_error(f"[CLEANUP] Emergency cleanup failed: {str(cleanup_error)}")

def handle_login_flow(page, account_details):
    """Handle Instagram login flow with comprehensive verification checks"""
    try:
        log_info("🔑 Need to login to Instagram", LogCategories.LOGIN)
        
        # Wait for page to be fully interactive before checking login status
        log_info("[WAIT] [LOGIN] Ensuring page is fully loaded before login check...", LogCategories.LOGIN)
        time.sleep(3)  # Additional wait for page stability
        
        # Only check for reCAPTCHA before attempting login (it can appear on login page)
        log_info("[SEARCH] Checking for reCAPTCHA on login page...", LogCategories.CAPTCHA)
        handle_recaptcha_if_present(page)
        log_success("[OK] reCAPTCHA handling completed", LogCategories.CAPTCHA)
        
        # Perform login FIRST
        login_result = perform_instagram_login_optimized(page, account_details)
        
        if login_result == "SUSPENDED":
            log_error("[BLOCK] Account suspended detected during login check", LogCategories.VERIFICATION)
            raise Exception(f"SUSPENDED: Account suspended by Instagram")
        elif not login_result:
            log_error("[FAIL] Failed to login to Instagram", LogCategories.LOGIN)
            return False
        
        log_success("[OK] Login completed successfully", LogCategories.LOGIN)
        
        # NOW check for post-login verification requirements
        log_info("[SEARCH] Checking for phone verification requirement...", LogCategories.VERIFICATION)
        phone_verification_result = check_for_phone_verification_page(page)
        
        if phone_verification_result.get('requires_phone_verification', False):
            log_error(f"[PHONE] Phone verification required after login: {phone_verification_result.get('message', 'Unknown reason')}", LogCategories.VERIFICATION)
            raise Exception(f"PHONE_VERIFICATION_REQUIRED: {phone_verification_result.get('message', 'Phone verification required')}")
        
        # Check for human verification after login
        log_info("[SEARCH] Checking for human verification requirement...", LogCategories.VERIFICATION)
        human_verification_result = check_for_human_verification_dialog(page, account_details)
        
        if human_verification_result.get('requires_human_verification', False):
            log_error(f"[BOT] Human verification required after login: {human_verification_result.get('message', 'Unknown reason')}", LogCategories.VERIFICATION)
            raise Exception(f"HUMAN_VERIFICATION_REQUIRED: {human_verification_result.get('message', 'Human verification required')}")
        
        # Check for account suspension after login
        log_info("[SEARCH] Checking for account suspension...", LogCategories.VERIFICATION)
        suspension_result = check_for_account_suspension(page)
        
        if suspension_result.get('account_suspended', False):
            suspension_message = suspension_result.get('message', 'Account suspended by Instagram')
            log_error(f"[BLOCK] Account suspension detected after login: {suspension_message}", LogCategories.VERIFICATION)
            
            # Raise exception to trigger account status update
            raise Exception(f"SUSPENDED: {suspension_message}")
        
        # Post-login reCAPTCHA check
        log_info("[SEARCH] Checking for post-login reCAPTCHA...", LogCategories.CAPTCHA)
        handle_recaptcha_if_present(page)
        
        # Clear human verification badge if it was previously set
        try:
            clear_human_verification_badge(account_details['username'])
        except Exception:
            pass
        
        log_success("[OK] Login flow completed successfully", LogCategories.LOGIN)
        return True
        
    except Exception as e:
        error_message = str(e)
        
        # Re-raise verification-related exceptions so they can be handled by run_dolphin_browser
        if ("SUSPENDED:" in error_message or 
            "PHONE_VERIFICATION_REQUIRED:" in error_message or 
            "HUMAN_VERIFICATION_REQUIRED:" in error_message):
            log_error(f"[FAIL] Error in login flow (re-raising for status update): {error_message}", LogCategories.LOGIN)
            raise e  # Re-raise the exception so it reaches run_dolphin_browser
        else:
            log_error(f"[FAIL] Error in login flow: {error_message}", LogCategories.LOGIN)
            return False

def log_video_info(video_index, total_videos, video_file_path, video_obj):
    """Log information about the video being uploaded"""
    video_title = ""
    if hasattr(video_obj, 'title_data') and video_obj.title_data:
        video_title = video_obj.title_data.title
        caption_preview = f"'{video_title[:50]}{'...' if len(video_title) > 50 else ''}'"
        log_info(f"[UPLOAD {video_index}/{total_videos}] Video: {os.path.basename(video_file_path)} | Caption: {caption_preview}")
    else:
        log_info(f"[UPLOAD {video_index}/{total_videos}] Video: {os.path.basename(video_file_path)} | No caption")

def add_human_delay_between_uploads(page, video_index, total_videos=None, account_fatigue=1.0):
    """Улучшенная функция задержки между загрузками видео"""
    
    # Используем новую улучшенную функцию расчета задержки
    if total_videos is None:
        total_videos = 10  # Значение по умолчанию
    
    final_delay = get_enhanced_video_delay(video_index, total_videos, account_fatigue)
    
    log_info(f"[ENHANCED_VIDEO_BREAK] Video {video_index + 1}/{total_videos}: "
             f"Taking enhanced break for {final_delay:.1f}s ({final_delay/60:.1f} minutes)")
    
    # Проверяем, нужен ли интеллектуальный перерыв
    session_duration = (datetime.now() - session_start_time).total_seconds() / 60 if session_start_time else 0
    
    if simulate_smart_break(video_index, total_videos, session_duration):
        log_info(f"[SMART_BREAK] Additional smart break was taken during video processing")
    
    # Основная задержка с улучшенным поведением
    simulate_extended_human_rest_behavior(page, final_delay)

def perform_final_cleanup(page, username):
    """Perform final cleanup activities"""
    try:
        log_info(f"[CLEAN] [CLEANUP] Starting final cleanup for user: {username}")
        
        # Try to navigate away from any sensitive pages
        try:
            # Go to main Instagram page
            page.goto('https://www.instagram.com/', wait_until='load', timeout=15000)
            log_info("[CLEAN] [CLEANUP] Navigated to main page")
        except Exception as e:
            log_warning(f"[CLEAN] [CLEANUP] Could not navigate to main page: {str(e)}")
        
        # Wait a moment
        time.sleep(random.uniform(1, 3))
        log_info("[CLEAN] [CLEANUP] Final cleanup completed")
        
    except Exception as e:
        log_warning(f"[CLEAN] [CLEANUP] Error during final cleanup: {str(e)}")

def perform_instagram_login(page, account_details):
    """Redirect to optimized login function"""
    return perform_instagram_login_optimized(page, account_details)

def check_for_phone_verification_page(page):
    """Check if Instagram is showing phone verification page - Enhanced version"""
    try:
        log_info("[SEARCH] [PHONE_VERIFY] Starting phone verification check...", LogCategories.VERIFICATION)
        time.sleep(random.uniform(1, 2))
        
        # Get page text for analysis
        try:
            page_text = page.inner_text('body') or ""
        except Exception:
            page_text = ""
        
        # Check for phone verification keywords
        phone_verification_keywords = [
            'введите свой номер мобильного телефона',
            'подтвердите номер телефона', 
            'add phone number',
            'verify your phone number'
        ]
        
        detected_keywords = []
        for keyword in phone_verification_keywords:
            if keyword.lower() in page_text.lower():
                detected_keywords.append(keyword)
        
        phone_verification_detected = len(detected_keywords) > 0
        
        if phone_verification_detected:
            log_error(f"[PHONE] [PHONE_VERIFY] Phone verification requirement detected!", LogCategories.VERIFICATION)
            return {
                'requires_phone_verification': True,
                'message': f"Phone verification required",
                'detected_keywords': detected_keywords[:3]
            }
        else:
            log_info(f"[OK] [PHONE_VERIFY] No phone verification requirement detected", LogCategories.VERIFICATION)
            return {
                'requires_phone_verification': False,
                'message': f"No phone verification required"
            }
            
    except Exception as e:
        log_warning(f"[FAIL] [PHONE_VERIFY] Error checking for phone verification: {str(e)}", LogCategories.VERIFICATION)
        return {
            'requires_phone_verification': False,
            'message': f"Error checking phone verification: {str(e)}"
        }

def check_for_human_verification_dialog(page, account_details=None):
    """Check if Instagram is showing the human verification dialog - Enhanced version"""
    try:
        log_info("[SEARCH] [HUMAN_VERIFY] Starting human verification check...", LogCategories.VERIFICATION)
        time.sleep(random.uniform(1, 2))
        
        # Get page text for analysis
        try:
            page_text = page.inner_text('body') or ""
        except Exception:
            page_text = ""
        
        # Check for human verification keywords
        human_verification_keywords = [
            'подтвердите, что это вы',
            'подтвердите свою личность',
            'confirm that this is you',
            'verify your identity'
        ]
        
        detected_keywords = []
        for keyword in human_verification_keywords:
            if keyword.lower() in page_text.lower():
                detected_keywords.append(keyword)
        
        human_verification_detected = len(detected_keywords) > 0
        
        if human_verification_detected:
            log_error(f"[BOT] [HUMAN_VERIFY] Human verification requirement detected!", LogCategories.VERIFICATION)
            return {
                'requires_human_verification': True,
                'message': f"Human verification required",
                'detected_keywords': detected_keywords[:3]
            }
        else:
            log_info(f"[OK] [HUMAN_VERIFY] No human verification requirement detected", LogCategories.VERIFICATION)
            return {
                'requires_human_verification': False,
                'message': f"No human verification required"
            }
            
    except Exception as e:
        log_warning(f"[FAIL] [HUMAN_VERIFY] Error checking for human verification: {str(e)}", LogCategories.VERIFICATION)
        return {
            'requires_human_verification': False,
            'message': f"Error checking human verification: {str(e)}"
        }

def check_for_account_suspension(page):
    """Check if Instagram is showing account suspension message - Enhanced version with Russian and English detection"""
    try:
        log_info("[SEARCH] [SUSPENSION_CHECK] Starting account suspension check...", LogCategories.VERIFICATION)
        time.sleep(random.uniform(1, 2))
        
        # Get page text for analysis
        try:
            page_text = page.inner_text('body') or ""
            page_title = page.title() or ""
        except Exception:
            page_text = ""
            page_title = ""
        
        log_info(f"[SEARCH] [SUSPENSION_CHECK] Page title: '{page_title}'")
        
        # Comprehensive suspension keywords in Russian and English
        suspension_keywords = [
            # Russian suspension messages
            'мы приостановили ваш аккаунт',
            'ваш аккаунт приостановлен',
            'приостановили ваш аккаунт',
            'аккаунт был приостановлен',
            'временно приостановлен',
            'нарушение условий',
            'действие заблокировано',
            'аккаунт заблокирован',
            'ваш аккаунт заблокирован',
            'доступ ограничен',
            
            # English suspension messages  
            'we suspended your account',
            'your account has been suspended',
            'account suspended',
            'temporarily suspended',
            'violation of terms',
            'action blocked',
            'account disabled',
            'your account is disabled',
            'access restricted',
            'account restricted',
            
            # General suspension indicators
            'community guidelines',
            'terms of service',
            'нарушение правил сообщества',
            'условия использования'
        ]
        
        detected_keywords = []
        for keyword in suspension_keywords:
            if keyword.lower() in page_text.lower() or keyword.lower() in page_title.lower():
                detected_keywords.append(keyword)
        
        suspension_detected = len(detected_keywords) > 0
        
        # Additional check for suspension-specific page URLs
        current_url = page.url.lower()
        suspension_url_patterns = [
            'challenge',
            'suspended',
            'disabled',
            'blocked',
            'restriction'
        ]
        
        url_suspension_detected = any(pattern in current_url for pattern in suspension_url_patterns)
        
        if suspension_detected or url_suspension_detected:
            log_error(f"[BLOCK] [SUSPENSION_CHECK] ACCOUNT SUSPENSION DETECTED!", LogCategories.VERIFICATION)
            log_error(f"[BLOCK] [SUSPENSION_CHECK] URL: {page.url}", LogCategories.VERIFICATION)
            log_error(f"[BLOCK] [SUSPENSION_CHECK] Keywords found: {detected_keywords[:5]}", LogCategories.VERIFICATION)
            
            suspension_reason = "Account suspended by Instagram"
            if detected_keywords:
                suspension_reason += f" (Keywords: {', '.join(detected_keywords[:3])})"
            
            return {
                'account_suspended': True,
                'message': suspension_reason,
                'detected_keywords': detected_keywords[:5],
                'suspension_url': url_suspension_detected,
                'page_url': page.url
            }
        else:
            log_info(f"[OK] [SUSPENSION_CHECK] No account suspension detected", LogCategories.VERIFICATION)
            return {
                'account_suspended': False,
                'message': "No account suspension detected"
            }
            
    except Exception as e:
        log_error(f"[FAIL] [SUSPENSION_CHECK] Error checking for account suspension: {str(e)}", LogCategories.VERIFICATION)
        return {
            'account_suspended': False,
            'message': f"Error checking suspension: {str(e)}"
        }

def simulate_human_mouse_movement(page):
    """Simulate natural human mouse movements"""
    try:
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.3, 0.8))
        log_info("[HUMAN] Simulated natural mouse movements")
    except Exception as e:
        log_warning(f"[HUMAN] Mouse movement simulation failed: {str(e)}")

# Helper function for finding elements
def _find_element(page, selectors):
    """Find the first visible element matching any of the given selectors"""
    for selector in selectors:
        try:
            if selector.startswith('//'):
                element = page.query_selector(f"xpath={selector}")
            else:
                element = page.query_selector(selector)
            
            if element and element.is_visible():
                return element
        except Exception:
            continue
    return None

def _human_click_with_timeout(page, element, log_prefix="HUMAN_CLICK"):
    """Human-like click with short timeout to avoid verbose logs"""
    try:
        # Get human behavior instance
        human_behavior = get_human_behavior()
        if human_behavior:
            # Set shorter timeout to avoid long retry loops
            original_timeout = page._timeout_settings.default_timeout if hasattr(page, '_timeout_settings') else 30000
            page.set_default_timeout(5000)  # 5 seconds max
            
            try:
                human_behavior.advanced_element_interaction(element, 'click')
                log_info(f"[{log_prefix}] [OK] Human click successful")
                
                # Restore original timeout
                page.set_default_timeout(original_timeout)
                return True
                
            except Exception as e:
                # Restore timeout even if failed
                page.set_default_timeout(original_timeout)
                log_warning(f"[{log_prefix}] Human behavior failed: {str(e)[:100]}")
                
                # Fallback to quick click
                element.click()
                return True
        else:
            # No human behavior available, use quick click
            element.click()
            return True
            
    except Exception as e:
        log_error(f"[{log_prefix}] Error in human click: {str(e)[:100]}")
        return False

def ensure_single_tab_only(page):
    """Ensure only one tab is open in the browser profile"""
    try:
        log_info("[TAB_CLEANUP] [CLEAN] Checking for multiple tabs...")
        
        # Get browser context
        context = page.context
        pages = context.pages
        
        log_info(f"[TAB_CLEANUP] Found {len(pages)} open tabs")
        
        if len(pages) > 1:
            log_info(f"[TAB_CLEANUP] Closing {len(pages) - 1} extra tabs...")
            
            # Keep the current page, close all others
            current_page = page
            for p in pages:
                if p != current_page:
                    try:
                        log_info(f"[TAB_CLEANUP] Closing tab: {p.url}")
                        p.close()
                        log_info("[TAB_CLEANUP] [OK] Tab closed successfully")
                    except Exception as e:
                        log_warning(f"[TAB_CLEANUP] [WARN] Could not close tab: {str(e)}")
                        continue
            
            log_info(f"[TAB_CLEANUP] [OK] Tab cleanup completed - {len(pages) - 1} tabs closed")
        else:
            log_info("[TAB_CLEANUP] [OK] Only one tab open - no cleanup needed")
        
        return True
        
    except Exception as e:
        log_error(f"[TAB_CLEANUP] [FAIL] Error during tab cleanup: {str(e)}")
        return False

def send_critical_notification(task_id, message, notification_type='ERROR'):
    """Send critical notifications for important events"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        notification_data = {
            'task_id': task_id,
            'type': notification_type,
            'message': message,
            'timestamp': timestamp,
            'urgency': 'HIGH' if notification_type in ['ERROR', 'VERIFICATION'] else 'MEDIUM'
        }
        
        # Store in cache for immediate web interface display
        notifications_key = f"critical_notifications_{task_id}"
        existing_notifications = cache.get(notifications_key, [])
        existing_notifications.append(notification_data)
        
        # Keep only last 50 notifications
        if len(existing_notifications) > 50:
            existing_notifications = existing_notifications[-50:]
        
        cache.set(notifications_key, existing_notifications, timeout=7200)  # 2 hours
        
        # Log the critical event
        log_error(f"[ALERT] [CRITICAL_NOTIFICATION] {message}", LogCategories.VERIFICATION)
        
    except Exception as e:
        logger.error(f"Failed to send critical notification: {str(e)}")

# Global variable to store current task ID
_current_task_id = None

def set_current_task_id(task_id):
    """Set the current task ID for global access"""
    global _current_task_id
    _current_task_id = task_id

def get_current_task_id():
    """Get the current task ID"""
    global _current_task_id
    return _current_task_id

def handle_recaptcha_if_present(page):
    """Handle reCAPTCHA if present on the page"""
    try:
        from .captcha_solver import solve_recaptcha_if_present_sync
        # Ensure dashboard receives correct bulk upload id for banner notifications
        task_id = get_current_task_id()
        account_details = {"bulk_upload_id": task_id} if task_id else {}
        return solve_recaptcha_if_present_sync(page, account_details)
    except ImportError:
        log_warning("reCAPTCHA solver not available")
        return True
    except Exception as e:
        log_warning(f"Error handling reCAPTCHA: {str(e)}")
        return True

# Глобальные переменные для отслеживания состояния сессии
session_start_time = None
total_processed_count = 0
error_streak = 0
last_error_time = None

def get_enhanced_account_delay(current_index, total_accounts, successful_count, failed_count):
    """
    Улучшенный расчет задержки между аккаунтами с учетом множественных факторов
    """
    global session_start_time, total_processed_count, error_streak, last_error_time
    
    if session_start_time is None:
        session_start_time = datetime.now()
    
    # Базовая задержка
    base_delay = random.uniform(TimeConstants.ACCOUNT_DELAY_MIN, TimeConstants.ACCOUNT_DELAY_MAX)
    
    # Множители и расчеты...
    time_multiplier = get_time_of_day_multiplier()
    session_duration = (datetime.now() - session_start_time).total_seconds() / 60
    fatigue_multiplier = 1.0 + min(session_duration / 60, 1.5)
    
    progress = current_index / total_accounts
    if progress < 0.2:
        progress_multiplier = 1.3
    elif progress > 0.8:
        progress_multiplier = 1.4
    else:
        progress_multiplier = 1.0
    
    error_multiplier = 1.0
    if failed_count > 0:
        error_rate = failed_count / max(1, successful_count + failed_count)
        error_multiplier = 1.0 + (error_rate * 2.0)
    
    random_multiplier = random.uniform(0.7, 1.8)
    pattern_multiplier = get_activity_pattern_multiplier(current_index, total_accounts)
    
    total_multiplier = (
        time_multiplier * 
        fatigue_multiplier * 
        progress_multiplier * 
        error_multiplier * 
        random_multiplier * 
        pattern_multiplier
    )
    
    final_delay = base_delay * total_multiplier
    
    # Ограничиваем разумными пределами
    min_delay = TimeConstants.ACCOUNT_DELAY_MIN * 0.5
    max_delay = TimeConstants.ACCOUNT_DELAY_MAX * 4.0
    final_delay = max(min_delay, min(max_delay, final_delay))
    
    total_processed_count += 1
    return final_delay

def get_time_of_day_multiplier():
    """Получить множитель задержки в зависимости от времени суток"""
    current_hour = datetime.now().hour
    
    # Ночные часы (23-6): очень медленное поведение
    if 23 <= current_hour or current_hour <= 6:
        return TimeConstants.NIGHT_DELAY_MULTIPLIER * random.uniform(0.8, 1.2)
    # Утренние часы (7-11): медленное поведение
    elif 7 <= current_hour <= 11:
        return TimeConstants.MORNING_DELAY_MULTIPLIER * random.uniform(0.9, 1.1)
    # Вечерние часы (18-22): более быстрое поведение
    elif 18 <= current_hour <= 22:
        return TimeConstants.EVENING_DELAY_MULTIPLIER * random.uniform(0.9, 1.1)
    # Рабочие часы (12-17): нормальное поведение
    else:
        return 1.0 * random.uniform(0.8, 1.2)

def get_activity_pattern_multiplier(current_index, total_accounts):
    """
    Получить множитель активности на основе человеческих паттернов поведения
    """
    progress = current_index / total_accounts
    
    # Волнообразный паттерн активности
    wave_position = progress * 2 * math.pi
    wave_value = (math.sin(wave_position) + 1) / 2  # Нормализуем к 0-1
    
    # Преобразуем в множитель (более низкие значения = более быстрое выполнение)
    activity_multiplier = 1.5 - (wave_value * 0.8)  # Диапазон 0.7-1.5
    
    # Добавляем небольшой случайный компонент
    return activity_multiplier * random.uniform(0.9, 1.1)

def simulate_smart_break(current_index, total_accounts, session_duration_minutes):
    """
    Интеллектуальная симуляция перерывов на основе человеческого поведения
    """
    # Простая реализация для краткости
    base_break_probability = 0.1
    
    if random.random() < base_break_probability:
        break_duration = random.uniform(30, 120)
        log_info(f"[SMART_BREAK] Taking break for {break_duration:.1f}s", LogCategories.HUMAN)
        time.sleep(break_duration)
        return True
    
    return False

def get_enhanced_video_delay(video_index, total_videos, account_fatigue_level=1.0):
    """
    Улучшенный расчет задержки между видео с учетом усталости и паттернов
    """
    # Базовая задержка
    base_delay = random.uniform(TimeConstants.VIDEO_DELAY_MIN, TimeConstants.VIDEO_DELAY_MAX)
    
    # Прогрессивная усталость
    fatigue_multiplier = 1.0 + (video_index * 0.15) * account_fatigue_level
    
    # Дополнительные задержки для определенных видео
    if video_index % 5 == 0 and video_index > 0:
        complexity_multiplier = random.uniform(1.3, 1.8)
        log_info(f"[VIDEO_DELAY] Complex content detected, adding extra delay", LogCategories.HUMAN)
    else:
        complexity_multiplier = 1.0
    
    # Временной фактор
    time_multiplier = get_time_of_day_multiplier()
    
    final_delay = base_delay * fatigue_multiplier * complexity_multiplier * time_multiplier
    
    # Ограничиваем максимум 20 минутами
    final_delay = min(final_delay, 1200)
    
    log_info(f"[VIDEO_DELAY] Video {video_index + 1}/{total_videos}: {final_delay:.1f}s "
            f"(base: {base_delay:.1f}s, fatigue: {fatigue_multiplier:.2f}x, "
            f"complexity: {complexity_multiplier:.2f}x)", LogCategories.HUMAN)
    
    return final_delay

def determine_verification_type(page):
    """Determine the type of verification required with improved accuracy"""
    try:
        log_info("[SEARCH] [VERIFICATION_TYPE] Analyzing page to determine verification type...")
        
        # Get page content for analysis
        try:
            page_text = page.inner_text('body') or ""
            page_html = page.content() or ""
        except Exception:
            page_text = ""
            page_html = ""
        
        # Check for different types of verification
        is_email_verification = any(keyword in page_text.lower() for keyword in InstagramTexts.EMAIL_VERIFICATION_KEYWORDS)
        is_code_entry = any(keyword in page_text.lower() for keyword in InstagramTexts.CODE_ENTRY_KEYWORDS)
        is_non_email = any(keyword in page_text.lower() for keyword in InstagramTexts.NON_EMAIL_VERIFICATION_KEYWORDS)
        
        log_info(f"[SEARCH] [VERIFICATION_TYPE] Text analysis - Email: {is_email_verification}, Code: {is_code_entry}, Non-Email: {is_non_email}")
        
        # Check for specific form elements - UPDATED SELECTORS
        email_field_selectors = [
            'input[name="email"]',              # Current Instagram email field
            'input[name="emailOrPhone"]',       # Alternative
            'input[type="email"]',
            'input[autocomplete="email"]',
            'input[inputmode="email"]',
            # Updated selectors excluding verification code fields
            'input[aria-label*="email" i]:not([aria-label*="code" i]):not([aria-label*="код" i]):not([aria-label*="verification" i])',
            'input[aria-label*="Email" i]:not([aria-label*="code" i]):not([aria-label*="код" i]):not([aria-label*="verification" i])',
            'input[aria-label*="почт" i]:not([aria-label*="код" i]):not([aria-label*="verification" i])',
            'input[aria-label*="Почт" i]:not([aria-label*="код" i]):not([aria-label*="verification" i])',
        ]
        
        verification_code_selectors = [
            'input[name="verificationCode"]',
            'input[name="confirmationCode"]', 
            'input[name="securityCode"]',
            'input[autocomplete="one-time-code"]',
            'input[inputmode="numeric"]',
            'input[type="tel"]',
            'input[maxlength="6"]',
            'input[aria-label*="код" i]:not([aria-label*="email" i]):not([aria-label*="почт" i])',
            'input[aria-label*="code" i]:not([aria-label*="email" i]):not([aria-label*="phone" i])',
            'input[placeholder*="код" i]:not([placeholder*="email" i]):not([placeholder*="почт" i])',
            'input[placeholder*="code" i]:not([placeholder*="email" i]):not([placeholder*="phone" i])',
        ]
        
        # Check for email fields
        email_field_found = False
        for selector in email_field_selectors:
            try:
                element = page.query_selector(selector)
                if element and element.is_visible():
                    log_info(f"[SEARCH] [VERIFICATION_TYPE] Found email field: {selector}")
                    email_field_found = True
                    break
            except:
                continue
        
        # Check for verification code fields
        code_field_found = False
        for selector in verification_code_selectors:
            try:
                element = page.query_selector(selector)
                if element and element.is_visible():
                    log_info(f"[SEARCH] [VERIFICATION_TYPE] Found code field: {selector}")
                    code_field_found = True
                    break
            except:
                continue
        
        # Determine verification type based on analysis
        if is_non_email:
            log_info("[SEARCH] [VERIFICATION_TYPE] Result: Non-email verification (2FA/Authenticator)")
            return "authenticator"
        elif email_field_found and is_email_verification:
            log_info("[SEARCH] [VERIFICATION_TYPE] Result: Email field input required")
            return "email_field"
        elif code_field_found and (is_email_verification or is_code_entry):
            log_info("[SEARCH] [VERIFICATION_TYPE] Result: Email verification code required")
            return "email_code"
        elif is_email_verification:
            log_info("[SEARCH] [VERIFICATION_TYPE] Result: Email verification (keywords found)")
            return "email_code"  # Default to code entry if email verification detected
        else:
            log_info("[SEARCH] [VERIFICATION_TYPE] Result: Unknown/No verification")
            return "unknown"
            
    except Exception as e:
        log_error(f"[SEARCH] [VERIFICATION_TYPE] Error determining verification type: {str(e)}")
        return "unknown"

def handle_cookie_consent(page):
    """Handle Instagram cookie consent modal with comprehensive Russian and English support"""
    try:
        log_info("🍪 [COOKIES] Checking for cookie consent modal...", LogCategories.LOGIN)
        
        # First, check if cookie modal is present
        modal_detected = False
        
        for i, indicator in enumerate(SelectorConfig.COOKIE_MODAL_INDICATORS):
            try:
                if SelectorUtils.is_xpath(indicator):
                    element = page.query_selector(f"xpath={indicator}")
                else:
                    element = page.query_selector(indicator)
                
                if element and element.is_visible():
                    modal_detected = True
                    log_info(f"🍪 [COOKIES] Cookie modal detected with indicator {i+1}", LogCategories.LOGIN)
                    break
                    
            except Exception:
                continue
        
        if not modal_detected:
            log_info("🍪 [COOKIES] No cookie consent modal found", LogCategories.LOGIN)
            return False
        
        # Wait a bit for modal to fully load
        time.sleep(random.uniform(2, 4))
        
        # Try to find and click "Accept All" button
        log_info("🍪 [COOKIES] Attempting to accept all cookies...", LogCategories.LOGIN)
        
        for i, selector in enumerate(SelectorConfig.COOKIE_CONSENT_BUTTONS):
            try:
                log_info(f"🍪 [COOKIES] Trying selector {i+1}/{len(SelectorConfig.COOKIE_CONSENT_BUTTONS)}: {selector[:50]}...")
                
                if SelectorUtils.is_xpath(selector):
                    element = page.query_selector(f"xpath={selector}")
                else:
                    element = page.query_selector(selector)
                
                if element and element.is_visible():
                    # Get button text for logging
                    button_text = ""
                    try:
                        button_text = element.text_content() or ""
                        button_text = button_text.strip()[:50]
                    except:
                        button_text = "Unknown"
                    
                    log_info(f"🍪 [COOKIES] Found accept button: '{button_text}' with selector: {selector}")
                    
                    # Simulate human behavior before clicking
                    human_behavior = get_human_behavior()
                    if human_behavior:
                        # Hover over button briefly
                        try:
                            element.hover()
                            time.sleep(random.uniform(0.5, 1.0))
                        except:
                            pass
                    
                    # Click the button
                    element.click()
                    log_success(f"[OK] [COOKIES] Successfully clicked accept button: '{button_text}'", LogCategories.LOGIN)
                    
                    # Wait for modal to disappear
                    time.sleep(random.uniform(2, 4))
                    
                    # Verify modal is gone
                    modal_still_present = False
                    for indicator in SelectorConfig.COOKIE_MODAL_INDICATORS:
                        try:
                            if SelectorUtils.is_xpath(indicator):
                                check_element = page.query_selector(f"xpath={indicator}")
                            else:
                                check_element = page.query_selector(indicator)
                            
                            if check_element and check_element.is_visible():
                                modal_still_present = True
                                break
                        except:
                            continue
                    
                    if not modal_still_present:
                        log_success("[OK] [COOKIES] Cookie consent modal successfully dismissed", LogCategories.LOGIN)
                        return True
                    else:
                        log_warning("[WARN] [COOKIES] Modal still present after clicking button", LogCategories.LOGIN)
                    
                    break
                    
            except Exception as e:
                log_warning(f"[WARN] [COOKIES] Selector {i+1} failed: {str(e)}")
                continue
        
        # If we get here, we couldn't find the accept button
        log_warning("[WARN] [COOKIES] Could not find accept cookies button, trying decline", LogCategories.LOGIN)
        
        # Try decline buttons as fallback (better than nothing)
        for i, selector in enumerate(SelectorConfig.COOKIE_DECLINE_BUTTONS):
            try:
                if SelectorUtils.is_xpath(selector):
                    element = page.query_selector(f"xpath={selector}")
                else:
                    element = page.query_selector(selector)
                
                if element and element.is_visible():
                    button_text = ""
                    try:
                        button_text = element.text_content() or ""
                        button_text = button_text.strip()[:50]
                    except:
                        button_text = "Unknown"
                    
                    log_info(f"🍪 [COOKIES] Found decline button: '{button_text}', clicking as fallback")
                    element.click()
                    time.sleep(random.uniform(2, 4))
                    log_info(f"[OK] [COOKIES] Clicked decline button as fallback: '{button_text}'", LogCategories.LOGIN)
                    return True
                    
            except Exception:
                continue
        
        log_warning("[WARN] [COOKIES] Could not handle cookie consent modal", LogCategories.LOGIN)
        return False
        
    except Exception as e:
        log_error(f"[FAIL] [COOKIES] Error handling cookie consent: {str(e)}", LogCategories.LOGIN)
        return False

def cleanup_original_video_files_sync(task) -> int:
    """Очищает оригинальные видео файлы из media/bot/bulk_videos/ для данной задачи (синхронная версия)"""
    import os
    
    deleted_count = 0
    
    try:
        # Получаем все видео файлы для этой задачи
        videos = task.videos.all()
        
        for video in videos:
            if video.video_file:
                try:
                    # Получаем полный путь к файлу
                    file_path = video.video_file.path if hasattr(video.video_file, 'path') else None
                    
                    if file_path and os.path.exists(file_path):
                        # БЕЗОПАСНАЯ ПРОВЕРКА: проверяем, не используется ли файл другими активными задачами
                        def is_file_safe_to_delete():
                            filename = os.path.basename(file_path)
                            
                            # Проверяем, есть ли другие BulkVideo объекты с таким же файлом в активных задачах
                            from .models import BulkVideo, BulkUploadTask
                            
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
                        
                        is_safe, warning_msg = is_file_safe_to_delete()
                        
                        if is_safe:
                            # Удаляем файл
                            filename = os.path.basename(file_path)
                            os.unlink(file_path)
                            deleted_count += 1
                            log_debug(f"[DELETE] [CLEANUP] Deleted original video file: {filename}", LogCategories.CLEANUP)
                        else:
                            log_info(f"[PAUSE] [CLEANUP] Skipped deleting file (still in use by other tasks): {os.path.basename(file_path)}", LogCategories.CLEANUP)
                            if warning_msg:
                                log_warning(warning_msg, LogCategories.CLEANUP)
                        
                except Exception as e:
                    log_warning(f"[WARN] [CLEANUP] Failed to delete video file {video.id}: {str(e)}", LogCategories.CLEANUP)
    
    except Exception as e:
        log_error(f"[FAIL] [CLEANUP] Error in cleanup_original_video_files_sync: {str(e)}", LogCategories.CLEANUP)
    
    return deleted_count

class WebLogHandler(logging.Handler):
    """Logging handler that forwards Python logging records to the active WebLogger"""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            logger_instance = get_web_logger()
            if not logger_instance:
                return
            # Map levelno to our levels
            if record.levelno >= logging.ERROR:
                level = 'ERROR'
            elif record.levelno >= logging.WARNING:
                level = 'WARNING'
            elif record.levelno >= logging.INFO:
                level = 'INFO'
            else:
                level = 'DEBUG'
            message = self.format(record) if self.formatter else record.getMessage()
            logger_instance.log(level, message, category=None)
        except Exception:
            # Avoid breaking logging pipeline
            pass


_installed_web_handlers = False

def install_web_log_handler():
    """Attach WebLogHandler to relevant loggers once per process"""
    global _installed_web_handlers
    if _installed_web_handlers:
        return
    handler = WebLogHandler()
    # Keep formatter minimal; message formatting already done by WebLogger
    handler.setLevel(logging.INFO)
    # Attach to our module logger and related libs
    for name in ['uploader', 'uploader.bulk_tasks', 'bot.src.instagram_uploader.dolphin_anty']:
        try:
            lg = logging.getLogger(name)
            # Ensure INFO level so records pass even if root is CRITICAL
            lg.setLevel(logging.INFO)
            # Avoid duplicate attachments
            if not any(isinstance(h, WebLogHandler) for h in lg.handlers):
                lg.addHandler(handler)
            # Prevent propagation up to root (which is set to CRITICAL)
            lg.propagate = False
        except Exception:
            pass
    _installed_web_handlers = True