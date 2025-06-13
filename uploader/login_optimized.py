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


def perform_instagram_login_optimized(page, account_details):
    """Optimized Instagram login with enhanced logged-in detection"""
    try:
        from .selectors_config import InstagramSelectors
        
        selectors = InstagramSelectors()
        username = account_details['username']
        password = account_details['password']
        tfa_secret = account_details.get('tfa_secret')
        
        log_info(f"Starting login process for: {username}")
        
        # Enhanced check if already logged in
        if _check_if_already_logged_in(page, selectors):
            log_info(f"✅ Already logged in! Skipping login process for user: {username}")
            return True
        
        # Perform login steps
        if not _fill_login_credentials(page, username, password):
            return False
        
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
    log_info("🔍 Checking if already logged in...")
    
    # Wait a moment for page to fully load
    time.sleep(random.uniform(2, 4))
    
    # Get current URL for context
    current_url = page.url
    log_info(f"🔍 Current URL: {current_url}")
    
    # First check if we see login form elements
    login_form_present = False
    found_login_elements = []
    
    for indicator in selectors.LOGIN_FORM_INDICATORS:
        element = page.query_selector(indicator)
        if element and element.is_visible():
            login_form_present = True
            found_login_elements.append(indicator)
            log_info(f"🔍 Found login form element: {indicator}")
    
    if login_form_present:
        log_info(f"🔍 Login form detected with elements: {found_login_elements[:3]}")
        return False
    
    # No login form found, check for logged-in indicators
    logged_in_found = False
    found_indicators = []
    
    log_info("🔍 No login form found, checking for logged-in indicators...")
    
    for i, indicator in enumerate(selectors.LOGGED_IN_INDICATORS):
        try:
            element = page.query_selector(indicator)
            if element and element.is_visible():
                logged_in_found = True
                found_indicators.append(indicator)
                log_info(f"✅ Found logged-in indicator {i+1}: {indicator}")
                
                # Get element text for additional context
                try:
                    element_text = element.text_content() or ""
                    if element_text.strip():
                        log_info(f"✅ Element text: '{element_text.strip()}'")
                except:
                    pass
                
                # If we found a strong indicator, we can be confident
                if any(strong_keyword in indicator.lower() for strong_keyword in [
                    'главная', 'home', 'создать', 'create', 'профиль', 'profile'
                ]):
                    log_info(f"✅ Strong logged-in indicator found: {indicator}")
                    break
                    
        except Exception as e:
            log_warning(f"🔍 Error checking indicator {indicator}: {str(e)}")
            continue
    
    if logged_in_found:
        log_info(f"✅ Already logged in! Found {len(found_indicators)} indicators: {found_indicators[:5]}")
        
        # Additional verification - check page title
        try:
            page_title = page.title()
            log_info(f"✅ Page title: '{page_title}'")
            
            # Instagram main page usually has "Instagram" in title
            if "instagram" in page_title.lower():
                log_info("✅ Page title confirms Instagram main page")
            
        except Exception as e:
            log_warning(f"🔍 Could not get page title: {str(e)}")
        
        # Simulate human behavior - look around a bit
        from .bulk_tasks_playwright import simulate_human_mouse_movement, handle_save_login_info_dialog
        simulate_human_mouse_movement(page)
        time.sleep(random.uniform(1, 3))
        
        # Even if already logged in, check for save login dialog
        handle_save_login_info_dialog(page)
        
        return True
    else:
        log_info("🔍 No logged-in indicators found")
        
        # Additional debugging - check what's actually on the page
        try:
            # Get page text for analysis
            page_text = page.inner_text('body') or ""
            page_text_sample = page_text[:200] if page_text else "No text found"
            log_info(f"🔍 Page text sample: '{page_text_sample}...'")
            
            # Check for common Instagram keywords
            instagram_keywords = ['instagram', 'инстаграм', 'войти', 'log in', 'sign up', 'регистрация']
            found_keywords = [keyword for keyword in instagram_keywords if keyword in page_text.lower()]
            if found_keywords:
                log_info(f"🔍 Found Instagram keywords: {found_keywords}")
            
        except Exception as e:
            log_warning(f"🔍 Could not analyze page text: {str(e)}")
        
        # Take a screenshot for debugging
        try:
            screenshot_path = f"login_check_debug_{int(time.time())}.png"
            page.screenshot(path=screenshot_path)
            log_info(f"🔍 Debug screenshot saved: {screenshot_path}")
        except Exception as e:
            log_warning(f"🔍 Could not take debug screenshot: {str(e)}")
    
    return False


def _fill_login_credentials(page, username, password):
    """Fill login credentials with human-like behavior"""
    log_info("Not logged in, proceeding with login process...")
    
    # Wait for and find username input
    try:
        username_input = page.wait_for_selector('input[name="username"]', timeout=10000)
        if not username_input:
            log_error("Username input not found")
            return False
    except:
        log_error("Username input not found")
        return False
    
    # Human-like typing for username
    log_info("Entering username")
    username_input.click()
    time.sleep(random.uniform(0.5, 1.0))
    
    # Clear any existing content and type username character by character
    username_input.fill('')
    time.sleep(random.uniform(0.3, 0.7))
    
    for char in username:
        username_input.type(char)
        time.sleep(random.uniform(0.05, 0.15))
    
    # Small delay before password
    time.sleep(random.uniform(0.8, 1.5))
    
    # Find password input
    password_input = page.query_selector('input[name="password"]')
    if not password_input:
        log_error("Password input not found")
        return False
    
    # Human-like typing for password
    log_info("Entering password")
    password_input.click()
    time.sleep(random.uniform(0.3, 0.7))
    
    # Clear any existing content and type password character by character
    password_input.fill('')
    time.sleep(random.uniform(0.3, 0.7))
    
    for char in password:
        password_input.type(char)
        time.sleep(random.uniform(0.05, 0.12))
    
    return True


def _submit_login_form(page):
    """Submit the login form"""
    # Human delay before clicking login
    time.sleep(random.uniform(1.0, 2.0))
    
    # Click login button
    log_info("Clicking login button")
    login_button = page.query_selector('button[type="submit"]') or page.query_selector('button:has-text("Log in")')
    if login_button:
        login_button.click()
    else:
        # Fallback: press Enter
        password_input = page.query_selector('input[name="password"]')
        if password_input:
            password_input.press("Enter")
    
    # Wait for navigation or 2FA
    time.sleep(random.uniform(3, 5))
    return True


def _check_for_human_verification_dialog(page):
    """Check for human verification dialog that requires manual verification"""
    try:
        log_info("🤖 Checking for human verification dialog...")
        
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
            log_warning("🤖 Human verification dialog detected!")
            log_warning("🤖 Instagram requires manual human verification for this account")
            
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
                        log_warning(f"🤖 Found human verification element: {selector}")
                        log_warning(f"🤖 Element text: '{element_text.strip()}'")
                        break
                        
                except Exception as e:
                    log_warning(f"🤖 Error checking selector {selector}: {str(e)}")
                    continue
            
            if verification_dialog_found:
                log_error("🤖 ❌ Human verification dialog confirmed!")
                log_error("🤖 ❌ This account requires manual human verification")
                log_error("🤖 ❌ The account cannot be used for automation until verified")
                
                # Take a screenshot for debugging
                try:
                    screenshot_path = f"human_verification_dialog_{int(time.time())}.png"
                    page.screenshot(path=screenshot_path)
                    log_warning(f"🤖 Screenshot saved: {screenshot_path}")
                except Exception as e:
                    log_warning(f"🤖 Could not take screenshot: {str(e)}")
                
                return True
            else:
                log_info("🤖 Human verification keywords found in text but no dialog elements detected")
                log_info("🤖 This might be a different type of verification page")
                return True  # Still treat as human verification required
        else:
            log_info("🤖 No human verification dialog detected")
            return False
            
    except Exception as e:
        log_error(f"🤖 Error checking for human verification dialog: {str(e)}")
        return False


def _handle_login_completion(page, account_details, selectors):
    """Handle login completion including 2FA and human verification checks"""
    log_info("Checking for 2FA requirement and other post-login dialogs...")
    
    # Wait a bit more for the page to fully load after login attempt
    time.sleep(random.uniform(5, 8))
    
    # First check for human verification dialog
    if _check_for_human_verification_dialog(page):
        log_error("❌ Human verification required for this account")
        raise Exception("HUMAN_VERIFICATION_REQUIRED")
    
    # Try multiple times to find verification input as page might still be loading
    tfa_input = None
    max_attempts = 5
    
    for attempt in range(max_attempts):
        log_info(f"Verification check attempt {attempt + 1}/{max_attempts}")
        
        # Use the comprehensive function to find verification code input
        from .bulk_tasks_playwright import find_verification_code_input
        tfa_input = find_verification_code_input(page)
        
        if tfa_input:
            log_info(f"Found verification input on attempt {attempt + 1}")
            break
        else:
            # Check if we're already logged in (successful login without 2FA)
            for indicator in selectors.LOGGED_IN_INDICATORS:
                element = page.query_selector(indicator)
                if element and element.is_visible():
                    log_info(f"✅ Login successful! Found indicator: {indicator}")
                    
                    # Handle save login info dialog after successful login
                    from .bulk_tasks_playwright import handle_save_login_info_dialog
                    handle_save_login_info_dialog(page)
                    
                    return True
            
            if attempt < max_attempts - 1:  # Don't wait on the last attempt
                log_info("No verification input found, waiting 5 seconds before retry...")
                time.sleep(5)
    
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
    """Handle email verification"""
    from .bulk_tasks_playwright import get_email_verification_code
    
    email_login = account_details.get('email_login')
    email_password = account_details.get('email_password')
    
    if not email_login or not email_password:
        log_error("📧 Email credentials not provided for verification")
        return False
    
    verification_code = get_email_verification_code(email_login, email_password)
    
    if verification_code:
        log_info(f"📧 Got email verification code: {verification_code}")
        return _enter_verification_code(page, tfa_input, verification_code)
    else:
        log_error("📧 Failed to get email verification code")
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
    
    log_info("Entering verification code...")
    tfa_input.click()
    time.sleep(random.uniform(0.5, 1.0))
    
    # Clear and enter code character by character
    tfa_input.fill('')
    time.sleep(random.uniform(0.3, 0.7))
    
    for char in verification_code:
        tfa_input.type(char)
        time.sleep(random.uniform(0.1, 0.3))
    
    # Submit the code
    time.sleep(random.uniform(1.0, 2.0))
    
    # Try to find and click submit button
    from .bulk_tasks_playwright import find_submit_button
    submit_button = find_submit_button(page)
    
    if submit_button:
        submit_button.click()
    else:
        tfa_input.press("Enter")
    
    # Wait for verification
    time.sleep(random.uniform(5, 8))
    
    # Check if login was successful
    from .selectors_config import InstagramSelectors
    selectors = InstagramSelectors()
    
    for indicator in selectors.LOGGED_IN_INDICATORS:
        element = page.query_selector(indicator)
        if element and element.is_visible():
            log_info(f"✅ 2FA verification successful! Found indicator: {indicator}")
            
            # Handle save login info dialog
            from .bulk_tasks_playwright import handle_save_login_info_dialog
            handle_save_login_info_dialog(page)
            
            return True
    
    log_error("❌ 2FA verification failed")
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
            log_warning(f"📱 Phone verification required! Found element: {selector}")
            break
    
    if phone_verification_found:
        log_error("❌ Instagram requires phone verification for this account")
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
                log_error("[LOGIN] ❌ Phone verification required")
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
                log_warning("[LOGIN] ⚠️ Suspicious activity warning detected")
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
                log_warning("[LOGIN] ⚠️ CAPTCHA detected")
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
                        log_info("[LOGIN] ✅ Dismissed save login info dialog")
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
                log_info("[LOGIN] 🔔 Notification permission dialog detected")
                try:
                    # Click "Not Now" or "Не сейчас"
                    if "Not Now" in selector or "Не сейчас" in selector:
                        element.click()
                        log_info("[LOGIN] ✅ Dismissed notification dialog")
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
            log_info("[LOGIN] ✅ Successfully reached Instagram main page")
            return True
        else:
            log_warning("[LOGIN] ⚠️ May not have reached main page properly")
            # Take screenshot for debugging
            PageUtils.take_screenshot(page, "login_final_state")
            return True  # Continue anyway
            
    except Exception as e:
        if "PHONE_VERIFICATION_REQUIRED" in str(e):
            raise e  # Re-raise phone verification requirement
        else:
            log_warning(f"[LOGIN] ⚠️ Post-login check failed: {str(e)}")
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