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
    """REFACTORED: Initialize human behavior using unified system"""
    try:
        log_info("[ASYNC_HUMAN] Initializing unified human behavior system...")
        
        # Import and initialize unified system
        from ..human_behavior_unified import init_unified_human_behavior
        init_unified_human_behavior(page)
        
        log_info("[ASYNC_HUMAN] [OK] Unified human behavior initialized")
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
    """
    ENHANCED: Click element with improved human behavior simulation and robust error handling
    """
    try:
        log_info(f"[ASYNC_UPLOAD] [BOT] Starting enhanced click for {element_name}")
        
        # Enhanced mouse movement with better trajectory calculation
        success = await asyncio.wait_for(
            _enhanced_click_with_trajectory(page, element, element_name),
            timeout=5.0
        )
        if success:
            log_info(f"[ASYNC_UPLOAD] [OK] Enhanced click successful for {element_name}")
            return True
        
        # Fallback to unified system
        from ..human_behavior_unified import get_unified_human_behavior, click_element_with_behavior_unified
        success = await asyncio.wait_for(
            click_element_with_behavior_unified(page, element, element_name),
            timeout=5.0
        )
        if success:
            log_info(f"[ASYNC_UPLOAD] [OK] Unified system click successful for {element_name}")
            return True
        
        # Final fallback to simple click
        log_info(f"[ASYNC_UPLOAD] [FALLBACK] Using simple click for {element_name}")
        await element.click()
        return True
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error clicking {element_name}: {str(e)[:100]}")
        # Last resort fallback
        try:
            await element.click()
            return True
        except Exception:
            return False


async def _enhanced_click_with_trajectory(page, element, element_name):
    """
    Enhanced click implementation with improved trajectory calculation
    Applies Open/Closed Principle - extends behavior without modifying core logic
    """
    try:
        # Normalize element handling
        if hasattr(element, "first"):
            element = element.first()
        
        # Ensure element is visible and in viewport
        try:
            await element.scroll_into_view_if_needed(timeout=2000)
            if not await element.is_visible():
                log_info(f"[ENHANCED_CLICK] Element {element_name} not visible")
                return False
        except Exception as e:
            log_info(f"[ENHANCED_CLICK] Visibility check failed for {element_name}: {e}")
            return False
        
        # Get element bounding box for trajectory calculation
        box = await element.bounding_box()
        if not box:
            log_info(f"[ENHANCED_CLICK] Could not get bounding box for {element_name}")
            return False
        
        # Enhanced trajectory calculation with better precision
        target_x, target_y = _calculate_enhanced_click_position(box)
        
        # Get current mouse position for trajectory
        current_pos = await page.evaluate("() => ({ x: window.mouseX || 0, y: window.mouseY || 0 })")
        start_x, start_y = current_pos.get('x', 0), current_pos.get('y', 0)
        
        # Enhanced curved movement with better timing
        await _enhanced_curved_movement(page, start_x, start_y, target_x, target_y, element_name)
        
        # Enhanced hover and click timing
        await _enhanced_hover_and_click(page, element, element_name)
        
        return True
        
    except Exception as e:
        log_info(f"[ENHANCED_CLICK] Enhanced click failed for {element_name}: {e}")
        return False


def _calculate_enhanced_click_position(box):
    """
    Calculate enhanced click position with better precision and natural variation
    """
    # Use golden ratio for more natural positioning
    golden_ratio = 0.618
    
    # Calculate base position using golden ratio
    base_x = box['x'] + box['width'] * golden_ratio
    base_y = box['y'] + box['height'] * golden_ratio
    
    # Add natural variation based on element size
    variation_x = min(box['width'] * 0.2, 15)  # Max 15px variation
    variation_y = min(box['height'] * 0.2, 10)  # Max 10px variation
    
    # Apply variation with bias toward center
    offset_x = random.uniform(-variation_x, variation_x) * 0.7
    offset_y = random.uniform(-variation_y, variation_y) * 0.7
    
    target_x = base_x + offset_x
    target_y = base_y + offset_y
    
    # Ensure position stays within element bounds
    target_x = max(box['x'] + 2, min(target_x, box['x'] + box['width'] - 2))
    target_y = max(box['y'] + 2, min(target_y, box['y'] + box['height'] - 2))
    
    return target_x, target_y


async def _enhanced_curved_movement(page, start_x, start_y, end_x, end_y, element_name):
    """
    Enhanced curved mouse movement with better mathematical precision
    """
    try:
        # Calculate distance for adaptive step count
        distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
        
        # Adaptive step count based on distance (more steps for longer movements)
        base_steps = max(12, min(25, int(distance / 40)))
        steps = base_steps + random.randint(-2, 3)  # Add variation
        
        # Enhanced control point calculation for more natural curves
        mid_x = (start_x + end_x) / 2
        mid_y = (start_y + end_y) / 2
        
        # Dynamic curve intensity based on distance and direction
        curve_intensity = min(60, distance / 8)
        direction_bias = 1 if (end_x - start_x) * (end_y - start_y) > 0 else -1
        
        # Create two control points for cubic Bezier curve
        control1_x = start_x + (end_x - start_x) * 0.3 + random.uniform(-curve_intensity/2, curve_intensity/2)
        control1_y = start_y + (end_y - start_y) * 0.3 + random.uniform(-curve_intensity/3, curve_intensity/3) * direction_bias
        
        control2_x = start_x + (end_x - start_x) * 0.7 + random.uniform(-curve_intensity/3, curve_intensity/3)
        control2_y = start_y + (end_y - start_y) * 0.7 + random.uniform(-curve_intensity/2, curve_intensity/2) * direction_bias
        
        # Execute enhanced curved movement with variable speed
        for i in range(steps + 1):
            t = i / steps
            
            # Cubic Bezier curve calculation for smoother movement
            x = ((1-t)**3 * start_x + 
                 3*(1-t)**2*t * control1_x + 
                 3*(1-t)*t**2 * control2_x + 
                 t**3 * end_x)
            
            y = ((1-t)**3 * start_y + 
                 3*(1-t)**2*t * control1_y + 
                 3*(1-t)*t**2 * control2_y + 
                 t**3 * end_y)
            
            # Add micro-variations for naturalness (smaller than before)
            x += random.uniform(-1.5, 1.5)
            y += random.uniform(-1.5, 1.5)
            
            await page.mouse.move(x, y)
            
            # Variable movement speed with acceleration/deceleration
            if i < steps * 0.3:  # Acceleration phase
                move_delay = random.uniform(0.015, 0.025)
            elif i > steps * 0.7:  # Deceleration phase
                move_delay = random.uniform(0.020, 0.035)
            else:  # Constant speed phase
                move_delay = random.uniform(0.008, 0.018)
            
            await asyncio.sleep(move_delay)
        
        log_debug(f"[ENHANCED_CLICK] Curved movement completed for {element_name} ({steps} steps)")
        
    except Exception as e:
        log_info(f"[ENHANCED_CLICK] Curved movement failed for {element_name}: {e}")
        # Fallback to direct movement
        try:
            await page.mouse.move(end_x, end_y)
        except Exception:
            pass


async def _enhanced_hover_and_click(page, element, element_name):
    """
    Enhanced hover and click timing with more realistic patterns
    """
    try:
        # Pre-hover thinking pause (occasionally)
        if random.random() < 0.3:  # 30% chance
            thinking_delay = random.uniform(0.2, 0.8)
            await asyncio.sleep(thinking_delay)
        
        # Enhanced hover with natural duration
        try:
            await element.hover(timeout=3000)
            
            # Natural hover duration with variation
            base_hover_time = random.uniform(0.1, 0.3)
            
            # Longer hover for important elements (buttons, links)
            if any(keyword in element_name.lower() for keyword in ['button', 'submit', 'upload', 'post']):
                base_hover_time *= random.uniform(1.2, 1.8)
            
            await asyncio.sleep(base_hover_time)
            
        except Exception as e:
            log_debug(f"[ENHANCED_CLICK] Hover failed for {element_name}: {e}")
        
        # Brief pause before click (micro-hesitation)
        pre_click_delay = random.uniform(0.05, 0.15)
        await asyncio.sleep(pre_click_delay)
        
        # Perform the actual click
        await element.click()
        
        # Post-click delay with context awareness
        base_post_delay = random.uniform(0.3, 0.7)
        
        # Longer delays for form submissions or important actions
        if any(keyword in element_name.lower() for keyword in ['submit', 'post', 'upload', 'send']):
            base_post_delay *= random.uniform(1.5, 2.2)
        
        await asyncio.sleep(base_post_delay)
        
        log_debug(f"[ENHANCED_CLICK] Click sequence completed for {element_name}")
        
    except Exception as e:
        log_info(f"[ENHANCED_CLICK] Click sequence failed for {element_name}: {e}")
        raise

async def _type_like_human_async(page, element, text):
    """
    ENHANCED: Type text with improved error and correction logic and robust error handling
    """
    try:
        log_info("[ASYNC_UPLOAD] [BOT] Starting enhanced human-like typing...")
        
        # Enhanced typing with improved error handling
        success = await asyncio.wait_for(
            _enhanced_human_typing(page, element, text),
            timeout=8.0
        )
        if success:
            log_info("[ASYNC_UPLOAD] [OK] Enhanced human-like typing completed")
            return
        
        # Fallback to unified system
        from ..human_behavior_unified import type_like_human_unified
        success = await asyncio.wait_for(
            type_like_human_unified(page, element, text, "caption_typing"),
            timeout=8.0
        )
        if success:
            log_info("[ASYNC_UPLOAD] [OK] Unified human-like typing completed")
            return
        
        # Final fallback to simple typing
        log_info("[ASYNC_UPLOAD] [FALLBACK] Using simple typing")
        await element.fill(text)
        
    except Exception as e:
        log_info(f"[ASYNC_UPLOAD] [FAIL] Error in human-like typing: {str(e)[:100]}")
        # Final fallback
        try:
            await element.fill(text)
        except Exception:
            pass


async def _enhanced_human_typing(page, element, text):
    """
    Enhanced human typing with improved error and correction patterns
    Uses consistent delay generation interface and better error logic
    """
    try:
        # Focus on element with natural behavior
        await element.click()
        focus_delay = _get_enhanced_typing_delay(0.3, 'focus')
        await asyncio.sleep(focus_delay)
        
        # Clear field naturally (Ctrl+A then type)
        await page.keyboard.press('Control+a')
        await asyncio.sleep(random.uniform(0.1, 0.2))
        
        # Enhanced typing with error simulation
        await _type_with_enhanced_errors(page, element, text)
        
        # Final pause after typing
        final_delay = _get_enhanced_typing_delay(0.5, 'completion')
        await asyncio.sleep(final_delay)
        
        log_debug(f"[ENHANCED_TYPING] Successfully typed {len(text)} characters")
        return True
        
    except Exception as e:
        log_info(f"[ENHANCED_TYPING] Enhanced typing failed: {e}")
        return False


async def _type_with_enhanced_errors(page, element, text):
    """
    Type text with enhanced error and correction patterns
    Improved timing calculations and more realistic error behavior
    """
    typing_session = _create_typing_session(text)
    
    i = 0
    while i < len(text):
        char = text[i]
        
        # Enhanced thinking pause logic
        if _should_pause_while_typing(i, len(text)):
            thinking_delay = _get_enhanced_typing_delay(1.2, 'thinking')
            await asyncio.sleep(thinking_delay)
        
        # Enhanced error decision with context awareness
        if _should_make_enhanced_error(char, i, text, typing_session):
            chars_typed = await _make_enhanced_typing_error(page, char, text, i)
            typing_session['errors_made'] += 1
            typing_session['last_error_pos'] = i
        else:
            # Normal character typing
            await page.keyboard.type(char)
            chars_typed = 1
        
        # Enhanced character-specific delay
        char_delay = _get_character_typing_delay(char, typing_session)
        await asyncio.sleep(char_delay)
        
        i += chars_typed


def _create_typing_session(text):
    """Create typing session context for enhanced behavior"""
    return {
        'text_length': len(text),
        'start_time': time.time(),
        'errors_made': 0,
        'last_error_pos': -1,
        'typing_speed': random.uniform(2.5, 4.5),  # chars per second
        'error_rate': random.uniform(0.02, 0.08),  # 2-8% error rate
        'fatigue_factor': 1.0
    }


def _should_pause_while_typing(position, text_length):
    """Enhanced logic for thinking pauses during typing"""
    # More pauses at sentence boundaries
    if position > 0 and position < text_length - 1:
        # Pause after punctuation
        if text[position - 1] in '.!?':
            return random.random() < 0.7  # 70% chance
        
        # Pause after commas
        if text[position - 1] in ',;:':
            return random.random() < 0.3  # 30% chance
        
        # Random thinking pauses
        return random.random() < 0.05  # 5% chance
    
    return False


def _should_make_enhanced_error(char, position, text, session):
    """
    Enhanced error decision logic with context awareness
    Considers fatigue, recent errors, and character difficulty
    """
    base_error_rate = session['error_rate']
    
    # Increase error rate with fatigue over time
    elapsed_time = time.time() - session['start_time']
    fatigue_multiplier = 1.0 + (elapsed_time / 60) * 0.3  # 30% increase per minute
    
    # Reduce error rate immediately after an error (concentration effect)
    if session['last_error_pos'] >= 0 and position - session['last_error_pos'] < 5:
        fatigue_multiplier *= 0.5
    
    # Increase error rate for difficult characters
    if char in '{}[]()":;\'':
        fatigue_multiplier *= 1.5
    
    # Don't make errors at the very beginning or end
    if position < 2 or position > len(text) - 3:
        return False
    
    adjusted_error_rate = base_error_rate * fatigue_multiplier
    return random.random() < adjusted_error_rate


async def _make_enhanced_typing_error(page, char, text, position):
    """
    Make enhanced typing error with improved correction patterns
    Returns number of characters that were effectively typed
    """
    error_types = ['wrong_char', 'double_char', 'transpose', 'skip_char']
    
    # Remove transpose if near end of text
    if position >= len(text) - 2:
        error_types.remove('transpose')
    
    error_type = random.choice(error_types)
    
    if error_type == 'wrong_char':
        # Type wrong character then correct
        wrong_char = _get_enhanced_similar_char(char)
        await page.keyboard.type(wrong_char)
        
        # Realize error and correct
        await _enhanced_error_correction(page, 1)
        await page.keyboard.type(char)
        return 1
        
    elif error_type == 'double_char':
        # Type character twice then correct
        await page.keyboard.type(char + char)
        
        # Realize error and correct
        await _enhanced_error_correction(page, 1)
        return 1
        
    elif error_type == 'transpose':
        # Type next character first, then current
        next_char = text[position + 1]
        await page.keyboard.type(next_char + char)
        
        # Realize error and correct both
        await _enhanced_error_correction(page, 2)
        await page.keyboard.type(char + next_char)
        return 2  # We typed both characters
        
    elif error_type == 'skip_char':
        # Skip character, then realize and go back
        next_char = text[position + 1] if position + 1 < len(text) else ''
        if next_char:
            await page.keyboard.type(next_char)
            
            # Realize error and correct
            await _enhanced_error_correction(page, 1)
            await page.keyboard.type(char + next_char)
            return 2
        else:
            # Just type the character normally if at end
            await page.keyboard.type(char)
            return 1
    
    return 1


async def _enhanced_error_correction(page, chars_to_delete):
    """Enhanced error correction with realistic timing"""
    # Pause to "realize" the error
    realization_delay = _get_enhanced_typing_delay(0.6, 'error_realization')
    await asyncio.sleep(realization_delay)
    
    # Delete wrong characters with natural timing
    for _ in range(chars_to_delete):
        await page.keyboard.press('Backspace')
        backspace_delay = _get_enhanced_typing_delay(0.12, 'correction')
        await asyncio.sleep(backspace_delay)
    
    # Brief pause before retyping
    correction_pause = _get_enhanced_typing_delay(0.25, 'correction_pause')
    await asyncio.sleep(correction_pause)


def _get_enhanced_similar_char(char):
    """
    Enhanced similar character logic with better keyboard layout awareness
    """
    # Enhanced QWERTY layout with more comprehensive mappings
    enhanced_layout = {
        'q': ['w', 'a', '1'], 'w': ['q', 'e', 's', '2'], 'e': ['w', 'r', 'd', '3'],
        'r': ['e', 't', 'f', '4'], 't': ['r', 'y', 'g', '5'], 'y': ['t', 'u', 'h', '6'],
        'u': ['y', 'i', 'j', '7'], 'i': ['u', 'o', 'k', '8'], 'o': ['i', 'p', 'l', '9'],
        'p': ['o', 'l', '0'], 'a': ['q', 's', 'z'], 's': ['w', 'a', 'd', 'x', 'z'],
        'd': ['e', 's', 'f', 'c', 'x'], 'f': ['r', 'd', 'g', 'v', 'c'],
        'g': ['t', 'f', 'h', 'b', 'v'], 'h': ['y', 'g', 'j', 'n', 'b'],
        'j': ['u', 'h', 'k', 'm', 'n'], 'k': ['i', 'j', 'l', 'm'],
        'l': ['o', 'k', 'p'], 'z': ['a', 's', 'x'], 'x': ['z', 's', 'd', 'c'],
        'c': ['x', 'd', 'f', 'v'], 'v': ['c', 'f', 'g', 'b'],
        'b': ['v', 'g', 'h', 'n'], 'n': ['b', 'h', 'j', 'm'],
        'm': ['n', 'j', 'k'], ' ': ['n', 'b', 'v']  # Common spacebar errors
    }
    
    char_lower = char.lower()
    
    if char_lower in enhanced_layout:
        similar_chars = enhanced_layout[char_lower]
        similar = random.choice(similar_chars)
        return similar.upper() if char.isupper() else similar
    
    # Fallback for special characters
    if char.isdigit():
        # Adjacent number errors
        digit_map = {'1': ['2', 'q'], '2': ['1', '3', 'w'], '3': ['2', '4', 'e'],
                    '4': ['3', '5', 'r'], '5': ['4', '6', 't'], '6': ['5', '7', 'y'],
                    '7': ['6', '8', 'u'], '8': ['7', '9', 'i'], '9': ['8', '0', 'o'],
                    '0': ['9', 'p']}
        if char in digit_map:
            return random.choice(digit_map[char])
    
    return char  # Return original if no similar char found


def _get_character_typing_delay(char, session):
    """
    Enhanced character-specific typing delay with consistent interface
    """
    base_delay = 1.0 / session['typing_speed']
    
    # Character-specific adjustments
    if char == ' ':
        # Spaces often have longer delays (thinking)
        base_delay *= random.uniform(1.2, 2.0)
    elif char in '.!?':
        # Sentence endings have longer pauses
        base_delay *= random.uniform(2.0, 3.5)
    elif char in ',;:':
        # Punctuation has medium pauses
        base_delay *= random.uniform(1.3, 2.2)
    elif char in '()[]{}':
        # Brackets require more thought
        base_delay *= random.uniform(1.4, 2.0)
    elif char.isupper():
        # Capital letters (shift key) take slightly longer
        base_delay *= random.uniform(1.1, 1.3)
    elif char in 'etaoinshrdlu':
        # Common letters are faster
        base_delay *= random.uniform(0.8, 1.0)
    
    # Apply fatigue factor
    base_delay *= session['fatigue_factor']
    
    # Add natural variation
    variation = base_delay * 0.3
    final_delay = base_delay + random.uniform(-variation, variation)
    
    return max(0.02, final_delay)  # Minimum 20ms delay


def _get_enhanced_typing_delay(base_time, context):
    """
    Enhanced typing delay with consistent interface and context awareness
    """
    # Context-specific multipliers
    context_multipliers = {
        'focus': random.uniform(0.8, 1.2),
        'thinking': random.uniform(0.9, 1.4),
        'completion': random.uniform(0.7, 1.1),
        'error_realization': random.uniform(1.2, 1.8),
        'correction': random.uniform(0.9, 1.1),
        'correction_pause': random.uniform(0.8, 1.3)
    }
    
    multiplier = context_multipliers.get(context, 1.0)
    
    # Add natural variation
    variation = base_time * 0.25
    final_delay = base_time * multiplier + random.uniform(-variation, variation)
    
    return max(0.05, final_delay)  # Minimum 50ms delay

async def _human_click_with_timeout_async(page, element, log_prefix="HUMAN_CLICK"):
    """
    ENHANCED: Human-like click with robust timeout handling and error recovery
    """
    try:
        # Set shorter timeout to avoid long retry loops
        original_timeout = getattr(page, '_timeout_settings', {}).get('default_timeout', 30000)
        if hasattr(page, 'set_default_timeout'):
            page.set_default_timeout(5000)  # 5 seconds max
        
        try:
            # Human-like interaction with centralized timing
            from ..human_behavior_core.timing_engine import get_timing_manager
            timing_manager = get_timing_manager()
            
            await element.hover()
            hover_delay = timing_manager.get_delay('mouse_movement', 'hover_duration', 'click')
            await asyncio.sleep(hover_delay)
            
            await element.click()
            click_delay = timing_manager.get_delay('mouse_movement', 'click_delay', 'click')
            await asyncio.sleep(click_delay)
            
            log_info(f"[{log_prefix}] [OK] Enhanced human click successful")
            return True
            
        finally:
            # Always restore original timeout
            if hasattr(page, 'set_default_timeout'):
                page.set_default_timeout(original_timeout)
                
    except Exception as e:
        log_info(f"[{log_prefix}] Human behavior failed: {str(e)[:100]}")
        
        # Fallback to simple click
        try:
            await element.click()
            return True
        except Exception as final_e:
            log_info(f"[{log_prefix}] Final click fallback failed: {str(final_e)[:100]}")
            return False

async def simulate_page_scan_async(page):
    """
    ENHANCED: Simulate page scanning with improved behavior quality and robust error handling
    """
    try:
        log_info("[ASYNC_HUMAN] Starting enhanced page scan")
        
        # Enhanced page scanning with better patterns
        success = await asyncio.wait_for(
            _enhanced_page_scanning_behavior(page),
            timeout=10.0
        )
        if success:
            log_info("[ASYNC_HUMAN] Enhanced page scan completed")
            return
        
        # Fallback to unified system
        from ..human_behavior_unified import simulate_page_scan_unified
        await asyncio.wait_for(
            simulate_page_scan_unified(page),
            timeout=10.0
        )
        
    except Exception as e:
        log_info(f"[ASYNC_HUMAN] Page scan simulation error: {str(e)[:100]}")
        # Simple fallback
        try:
            import random
            await asyncio.sleep(random.uniform(0.5, 1.5))
        except Exception:
            pass

async def simulate_mouse_movement_to_element_async(page, element):
    """
    ENHANCED: Simulate human mouse movement to element with better precision and robust error handling
    """
    try:
        # Enhanced element movement with better error handling
        success = await asyncio.wait_for(
            _enhanced_mouse_to_element_movement(page, element),
            timeout=3.0
        )
        if not success:
            # Fallback to basic movement (original logic)
            await _fallback_mouse_to_element(page, element)
            
    except Exception as e:
        log_info(f"[ASYNC_HUMAN] Mouse movement to element error: {str(e)[:100]}")
        # Simple fallback
        try:
            await element.hover()
        except Exception:
            pass

async def simulate_random_browsing_async(page):
    """
    ENHANCED: Simulate human browsing with consolidated behavior patterns and robust error handling
    """
    try:
        log_info("[ASYNC_HUMAN] Starting enhanced human browsing")
        
        # Enhanced browsing behavior with consolidated patterns
        await asyncio.wait_for(
            _enhanced_browsing_patterns(page),
            timeout=15.0
        )
        
        log_info("[ASYNC_HUMAN] Enhanced human browsing completed")
        
    except Exception as e:
        log_info(f"[ASYNC_HUMAN] Random browsing simulation error: {str(e)[:100]}")
        # Simple fallback
        try:
            import random
            await asyncio.sleep(random.uniform(1.0, 3.0))
        except Exception:
            pass

async def _enhanced_page_scanning_behavior(page):
    """
    Enhanced page scanning with consolidated scrolling and mouse movement
    Eliminates duplicate code while improving behavior quality
    """
    try:
        viewport = await page.viewport_size()
        if not viewport:
            return False
        
        # Choose scanning pattern based on page type
        scan_patterns = ['visual_scan', 'scroll_scan', 'mixed_scan']
        pattern = random.choice(scan_patterns)
        
        if pattern == 'visual_scan':
            await _enhanced_visual_scan_pattern(page, viewport)
        elif pattern == 'scroll_scan':
            await _enhanced_scroll_scan_pattern(page, viewport)
        else:  # mixed_scan
            await _enhanced_mixed_scan_pattern(page, viewport)
        
        return True
        
    except Exception as e:
        log_info(f"[ENHANCED_SCAN] Enhanced page scanning failed: {e}")
        return False


async def _enhanced_visual_scan_pattern(page, viewport):
    """Enhanced visual scanning with natural reading patterns"""
    try:
        # Natural reading patterns (F-pattern or Z-pattern)
        if random.random() < 0.6:  # 60% F-pattern, 40% Z-pattern
            # F-pattern: horizontal at top, middle, then vertical scan
            scan_points = [
                (viewport['width'] * 0.1, viewport['height'] * 0.2),
                (viewport['width'] * 0.8, viewport['height'] * 0.2),
                (viewport['width'] * 0.1, viewport['height'] * 0.4),
                (viewport['width'] * 0.6, viewport['height'] * 0.4),
                (viewport['width'] * 0.1, viewport['height'] * 0.7),
            ]
        else:
            # Z-pattern: top-left to top-right, diagonal, bottom sweep
            scan_points = [
                (viewport['width'] * 0.1, viewport['height'] * 0.2),
                (viewport['width'] * 0.8, viewport['height'] * 0.2),
                (viewport['width'] * 0.4, viewport['height'] * 0.5),
                (viewport['width'] * 0.1, viewport['height'] * 0.8),
                (viewport['width'] * 0.8, viewport['height'] * 0.8),
            ]
        
        # Execute scanning movements with natural timing
        for i, (x, y) in enumerate(scan_points):
            await page.mouse.move(x, y, steps=random.randint(6, 12))
            
            # Natural reading pause
            read_time = random.uniform(0.8, 1.8)
            await asyncio.sleep(read_time)
        
    except Exception as e:
        log_debug(f"[ENHANCED_SCAN] Visual scan pattern failed: {e}")


async def _enhanced_scroll_scan_pattern(page, viewport):
    """Enhanced scroll scanning with natural scrolling behavior"""
    try:
        scroll_sessions = random.randint(2, 4)
        
        for session in range(scroll_sessions):
            # Variable scroll amounts - start small, increase, then decrease
            if session == 0:
                scroll_amount = random.randint(100, 200)  # Initial peek
            elif session == scroll_sessions - 1:
                scroll_amount = random.randint(150, 250)  # Final scan
            else:
                scroll_amount = random.randint(200, 400)  # Main scrolling
            
            # Mostly scroll down, occasionally up
            direction = 1 if random.random() < 0.85 else -1
            await page.mouse.wheel(0, scroll_amount * direction)
            
            # Natural pause to read content
            read_pause = random.uniform(1.2, 2.5)
            await asyncio.sleep(read_pause)
            
            # Occasional mouse movement during scroll pause
            if random.random() < 0.4:
                mouse_x = random.randint(200, viewport['width'] - 200)
                mouse_y = random.randint(200, viewport['height'] - 200)
                await page.mouse.move(mouse_x, mouse_y, steps=random.randint(4, 8))
        
    except Exception as e:
        log_debug(f"[ENHANCED_SCAN] Scroll scan pattern failed: {e}")


async def _enhanced_mixed_scan_pattern(page, viewport):
    """Enhanced mixed scanning combining visual and scroll"""
    try:
        # Start with brief visual scan
        await _enhanced_visual_scan_pattern(page, viewport)
        
        # Transition pause
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # Follow with scroll scan
        await _enhanced_scroll_scan_pattern(page, viewport)
        
    except Exception as e:
        log_debug(f"[ENHANCED_SCAN] Mixed scan pattern failed: {e}")


async def _enhanced_browsing_patterns(page):
    """
    Enhanced browsing behavior with consolidated action patterns
    Eliminates duplicate scrolling and movement code
    """
    try:
        viewport = await page.viewport_size()
        if not viewport:
            return
        
        # Enhanced browsing session with weighted actions
        session_duration = random.uniform(3.0, 7.0)
        start_time = asyncio.get_event_loop().time()
        
        actions_count = 0
        max_actions = random.randint(4, 8)
        
        while (asyncio.get_event_loop().time() - start_time < session_duration and 
               actions_count < max_actions):
            
            # Weighted action selection for more natural behavior
            action = random.choices(
                ['scroll', 'mouse_move', 'pause', 'hover_scan'],
                weights=[0.4, 0.3, 0.2, 0.1]
            )[0]
            
            if action == 'scroll':
                await _enhanced_browsing_scroll(page)
            elif action == 'mouse_move':
                await _enhanced_browsing_mouse_move(page, viewport)
            elif action == 'pause':
                await _enhanced_browsing_pause()
            elif action == 'hover_scan':
                await _enhanced_browsing_hover_scan(page)
            
            actions_count += 1
            
            # Natural pause between actions
            inter_action_pause = random.uniform(0.3, 0.8)
            await asyncio.sleep(inter_action_pause)
        
    except Exception as e:
        log_info(f"[ENHANCED_BROWSING] Enhanced browsing patterns failed: {e}")


async def _enhanced_browsing_scroll(page):
    """Enhanced scrolling with natural patterns"""
    scroll_distance = random.randint(150, 400)
    direction = random.choice([1, -1])  # Mostly down, some up
    
    # Bias toward downward scrolling (85% down, 15% up)
    if random.random() < 0.85:
        direction = 1
    
    await page.mouse.wheel(0, scroll_distance * direction)


async def _enhanced_browsing_mouse_move(page, viewport):
    """Enhanced mouse movement with natural trajectories"""
    target_x = random.randint(100, viewport['width'] - 100)
    target_y = random.randint(100, viewport['height'] - 100)
    
    # Use variable steps for more natural movement
    steps = random.randint(8, 16)
    await page.mouse.move(target_x, target_y, steps=steps)


async def _enhanced_browsing_pause():
    """Enhanced pause with context-aware timing"""
    # Different pause types with different durations
    pause_types = ['quick_scan', 'reading', 'thinking']
    pause_type = random.choice(pause_types)
    
    if pause_type == 'quick_scan':
        duration = random.uniform(0.5, 1.2)
    elif pause_type == 'reading':
        duration = random.uniform(1.5, 3.0)
    else:  # thinking
        duration = random.uniform(2.0, 4.0)
    
    await asyncio.sleep(duration)


async def _enhanced_browsing_hover_scan(page):
    """Enhanced hover scanning of page elements"""
    try:
        # Look for interactive elements to hover over
        selectors = ['button', 'a', '[role="button"]', 'img', 'h1', 'h2']
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    # Pick random visible elements
                    sample_size = min(2, len(elements))
                    for element in random.sample(elements, sample_size):
                        if await element.is_visible():
                            await element.hover()
                            hover_duration = random.uniform(0.4, 0.9)
                            await asyncio.sleep(hover_duration)
                            return  # Exit after successful hover
            except Exception:
                continue
                
    except Exception as e:
        log_debug(f"[ENHANCED_BROWSING] Hover scan failed: {e}")


async def _enhanced_mouse_to_element_movement(page, element):
    """Enhanced mouse movement to specific element with better precision"""
    try:
        # Normalize element handling
        if hasattr(element, "first"):
            element = element.first()
        
        # Ensure element is in viewport
        try:
            await element.scroll_into_view_if_needed(timeout=2000)
        except Exception:
            pass
        
        # Get element position
        box = await element.bounding_box()
        if not box:
            return False
        
        # Enhanced position calculation with golden ratio
        golden_ratio = 0.618
        target_x = box['x'] + box['width'] * golden_ratio
        target_y = box['y'] + box['height'] * golden_ratio
        
        # Add natural variation
        variation_x = min(box['width'] * 0.15, 10)
        variation_y = min(box['height'] * 0.15, 8)
        
        target_x += random.uniform(-variation_x, variation_x)
        target_y += random.uniform(-variation_y, variation_y)
        
        # Ensure position stays within bounds
        target_x = max(box['x'] + 2, min(target_x, box['x'] + box['width'] - 2))
        target_y = max(box['y'] + 2, min(target_y, box['y'] + box['height'] - 2))
        
        # Enhanced movement with variable steps
        steps = random.randint(10, 18)
        await page.mouse.move(target_x, target_y, steps=steps)
        
        # Natural pause at element
        element_pause = random.uniform(0.3, 0.7)
        await asyncio.sleep(element_pause)
        
        return True
        
    except Exception as e:
        log_debug(f"[ENHANCED_MOUSE] Enhanced mouse to element failed: {e}")
        return False


async def _fallback_mouse_to_element(page, element):
    """Fallback mouse movement (original logic)"""
    try:
        # Original logic as fallback
        if hasattr(element, "first"):
            element = element.first()
        try:
            await element.scroll_into_view_if_needed(timeout=2000)
        except Exception:
            pass
        
        box = await element.bounding_box()
        if box:
            x = box['x'] + box['width'] * random.uniform(0.2, 0.8)
            y = box['y'] + box['height'] * random.uniform(0.2, 0.8)
            
            await page.mouse.move(x, y, steps=random.randint(8, 20))
            await asyncio.sleep(random.uniform(0.2, 0.6))
            
    except Exception as e:
        log_debug(f"[FALLBACK_MOUSE] Fallback mouse movement failed: {e}")


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