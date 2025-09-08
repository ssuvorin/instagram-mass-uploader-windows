"""Auto-refactored module: file_input"""
from .logging import logger

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
                'выбрать на компьютере', 'select from computer', 'seleccionar desde el ordenador', 'seleccionar desde la computadora', 'selecionar do computador',
                'выбрать файлы', 'select files', 'seleccionar archivos', 'selecionar arquivos',
                'перетащите файлы', 'drag files', 'arrastra los archivos', 'arrastar arquivos',
                'загрузить файл', 'upload file', 'subir archivo', 'carregar arquivo'
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

__all__ = ['check_for_file_dialog_async', 'find_file_input_adaptive_async', 'is_valid_file_input_async', 'find_input_via_dialog_structure_async', 'find_input_via_button_async', 'find_input_via_form_context_async', 'find_input_via_css_patterns_async', 'find_input_via_broad_search_async', 'check_for_human_verification_dialog_async']


# === v2 strategy-based discovery (non-breaking additions) ===
from typing import Optional, Any, List
from .providers import register, strategies

# Try registering known strategies if they exist in this module
KNOWN = [
    "find_input_via_dialog_structure_async",
    "find_input_via_button_async",
    "find_input_via_form_context_async",
    "find_input_via_css_patterns_async",
    "find_input_via_broad_search_async",
]

for name in KNOWN:
    if name in globals() and callable(globals()[name]):
        register(globals()[name])

async def find_file_input_unified_v2_async(page, *, timeout: Optional[float] = None) -> Optional[Any]:
    """v2: iterate over registered strategies and return the first successful element/handle."""
    for provider in strategies():
        try:
            res = await provider(page, timeout=timeout) if "timeout" in provider.__code__.co_varnames else await provider(page)
            if res:
                return res
        except Exception:
            # keep parity with current permissive behavior
            continue
    return None


# === PASS 5 ADAPTIVE FILE INPUT SHIM (non-breaking) ===
try:
    _orig_find_file_input_adaptive_async = find_file_input_adaptive_async
except Exception:
    _orig_find_file_input_adaptive_async = None

from .logging import logger

async def find_file_input_adaptive_async(*args, **kwargs):
    """Try v2 unified file input first; fallback to original behavior."""
    try:
        from .file_input import find_file_input_unified_v2_async as _v2_unified
        res = await _v2_unified(*args, **kwargs)
        if res:
            return res
    except Exception as e:
        logger.debug("v2 unified file input failed: " + repr(e))
    if _orig_find_file_input_adaptive_async is not None:
        return await _orig_find_file_input_adaptive_async(*args, **kwargs)
    return None
