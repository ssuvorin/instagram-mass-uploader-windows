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
from .login_optimized import perform_instagram_login_optimized
from .logging_utils import log_info, log_error, log_debug, log_warning
from .human_behavior import AdvancedHumanBehavior, init_human_behavior, get_human_behavior
from .captcha_solver import solve_recaptcha_if_present, detect_recaptcha_on_page, RuCaptchaSolver, solve_recaptcha_if_present_sync

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

# Configure logging to suppress verbose Playwright logs
logging.getLogger('playwright').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logging.getLogger('websockets').setLevel(logging.CRITICAL)

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
    from bot.src.instagram_uploader.email import Email
except ImportError as e:
    print(f"Error importing required modules: {str(e)}. Make sure they're installed.")

# Setup logging
logger = logging.getLogger('uploader.bulk_tasks')

# Enhanced logging system for web interface
import json
from datetime import datetime
from django.core.cache import cache

class WebLogger:
    """Enhanced logger that sends logs to web interface in real-time"""
    
    def __init__(self, task_id, account_id=None):
        self.task_id = task_id
        self.account_id = account_id
        self.log_buffer = []
        
    def log(self, level, message, category=None):
        """Log message with enhanced formatting for web interface"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Check if message contains any verbose keywords
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in VerboseFilters.PLAYWRIGHT_VERBOSE_KEYWORDS):
            return  # Skip these verbose logs
        
        # Create formatted log entry
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'category': category or 'GENERAL'
        }
        
        # Add to buffer
        self.log_buffer.append(log_entry)
        
        # Store in cache for real-time updates
        cache_key = f"task_logs_{self.task_id}"
        if self.account_id:
            cache_key += f"_account_{self.account_id}"
            
        existing_logs = cache.get(cache_key, [])
        existing_logs.append(log_entry)
        
        # Keep only last 1000 log entries to prevent memory issues
        if len(existing_logs) > Limits.MAX_LOG_ENTRIES:
            existing_logs = existing_logs[-Limits.MAX_LOG_ENTRIES:]
            
        cache.set(cache_key, existing_logs, timeout=3600)
        
        # Also log to console for debugging (but filtered)
        if level in ['ERROR', 'WARNING', 'SUCCESS']:
            print(f"[{timestamp}] [{level}] {message}")

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

def get_email_verification_code(email_login, email_password):
    """Get verification code from email using the Email class with enhanced logging"""
    if not email_login or not email_password:
        log_warning("📧 Email credentials not provided for verification code retrieval")
        return None
        
    try:
        log_info(f"📧 [EMAIL_CODE] Starting email check for verification code")
        log_info(f"📧 [EMAIL_CODE] Email: {email_login}")
        
        email_client = Email(email_login, email_password)
        log_info(f"📧 [EMAIL_CODE] Email client initialized successfully")
        
        # First test the connection
        log_info(f"📧 [EMAIL_CODE] Testing email connection...")
        connection_test = email_client.test_connection()
        
        if not connection_test:
            log_error(f"📧 [EMAIL_CODE] ❌ Email connection test failed")
            log_error(f"📧 [EMAIL_CODE] Please check:")
            log_error(f"📧 [EMAIL_CODE] - Email address: {email_login}")
            log_error(f"📧 [EMAIL_CODE] - Password is correct")
            log_error(f"📧 [EMAIL_CODE] - Email provider supports IMAP/POP3")
            log_error(f"📧 [EMAIL_CODE] - Two-factor authentication is disabled for email")
            return None
        
        log_info(f"📧 [EMAIL_CODE] ✅ Email connection test successful")
        
        # Now try to get verification code
        verification_code = email_client.get_verification_code()
        
        if verification_code:
            log_info(f"📧 [EMAIL_CODE] ✅ Successfully retrieved email verification code: {verification_code}")
            return verification_code
        else:
            log_warning("📧 [EMAIL_CODE] ❌ No verification code found in email")
            log_warning("📧 [EMAIL_CODE] Possible reasons:")
            log_warning("📧 [EMAIL_CODE] - Email not received yet (try waiting)")
            log_warning("📧 [EMAIL_CODE] - Code is in a different email format")
            log_warning("📧 [EMAIL_CODE] - Email was already read/deleted")
            return None
            
    except Exception as e:
        log_error(f"📧 [EMAIL_CODE] ❌ Error getting email verification code: {str(e)}")
        return None

def navigate_to_upload_with_human_behavior(page):
    """Navigate to upload page with advanced human behavior - Optimized version"""
    try:
        # Initialize human behavior
        init_human_behavior(page)
        
        # Use the new InstagramNavigator class
        navigator = InstagramNavigator(page, get_human_behavior())
        return navigator.navigate_to_upload()
        
    except Exception as e:
        log_error(f"[UPLOAD] ❌ Navigation failed: {str(e)}")
        return False

def upload_video_with_human_behavior(page, video_file_path, video_obj):
    """Upload video with advanced human behavior - Optimized version"""
    try:
        log_info(f"[UPLOAD] 🎬 Starting advanced upload of: {os.path.basename(video_file_path)}")
        
        # Ensure human behavior is initialized
        human_behavior = get_human_behavior()
        if not human_behavior:
            init_human_behavior(page)
            human_behavior = get_human_behavior()
        
        # Use the new InstagramUploader class
        uploader = InstagramUploader(page, human_behavior)
        return uploader.upload_video(video_file_path, video_obj)
        
    except Exception as e:
        log_error(f"[UPLOAD] ❌ Upload failed: {str(e)}")
        return False

def handle_location_and_mentions_advanced(page, video_obj):
    """Handle location and mentions with advanced human behavior"""
    try:
        # Get human behavior instance
        human_behavior = get_human_behavior()
        if not human_behavior:
            log_warning("[UPLOAD] Human behavior not initialized, skipping location and mentions")
            return
        
        # Debug: log video object information
        log_info(f"[UPLOAD] 🔍 Debug: video_obj type: {type(video_obj)}")
        log_info(f"[UPLOAD] 🔍 Debug: video_obj attributes: {dir(video_obj)}")
        if hasattr(video_obj, 'id'):
            log_info(f"[UPLOAD] 🔍 Debug: video_obj.id: {video_obj.id}")
        
        # Handle location with advanced behavior - use get_effective_location() method if available
        location = None
        if hasattr(video_obj, 'get_effective_location'):
            location = video_obj.get_effective_location()
            log_info(f"[UPLOAD] 🔍 Debug: get_effective_location() returned: '{location}'")
        else:
            location = getattr(video_obj, 'location', None)
            log_info(f"[UPLOAD] 🔍 Debug: direct location attribute: '{location}'")
            
        if location and location.strip():  # Only use location if explicitly set and not empty
            log_info(f"[UPLOAD] 📍 Setting location with advanced behavior: {location}")
            
            location_field = None
            for selector in InstagramSelectors.LOCATION_FIELDS:
                try:
                    if selector.startswith('//'):
                        location_field = page.query_selector(f"xpath={selector}")
                    else:
                        location_field = page.query_selector(selector)
                    
                    if location_field and location_field.is_visible():
                        log_info(f"[UPLOAD] ✅ Found location field with selector: {selector}")
                        break
                        
                except Exception as e:
                    log_warning(f"[UPLOAD] Error with location selector {selector}: {str(e)}")
                    continue
            
            if location_field:
                human_behavior.advanced_element_interaction(location_field, 'click')
                human_behavior.human_typing(location_field, location, simulate_mistakes=False)
                
                # Wait for suggestions with human behavior - increased time
                suggestion_wait = human_behavior.get_human_delay(3.0, 1.0)  # Increased from 2.0, 0.5
                log_info(f"[UPLOAD] ⏳ Waiting {suggestion_wait:.1f}s for location suggestions...")
                time.sleep(suggestion_wait)
                
                # Click first suggestion with comprehensive selectors
                for selector in InstagramSelectors.LOCATION_SUGGESTIONS:
                    try:
                        if selector.startswith('//'):
                            first_suggestion = page.query_selector(f"xpath={selector}")
                        else:
                            first_suggestion = page.query_selector(selector)
                        
                        if first_suggestion and first_suggestion.is_visible():
                            log_info(f"[UPLOAD] ✅ Clicking location suggestion")
                            human_behavior.advanced_element_interaction(first_suggestion, 'click')
                            break
                            
                    except Exception as e:
                        continue
            else:
                log_warning("[UPLOAD] ⚠️ Location field not found")
        else:
            log_info("[UPLOAD] 📍 No location specified for this video, skipping location setting")
        
        # Handle mentions with advanced behavior - use get_effective_mentions_list() method if available
        mentions_list = []
        if hasattr(video_obj, 'get_effective_mentions_list'):
            mentions_list = video_obj.get_effective_mentions_list()
            log_info(f"[UPLOAD] 🔍 Debug: get_effective_mentions_list() returned: {mentions_list}")
        else:
            mentions = getattr(video_obj, 'mentions', None)
            log_info(f"[UPLOAD] 🔍 Debug: direct mentions attribute: '{mentions}'")
            if mentions and mentions.strip():
                mentions_list = [mention.strip() for mention in mentions.split('\n') if mention.strip()]
                log_info(f"[UPLOAD] 🔍 Debug: parsed mentions_list: {mentions_list}")
            
        if mentions_list and len(mentions_list) > 0:
            log_info(f"[UPLOAD] 👥 Setting {len(mentions_list)} mentions with advanced behavior...")
            
            for mention_index, mention in enumerate(mentions_list):
                if not mention.strip():  # Skip empty mentions
                    continue
                
                # Add pause between mentions processing (except for the first one)
                if mention_index > 0:
                    mention_pause = random.uniform(2, 4)
                    log_info(f"[UPLOAD] ⏳ Pause between mentions processing: {mention_pause:.1f}s...")
                    time.sleep(mention_pause)
                
                log_info(f"[UPLOAD] 👤 Processing mention {mention_index + 1}/{len(mentions_list)}: {mention}")
                    
                mention_field = None
                for selector in InstagramSelectors.MENTION_FIELDS:
                    try:
                        if selector.startswith('//'):
                            mention_field = page.query_selector(f"xpath={selector}")
                        else:
                            mention_field = page.query_selector(selector)
                        
                        if mention_field and mention_field.is_visible():
                            log_info(f"[UPLOAD] ✅ Found mention field with selector: {selector}")
                            break
                            
                    except Exception as e:
                        log_warning(f"[UPLOAD] Error with mention selector {selector}: {str(e)}")
                        continue
                
                if mention_field:
                    human_behavior.advanced_element_interaction(mention_field, 'click')
                    human_behavior.human_typing(mention_field, mention, simulate_mistakes=False)
                    
                    # Wait and select first suggestion - increased time
                    suggestion_wait = human_behavior.get_human_delay(3.0, 1.0)  # Increased from 2.0, 0.5
                    log_info(f"[UPLOAD] ⏳ Waiting {suggestion_wait:.1f}s for mention suggestions...")
                    time.sleep(suggestion_wait)
                    
                    # Click first mention suggestion
                    for selector in InstagramSelectors.MENTION_SUGGESTIONS:
                        try:
                            if selector.startswith('//'):
                                first_mention = page.query_selector(f"xpath={selector}")
                            else:
                                first_mention = page.query_selector(selector)
                            
                            if first_mention and first_mention.is_visible():
                                log_info(f"[UPLOAD] ✅ Clicking mention suggestion for: {mention}")
                                human_behavior.advanced_element_interaction(first_mention, 'click')
                                break
                                
                        except Exception as e:
                            continue
                else:
                    log_warning(f"[UPLOAD] ⚠️ Mention field not found for: {mention}")
            
            # Click done button with comprehensive selectors
            for selector in InstagramSelectors.DONE_BUTTONS:
                try:
                    if selector.startswith('//'):
                        done_button = page.query_selector(f"xpath={selector}")
                    else:
                        done_button = page.query_selector(selector)
                    
                    if done_button and done_button.is_visible():
                        log_info(f"[UPLOAD] ✅ Clicking done button for mentions")
                        human_behavior.advanced_element_interaction(done_button, 'click')
                        break
                        
                except Exception as e:
                    continue
        else:
            log_info("[UPLOAD] 👥 No mentions specified for this video, skipping mentions setting")
        
    except Exception as e:
        log_error(f"[UPLOAD] ❌ Error handling location and mentions: {str(e)}")
        import traceback
        log_error(f"[UPLOAD] Stack trace: {traceback.format_exc()}")

def click_next_button(page, step_number):
    """Click next button with human-like behavior (like Selenium version)"""
    try:
        log_info(f"[UPLOAD] Clicking next button for step {step_number}...")
        
        # Human-like delay before clicking
        time.sleep(random.uniform(2, 4))
        
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
                        log_info(f"[UPLOAD] ✅ Found next button for step {step_number}: '{button_text.strip()}' with selector: {selector}")
                        used_selector = selector
                        break
                    elif selector.startswith('div[class*="x1i10hfl"]') and button_text.strip():
                        # For Instagram-specific selectors, if we find a button with any text, it might be the next button
                        log_info(f"[UPLOAD] 🎯 Found potential Instagram next button: '{button_text.strip()}' with selector: {selector}")
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
                time.sleep(random.uniform(0.5, 1.0))
                
                # Hover over button
                next_button.hover()
                time.sleep(random.uniform(0.5, 1.0))
                
                # Use JavaScript click like Selenium version for better reliability
                page.evaluate('arguments[0].click()', next_button)
                
                # Wait after click
                time.sleep(random.uniform(2, 3))
                
                log_info(f"[UPLOAD] ✅ Successfully clicked next button for step {step_number}")
                return True
                
            except Exception as click_error:
                log_warning(f"[UPLOAD] ⚠️ Error clicking next button: {str(click_error)}")
                
                # Fallback: try direct click
                try:
                    next_button.click()
                    time.sleep(random.uniform(2, 3))
                    log_info(f"[UPLOAD] ✅ Successfully clicked next button (fallback) for step {step_number}")
                    return True
                except Exception as fallback_error:
                    log_error(f"[UPLOAD] ❌ Fallback click also failed: {str(fallback_error)}")
                    return False
        else:
            log_warning(f"[UPLOAD] ⚠️ Next button not found for step {step_number}")
            
            # Debug: log available buttons with Instagram-specific classes
            try:
                all_buttons = page.query_selector_all('button, div[role="button"], div[class*="x1i10hfl"], div[tabindex="0"]')
                log_info(f"[UPLOAD] 🔍 Available clickable elements on page for step {step_number}:")
                for i, btn in enumerate(all_buttons[:15]):  # Show first 15 elements
                    try:
                        btn_text = btn.text_content() or "no-text"
                        btn_aria = btn.get_attribute('aria-label') or "no-aria"
                        btn_role = btn.get_attribute('role') or "no-role"
                        btn_classes = btn.get_attribute('class') or "no-classes"
                        
                        # Show only elements that might be buttons
                        if btn_text.strip() or btn_role == "button" or "x1i10hfl" in btn_classes:
                            log_info(f"[UPLOAD] Element {i+1}: '{btn_text.strip()}' (role: '{btn_role}', aria: '{btn_aria}', classes: '{btn_classes[:50]}...')")
                    except Exception as debug_error:
                        log_warning(f"[UPLOAD] Error debugging element {i+1}: {str(debug_error)}")
                        continue
            except Exception as e:
                log_warning(f"[UPLOAD] Could not debug buttons: {str(e)}")
            
            return False
            
    except Exception as e:
        log_error(f"[UPLOAD] ❌ Error clicking next button for step {step_number}: {str(e)}")
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
    """Detect email verification page and auto-fill email field"""
    if not email_login:
        log_warning("📧 [EMAIL_FIELD] No email login provided")
        return False
        
    try:
        log_info(f"📧 [EMAIL_FIELD] Starting email field detection for: {email_login}")
        
        # Get page content for analysis
        try:
            page_text = page.inner_text('body') or ""
        except Exception:
            page_text = ""
        
        # Check if this is email verification page
        is_email_verification = any(keyword in page_text.lower() for keyword in InstagramTexts.EMAIL_VERIFICATION_KEYWORDS)
        is_code_entry = any(keyword in page_text.lower() for keyword in InstagramTexts.CODE_ENTRY_KEYWORDS)
        
        log_info(f"📧 [EMAIL_FIELD] Email verification: {is_email_verification}, Code entry: {is_code_entry}")
        
        if is_code_entry:
            log_info("📧 [EMAIL_FIELD] Code entry page detected - skipping email fill")
            return False
        
        if not is_code_entry and is_email_verification:
            email_field = _find_element(page, InstagramSelectors.EMAIL_FIELDS)
            
            if email_field and email_field.is_visible():
                current_value = email_field.input_value() or ""
                
                if current_value.strip() == email_login.strip():
                    log_info(f"📧 [EMAIL_FIELD] ✅ Email field already contains correct email")
                    return True
                
                # Fill email with human-like behavior
                email_field.click()
                time.sleep(random.uniform(0.5, 1.0))
                
                if current_value:
                    email_field.fill('')
                    time.sleep(random.uniform(0.3, 0.7))
                
                for char in email_login:
                    email_field.type(char)
                    time.sleep(random.uniform(0.1, 0.2))
                
                time.sleep(random.uniform(0.5, 1.0))
                final_value = email_field.input_value() or ""
                
                if final_value.strip() == email_login.strip():
                    log_info(f"📧 [EMAIL_FIELD] ✅ Successfully filled email field")
                    return True
                else:
                    log_error(f"📧 [EMAIL_FIELD] ❌ Email field fill verification failed")
                    return False
            else:
                log_warning(f"📧 [EMAIL_FIELD] ❌ No visible email field found")
                return False
        else:
            log_info(f"📧 [EMAIL_FIELD] Skipping email field fill")
            return False
            
    except Exception as e:
        log_error(f"📧 [EMAIL_FIELD] ❌ Error in email field detection: {str(e)}")
        return False

def find_submit_button(page):
    """Find submit button using stable selectors"""
    try:
        log_info("🔍 [SUBMIT_BTN] Looking for submit button...")
        
        button = _find_element(page, InstagramSelectors.SUBMIT_BUTTONS)
        if button:
            button_text = button.text_content() or 'no-text'
            button_type = button.get_attribute('type') or 'unknown'
            log_info(f"✅ [SUBMIT_BTN] Found submit button: '{button_text.strip()}' (type: {button_type})")
            return button
        
        log_warning("❌ [SUBMIT_BTN] No submit button found")
        return None
        
    except Exception as e:
        log_error(f"❌ [SUBMIT_BTN] Error in submit button detection: {str(e)}")
        return None

def find_verification_code_input(page):
    """Find verification code input field"""
    try:
        log_info("🔍 [CODE_INPUT] Looking for verification code input field...")
        time.sleep(random.uniform(1, 2))
        
        try:
            page_text = page.inner_text('body') or ""
        except Exception:
            page_text = ""
            
        is_verification_page = any(keyword in page_text.lower() for keyword in InstagramTexts.VERIFICATION_PAGE_KEYWORDS)
        
        log_info(f"🔍 [CODE_INPUT] Verification page detected: {is_verification_page}")
        
        if is_verification_page:
            input_field = _find_element(page, InstagramSelectors.VERIFICATION_CODE_FIELDS)
            if input_field:
                field_name = input_field.get_attribute('name') or 'unknown'
                field_type = input_field.get_attribute('type') or 'unknown'
                log_info(f"✅ [CODE_INPUT] Found input field: name={field_name}, type={field_type}")
                return input_field
        else:
            input_field = _find_element(page, InstagramSelectors.VERIFICATION_CODE_FIELDS_RESTRICTIVE)
            if input_field:
                return input_field
        
        log_warning("❌ [CODE_INPUT] No verification code input found")
        return None
        
    except Exception as e:
        log_error(f"❌ [CODE_INPUT] Error in code input detection: {str(e)}")
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
                    log_info(f"[SAVE_LOGIN] ✅ Found save button: '{button_text.strip()}'")
                    
                    try:
                        save_button.hover()
                        time.sleep(random.uniform(0.5, 1.0))
                        save_button.click()
                        time.sleep(random.uniform(2, 4))
                        log_info("[SAVE_LOGIN] ✅ Successfully clicked save login info button")
                        return True
                    except Exception as e:
                        log_error(f"[SAVE_LOGIN] ❌ Error clicking save button: {str(e)}")
            
            # If no save button, look for "Not now" button
            log_warning("[SAVE_LOGIN] ⚠️ Could not find save button, looking for 'Not now' button...")
            not_now_button = _find_element(page, InstagramSelectors.NOT_NOW_BUTTONS)
            
            if not_now_button and not_now_button.is_visible():
                log_info(f"[SAVE_LOGIN] Found 'Not now' button, dismissing dialog...")
                not_now_button.hover()
                time.sleep(random.uniform(0.5, 1.0))
                not_now_button.click()
                time.sleep(random.uniform(2, 4))
                log_info("[SAVE_LOGIN] ✅ Dismissed save login dialog with 'Not now'")
                return True
            
            log_warning("[SAVE_LOGIN] ⚠️ Could not find any button to handle save login dialog")
            return False
        else:
            log_info("[SAVE_LOGIN] No save login info dialog found")
            return True
            
    except Exception as e:
        log_error(f"[SAVE_LOGIN] ❌ Error handling save login dialog: {str(e)}")
        return False

def check_video_posted_successfully(page, video_file_path):
    """Check if video was posted successfully"""
    try:
        log_info("[UPLOAD] Checking if video was posted successfully...")
        time.sleep(random.uniform(5, 8))
        
        # Check for success indicators
        success_element = _find_element(page, InstagramSelectors.SUCCESS_INDICATORS)
        if success_element:
            element_text = success_element.text_content() or ""
            log_info(f"[UPLOAD] ✅ Success indicator found: '{element_text.strip()}'")
            log_info(f"[UPLOAD] ✅ Video {os.path.basename(video_file_path)} successfully posted")
            return True
        
        # Check if we're no longer on upload page
        log_info("[UPLOAD] No explicit success message found, checking upload page status...")
        
        upload_element = _find_element(page, InstagramSelectors.UPLOAD_PAGE_INDICATORS)
        if not upload_element:
            log_info(f"[UPLOAD] ✅ No upload page indicators found - video {os.path.basename(video_file_path)} posted successfully")
            return True
        else:
            log_warning(f"[UPLOAD] ⚠️ Still on upload page - video {os.path.basename(video_file_path)} may not have been posted")
            
            # Check for error messages
            error_element = _find_element(page, InstagramSelectors.ERROR_INDICATORS)
            if error_element:
                error_text = error_element.text_content() or ""
                log_error(f"[UPLOAD] ❌ Error message found: '{error_text.strip()}'")
                return False
            else:
                log_info(f"[UPLOAD] ⏳ No error messages found, video might still be processing...")
                return True
                
    except Exception as e:
        log_error(f"[UPLOAD] Error checking if video was posted: {str(e)}")
        return False

def handle_success_dialog_and_close(page, video_file_path):
    """Handle success dialog after video posting and close it naturally"""
    try:
        log_info("[SUCCESS] 🎉 Handling success dialog after video posting...")
        
        # Wait for video processing and success dialog
        initial_wait = random.uniform(20, 30)
        log_info(f"[SUCCESS] ⏳ Waiting {initial_wait:.1f}s for video processing and success dialog...")
        time.sleep(initial_wait)
        
        # Look for success dialog
        success_dialog = _find_element(page, InstagramSelectors.SUCCESS_DIALOGS)
        found_success_message = bool(success_dialog)
        
        if found_success_message:
            element_text = success_dialog.text_content() or ""
            log_info(f"[SUCCESS] ✅ Found success message: '{element_text.strip()}'")
            
            # Human reaction to success
            reaction_time = random.uniform(2, 4)
            log_info(f"[SUCCESS] 😊 Reading success message for {reaction_time:.1f}s...")
            time.sleep(reaction_time)
            
            # Look for close button
            close_button = _find_element(page, InstagramSelectors.CLOSE_BUTTONS)
            
            if close_button:
                try:
                    bounding_box = close_button.bounding_box()
                    if bounding_box:
                        log_info(f"[SUCCESS] 🎯 Found close button")
                        
                        time.sleep(random.uniform(1, 2))
                        human_behavior = get_human_behavior()
                        if human_behavior:
                            human_behavior.advanced_element_interaction(close_button, 'click')
                        else:
                            close_button.click()
                        
                        close_wait = random.uniform(1.5, 3)
                        log_info(f"[SUCCESS] ⏳ Waiting {close_wait:.1f}s for dialog to close...")
                        time.sleep(close_wait)
                        log_info("[SUCCESS] ✅ Success dialog closed successfully!")
                        
                except Exception as e:
                    log_warning(f"[SUCCESS] Error getting close button details: {str(e)}")
            
            if not close_button:
                # Try alternative methods
                log_info("[SUCCESS] 🔍 No close button found, trying alternative methods...")
                
                try:
                    log_info("[SUCCESS] ⌨️ Trying Escape key...")
                    page.keyboard.press('Escape')
                    time.sleep(random.uniform(1, 2))
                except Exception as e:
                    log_warning(f"[SUCCESS] ⚠️ Escape key failed: {str(e)}")
                
                try:
                    log_info("[SUCCESS] 🖱️ Trying to click outside dialog...")
                    page.mouse.click(50, 50)
                    time.sleep(random.uniform(1, 2))
                except Exception as e:
                    log_warning(f"[SUCCESS] ⚠️ Click outside failed: {str(e)}")
        else:
            log_info("[SUCCESS] ℹ️ No explicit success dialog found, checking main interface...")
            
            # Check if back to main interface
            main_element = _find_element(page, InstagramSelectors.MAIN_INTERFACE_INDICATORS)
            if main_element:
                log_info(f"[SUCCESS] ✅ Back to main interface - video likely posted successfully")
                return True
        
        # Final verification
        upload_element = _find_element(page, InstagramSelectors.UPLOAD_PAGE_INDICATORS)
        if not upload_element:
            log_info(f"[SUCCESS] ✅ Video {os.path.basename(video_file_path)} posted successfully!")
            return True
        else:
            log_warning(f"[SUCCESS] ⚠️ Still on upload page - video may not have posted")
            return False
            
    except Exception as e:
        log_error(f"[SUCCESS] ❌ Error handling success dialog: {str(e)}")
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
            log_info(f"[EXTENDED_REST] 🎯 Activity {activity_count}: {activity} for {activity_duration:.1f}s")
            
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
        
        log_info(f"[EXTENDED_REST] ✅ Extended rest period completed after {activity_count} activities")
        
    except Exception as e:
        log_warning(f"[EXTENDED_REST] Error during extended rest: {str(e)}")
        # Fallback to simple sleep
        time.sleep(total_duration)

def run_bulk_upload_task(task_id):
    """Optimized bulk upload task runner with modular architecture"""
    # Initialize web logger for real-time log updates
    init_web_logger(task_id)
    
    log_info(f"Starting bulk upload task with ID: {task_id}", LogCategories.TASK_START)
    task = get_task_with_accounts(task_id)
    
    try:
        # Update task status with colorful emojis for better visibility in logs
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        log_info(f"Task name: {task.name}", LogCategories.TASK_INFO)
        update_task_log(task, f"[{timestamp}] 🚀 Starting bulk upload task '{task.name}'\n")
        
        # Get all account tasks
        account_tasks = get_account_tasks(task)
        
        log_info(f"Found {len(account_tasks)} accounts to process")
        update_task_log(task, f"[{timestamp}] 👥 Found {len(account_tasks)} accounts to process\n")
        
        completed_count = 0
        failed_count = 0
        
        for account_index, account_task in enumerate(account_tasks):
            try:
                # Check account status before processing
                account = get_account_from_task(account_task)
                username = get_account_username(account_task)
                
                # Skip non-active accounts
                if account.status != 'ACTIVE':
                    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_warning(f"Skipping account {username} - Status: {account.status} (Only ACTIVE accounts are processed)")
                    update_account_task(
                        account_task,
                        status=TaskStatus.FAILED,
                        completed_at=timezone.now(),
                        log_message=f"[{timestamp}] ⚠️ Account skipped - Status: {account.status} (Only ACTIVE accounts allowed for bulk upload)\n"
                    )
                    failed_count += 1
                    continue
                
                # Add human-like delay between accounts (except first one)
                if account_index > 0:
                    account_delay = random.uniform(TimeConstants.ACCOUNT_DELAY_MIN, TimeConstants.ACCOUNT_DELAY_MAX)
                    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_info(f"Waiting {account_delay:.1f} seconds before processing next account (human behavior)")
                    update_task_log(task, f"[{timestamp}] ⏰ Waiting {account_delay:.1f}s between accounts for human behavior\n")
                    time.sleep(account_delay)
                
                # Mark as running
                timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                log_info(f"Starting upload for account: {username}")
                update_account_task(
                    account_task,
                    status=TaskStatus.RUNNING,
                    started_at=timezone.now(),
                    log_message=f"[{timestamp}] 🔄 Starting upload for account: {username}\n"
                )
                
                # Get ALL videos from the task for random distribution
                all_videos = get_all_task_videos(task)
                all_titles = get_all_task_titles(task)
                
                if not all_videos:
                    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_info(f"No videos found in task for account: {username}")
                    update_account_task(
                        account_task,
                        status=TaskStatus.COMPLETED,
                        completed_at=timezone.now(),
                        log_message=f"[{timestamp}] ⚠️ No videos in task to upload\n"
                    )
                    completed_count += 1
                    continue
                
                # Process account with optimized logic
                result_type, completed_inc, failed_inc = process_account_videos(
                    account_task, task, all_videos, all_titles, task_id
                )
                
                completed_count += completed_inc
                failed_count += failed_inc
                
                # Mark account as used
                account = get_account_from_task(account_task)
                mark_account_as_used(account)
                
            except Exception as e:
                handle_account_task_error(account_task, task, e)
                failed_count += 1
        
        # Update main task status based on individual tasks
        handle_task_completion(task, completed_count, failed_count, len(account_tasks))
        
    except Exception as e:
        handle_critical_task_error(task, task_id, e)
        logger.error(f"Error processing bulk upload task {task_id}: {str(e)}")

def process_account_videos(account_task, task, all_videos, all_titles, task_id):
    """Process videos for a single account"""
    # Convert QuerySet to list and randomize videos and titles
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
            log_message=f"[{timestamp}] ❌ No valid video files to upload\n"
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
    """Prepare video files for upload"""
    temp_files = []
    video_files_to_upload = []
    
    for video in videos_for_account:
        video_filename = os.path.basename(video.video_file.name)
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        log_info(f"Preparing video: {video_filename}")
        update_account_task(
            account_task,
            log_message=f"[{timestamp}] 📋 Preparing video: {video_filename}\n"
        )
        
        try:
            with NamedTemporaryFile(delete=False, suffix=f"_{video_filename}") as tmp:
                log_debug(f"Creating temporary file: {tmp.name}")
                for chunk in video.video_file.chunks():
                    tmp.write(chunk)
                temp_files.append(tmp.name)
                video_files_to_upload.append(tmp.name)
                
                timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                log_info(f"Saved video to temporary file: {tmp.name}")
                update_account_task(
                    account_task,
                    log_message=f"[{timestamp}] ✅ Saved video to temporary file\n"
                )
        except Exception as e:
            log_error(f"Error creating temporary file for {video_filename}: {str(e)}")
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            update_account_task(
                account_task,
                log_message=f"[{timestamp}] ❌ Error creating temporary file: {str(e)}\n"
            )
    
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
    """Optimized Dolphin browser runner"""
    dolphin = None
    dolphin_browser = None
    page = None
    dolphin_profile_id = None
    
    try:
        init_web_logger(task_id, account_task_id)
        
        username = account_details['username']
        log_info(f"Starting Dolphin Anty browser for account: {username}", LogCategories.DOLPHIN)
        
        # Initialize Dolphin
        dolphin_token = os.environ.get("DOLPHIN_API_TOKEN")
        if not dolphin_token:
            log_error("No Dolphin API token found", LogCategories.DOLPHIN)
            result_queue.put(("DOLPHIN_ERROR", "Dolphin API token not configured"))
            return
            
        from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
        from bot.src.instagram_uploader.browser_dolphin import DolphinBrowser
        
        dolphin = DolphinAnty(api_key=dolphin_token)
        
        # Authenticate
        if not authenticate_dolphin(dolphin):
            result_queue.put(("DOLPHIN_ERROR", "Failed to authenticate with Dolphin Anty API"))
            return
        
        # Get profile
        dolphin_profile_id = get_dolphin_profile_id(username)
        if not dolphin_profile_id:
            result_queue.put(("PROFILE_ERROR", f"No Dolphin profile found for account: {username}"))
            return
        
        # Connect to browser
        dolphin_browser = DolphinBrowser(dolphin_api_token=dolphin_token)
        page = dolphin_browser.connect_to_profile(dolphin_profile_id, headless=False)
        
        if not page:
            result_queue.put(("PROFILE_ERROR", f"Profile {dolphin_profile_id} is not available"))
            return
        
        log_success(f"Successfully connected to Dolphin profile: {dolphin_profile_id}", LogCategories.DOLPHIN)
        
        # Perform Instagram operations
        if not perform_instagram_operations(page, account_details, videos, video_files_to_upload):
            result_queue.put(("LOGIN_ERROR", "Failed Instagram operations"))
            return
        
        # Success
        uploaded_count = len([v for v in videos if getattr(v, 'uploaded', False)])
        success_message = f"Uploaded {uploaded_count}/{len(video_files_to_upload)} videos successfully"
        log_info(f"[COMPLETE] {success_message}")
        result_queue.put(("SUCCESS", success_message))
        
    except Exception as e:
        error_message = str(e)
        
        # Handle specific verification errors
        if "PHONE_VERIFICATION_REQUIRED" in error_message:
            log_error(f"📱 Phone verification required for account: {username}", LogCategories.VERIFICATION)
            result_queue.put(("PHONE_VERIFICATION_REQUIRED", f"Phone verification required for account: {username}"))
            
            # Update Instagram account status in database
            try:
                from .models import InstagramAccount
                instagram_account = InstagramAccount.objects.get(username=username)
                instagram_account.status = TaskStatus.PHONE_VERIFICATION_REQUIRED
                instagram_account.save()
                log_info(f"Updated account {username} status to PHONE_VERIFICATION_REQUIRED", LogCategories.DATABASE)
            except Exception as db_error:
                log_error(f"Failed to update account status in database: {str(db_error)}", LogCategories.DATABASE)
                
        elif "HUMAN_VERIFICATION_REQUIRED" in error_message:
            log_error(f"🤖 Human verification required for account: {username}", LogCategories.VERIFICATION)
            result_queue.put(("HUMAN_VERIFICATION_REQUIRED", f"Human verification required for account: {username}"))
            
            # Update Instagram account status in database
            try:
                from .models import InstagramAccount
                instagram_account = InstagramAccount.objects.get(username=username)
                instagram_account.status = TaskStatus.HUMAN_VERIFICATION_REQUIRED
                instagram_account.save()
                log_info(f"Updated account {username} status to HUMAN_VERIFICATION_REQUIRED", LogCategories.DATABASE)
            except Exception as db_error:
                log_error(f"Failed to update account status in database: {str(db_error)}", LogCategories.DATABASE)
                
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
    """Perform all Instagram operations"""
    try:
        # Navigate to Instagram
        log_info(f"Navigating to Instagram.com", LogCategories.NAVIGATION)
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=TimeConstants.PAGE_LOAD_TIMEOUT)
        log_success(f"Successfully loaded Instagram.com", LogCategories.NAVIGATION)
        
        # Initialize human behavior
        init_human_behavior(page)
        human_behavior = get_human_behavior()
        
        # Human-like delay
        human_delay = human_behavior.get_human_delay(2.0, 1.0)
        log_info(f"Taking a moment to look at the page ({human_delay:.1f}s)", LogCategories.HUMAN)
        time.sleep(human_delay)
        
        # Check for phone verification requirement immediately after page load
        log_info("🔍 Checking for phone verification requirement...", LogCategories.VERIFICATION)
        if check_for_phone_verification_page(page):
            raise Exception("PHONE_VERIFICATION_REQUIRED")
        
        # Check login status and login if needed
        if not handle_login_flow(page, account_details):
            return False
        
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
        return True
        
    except Exception as e:
        error_message = str(e)
        if "PHONE_VERIFICATION_REQUIRED" in error_message:
            log_error(f"Phone verification required: {error_message}", LogCategories.VERIFICATION)
            raise e  # Re-raise to be caught by run_dolphin_browser
        elif "HUMAN_VERIFICATION_REQUIRED" in error_message:
            log_error(f"Human verification required: {error_message}", LogCategories.VERIFICATION)
            raise e  # Re-raise to be caught by run_dolphin_browser
        else:
            log_error(f"Error in Instagram operations: {error_message}")
            return False

def cleanup_browser_session(page, dolphin_browser, dolphin_profile_id, dolphin):
    """Clean up browser session safely"""
    try:
        log_info("[CLEANUP] Starting comprehensive browser cleanup")
        if page and dolphin_browser:
            BrowserManager.safely_close_browser(page, dolphin_browser, dolphin_profile_id)
            log_info("[CLEANUP] ✅ Browser cleanup completed successfully")
        else:
            log_info("[CLEANUP] Browser objects not initialized, skipping cleanup")
    except Exception as cleanup_error:
        log_error(f"[CLEANUP] Emergency cleanup failed: {str(cleanup_error)}")

def handle_login_flow(page, account_details):
    """Handle the complete login flow with verification checks"""
    try:
        # Check for human verification dialog first
        if check_for_human_verification_dialog(page, account_details):
            log_error("Human verification dialog detected", LogCategories.LOGIN)
            raise Exception("HUMAN_VERIFICATION_REQUIRED")
        
        # Check for phone verification requirement
        if check_for_phone_verification_page(page):
            log_error("Phone verification requirement detected in login flow", LogCategories.VERIFICATION)
            raise Exception("PHONE_VERIFICATION_REQUIRED")
        
        # Look for login indicators
        login_form = page.query_selector('form[id*="loginForm"]')
        username_input = page.query_selector('input[name="username"]')
        logged_in_indicator = page.query_selector('svg[aria-label*="Home"]') or page.query_selector('[aria-label*="Home"]')
        
        if logged_in_indicator and not username_input:
            log_success("Already logged in to Instagram", LogCategories.LOGIN)
            
            # Check again for verification dialogs after login
            if check_for_human_verification_dialog(page, account_details):
                log_error("Human verification dialog detected after login check", LogCategories.LOGIN)
                raise Exception("HUMAN_VERIFICATION_REQUIRED")
                
            if check_for_phone_verification_page(page):
                log_error("Phone verification requirement detected after login check", LogCategories.VERIFICATION)
                raise Exception("PHONE_VERIFICATION_REQUIRED")
                
            return True
        else:
            log_info("Need to login to Instagram", LogCategories.LOGIN)
            
            # Perform login
            success = perform_instagram_login(page, account_details)
            if not success:
                log_error("Failed to login to Instagram", LogCategories.LOGIN)
                return False
            
            log_success("Successfully logged in to Instagram", LogCategories.LOGIN)
            return True
            
    except Exception as e:
        error_message = str(e)
        if "PHONE_VERIFICATION_REQUIRED" not in error_message and "HUMAN_VERIFICATION_REQUIRED" not in error_message:
            # Check for verification requirements after failed login
            if check_for_phone_verification_page(page):
                log_error("Phone verification requirement detected after failed login", LogCategories.VERIFICATION)
                raise Exception("PHONE_VERIFICATION_REQUIRED")
        
        log_error(f"[LOGIN] Login process failed: {str(e)}")
        
        # Re-raise verification exceptions
        if "PHONE_VERIFICATION_REQUIRED" in error_message or "HUMAN_VERIFICATION_REQUIRED" in error_message:
            raise e
            
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

def add_human_delay_between_uploads(page, video_index):
    """Add human-like delay between video uploads"""
    # Calculate delay with fatigue simulation
    base_delay = random.uniform(TimeConstants.VIDEO_DELAY_MIN, TimeConstants.VIDEO_DELAY_MAX)
    fatigue_multiplier = 1 + (video_index * 0.1)  # 10% more delay per video
    total_delay = base_delay * fatigue_multiplier
    variance = random.uniform(0.8, 1.3)
    final_delay = min(total_delay * variance, 900)  # Cap at 15 minutes
    
    log_info(f"[HUMAN_BREAK] Extended break between uploads: {final_delay:.1f}s ({final_delay/60:.1f} minutes)")
    log_info(f"[HUMAN_BREAK] Video {video_index} fatigue factor: {fatigue_multiplier:.2f}x")
    
    simulate_extended_human_rest_behavior(page, final_delay)

def perform_final_cleanup(page, username):
    """Perform final cleanup and browsing simulation"""
    # Take final screenshot
    screenshot_path = f"instagram_final_{username}.png"
    log_info(f"Taking final screenshot: {screenshot_path}")
    page.screenshot(path=screenshot_path)
    log_info(f"Saved final screenshot to {screenshot_path}")

    # Human-like browsing before closing
    log_info("Simulating normal browsing behavior")
    simulate_normal_browsing_behavior(page)

def perform_instagram_login(page, account_details):
    """Wrapper function for login with reCAPTCHA handling"""
    try:
        # Check for human verification dialog first
        if check_for_human_verification_dialog(page, account_details):
            log_error("Human verification dialog detected", LogCategories.LOGIN)
            raise Exception("HUMAN_VERIFICATION_REQUIRED")
        
        # Check for phone verification before login
        if check_for_phone_verification_page(page):
            log_error("Phone verification requirement detected before login", LogCategories.VERIFICATION)
            raise Exception("PHONE_VERIFICATION_REQUIRED")
        
        # Check for reCAPTCHA and solve it
        log_info("🔍 Checking for reCAPTCHA on login page...", LogCategories.CAPTCHA)
        captcha_solved = solve_recaptcha_if_present_sync(page, account_details)
        
        if not captcha_solved:
            log_error("❌ Failed to solve reCAPTCHA on login page", LogCategories.CAPTCHA)
        else:
            log_success("✅ reCAPTCHA handling completed", LogCategories.CAPTCHA)
        
        # Use optimized login function
        result = perform_instagram_login_optimized(page, account_details)
        
        # Check for phone verification after login attempt
        if check_for_phone_verification_page(page):
            log_error("Phone verification requirement detected after login", LogCategories.VERIFICATION)
            raise Exception("PHONE_VERIFICATION_REQUIRED")
        
        # Check again after login
        if check_for_human_verification_dialog(page, account_details):
            log_error("Human verification dialog detected after login", LogCategories.LOGIN)
            raise Exception("HUMAN_VERIFICATION_REQUIRED")
        
        # Final check for post-login captcha
        log_info("🔍 Checking for post-login reCAPTCHA...", LogCategories.CAPTCHA)
        solve_recaptcha_if_present_sync(page, account_details)
        
        return result
        
    except Exception as e:
        error_message = str(e)
        
        # Before returning False, check if it's a verification issue
        if "PHONE_VERIFICATION_REQUIRED" not in error_message and "HUMAN_VERIFICATION_REQUIRED" not in error_message:
            # Check for verification requirements after failed login
            if check_for_phone_verification_page(page):
                log_error("Phone verification requirement detected after failed login", LogCategories.VERIFICATION)
                raise Exception("PHONE_VERIFICATION_REQUIRED")
        
        log_error(f"[LOGIN] Login process failed: {str(e)}")
        
        # Re-raise verification exceptions
        if "PHONE_VERIFICATION_REQUIRED" in error_message or "HUMAN_VERIFICATION_REQUIRED" in error_message:
            raise e
            
        return False

def check_for_phone_verification_page(page):
    """Check if Instagram is showing phone verification page"""
    try:
        log_info("🔍 Checking for phone verification requirement...", LogCategories.VERIFICATION)
        time.sleep(random.uniform(1, 2))
        
        # Get page text
        try:
            page_text = page.inner_text('body') or ""
        except Exception:
            page_text = ""
        
        # Check for phone verification keywords
        phone_verification_keywords = [
            'введите свой номер мобильного телефона',
            'enter your mobile phone number',
            'confirm your phone number',
            'подтвердите номер телефона',
            'номер мобильного телефона',
            'mobile phone number',
            'вам необходимо подтвердить этот номер',
            'you need to confirm this phone number',
            'добавьте номер телефона',
            'add phone number',
            'phone verification required'
        ]
        
        phone_verification_detected = any(keyword.lower() in page_text.lower() for keyword in phone_verification_keywords)
        
        if phone_verification_detected:
            log_error("📱 Phone verification requirement detected!", LogCategories.VERIFICATION)
            log_info(f"🔍 Page text sample: '{page_text[:200]}...'", LogCategories.VERIFICATION)
            
            # Take screenshot for documentation
            try:
                timestamp = int(time.time())
                screenshot_path = f"phone_verification_detected_{timestamp}.png"
                page.screenshot(path=screenshot_path)
                log_info(f"Screenshot saved: {screenshot_path}", LogCategories.VERIFICATION)
            except Exception as e:
                log_warning(f"Could not take screenshot: {str(e)}", LogCategories.VERIFICATION)
            
            return True
        else:
            log_info("✅ No phone verification requirement detected", LogCategories.VERIFICATION)
            return False
            
    except Exception as e:
        log_warning(f"Error checking for phone verification: {str(e)}", LogCategories.VERIFICATION)
        return False

def check_for_human_verification_dialog(page, account_details=None):
    """Check if Instagram is showing the human verification dialog"""
    try:
        log_info("Checking for human verification dialog...", LogCategories.VERIFICATION)
        time.sleep(random.uniform(1, 2))
        
        # Get page text
        try:
            page_text = page.inner_text('body') or ""
        except Exception:
            page_text = ""
        
        # Check for verification keywords
        verification_detected = any(keyword.lower() in page_text.lower() for keyword in InstagramTexts.VERIFICATION_KEYWORDS)
        
        if verification_detected:
            log_warning("Human verification keywords found", LogCategories.VERIFICATION)
            
            # Special handling for reCAPTCHA verification
            if any(keyword in page_text.lower() for keyword in ['подтвердите, что это вы', 'подтвердите что это вы']):
                log_info("🤖 Detected verification dialog - checking for reCAPTCHA...", LogCategories.CAPTCHA)
                
                try:
                    captcha_params = detect_recaptcha_on_page(page)
                    if captcha_params:
                        log_info("🔍 reCAPTCHA detected, attempting to solve...", LogCategories.CAPTCHA)
                        captcha_solved = solve_recaptcha_if_present_sync(page, account_details)
                        
                        if captcha_solved:
                            log_success("✅ reCAPTCHA solved", LogCategories.CAPTCHA)
                            time.sleep(random.uniform(2, 4))
                            
                            # Recheck if verification dialog is still present
                            try:
                                updated_page_text = page.inner_text('body') or ""
                                still_verification = any(keyword.lower() in updated_page_text.lower() for keyword in InstagramTexts.VERIFICATION_KEYWORDS)
                                
                                if not still_verification:
                                    log_success("✅ Verification dialog resolved", LogCategories.CAPTCHA)
                                    return False
                            except:
                                pass
                        else:
                            log_error("❌ Failed to solve reCAPTCHA", LogCategories.CAPTCHA)
                except Exception as e:
                    log_error(f"❌ Error handling reCAPTCHA: {str(e)}", LogCategories.CAPTCHA)
            
            # Check for verification dialog elements
            dialog_elements_found = []
            for selector in InstagramSelectors.HUMAN_VERIFICATION_DIALOGS:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        dialog_elements_found.append(selector)
                except Exception:
                    continue
            
            if dialog_elements_found:
                log_error(f"Human verification dialog confirmed!", LogCategories.VERIFICATION)
                
                # Take screenshot for documentation
                try:
                    timestamp = int(time.time())
                    screenshot_path = f"human_verification_detected_{timestamp}.png"
                    page.screenshot(path=screenshot_path)
                    log_info(f"Screenshot saved: {screenshot_path}", LogCategories.VERIFICATION)
                except Exception as e:
                    log_warning(f"Could not take screenshot: {str(e)}", LogCategories.VERIFICATION)
                
                return True
            else:
                log_info("Verification keywords found but no dialog elements", LogCategories.VERIFICATION)
                return False
        else:
            log_info("No human verification dialog detected", LogCategories.VERIFICATION)
            return False
            
    except Exception as e:
        log_warning(f"Error checking for human verification dialog: {str(e)}", LogCategories.VERIFICATION)
        return False

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