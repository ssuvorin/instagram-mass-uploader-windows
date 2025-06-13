import os
import time
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class RuCaptchaSolver:
    """
    Класс для решения reCAPTCHA v2 через ruCAPTCHA API
    Документация: https://rucaptcha.com/api-docs/recaptcha-v2
    """
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('RUCAPTCHA_API_KEY') or os.environ.get('CAPTCHA_API_KEY')
        self.base_url = "https://rucaptcha.com"
        self.create_task_url = f"{self.base_url}/createTask"
        self.get_result_url = f"{self.base_url}/getTaskResult"
        
        if not self.api_key:
            logger.warning("⚠️ No reCAPTCHA API key found. Set RUCAPTCHA_API_KEY environment variable")
    
    def solve_recaptcha_v2(self, site_key, page_url, proxy=None, user_agent=None, cookies=None, timeout=120):
        """
        Решить reCAPTCHA v2
        
        Args:
            site_key (str): Ключ сайта reCAPTCHA (data-sitekey)
            page_url (str): URL страницы с капчей
            proxy (dict): Прокси в формате {"type": "http", "host": "...", "port": ..., "login": "...", "password": "..."}
            user_agent (str): User-Agent браузера
            cookies (str): Куки в формате "key1=val1; key2=val2"
            timeout (int): Таймаут в секундах
            
        Returns:
            str: Токен решения капчи или None в случае ошибки
        """
        
        if not self.api_key:
            logger.error("❌ reCAPTCHA API key not configured")
            return None
        
        logger.info(f"🤖 Starting reCAPTCHA v2 solving for {page_url}")
        
        # Создание задачи
        task_id = self._create_task(site_key, page_url, proxy, user_agent, cookies)
        if not task_id:
            return None
        
        # Ожидание решения
        return self._wait_for_result(task_id, timeout)
    
    def _create_task(self, site_key, page_url, proxy=None, user_agent=None, cookies=None):
        """Создать задачу решения капчи"""
        
        # Базовая задача
        task_data = {
            "type": "RecaptchaV2TaskProxyless" if not proxy else "RecaptchaV2Task",
            "websiteURL": page_url,
            "websiteKey": site_key
        }
        
        # Добавляем дополнительные параметры
        if user_agent:
            task_data["userAgent"] = user_agent
            logger.info(f"🌐 Added User-Agent to task: {user_agent[:80]}{'...' if len(user_agent) > 80 else ''}")
            
        if cookies:
            task_data["cookies"] = cookies
            cookie_preview = cookies[:100] + ('...' if len(cookies) > 100 else '')
            logger.info(f"🍪 Added cookies to task: {cookie_preview}")
            
        # Если используется прокси
        if proxy:
            task_data.update({
                "proxyType": proxy.get("type", "http"),
                "proxyAddress": proxy["host"],
                "proxyPort": proxy["port"]
            })
            
            if proxy.get("login"):
                task_data["proxyLogin"] = proxy["login"]
            if proxy.get("password"):
                task_data["proxyPassword"] = proxy["password"]
            
            logger.info(f"🔒 Added proxy to task: {proxy['host']}:{proxy['port']} (type: {proxy.get('type', 'http')})")
        else:
            logger.info("⚠️ No proxy added to task - using direct connection")
        
        # Запрос создания задачи
        payload = {
            "clientKey": self.api_key,
            "task": task_data
        }
        
        try:
            logger.info(f"📤 Sending task to ruCAPTCHA: {task_data['type']}")
            response = requests.post(self.create_task_url, json=payload, timeout=30)
            result = response.json()
            
            if result.get("errorId") == 0:
                task_id = result.get("taskId")
                logger.info(f"✅ Task created successfully. Task ID: {task_id}")
                return task_id
            else:
                logger.error(f"❌ Failed to create task: {result.get('errorDescription', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating captcha task: {str(e)}")
            return None
    
    def _wait_for_result(self, task_id, timeout=120):
        """Ожидать результат решения капчи"""
        
        start_time = time.time()
        check_interval = 5  # Проверяем каждые 5 секунд
        
        logger.info(f"⏳ Waiting for captcha solution (timeout: {timeout}s)")
        
        while time.time() - start_time < timeout:
            try:
                payload = {
                    "clientKey": self.api_key,
                    "taskId": task_id
                }
                
                response = requests.post(self.get_result_url, json=payload, timeout=30)
                result = response.json()
                
                if result.get("errorId") == 0:
                    if result.get("status") == "ready":
                        solution = result.get("solution", {}).get("gRecaptchaResponse")
                        if solution:
                            logger.info("✅ Captcha solved successfully!")
                            return solution
                        else:
                            logger.error("❌ No solution in response")
                            return None
                    
                    elif result.get("status") == "processing":
                        elapsed = int(time.time() - start_time)
                        logger.info(f"⏳ Still processing... ({elapsed}s elapsed)")
                        time.sleep(check_interval)
                        continue
                    
                    else:
                        logger.error(f"❌ Unexpected status: {result.get('status')}")
                        return None
                
                else:
                    logger.error(f"❌ Error getting result: {result.get('errorDescription', 'Unknown error')}")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Error checking captcha result: {str(e)}")
                time.sleep(check_interval)
                continue
        
        logger.error(f"❌ Captcha solving timeout ({timeout}s)")
        return None
    
    def get_balance(self):
        """Получить баланс аккаунта"""
        if not self.api_key:
            return None
        
        try:
            payload = {"clientKey": self.api_key}
            response = requests.post(f"{self.base_url}/getBalance", json=payload, timeout=10)
            result = response.json()
            
            if result.get("errorId") == 0:
                balance = result.get("balance", 0)
                logger.info(f"💰 ruCAPTCHA balance: ${balance}")
                return balance
            else:
                logger.error(f"❌ Error getting balance: {result.get('errorDescription')}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error checking balance: {str(e)}")
            return None


def detect_recaptcha_on_page(page):
    """
    Определить наличие reCAPTCHA на странице и извлечь параметры
    
    Args:
        page: Playwright page object
        
    Returns:
        dict: Параметры капчи или None если капча не найдена
    """
    try:
        # Проверяем наличие iframe с reCAPTCHA
        recaptcha_iframe = page.locator('iframe[title*="recaptcha" i], iframe[src*="recaptcha"], iframe[id*="recaptcha"], iframe[title*="Google Recaptcha"]').first
        
        if recaptcha_iframe.count() > 0:
            logger.info("🔍 reCAPTCHA iframe detected")
            
            # Получаем URL страницы
            page_url = page.url
            
            # Пытаемся найти sitekey различными способами
            site_key = None
            
            # Способ 1: через data-sitekey атрибут
            try:
                sitekey_element = page.locator('[data-sitekey]').first
                if sitekey_element.count() > 0:
                    site_key = sitekey_element.get_attribute('data-sitekey')
                    logger.info(f"✅ Found sitekey via data-sitekey: {site_key}")
            except:
                pass
            
            # Способ 2: через скрипт поиска в iframe src
            if not site_key:
                try:
                    iframe_src = recaptcha_iframe.get_attribute('src')
                    if iframe_src and 'recaptcha' in iframe_src.lower():
                        # Пытаемся извлечь sitekey из URL
                        import re
                        match = re.search(r'[?&]k=([^&]+)', iframe_src)
                        if match:
                            site_key = match.group(1)
                            logger.info(f"✅ Found sitekey in iframe src: {site_key}")
                except:
                    pass
            
            # Способ 3: через window.recaptcha
            if not site_key:
                try:
                    site_key = page.evaluate("""() => {
                        // Ищем в window объектах
                        if (window.grecaptcha && window.grecaptcha.render) {
                            const elements = document.querySelectorAll('[data-sitekey]');
                            for (let el of elements) {
                                return el.getAttribute('data-sitekey');
                            }
                        }
                        
                        // Ищем в скриптах
                        const scripts = document.querySelectorAll('script');
                        for (let script of scripts) {
                            const match = script.innerHTML.match(/['"](6[a-zA-Z0-9_-]{39})['"]/);
                            if (match) return match[1];
                        }
                        
                        return null;
                    }""")
                    if site_key:
                        logger.info(f"✅ Found sitekey via JavaScript: {site_key}")
                except:
                    pass
            
            # Способ 4: стандартный ключ Instagram
            if not site_key:
                # Instagram часто использует известные ключи
                instagram_sitekeys = [
                    "6LfI9gcTAAAAAJz0P5ALAU4K4-kCpB9PBKH9q3Zu",  # Основной ключ Instagram
                    "6Le_ZMEZAAAAAKGCeFBjgKYRaJ5tIwjh6e-vgKA-",  # Альтернативный ключ
                ]
                
                for test_key in instagram_sitekeys:
                    site_key = test_key
                    logger.info(f"🔧 Using known Instagram sitekey: {site_key}")
                    break
            
            if not site_key:
                logger.error("❌ Could not find reCAPTCHA sitekey")
                return None
            
            return {
                "site_key": site_key,
                "page_url": page_url,
                "iframe_present": True
            }
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error detecting reCAPTCHA: {str(e)}")
        return None


async def solve_recaptcha_if_present(page, account_details=None, max_attempts=3):
    """
    Проверить наличие reCAPTCHA на странице и решить её если найдена
    
    Args:
        page: Playwright page object
        account_details: Детали аккаунта (для прокси и user-agent)
        max_attempts: Максимальное количество попыток
        
    Returns:
        bool: True если капча решена или отсутствует, False если не удалось решить
    """
    
    for attempt in range(max_attempts):
        try:
            # Ждем немного для загрузки страницы
            await page.wait_for_timeout(2000)
            
            # Проверяем наличие капчи
            captcha_params = detect_recaptcha_on_page(page)
            
            if not captcha_params:
                logger.info("✅ No reCAPTCHA detected")
                return True
            
            logger.info(f"🤖 reCAPTCHA detected, attempting to solve (attempt {attempt + 1}/{max_attempts})")
            
            # Создаем решатель капчи
            solver = RuCaptchaSolver()
            
            # Подготавливаем параметры
            user_agent = None
            proxy = None
            cookies = None
            
            if account_details:
                # User-Agent из текущего браузера (Dolphin профиля)
                user_agent = await page.evaluate('navigator.userAgent')
                logger.info(f"🌐 Using User-Agent from Dolphin profile: {user_agent[:100]}{'...' if len(user_agent) > 100 else ''}")
                
                # Прокси из аккаунта
                if account_details.get("proxy"):
                    proxy_data = account_details["proxy"]
                    proxy = {
                        "type": proxy_data.get("type", "http").lower(),
                        "host": proxy_data.get("host"),
                        "port": proxy_data.get("port"),
                        "login": proxy_data.get("user"),
                        "password": proxy_data.get("pass")
                    }
                    logger.info(f"🔒 Using proxy for reCAPTCHA: {proxy['host']}:{proxy['port']} (type: {proxy['type']})")
                else:
                    logger.info("⚠️ No proxy found in account_details for reCAPTCHA solving")
                
                # Куки из текущего браузера (Dolphin профиля)
                try:
                    page_cookies = await page.context.cookies()
                    if page_cookies:
                        cookies = "; ".join([f"{c['name']}={c['value']}" for c in page_cookies])
                        # Логируем количество кук и первые несколько для проверки
                        cookie_count = len(page_cookies)
                        sample_cookies = [f"{c['name']}={c['value'][:10]}..." for c in page_cookies[:3]]
                        logger.info(f"🍪 Using {cookie_count} cookies from Dolphin profile: {', '.join(sample_cookies)}")
                    else:
                        logger.info("⚠️ No cookies found in Dolphin profile")
                        cookies = None
                except Exception as cookie_error:
                    logger.warning(f"⚠️ Error extracting cookies from Dolphin profile: {str(cookie_error)}")
                    cookies = None
            
            # Решаем капчу
            solution = solver.solve_recaptcha_v2(
                site_key=captcha_params["site_key"],
                page_url=captcha_params["page_url"],
                proxy=proxy,
                user_agent=user_agent,
                cookies=cookies,
                timeout=180  # 3 минуты
            )
            
            if not solution:
                logger.error(f"❌ Failed to solve reCAPTCHA (attempt {attempt + 1})")
                if attempt < max_attempts - 1:
                    await page.wait_for_timeout(5000)  # Ждем перед следующей попыткой
                continue
            
            # Вставляем решение в страницу
            success = await _inject_captcha_solution(page, solution)
            
            if success:
                logger.info("✅ reCAPTCHA solved and injected successfully")
                return True
            else:
                logger.error(f"❌ Failed to inject solution (attempt {attempt + 1})")
                if attempt < max_attempts - 1:
                    await page.wait_for_timeout(5000)
                continue
                
        except Exception as e:
            logger.error(f"❌ Error solving reCAPTCHA (attempt {attempt + 1}): {str(e)}")
            if attempt < max_attempts - 1:
                await page.wait_for_timeout(5000)
            continue
    
    logger.error("❌ Failed to solve reCAPTCHA after all attempts")
    return False


async def _inject_captcha_solution(page, solution):
    """Вставить решение капчи в страницу"""
    try:
        logger.info("💉 Injecting reCAPTCHA solution into page")
        
        # Способ 1: Через g-recaptcha-response элемент
        success = await page.evaluate(f"""(solution) => {{
            try {{
                // Найти и заполнить скрытое поле
                const responseField = document.querySelector('#g-recaptcha-response') || 
                                    document.querySelector('[name="g-recaptcha-response"]') ||
                                    document.querySelector('#recaptcha-input') ||
                                    document.querySelector('input[type="hidden"][id*="recaptcha"]');
                
                if (responseField) {{
                    responseField.value = solution;
                    responseField.style.display = 'block';
                    console.log('✅ Solution injected into response field');
                    
                    // Trigger events
                    responseField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    responseField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    
                    return true;
                }}
                
                return false;
            }} catch (e) {{
                console.error('Error injecting solution:', e);
                return false;
            }}
        }}""", solution)
        
        if success:
            # Способ 2: Через window.grecaptcha callback
            await page.evaluate(f"""(solution) => {{
                try {{
                    if (window.grecaptcha && window.grecaptcha.getResponse) {{
                        // Попытка установить через grecaptcha API
                        const widgets = document.querySelectorAll('[data-sitekey]');
                        for (let widget of widgets) {{
                            const widgetId = widget.getAttribute('data-widget-id');
                            if (widgetId !== null) {{
                                window.grecaptcha.reset(widgetId);
                                // Симулируем успешное решение
                                if (widget.getAttribute('data-callback')) {{
                                    const callback = window[widget.getAttribute('data-callback')];
                                    if (typeof callback === 'function') {{
                                        callback(solution);
                                    }}
                                }}
                            }}
                        }}
                    }}
                    
                    // Активируем кнопки
                    const submitButtons = document.querySelectorAll('button[disabled], [aria-disabled="true"]');
                    for (let btn of submitButtons) {{
                        btn.removeAttribute('disabled');
                        btn.removeAttribute('aria-disabled');
                        btn.style.pointerEvents = 'auto';
                        if (btn.style.background && btn.style.background.includes('rgba')) {{
                            btn.style.background = btn.style.background.replace(/rgba\\([^,]+,[^,]+,[^,]+,[^)]+\\)/g, 'rgb(0, 149, 246)');
                        }}
                    }}
                    
                    console.log('✅ Solution processed');
                    return true;
                }} catch (e) {{
                    console.error('Error in callback processing:', e);
                    return false;
                }}
            }}""", solution)
        
        # Ждем обновления UI
        await page.wait_for_timeout(2000)
        
        # Проверяем, что кнопка "Далее" стала активной
        next_button = page.locator('button:has-text("Далее"), [role="button"]:has-text("Далее"), [aria-label="Далее"]').first
        
        if next_button.count() > 0:
            # Проверяем, стала ли кнопка активной
            is_enabled = await next_button.evaluate('''el => {
                return !el.hasAttribute('disabled') && 
                       el.getAttribute('aria-disabled') !== 'true' &&
                       el.style.pointerEvents !== 'none';
            }''')
            
            if is_enabled:
                logger.info("✅ Captcha solved - Next button is now enabled")
                
                # Нажимаем кнопку "Далее"
                await next_button.click()
                await page.wait_for_timeout(3000)
                
                return True
            else:
                logger.warning("⚠️ Solution injected but button still disabled")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error injecting captcha solution: {str(e)}")
        return False


def solve_recaptcha_if_present_sync(page, account_details=None, max_attempts=3):
    """
    Synchronous version of solve_recaptcha_if_present
    Detects and solves reCAPTCHA v2 if present on the page
    """
    try:
        logger.info("🔍 Starting synchronous reCAPTCHA detection...")
        
        # Check if reCAPTCHA API key is available
        api_key = os.environ.get('RUCAPTCHA_API_KEY') or os.environ.get('CAPTCHA_API_KEY')
        if not api_key:
            logger.warning("⚠️ No reCAPTCHA API key found - skipping captcha solving")
            return False
        
        # Detect reCAPTCHA on page
        captcha_params = detect_recaptcha_on_page(page)
        if not captcha_params:
            logger.info("ℹ️ No reCAPTCHA detected on page")
            return True  # No captcha to solve
        
        site_key = captcha_params.get('site_key')
        if not site_key:
            logger.warning("⚠️ reCAPTCHA detected but no sitekey found")
            return False
        
        logger.info(f"🔧 reCAPTCHA detected with sitekey: {site_key}")
        
        # Initialize solver
        solver = RuCaptchaSolver(api_key)
        current_url = page.url
        
        # Prepare additional parameters
        user_agent = None
        cookies = None
        proxy = None
        
        try:
            # Get User-Agent from current browser
            user_agent = page.evaluate('navigator.userAgent')
            logger.info(f"🌐 Using User-Agent from browser: {user_agent[:100]}{'...' if len(user_agent) > 100 else ''}")
        except Exception as e:
            logger.warning(f"⚠️ Could not get User-Agent: {e}")
        
        try:
            # Get cookies from current context
            cookies_list = page.context.cookies()
            if cookies_list:
                cookies = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_list])
                logger.info(f"🍪 Using {len(cookies_list)} cookies from browser context")
        except Exception as e:
            logger.warning(f"⚠️ Could not get cookies: {e}")
        
        # Get proxy from account_details if available
        if account_details and account_details.get("proxy"):
            proxy_data = account_details["proxy"]
            proxy = {
                "type": proxy_data.get("type", "http").lower(),
                "host": proxy_data.get("host"),
                "port": proxy_data.get("port"),
                "login": proxy_data.get("user"),
                "password": proxy_data.get("pass")
            }
            logger.info(f"🔒 Using proxy for reCAPTCHA: {proxy['host']}:{proxy['port']}")
        
        # Attempt to solve reCAPTCHA
        for attempt in range(max_attempts):
            try:
                logger.info(f"🚀 reCAPTCHA solving attempt {attempt + 1}/{max_attempts}")
                
                # Solve the captcha using the correct method name
                solution = solver.solve_recaptcha_v2(
                    site_key=site_key,
                    page_url=current_url,
                    user_agent=user_agent,
                    cookies=cookies,
                    proxy=proxy
                )
                
                if solution:
                    logger.info("✅ reCAPTCHA solved successfully, injecting solution...")
                    
                    # Inject solution into page
                    success = inject_captcha_solution_sync(page, solution)
                    
                    if success:
                        logger.info("✅ reCAPTCHA solution injected successfully")
                        return True
                    else:
                        logger.error("❌ Failed to inject reCAPTCHA solution")
                        if attempt < max_attempts - 1:
                            logger.info(f"🔄 Retrying... (attempt {attempt + 2}/{max_attempts})")
                            continue
                else:
                    logger.error(f"❌ Failed to solve reCAPTCHA (attempt {attempt + 1})")
                    if attempt < max_attempts - 1:
                        logger.info(f"🔄 Retrying... (attempt {attempt + 2}/{max_attempts})")
                        continue
                        
            except Exception as e:
                logger.error(f"❌ Error during reCAPTCHA solving attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    logger.info(f"🔄 Retrying... (attempt {attempt + 2}/{max_attempts})")
                    continue
        
        logger.error(f"❌ Failed to solve reCAPTCHA after {max_attempts} attempts")
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in sync reCAPTCHA solving: {e}")
        return False

def inject_captcha_solution_sync(page, solution):
    """
    Synchronous version of solution injection
    Inject reCAPTCHA solution into the page
    """
    try:
        logger.info("💉 Injecting reCAPTCHA solution into page...")
        
        # Method 1: Direct callback execution
        try:
            logger.info("🎯 Trying direct callback execution...")
            result = page.evaluate(f"""
                () => {{
                    if (window.grecaptcha && window.grecaptcha.getResponse) {{
                        // Find the reCAPTCHA widget
                        const captchaElements = document.querySelectorAll('[data-sitekey]');
                        if (captchaElements.length > 0) {{
                            // Execute callback with solution
                            if (window.___grecaptcha_cfg && window.___grecaptcha_cfg.clients) {{
                                Object.keys(window.___grecaptcha_cfg.clients).forEach(key => {{
                                    const client = window.___grecaptcha_cfg.clients[key];
                                    if (client && client.callback) {{
                                        client.callback('{solution}');
                                    }}
                                }});
                                return true;
                            }}
                        }}
                    }}
                    return false;
                }}
            """)
            
            if result:
                logger.info("✅ Direct callback execution successful")
                time.sleep(2)  # Wait for page to process
                return True
                
        except Exception as e:
            logger.warning(f"⚠️ Direct callback failed: {e}")
        
        # Method 2: Textarea injection
        try:
            logger.info("🎯 Trying textarea injection...")
            result = page.evaluate(f"""
                () => {{
                    const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (textarea) {{
                        textarea.style.display = 'block';
                        textarea.value = '{solution}';
                        
                        // Trigger events
                        textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        
                        // Hide it again
                        setTimeout(() => {{ textarea.style.display = 'none'; }}, 100);
                        return true;
                    }}
                    return false;
                }}
            """)
            
            if result:
                logger.info("✅ Textarea injection successful")
                time.sleep(2)
                return True
                
        except Exception as e:
            logger.warning(f"⚠️ Textarea injection failed: {e}")
        
        # Method 3: Global variable injection
        try:
            logger.info("🎯 Trying global variable injection...")
            page.evaluate(f"""
                () => {{
                    window.recaptchaSolution = '{solution}';
                    window.dispatchEvent(new CustomEvent('recaptchaSolved', {{
                        detail: {{ solution: '{solution}' }}
                    }}));
                }}
            """)
            
            logger.info("✅ Global variable injection completed")
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Global variable injection failed: {e}")
        
        logger.error("❌ All injection methods failed")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error injecting reCAPTCHA solution: {e}")
        return False 