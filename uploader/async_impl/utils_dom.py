"""Auto-refactored module: utils_dom"""
from .logging import logger

from .file_input import check_for_file_dialog_async
from .human import _type_like_human_async
from .human import click_element_with_behavior_async
from .human import simulate_human_mouse_movement_async
from .human import simulate_page_scan_async
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
        suspension_keywords = SelectorConfig.SUSPENSION_TEXT_KEYWORDS
        
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
        # Before treating as suspended, check if this is actually a verification checkpoint
        try:
            from ..email_verification_async import determine_verification_type_async
            verification_type = await determine_verification_type_async(page)
            # If any verification is detected, do NOT mark as suspended here
            if verification_type in ("email_code", "email_field", "authenticator"):
                log_info(f"[SEARCH] [ASYNC_LOGIN] URL suggests suspension, but verification '{verification_type}' detected; proceeding with verification instead of SUSPENDED")
            else:
                log_info(f"[BLOCK] [ASYNC_LOGIN] Account suspension also detected from URL: {current_url}")
                return "SUSPENDED"
        except Exception as verification_probe_error:
            # If verification probe fails, fall back to previous behavior
            log_info(f"[WARN] [ASYNC_LOGIN] Verification probe failed during suspension URL check: {str(verification_probe_error)}")
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

async def handle_anti_automation_warning_async(page) -> bool:
    """Detect and dismiss anti-automation warning banner/dialog (RU/EN/ES/PT)."""
    try:
        # Quick scan for known texts (non-fatal if missing)
        warning_text_selectors = [
            # Portuguese
            'span:has-text("Suspeitamos que o comportamento da sua conta seja automatizado")',
            'div:has-text("Suspeitamos que o comportamento da sua conta seja automatizado")',
            # English
            'div:has-text("We suspect your account behavior is automated")',
            # Spanish
            'div:has-text("Sospechamos que el comportamiento de tu cuenta es automatizado")',
            # Russian
            'div:has-text("Мы подозреваем автоматизированное поведение вашей учетной записи")',
        ]
        ignore_button_selectors = [
            # PT/ES
            'div[role="button"]:has-text("Ignorar")',
            'button:has-text("Ignorar")',
            # EN
            'div[role="button"]:has-text("Ignore")',
            'button:has-text("Ignore")',
            # RU (варианты)
            'div[role="button"]:has-text("Игнорировать")',
            'div[role="button"]:has-text("Пропустить")',
            'button:has-text("Игнорировать")',
            'button:has-text("Пропустить")',
        ]

        found_warning = False
        for sel in warning_text_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    found_warning = True
                    log_info(f"[ASYNC_UPLOAD] [WARN] Anti-automation warning detected: {sel}")
                    break
            except Exception:
                continue

        # If not found by text, still try clicking known ignore buttons (can appear without main text)
        if not found_warning:
            log_debug("[ASYNC_UPLOAD] [SEARCH] No explicit warning text; probing ignore buttons")

        for sel in ignore_button_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.hover()
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    await btn.click()
                    log_info(f"[ASYNC_UPLOAD] [OK] Dismissed anti-automation warning via: {sel}")
                    await asyncio.sleep(random.uniform(0.6, 1.0))
                    return True
            except Exception:
                continue

        return False
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [WARN] Error handling anti-automation warning: {str(e)}")
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
                
                # Quick check: main Instagram interface elements (broadened, multilingual)
                navigation_selectors = [
                    'nav', '[role="navigation"]', '[data-testid="navigation"]', 'main[role="main"]',
                    'div[data-testid="ig-nav-bar"]'
                ]
                main_interface_found = False
                # Try navigation containers first
                for nav_sel in navigation_selectors:
                    try:
                        el = await page.query_selector(nav_sel)
                        if el and await el.is_visible():
                            main_interface_found = True
                            break
                    except Exception:
                        continue
                # If not found, try explicit MAIN_INTERFACE icons/labels (RU/EN/ES/PT)
                if not main_interface_found:
                    for sel in SelectorConfig.MAIN_INTERFACE:
                        try:
                            el = await page.query_selector(sel)
                            if el and await el.is_visible():
                                main_interface_found = True
                                break
                        except Exception:
                            continue
                if not main_interface_found:
                    log_info(f"[ASYNC_READY] [WAIT] Main interface not found")
                    await asyncio.sleep(0.8)
                    continue
                
                # Quick check: upload button visibility (centralized selectors)
                upload_button = None
                for sel in SelectorConfig.UPLOAD_BUTTON:
                    try:
                        formatted = f"xpath={sel}" if sel.startswith('//') else sel
                        el = await page.query_selector(formatted)
                        if el and await el.is_visible():
                            upload_button = el
                            break
                    except Exception:
                        continue
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

async def find_element_with_selectors_async(page, selectors, element_name: str = "ELEMENT", *, timeout: Optional[float] = None):
    """Unified finder: returns a single Locator (.first()) for given selectors; RU/EN safe.
    Accepts legacy third positional arg (element_name) and optional timeout.
    """
    try:
        for i, selector in enumerate(selectors):
            try:
                formatted = f"xpath={selector}" if selector.startswith('//') else selector
                loc = page.locator(formatted).first()
                # Minimal wait for visibility if requested
                if timeout:
                    await loc.wait_for(state="visible", timeout=timeout)
                # Quick soft visibility probe
                try:
                    visible = await loc.is_visible()
                except Exception:
                    visible = True  # Some elements might not support is_visible; still attempt
                if visible:
                    log_info(f"[ASYNC_UPLOAD] [OK] Found {element_name} with selector: {selector}")
                    return loc
            except Exception as e:
                log_info(f"[ASYNC_UPLOAD] Selector failed: {selector} - {str(e)}")
                continue
        log_info(f"[ASYNC_UPLOAD] [FAIL] {element_name} not found with any selector")
        return None
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error finding {element_name}: {str(e)}")
        return None

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

async def click_post_option_async(page, account=None) -> bool:
    """Find and click post option in dropdown - ENHANCED with multilingual support"""
    try:
        log_info("[ASYNC_UPLOAD] [SEARCH] Looking for 'Post' option with multilingual detection...")
        
        # Resolve account locale for multilingual selectors
        locale = 'ru'  # default
        if account:
            locale = LocaleResolver.resolve_account_locale(account)
            log_info(f"[ASYNC_UPLOAD] [LOCALE] Using locale: {locale} for account")
        
        # Get multilingual selector provider
        provider = get_multilingual_selector_provider()
        
        # ENHANCED: Longer human-like pause to read menu options
        reading_time = 4.0 + random.uniform(-1.0, 1.0)  # Increased from 2.0 to 4.0 seconds
        log_info(f"[ASYNC_UPLOAD] 📖 Reading menu options for {reading_time:.1f}s (enhanced wait)...")
        await asyncio.sleep(reading_time)
        
        await simulate_page_scan_async(page)
        
        post_option = None
        found_selector = None
        
        # Get multilingual post option selectors
        post_selectors = provider.get_post_option_selectors(locale)
        
        for i, selector in enumerate(post_selectors):
            try:
                if i > 0:
                    # ENHANCED: Longer pause between selectors
                    selector_wait = 1.0 + random.uniform(-0.3, 0.3)  # Increased from 0.3-0.7 to 0.7-1.3
                    await asyncio.sleep(selector_wait)
                
                log_info(f"[ASYNC_UPLOAD] [SEARCH] Trying selector {i+1}/{len(post_selectors)}: {selector}")
                
                if selector.startswith('//'):
                    post_option = await page.query_selector(f"xpath={selector}")
                else:
                    post_option = await page.query_selector(selector)
                
                if post_option and await post_option.is_visible():
                    try:
                        element_text = await post_option.text_content() or ""
                        element_aria = await post_option.get_attribute('aria-label') or ""
                        combined_text = (element_text + " " + element_aria).lower()
                        
                        # ENHANCED: Multilingual post keywords based on locale
                        post_keywords = []
                        if locale == 'es':
                            post_keywords = ['publicación', 'post', 'crear publicación', 'crear', 'nueva publicación']
                        elif locale == 'pt':
                            post_keywords = ['publicação', 'post', 'criar publicação', 'criar', 'nova publicação']
                        elif locale == 'en':
                            post_keywords = ['post', 'create post', 'create', 'new post', 'add post']
                        else:  # ru
                            post_keywords = ['публикация', 'post', 'создать публикацию', 'создать', 'новая публикация']
                        
                        if any(keyword in combined_text for keyword in post_keywords):
                            log_info(f"[ASYNC_UPLOAD] [OK] Found 'Post' option: '{element_text.strip()}'")
                            found_selector = selector
                            break
                        else:
                            log_info(f"[ASYNC_UPLOAD] [SEARCH] Element found but text doesn't match: '{element_text.strip()}'")
                            post_option = None
                            continue
                    except Exception as text_error:
                        log_info(f"[ASYNC_UPLOAD] [OK] Found potential 'Post' option (text check failed: {str(text_error)})")
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

async def add_video_location_async(page, video_obj, account=None):
    """Add video location - FULL VERSION with multilingual support"""
    try:
        log_info(f"[ASYNC_UPLOAD] [SEARCH] Starting location search for video_obj: {type(video_obj)}")
        
        # Resolve account locale for multilingual selectors
        locale = 'ru'  # default
        if account:
            locale = LocaleResolver.resolve_account_locale(account)
            log_info(f"[ASYNC_UPLOAD] [LOCALE] Using locale: {locale} for account")
        
        # Get multilingual selector provider
        provider = get_multilingual_selector_provider()
        
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
        
        # Get multilingual location input selectors
        location_field_selectors = SelectorConfig.LOCATION_INPUT
        
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

async def add_video_mentions_async(page, video_obj, account=None):
    """Add video mentions - FULL VERSION with multilingual support"""
    try:
        log_info(f"[ASYNC_UPLOAD] [SEARCH] Starting mentions search for video_obj: {type(video_obj)}")
        
        # Resolve account locale for multilingual selectors
        locale = 'ru'  # default
        if account:
            locale = LocaleResolver.resolve_account_locale(account)
            log_info(f"[ASYNC_UPLOAD] [LOCALE] Using locale: {locale} for account")
        
        # Get multilingual selector provider
        provider = get_multilingual_selector_provider()
        
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
        
        # Mentions field selectors (centralized)
        mentions_field_selectors = SelectorConfig.MENTIONS_INPUT
        
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
        done_button_selectors = provider.get_done_button_selectors(locale)
        
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
            upload_context_indicators = SelectorConfig.UPLOAD_CONTEXT_INDICATORS
            
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

async def click_share_button_async(page, account=None):
    """Click share button - ENHANCED VERSION with multilingual selector support"""
    try:
        log_info("[ASYNC_UPLOAD] Looking for share button...")
        
        # Resolve account locale for multilingual selectors
        locale = 'ru'  # default
        if account:
            locale = LocaleResolver.resolve_account_locale(account)
            log_info(f"[ASYNC_UPLOAD] [LOCALE] Using locale: {locale} for account")
        
        # Get multilingual selector provider
        provider = get_multilingual_selector_provider()
        
        # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Проверяем контекст загрузки перед поиском кнопки
        log_info("[ASYNC_UPLOAD] [SEARCH] Checking upload context before searching for share button...")
        upload_context_indicators = SelectorConfig.UPLOAD_CONTEXT_INDICATORS
        
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
        
        # Get multilingual share button selectors
        share_selectors = provider.get_share_button_selectors(locale)
        
        # Restrict search inside stable upload container only
        container_selectors = [
            'div[role="dialog"]',
        ]
        
        # Prefer text-based selectors for PT/RU/EN/ES
        publish_text_variants = [
            "Compartilhar", "Publicar", "Postar",  # PT
            "Опубликовать", "Публикация",           # RU
            "Share", "Post", "Publish",            # EN
            "Compartir", "Publicación"              # ES
        ]
        for container in container_selectors:
            for txt in publish_text_variants:
                share_selectors.append(f'{container} [role="button"]:has-text("{txt}")')
                share_selectors.append(f'{container} button:has-text("{txt}")')
        
        # XPath fallbacks inside dialog container
        share_selectors.extend([
            '//div[@role="dialog"]//div[@role="button" and (contains(., "Compartilhar") or contains(., "Publicar") or contains(., "Postar") or contains(., "Share") or contains(., "Publish") or contains(., "Опубликовать") or contains(., "Публикация") or contains(., "Compartir") or contains(., "Publicación"))]',
            '//div[@role="dialog"]//button[(contains(., "Compartilhar") or contains(., "Publicar") or contains(., "Postar") or contains(., "Share") or contains(., "Publish") or contains(., "Опубликовать") or contains(., "Публикация") or contains(., "Compartir") or contains(., "Publicación"))]',
        ])

        # Remove unstable container '_ap97' from any residual selectors (safety)
        share_selectors = [sel for sel in share_selectors if '_ap97' not in sel]
        

        # Dynamic context-aware XPath (no fixed container): verify ancestor has heading like "Novo reel" etc.
        share_selectors.extend([
            '//*[self::div[@role="button"] or self::button][(contains(normalize-space(.), "Compartilhar") or contains(normalize-space(.), "Publicar") or contains(normalize-space(.), "Postar") or contains(normalize-space(.), "Share") or contains(normalize-space(.), "Publish") or contains(normalize-space(.), "Опубликовать") or contains(normalize-space(.), "Публикация") or contains(normalize-space(.), "Compartir") or contains(normalize-space(.), "Publicación")) and ancestor::*[.//div[@role="heading" or self::h1][contains(., "Novo reel") or contains(., "New reel") or contains(., "Новый") or contains(., "Nuevo reel")]]]',
            '//*[self::div[@role="button"] or self::button][(contains(normalize-space(.), "Compartilhar") or contains(normalize-space(.), "Publicar") or contains(normalize-space(.), "Postar") or contains(normalize-space(.), "Share") or contains(normalize-space(.), "Publish") or contains(normalize-space(.), "Опубликовать") or contains(normalize-space(.), "Публикация") or contains(normalize-space(.), "Compartir") or contains(normalize-space(.), "Publicación")) and ancestor::*[contains(., "Novo reel") or contains(., "New reel") or contains(., "Reel novo") or contains(., "Рилс") or contains(., "Nuevo reel")]]'
        ])
        
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
                            # Дополнительная проверка текста кнопки: публиковать, а не назад/отмена
                            btn_text_raw = ""
                            try:
                                btn_text_raw = await element.text_content() or ""
                            except Exception:
                                btn_text_raw = ""
                            btn_aria = await element.get_attribute('aria-label') or ""
                            combined_text = (btn_text_raw + " " + btn_aria).strip().lower()
                            publish_keywords = [
                                'share', 'post', 'publish',
                                'опубликовать', 'публикация',
                                'compartilhar', 'publicar', 'postar',
                                'compartir', 'publicación'
                            ]
                            negative_keywords = [
                                'back', 'voltar', 'atrás', 'назад',
                                'cancel', 'cancelar', 'отмена'
                            ]
                            if any(nk in combined_text for nk in negative_keywords):
                                log_info(f"[ASYNC_UPLOAD] [WARN] Skipping non-publish button (likely back/cancel): '{combined_text[:40]}'")
                                continue
                            if combined_text and any(pk in combined_text for pk in publish_keywords):
                                log_info(f"[ASYNC_UPLOAD] [OK] Found share/publish button in dialog: {selector}")
                                share_button = element
                                break
                            else:
                                # If no text is present (icon-only), keep as candidate last resort
                                if not combined_text:
                                    log_info(f"[ASYNC_UPLOAD] [OK] Found candidate button (no text), keeping as fallback: {selector}")
                                    if share_button is None:
                                        share_button = element
                                    continue
                                log_info(f"[ASYNC_UPLOAD] [SEARCH] Button text doesn't match publish keywords: '{combined_text[:50]}'")
                                continue
                        else:
                            log_info(f"[ASYNC_UPLOAD] [WARN] Share button found but not in upload dialog: {selector}")
                            # Продолжаем поиск
                            continue
                    except Exception as context_error:
                        log_info(f"[ASYNC_UPLOAD] [WARN] Error checking button context: {str(context_error)}")
                        # Если не можем проверить контекст, не кликаем вслепую — продолжаем поиск
                        log_info(f"[ASYNC_UPLOAD] [WARN] Context check failed; continuing search: {selector}")
                        continue
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
        success_selectors = SelectorConfig.SUCCESS_DIALOG
        
        error_selectors = SelectorConfig.ERROR_DIALOG
        
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
        cookie_modal_indicators = SelectorConfig.COOKIE_MODAL_INDICATORS
        
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
        cookie_consent_buttons = SelectorConfig.COOKIE_CONSENT_BUTTONS
        
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
        from ..captcha_solver import solve_recaptcha_if_present
        
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

async def check_for_phone_verification_page_async(page):
    """Check for phone verification requirement - async version"""
    try:
        phone_verification_indicators = SelectorConfig.PHONE_VERIFICATION_INDICATORS
        
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

async def check_for_account_suspension_async(page):
    """Check for account suspension - async version"""
    try:
        suspension_indicators = SelectorConfig.SUSPENSION_INDICATORS
        
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

async def _find_original_by_text_content_async(page, account=None):
    """Поиск 'Оригинал' по текстовому содержимому - async version with multilingual support"""
    log_info("[ASYNC_CROP] 📐 [TEXT] Searching for 'Original' by text content...")
    
    # Resolve account locale for multilingual selectors
    locale = 'ru'  # default
    if account:
        locale = LocaleResolver.resolve_account_locale(account)
        log_info(f"[ASYNC_CROP] [LOCALE] Using locale: {locale} for account")
    
    # Get multilingual selector provider
    provider = get_multilingual_selector_provider()
    
    # Get multilingual crop original selectors
    text_selectors = provider.get_crop_original_selectors(locale)
    
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
        # Centralized email submit button selectors
        submit_button = None
        for sel in SelectorConfig.EMAIL_SUBMIT_BUTTONS:
            try:
                submit_button = await page.query_selector(sel)
                if submit_button and await submit_button.is_visible():
                    break
            except Exception:
                continue
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
                # Ensure locale and language present even if to_dict missed
                try:
                    account_details.setdefault('locale', account.locale or 'ru_BY')
                except Exception:
                    account_details.setdefault('locale', 'ru_BY')
                try:
                    lang = (account_details.get('locale') or 'ru_BY').split('_', 1)[0].lower()
                    if lang not in ('en','ru','es','pt'):
                        lang = 'ru'
                    account_details.setdefault('language', lang)
                except Exception:
                    account_details.setdefault('language', 'ru')
                
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
        
        # Quick check: main navigation element or MAIN_INTERFACE icons (multilingual)
        main_interface_found = False
        for nav_sel in ['nav', '[role="navigation"]', '[data-testid="navigation"]', 'main[role="main"]', 'div[data-testid="ig-nav-bar"]']:
            try:
                el = await page.query_selector(nav_sel)
                if el and await el.is_visible():
                    main_interface_found = True
                    break
            except Exception:
                continue
        if not main_interface_found:
            for sel in SelectorConfig.MAIN_INTERFACE:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        main_interface_found = True
                        break
                except Exception:
                    continue
        if not main_interface_found:
            log_info("[ASYNC_UPLOAD] [WARN] Main interface not found")
            return False
        
        # Quick check: upload button (centralized)
        upload_button = None
        for sel in SelectorConfig.UPLOAD_BUTTON:
            try:
                formatted = f"xpath={sel}" if sel.startswith('//') else sel
                el = await page.query_selector(formatted)
                if el and await el.is_visible():
                    upload_button = el
                    break
            except Exception:
                continue
        if not upload_button:
            log_info("[ASYNC_UPLOAD] [WARN] Upload button not found or not visible")
            return False
        
        log_info("[ASYNC_UPLOAD] [OK] Page elements verified successfully")
        return True
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error in verify_page_elements_state_async: {str(e)}")
        return False

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

__all__ = ['check_if_already_logged_in_async', 'wait_for_page_ready_async', 'find_element_with_selectors_async', 'check_for_dropdown_menu_async', 'click_post_option_async', 'add_video_location_async', 'add_video_mentions_async', 'click_share_button_async', 'check_video_posted_successfully_async', 'handle_cookie_consent_async', 'safely_close_all_windows_async', 'handle_recaptcha_if_present_async', 'check_for_phone_verification_page_async', 'check_for_account_suspension_async', 'log_video_info_async', 'handle_email_field_verification_async', 'cleanup_original_video_files_async', 'get_account_details_async', 'get_assigned_videos_async', 'prepare_unique_videos_async', 'verify_page_elements_state_async', 'retry_navigation_async']


# === v2 helpers (non-breaking additions) ===
from typing import Optional, Sequence, Any
from .dom_helpers import click_human_like, find_element_with_fallbacks

async def find_element_with_selectors_v2_async(page, selectors: Sequence[str], *, timeout: Optional[float] = None):
    """
    v2: uses a single helper to iterate selectors. Behavior: returns locator or None.
    Original functions remain intact.
    """
    return await find_element_with_fallbacks(page, selectors, timeout=timeout)

async def click_element_with_behavior_v2_async(page, locator_or_selector: Any, *, delay_ms: int = 60, timeout: Optional[float] = None):
    """
    v2: centralized click with small human-like delay.
    """
    return await click_human_like(page, locator_or_selector, delay_ms=delay_ms, timeout=timeout)


# === PASS 3: shim overrides for critical helpers (non-breaking) ===
try:
    _find_element_with_selectors_async_original = find_element_with_selectors_async
except Exception:
    _find_element_with_selectors_async_original = None

try:
    _click_element_with_behavior_async_original = click_element_with_behavior_async
except Exception:
    _click_element_with_behavior_async_original = None

from typing import Optional, Sequence, Any

async def find_element_with_selectors_async(page, selectors: Sequence[str], *, timeout: Optional[float] = None):
    """Shim: try v2 first, then fall back to original implementation."""
    try:
        loc = await find_element_with_selectors_v2_async(page, selectors, timeout=timeout)
        if loc is not None:
            return loc
    except Exception as e:
        logger.debug(f"v2 find_element_with_selectors failed, falling back: {e}")
    if _find_element_with_selectors_async_original:
        return await _find_element_with_selectors_async_original(page, selectors, timeout=timeout)
    return None

async def click_element_with_behavior_async(page, locator_or_selector: Any, *, delay_ms: int = 60, timeout: Optional[float] = None):
    """Shim: try v2 click, then fall back to original behavior."""
    try:
        return await click_element_with_behavior_v2_async(page, locator_or_selector, delay_ms=delay_ms, timeout=timeout)
    except Exception as e:
        logger.debug(f"v2 click_element_with_behavior failed, falling back: {e}")
    if _click_element_with_behavior_async_original:
        return await _click_element_with_behavior_async_original(page, locator_or_selector, delay_ms=delay_ms, timeout=timeout)
    return None
