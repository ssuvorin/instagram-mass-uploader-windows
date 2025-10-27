"""
YouTube Shorts automation helpers (async) using Playwright page and Dolphin profile.
Implements human-like behavior, robust selectors, retries, and clean async APIs.

This module is platform-agnostic: it assumes an already connected Playwright `page`
from an existing Dolphin Anty profile. It focuses solely on automating YouTube login,
navigation to Studio, and Shorts upload + publish.
"""

import asyncio
import random
import os
from typing import List, Optional, Dict

from playwright.async_api import Page

import logging
from .audio_recaptcha_solver import solve_recaptcha_with_audio
from .enhanced_captcha_solver import EnhancedCaptchaSolver, CaptchaConfig

# Initialize centralized Django logger for YouTube automation
logger = logging.getLogger('youtube.automation')


# Robust selector sets with fallbacks - Universal XPath selectors
YOUTUBE_SELECTORS: Dict[str, List[str]] = {
    # Google login - Universal selectors
    'email_input': [
        '//input[@type="email" and (@id="identifierId" or @name="identifier")]',
        '//input[@type="email"]',
        '//input[@name="identifier"]',
    ],
    'email_next': [
        '//button[@type="submit" and contains(@class, "VfPpkd-LgbsSe")]',
        '//div[@id="identifierNext"]//button',
        '//button[contains(@class, "VfPpkd-LgbsSe") and (contains(., "Next") or contains(., "Siguiente") or contains(., "Weiter") or contains(., "Suivant"))]',
        '//button[@type="submit"]',
        '//button[contains(@class, "VfPpkd-LgbsSe")]',
    ],
    'password_input': [
        '//input[@type="password" and @name="Passwd"]',
        '//input[@type="password"]',
        '//input[@name="Passwd"]',
    ],
    'password_next': [
        '//button[@type="submit" and contains(@class, "VfPpkd-LgbsSe")]',
        '//div[@id="passwordNext"]//button',
        '//button[contains(@class, "VfPpkd-LgbsSe") and (contains(., "Next") or contains(., "Siguiente") or contains(., "Weiter") or contains(., "Suivant"))]',
        '//button[@type="submit"]',
        '//button[contains(@class, "VfPpkd-LgbsSe")]',
    ],

    # Verification - Universal selectors
    'verify_title': [
        '//h1[contains(text(), "Verify") or contains(text(), "Verificar") or contains(text(), "Bestätigen") or contains(text(), "Vérifier")]',
        '//h1[contains(., "Verify") or contains(., "Verificar") or contains(., "Bestätigen") or contains(., "Vérifier")]',
    ],
    'try_another_way': [
        '//button[contains(text(), "Try another way") or contains(text(), "Probar otro método") or contains(text(), "Andere Methode versuchen") or contains(text(), "Essayer une autre méthode")]',
        '//button[contains(., "Try another way") or contains(., "Probar otro método") or contains(., "Andere Methode versuchen") or contains(., "Essayer une autre méthode")]',
    ],
    'captcha_img': [
        '//img[@id="captchaimg"]',
        '//img[contains(@src, "captcha")]',
    ],
    'captcha_input': [
        '//input[@name="ca"]',
        '//input[contains(@name, "captcha")]',
    ],

    # YouTube Studio + Upload flow - Universal selectors based on real HTML structure
    'file_input': [
        '//input[@type="file" and @name="Filedata"]',
        '//input[@type="file"]',
    ],
    'select_files_btn': [
        '//ytcp-button[@id="select-files-button"]//button',
        '//button[@aria-label="Select files" or @aria-label="Seleccionar archivos" or @aria-label="Dateien auswählen" or @aria-label="Sélectionner des fichiers"]',
        '//ytcp-button[@id="select-files-button"]',
    ],
    'title_input': [
        '//div[@id="textbox" and @contenteditable="true" and contains(@aria-label, "title")]',
        '//div[@id="textbox" and @contenteditable="true" and contains(@aria-label, "título")]',
        '//div[@id="textbox" and @contenteditable="true" and contains(@aria-label, "Titel")]',
        '//div[@id="textbox" and @contenteditable="true" and contains(@aria-label, "titre")]',
        '//div[@id="textbox" and @contenteditable="true"]',
    ],
    'description_input': [
        '//div[@id="textbox" and @contenteditable="true" and contains(@aria-label, "description")]',
        '//div[@id="textbox" and @contenteditable="true" and contains(@aria-label, "descripción")]',
        '//div[@id="textbox" and @contenteditable="true" and contains(@aria-label, "Beschreibung")]',
        '//div[@id="textbox" and @contenteditable="true" and contains(@aria-label, "description")]',
        '//div[@id="textbox" and @contenteditable="true"]',
    ],
    'shorts_checkbox': [
        '//tp-yt-paper-checkbox[@id="shorts-checkbox"]',
        '//input[@type="checkbox" and contains(@aria-label, "Shorts")]',
    ],
    'next_button': [
        '//ytcp-button[@id="next-button"]//button',
        '//button[@aria-label="Next" or @aria-label="Siguiente" or @aria-label="Weiter" or @aria-label="Suivant"]',
        '//ytcp-button[@id="next-button"]',
        '//button[contains(@class, "ytcpButtonShapeImplHost") and contains(., "Next")]',
    ],
    'publish_button': [
        '//ytcp-button[@id="done-button"]//button',
        '//button[@aria-label="Publish" or @aria-label="Publicar" or @aria-label="Veröffentlichen" or @aria-label="Publier"]',
        '//ytcp-button[@id="done-button"]',
        '//button[contains(@class, "ytcpButtonShapeImplHost") and contains(., "Publish")]',
    ],

    # Generic close buttons - Universal selectors
    'close_buttons': [
        '//button[@aria-label="Close" or @aria-label="Cerrar" or @aria-label="Schließen" or @aria-label="Fermer"]',
        '//button[contains(text(), "Skip") or contains(text(), "Omitir") or contains(text(), "Überspringen") or contains(text(), "Ignorer")]',
        '//button[contains(text(), "Maybe later") or contains(text(), "Tal vez más tarde") or contains(text(), "Vielleicht später") or contains(text(), "Peut-être plus tard")]',
        '//button[contains(text(), "Not now") or contains(text(), "Ahora no") or contains(text(), "Nicht jetzt") or contains(text(), "Pas maintenant")]',
        '//button[contains(text(), "Continue") or contains(text(), "Continuar") or contains(text(), "Weiter") or contains(text(), "Continuer")]',
    ],
    
    # Additional YouTube Studio selectors based on real HTML structure
    'ytcp_social_suggestion_input': [
        '//ytcp-social-suggestion-input[@id="input"]',
        '//ytcp-social-suggestion-input',
    ],
    'ytcp_button_shape': [
        '//button[contains(@class, "ytcpButtonShapeImplHost")]',
        '//ytcp-button-shape//button',
    ],
    'ytcp_form_input_container': [
        '//div[@class="style-scope ytcp-form-input-container"]',
        '//ytcp-form-input-container',
    ],
    'ytcp_uploads_dialog': [
        '//ytcp-uploads-dialog',
        '//div[contains(@class, "ytcp-uploads-dialog")]',
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

        await element.click(timeout=10000)
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
        logger.error(f"[YT TYPE] Error while typing: {e}")
        raise


async def login_to_google(page: Page, email: str, password: str, proxy: Optional[Dict] = None, user_agent: Optional[str] = None, task_id: int = None) -> bool:
    try:
        logger.info(f"[YT LOGIN] Starting login for {email}")
        # Start from YouTube Studio - Google will redirect to login if needed
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"[YT LOGIN] Navigation attempt {attempt + 1}/{max_retries} to YouTube Studio")
                await page.goto('https://studio.youtube.com', wait_until='domcontentloaded', timeout=45000)
                break  # Success, exit retry loop
            except Exception as nav_error:
                if attempt == max_retries - 1:  # Last attempt
                    logger.error(f"[YT LOGIN] Failed to navigate to YouTube Studio after {max_retries} attempts: {nav_error}")
                    raise nav_error
                else:
                    logger.warning(f"[YT LOGIN] Navigation attempt {attempt + 1} failed, retrying: {nav_error}")
                    await human_like_delay(2000, 4000)  # Wait before retry

        await human_like_delay(3000, 5000)
        
        # Check if we're already logged in by looking for YouTube Studio elements
        try:
            # Look for YouTube Studio specific elements
            studio_elements = [
                '//ytcp-button[@id="select-files-button"]',
                '//ytcp-uploads-dialog',
                '//div[contains(@class, "ytcp-uploads-dialog")]',
                '//button[contains(@aria-label, "Create")]',
                '//a[contains(@href, "studio.youtube.com")]'
            ]
            
            for selector in studio_elements:
                element = page.locator(selector)
                if await element.is_visible():
                    logger.info(f"[YT LOGIN] Already logged in - found YouTube Studio element: {selector}")
                    return True
        except Exception:
            pass
        
        logger.info("[YT LOGIN] Not logged in, proceeding with login process...")

        email_input = await find_element_by_selectors(page, YOUTUBE_SELECTORS['email_input'])
        if not email_input:
            raise RuntimeError('Email input not found')
        await human_like_type(page, email_input, email)
        await human_like_delay(1500, 2500)

        next_btn = await find_element_by_selectors(page, YOUTUBE_SELECTORS['email_next'])
        if not next_btn:
            raise RuntimeError('Next button (email) not found')
        await next_btn.click(timeout=10000)
        await human_like_delay(10000, 20000)  # REDUCED from 3-5s to 1-2s for faster processingслуф

        # Check for reCaptcha after email submission
        logger.info('[YT LOGIN] Checking for reCaptcha after email submission...')
        await _handle_recaptcha_check(page, proxy=proxy, user_agent=user_agent, task_id=task_id)
        await human_like_delay(3000, 6000)  # Wait longer for page transition

        # Check if we reached password field (captcha solved successfully)
        logger.info('[YT LOGIN] 🔍 Checking if password field appeared after captcha...')
        pwd_input = await find_element_by_selectors(page, YOUTUBE_SELECTORS['password_input'], timeout=15000)

        if not pwd_input:
            logger.warning('[YT LOGIN] ❌ Password field not found after captcha attempt - captcha may not be solved')
            logger.info('[YT LOGIN] 📄 Current page content check...')
            try:
                # Log current page URL and title for debugging
                current_url = page.url
                title = await page.title()
                logger.info(f'[YT LOGIN] Current URL: {current_url}')
                logger.info(f'[YT LOGIN] Page title: {title}')

                # Check if we're still on captcha page
                captcha_indicators = [
                    'iframe[src*="recaptcha"]',
                    '.recaptcha-checkbox',
                    'text="No soy un robot"'
                ]
                captcha_still_present = False
                for indicator in captcha_indicators:
                    try:
                        element = page.locator(indicator)
                        if await element.is_visible(timeout=3000):
                            logger.warning(f'[YT LOGIN] ⚠️ Captcha still present: {indicator}')
                            captcha_still_present = True
                            break
                    except:
                        continue

                if captcha_still_present:
                    logger.info('[YT LOGIN] 🔄 Captcha still present, retrying captcha solving...')
                    await _handle_recaptcha_check(page, proxy=proxy, user_agent=user_agent, task_id=task_id)
                    await human_like_delay(3000, 6000)

                    # Check again for password field
                    pwd_input = await find_element_by_selectors(page, YOUTUBE_SELECTORS['password_input'], timeout=15000)
                    if not pwd_input:
                        logger.error('[YT LOGIN] ❌ Password field still not found after retry - login failed')
                        return False
                else:
                    logger.info('[YT LOGIN] ✅ Captcha seems solved, but password field not visible yet - waiting longer...')
                    await human_like_delay(5000, 8000)
                    pwd_input = await find_element_by_selectors(page, YOUTUBE_SELECTORS['password_input'], timeout=15000)
                    if not pwd_input:
                        logger.error('[YT LOGIN] ❌ Password field not found even after longer wait - login failed')
                        return False
            except Exception as e:
                logger.error(f'[YT LOGIN] Error during page analysis: {e}')
                return False

        logger.info('[YT LOGIN] ✅ Password field found - captcha solved successfully!')
        await human_like_type(page, pwd_input, password)
        await human_like_delay(1500, 2500)

        pwd_next = await find_element_by_selectors(page, YOUTUBE_SELECTORS['password_next'])
        if not pwd_next:
            raise RuntimeError('Next button (password) not found')
        await pwd_next.click(timeout=10000)
        await human_like_delay(4000, 7000)

        # Check for reCaptcha after password submission
        await _handle_recaptcha_check(page, proxy=proxy, user_agent=user_agent, task_id=task_id)
        await human_like_delay(2000, 4000)

        # Check if login was successful (look for Studio elements or account menu)
        logger.info('[YT LOGIN] Checking if login was successful...')
        studio_elements = [
            '//ytcp-button[@id="select-files-button"]',
            '//ytcp-uploads-dialog',
            '//div[contains(@class, "ytcp-uploads-dialog")]',
            '//button[contains(@aria-label, "Create")]',
            '//a[contains(@href, "studio.youtube.com")]',
            '//div[contains(@class, "ytcp-uploads-file-picker")]'
        ]

        login_successful = False
        for selector in studio_elements:
            try:
                element = page.locator(selector)
                if await element.is_visible(timeout=5000):
                    logger.info(f'[YT LOGIN] Login successful - found Studio element: {selector}')
                    login_successful = True
                    break
            except Exception:
                continue

        if not login_successful:
            logger.warning('[YT LOGIN] Login may not be successful - Studio elements not found')
            # Could add additional retry logic here if needed

        # Basic verification handling (best-effort)
        await _handle_basic_verification(page, password, proxy=proxy, user_agent=user_agent)

        # Confirm logged in by checking YouTube Studio elements
        try:
            await page.goto('https://studio.youtube.com', wait_until='domcontentloaded', timeout=45000)
            await human_like_delay(4000, 6000)
            
            # Look for YouTube Studio specific elements to confirm login
            studio_confirm_elements = [
                '//ytcp-button[@id="select-files-button"]',
                '//ytcp-uploads-dialog',
                '//div[contains(@class, "ytcp-uploads-dialog")]',
                '//button[contains(@aria-label, "Create")]',
                '//a[contains(@href, "studio.youtube.com")]',
                '//div[contains(@class, "ytcp-uploads-file-picker")]'
            ]
            
            for selector in studio_confirm_elements:
                element = page.locator(selector)
                if await element.is_visible():
                    logger.info(f"[YT LOGIN] Success for {email} - found YouTube Studio element: {selector}")
                    return True
            
            logger.warning("[YT LOGIN] Could not confirm login via YouTube Studio elements; proceeding optimistically")
            return True
        except Exception as e:
            logger.warning(f"[YT LOGIN] Error confirming login: {e}; proceeding optimistically")
            return True
        return True
    except Exception as e:
        logger.error(f"[YT LOGIN] Error: {e}")
        return False


async def _handle_recaptcha_check(page: Page, proxy: Optional[Dict] = None, user_agent: Optional[str] = None, task_id: int = None) -> None:
    """Enhanced reCaptcha detection and solving using new captcha solver"""
    try:
        logger.info('[YT RECAPTCHA] Starting enhanced reCaptcha detection and solving...')
        
        # Create enhanced captcha solver with configuration
        config = CaptchaConfig(
            audio_timeout=30,
            api_timeout=120,
            max_retries=3,
            rucaptcha_api_key=os.getenv('RUCAPTCHA_API_KEY'),
            enable_audio_challenge=True,
            enable_api_fallback=True,
            submission_delay=3
        )
        
        solver = EnhancedCaptchaSolver(config, task_id=task_id)
        
        # Attempt to solve captcha with retry logic
        max_captcha_retries = 2
        for captcha_attempt in range(max_captcha_retries):
            logger.info(f'[YT RECAPTCHA] Captcha solving attempt {captcha_attempt + 1}/{max_captcha_retries}')

            result = await solver.solve_captcha(page, proxy, user_agent)

            if result.success:
                break  # Success, exit retry loop
            elif result.retry_recommended and captcha_attempt < max_captcha_retries - 1:
                logger.warning(f'[YT RECAPTCHA] Captcha attempt {captcha_attempt + 1} failed, retrying after delay...')
                await human_like_delay(5000, 10000)  # Wait before retry
                continue
            else:
                # Last attempt or no retry recommended
                break

        if result.success:
            logger.info(f'[YT RECAPTCHA] Captcha solved successfully using {result.method_used.value if result.method_used else "unknown method"} in {result.processing_time:.1f}s')
            
            # Wait for page to process the solution
            await human_like_delay(3000, 5000)
            
            # Check if we need to click a next button
            current_url = page.url
            if 'recaptcha' in current_url.lower() or 'challenge' in current_url.lower():
                logger.info('[YT RECAPTCHA] Still on challenge page, attempting to proceed...')
                await _click_google_next_universal(page)
            else:
                logger.info('[YT RECAPTCHA] Page has progressed automatically')
                
        else:
            logger.error(f'[YT RECAPTCHA] Captcha solving failed: {result.error_message}')
            if result.retry_recommended:
                logger.info('[YT RECAPTCHA] Retry recommended for this captcha')
            else:
                logger.warning('[YT RECAPTCHA] No retry recommended, may need manual intervention')
            
    except Exception as e:
        logger.error(f'[YT RECAPTCHA] Critical error in enhanced captcha handling: {e}')


async def _extract_recaptcha_site_key(page: Page) -> str:
    """Extract reCaptcha site key from the page using JavaScript and DOM methods"""
    try:
        # METHOD 1: JavaScript extraction from reCaptcha configuration (most reliable)
        try:
            site_key = await page.evaluate("""
                () => {
                    // Check reCaptcha configuration first
                    if (typeof ___grecaptcha_cfg !== 'undefined' && ___grecaptcha_cfg.clients) {
                        const clients = Object.entries(___grecaptcha_cfg.clients);
                        for (const [id, client] of clients) {
                            const objects = Object.entries(client).filter(([_, value]) => value && typeof value === 'object');
                            for (const [toplevelKey, toplevel] of objects) {
                                const found = Object.entries(toplevel).find(([_, value]) => (
                                    value && typeof value === 'object' && 'sitekey' in value
                                ));
                                if (found) {
                                    const [_, sublevel] = found;
                                    return sublevel.sitekey;
                                }
                            }
                        }
                    }
                    return null;
                }
            """)
            
            if site_key:
                logger.info(f'[YT RECAPTCHA] Site key found via JavaScript config: {site_key}')
                return site_key
                
        except Exception as js_e:
            logger.warning(f'[YT RECAPTCHA] JavaScript config extraction failed: {js_e}')
        
        # METHOD 2: Try to find site key in script tags
        site_key_script = await page.evaluate('''
            () => {
                const scripts = document.querySelectorAll('script');
                for (let script of scripts) {
                    const content = script.textContent || script.innerHTML;
                    // Look for sitekey in various formats
                    const patterns = [
                        /sitekey["\\s]*:["\\s]*([^"\\s,}]+)/i,
                        /data-sitekey["\\s]*=["\\s]*["']([^"']+)["']/i,
                        /sitekey["\\s]*=["\\s]*["']([^"']+)["']/i,
                        /"sitekey":\\s*"([^"]+)"/i,
                        /'sitekey':\\s*'([^']+)'/i
                    ];
                    
                    for (let pattern of patterns) {
                        const match = content.match(pattern);
                        if (match && match[1]) {
                            return match[1];
                        }
                    }
                }
                return null;
            }
        ''')
        
        if site_key_script:
            logger.info(f'[YT RECAPTCHA] Found site key in scripts: {site_key_script}')
            return site_key_script
            
        # METHOD 3: Try to find in data attributes (both formats)
        site_key_data = await page.evaluate('''
            () => {
                // Try data-site-key first (from real HTML)
                let elements = document.querySelectorAll('[data-site-key]');
                if (elements.length > 0) {
                    return elements[0].getAttribute('data-site-key');
                }
                
                // Try data-sitekey as fallback
                elements = document.querySelectorAll('[data-sitekey]');
                if (elements.length > 0) {
                    return elements[0].getAttribute('data-sitekey');
                }
                
                return null;
            }
        ''')
        
        if site_key_data:
            logger.info(f'[YT RECAPTCHA] Found site key in data attribute: {site_key_data}')
            return site_key_data
            
        # METHOD 4: Look for reCaptcha div with site key
        site_key_div = await page.evaluate('''
            () => {
                const recaptchaDivs = document.querySelectorAll('div[class*="recaptcha"], div[id*="recaptcha"]');
                for (let div of recaptchaDivs) {
                    const sitekey = div.getAttribute('data-sitekey');
                    if (sitekey) return sitekey;
                }
                return null;
            }
        ''')
        
        if site_key_div:
            logger.info(f'[YT RECAPTCHA] Found site key in div: {site_key_div}')
            return site_key_div
            
        # METHOD 5: Look in iframe src
        site_key_iframe = await page.evaluate('''
            () => {
                const iframes = document.querySelectorAll('iframe[src*="recaptcha"]');
                for (let iframe of iframes) {
                    const src = iframe.src;
                    const match = src.match(/[?&]k=([^&]+)/);
                    if (match) return match[1];
                }
                return null;
            }
        ''')
        
        if site_key_iframe:
            logger.info(f'[YT RECAPTCHA] Found site key in iframe: {site_key_iframe}')
            return site_key_iframe
        
        logger.warning('[YT RECAPTCHA] Could not find site key using any method')
        return ''
        
    except Exception as e:
        logger.warning(f'[YT RECAPTCHA] Error extracting site key: {e}')
        return ''


async def _solve_recaptcha_with_rucaptcha(page_url: str, site_key: str, proxy: Optional[Dict] = None, user_agent: Optional[str] = None) -> str:
    """Solve reCaptcha using RuCaptcha API (new JSON format)"""
    try:
        import os
        import aiohttp
        import asyncio
        import json
        
        logger.info(f'[YT RECAPTCHA] Starting RuCaptcha solving for URL: {page_url}')
        logger.info(f'[YT RECAPTCHA] Using site key: {site_key}')
        
        api_key = os.environ.get('RUCAPTCHA_API_KEY')
        if not api_key:
            logger.error('[YT RECAPTCHA] RUCAPTCHA_API_KEY not found in environment')
            return ''
        
        logger.info(f'[YT RECAPTCHA] Using API key: {api_key[:10]}...')
        
        # Create task using new JSON API
        create_task_url = 'https://api.rucaptcha.com/createTask'
        # Decide on task type depending on proxy presence
        if proxy and proxy.get('host') and proxy.get('port'):
            # Normalize proxy type for RuCaptcha: HTTP or SOCKS5
            proxy_type = (proxy.get('type') or 'http').upper()
            if proxy_type not in ('HTTP', 'HTTPS', 'SOCKS5'):
                proxy_type = 'HTTP'
            task_obj = {
                "type": "RecaptchaV2Task",
                "websiteURL": page_url,
                "websiteKey": site_key,
                "proxyType": proxy_type,
                "proxyAddress": proxy.get('host'),
                "proxyPort": int(proxy.get('port')),
            }
            if proxy.get('user'):
                task_obj["proxyLogin"] = proxy.get('user')
            if proxy.get('pass'):
                task_obj["proxyPassword"] = proxy.get('pass')
            if user_agent:
                task_obj["userAgent"] = user_agent
        else:
            task_obj = {
                "type": "RecaptchaV2TaskProxyless",
                "websiteURL": page_url,
                "websiteKey": site_key,
                "isInvisible": False
            }
            if user_agent:
                task_obj["userAgent"] = user_agent

        task_data = {
            "clientKey": api_key,
            "task": task_obj,
            "softId": "3898"  # Soft ID for identification
        }
        
        logger.info(f'[YT RECAPTCHA] Sending task creation request to: {create_task_url}')
        logger.info(f'[YT RECAPTCHA] Task data: {json.dumps(task_data, indent=2)}')
        
        async with aiohttp.ClientSession() as session:
            # Submit task
            async with session.post(create_task_url, json=task_data) as response:
                response_text = await response.text()
                logger.info(f'[YT RECAPTCHA] Response status: {response.status}')
                logger.info(f'[YT RECAPTCHA] Response text: {response_text}')
                
                result = await response.json()
                
                if result.get('errorId') != 0:
                    logger.error(f'[YT RECAPTCHA] Task creation failed: {result}')
                    return ''
                
                task_id = result.get('taskId')
                logger.info(f'[YT RECAPTCHA] Task created, ID: {task_id}')
                
                # Wait for solution
                get_result_url = 'https://api.rucaptcha.com/getTaskResult'
                result_data = {
                    "clientKey": api_key,
                    "taskId": task_id
                }
                
                for attempt in range(30):  # Wait up to 5 minutes
                    logger.info(f'[YT RECAPTCHA] Polling for solution (attempt {attempt + 1}/30)')
                    await asyncio.sleep(10)
                    
                    async with session.post(get_result_url, json=result_data) as result_response:
                        result_json = await result_response.json()
                        if result_json.get('status') == 'ready':
                            solution = result_json.get('solution', {}).get('gRecaptchaResponse')
                            if solution:
                                logger.info(f'[YT RECAPTCHA] Solution received: {solution[:20]}...')
                                return solution
                            else:
                                logger.error('[YT RECAPTCHA] No solution in response')
                                return ''
                        elif result_json.get('errorId') != 0:
                            logger.error(f'[YT RECAPTCHA] Error getting result: {result_json}')
                            return ''
                        else:
                            logger.info(f'[YT RECAPTCHA] Not ready yet, will retry...')
                            continue
                
                logger.error('[YT RECAPTCHA] Timeout waiting for solution')
                return ''
                
    except Exception as e:
        logger.error(f'[YT RECAPTCHA] Error solving reCaptcha: {e}')
        return ''


async def _submit_recaptcha_solution(page: Page, solution: str) -> None:
    """ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ функции отправки reCAPTCHA"""
    try:
        logger.info(f'[YT RECAPTCHA] FINAL FIX: Submitting solution: {solution[:20]}...')
        
        # ШАГ 1: Вставить токен (ваш код уже работает)
        insert_result = await page.evaluate(f'''
            () => {{
                const textarea = document.getElementById('g-recaptcha-response') ||
                               document.querySelector('textarea[name="g-recaptcha-response"]');
                if (textarea) {{
                    textarea.value = '{solution}';
                    const event = new Event('change', {{ bubbles: true }});
                    textarea.dispatchEvent(event);
                    return 'token_inserted';
                }}
                return 'textarea_not_found';
            }}
        ''')
        logger.info(f'[YT RECAPTCHA] Token insert: {insert_result}')
        
        # ШАГ 2: Обязательная задержка 
        await asyncio.sleep(3)
        
        # ШАГ 3: Поиск callback (ваш код уже работает)
        callback_result = await page.evaluate(f'''
            () => {{
                const solution = '{solution}';
                if (typeof ___grecaptcha_cfg !== 'undefined' && ___grecaptcha_cfg.clients) {{
                    const clients = ___grecaptcha_cfg.clients;
                    const paths = ['callback', 'L.L.callback', 'I.I.callback', 'A.A.callback', 'D.D.callback'];
                    
                    for (let clientId in clients) {{
                        for (let path of paths) {{
                            let current = clients[clientId];
                            const parts = path.split('.');
                            for (let part of parts) {{
                                current = current[part];
                                if (!current) break;
                            }}
                            if (typeof current === 'function') {{
                                current(solution);
                                return `callback_executed_${{path}}`;
                            }}
                                }}
                            }}
                        }}
                return 'no_callback_found';
            }}
        ''')
        logger.info(f'[YT RECAPTCHA] Callback result: {callback_result}')
        
        # ШАГ 4: КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ - ВСЕГДА пытаемся кликнуть кнопку
        await asyncio.sleep(1)
        button_success = await _click_google_recaptcha_button_fixed(page)
        
        if button_success:
            logger.info('[YT RECAPTCHA] FIXED: Button clicked successfully!')
        else:
            logger.warning('[YT RECAPTCHA] FIXED: Button click failed, using fallback...')
            # Fallback: form.submit()
            await page.evaluate(f'''
                () => {{
                    const textarea = document.getElementById('g-recaptcha-response');
                    if (textarea && textarea.value === '{solution}') {{
                        const form = textarea.closest('form');
                        if (form) {{
                            form.submit();
                        }}
                }}
            }}
        ''')
        
        # ШАГ 5: Ждем результата
        await asyncio.sleep(5)
        
        # ШАГ 6: Проверяем что нет 400 ошибки
        current_url = page.url
        page_content = await page.content()
        
        if '400' in page_content and 'error' in page_content.lower():
            logger.error('[YT RECAPTCHA] DETECTED 400 error on page')
            return False
        
        logger.info(f'[YT RECAPTCHA] FINAL FIX completed. URL: {current_url}')
        
    except Exception as e:
        logger.error(f'[YT RECAPTCHA] Error in FINAL FIX: {e}')


async def debug_400_error(page: Page) -> None:
    """Debug function to analyze causes of 400 errors"""
    try:
        debug_info = await page.evaluate('''
            () => {
                const info = {
                    forms: [],
                    recaptcha_elements: [],
                    hidden_inputs: [],
                    current_url: window.location.href,
                    page_title: document.title
                };
                
                // Analyze forms and hidden fields
                document.querySelectorAll('form').forEach((form, index) => {
                    const hiddenInputs = [];
                    form.querySelectorAll('input[type="hidden"]').forEach(input => {
                        hiddenInputs.push({
                            name: input.name,
                            value: input.value ? input.value.substring(0, 50) + '...' : ''
                        });
                    });
                    
                    info.forms.push({
                        index: index,
                        action: form.action,
                        method: form.method,
                        elements_count: form.elements.length,
                        hidden_inputs: hiddenInputs
                    });
                });
                
                // Analyze reCAPTCHA elements
                document.querySelectorAll('[data-site-key], .g-recaptcha, #g-recaptcha-response').forEach((el, index) => {
                    info.recaptcha_elements.push({
                        index: index,
                        tag: el.tagName,
                        id: el.id,
                        class: el.className,
                        site_key: el.getAttribute('data-site-key') || 'none'
                    });
                });
                
                return info;
            }
        ''')
        
        logger.info(f'[YT DEBUG] Page analysis: {debug_info}')
        
    except Exception as e:
        logger.warning(f'[YT DEBUG] Error analyzing page: {e}')


async def _click_google_recaptcha_button_fixed(page: Page) -> bool:
    """ИСПРАВЛЕННАЯ функция поиска кнопки на странице reCAPTCHA Google"""
    try:
        logger.info('[YT RECAPTCHA] Starting FIXED button search for Google reCAPTCHA page...')
        
        # Специальные селекторы для Google reCAPTCHA challenge page
        recaptcha_page_selectors = [
            # Google reCAPTCHA specific selectors
            'button[type="submit"]',  # Стабильный селектор
            '.VfPpkd-LgbsSe',
            'button[type="submit"]',
            'input[type="submit"]',
            # Universal submit selectors
            'button:has-text("Siguiente")',
            'button:has-text("Next")',
            'button:has-text("Continue")',
            'button:has-text("Submit")',
            'button:has-text("Далее")',
            # CSS contains selectors
            'button[class*="VfPpkd"]',
            'button[class*="LgbsSe"]'
        ]
        
        for selector in recaptcha_page_selectors:
            try:
                logger.info(f'[YT RECAPTCHA] Trying selector: {selector}')
                
                if ':has-text(' in selector:
                    # Playwright text selectors
                    elements = await page.locator(selector).all()
                else:
                    # Regular CSS selectors
                    elements = await page.query_selector_all(selector)
                    
                logger.info(f'[YT RECAPTCHA] Found {len(elements)} elements with selector: {selector}')
                
                for element in elements:
                    try:
                        is_visible = await element.is_visible()
                        if not is_visible:
                            continue
                            
                        # Get text content
                        if ':has-text(' not in selector:
                            text = await element.inner_text() if element else ""
                        else:
                            text = await element.text_content() if element else ""
                            
                        logger.info(f'[YT RECAPTCHA] Button text: "{text}" (visible: {is_visible})')
                        
                        # Click any visible submit button on reCAPTCHA page
                        if (selector in ['button[type="submit"]', 'input[type="submit"]'] or
                            any(word in text.lower() for word in ['siguiente', 'next', 'continue', 'submit', 'далее'])):
                            
                            logger.info(f'[YT RECAPTCHA] CLICKING button: {selector} with text: {text}')
                            await element.click(timeout=10000)
                            await asyncio.sleep(2)
                            return True
                            
                    except Exception as e:
                        logger.warning(f'[YT RECAPTCHA] Error checking element: {e}')
                        continue
                        
            except Exception as e:
                logger.warning(f'[YT RECAPTCHA] Error with selector {selector}: {e}')
                continue
        
        # Last resort: try to click ANY visible button
        try:
            logger.info('[YT RECAPTCHA] Last resort: clicking any visible button...')
            all_buttons = await page.query_selector_all('button')
            for button in all_buttons:
                if await button.is_visible():
                    text = await button.inner_text()
                    logger.info(f'[YT RECAPTCHA] Found visible button: "{text}"')
                    await button.click(timeout=10000)
                    await asyncio.sleep(2)
                    return True
        except Exception as e:
            logger.warning(f'[YT RECAPTCHA] Last resort failed: {e}')
        
        logger.warning('[YT RECAPTCHA] FIXED button search found NO clickable buttons')
        return False
        
    except Exception as e:
        logger.error(f'[YT RECAPTCHA] Error in FIXED button search: {e}')
        return False


async def _handle_basic_verification(page: Page, password: str, proxy: Optional[Dict] = None, user_agent: Optional[str] = None) -> None:
    try:
        await human_like_delay(600, 1200)
        verify_el = page.locator(YOUTUBE_SELECTORS['verify_title'][0])
        if await verify_el.is_visible():
            logger.info('[YT VERIFY] Verification page detected')
            try_another = page.locator(YOUTUBE_SELECTORS['try_another_way'][0])
            for _ in range(2):
                if await try_another.is_visible():
                    await try_another.click(timeout=10000)
                    await human_like_delay(1000, 2000)
        # CAPTCHA placeholder wait - now with RuCaptcha support
        captcha_img = page.locator(YOUTUBE_SELECTORS['captcha_img'][0])
        if await captcha_img.is_visible():
            logger.warning('[YT VERIFY] CAPTCHA detected; attempting to solve with RuCaptcha')
            await _handle_recaptcha_check(page, proxy=proxy, user_agent=user_agent)
        # Also check for reCaptcha in verification page
        recaptcha_iframe = page.locator('iframe[src*="recaptcha"]')
        if await recaptcha_iframe.is_visible():
            logger.warning('[YT VERIFY] reCaptcha detected in verification page')
            await _handle_recaptcha_check(page, proxy=proxy, user_agent=user_agent)
        # Recovery password re-entry
        rec_pwd = page.locator('input[type="password"]')
        if await rec_pwd.is_visible():
            await human_like_type(page, rec_pwd, password)
            next_btn = page.locator('//button[contains(text(), "Next")]')
            if await next_btn.is_visible():
                await next_btn.click(timeout=10000)
                await human_like_delay(1500, 3000)
    except Exception as e:
        logger.warning(f"[YT VERIFY] Warning while handling verification: {e}")


async def navigate_to_studio(page: Page) -> None:
    logger.info('[YT NAV] Navigating to YouTube Studio')
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f'[YT NAV] Navigation attempt {attempt + 1}/{max_retries} to YouTube Studio')
            await page.goto('https://studio.youtube.com', wait_until='domcontentloaded', timeout=45000)
            break  # Success, exit retry loop
        except Exception as nav_error:
            if attempt == max_retries - 1:  # Last attempt
                logger.error(f'[YT NAV] Failed to navigate to YouTube Studio after {max_retries} attempts: {nav_error}')
                raise nav_error
            else:
                logger.warning(f'[YT NAV] Navigation attempt {attempt + 1} failed, retrying: {nav_error}')
                await human_like_delay(2000, 4000)  # Wait before retry

    await human_like_delay(1200, 2600)
    # Attempt to close any popups
    await _close_popups(page)


async def _click_google_next_universal(page: Page) -> None:
    """Click Google primary action Next button using robust, language-agnostic XPath fallbacks."""
    try:
        await human_like_delay(500, 1200)

        # Extended list of button texts in multiple languages
        button_texts = [
            'Next', 'Siguiente', 'Weiter', 'Suivant', 'Далее', 'Continuar', 
            'Continue', 'Continuer', 'Продолжить', 'Submit', 'Enviar', 'Enviar',
            'Confirmar', 'Confirm', 'Bestätigen', 'Confirmer', 'Подтвердить',
            'Proceed', 'Proceder', 'Fortfahren', 'Procéder', 'Продолжить',
            'Done', 'Hecho', 'Fertig', 'Terminé', 'Готово', 'Finalizar'
        ]

        # 1) Google-specific selectors first (most reliable for Google forms)
        next_locators = [
            # Google-specific selectors (highest priority)
            '//button[@type="submit"]',  # Стабильный селектор
            '//button[contains(@class, "VfPpkd-LgbsSe")]',  # Google Material Design
            '//button[@data-identifier]',  # Google forms identifier
            '//button[@data-primary-action-label]',  # Google primary action
            # Button by type and visible text
            f'//button[@type="submit" and .//span[{" or ".join([f"contains(normalize-space(.), \"{text}\")" for text in button_texts])}]]',
            # Button by type only
            '//button[@type="submit"]',
            '//input[@type="submit"]',
            # Button by stable class patterns
            '//button[contains(@class, "goog-button")]',
            '//button[contains(@class, "submit")]',
            # Button by role attribute
            '//button[@role="button"]',
            # Button by data attributes
            '//button[@data-action]',
            # Any visible Next-like button as fallback
            f'//button[.//span[{" or ".join([f"contains(., \"{text}\")" for text in button_texts])}]]',
            # Generic button selectors
            '//button[contains(@class, "button")]',
            '//button[contains(@class, "btn")]',
        ]

        for sel in next_locators:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    logger.info(f"[YT RECAPTCHA] Clicking primary action button via selector: {sel}")
                    await btn.click(timeout=10000)
                    await human_like_delay(2500, 5000)
                    return
            except Exception as e:
                logger.warning(f"[YT RECAPTCHA] Failed clicking selector {sel}: {e}")
                continue

        # 2) Fallback: Try clicking any visible button by Google-specific attributes
        try:
            fallback_selectors = [
                'button[type="submit"]',  # Стабильный селектор
                'button[data-identifier]',  # Google forms
                'button[data-primary-action-label]',  # Google primary action
                'button[type="submit"]',
                'input[type="submit"]',
                'button[role="button"]',
                'button[data-action]'
            ]
            
            for selector in fallback_selectors:
                try:
                    fallback_btn = page.locator(selector).first
                    if await fallback_btn.is_visible():
                        logger.info(f"[YT RECAPTCHA] Clicked fallback button: {selector}")
                        await fallback_btn.click(timeout=10000)
                        await human_like_delay(2500, 5000)
                        return
                except Exception:
                    continue
        except Exception:
            pass

        # 3) Last resort: Try to find any submit button by Google patterns
        try:
            submit_selectors = [
                'button[type="submit"]',  # Стабильный селектор  # Google-specific
                'button[data-identifier]',  # Google forms
                'button[type="submit"]',
                'input[type="submit"]',
                'button[role="button"]',
                'button[class*="submit"]',
                'button[class*="button"]',
                'button[class*="btn"]',
                '.VfPpkd-LgbsSe',  # Google Material Design
                'button[data-primary-action-label]'
            ]
            
            for selector in submit_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible():
                        await btn.click(timeout=10000)
                        logger.info(f"[YT RECAPTCHA] Clicked last resort button: {selector}")
                        await human_like_delay(2500, 5000)
                        return
                except Exception:
                    continue
        except Exception:
            pass

        logger.warning("[YT RECAPTCHA] No suitable button found to click")
    except Exception as e:
        logger.warning(f"[YT RECAPTCHA] Error in _click_google_next_universal: {e}")


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
                    await btn.click(timeout=10000)
                    await human_like_delay(400, 900)
                    logger.info(f"[YT NAV] Closed popup: {selector}")
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"[YT NAV] Error closing popups: {e}")


async def upload_and_publish_short(page: Page, video_path: str, title: Optional[str], description: Optional[str]) -> bool:
    try:
        logger.info(f"[YT UPLOAD] Uploading file: {video_path}")
        await page.goto('https://studio.youtube.com/channel/UC/videos/upload', wait_until='domcontentloaded', timeout=45000)
        await human_like_delay(1200, 2500)

        file_input = page.locator(YOUTUBE_SELECTORS['file_input'][0])
        if not await file_input.is_visible():
            select_btn = page.locator(YOUTUBE_SELECTORS['select_files_btn'][0])
            try:
                await file_input.set_input_files(video_path)
            except Exception:
                pass
            if await select_btn.is_visible():
                await select_btn.click(timeout=10000)
        else:
            await file_input.set_input_files(video_path)

        await human_like_delay(2500, 5000)
        await page.wait_for_selector('div[contenteditable="true"]', timeout=60000)

        if title:
            title_input = page.locator(YOUTUBE_SELECTORS['title_input'][0]).first
            if await title_input.is_visible():
                await human_like_type(page, title_input, title)
                logger.info(f"[YT UPLOAD] Title set")

        if description:
            desc_input = page.locator(YOUTUBE_SELECTORS['description_input'][0]).first
            if await desc_input.is_visible():
                await human_like_type(page, desc_input, description)
                logger.info("[YT UPLOAD] Description set")

        shorts_checkbox = page.locator(YOUTUBE_SELECTORS['shorts_checkbox'][0])
        try:
            if await shorts_checkbox.is_visible():
                await shorts_checkbox.check()
                logger.info('[YT UPLOAD] Marked as Shorts')
                await human_like_delay(400, 900)
        except Exception:
            pass

        # Walk through Next steps
        for _ in range(4):
            await human_like_delay(700, 1500)
            next_btn = page.locator(YOUTUBE_SELECTORS['next_button'][0])
            if await next_btn.is_visible():
                await next_btn.click(timeout=10000)
                await human_like_delay(1200, 2200)
            else:
                break

        # Final publish
        published = False
        for selector in YOUTUBE_SELECTORS['publish_button']:
            btn = page.locator(selector)
            if await btn.is_visible():
                await btn.click(timeout=10000)
                logger.info('[YT UPLOAD] Publish clicked')
                published = True
                await human_like_delay(1500, 2800)
                break
        if not published:
            logger.warning('[YT UPLOAD] Publish button not found')

        return published
    except Exception as e:
        logger.error(f"[YT UPLOAD] Error: {e}")
        return False


async def perform_youtube_operations_async(page: Page, account_details: Dict, videos: List[Dict], video_files: List[str], task_id: int = None) -> int:
    """
    Performs YouTube operations: login, navigate to Studio, upload each video.
    Returns number of successfully uploaded videos.
    """
    success_count = 0
    email = account_details.get('email') or account_details.get('username') or ''
    password = account_details.get('password') or ''

    # Collect proxy and user agent for captcha solver consistency
    proxy = None
    try:
        proxy = account_details.get('proxy') if isinstance(account_details, dict) else None
    except Exception:
        proxy = None
    try:
        user_agent = await page.evaluate('navigator.userAgent')
    except Exception:
        user_agent = None
    logger.info(f"[YT RECAPTCHA] Passing to solver -> proxy: {'yes' if proxy else 'no'}, userAgent: {'yes' if user_agent else 'no'}")

    # Login
    if not await login_to_google(page, email, password, proxy=proxy, user_agent=user_agent, task_id=task_id):
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


