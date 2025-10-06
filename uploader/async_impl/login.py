"""Auto-refactored module: login"""
from .logging import logger

from .file_input import check_for_human_verification_dialog_async
from .utils_dom import check_if_already_logged_in_async
from .utils_dom import handle_email_field_verification_async
from .utils_dom import handle_recaptcha_if_present_async
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
import re
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
    process_browser_result, handle_account_task_error, handle_critical_task_error,
    clear_human_verification_badge_async
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


async def handle_login_flow_async(page, account_details: Dict) -> bool:
    """Handle Instagram login flow - enhanced to match sync version exactly"""
    try:
        log_info("🔑 [ASYNC_LOGIN] Starting enhanced login flow...")
        
        # Wait for page to be fully interactive before checking login status
        log_info("[WAIT] [ASYNC_LOGIN] Ensuring page is fully loaded before login check...")
        await asyncio.sleep(3)  # Additional wait for page stability
        
        # Import selectors for detailed checks
        try:
            from ..selectors_config import InstagramSelectors
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
                    'button:has-text("Iniciar sesión")',
                    'button:has-text("Entrar")',
                    'div[role="button"]:has-text("Log in")',
                    'div[role="button"]:has-text("Войти")',
                    'div[role="button"]:has-text("Iniciar sesión")',
                    'div[role="button"]:has-text("Entrar")',
                    
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
                    
                    # Spanish indicators
                    'svg[aria-label*="Inicio"]',
                    'svg[aria-label*="Notificaciones"]',
                    'svg[aria-label*="Nueva publicación"]',
                    '[aria-label*="Inicio"]',
                    '[aria-label*="Notificaciones"]',
                    
                    # Portuguese indicators  
                    'svg[aria-label*="Início"]',
                    'svg[aria-label*="Notificações"]',
                    'svg[aria-label*="Nova publicação"]',
                    '[aria-label*="Início"]',
                    '[aria-label*="Notificações"]',
                    
                    # Profile/user menu indicators
                    'svg[aria-label*="Profile"]',
                    'svg[aria-label*="Perfil"]',
                    '[aria-label*="Profile"]',
                    '[aria-label*="Perfil"]',
                    'img[alt*="profile picture"]',
                    'img[alt*="foto de perfil"]',
                    'img[alt*="foto do perfil"]',
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
                    'svg[aria-label*="Buscar"]',
                    '[aria-label*="Search"]',
                    '[aria-label*="Buscar"]',
                    'input[placeholder*="Search"]',
                    'input[placeholder*="Buscar"]',
                    
                    # Messages indicators
                    'svg[aria-label*="Direct"]',
                    'svg[aria-label*="Directo"]',
                    'svg[aria-label*="Direto"]',
                    '[aria-label*="Direct"]',
                    '[aria-label*="Directo"]',
                    '[aria-label*="Direto"]',
                    'a[href*="/direct/"]',
                    
                    # Activity indicators
                    'svg[aria-label*="Activity"]',
                    'svg[aria-label*="Actividad"]',
                    'svg[aria-label*="Atividade"]',
                    '[aria-label*="Activity"]',
                    '[aria-label*="Actividad"]',
                    '[aria-label*="Atividade"]',
                    
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
        
        # Pre-login verification handling: if Instagram shows a verification step (email code/2FA/email field),
        # handle it immediately instead of attempting username/password on a non-login page.
        try:
            log_info("[SEARCH] [ASYNC_LOGIN] Checking for verification before attempting login...")
            verification_type = await determine_verification_type_async(page)
            log_info(f"[SEARCH] [ASYNC_LOGIN] Pre-login verification detected: {verification_type}")
            
            if verification_type == "authenticator":
                log_info("[PHONE] [ASYNC_LOGIN] 2FA/Authenticator verification required (pre-login)")
                result = await handle_2fa_async(page, account_details)
                if result == "SUSPENDED":
                    log_info("[BLOCK] [ASYNC_LOGIN] Account suspended detected during pre-login 2FA")
                    raise Exception("SUSPENDED: Account suspended during 2FA verification")
                if result:
                    log_info("[OK] [ASYNC_LOGIN] 2FA verification completed successfully (pre-login)")
                    return True
                else:
                    log_error("[FAIL] [ASYNC_LOGIN] 2FA verification failed (pre-login)")
                    return False
            elif verification_type == "email_code":
                log_info("📧 [ASYNC_LOGIN] Email verification code required (pre-login)")
                result = await handle_email_verification_async(page, account_details)
                if result == "SUSPENDED":
                    log_info("[BLOCK] [ASYNC_LOGIN] Account suspended detected during pre-login email verification")
                    raise Exception("SUSPENDED: Account suspended during email verification")
                if result:
                    log_info("[OK] [ASYNC_LOGIN] Email verification completed successfully (pre-login)")
                    return True
                else:
                    log_error("[FAIL] [ASYNC_LOGIN] Email verification failed (pre-login)")
                    return False
            elif verification_type == "email_field":
                log_info("📧 [ASYNC_LOGIN] Email field input required (pre-login)")
                result = await handle_email_field_verification_async(page, account_details)
                if result:
                    log_info("[OK] [ASYNC_LOGIN] Email field verification completed successfully (pre-login)")
                    return True
                else:
                    log_error("[FAIL] [ASYNC_LOGIN] Email field verification failed (pre-login)")
                    return False
        except Exception as pre_ver_err:
            # If verification probe throws a critical status, bubble it up; otherwise, proceed to regular login
            if any(tag in str(pre_ver_err) for tag in [
                "SUSPENDED:", "PHONE_VERIFICATION_REQUIRED:", "HUMAN_VERIFICATION_REQUIRED:"
            ]):
                raise
            log_warning(f"[WARN] [ASYNC_LOGIN] Pre-login verification check failed: {pre_ver_err}")
        
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
            try:
                await clear_human_verification_badge_async(account_details['username'])
            except Exception:
                pass
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
            'button[aria-label*="Nueva publicación"]',
            'button[aria-label*="Criar"]',
            'svg[aria-label="Notifications"]',
            'svg[aria-label="Notificaciones"]',
            'svg[aria-label="Notificações"]',
            'svg[aria-label="Direct"]',
            'svg[aria-label="New post"]',
            'svg[aria-label*="Nueva publicación"]',
            'svg[aria-label*="Nova publicação"]',
            'main[role="main"]',
            'nav[role="navigation"]'
        ]
                # Use the proper verification type detection function (fixed import path)
        from ..email_verification_async import determine_verification_type_async
        
        verification_type = await determine_verification_type_async(page)
        log_info(f"[SEARCH] [ASYNC_LOGIN] Detected verification type: {verification_type}")
        
        if verification_type == "authenticator":
            log_info("[PHONE] [ASYNC_LOGIN] 2FA/Authenticator verification required")
            result = await handle_2fa_async(page, account_details)
            if result:
                log_info("[OK] [ASYNC_LOGIN] 2FA verification completed successfully")
                try:
                    await clear_human_verification_badge_async(account_details['username'])
                except Exception:
                    pass
                return True
            else:
                log_error("[FAIL] [ASYNC_LOGIN] 2FA verification failed")
                return False
                
        elif verification_type == "email_code":
            log_info("📧 [ASYNC_LOGIN] Email verification code required")
            result = await handle_email_verification_async(page, account_details)
            if result:
                log_info("[OK] [ASYNC_LOGIN] Email verification completed successfully")
                try:
                    await clear_human_verification_badge_async(account_details['username'])
                except Exception:
                    pass
                return True
            else:
                log_error("[FAIL] [ASYNC_LOGIN] Email verification failed")
                return False
                
        elif verification_type == "email_field":
            log_info("📧 [ASYNC_LOGIN] Email field input required")
            result = await handle_email_field_verification_async(page, account_details)
            if result:
                log_info("[OK] [ASYNC_LOGIN] Email field verification completed successfully")
                try:
                    await clear_human_verification_badge_async(account_details['username'])
                except Exception:
                    pass
                return True
            else:
                log_error("[FAIL] [ASYNC_LOGIN] Email field verification failed")
                return False
                
        elif verification_type == "unknown":
            log_info("[OK] [ASYNC_LOGIN] No verification required - checking if truly logged in...")
            
            # ACTUAL CHECK: verify logged-in indicators on the page (RU + EN)
            indicators = [
                # Russian UI
                'svg[aria-label*="Главная"]',
                '[aria-label*="Главная"]',
                'svg[aria-label*="Создать"]',
                'svg[aria-label*="Сообщения"]',
                'svg[aria-label*="Уведомления"]',
                'svg[aria-label*="Профиль"]',
                'a[aria-label*="Главная"]',
                # English UI
                'svg[aria-label="Notifications"]',
                'svg[aria-label="Direct"]', 
                'svg[aria-label="New post"]',
                # Spanish UI
                'svg[aria-label*="Notificaciones"]',
                'svg[aria-label*="Directo"]',
                'svg[aria-label*="Nueva publicación"]',
                'a[aria-label*="Inicio"]',
                # Portuguese UI
                'svg[aria-label*="Notificações"]',
                'svg[aria-label*="Direto"]',
                'svg[aria-label*="Nova publicação"]',
                'a[aria-label*="Início"]',
                # Common containers/links
                'main[role="main"]:not(:has(form))',
                'nav[role="navigation"]',
                'a[href="/"]',
                'a[href="/explore/"]'
            ]
            for indicator in indicators:
                try:
                    el = await page.query_selector(indicator)
                    if el and await el.is_visible():
                        log_info(f"[OK] [ASYNC_LOGIN] Looks logged in - found indicator: {indicator}")
                        return True
                except Exception:
                    continue
            
            # Fallback: navigate to home and retry a short check
            try:
                log_info("[RETRY] [ASYNC_LOGIN] Forcing navigation to home and re-checking indicators...")
                await page.goto('https://www.instagram.com/', wait_until='domcontentloaded')
                await asyncio.sleep(random.uniform(2, 4))
                for indicator in indicators:
                    try:
                        el = await page.query_selector(indicator)
                        if el and await el.is_visible():
                            log_info(f"[OK] [ASYNC_LOGIN] Logged-in indicator after reload: {indicator}")
                            try:
                                await clear_human_verification_badge_async(account_details['username'])
                            except Exception:
                                pass
                            return True
                    except Exception:
                        continue
            except Exception as nav_err:
                log_warning(f"[WARN] [ASYNC_LOGIN] Home navigation check failed: {nav_err}")
            
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
            'input[aria-label*="Teléfono"]',
            'input[aria-label*="Telefone"]',
            'input[placeholder*="Телефон"]',
            'input[placeholder*="Phone"]',
            'input[placeholder*="Teléfono"]',
            'input[placeholder*="Telefone"]',
            'input[placeholder*="Username"]',
            'input[placeholder*="Имя пользователя"]',
            'input[aria-label*="usuario"]',
            'input[placeholder*="usuario"]',
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
            'input[aria-label*="Contraseña"]',
            'input[aria-label*="Senha"]',
            'input[placeholder*="Contraseña"]',
            'input[placeholder*="Senha"]',
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
            # XPATH селекторы - более точные и надежные для всех языков
            # Основная кнопка входа (НЕ Facebook) - по тексту внутри кнопки
            '//button[@type="submit" and (contains(text(), "Log in") or contains(text(), "Войти") or contains(text(), "Iniciar sesión") or contains(text(), "Entrar") or contains(text(), "Вход"))]',
            '//button[@type="submit" and (.//div[contains(text(), "Log in") or contains(text(), "Войти") or contains(text(), "Iniciar sesión") or contains(text(), "Entrar")])]',
            '//button[@type="submit" and (.//span[contains(text(), "Log in") or contains(text(), "Войти") or contains(text(), "Iniciar sesión") or contains(text(), "Entrar")])]',
            
            # Исключаем Facebook кнопки явно
            '//button[@type="submit" and not(contains(., "Facebook")) and not(contains(., "facebook"))]',
            '//form[@id="loginForm"]//button[@type="submit"]',
            '//form[contains(@id, "login")]//button[@type="submit"]',
            
            # CSS селекторы как fallback
            'form#loginForm button[type="submit"]:not(:has-text("Facebook"))',
            'form[id*="login"] button[type="submit"]:not(:has-text("Facebook"))',
            'button[type="submit"]:not(:has-text("Facebook")):not(:has-text("facebook"))',
            
            # Instagram's dynamic class-based selectors (исключаем Facebook)
            'button[class*="_aswp"][type="submit"]:not(:has-text("Facebook"))',
            'button[class*="_aswr"][type="submit"]:not(:has-text("Facebook"))',
            'button[class*="_aswu"][type="submit"]:not(:has-text("Facebook"))',
            'button[class*="_asw_"][type="submit"]:not(:has-text("Facebook"))',
            'button[class*="_asx2"][type="submit"]:not(:has-text("Facebook"))',
            
            # Text-based селекторы (точные тексты)
            'button:has-text("Войти"):not(:has-text("Facebook"))',
            'button:has-text("Log in"):not(:has-text("Facebook"))',
            'button:has-text("Iniciar sesión"):not(:has-text("Facebook"))',
            'button:has-text("Entrar"):not(:has-text("Facebook"))',
        ]
        
        login_button = None
        for selector in login_selectors:
            try:
                login_button = await page.query_selector(selector)
                if login_button and await login_button.is_visible():
                    button_text = await login_button.text_content() or ""
                    # Убеждаемся что это НЕ Facebook кнопка
                    if 'facebook' not in button_text.lower():
                        log_info(f"[OK] [ASYNC_LOGIN] Found login button: '{button_text.strip()}'")
                        break
                    else:
                        log_info(f"[SKIP] [ASYNC_LOGIN] Skipping Facebook button: '{button_text.strip()}'")
                        login_button = None
            except:
                continue
        
        if not login_button:
            # Fallbacks: try submitting the form or pressing Enter in password field (works with dynamic, disabled buttons)
            log_info("[WARN] [ASYNC_LOGIN] Login button not found - trying form submit fallbacks")
            try:
                # Try to submit via the form element
                form_el = await page.query_selector('form#loginForm, form[id*="login"], form[action*="login"]')
                if form_el:
                    try:
                        await form_el.evaluate('(el) => el.requestSubmit ? el.requestSubmit() : el.submit()')
                        await asyncio.sleep(random.uniform(3, 5))
                        current_url = page.url
                        if '/accounts/login' not in current_url and 'instagram.com' in current_url:
                            log_info("[OK] [ASYNC_LOGIN] Login submitted via form fallback")
                            return True
                    except Exception:
                        pass
                # Press Enter on password field
                try:
                    await password_field.press('Enter')
                    await asyncio.sleep(random.uniform(3, 5))
                    current_url = page.url
                    if '/accounts/login' not in current_url and 'instagram.com' in current_url:
                        log_info("[OK] [ASYNC_LOGIN] Login submitted via Enter key fallback")
                        return True
                except Exception:
                    pass
            except Exception:
                pass
            log_info("[FAIL] [ASYNC_LOGIN] Login button not found")
            return False
        
        # Wait for button to become enabled if it's initially disabled
        try:
            is_disabled = True
            for i in range(15):  # up to ~7.5s
                try:
                    disabled_attr = await login_button.get_attribute('disabled')
                    # Check if disabled attribute is present (even if empty string)
                    is_disabled = disabled_attr is not None
                    if not is_disabled:
                        log_info(f"[OK] [ASYNC_LOGIN] Login button enabled after {i * 0.5}s")
                        break
                    log_info(f"[WAIT] [ASYNC_LOGIN] Button still disabled, waiting... ({i * 0.5}s)")
                except Exception:
                    # If we can't check, assume enabled
                    is_disabled = False
                    break
                await asyncio.sleep(0.5)
            
            if is_disabled:
                log_info("[WARN] [ASYNC_LOGIN] Login button still disabled after waiting, will try anyway")
        except Exception:
            pass

        log_info("🔐 [ASYNC_LOGIN] Clicking login button...")
        navigation_promises = [
            page.wait_for_url(re.compile(r"https://www\\.instagram\\.com/.*"), timeout=20000),
            page.wait_for_load_state('domcontentloaded', timeout=20000)
        ]
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(navigation_promises[0])
                tg.create_task(navigation_promises[1])
                await login_button.click()
        except Exception:
            try:
                await login_button.evaluate('(el) => el.click()')
            except Exception:
                try:
                    await password_field.press('Enter')
                except Exception:
                    pass
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=20000)
            except Exception:
                pass
        
        # Give time for client-side redirects/render
        await asyncio.sleep(random.uniform(3, 5))
        
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
            'input[aria-label*="Teléfono"]',
            'input[aria-label*="Telefone"]',
            'input[aria-label*="Username"]',
            'input[placeholder*="Телефон"]',
            'input[placeholder*="Phone"]',
            'input[placeholder*="Teléfono"]',
            'input[placeholder*="Telefone"]',
            'input[placeholder*="Username"]',
            'input[placeholder*="Имя пользователя"]',
            'input[aria-label*="usuario"]',
            'input[placeholder*="usuario"]',
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
            'input[aria-label*="Contraseña"]',
            'input[aria-label*="Senha"]',
            'input[placeholder*="Contraseña"]',
            'input[placeholder*="Senha"]',
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
            # XPATH селекторы - более точные и надежные для всех языков
            # Основная кнопка входа (НЕ Facebook) - по тексту внутри кнопки
            '//button[@type="submit" and (contains(text(), "Log in") or contains(text(), "Войти") or contains(text(), "Iniciar sesión") or contains(text(), "Entrar") or contains(text(), "Вход"))]',
            '//button[@type="submit" and (.//div[contains(text(), "Log in") or contains(text(), "Войти") or contains(text(), "Iniciar sesión") or contains(text(), "Entrar")])]',
            '//button[@type="submit" and (.//span[contains(text(), "Log in") or contains(text(), "Войти") or contains(text(), "Iniciar sesión") or contains(text(), "Entrar")])]',
            
            # Исключаем Facebook кнопки явно
            '//button[@type="submit" and not(contains(., "Facebook")) and not(contains(., "facebook"))]',
            '//form[@id="loginForm"]//button[@type="submit"]',
            '//form[contains(@id, "login")]//button[@type="submit"]',
            
            # CSS селекторы как fallback
            'form#loginForm button[type="submit"]:not(:has-text("Facebook"))',
            'form[id*="login"] button[type="submit"]:not(:has-text("Facebook"))',
            'button[type="submit"]:not(:has-text("Facebook")):not(:has-text("facebook"))',
            
            # Instagram's dynamic class-based selectors (исключаем Facebook)
            'button[class*="_aswp"][type="submit"]:not(:has-text("Facebook"))',
            'button[class*="_aswr"][type="submit"]:not(:has-text("Facebook"))',
            'button[class*="_aswu"][type="submit"]:not(:has-text("Facebook"))',
            'button[class*="_asw_"][type="submit"]:not(:has-text("Facebook"))',
            'button[class*="_asx2"][type="submit"]:not(:has-text("Facebook"))',
            
            # Text-based селекторы (точные тексты)
            'button:has-text("Войти"):not(:has-text("Facebook"))',
            'button:has-text("Log in"):not(:has-text("Facebook"))',
            'button:has-text("Iniciar sesión"):not(:has-text("Facebook"))',
            'button:has-text("Entrar"):not(:has-text("Facebook"))',
        ]
        
        login_button = None
        for selector in login_selectors:
            try:
                login_button = await page.query_selector(selector)
                if login_button and await login_button.is_visible():
                    # Verify this is actually a login button
                    button_text = await login_button.text_content() or ""
                    if (any(keyword in button_text.lower() for keyword in ['войти', 'log in', 'login', 'submit', 'iniciar sesión', 'entrar', 'entrar']) and 
                        'facebook' not in button_text.lower()):
                        log_info(f"[OK] [ASYNC_LOGIN] Found login button: '{button_text.strip()}'")
                        break
                    elif 'facebook' in button_text.lower():
                        log_info(f"[SKIP] [ASYNC_LOGIN] Skipping Facebook button: '{button_text.strip()}'")
                        login_button = None
            except:
                continue
        
        if not login_button:
            # Fallbacks: submit the form or press Enter in password field
            log_info("[WARN] [ASYNC_LOGIN] Login button not found - trying form submit fallbacks")
            try:
                form_el = await page.query_selector('form#loginForm, form[id*="login"], form[action*="login"]')
                if form_el:
                    try:
                        await form_el.evaluate('(el) => el.requestSubmit ? el.requestSubmit() : el.submit()')
                        await asyncio.sleep(random.uniform(3, 5))
                        return await handle_login_completion_async(page, account_details)
                    except Exception:
                        pass
                try:
                    await password_field.press('Enter')
                    await asyncio.sleep(random.uniform(3, 5))
                    return await handle_login_completion_async(page, account_details)
                except Exception:
                    pass
            except Exception:
                pass
            log_info("[FAIL] [ASYNC_LOGIN] Login button not found")
            return False
        
        # Human-like interaction before clicking
        await login_button.hover()
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # Wait for button to become enabled if disabled
        try:
            is_disabled = True
            for i in range(15):  # up to ~7.5s
                try:
                    disabled_attr = await login_button.get_attribute('disabled')
                    # Check if disabled attribute is present (even if empty string)
                    is_disabled = disabled_attr is not None
                    if not is_disabled:
                        log_info(f"[OK] [ASYNC_LOGIN] Login button enabled after {i * 0.5}s")
                        break
                    log_info(f"[WAIT] [ASYNC_LOGIN] Button still disabled, waiting... ({i * 0.5}s)")
                except Exception:
                    # If we can't check, assume enabled
                    is_disabled = False
                    break
                await asyncio.sleep(0.5)
            
            if is_disabled:
                log_info("[WARN] [ASYNC_LOGIN] Login button still disabled after waiting, will try anyway")
        except Exception:
            pass

        log_info("🔐 [ASYNC_LOGIN] Clicking login button...")
        try:
            await login_button.click()
        except Exception:
            try:
                await login_button.evaluate('(el) => el.click()')
            except Exception:
                try:
                    await password_field.press('Enter')
                except Exception:
                    pass
        
        # Wait for navigation/load to settle to avoid destroyed execution context
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=20000)
        except Exception:
            pass
        # Small human-like wait
        await asyncio.sleep(random.uniform(2, 4))
        
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
        
        # Wait for page to respond and stabilize after navigation
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=20000)
        except Exception:
            pass
        await asyncio.sleep(random.uniform(2, 4))
        
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
        if ('/two_factor/' in current_url or '/challenge/' in current_url or '/accounts/login' in current_url or 
            'auth_platform/codeentry' in current_url or '/codeentry/' in current_url):
            log_info(f"[ALERT] [ASYNC_LOGIN] Still on authentication/verification page: {current_url}")
            # НЕ ПРОВЕРЯЕМ индикаторы входа - мы все еще в процессе аутентификации
            # Переходим к обработке верификации
        elif 'instagram.com' in current_url:
            # Additional verification - look for logged-in elements
            logged_in_indicators = [
                # English
                'svg[aria-label="Notifications"]',
                'svg[aria-label="Direct"]', 
                'svg[aria-label="New post"]',
                'svg[aria-label*="Home"]',
                # Russian
                'svg[aria-label*="Главная"]',
                'svg[aria-label*="Создать"]',
                'svg[aria-label*="Сообщения"]',
                'svg[aria-label*="Уведомления"]',
                # Spanish
                'svg[aria-label*="Notificaciones"]',
                'svg[aria-label*="Inicio"]',
                'svg[aria-label*="Nueva publicación"]',
                'svg[aria-label*="Directo"]',
                # Portuguese
                'svg[aria-label*="Notificações"]',
                'svg[aria-label*="Início"]',
                'svg[aria-label*="Nova publicação"]',
                'svg[aria-label*="Direto"]',
                # Common elements
                'a[href*="/accounts/edit/"]',
                'main[role="main"]',
                'nav[role="navigation"]',
                'a[href="/"]',  # Home link
                'a[href="/explore/"]',  # Explore link
                'a[href="/reels/"]',  # Reels link
                'a[href*="/accounts/activity/"]',  # Activity link
            ]
            
            # Retry loop to avoid 'execution context destroyed' and allow UI to render
            for _ in range(3):
                for indicator in logged_in_indicators:
                    try:
                        element = await page.query_selector(indicator)
                        if element and await element.is_visible():
                            log_info(f"[OK] [ASYNC_LOGIN] Login successful - found logged-in indicator: {indicator}")
                            try:
                                await clear_human_verification_badge_async(account_details['username'])
                            except Exception:
                                pass
                            return True
                    except Exception as e:
                        # If destroyed due to navigation, wait and retry
                        if 'Execution context was destroyed' in str(e):
                            await asyncio.sleep(1.0)
                            continue
                        log_warning(f"[WARN] [ASYNC_LOGIN] Error checking indicator {indicator}: {e}")
                        continue
                # brief wait between retries
                await asyncio.sleep(1.0)
        
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
        
        # Check for verification requirements (fixed import path)
        from ..email_verification_async import determine_verification_type_async
        
        verification_type = await determine_verification_type_async(page)
        log_info(f"[SEARCH] [ASYNC_LOGIN] Detected verification type: {verification_type}")
        
        if verification_type == "authenticator":
            log_info("[PHONE] [ASYNC_LOGIN] 2FA/Authenticator verification required")
            result = await handle_2fa_async(page, account_details)
            if result == "SUSPENDED":
                log_info("[BLOCK] [ASYNC_LOGIN] Account suspended detected right after 2FA")
                return "SUSPENDED"
            if result:
                log_info("[OK] [ASYNC_LOGIN] 2FA verification completed successfully")
                try:
                    await clear_human_verification_badge_async(account_details['username'])
                except Exception:
                    pass
                return True
            else:
                log_error("[FAIL] [ASYNC_LOGIN] 2FA verification failed")
                return False
                
        elif verification_type == "email_code":
            log_info("📧 [ASYNC_LOGIN] Email verification code required")
            result = await handle_email_verification_async(page, account_details)
            if result == "SUSPENDED":
                log_info("[BLOCK] [ASYNC_LOGIN] Account suspended detected right after email verification")
                return "SUSPENDED"
            if result:
                log_info("[OK] [ASYNC_LOGIN] Email verification completed successfully")
                try:
                    await clear_human_verification_badge_async(account_details['username'])
                except Exception:
                    pass
                return True
            else:
                log_error("[FAIL] [ASYNC_LOGIN] Email verification failed - LOGIN NOT COMPLETED")
                return False  # КРИТИЧНО: НЕ ПРОДОЛЖАЕМ если верификация failed!
                
        elif verification_type == "email_field":
            log_info("📧 [ASYNC_LOGIN] Email field input required")
            result = await handle_email_field_verification_async(page, account_details)
            if result:
                log_info("[OK] [ASYNC_LOGIN] Email field verification completed successfully")
                try:
                    await clear_human_verification_badge_async(account_details['username'])
                except Exception:
                    pass
                return True
            else:
                log_error("[FAIL] [ASYNC_LOGIN] Email field verification failed")
                return False
                
        elif verification_type == "unknown":
            log_info("[OK] [ASYNC_LOGIN] No verification required - checking if truly logged in...")
            
            # ТОЛЬКО ЗДЕСЬ проверяем индикаторы успешного входа (RU + EN + ES + PT)
            logged_in_indicators = [
                # Russian UI
                'svg[aria-label*="Главная"]',
                '[aria-label*="Главная"]',
                'svg[aria-label*="Создать"]',
                'svg[aria-label*="Сообщения"]',
                'svg[aria-label*="Уведомления"]',
                'svg[aria-label*="Профиль"]',
                'a[aria-label*="Главная"]',
                # English UI
                'svg[aria-label="Notifications"]',
                'svg[aria-label="Direct"]', 
                'svg[aria-label="New post"]',
                'svg[aria-label*="Home"]',
                # Spanish UI
                'svg[aria-label*="Notificaciones"]',
                'svg[aria-label*="Inicio"]',
                'svg[aria-label*="Nueva publicación"]',
                'svg[aria-label*="Directo"]',
                'a[aria-label*="Inicio"]',
                # Portuguese UI
                'svg[aria-label*="Notificações"]',
                'svg[aria-label*="Início"]',
                'svg[aria-label*="Nova publicação"]',
                'svg[aria-label*="Direto"]',
                'a[aria-label*="Início"]',
                # Common containers/links
                'main[role="main"]:not(:has(form))',
                'nav[role="navigation"]',
                'a[href="/"]',
                'a[href="/explore/"]'
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

async def detect_suspended_account_async(page) -> bool:
    """Detect if account is suspended/disabled/locked based on page text and alerts."""
    try:
        body_text = (await page.inner_text('body')) or ''
    except Exception:
        body_text = ''
    text = body_text.lower()
    keywords = [
        'suspend', 'disabled', 'locked', 'temporarily locked', 'violation',
        'приостановлен', 'заблокирован', 'заблокирована', 'временно заблокирован',
        'ваша учетная запись заблокирована', 'аккаунт заблокирован', 'аккаунт отключен'
    ]
    if any(k in text for k in keywords):
        return True
    try:
        # Look for alert/error containers possibly holding suspension messages
        error_elements = await page.query_selector_all('div[role="alert"], .error-message, [data-testid="login-error"]')
        for el in error_elements:
            try:
                if await el.is_visible():
                    t = (await el.text_content() or '').lower()
                    if any(k in t for k in keywords):
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False

async def handle_2fa_async(page, account_details):
    """Handle 2FA authentication using API instead of pyotp"""
    try:
        tfa_secret = account_details.get('tfa_secret')
        if not tfa_secret:
            log_info("[FAIL] [ASYNC_2FA] 2FA required but no secret provided")
            return False
        
        log_info("[PHONE] [ASYNC_2FA] Handling 2FA authentication...")
        
        # Find 2FA code input using centralized selectors
        code_input = None
        from ..selectors_config import InstagramSelectors as SelectorConfig
        code_selectors = SelectorConfig.TFA_INPUT + [
            # Additional dynamic selectors
            'input[id^="_r_"]',
            'input[type="text"][dir="ltr"][autocomplete="off"]',
            'label[for^="_r_"] + input',
            'input[aria-describedby="verificationCodeDescription"]',
            'input[type="tel"][maxlength]',
            'input[type="tel"]',
            'label:has-text("Код") + input'
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
            # Возможно, сразу телефонная проверка / другая форма
            from .utils_dom import check_for_phone_verification_page_async
            phone_check = await check_for_phone_verification_page_async(page)
            if phone_check.get('requires_phone_verification'):
                log_error("[PHONE] [ASYNC_2FA] Phone verification required instead of 2FA input")
                raise Exception("PHONE_VERIFICATION_REQUIRED: Detected phone verification after 2FA phase")
            return False
        
        # Retry up to 3 times with fresh TOTP (30s window)
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            # Get 2FA code from API freshly each attempt
            code = await get_2fa_code_async(tfa_secret)
            if not code:
                log_info("[FAIL] [ASYNC_2FA] Failed to get 2FA code from API")
                return False
            
            log_info(f"[PHONE] [ASYNC_2FA] Attempt {attempt}/{max_attempts}: Got 2FA code from API: {code}")
            
            # Enter 2FA code
            await code_input.click()
            await asyncio.sleep(random.uniform(0.4, 0.9))
            await code_input.fill("")
            await asyncio.sleep(random.uniform(0.2, 0.4))
            await code_input.type(code, delay=int(random.uniform(30, 70)))
            await asyncio.sleep(random.uniform(0.8, 1.6))
            
            # Submit 2FA form
            submit_button = await page.query_selector(
                'button[type="submit"], '
                'button:has-text("Confirm"), '
                'button:has-text("Подтвердить"), '
                'button:has-text("Confirmar"), '
                'button:has-text("Confirmação"), '
                'div[role="button"]:has-text("Confirm"), '
                'div[role="button"]:has-text("Подтвердить"), '
                'div[role="button"]:has-text("Confirmar"), '
                'div[role="button"]:has-text("Confirmação")'
            )
            if submit_button:
                await submit_button.click()
            else:
                # Fallback: press Enter
                try:
                    await page.keyboard.press('Enter')
                except Exception:
                    pass
            
            # Wait/poll for redirect or success indicators up to ~15s
            success = False
            for _ in range(15):
                await asyncio.sleep(1.0)
                current_url = page.url
                if '/two_factor/' not in current_url and '/challenge/' not in current_url and '/accounts/login' not in current_url:
                    success = True
                    break
            
            if success:
                log_info("[OK] [ASYNC_2FA] 2FA authentication successful - redirected from 2FA page")
                # Handle save login info dialog after successful 2FA
                await handle_save_login_info_dialog_async(page)
                # Сразу после успеха проверим требование телефона
                try:
                    from .utils_dom import check_for_phone_verification_page_async
                    phone_check = await check_for_phone_verification_page_async(page)
                    if phone_check.get('requires_phone_verification'):
                        log_error("[PHONE] [ASYNC_2FA] Phone verification required after successful 2FA")
                        raise Exception("PHONE_VERIFICATION_REQUIRED: Phone verification detected post-2FA")
                except Exception as e:
                    # Пробросим дальше для верхнего уровня
                    raise
                # After success, check if account is suspended/locked
                if await detect_suspended_account_async(page):
                    log_info("[BLOCK] [ASYNC_2FA] Account appears suspended/locked after 2FA")
                    return "SUSPENDED"
                return True
            
            # Check for explicit error messages; ignore generic labels
            try:
                error_elements = await page.query_selector_all('[role="alert"], .error-message, ._aa4a')
                error_text_combined = " ".join([((await el.text_content()) or "").strip() for el in error_elements])
                normalized = error_text_combined.lower()
                if any(kw in normalized for kw in [
                    'invalid', 'incorrect', 'try again', 'неверн', 'ошиб', 'повторите', 'некоррект', 'try again later'
                ]):
                    log_error(f"[FAIL] [ASYNC_2FA] 2FA error: {error_text_combined}")
                    # On explicit error, retry with fresh code unless attempts exhausted
                    continue
            except Exception:
                pass
            
            # Если не редиректнуло и нет явной ошибки — проверим телефонную верификацию перед ретраем
            try:
                from .utils_dom import check_for_phone_verification_page_async
                phone_check = await check_for_phone_verification_page_async(page)
                if phone_check.get('requires_phone_verification'):
                    log_error("[PHONE] [ASYNC_2FA] Phone verification required during 2FA")
                    raise Exception("PHONE_VERIFICATION_REQUIRED: Phone verification detected during 2FA")
            except Exception as e:
                raise

            # If still here: no redirect and no explicit error; retry once more
            log_info(f"[WARN] [ASYNC_2FA] No redirect after submit; retrying ({attempt}/{max_attempts})")
        
        log_info("[FAIL] [ASYNC_2FA] 2FA verification failed after retries")
        return False
             
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_2FA] Error in 2FA handling: {str(e)}")
        return False

async def handle_email_verification_async(page, account_details):
    """Handle email verification code entry"""
    try:
        email_login = account_details.get('email_login')
        email_password = account_details.get('email_password')
        
        # Fallback: if email not provided, use username@rambler.ru and Instagram password
        if not email_login or not email_password:
            try:
                username = account_details.get('username')
                insta_password = account_details.get('password')
                if username and insta_password:
                    fallback_email = f"{username}@rambler.ru"
                    email_login = email_login or fallback_email
                    email_password = email_password or insta_password
                    log_info(f"[ASYNC_EMAIL] [FALLBACK] Using fallback email credentials: {email_login} / <insta-password>")
                else:
                    log_info("[FAIL] [ASYNC_EMAIL] Missing username/password for fallback email credentials")
                    return False
            except Exception as cred_err:
                log_info(f"[FAIL] [ASYNC_EMAIL] Could not build fallback email credentials: {cred_err}")
                return False
        
        log_info("📧 [ASYNC_EMAIL] Starting email verification...")
        
        # Wait for page to fully load and render email verification elements
        log_info("📧 [ASYNC_EMAIL] Waiting for email verification page to load...")
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=20000)
            await page.wait_for_load_state('networkidle', timeout=15000)
        except Exception as e:
            log_info(f"[WARN] [ASYNC_EMAIL] Load state wait failed: {e}")
        
        # Additional wait for JavaScript rendering
        await asyncio.sleep(random.uniform(3, 5))
        
        # Check if page content indicates email verification
        try:
            page_text = await page.inner_text('body') or ""
            log_info(f"📧 [ASYNC_EMAIL] Page content check - contains verification keywords: {any(kw in page_text.lower() for kw in ['code', 'código', 'verification', 'verificación', 'confirm'])}")
        except Exception:
            pass
        
        # Find verification code input with retry logic
        code_input = None
        code_selectors = [
            # Instagram's dynamic email/code fields for auth_platform/codeentry
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
            'input[placeholder*="código"]',  # Spanish
            'label:has-text("Код") + input',  # По label "Код"
            
            # XPath селекторы для более надежного поиска
            '//input[@type="text" and (@autocomplete="off" or @autocomplete="one-time-code")]',
            '//input[@inputmode="numeric"]',
            '//input[@maxlength="6" or @maxlength="8"]',
            '//input[contains(@placeholder, "code") or contains(@placeholder, "código") or contains(@placeholder, "код")]',
        ]
        # Дополнительные селекторы из реального HTML Instagram
        additional_selectors = [
            'input[id^="_r_"]',  # Instagram использует динамические ID типа "_r_7_"
            'input[type="text"][dir="ltr"][autocomplete="off"]',
            'label[for^="_r_"] + input',  # По связанному label
        ]
        code_selectors.extend(additional_selectors)
        
        # Retry finding code input field with delays (page might still be loading)
        max_retries = 10
        for retry in range(max_retries):
            log_info(f"📧 [ASYNC_EMAIL] Searching for code input field (attempt {retry + 1}/{max_retries})...")
            
            for selector in code_selectors:
                try:
                    code_input = await page.query_selector(selector)
                    if code_input and await code_input.is_visible():
                        log_info(f"📧 [ASYNC_EMAIL] Found code input field with selector: {selector}")
                        break
                except Exception as e:
                    log_info(f"[WARN] [ASYNC_EMAIL] Error with selector {selector}: {e}")
                    continue
            
            if code_input:
                break
            
            # Wait before next retry
            log_info(f"📧 [ASYNC_EMAIL] Code input not found, waiting before retry {retry + 1}/{max_retries}...")
            await asyncio.sleep(2)
        
        if not code_input:
            log_info("[FAIL] [ASYNC_EMAIL] Email verification code input not found after retries")
            # Debug: log page content for investigation
            try:
                page_html = await page.content()
                log_info(f"[DEBUG] [ASYNC_EMAIL] Page URL: {page.url}")
                log_info(f"[DEBUG] [ASYNC_EMAIL] Page title: {await page.title()}")
                log_info(f"[DEBUG] [ASYNC_EMAIL] Page contains input fields: {page_html.count('<input')}")
            except Exception:
                pass
            return False
        
        # Extended polling for code arrival (avoid premature exit on slow providers like FirstMail)
        total_wait_seconds = 240  # ~4 minutes budget
        per_call_retries = 1      # let outer loop control timing; inner call should be quick
        attempt = 0
        start_ts = time.time()
        while time.time() - start_ts < total_wait_seconds:
            attempt += 1
            log_info(f"📧 [ASYNC_EMAIL] Polling mailbox for code (attempt {attempt}, elapsed {int(time.time() - start_ts)}s/{total_wait_seconds}s)...")
            verification_code = await get_email_verification_code_async(email_login, email_password, max_retries=per_call_retries)
            if not verification_code:
                # Wait a bit and retry until timeout
                await asyncio.sleep(random.uniform(8, 15))
                continue
            
            log_info(f"📧 [ASYNC_EMAIL] Got verification code: {verification_code}")
            
            # Enter verification code (human-like)
            await code_input.click()
            await asyncio.sleep(random.uniform(0.4, 0.9))
            await code_input.fill("")
            await asyncio.sleep(random.uniform(0.2, 0.4))
            await code_input.type(verification_code, delay=int(random.uniform(30, 70)))
            await asyncio.sleep(random.uniform(0.8, 1.6))
            
            # Submit verification form - using centralized selectors
            from ..selectors_config import InstagramSelectors as SelectorConfig
            submit_selectors = SelectorConfig.EMAIL_SUBMIT_BUTTONS + [
                # Additional continue/next button variants
                'div[role="button"]:has-text("Продолжить")',
                'div[role="button"]:has-text("Continue")',
                'div[role="button"]:has-text("Continuar")',  # ES/PT
                'div[role="button"]:has-text("Seguir")',      # PT
                'div[role="button"]:has-text("Siguiente")',  # ES
                'div[role="button"]:has-text("Weiter")',      # DE
                'div[role="button"]:has-text("Fortfahren")',  # DE
                'div[role="button"]:has-text("Επόμενο")',     # EL
                'div[role="button"]:has-text("Συνέχεια")',    # EL
                'button:has-text("Продолжить")',
                'button:has-text("Continue")', 
                'button:has-text("Continuar")',
                'button:has-text("Seguir")',
                'button:has-text("Siguiente")',
                'button:has-text("Weiter")',      # DE
                'button:has-text("Fortfahren")', # DE
                'button:has-text("Επόμενο")',     # EL
                'button:has-text("Συνέχεια")',    # EL
                '[role="button"]:has(span:has-text("Продолжить"))',
                '[role="button"]:has(span:has-text("Continue"))',
                '[role="button"]:has(span:has-text("Continuar"))',
                '[role="button"]:has(span:has-text("Seguir"))',
                '[role="button"]:has(span:has-text("Siguiente"))',
                '[role="button"]:has(span:has-text("Weiter"))',      # DE
                '[role="button"]:has(span:has-text("Fortfahren"))',  # DE
                '[role="button"]:has(span:has-text("Επόμενο"))',     # EL
                '[role="button"]:has(span:has-text("Συνέχεια"))',    # EL
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
            else:
                log_error("📧 [ASYNC_EMAIL] Submit button not found - trying Enter key")
                await code_input.press('Enter')
            
            # Poll up to 30s for redirect off verification pages (can be slow)
            success = False
            for _ in range(30):
                await asyncio.sleep(1.0)
                current_url = page.url
                if ('/accounts/login' not in current_url and 'challenge' not in current_url and 
                    'auth_platform' not in current_url and '/codeentry/' not in current_url):
                    success = True
                    break
            
            # Check for human verification requirement FIRST
            if not success:
                human_verification_result = await check_for_human_verification_dialog_async(page, account_details)
                if human_verification_result.get('requires_human_verification', False):
                    log_error(f"[BOT] [ASYNC_EMAIL] Human verification required after email: {human_verification_result.get('message', 'Unknown reason')}")
                    raise Exception(f"HUMAN_VERIFICATION_REQUIRED: {human_verification_result.get('message', 'Human verification required after email verification')}")
            
            if success:
                log_info("[OK] [ASYNC_EMAIL] Email verification successful")
                await handle_save_login_info_dialog_async(page)
                try:
                    await clear_human_verification_badge_async(account_details['username'])
                except Exception:
                    pass
                # After success, check if account is suspended/locked
                if await detect_suspended_account_async(page):
                    log_info("[BLOCK] [ASYNC_EMAIL] Account appears suspended/locked after email verification")
                    return "SUSPENDED"
                return True
            
            # Inspect explicit error messages to decide retry
            try:
                error_elements = await page.query_selector_all('[role="alert"], .error-message, ._aa4a')
                error_text_combined = " ".join([((await el.text_content()) or "").strip() for el in error_elements])
                normalized = error_text_combined.lower()
                if any(kw in normalized for kw in [
                    'invalid', 'incorrect', 'неверн', 'ошиб', 'повторите', 'некоррект'
                ]):
                    log_error(f"[FAIL] [ASYNC_EMAIL] Email code error: {error_text_combined}")
                    # retry with a new code
                    continue
            except Exception:
                pass
            
            log_info(f"[WARN] [ASYNC_EMAIL] No redirect after code submit; will continue polling if time budget remains")
        
        log_info("[FAIL] [ASYNC_EMAIL] Email verification failed after extended waiting")
        return False
            
    except Exception as e:
        log_error(f"[FAIL] [ASYNC_EMAIL] Error in email verification: {str(e)}")
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
            # Russian
            'сохранить данные для входа', 'сохранить информацию', 'запомнить', 'сохранить',
            # English
            'save login info', 'save your login info', 'remember', 'save',
            # Spanish
            'guardar información de inicio', 'guardar inicio de sesión', 'guardar', 'recordar',
            # Portuguese
            'salvar informações de login', 'salvar login', 'salvar', 'lembrar'
        ]
        
        is_save_login_dialog = any(keyword in page_text.lower() for keyword in save_login_keywords)
        log_info(f"[ASYNC_SAVE_LOGIN] Save login dialog detected: {is_save_login_dialog}")
        
        if is_save_login_dialog:
            log_info("[ASYNC_SAVE_LOGIN] 💾 Save login info dialog found")
            
            # Look for "Save" button
            save_button_selectors = [
                'button:has-text("Сохранить")',
                'button:has-text("Save")',
                'button:has-text("Guardar")',
                'button:has-text("Salvar")',
                'div[role="button"]:has-text("Сохранить")',
                'div[role="button"]:has-text("Save")',
                'div[role="button"]:has-text("Guardar")',
                'div[role="button"]:has-text("Salvar")',
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
                'button:has-text("Ahora no")',
                'button:has-text("Agora não")',
                'div[role="button"]:has-text("Не сейчас")',
                'div[role="button"]:has-text("Not now")',
                'div[role="button"]:has-text("Ahora no")',
                'div[role="button"]:has-text("Agora não")',
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

__all__ = ['handle_login_flow_async', 'check_post_login_verifications_async', 'perform_instagram_login_optimized_async', 'perform_enhanced_instagram_login_async', 'handle_login_completion_async', 'handle_2fa_async', 'handle_email_verification_async', 'handle_save_login_info_dialog_async']


# === PASS 4: SAFE SHIMS FOR LOGIN FUNCTIONS (non-breaking) ===
from .logging import logger
import inspect, asyncio
try:
    _orig_handle_login_flow_async = handle_login_flow_async
except Exception:
    _orig_handle_login_flow_async = None
async def handle_login_flow_async(*args, **kwargs):
    """Auto-wrapped login function. Behavior unchanged; adds structured logs."""
    logger.info('LOGIN:handle_login_flow_async start')
    try:
        if _orig_handle_login_flow_async is None:
            logger.warning('LOGIN:handle_login_flow_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_handle_login_flow_async):
            res = await _orig_handle_login_flow_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_handle_login_flow_async(*args, **kwargs))
        logger.info('LOGIN:handle_login_flow_async ok')
        return res
    except Exception as e:
        logger.error('LOGIN:handle_login_flow_async error: ' + repr(e))
        raise
try:
    _orig_check_post_login_verifications_async = check_post_login_verifications_async
except Exception:
    _orig_check_post_login_verifications_async = None
async def check_post_login_verifications_async(*args, **kwargs):
    """Auto-wrapped login function. Behavior unchanged; adds structured logs."""
    logger.info('LOGIN:check_post_login_verifications_async start')
    try:
        if _orig_check_post_login_verifications_async is None:
            logger.warning('LOGIN:check_post_login_verifications_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_check_post_login_verifications_async):
            res = await _orig_check_post_login_verifications_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_check_post_login_verifications_async(*args, **kwargs))
        logger.info('LOGIN:check_post_login_verifications_async ok')
        return res
    except Exception as e:
        logger.error('LOGIN:check_post_login_verifications_async error: ' + repr(e))
        raise
try:
    _orig_perform_instagram_login_optimized_async = perform_instagram_login_optimized_async
except Exception:
    _orig_perform_instagram_login_optimized_async = None
async def perform_instagram_login_optimized_async(*args, **kwargs):
    """Auto-wrapped login function. Behavior unchanged; adds structured logs."""
    logger.info('LOGIN:perform_instagram_login_optimized_async start')
    try:
        if _orig_perform_instagram_login_optimized_async is None:
            logger.warning('LOGIN:perform_instagram_login_optimized_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_perform_instagram_login_optimized_async):
            res = await _orig_perform_instagram_login_optimized_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_perform_instagram_login_optimized_async(*args, **kwargs))
        logger.info('LOGIN:perform_instagram_login_optimized_async ok')
        return res
    except Exception as e:
        logger.error('LOGIN:perform_instagram_login_optimized_async error: ' + repr(e))
        raise
try:
    _orig_perform_enhanced_instagram_login_async = perform_enhanced_instagram_login_async
except Exception:
    _orig_perform_enhanced_instagram_login_async = None
async def perform_enhanced_instagram_login_async(*args, **kwargs):
    """Auto-wrapped login function. Behavior unchanged; adds structured logs."""
    logger.info('LOGIN:perform_enhanced_instagram_login_async start')
    try:
        if _orig_perform_enhanced_instagram_login_async is None:
            logger.warning('LOGIN:perform_enhanced_instagram_login_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_perform_enhanced_instagram_login_async):
            res = await _orig_perform_enhanced_instagram_login_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_perform_enhanced_instagram_login_async(*args, **kwargs))
        logger.info('LOGIN:perform_enhanced_instagram_login_async ok')
        return res
    except Exception as e:
        logger.error('LOGIN:perform_enhanced_instagram_login_async error: ' + repr(e))
        raise
try:
    _orig_handle_login_completion_async = handle_login_completion_async
except Exception:
    _orig_handle_login_completion_async = None
async def handle_login_completion_async(*args, **kwargs):
    """Auto-wrapped login function. Behavior unchanged; adds structured logs."""
    logger.info('LOGIN:handle_login_completion_async start')
    try:
        if _orig_handle_login_completion_async is None:
            logger.warning('LOGIN:handle_login_completion_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_handle_login_completion_async):
            res = await _orig_handle_login_completion_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_handle_login_completion_async(*args, **kwargs))
        logger.info('LOGIN:handle_login_completion_async ok')
        return res
    except Exception as e:
        logger.error('LOGIN:handle_login_completion_async error: ' + repr(e))
        raise
try:
    _orig_handle_2fa_async = handle_2fa_async
except Exception:
    _orig_handle_2fa_async = None
async def handle_2fa_async(*args, **kwargs):
    """Auto-wrapped login function. Behavior unchanged; adds structured logs."""
    logger.info('LOGIN:handle_2fa_async start')
    try:
        if _orig_handle_2fa_async is None:
            logger.warning('LOGIN:handle_2fa_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_handle_2fa_async):
            res = await _orig_handle_2fa_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_handle_2fa_async(*args, **kwargs))
        logger.info('LOGIN:handle_2fa_async ok')
        return res
    except Exception as e:
        logger.error('LOGIN:handle_2fa_async error: ' + repr(e))
        raise
try:
    _orig_handle_email_verification_async = handle_email_verification_async
except Exception:
    _orig_handle_email_verification_async = None
async def handle_email_verification_async(*args, **kwargs):
    """Auto-wrapped login function. Behavior unchanged; adds structured logs."""
    logger.info('LOGIN:handle_email_verification_async start')
    try:
        if _orig_handle_email_verification_async is None:
            logger.warning('LOGIN:handle_email_verification_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_handle_email_verification_async):
            res = await _orig_handle_email_verification_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_handle_email_verification_async(*args, **kwargs))
        logger.info('LOGIN:handle_email_verification_async ok')
        return res
    except Exception as e:
        logger.error('LOGIN:handle_email_verification_async error: ' + repr(e))
        raise
try:
    _orig_handle_save_login_info_dialog_async = handle_save_login_info_dialog_async
except Exception:
    _orig_handle_save_login_info_dialog_async = None
async def handle_save_login_info_dialog_async(*args, **kwargs):
    """Auto-wrapped login function. Behavior unchanged; adds structured logs."""
    logger.info('LOGIN:handle_save_login_info_dialog_async start')
    try:
        if _orig_handle_save_login_info_dialog_async is None:
            logger.warning('LOGIN:handle_save_login_info_dialog_async original missing; no-op')
            return None
        if inspect.iscoroutinefunction(_orig_handle_save_login_info_dialog_async):
            res = await _orig_handle_save_login_info_dialog_async(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: _orig_handle_save_login_info_dialog_async(*args, **kwargs))
        logger.info('LOGIN:handle_save_login_info_dialog_async ok')
        return res
    except Exception as e:
        logger.error('LOGIN:handle_save_login_info_dialog_async error: ' + repr(e))
        raise