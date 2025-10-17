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


# Robust selector sets with fallbacks - Universal XPath selectors
YOUTUBE_SELECTORS: Dict[str, List[str]] = {
    # Google login - Universal selectors
    'email_input': [
        '//input[@type="email" and (@id="identifierId" or @name="identifier")]',
        '//input[@type="email"]',
        '//input[@name="identifier"]',
    ],
    'email_next': [
        '//button[@jsname="LgbsSe" and contains(@class, "VfPpkd-LgbsSe")]',
        '//div[@id="identifierNext"]//button',
        '//button[contains(@class, "VfPpkd-LgbsSe") and (contains(., "Next") or contains(., "Siguiente") or contains(., "Weiter") or contains(., "Suivant"))]',
    ],
    'password_input': [
        '//input[@type="password" and @name="Passwd"]',
        '//input[@type="password"]',
        '//input[@name="Passwd"]',
    ],
    'password_next': [
        '//button[@jsname="LgbsSe" and contains(@class, "VfPpkd-LgbsSe")]',
        '//div[@id="passwordNext"]//button',
        '//button[contains(@class, "VfPpkd-LgbsSe") and (contains(., "Next") or contains(., "Siguiente") or contains(., "Weiter") or contains(., "Suivant"))]',
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


async def login_to_google(page: Page, email: str, password: str, proxy: Optional[Dict] = None, user_agent: Optional[str] = None) -> bool:
    try:
        log_info(f"[YT LOGIN] Starting login for {email}")
        # Start from YouTube Studio - Google will redirect to login if needed
        await page.goto('https://studio.youtube.com', wait_until='networkidle')
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
                    log_info(f"[YT LOGIN] Already logged in - found YouTube Studio element: {selector}")
                    return True
        except Exception:
            pass
        
        log_info("[YT LOGIN] Not logged in, proceeding with login process...")

        email_input = await find_element_by_selectors(page, YOUTUBE_SELECTORS['email_input'])
        if not email_input:
            raise RuntimeError('Email input not found')
        await human_like_type(page, email_input, email)
        await human_like_delay(1500, 2500)

        next_btn = await find_element_by_selectors(page, YOUTUBE_SELECTORS['email_next'])
        if not next_btn:
            raise RuntimeError('Next button (email) not found')
        await next_btn.click()
        await human_like_delay(3000, 5000)

        # Check for reCaptcha after email submission
        log_info('[YT LOGIN] Checking for reCaptcha after email submission...')
        await _handle_recaptcha_check(page, proxy=proxy, user_agent=user_agent)
        await human_like_delay(2000, 3500)
        log_info('[YT LOGIN] reCaptcha check completed, looking for password field...')

        pwd_input = await find_element_by_selectors(page, YOUTUBE_SELECTORS['password_input'], timeout=40000)
        if not pwd_input:
            raise RuntimeError('Password input not found')
        await human_like_type(page, pwd_input, password)
        await human_like_delay(1500, 2500)

        pwd_next = await find_element_by_selectors(page, YOUTUBE_SELECTORS['password_next'])
        if not pwd_next:
            raise RuntimeError('Next button (password) not found')
        await pwd_next.click()
        await human_like_delay(4000, 7000)

        # Check for reCaptcha after password submission
        await _handle_recaptcha_check(page, proxy=proxy, user_agent=user_agent)
        await human_like_delay(3000, 5000)

        # Basic verification handling (best-effort)
        await _handle_basic_verification(page, password, proxy=proxy, user_agent=user_agent)

        # Confirm logged in by checking YouTube Studio elements
        try:
            await page.goto('https://studio.youtube.com', wait_until='networkidle')
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
                    log_info(f"[YT LOGIN] Success for {email} - found YouTube Studio element: {selector}")
                    return True
            
            log_warning("[YT LOGIN] Could not confirm login via YouTube Studio elements; proceeding optimistically")
            return True
        except Exception as e:
            log_warning(f"[YT LOGIN] Error confirming login: {e}; proceeding optimistically")
                return True
        return True
    except Exception as e:
        log_error(f"[YT LOGIN] Error: {e}")
        return False


async def _handle_recaptcha_check(page: Page, proxy: Optional[Dict] = None, user_agent: Optional[str] = None) -> None:
    """Handle reCaptcha detection and solving using RuCaptcha API"""
    try:
        log_info('[YT RECAPTCHA] Starting reCaptcha detection...')
        
        # Wait a bit for page to load
        await human_like_delay(12000, 15000)
        
        # Check for various reCaptcha indicators - Based on real HTML structure
        recaptcha_indicators = [
            # Main reCaptcha container with data-site-key
            '//div[@data-site-key]',
            '//div[@data-sitekey]',
            # reCaptcha iframe
            '//iframe[contains(@src, "recaptcha")]',
            '//iframe[contains(@src, "google.com/recaptcha")]',
            '//iframe[contains(@src, "gstatic.com/recaptcha")]',
            '//iframe[@title="reCAPTCHA"]',
            # reCaptcha response textarea
            '//textarea[@name="g-recaptcha-response"]',
            # reCaptcha container with specific classes from real HTML
            '//div[@class="njnYzb"]',
            '//div[@class="YqLCIe"]',
            '//div[@class="xRXYb"]',
            # Generic reCaptcha indicators
            '//div[contains(@class, "g-recaptcha")]',
            '//div[contains(@data-callback, "recaptcha")]',
            '//div[contains(@class, "recaptcha")]',
            '//div[contains(@id, "recaptcha")]',
            # Text indicators
            '//div[contains(text(), "Demuestra que no eres un robot")]',
            '//div[contains(text(), "robot")]',
            '//div[contains(text(), "captcha")]'
        ]
        
        recaptcha_found = False
        for indicator in recaptcha_indicators:
            try:
                log_info(f"[YT RECAPTCHA] Checking indicator: {indicator}")
                element = page.locator(indicator).first
                if await element.is_visible():
                    log_warning(f'[YT RECAPTCHA] reCaptcha detected with selector: {indicator}')
                    recaptcha_found = True
                    break
            except Exception as e:
                log_warning(f'[YT RECAPTCHA] Error checking selector {indicator}: {e}')
                continue
        
        if not recaptcha_found:
            log_info('[YT RECAPTCHA] No reCaptcha detected, continuing...')
            return
        
        # Get site key from the page
        site_key = await _extract_recaptcha_site_key(page)
        if not site_key:
            log_error('[YT RECAPTCHA] Could not extract site key')
            return
        
        log_info(f'[YT RECAPTCHA] Site key extracted: {site_key}')
        
        # Solve reCaptcha using RuCaptcha
        # If proxy is present, use RecaptchaV2Task (proxy-based) to match browser IP
        if proxy:
            log_info('[YT RECAPTCHA] Proxy detected; using proxy-based solving via RuCaptcha')
            log_info(f"[YT RECAPTCHA] Proxy details for solver: {proxy.get('type','http')} {proxy.get('host')}:{proxy.get('port')}")
        else:
            log_info('[YT RECAPTCHA] No proxy provided; using proxyless solving via RuCaptcha')
        solution = await _solve_recaptcha_with_rucaptcha(page.url, site_key, proxy=proxy, user_agent=user_agent)
        if solution:
            log_info('[YT RECAPTCHA] Successfully solved reCaptcha')
            await _submit_recaptcha_solution(page, solution)
            
            # Wait for page to process the solution
            await human_like_delay(5000, 9000)
            # Try to proceed by clicking primary action if present
            await _click_google_next_universal(page)
        else:
            log_error('[YT RECAPTCHA] Failed to solve reCaptcha')
            
    except Exception as e:
        log_warning(f'[YT RECAPTCHA] Error handling reCaptcha: {e}')


async def _extract_recaptcha_site_key(page: Page) -> str:
    """Extract reCaptcha site key from the page"""
    try:
        # Method 1: Try to find site key in script tags
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
            log_info(f'[YT RECAPTCHA] Found site key in scripts: {site_key_script}')
            return site_key_script
            
        # Method 2: Try to find in data attributes (both formats)
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
            log_info(f'[YT RECAPTCHA] Found site key in data attribute: {site_key_data}')
            return site_key_data
            
        # Method 3: Look for reCaptcha div with site key
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
            log_info(f'[YT RECAPTCHA] Found site key in div: {site_key_div}')
            return site_key_div
            
        # Method 4: Look in iframe src
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
            log_info(f'[YT RECAPTCHA] Found site key in iframe: {site_key_iframe}')
            return site_key_iframe
        
        log_warning('[YT RECAPTCHA] Could not find site key using any method')
        return ''
        
    except Exception as e:
        log_warning(f'[YT RECAPTCHA] Error extracting site key: {e}')
        return ''


async def _solve_recaptcha_with_rucaptcha(page_url: str, site_key: str, proxy: Optional[Dict] = None, user_agent: Optional[str] = None) -> str:
    """Solve reCaptcha using RuCaptcha API (new JSON format)"""
    try:
        import os
        import aiohttp
        import asyncio
        import json
        
        log_info(f'[YT RECAPTCHA] Starting RuCaptcha solving for URL: {page_url}')
        log_info(f'[YT RECAPTCHA] Using site key: {site_key}')
        
        api_key = os.environ.get('RUCAPTCHA_API_KEY')
        if not api_key:
            log_error('[YT RECAPTCHA] RUCAPTCHA_API_KEY not found in environment')
            return ''
        
        log_info(f'[YT RECAPTCHA] Using API key: {api_key[:10]}...')
        
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
        
        log_info(f'[YT RECAPTCHA] Sending task creation request to: {create_task_url}')
        log_info(f'[YT RECAPTCHA] Task data: {json.dumps(task_data, indent=2)}')
        
        async with aiohttp.ClientSession() as session:
            # Submit task
            async with session.post(create_task_url, json=task_data) as response:
                response_text = await response.text()
                log_info(f'[YT RECAPTCHA] Response status: {response.status}')
                log_info(f'[YT RECAPTCHA] Response text: {response_text}')
                
                result = await response.json()
                
                if result.get('errorId') != 0:
                    log_error(f'[YT RECAPTCHA] Task creation failed: {result}')
                    return ''
                
                task_id = result.get('taskId')
                log_info(f'[YT RECAPTCHA] Task created, ID: {task_id}')
                
                # Wait for solution
                get_result_url = 'https://api.rucaptcha.com/getTaskResult'
                result_data = {
                    "clientKey": api_key,
                    "taskId": task_id
                }
                
                for attempt in range(30):  # Wait up to 5 minutes
                    log_info(f'[YT RECAPTCHA] Polling for solution (attempt {attempt + 1}/30)')
                    await asyncio.sleep(10)
                    
                    async with session.post(get_result_url, json=result_data) as result_response:
                        result_json = await result_response.json()
                        if result_json.get('status') == 'ready':
                            solution = result_json.get('solution', {}).get('gRecaptchaResponse')
                            if solution:
                                log_info(f'[YT RECAPTCHA] Solution received: {solution[:20]}...')
                                return solution
                            else:
                                log_error('[YT RECAPTCHA] No solution in response')
                                return ''
                        elif result_json.get('errorId') != 0:
                            log_error(f'[YT RECAPTCHA] Error getting result: {result_json}')
                            return ''
                        else:
                            log_info(f'[YT RECAPTCHA] Not ready yet, will retry...')
                            continue
                
                log_error('[YT RECAPTCHA] Timeout waiting for solution')
                return ''
                
    except Exception as e:
        log_error(f'[YT RECAPTCHA] Error solving reCaptcha: {e}')
        return ''


async def _submit_recaptcha_solution(page: Page, solution: str) -> None:
    """Submit reCaptcha solution to the page"""
    try:
        log_info(f'[YT RECAPTCHA] Submitting solution: {solution[:20]}...')
        
        # Method 1: Try to find the reCaptcha response textarea
        response_textarea = page.locator('textarea[name="g-recaptcha-response"]').first
        if await response_textarea.is_visible():
            await response_textarea.fill(solution)
            log_info('[YT RECAPTCHA] Solution submitted to textarea')
            
            # Try to trigger form submission
            await page.evaluate('''
                () => {
                    // Try to find and click submit button - Universal selectors
                    const submitButtons = document.querySelectorAll('button[type="submit"], input[type="submit"]');
                    for (let btn of submitButtons) {
                        if (btn.offsetParent !== null) { // Check if visible
                            btn.click();
                            return 'submit_clicked';
                        }
                    }
                    
                    // Try to find next buttons in different languages
                    const nextButtons = document.querySelectorAll('button');
                    for (let btn of nextButtons) {
                        const text = btn.textContent || btn.innerText || '';
                        if (text.includes('Next') || text.includes('Siguiente') || text.includes('Weiter') || text.includes('Suivant')) {
                            if (btn.offsetParent !== null) {
                                btn.click();
                                return 'next_clicked';
                            }
                        }
                    }
                    
                    // Try to trigger form submission
                    const forms = document.querySelectorAll('form');
                    for (let form of forms) {
                        form.submit();
                        return 'form_submitted';
                    }
                    
                    return 'no_submit_found';
                }
            ''')
            
            await human_like_delay(3000, 6000)
            return
        
        # Method 2: Try to submit via JavaScript callback
        callback_result = await page.evaluate(f'''
            () => {{
                try {{
                    // Find callback function
                    const callbackElements = document.querySelectorAll('[data-callback]');
                    for (let element of callbackElements) {{
                        const callbackName = element.getAttribute('data-callback');
                        if (callbackName && window[callbackName]) {{
                            window[callbackName]('{solution}');
                            return 'callback_executed';
                        }}
                    }}
                    
                    // Try to trigger grecaptcha callback manually
                    if (window.grecaptcha) {{
                        // Find all reCaptcha widgets
                        const widgets = document.querySelectorAll('.g-recaptcha');
                        for (let widget of widgets) {{
                            const widgetId = widget.getAttribute('data-widget-id') || 
                                           widget.querySelector('[data-widget-id]')?.getAttribute('data-widget-id');
                            if (widgetId) {{
                                // Try to execute callback
                                const callback = widget.getAttribute('data-callback');
                                if (callback && window[callback]) {{
                                    window[callback]('{solution}');
                                    return 'grecaptcha_callback_executed';
                                }}
                            }}
                        }}
                    }}
                    
                    return 'no_callback_found';
                }} catch (e) {{
                    return 'error: ' + e.message;
                }}
            }}
        ''')
        
        log_info(f'[YT RECAPTCHA] Callback result: {callback_result}')
        
        # Method 3: Click primary action (Next) using universal XPaths
        await _click_google_next_universal(page)
        
        await human_like_delay(3000, 6000)
        
    except Exception as e:
        log_warning(f'[YT RECAPTCHA] Error submitting solution: {e}')


async def _handle_basic_verification(page: Page, password: str, proxy: Optional[Dict] = None, user_agent: Optional[str] = None) -> None:
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
        # CAPTCHA placeholder wait - now with RuCaptcha support
        captcha_img = page.locator(YOUTUBE_SELECTORS['captcha_img'][0])
        if await captcha_img.is_visible():
            log_warning('[YT VERIFY] CAPTCHA detected; attempting to solve with RuCaptcha')
            await _handle_recaptcha_check(page, proxy=proxy, user_agent=user_agent)
        # Also check for reCaptcha in verification page
        recaptcha_iframe = page.locator('iframe[src*="recaptcha"]')
        if await recaptcha_iframe.is_visible():
            log_warning('[YT VERIFY] reCaptcha detected in verification page')
            await _handle_recaptcha_check(page, proxy=proxy, user_agent=user_agent)
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


async def _click_google_next_universal(page: Page) -> None:
    """Click Google primary action Next button using robust, language-agnostic XPath fallbacks."""
    try:
        await human_like_delay(500, 1200)

        # 1) Button by jsname and visible text in common languages
        next_locators = [
            # Button with jsname and visible localized label
            '//button[@jsname="LgbsSe" and .//span[contains(normalize-space(.), "Next") or contains(normalize-space(.), "Siguiente") or contains(normalize-space(.), "Weiter") or contains(normalize-space(.), "Suivant") or contains(normalize-space(.), "Далее")]]',
            # Primary action container -> button
            '//div[@jsname="Njthtb"]//button[@jsname="LgbsSe"]',
            # Action footer with primary action label attribute
            '//div[@data-primary-action-label]//button[@jsname="LgbsSe"]',
            # Any visible Next-like button as a fallback
            '//button[.//span[contains(., "Next") or contains(., "Siguiente") or contains(., "Weiter") or contains(., "Suivant") or contains(., "Далее")]]',
        ]

        for sel in next_locators:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    log_info(f"[YT RECAPTCHA] Clicking primary action button via selector: {sel}")
                    await btn.click()
                    await human_like_delay(2500, 5000)
                    return
            except Exception as e:
                log_warning(f"[YT RECAPTCHA] Failed clicking selector {sel}: {e}")
                continue

        # As a last resort, try clicking any visible submit button
        try:
            fallback_btn = page.locator('//button[@type="submit"]').first
            if await fallback_btn.is_visible():
                log_info('[YT RECAPTCHA] Clicking fallback submit button')
                await fallback_btn.click()
                await human_like_delay(2500, 5000)
        except Exception:
            pass
    except Exception as e:
        log_warning(f"[YT RECAPTCHA] Error in _click_google_next_universal: {e}")


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
    log_info(f"[YT RECAPTCHA] Passing to solver -> proxy: {'yes' if proxy else 'no'}, userAgent: {'yes' if user_agent else 'no'}")

    # Login
    if not await login_to_google(page, email, password, proxy=proxy, user_agent=user_agent):
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


