"""Auto-refactored module: crop"""
from .logging import logger

from .human import _human_click_with_timeout_async
from .utils_dom import _find_any_available_option_async
from .utils_dom import _find_original_by_first_position_async
from .utils_dom import _find_original_by_svg_icon_async
from .utils_dom import _find_original_by_text_content_async
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
                        # Lazy import to avoid circular dependency with .upload
                        try:
                            from .upload import handle_reels_dialog_async as _handle_reels_dialog_async
                            await _handle_reels_dialog_async(page)
                        except Exception as import_error:
                            log_info(f"[ASYNC_CROP] Reels dialog handler unavailable: {repr(import_error)}")
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

__all__ = ['handle_crop_async']


# === PASS 5 SAFE SHIMS CROP (non-breaking) ===
from .logging import logger
import inspect, asyncio
try:
    _orig_handle_crop_async = handle_crop_async
except Exception:
    _orig_handle_crop_async = None
async def handle_crop_async(*args, **kwargs):
    """Auto-wrapped function (CROP). Behavior unchanged; adds structured logs."""
    logger.info('CROP:handle_crop_async start')
    try:
        if _orig_handle_crop_async is None:
            logger.warning('CROP:handle_crop_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_handle_crop_async):
            res = await _orig_handle_crop_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_handle_crop_async(*args, **kwargs))
        logger.info('CROP:handle_crop_async ok')
        return res
    except Exception as e:
        logger.error('CROP:handle_crop_async error: ' + repr(e))
        raise
try:
    _orig__verify_crop_page_adaptive_async = _verify_crop_page_adaptive_async
except Exception:
    _orig__verify_crop_page_adaptive_async = None
async def _verify_crop_page_adaptive_async(*args, **kwargs):
    """Auto-wrapped function (CROP). Behavior unchanged; adds structured logs."""
    logger.info('CROP:_verify_crop_page_adaptive_async start')
    try:
        if _orig__verify_crop_page_adaptive_async is None:
            logger.warning('CROP:_verify_crop_page_adaptive_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig__verify_crop_page_adaptive_async):
            res = await _orig__verify_crop_page_adaptive_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig__verify_crop_page_adaptive_async(*args, **kwargs))
        logger.info('CROP:_verify_crop_page_adaptive_async ok')
        return res
    except Exception as e:
        logger.error('CROP:_verify_crop_page_adaptive_async error: ' + repr(e))
        raise
try:
    _orig__handle_crop_adaptive_async = _handle_crop_adaptive_async
except Exception:
    _orig__handle_crop_adaptive_async = None
async def _handle_crop_adaptive_async(*args, **kwargs):
    """Auto-wrapped function (CROP). Behavior unchanged; adds structured logs."""
    logger.info('CROP:_handle_crop_adaptive_async start')
    try:
        if _orig__handle_crop_adaptive_async is None:
            logger.warning('CROP:_handle_crop_adaptive_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig__handle_crop_adaptive_async):
            res = await _orig__handle_crop_adaptive_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig__handle_crop_adaptive_async(*args, **kwargs))
        logger.info('CROP:_handle_crop_adaptive_async ok')
        return res
    except Exception as e:
        logger.error('CROP:_handle_crop_adaptive_async error: ' + repr(e))
        raise
try:
    _orig__find_crop_by_semantic_attributes_async = _find_crop_by_semantic_attributes_async
except Exception:
    _orig__find_crop_by_semantic_attributes_async = None
async def _find_crop_by_semantic_attributes_async(*args, **kwargs):
    """Auto-wrapped function (CROP). Behavior unchanged; adds structured logs."""
    logger.info('CROP:_find_crop_by_semantic_attributes_async start')
    try:
        if _orig__find_crop_by_semantic_attributes_async is None:
            logger.warning('CROP:_find_crop_by_semantic_attributes_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig__find_crop_by_semantic_attributes_async):
            res = await _orig__find_crop_by_semantic_attributes_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig__find_crop_by_semantic_attributes_async(*args, **kwargs))
        logger.info('CROP:_find_crop_by_semantic_attributes_async ok')
        return res
    except Exception as e:
        logger.error('CROP:_find_crop_by_semantic_attributes_async error: ' + repr(e))
        raise
try:
    _orig__find_crop_by_svg_content_async = _find_crop_by_svg_content_async
except Exception:
    _orig__find_crop_by_svg_content_async = None
async def _find_crop_by_svg_content_async(*args, **kwargs):
    """Auto-wrapped function (CROP). Behavior unchanged; adds structured logs."""
    logger.info('CROP:_find_crop_by_svg_content_async start')
    try:
        if _orig__find_crop_by_svg_content_async is None:
            logger.warning('CROP:_find_crop_by_svg_content_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig__find_crop_by_svg_content_async):
            res = await _orig__find_crop_by_svg_content_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig__find_crop_by_svg_content_async(*args, **kwargs))
        logger.info('CROP:_find_crop_by_svg_content_async ok')
        return res
    except Exception as e:
        logger.error('CROP:_find_crop_by_svg_content_async error: ' + repr(e))
        raise
try:
    _orig__find_crop_by_context_analysis_async = _find_crop_by_context_analysis_async
except Exception:
    _orig__find_crop_by_context_analysis_async = None
async def _find_crop_by_context_analysis_async(*args, **kwargs):
    """Auto-wrapped function (CROP). Behavior unchanged; adds structured logs."""
    logger.info('CROP:_find_crop_by_context_analysis_async start')
    try:
        if _orig__find_crop_by_context_analysis_async is None:
            logger.warning('CROP:_find_crop_by_context_analysis_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig__find_crop_by_context_analysis_async):
            res = await _orig__find_crop_by_context_analysis_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig__find_crop_by_context_analysis_async(*args, **kwargs))
        logger.info('CROP:_find_crop_by_context_analysis_async ok')
        return res
    except Exception as e:
        logger.error('CROP:_find_crop_by_context_analysis_async error: ' + repr(e))
        raise
try:
    _orig__find_crop_by_fallback_patterns_async = _find_crop_by_fallback_patterns_async
except Exception:
    _orig__find_crop_by_fallback_patterns_async = None
async def _find_crop_by_fallback_patterns_async(*args, **kwargs):
    """Auto-wrapped function (CROP). Behavior unchanged; adds structured logs."""
    logger.info('CROP:_find_crop_by_fallback_patterns_async start')
    try:
        if _orig__find_crop_by_fallback_patterns_async is None:
            logger.warning('CROP:_find_crop_by_fallback_patterns_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig__find_crop_by_fallback_patterns_async):
            res = await _orig__find_crop_by_fallback_patterns_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig__find_crop_by_fallback_patterns_async(*args, **kwargs))
        logger.info('CROP:_find_crop_by_fallback_patterns_async ok')
        return res
    except Exception as e:
        logger.error('CROP:_find_crop_by_fallback_patterns_async error: ' + repr(e))
        raise
try:
    _orig__human_click_crop_button_async = _human_click_crop_button_async
except Exception:
    _orig__human_click_crop_button_async = None
async def _human_click_crop_button_async(*args, **kwargs):
    """Auto-wrapped function (CROP). Behavior unchanged; adds structured logs."""
    logger.info('CROP:_human_click_crop_button_async start')
    try:
        if _orig__human_click_crop_button_async is None:
            logger.warning('CROP:_human_click_crop_button_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig__human_click_crop_button_async):
            res = await _orig__human_click_crop_button_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig__human_click_crop_button_async(*args, **kwargs))
        logger.info('CROP:_human_click_crop_button_async ok')
        return res
    except Exception as e:
        logger.error('CROP:_human_click_crop_button_async error: ' + repr(e))
        raise
try:
    _orig__select_original_aspect_ratio_async = _select_original_aspect_ratio_async
except Exception:
    _orig__select_original_aspect_ratio_async = None
async def _select_original_aspect_ratio_async(*args, **kwargs):
    """Auto-wrapped function (CROP). Behavior unchanged; adds structured logs."""
    logger.info('CROP:_select_original_aspect_ratio_async start')
    try:
        if _orig__select_original_aspect_ratio_async is None:
            logger.warning('CROP:_select_original_aspect_ratio_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig__select_original_aspect_ratio_async):
            res = await _orig__select_original_aspect_ratio_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig__select_original_aspect_ratio_async(*args, **kwargs))
        logger.info('CROP:_select_original_aspect_ratio_async ok')
        return res
    except Exception as e:
        logger.error('CROP:_select_original_aspect_ratio_async error: ' + repr(e))
        raise