"""
Optimized Instagram Login Functions
Provides streamlined and modular login functionality
"""

import time
import random
from .instagram_automation import InstagramLoginHandler
from .browser_utils import ErrorHandler, PageUtils
from .human_behavior import init_human_behavior
from .logging_utils import log_info, log_error, log_warning
from .task_utils import clear_human_verification_badge


def perform_instagram_login_optimized(page, account_details):
    """Optimized Instagram login with enhanced logged-in detection"""
    try:
        from .selectors_config import InstagramSelectors
        from .bulk_tasks_playwright import handle_cookie_consent  # Import cookie handler
        
        selectors = InstagramSelectors()
        username = account_details['username']
        password = account_details['password']
        tfa_secret = account_details.get('tfa_secret')
        
        log_info(f"Starting login process for: {username}")
        
        # Handle cookie consent modal BEFORE login check
        handle_cookie_consent(page)
        
        # Enhanced check if already logged in
        logged_in_status = _check_if_already_logged_in(page, selectors)
        
        if logged_in_status == "SUSPENDED":
            log_error(f"[BLOCK] Account {username} is SUSPENDED - cannot proceed with login")
            return "SUSPENDED"
        elif logged_in_status:
            log_info(f"[OK] Already logged in! Skipping login process for user: {username}")
            # Clear human verification badge if previously set
            clear_human_verification_badge(username)
            return True
        
        # Perform login steps
        if not _fill_login_credentials(page, username, password):
            return False
        
        # [OK] ДОПОЛНИТЕЛЬНАЯ ПАУЗА: Ждем после заполнения полей перед отправкой
        log_info("[WAIT] Waiting after filling credentials before form submission...")
        time.sleep(random.uniform(3, 6))  # Дополнительная пауза для человекоподобного поведения
        
        # Submit login form
        if not _submit_login_form(page):
            return False
        
        # Handle 2FA if needed
        return _handle_login_completion(page, account_details, selectors)
        
    except Exception as e:
        log_error(f"Login process failed: {str(e)}")
        return False


def _check_if_already_logged_in(page, selectors):
    """Check if user is already logged in with enhanced detection"""
    log_info("[SEARCH] Checking if already logged in...")
    
    # Wait a moment for page to fully load
    time.sleep(random.uniform(2, 4))
    
    # Get current URL for context
    current_url = page.url
    log_info(f"[SEARCH] Current URL: {current_url}")
    
    # Check for account suspension first - this is critical
    log_info("[BLOCK] Checking for account suspension...")
    
    # Check page text for suspension keywords (PRIMARY METHOD)
    try:
        page_text = page.inner_text('body') or ""
        suspension_keywords = [
            'мы приостановили ваш аккаунт',
            'приостановили ваш аккаунт',
            'аккаунт приостановлен',
            'ваш аккаунт приостановлен',
            'account suspended',
            'account has been suspended',
            'we suspended your account',
            'your account is suspended',
            'your account has been disabled',
            'account disabled',
            'аккаунт заблокирован',
            'ваш аккаунт заблокирован',
            'временно приостановлен',
            'temporarily suspended',
            'осталось',  # "Осталось X дней, чтобы обжаловать"
            'days left'  # "X days left to appeal"
        ]
        
        for keyword in suspension_keywords:
            if keyword in page_text.lower():
                log_error(f"[BLOCK] Account suspension detected from text: '{keyword}'")
                log_error(f"[BLOCK] Page text sample: '{page_text[:200]}...'")
                return "SUSPENDED"
                
    except Exception as e:
        log_warning(f"[BLOCK] Could not check page text for suspension: {str(e)}")
    
    # Optional secondary check for URL patterns (as backup only)
    suspension_url_patterns = [
        '/accounts/suspended',
        '/challenge/suspended',
        '/suspended'
    ]
    
    url_indicates_suspension = any(pattern in current_url.lower() for pattern in suspension_url_patterns)
    if url_indicates_suspension:
        log_error(f"[BLOCK] Account suspension also detected from URL: {current_url}")
        return "SUSPENDED"
    
    # First check if we see login form elements
    login_form_present = False
    found_login_elements = []
    
    for indicator in selectors.LOGIN_FORM_INDICATORS:
        element = page.query_selector(indicator)
        if element and element.is_visible():
            login_form_present = True
            found_login_elements.append(indicator)
            log_info(f"[SEARCH] Found login form element: {indicator}")
    
    if login_form_present:
        log_info(f"[SEARCH] Login form detected with elements: {found_login_elements[:3]}")
        return False
    
    # No login form found, check for logged-in indicators
    logged_in_found = False
    found_indicators = []
    
    log_info("[SEARCH] No login form found, checking for logged-in indicators...")
    
    for i, indicator in enumerate(selectors.LOGGED_IN_INDICATORS):
        try:
            element = page.query_selector(indicator)
            if element and element.is_visible():
                # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: анализируем текст элемента
                try:
                    element_text = element.text_content() or ""
                    element_aria_label = element.get_attribute('aria-label') or ""
                    combined_text = (element_text + " " + element_aria_label).lower()
                    
                    # Исключаем элементы связанные с созданием аккаунта
                    exclusion_keywords = [
                        'новый аккаунт', 'new account', 
                        'создать аккаунт', 'create account',
                        'регистрация', 'sign up', 'signup',
                        'зарегистрироваться', 'register'
                    ]
                    
                    if any(keyword in combined_text for keyword in exclusion_keywords):
                        log_info(f"[SEARCH] Skipping element {i+1} (contains account creation text): '{element_text.strip()}'")
                        continue
                    
                    logged_in_found = True
                    found_indicators.append(indicator)
                    log_info(f"[OK] Found logged-in indicator {i+1}: {indicator}")
                    
                    if element_text.strip():
                        log_info(f"[OK] Element text: '{element_text.strip()}'")
                    
                except Exception as e:
                    # Если не можем получить текст, продолжаем как раньше
                    logged_in_found = True
                    found_indicators.append(indicator)
                    log_info(f"[OK] Found logged-in indicator {i+1}: {indicator}")
                    log_warning(f"[SEARCH] Could not analyze element text: {str(e)}")
                
                # If we found a strong indicator, we can be confident
                if any(strong_keyword in indicator.lower() for strong_keyword in [
                    'главная', 'home', 'профиль', 'profile', 'поиск', 'search', 'сообщения', 'messages'
                ]):
                    log_info(f"[OK] Strong logged-in indicator found: {indicator}")
                    break
                    
        except Exception as e:
            log_warning(f"[SEARCH] Error checking indicator {indicator}: {str(e)}")
            continue
    
    if logged_in_found:
        log_info(f"[OK] Already logged in! Found {len(found_indicators)} indicators: {found_indicators[:5]}")
        
        # Additional verification - check page title
        try:
            page_title = page.title()
            log_info(f"[OK] Page title: '{page_title}'")
            
            # Instagram main page usually has "Instagram" in title
            if "instagram" in page_title.lower():
                log_info("[OK] Page title confirms Instagram main page")
            
        except Exception as e:
            log_warning(f"[SEARCH] Could not get page title: {str(e)}")
        
        # Simulate human behavior - look around a bit
        from .bulk_tasks_playwright import simulate_human_mouse_movement, handle_save_login_info_dialog
        simulate_human_mouse_movement(page)
        time.sleep(random.uniform(1, 3))
        
        # Even if already logged in, check for save login dialog
        handle_save_login_info_dialog(page)
        
        return True
    else:
        log_info("[SEARCH] No logged-in indicators found")
        
        # Additional debugging - check what's actually on the page
        try:
            # Get page text for analysis
            page_text = page.inner_text('body') or ""
            page_text_sample = page_text[:200] if page_text else "No text found"
            log_info(f"[SEARCH] Page text sample: '{page_text_sample}...'")
            
            # Check for common Instagram keywords
            instagram_keywords = ['instagram', 'инстаграм', 'войти', 'log in', 'sign up', 'регистрация']
            found_keywords = [keyword for keyword in instagram_keywords if keyword in page_text.lower()]
            if found_keywords:
                log_info(f"[SEARCH] Found Instagram keywords: {found_keywords}")
            
        except Exception as e:
            log_warning(f"[SEARCH] Could not analyze page text: {str(e)}")
    
    return False


def _fill_login_credentials(page, username, password):
    """Fill login credentials with human-like behavior"""
    log_info("Not logged in, proceeding with login process...")
    
    # [OK] УЛУЧШЕННОЕ ЧЕЛОВЕКОПОДОБНОЕ ПОВЕДЕНИЕ: Инициализируем human behavior
    from .human_behavior import get_human_behavior, init_human_behavior
    human_behavior = get_human_behavior()
    if not human_behavior:
        init_human_behavior(page)
        human_behavior = get_human_behavior()
    
    # [OK] Симулируем сканирование страницы перед началом
    log_info("👁️ Scanning login page...")
    human_behavior.simulate_page_scanning()
    
    # Wait for and find username input - UPDATED SELECTORS
    try:
        # Try multiple selectors for username field
        username_selectors = [
            'input[name="email"]',              # Current Instagram selector  
            'input[name="username"]',           # Legacy selector
            'input[name="emailOrPhone"]',       # Alternative selector
            'input[type="text"]:not([name="pass"])',  # Any text input that's not password
            'input[aria-label*="Имя пользователя"]',
            'input[aria-label*="номер мобильного телефона"]',
            'input[aria-label*="электронный адрес"]',
            'input[placeholder*="Имя пользователя"]',
            'input[placeholder*="номер мобильного телефона"]',
            'input[placeholder*="электронный адрес"]',
        ]
        
        username_input = None
        used_selector = None
        
        for selector in username_selectors:
            try:
                username_input = page.wait_for_selector(selector, timeout=3000)
                if username_input and username_input.is_visible():
                    used_selector = selector
                    log_info(f"Found username field with selector: {selector}")
                    break
            except:
                continue
                
        if not username_input:
            log_error("Username input not found with any selector")
            return False
            
    except Exception as e:
        log_error(f"Username input not found: {str(e)}")
        return False
    
    # [OK] УЛУЧШЕННОЕ ЧЕЛОВЕКОПОДОБНОЕ ПОВЕДЕНИЕ: Ввод имени пользователя
    log_info("Entering username")
    
    # Симулируем небольшое раздумье перед вводом
    human_behavior.simulate_decision_making(options_count=1)
    
    # Продвинутое взаимодействие с элементом (движение мыши + клик)
    human_behavior.advanced_element_interaction(username_input, 'click')
    
    # Естественная пауза после клика
    time.sleep(human_behavior.get_advanced_human_delay(0.3, 0.2, 'thinking'))
    
    # [OK] Человекоподобная печать с возможными ошибками
    human_behavior.human_typing(username_input, username, simulate_mistakes=True)
    
    # [OK] Симулируем проверку введенного текста (перечитываем)
    log_info("👁️ Reviewing entered username...")
    reading_time = human_behavior.simulate_reading_time(len(username))
    time.sleep(reading_time)
    
    # [OK] Естественная пауза между полями
    transition_delay = human_behavior.get_advanced_human_delay(0.8, 0.4, 'thinking')
    time.sleep(transition_delay)
    
    # [OK] Случайное отвлечение (10% вероятность)
    human_behavior.simulate_distraction()
    
    # Find password input - UPDATED SELECTORS
    password_selectors = [
        'input[name="pass"]',               # Current Instagram selector
        'input[name="password"]',           # Legacy selector  
        'input[type="password"]',           # Any password input
        'input[aria-label*="Пароль"]',
        'input[placeholder*="Пароль"]',
    ]
    
    password_input = None
    
    for selector in password_selectors:
        try:
            password_input = page.query_selector(selector)
            if password_input and password_input.is_visible():
                log_info(f"Found password field with selector: {selector}")
                break
        except:
            continue
            
    if not password_input:
        log_error("Password input not found with any selector")
        return False
    
    # [OK] УЛУЧШЕННОЕ ЧЕЛОВЕКОПОДОБНОЕ ПОВЕДЕНИЕ: Ввод пароля
    log_info("Entering password")
    
    # Симулируем мысленную подготовку пароля
    human_behavior.simulate_decision_making(options_count=1)
    
    # Продвинутое взаимодействие с полем пароля
    human_behavior.advanced_element_interaction(password_input, 'click')
    
    # Естественная пауза после клика
    time.sleep(human_behavior.get_advanced_human_delay(0.2, 0.1, 'thinking'))
    
    # [OK] Человекоподобная печать пароля (без ошибок - люди осторожнее с паролями)
    human_behavior.human_typing(password_input, password, simulate_mistakes=False)
    
    # [OK] Небольшая пауза после ввода пароля (проверка)
    log_info("👁️ Reviewing password field...")
    time.sleep(human_behavior.get_advanced_human_delay(0.5, 0.3, 'thinking'))
    
    # [OK] Симулируем естественный перерыв если нужно
    human_behavior.simulate_break_pattern()
    
    log_info("[OK] Login credentials filled with human-like behavior")
    return True


def _submit_login_form(page):
    """Submit the login form"""
    # [OK] УЛУЧШЕННОЕ ЧЕЛОВЕКОПОДОБНОЕ ПОВЕДЕНИЕ: Получаем human behavior
    from .human_behavior import get_human_behavior
    human_behavior = get_human_behavior()
    
    # [OK] Симулируем время на размышления перед отправкой формы
    log_info("🤔 Reviewing form before submission...")
    human_behavior.simulate_decision_making(options_count=2)  # Решение "отправить" или "проверить еще раз"
    
    # UPDATED LOGIN BUTTON SELECTORS AND LOGIC
    log_info("Looking for login button...")
    
    # Try multiple selectors for login button
    login_button_selectors = [
        # Main submit button selectors
        'button[type="submit"]',
        'button:has-text("Войти")',
        'button:has-text("Log in")',
        'div[role="button"]:has-text("Войти")',
        'div[role="button"]:has-text("Log in")',
        
        # More specific selectors for Instagram's current structure
        'button:not([aria-disabled="true"]):has-text("Войти")',
        'div[role="button"]:not([aria-disabled="true"]):has-text("Войти")',
        'button:not([aria-disabled="true"]):has-text("Log in")',
        'div[role="button"]:not([aria-disabled="true"]):has-text("Log in")',
        
        # XPath selectors for better targeting
        '//button[contains(text(), "Войти") and not(@aria-disabled="true")]',
        '//button[contains(text(), "Log in") and not(@aria-disabled="true")]',
        '//div[@role="button" and contains(text(), "Войти") and not(@aria-disabled="true")]',
        '//div[@role="button" and contains(text(), "Log in") and not(@aria-disabled="true")]',
        
        # Fallback selectors (may be disabled initially)
        'button[aria-disabled="true"]:has-text("Войти")',
        'button[aria-disabled="true"]:has-text("Log in")',
        'div[role="button"][aria-disabled="true"]:has-text("Войти")',
        'div[role="button"][aria-disabled="true"]:has-text("Log in")',
    ]
    
    login_button = None
    used_selector = None
    
    # Wait for login button to become enabled (sometimes it's disabled initially)
    max_wait_time = 10  # seconds
    wait_interval = 0.5  # seconds
    waited_time = 0
    
    while waited_time < max_wait_time:
        for selector in login_button_selectors:
            try:
                if selector.startswith('//'):
                    login_button = page.query_selector(f"xpath={selector}")
                else:
                    login_button = page.query_selector(selector)
                
                if login_button and login_button.is_visible():
                    # Check if button is enabled
                    is_disabled = login_button.get_attribute('aria-disabled')
                    if is_disabled != 'true':
                        used_selector = selector
                        log_info(f"Found enabled login button with selector: {selector}")
                        break
                    else:
                        log_info(f"Found login button but it's disabled: {selector}")
                        
            except Exception as e:
                log_warning(f"Error checking selector {selector}: {str(e)}")
                continue
        
        if login_button and used_selector:
            break
            
        # [OK] ЧЕЛОВЕКОПОДОБНОЕ ПОВЕДЕНИЕ: Используем продвинутую задержку вместо простого sleep
        wait_delay = human_behavior.get_advanced_human_delay(wait_interval, 0.2, 'thinking')
        time.sleep(wait_delay)
        waited_time += wait_delay
        log_info(f"Waiting for login button to become enabled... ({waited_time:.1f}s)")
    
    # Try to click the login button
    if login_button and used_selector:
        try:
            log_info(f"Clicking login button with selector: {used_selector}")
            
            # [OK] УЛУЧШЕННОЕ ЧЕЛОВЕКОПОДОБНОЕ ПОВЕДЕНИЕ: Продвинутое взаимодействие с кнопкой
            # 1. Симулируем небольшое колебание перед кликом
            hesitation_delay = human_behavior.get_advanced_human_delay(0.5, 0.3, 'thinking')
            time.sleep(hesitation_delay)
            
            # 2. Продвинутое взаимодействие (движение мыши + клик)
            human_behavior.advanced_element_interaction(login_button, 'click')
            
            log_info("Login button clicked successfully")
        except Exception as e:
            log_warning(f"Error clicking login button: {str(e)}")
            # Fallback: try pressing Enter on password field
            log_info("Trying fallback: pressing Enter on password field")
            password_input = page.query_selector('input[name="pass"]') or page.query_selector('input[type="password"]')
            if password_input:
                # [OK] Человекоподобное нажатие Enter
                human_behavior.advanced_element_interaction(password_input, 'click')
                time.sleep(human_behavior.get_advanced_human_delay(0.2, 0.1, 'thinking'))
                password_input.press("Enter")
            else:
                log_error("No password field found for Enter fallback")
                return False
    else:
        log_warning("Login button not found or not enabled, trying Enter key fallback")
        # Fallback: press Enter on password field
        password_input = page.query_selector('input[name="pass"]') or page.query_selector('input[type="password"]')
        if password_input:
            # [OK] Человекоподобное нажатие Enter
            human_behavior.advanced_element_interaction(password_input, 'click')
            time.sleep(human_behavior.get_advanced_human_delay(0.2, 0.1, 'thinking'))
            password_input.press("Enter")
            log_info("Pressed Enter on password field as fallback")
        else:
            log_error("No password field found for Enter fallback")
            return False
    
    # [OK] УЛУЧШЕННОЕ ОЖИДАНИЕ: Используем продвинутые человекоподобные задержки
    log_info("[WAIT] Waiting for page to load after login submission...")
    
    # [OK] Симулируем естественное ожидание человека после клика
    post_click_delay = human_behavior.get_advanced_human_delay(8, 3, 'resting')
    time.sleep(post_click_delay)
    
    # Дополнительно ждем стабилизации DOM
    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        log_info("[OK] DOM content loaded")
    except Exception as e:
        log_warning(f"[WARN] DOM load timeout: {str(e)}")
    
    # [OK] Еще одна естественная пауза с симуляцией ожидания
    final_wait = human_behavior.get_advanced_human_delay(3, 2, 'resting')
    time.sleep(final_wait)
    
    log_info("[OK] Login form submission completed, page should be loaded")
    
    return True


def _check_for_human_verification_dialog(page):
    """Check for human verification dialog that requires manual verification"""
    try:
        log_info("[BOT] Checking for human verification dialog...")
        
        # Wait a moment for any dialogs to appear
        time.sleep(random.uniform(2, 4))
        
        # Keywords that indicate human verification requirement
        human_verification_keywords = [
            'подтвердите, что вы — человек',
            'подтвердите, что вы человек', 
            'confirm that you are human',
            'verify that you are human',
            'чтобы использовать свой аккаунт, подтвердите',
            'to use your account, confirm',
            'целостности аккаунта',
            'account integrity',
            'мера предосторожности',
            'safety measure',
            'нормами сообщества',
            'community guidelines'
        ]
        
        # Check page text for human verification dialog
        try:
            page_text = page.inner_text('body') or ""
        except Exception:
            page_text = ""
        
        is_human_verification_dialog = any(keyword in page_text.lower() for keyword in human_verification_keywords)
        
        if is_human_verification_dialog:
            log_warning("[BOT] Human verification dialog detected!")
            log_warning("[BOT] Instagram requires manual human verification for this account")
            
            # Look for specific selectors from the provided HTML
            human_verification_selectors = [
                # Text-based selectors for the dialog content
                'span:has-text("подтвердите, что вы — человек")',
                'span:has-text("confirm that you are human")',
                'div[data-bloks-name="bk.components.Text"]:has-text("подтвердите")',
                'div[data-bloks-name="bk.components.Text"]:has-text("человек")',
                
                # Button selectors for "Continue" button
                'div[role="button"][aria-label="Продолжить"]',
                'div[role="button"][aria-label="Continue"]',
                'div[data-bloks-name="bk.components.Flexbox"][role="button"]:has-text("Продолжить")',
                'div[data-bloks-name="bk.components.Flexbox"][role="button"]:has-text("Continue")',
                
                # Image selector for the verification icon
                'img[src*="mIFHU0SL-7O.png"]',
                'img[alt=""]:has([src*="cdninstagram.com"])',
                
                # Container selectors
                'div[data-bloks-name="bk.components.Flexbox"]',
                'div.wbloks_1',
                
                # XPath selectors for Russian text
                '//span[contains(text(), "подтвердите, что вы")]',
                '//span[contains(text(), "человек")]',
                '//div[contains(text(), "целостности аккаунта")]',
                '//div[@role="button" and contains(text(), "Продолжить")]',
                
                # XPath selectors for English text
                '//span[contains(text(), "confirm that you")]',
                '//span[contains(text(), "human")]',
                '//div[contains(text(), "account integrity")]',
                '//div[@role="button" and contains(text(), "Continue")]',
            ]
            
            verification_dialog_found = False
            found_selector = None
            
            for selector in human_verification_selectors:
                try:
                    if selector.startswith('//'):
                        element = page.query_selector(f"xpath={selector}")
                    else:
                        element = page.query_selector(selector)
                    
                    if element and element.is_visible():
                        verification_dialog_found = True
                        found_selector = selector
                        element_text = element.text_content() or ""
                        log_warning(f"[BOT] Found human verification element: {selector}")
                        log_warning(f"[BOT] Element text: '{element_text.strip()}'")
                        break
                        
                except Exception as e:
                    log_warning(f"[BOT] Error checking selector {selector}: {str(e)}")
                    continue
            
            if verification_dialog_found:
                log_error("[BOT] [FAIL] Human verification dialog confirmed!")
                log_error("[BOT] [FAIL] This account requires manual human verification")
                log_error("[BOT] [FAIL] The account cannot be used for automation until verified")
                
                return True
            else:
                log_info("[BOT] Human verification keywords found in text but no dialog elements detected")
                log_info("[BOT] This might be a different type of verification page")
                return True  # Still treat as human verification required
        else:
            log_info("[BOT] No human verification dialog detected")
            return False
            
    except Exception as e:
        log_error(f"[BOT] Error checking for human verification dialog: {str(e)}")
        return False


def _handle_login_completion(page, account_details, selectors):
    """Handle login completion including 2FA and human verification checks"""
    log_info("Checking for 2FA requirement and other post-login dialogs...")
    
    # [OK] УЛУЧШЕННОЕ ЧЕЛОВЕКОПОДОБНОЕ ПОВЕДЕНИЕ: Получаем human behavior
    from .human_behavior import get_human_behavior
    human_behavior = get_human_behavior()
    
    # [OK] УВЕЛИЧЕННОЕ ОЖИДАНИЕ: Больше времени для полной загрузки страницы после логина
    log_info("[WAIT] Waiting for page to fully stabilize after login...")
    
    # [OK] Симулируем естественное ожидание с движениями мыши
    initial_wait = human_behavior.get_advanced_human_delay(8, 3, 'resting')
    human_behavior.simulate_idle_mouse_movement(page, duration=initial_wait)
    
    # Дополнительное ожидание загрузки DOM
    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        log_info("[OK] DOM content loaded in login completion")
    except Exception as e:
        log_warning(f"[WARN] DOM load timeout in login completion: {str(e)}")
    
    # [OK] Симулируем естественное изучение страницы после загрузки
    log_info("👁️ Naturally exploring the page after login...")
    human_behavior.simulate_ui_exploration(page)
    
    # [OK] Еще одна пауза для стабилизации с переключениями внимания
    stabilization_time = human_behavior.get_advanced_human_delay(3, 2, 'reading')
    human_behavior.simulate_attention_shifts(page)
    time.sleep(stabilization_time)
    
    log_info("[OK] Login completion waiting phase finished")
    
    # First check for human verification dialog
    if _check_for_human_verification_dialog(page):
        log_error("[FAIL] Human verification required for this account")
        raise Exception("HUMAN_VERIFICATION_REQUIRED")
    
    # Try multiple times to find verification input as page might still be loading
    tfa_input = None
    max_attempts = 5
    
    for attempt in range(max_attempts):
        log_info(f"Verification check attempt {attempt + 1}/{max_attempts}")
        
        # [OK] Симулируем естественное поведение между попытками
        if attempt > 0:
            log_info("👁️ Looking around while waiting for page to load...")
            human_behavior.simulate_attention_shifts(page)
            
            # Возможно небольшой скролл для поиска элементов
            if random.random() < 0.3:  # 30% вероятность
                human_behavior.simulate_natural_scroll(page, direction='down', amount='small')
        
        # Use the comprehensive function to find verification code input
        from .bulk_tasks_playwright import find_verification_code_input
        tfa_input = find_verification_code_input(page)
        
        if tfa_input:
            log_info(f"Found verification input on attempt {attempt + 1}")
            break
        else:
            # Check if we're already logged in (successful login without 2FA)
            for indicator in selectors.LOGGED_IN_INDICATORS:
                try:
                    element = page.query_selector(indicator)
                    if element and element.is_visible():
                        # Дополнительная проверка содержимого для исключения false positive
                        element_text = element.text_content() or ""
                        exclude_keywords = ['новый аккаунт', 'create account', 'регистр', 'sign up']
                        if any(keyword in element_text.lower() for keyword in exclude_keywords):
                            log_warning(f"[WARN] Skipping login indicator with registration text: '{element_text.strip()}'")
                            continue
                        
                        log_info(f"[OK] Login successful! Found indicator: {indicator}")
                        log_info(f"[OK] Element text: '{element_text.strip()}'")
                        
                        # [OK] Симулируем естественное поведение после успешного входа
                        log_info("[PARTY] Login successful! Exploring main page...")
                        human_behavior.simulate_page_scanning()
                        
                        # Handle save login info dialog after successful login
                        from .bulk_tasks_playwright import handle_save_login_info_dialog
                        handle_save_login_info_dialog(page)
                        
                        # Clear human verification badge if previously set
                        clear_human_verification_badge(username)
                        
                        return True
                except Exception as e:
                    log_warning(f"Error checking login indicator {indicator}: {str(e)}")
                    continue
            
            if attempt < max_attempts - 1:  # Don't wait on the last attempt
                log_info("No verification input found, waiting before retry...")
                
                # [OK] Человекоподобное ожидание между попытками
                retry_wait = human_behavior.get_advanced_human_delay(5, 2, 'thinking')
                human_behavior.simulate_idle_mouse_movement(page, duration=retry_wait)
    
    if tfa_input:
        return _handle_2fa_verification(page, account_details, tfa_input)
    
    # If no 2FA and no success indicators, check for errors
    return _check_for_login_errors(page)


def _handle_2fa_verification(page, account_details, tfa_input):
    """Handle 2FA verification process"""
    log_info("2FA verification required")
    
    try:
        page_content = page.content()
        
        # Check if this is email verification or Google Authenticator
        if any(keyword in page_content.lower() for keyword in ['email', 'почт', 'отправили', 'sent']):
            log_info("📧 Email verification detected")
            return _handle_email_verification(page, account_details, tfa_input)
        else:
            log_info("🔐 Google Authenticator verification detected")
            return _handle_authenticator_verification(page, account_details, tfa_input)
            
    except Exception as e:
        log_error(f"Error in 2FA handling: {str(e)}")
        return False


def _handle_email_verification(page, account_details, tfa_input):
    """Handle email verification with improved retry logic and error handling"""
    from .bulk_tasks_playwright import get_email_verification_code
    
    email_login = account_details.get('email_login')
    email_password = account_details.get('email_password')
    
    if not email_login or not email_password:
        log_error("📧 Email credentials not provided for verification")
        return False
    
    log_info(f"📧 Starting email verification for: {email_login}")
    
    # Try to get verification code with retries
    max_retries = 3
    verification_code = get_email_verification_code(email_login, email_password, max_retries)
    
    if verification_code:
        log_info(f"📧 Got email verification code: {verification_code}")
        
        # Additional validation before entering code
        if len(verification_code) == 6 and verification_code.isdigit():
            success = _enter_verification_code(page, tfa_input, verification_code)
            if success:
                log_info("📧 [OK] Email verification completed successfully")
                return True
            else:
                log_error("📧 [FAIL] Failed to enter verification code")
                
                # Try one more time if code entry failed
                log_info("📧 Attempting one more code retrieval...")
                retry_code = get_email_verification_code(email_login, email_password, max_retries=1)
                if retry_code and retry_code != verification_code:
                    log_info(f"📧 Got new verification code: {retry_code}")
                    return _enter_verification_code(page, tfa_input, retry_code)
                
                return False
        else:
            log_error(f"📧 Invalid verification code format: {verification_code}")
            return False
    else:
        log_error("📧 Failed to get email verification code after all attempts")
        
        # Check if the email field needs to be filled
        log_info("📧 Checking if email field needs to be filled...")
        from .bulk_tasks_playwright import detect_and_fill_email_field
        email_filled = detect_and_fill_email_field(page, email_login)
        
        if email_filled:
            log_info("📧 Email field filled, trying to get code again...")
            # Wait a bit for email to arrive
            import time
            time.sleep(10)
            final_code = get_email_verification_code(email_login, email_password, max_retries=2)
            if final_code:
                return _enter_verification_code(page, tfa_input, final_code)
        
        return False


def _handle_authenticator_verification(page, account_details, tfa_input):
    """Handle Google Authenticator verification"""
    from .bulk_tasks_playwright import get_2fa_code
    
    tfa_secret = account_details.get('tfa_secret')
    
    if not tfa_secret:
        log_error("🔐 2FA secret not provided")
        return False
    
    verification_code = get_2fa_code(tfa_secret)
    
    if verification_code:
        log_info(f"🔐 Got 2FA code: {verification_code}")
        return _enter_verification_code(page, tfa_input, verification_code)
    else:
        log_error("🔐 Failed to get 2FA code")
        return False


def _enter_verification_code(page, tfa_input, verification_code):
    """Enter verification code with human behavior"""
    import time
    import random
    
    # [OK] УЛУЧШЕННОЕ ЧЕЛОВЕКОПОДОБНОЕ ПОВЕДЕНИЕ: Получаем human behavior
    from .human_behavior import get_human_behavior
    human_behavior = get_human_behavior()
    
    log_info("Entering verification code...")
    
    # [OK] Симулируем время на чтение/запоминание кода
    log_info("👁️ Reading verification code...")
    code_reading_time = human_behavior.simulate_reading_time(len(verification_code))
    time.sleep(code_reading_time)
    
    # Проверяем, что элемент все еще в DOM
    try:
        if not tfa_input.is_attached():
            log_warning("TFA input element detached, re-finding...")
            # Пытаемся найти элемент снова
            from .bulk_tasks_playwright import find_verification_code_input
            tfa_input = find_verification_code_input(page)
            if not tfa_input:
                log_error("[FAIL] Could not re-find verification code input")
                return False
    except Exception as e:
        log_warning(f"Error checking element attachment: {str(e)}")
    
    try:
        # [OK] УЛУЧШЕННОЕ ЧЕЛОВЕКОПОДОБНОЕ ПОВЕДЕНИЕ: Продвинутое взаимодействие
        # 1. Симулируем небольшое колебание перед вводом
        log_info("🤔 Preparing to enter verification code...")
        human_behavior.simulate_decision_making(options_count=1)
        
        # 2. Продвинутое взаимодействие с полем (движение мыши + клик)
        human_behavior.advanced_element_interaction(tfa_input, 'click')
        
        # 3. Естественная пауза после клика
        time.sleep(human_behavior.get_advanced_human_delay(0.3, 0.2, 'thinking'))
        
        # [OK] Человекоподобная печать кода с естественными паузами
        log_info("⌨️ Typing verification code with human-like behavior...")
        human_behavior.human_typing(tfa_input, verification_code, simulate_mistakes=False)  # Коды обычно вводят аккуратно
        
        # [OK] Симулируем проверку введенного кода
        log_info("👁️ Reviewing entered code...")
        review_time = human_behavior.get_advanced_human_delay(0.8, 0.4, 'thinking')
        time.sleep(review_time)
        
        # [OK] Симулируем небольшое колебание перед отправкой
        log_info("🤔 Double-checking before submission...")
        hesitation_time = human_behavior.get_advanced_human_delay(0.5, 0.3, 'thinking')
        time.sleep(hesitation_time)
        
        # Try to find and click submit button
        from .bulk_tasks_playwright import find_submit_button
        submit_button = find_submit_button(page)
        
        if submit_button:
            try:
                log_info("🖱️ Clicking submit button...")
                # [OK] Продвинутое взаимодействие с кнопкой подтверждения
                human_behavior.advanced_element_interaction(submit_button, 'click')
                log_info("[OK] Submit button clicked")
            except Exception as e:
                log_warning(f"Submit button click failed: {str(e)}, trying Enter key")
                # [OK] Человекоподобное нажатие Enter
                time.sleep(human_behavior.get_advanced_human_delay(0.2, 0.1, 'thinking'))
                tfa_input.press("Enter")
        else:
            log_info("No submit button found, pressing Enter")
            # [OK] Человекоподобное нажатие Enter
            time.sleep(human_behavior.get_advanced_human_delay(0.2, 0.1, 'thinking'))
            tfa_input.press("Enter")
    
    except Exception as e:
        log_error(f"Error entering verification code: {str(e)}")
        if "not attached to the DOM" in str(e):
            log_warning("Element detached during input, this usually means page is changing")
        return False
    
    # [OK] УЛУЧШЕННОЕ ОЖИДАНИЕ: Используем продвинутые человекоподобные задержки
    log_info("[WAIT] Waiting for verification code processing...")
    
    # [OK] Симулируем естественное ожидание после отправки кода
    processing_wait = human_behavior.get_advanced_human_delay(10, 4, 'resting')
    time.sleep(processing_wait)
    
    # Дополнительно ждем стабилизации DOM после ввода кода
    try:
        page.wait_for_load_state("domcontentloaded", timeout=20000)  # 20 секунд
        log_info("[OK] DOM content loaded after verification")
    except Exception as e:
        log_warning(f"[WARN] DOM load timeout after verification: {str(e)}")
    
    # [OK] Еще одна естественная пауза для полной обработки
    final_processing_wait = human_behavior.get_advanced_human_delay(5, 3, 'resting')
    time.sleep(final_processing_wait)
    
    log_info("[OK] Verification code processing completed")
    
    # Check if login was successful
    from .selectors_config import InstagramSelectors
    selectors = InstagramSelectors()
    
    for indicator in selectors.LOGGED_IN_INDICATORS:
        try:
            element = page.query_selector(indicator)
            if element and element.is_visible():
                # Дополнительная проверка содержимого элемента
                element_text = element.text_content() or ""
                log_info(f"[OK] Found logged-in indicator: {indicator}")
                log_info(f"[OK] Element text: '{element_text.strip()}'")
                
                # Исключаем элементы, которые содержат текст о создании аккаунта
                exclude_keywords = ['новый аккаунт', 'create account', 'регистр', 'sign up']
                if any(keyword in element_text.lower() for keyword in exclude_keywords):
                    log_warning(f"[WARN] Skipping element with registration text: '{element_text.strip()}'")
                    continue
                
                log_info(f"[OK] 2FA verification successful! Found valid indicator: {indicator}")
                
                # [OK] Симулируем естественное поведение после успешного входа
                log_info("[PARTY] Login successful! Simulating post-login behavior...")
                human_behavior.simulate_page_scanning()  # Осматриваемся на главной странице
                
                # Handle save login info dialog
                from .bulk_tasks_playwright import handle_save_login_info_dialog
                handle_save_login_info_dialog(page)
                
                # Clear human verification badge if previously set
                clear_human_verification_badge(account_details['username'])
                
                return True
        except Exception as e:
            log_warning(f"Error checking indicator {indicator}: {str(e)}")
            continue
    
    log_error("[FAIL] 2FA verification failed - no valid login indicators found")
    return False


def _check_for_login_errors(page):
    """Check for login errors and handle them"""
    # Check for phone verification requirement
    phone_verification_selectors = [
        'div:has-text("Подтвердите номер телефона")',
        'div:has-text("Confirm your phone number")',
        'input[placeholder*="номер телефона"]',
        'input[placeholder*="phone number"]',
    ]
    
    phone_verification_found = False
    for selector in phone_verification_selectors:
        element = page.query_selector(selector)
        if element and element.is_visible():
            phone_verification_found = True
            log_warning(f"[PHONE] Phone verification required! Found element: {selector}")
            break
    
    if phone_verification_found:
        log_error("[FAIL] Instagram requires phone verification for this account")
        raise Exception("PHONE_VERIFICATION_REQUIRED")
    
    # Check for error messages
    error_element = page.query_selector('div[role="alert"]') or page.query_selector('.error-message')
    if error_element:
        error_text = error_element.text_content()
        log_error(f"Login error: {error_text}")
    
    return False


def handle_post_login_checks(page, account_details):
    """Handle post-login checks and dialogs"""
    try:
        # Wait for page to stabilize
        PageUtils.wait_for_page_load(page, timeout=10000)
        
        # Check for phone verification requirement
        phone_verification_selectors = [
            'span:has-text("Введите свой номер мобильного телефона")',
            'span:has-text("Enter your mobile phone number")',
            'span[aria-label*="Введите свой номер мобильного телефона"]',
            'span[aria-label*="Enter your mobile phone number"]',
            'input[placeholder*="номер телефона"]',
            'input[placeholder*="phone number"]',
        ]
        
        for selector in phone_verification_selectors:
            element = page.query_selector(selector)
            if element and element.is_visible():
                log_error("[LOGIN] [FAIL] Phone verification required")
                raise Exception("PHONE_VERIFICATION_REQUIRED")
        
        # Check for suspicious activity warnings
        suspicious_activity_selectors = [
            'div:has-text("Подозрительная активность")',
            'div:has-text("Suspicious activity")',
            'div:has-text("Необычная активность")',
            'div:has-text("Unusual activity")',
        ]
        
        for selector in suspicious_activity_selectors:
            element = page.query_selector(selector)
            if element and element.is_visible():
                log_warning("[LOGIN] [WARN] Suspicious activity warning detected")
                return ErrorHandler.handle_login_error(page, "suspicious_activity")
        
        # Check for CAPTCHA
        captcha_selectors = [
            'iframe[src*="recaptcha"]',
            'div[class*="captcha"]',
            'img[alt*="captcha"]',
        ]
        
        for selector in captcha_selectors:
            element = page.query_selector(selector)
            if element and element.is_visible():
                log_warning("[LOGIN] [WARN] CAPTCHA detected")
                return ErrorHandler.handle_login_error(page, "captcha")
        
        # Check for save login info dialog
        save_login_selectors = [
            'button:has-text("Сохранить данные")',
            'button:has-text("Save Info")',
            'button:has-text("Not Now")',
            'button:has-text("Не сейчас")',
        ]
        
        for selector in save_login_selectors:
            element = page.query_selector(selector)
            if element and element.is_visible():
                log_info("[LOGIN] 💾 Save login info dialog detected")
                try:
                    # Click "Not Now" or "Не сейчас"
                    if "Not Now" in selector or "Не сейчас" in selector:
                        element.click()
                        log_info("[LOGIN] [OK] Dismissed save login info dialog")
                        break
                except:
                    continue
        
        # Check for notification permission dialog
        notification_selectors = [
            'button:has-text("Не сейчас")',
            'button:has-text("Not Now")',
            'button:has-text("Разрешить")',
            'button:has-text("Allow")',
        ]
        
        for selector in notification_selectors:
            element = page.query_selector(selector)
            if element and element.is_visible():
                log_info("[LOGIN] [BELL] Notification permission dialog detected")
                try:
                    # Click "Not Now" or "Не сейчас"
                    if "Not Now" in selector or "Не сейчас" in selector:
                        element.click()
                        log_info("[LOGIN] [OK] Dismissed notification dialog")
                        break
                except:
                    continue
        
        # Final check - verify we're on Instagram main page
        main_page_indicators = [
            'svg[aria-label*="Главная"]',
            'svg[aria-label*="Home"]',
            'svg[aria-label*="Создать"]',
            'svg[aria-label*="Create"]',
            '[aria-label*="Instagram"]',
        ]
        
        main_page_found = False
        for selector in main_page_indicators:
            element = page.query_selector(selector)
            if element and element.is_visible():
                main_page_found = True
                break
        
        if main_page_found:
            log_info("[LOGIN] [OK] Successfully reached Instagram main page")
            return True
        else:
            log_warning("[LOGIN] [WARN] May not have reached main page properly")
            return True  # Continue anyway
            
    except Exception as e:
        if "PHONE_VERIFICATION_REQUIRED" in str(e):
            raise e  # Re-raise phone verification requirement
        else:
            log_warning(f"[LOGIN] [WARN] Post-login check failed: {str(e)}")
            return True  # Continue anyway


def detect_login_errors(page):
    """Detect various login errors and return appropriate error type"""
    try:
        # Check for rate limiting
        rate_limit_selectors = [
            'div:has-text("Слишком много попыток")',
            'div:has-text("Too many attempts")',
            'div:has-text("Попробуйте позже")',
            'div:has-text("Try again later")',
        ]
        
        for selector in rate_limit_selectors:
            element = page.query_selector(selector)
            if element and element.is_visible():
                return "rate_limit"
        
        # Check for incorrect credentials
        incorrect_creds_selectors = [
            'div:has-text("Неверный пароль")',
            'div:has-text("Incorrect password")',
            'div:has-text("Неверное имя пользователя")',
            'div:has-text("Incorrect username")',
            'div[role="alert"]',
        ]
        
        for selector in incorrect_creds_selectors:
            element = page.query_selector(selector)
            if element and element.is_visible():
                error_text = element.text_content().lower()
                if any(word in error_text for word in ['password', 'пароль', 'username', 'пользователь']):
                    return "incorrect_credentials"
        
        # Check for account restrictions
        restriction_selectors = [
            'div:has-text("Аккаунт заблокирован")',
            'div:has-text("Account disabled")',
            'div:has-text("Временно заблокирован")',
            'div:has-text("Temporarily blocked")',
        ]
        
        for selector in restriction_selectors:
            element = page.query_selector(selector)
            if element and element.is_visible():
                return "account_restricted"
        
        return "unknown"
        
    except Exception as e:
        log_warning(f"[LOGIN] Error detecting login errors: {str(e)}")
        return "unknown" 