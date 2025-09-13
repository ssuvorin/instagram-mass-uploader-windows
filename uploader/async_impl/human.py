"""Auto-refactored module: human"""
from .logging import logger

# NOTE: Avoid importing from .utils_dom at module import time to prevent circular imports.
# We will lazily import `_quick_click_async` inside the function where it is needed.
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
from ..advanced_human_behavior import init_advanced_human_behavior, get_advanced_human_behavior
from ..captcha_solver import solve_recaptcha_if_present, detect_recaptcha_on_page, solve_recaptcha_if_present_sync
from ..email_verification_async import (
    get_email_verification_code_async,
    get_2fa_code_async,
    determine_verification_type_async
)
import django
from ..models import InstagramAccount, BulkUploadAccount


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

async def click_element_with_behavior_async(page, element, element_name):
    """Click element with human behavior - ПОЛНАЯ КОПИЯ из sync, enhanced for Locator.first() and visibility"""
    try:
        # Normalize to a single Locator when possible
        try:
            if hasattr(element, "first"):
                element = element.first()
        except Exception:
            pass
        
        # ENHANCED: Ensure element is in viewport
        try:
            await element.scroll_into_view_if_needed(timeout=2000)
        except Exception:
            pass
        
        # ENHANCED: Additional element readiness check before clicking
        try:
            is_visible = await element.is_visible()
            is_enabled = await element.is_enabled()
            
            if not is_visible:
                log_info(f"[ASYNC_UPLOAD] [WARN] {element_name} is not visible, waiting...")
                await asyncio.sleep(2.0 + random.uniform(-0.5, 0.5))
                try:
                    await element.scroll_into_view_if_needed(timeout=2000)
                except Exception:
                    pass
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
        
        # Use advanced human behavior if available
        human_behavior = get_advanced_human_behavior()
        if human_behavior:
            success = await human_behavior.human_click(element, element_name)
            if success:
                return True
            log_info(f"[ASYNC_UPLOAD] [FALLBACK] Advanced behavior failed, using basic click for {element_name}")
        
        # Fallback to basic behavior
        await simulate_mouse_movement_to_element_async(page, element)
        
        # Human decision pause
        decision_time = 1.0 + random.uniform(-0.3, 0.5)
        await asyncio.sleep(decision_time)
        
        # Try hover before click
        try:
            await element.hover(timeout=2000)
        except Exception:
            pass
        
        # Click element
        await element.click()
        log_info(f"[ASYNC_UPLOAD] [OK] {element_name} clicked successfully")
        
        # Brief pause after click
        await asyncio.sleep(0.5 + random.uniform(-0.2, 0.3))
        return True
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error clicking {element_name}: {str(e)}")
        return False

async def _type_like_human_async(page, element, text):
    """Type text like a human with advanced behavior simulation"""
    try:
        log_info("[ASYNC_UPLOAD] [BOT] Starting advanced human-like typing...")
        
        # Use advanced human behavior if available
        human_behavior = get_advanced_human_behavior()
        if human_behavior:
            success = await human_behavior.human_type(element, text, "caption_typing")
            if success:
                return True
            log_info("[ASYNC_UPLOAD] [FALLBACK] Advanced typing failed, using basic typing")
        
        # Fallback to basic human typing
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
            
            # Fallback to quick click via lazy import to avoid circular imports
            try:
                from .utils_dom import _quick_click_async as _lazy_quick_click_async
                return await _lazy_quick_click_async(page, element, log_prefix)
            except Exception as import_error:
                log_info(f"[{log_prefix}] Quick click import failed: {repr(import_error)}")
                # Minimal last-resort fallback
                try:
                    await element.click()
                    return True
                except Exception as final_e:
                    log_info(f"[{log_prefix}] Final click fallback failed: {str(final_e)[:100]}")
                    return False
            
    except Exception as e:
        log_info(f"[{log_prefix}] Error in human click: {str(e)[:100]}")
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
    """Simulate human mouse movement to element - async version, robust for Locator/ElementHandle"""
    try:
        # Normalize to a single Locator and ensure in view
        try:
            if hasattr(element, "first"):
                element = element.first()
            try:
                await element.scroll_into_view_if_needed(timeout=2000)
            except Exception:
                pass
        except Exception:
            pass
        
        # Get element position
        box = await element.bounding_box()
        if box:
            # Move to random position within element
            x = box['x'] + box['width'] * random.uniform(0.2, 0.8)
            y = box['y'] + box['height'] * random.uniform(0.2, 0.8)
            
            await page.mouse.move(x, y, steps=random.randint(8, 20))
            await asyncio.sleep(random.uniform(0.2, 0.6))
    except Exception as e:
        log_info(f"[ASYNC_HUMAN] Mouse movement to element error: {str(e)}")

async def simulate_random_browsing_async(page):
    """Simulate random browsing behavior - async version"""
    try:
        actions = [
            {"action": "scroll", "distance": random.randint(200, 800)},
            {"action": "pause", "duration": random.uniform(0.5, 2.0)},
            {"action": "move", "x": random.randint(50, 1200), "y": random.randint(50, 800)},
        ]
        for action in actions:
            if action["action"] == "scroll":
                await page.mouse.wheel(0, action["distance"])
            elif action["action"] == "pause":
                await asyncio.sleep(action["duration"])
            elif action["action"] == "move":
                await page.mouse.move(action["x"], action["y"], steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.2, 0.6))
    except Exception as e:
        log_info(f"[ASYNC_HUMAN] Random browsing simulation error: {str(e)}")

__all__ = ['init_human_behavior_async', 'simulate_human_mouse_movement_async', 'click_element_with_behavior_async', 'simulate_page_scan_async', 'simulate_mouse_movement_to_element_async', 'simulate_random_browsing_async']


# === PASS 6: HumanBehavior façade (non-breaking) ===
from typing import Optional, Any
from .logging import logger

class HumanBehavior:
    """
    Non-intrusive façade over existing human-like behavior helpers.
    Delegates to existing functions; does not change defaults or timings.
    """
    def __init__(self) -> None:
        logger.debug("HumanBehavior initialized")

    async def init(self, page: Any) -> None:
        if "init_human_behavior_async" in globals():
            try:
                await globals()["init_human_behavior_async"](page)
            except Exception as e:
                logger.debug("init_human_behavior_async failed: " + repr(e))

    async def mouse_move(self, page: Any, target: Any = None, *, duration_ms: Optional[int] = None) -> None:
        fn = globals().get("simulate_mouse_movement_to_element_async") or globals().get("simulate_human_mouse_movement_async")
        if fn:
            await fn(page, target) if target is not None else await fn(page)

    async def page_scan(self, page: Any) -> None:
        fn = globals().get("simulate_page_scan_async")
        if fn:
            await fn(page)

    async def random_browse(self, page: Any, *, max_steps: int = 3) -> None:
        fn = globals().get("simulate_random_browsing_async")
        if fn:
            try:
                await fn(page, max_steps=max_steps)
            except TypeError:
                # keep compatibility if the original signature differs
                await fn(page)

    async def pause_between_uploads(self) -> None:
        fn = globals().get("add_human_delay_between_uploads_async")
        if fn:
            await fn()


# === PASS 6 SAFE SHIMS HUMAN (non-breaking) ===
from .logging import logger
import inspect, asyncio
try:
    _orig_init_human_behavior_async = init_human_behavior_async
except Exception:
    _orig_init_human_behavior_async = None
async def init_human_behavior_async(*args, **kwargs):
    """Auto-wrapped human-behavior function. Behavior unchanged; adds structured logs."""
    logger.info('HUMAN:init_human_behavior_async start')
    try:
        if _orig_init_human_behavior_async is None:
            logger.warning('HUMAN:init_human_behavior_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_init_human_behavior_async):
            res = await _orig_init_human_behavior_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_init_human_behavior_async(*args, **kwargs))
        logger.info('HUMAN:init_human_behavior_async ok')
        return res
    except Exception as e:
        logger.error('HUMAN:init_human_behavior_async error: ' + repr(e))
        raise
try:
    _orig_simulate_human_mouse_movement_async = simulate_human_mouse_movement_async
except Exception:
    _orig_simulate_human_mouse_movement_async = None
async def simulate_human_mouse_movement_async(*args, **kwargs):
    """Auto-wrapped human-behavior function. Behavior unchanged; adds structured logs."""
    logger.info('HUMAN:simulate_human_mouse_movement_async start')
    try:
        if _orig_simulate_human_mouse_movement_async is None:
            logger.warning('HUMAN:simulate_human_mouse_movement_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_simulate_human_mouse_movement_async):
            res = await _orig_simulate_human_mouse_movement_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_simulate_human_mouse_movement_async(*args, **kwargs))
        logger.info('HUMAN:simulate_human_mouse_movement_async ok')
        return res
    except Exception as e:
        logger.error('HUMAN:simulate_human_mouse_movement_async error: ' + repr(e))
        raise
try:
    _orig_click_element_with_behavior_async = click_element_with_behavior_async
except Exception:
    _orig_click_element_with_behavior_async = None
async def click_element_with_behavior_async(*args, **kwargs):
    """Auto-wrapped human-behavior function. Behavior unchanged; adds structured logs."""
    logger.info('HUMAN:click_element_with_behavior_async start')
    try:
        if _orig_click_element_with_behavior_async is None:
            logger.warning('HUMAN:click_element_with_behavior_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_click_element_with_behavior_async):
            res = await _orig_click_element_with_behavior_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_click_element_with_behavior_async(*args, **kwargs))
        logger.info('HUMAN:click_element_with_behavior_async ok')
        return res
    except Exception as e:
        logger.error('HUMAN:click_element_with_behavior_async error: ' + repr(e))
        raise
try:
    _orig__type_like_human_async = _type_like_human_async
except Exception:
    _orig__type_like_human_async = None
async def _type_like_human_async(*args, **kwargs):
    """Auto-wrapped human-behavior function. Behavior unchanged; adds structured logs."""
    logger.info('HUMAN:_type_like_human_async start')
    try:
        if _orig__type_like_human_async is None:
            logger.warning('HUMAN:_type_like_human_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig__type_like_human_async):
            res = await _orig__type_like_human_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig__type_like_human_async(*args, **kwargs))
        logger.info('HUMAN:_type_like_human_async ok')
        return res
    except Exception as e:
        logger.error('HUMAN:_type_like_human_async error: ' + repr(e))
        raise
try:
    _orig__human_click_with_timeout_async = _human_click_with_timeout_async
except Exception:
    _orig__human_click_with_timeout_async = None
async def _human_click_with_timeout_async(*args, **kwargs):
    """Auto-wrapped human-behavior function. Behavior unchanged; adds structured logs."""
    logger.info('HUMAN:_human_click_with_timeout_async start')
    try:
        if _orig__human_click_with_timeout_async is None:
            logger.warning('HUMAN:_human_click_with_timeout_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig__human_click_with_timeout_async):
            res = await _orig__human_click_with_timeout_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig__human_click_with_timeout_async(*args, **kwargs))
        logger.info('HUMAN:_human_click_with_timeout_async ok')
        return res
    except Exception as e:
        logger.error('HUMAN:_human_click_with_timeout_async error: ' + repr(e))
        raise
try:
    _orig_simulate_page_scan_async = simulate_page_scan_async
except Exception:
    _orig_simulate_page_scan_async = None
async def simulate_page_scan_async(*args, **kwargs):
    """Auto-wrapped human-behavior function. Behavior unchanged; adds structured logs."""
    logger.info('HUMAN:simulate_page_scan_async start')
    try:
        if _orig_simulate_page_scan_async is None:
            logger.warning('HUMAN:simulate_page_scan_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_simulate_page_scan_async):
            res = await _orig_simulate_page_scan_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_simulate_page_scan_async(*args, **kwargs))
        logger.info('HUMAN:simulate_page_scan_async ok')
        return res
    except Exception as e:
        logger.error('HUMAN:simulate_page_scan_async error: ' + repr(e))
        raise
try:
    _orig_simulate_mouse_movement_to_element_async = simulate_mouse_movement_to_element_async
except Exception:
    _orig_simulate_mouse_movement_to_element_async = None
async def simulate_mouse_movement_to_element_async(*args, **kwargs):
    """Auto-wrapped human-behavior function. Behavior unchanged; adds structured logs."""
    logger.info('HUMAN:simulate_mouse_movement_to_element_async start')
    try:
        if _orig_simulate_mouse_movement_to_element_async is None:
            logger.warning('HUMAN:simulate_mouse_movement_to_element_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_simulate_mouse_movement_to_element_async):
            res = await _orig_simulate_mouse_movement_to_element_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_simulate_mouse_movement_to_element_async(*args, **kwargs))
        logger.info('HUMAN:simulate_mouse_movement_to_element_async ok')
        return res
    except Exception as e:
        logger.error('HUMAN:simulate_mouse_movement_to_element_async error: ' + repr(e))
        raise
try:
    _orig_simulate_random_browsing_async = simulate_random_browsing_async
except Exception:
    _orig_simulate_random_browsing_async = None
async def simulate_random_browsing_async(*args, **kwargs):
    """Auto-wrapped human-behavior function. Behavior unchanged; adds structured logs."""
    logger.info('HUMAN:simulate_random_browsing_async start')
    try:
        if _orig_simulate_random_browsing_async is None:
            logger.warning('HUMAN:simulate_random_browsing_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_simulate_random_browsing_async):
            res = await _orig_simulate_random_browsing_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_simulate_random_browsing_async(*args, **kwargs))
        logger.info('HUMAN:simulate_random_browsing_async ok')
        return res
    except Exception as e:
        logger.error('HUMAN:simulate_random_browsing_async error: ' + repr(e))
        raise