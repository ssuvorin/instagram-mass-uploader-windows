"""
YouTube Shorts automation helpers (async) using Playwright page and Dolphin profile.
Implements human-like behavior, robust selectors, retries, and clean async APIs.

This module is platform-agnostic: it assumes an already connected Playwright `page`
from an existing Dolphin Anty profile. It focuses solely on automating YouTube login,
navigation to Studio, and Shorts upload + publish.
"""

import asyncio
import random
from typing import List, Optional, Dict

from playwright.async_api import Page

from .logging_utils import log_info, log_warning, log_error


# Robust selector sets with fallbacks
YOUTUBE_SELECTORS: Dict[str, List[str]] = {
    # Google login
    'email_input': [
        'input[type="email"]#identifierId',
        '//input[@type="email" and @id="identifierId"]',
        'input[name="identifier"]',
    ],
    'email_next': [
        '//div[@id="identifierNext"]//button',
        '#identifierNext button',
        'button[jsname="LgbsSe"]',
    ],
    'password_input': [
        'input[type="password"][name="Passwd"]',
        '//input[@type="password" and @name="Passwd"]',
        '#password input[type="password"]',
    ],
    'password_next': [
        '//div[@id="passwordNext"]//button',
        '#passwordNext button',
        'button[jsname="LgbsSe"]',
    ],

    # Verification
    'verify_title': ['//h1[contains(text(), "Verify that it")]', '//h1[contains(., "Verify")]'],
    'try_another_way': ['//button[contains(text(), "Try another way")]'],
    'captcha_img': ['#captchaimg'],
    'captcha_input': ['input[name="ca"]'],

    # YouTube Studio + Upload flow
    'file_input': ['input[type="file"][name="Filedata"]', 'input[type="file"]'],
    'select_files_btn': ['#select-files-button button', '//ytcp-button//button'],
    'title_input': ['div[contenteditable="true"][aria-label*="title"]'],
    'description_input': ['div[contenteditable="true"][aria-label*="description"]'],
    'shorts_checkbox': ['//tp-yt-paper-checkbox[@id="shorts-checkbox"]'],
    'next_button': ['//button[contains(text(), "Next")]', 'ytcp-button[id="next-button"] button'],
    'publish_button': [
        '//button[contains(text(), "Publish")]',
        '//button[contains(text(), "Upload")]',
        '//ytcp-button[@id="done-button"]',
    ],

    # Generic close buttons
    'close_buttons': [
        '[aria-label="Close"]',
        '//button[contains(text(), "Skip")]',
        '//button[contains(text(), "Maybe later")]',
        '//button[contains(text(), "Not now")]',
        '//button[contains(text(), "Continue")]',
    ],
}


async def human_like_delay(min_ms: int = 400, max_ms: int = 1500) -> None:
    delay = random.uniform(min_ms / 1000.0, max_ms / 1000.0)
    await asyncio.sleep(delay)


async def find_element_by_selectors(page: Page, selectors: List[str], timeout: int = 30000):
    if isinstance(selectors, str):
        selectors = [selectors]
    for selector in selectors:
        try:
            el = page.locator(selector)
            await el.wait_for(state='visible', timeout=timeout)
            return el
        except Exception:
            continue
    return None


async def human_like_type(page: Page, element_or_selector, text: str) -> None:
    try:
        if isinstance(element_or_selector, str):
            element = await find_element_by_selectors(page, [element_or_selector])
            if not element:
                raise RuntimeError(f"Element not found: {element_or_selector}")
        else:
            element = element_or_selector

        await element.click()
        await human_like_delay(200, 600)
        try:
            await element.select_text()
        except Exception:
            try:
                await element.select_all()
            except Exception:
                pass
        await human_like_delay(120, 300)

        for i, ch in enumerate(text):
            await element.type(ch, delay=random.randint(40, 140))
            if i % random.randint(5, 12) == 0 and i > 0:
                await human_like_delay(120, 500)
    except Exception as e:
        log_error(f"[YT TYPE] Error while typing: {e}")
        raise


async def login_to_google(page: Page, email: str, password: str) -> bool:
    try:
        log_info(f"[YT LOGIN] Starting login for {email}")
        await page.goto('https://accounts.google.com/signin/v2/identifier', wait_until='networkidle')
        await human_like_delay(800, 1800)

        email_input = await find_element_by_selectors(page, YOUTUBE_SELECTORS['email_input'])
        if not email_input:
            raise RuntimeError('Email input not found')
        await human_like_type(page, email_input, email)
        await human_like_delay(300, 800)

        next_btn = await find_element_by_selectors(page, YOUTUBE_SELECTORS['email_next'])
        if not next_btn:
            raise RuntimeError('Next button (email) not found')
        await next_btn.click()
        await human_like_delay(1500, 3000)

        pwd_input = await find_element_by_selectors(page, YOUTUBE_SELECTORS['password_input'], timeout=40000)
        if not pwd_input:
            raise RuntimeError('Password input not found')
        await human_like_type(page, pwd_input, password)
        await human_like_delay(300, 800)

        pwd_next = await find_element_by_selectors(page, YOUTUBE_SELECTORS['password_next'])
        if not pwd_next:
            raise RuntimeError('Next button (password) not found')
        await pwd_next.click()
        await human_like_delay(2500, 5000)

        # Basic verification handling (best-effort)
        await _handle_basic_verification(page, password)

        # Confirm logged in by navigating to YouTube
        try:
            await page.goto('https://www.youtube.com', wait_until='networkidle')
            user_avatar = page.locator('button[aria-label*="Account menu"]')
            if await user_avatar.is_visible():
                log_info(f"[YT LOGIN] Success for {email}")
                return True
        except Exception:
            pass
        log_warning("[YT LOGIN] Could not confirm login via avatar; proceeding optimistically")
        return True
    except Exception as e:
        log_error(f"[YT LOGIN] Error: {e}")
        return False


async def _handle_basic_verification(page: Page, password: str) -> None:
    try:
        await human_like_delay(600, 1200)
        verify_el = page.locator(YOUTUBE_SELECTORS['verify_title'][0])
        if await verify_el.is_visible():
            log_info('[YT VERIFY] Verification page detected')
            try_another = page.locator(YOUTUBE_SELECTORS['try_another_way'][0])
            for _ in range(2):
                if await try_another.is_visible():
                    await try_another.click()
                    await human_like_delay(1000, 2000)
        # CAPTCHA placeholder wait
        captcha_img = page.locator(YOUTUBE_SELECTORS['captcha_img'][0])
        if await captcha_img.is_visible():
            log_warning('[YT VERIFY] CAPTCHA detected; waiting for manual/solver')
            await human_like_delay(3000, 6000)
        # Recovery password re-entry
        rec_pwd = page.locator('input[type="password"]')
        if await rec_pwd.is_visible():
            await human_like_type(page, rec_pwd, password)
            next_btn = page.locator('//button[contains(text(), "Next")]')
            if await next_btn.is_visible():
                await next_btn.click()
                await human_like_delay(1500, 3000)
    except Exception as e:
        log_warning(f"[YT VERIFY] Warning while handling verification: {e}")


async def navigate_to_studio(page: Page) -> None:
    log_info('[YT NAV] Navigating to YouTube Studio')
    await page.goto('https://studio.youtube.com', wait_until='networkidle')
    await human_like_delay(1200, 2600)
    # Attempt to close any popups
    await _close_popups(page)


async def _close_popups(page: Page) -> None:
    try:
        await human_like_delay(200, 600)
        try:
            await page.click('body', position={"x": 100, "y": 100}, timeout=1000)
        except Exception:
            pass
        for selector in YOUTUBE_SELECTORS['close_buttons']:
            try:
                btn = page.locator(selector)
                if await btn.is_visible():
                    await btn.click()
                    await human_like_delay(400, 900)
                    log_info(f"[YT NAV] Closed popup: {selector}")
            except Exception:
                continue
    except Exception as e:
        log_warning(f"[YT NAV] Error closing popups: {e}")


async def upload_and_publish_short(page: Page, video_path: str, title: Optional[str], description: Optional[str]) -> bool:
    try:
        log_info(f"[YT UPLOAD] Uploading file: {video_path}")
        await page.goto('https://studio.youtube.com/channel/UC/videos/upload', wait_until='networkidle')
        await human_like_delay(1200, 2500)

        file_input = page.locator(YOUTUBE_SELECTORS['file_input'][0])
        if not await file_input.is_visible():
            select_btn = page.locator(YOUTUBE_SELECTORS['select_files_btn'][0])
            try:
                await file_input.set_input_files(video_path)
            except Exception:
                pass
            if await select_btn.is_visible():
                await select_btn.click()
        else:
            await file_input.set_input_files(video_path)

        await human_like_delay(2500, 5000)
        await page.wait_for_selector('div[contenteditable="true"]', timeout=60000)

        if title:
            title_input = page.locator(YOUTUBE_SELECTORS['title_input'][0]).first
            if await title_input.is_visible():
                await human_like_type(page, title_input, title)
                log_info(f"[YT UPLOAD] Title set")

        if description:
            desc_input = page.locator(YOUTUBE_SELECTORS['description_input'][0]).first
            if await desc_input.is_visible():
                await human_like_type(page, desc_input, description)
                log_info("[YT UPLOAD] Description set")

        shorts_checkbox = page.locator(YOUTUBE_SELECTORS['shorts_checkbox'][0])
        try:
            if await shorts_checkbox.is_visible():
                await shorts_checkbox.check()
                log_info('[YT UPLOAD] Marked as Shorts')
                await human_like_delay(400, 900)
        except Exception:
            pass

        # Walk through Next steps
        for _ in range(4):
            await human_like_delay(700, 1500)
            next_btn = page.locator(YOUTUBE_SELECTORS['next_button'][0])
            if await next_btn.is_visible():
                await next_btn.click()
                await human_like_delay(1200, 2200)
            else:
                break

        # Final publish
        published = False
        for selector in YOUTUBE_SELECTORS['publish_button']:
            btn = page.locator(selector)
            if await btn.is_visible():
                await btn.click()
                log_info('[YT UPLOAD] Publish clicked')
                published = True
                await human_like_delay(1500, 2800)
                break
        if not published:
            log_warning('[YT UPLOAD] Publish button not found')

        return published
    except Exception as e:
        log_error(f"[YT UPLOAD] Error: {e}")
        return False


async def perform_youtube_operations_async(page: Page, account_details: Dict, videos: List[Dict], video_files: List[str]) -> int:
    """
    Performs YouTube operations: login, navigate to Studio, upload each video.
    Returns number of successfully uploaded videos.
    """
    success_count = 0
    email = account_details.get('email') or account_details.get('username') or ''
    password = account_details.get('password') or ''

    # Login
    if not await login_to_google(page, email, password):
        return 0

    await navigate_to_studio(page)

    for i, file_path in enumerate(video_files):
        title = None
        description = None
        try:
            v = videos[i] if i < len(videos) else None
            if isinstance(v, dict):
                title = v.get('title')
                description = v.get('description')
        except Exception:
            pass

        ok = await upload_and_publish_short(page, file_path, title, description)
        if ok:
            success_count += 1
        # Human-like pause between uploads
        await human_like_delay(1500, 4000)

    return success_count


