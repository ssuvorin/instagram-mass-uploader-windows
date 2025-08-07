import json
import os
from time import sleep
import time
import logging
import re

from playwright.sync_api import expect

from bot.src import logger
from bot.src.instagram_uploader import config
from bot.src.instagram_uploader.browser_dolphin import get_browser, get_page, close_browser
from bot.src.instagram_uploader.email_client import Email
from .tfa_api import TFAAPI
from bot.src.instagram_uploader.util import random_delay, realistic_type, human_action

logger = logging.getLogger(__name__)

def verify_ip_address(page):
    """
    Verify the current IP address by visiting an IP checking service
    """
    try:
        logger.info("[SEARCH] Проверка текущего IP-адреса...")
        page.goto("https://api.ipify.org")
        ip_text = page.content()
        
        # For ipify.org, the IP is the entire body content
        body_text = page.inner_text("body")
        if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", body_text):
            ip = body_text
            logger.info(f"[OK] Текущий IP-адрес: {ip}")
            return ip
            
        # Fallback to regex extraction from full content
        ip_match = re.search(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip_text)
        if ip_match:
            ip = ip_match.group(0)
            logger.info(f"[OK] Текущий IP-адрес: {ip}")
            return ip
        else:
            # Try alternative IP checking service
            logger.info("[RETRY] Пробуем альтернативный сервис проверки IP...")
            page.goto("https://checkip.amazonaws.com/")
            body_text = page.inner_text("body").strip()
            if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", body_text):
                ip = body_text
                logger.info(f"[OK] Текущий IP-адрес: {ip}")
                return ip
                
            logger.error("[FAIL] Не удалось определить IP-адрес")
            return None
    except Exception as e:
        logger.error(f"[FAIL] Ошибка при проверке IP-адреса: {str(e)}")
        return None

class Auth:

    def __init__(self, page, account_data):
        self.page = page
        self.username = account_data['username']
        self.password = account_data['password']
        self.tfa_secret = account_data.get("tfa_secret")  # Для 2FA
        self.email_username = account_data.get("email_username")  # Для верификации через почту
        self.email_password = account_data.get("email_password")  # Для верификации через почту
        self.tfa_api = TFAAPI() if self.tfa_secret else None
        
        # Инициализация прокси
        self.proxy = account_data.get("proxy", None)
        if self.proxy:
            logger.info(f"🌐 Инициализирован прокси: {self.proxy.get('host')}:{self.proxy.get('port')}")
        else:
            logger.info("🌐 Прокси не используется")

    def login_with_username_and_password(self, browser_data=None, page=None, username=None, password=None,
                                         email_username=None, email_password=None):
        """
        Login to instagram via username and password using Playwright
        """
        assert (self.username and self.password)
        if not username and not password:
            username = self.username
            password = self.password
            
        # Use email credentials from the method parameters or from the class if not provided
        if not email_username:
            email_username = self.email_username
        if not email_password:
            email_password = self.email_password
            
        try:
            # Verify proxy is configured
            if not self.proxy:
                logger.error("[FAIL] Прокси не настроен. Бот не может работать без прокси.")
                return None
                
            if not browser_data:
                logger.info("[RETRY] Инициализация браузера...")
                self.browser_data = get_browser(headless=False, proxy=self.proxy)
                logger.info("[SEARCH] Браузер запущен в видимом режиме")
            else:
                self.browser_data = browser_data
                logger.info("[RETRY] Используем существующий браузер")
            
            if not page:
                logger.info("[RETRY] Создание новой страницы...")
                self.page = get_page(self.browser_data)
                logger.info("[OK] Страница создана")
                
                # Verify IP address if proxy is used
                if self.proxy:
                    logger.info("🌐 Проверка работы прокси...")
                    ip = verify_ip_address(self.page)
                    if ip:
                        logger.info(f"🌐 Используется IP-адрес: {ip}")
                    else:
                        logger.error("[FAIL] Не удалось проверить IP-адрес или прокси не работает")
            else:
                self.page = page
                logger.info("[RETRY] Используем существующую страницу")

            # Navigate to Instagram
            logger.info(f"🌐 Переход на страницу Instagram: {config['paths']['main']}")
            self.page.goto(config['paths']['main'])
            logger.info("[WAIT] Ожидание загрузки страницы...")
            random_delay("major")  # Используем настраиваемую задержку вместо фиксированных 8 секунд

            logger.info(f'👤 Авторизация аккаунта {username} через логин и пароль')

            # Handle cookies dialog if present
            logger.info("[SEARCH] Проверка наличия диалога о cookies...")
            self._click_cookies()
            logger.info("[WAIT] Дополнительное ожидание после обработки cookies...")
            random_delay()

            # Check if we need to click login button to get to login page
            try:
                logger.info("[SEARCH] Поиск кнопки логина...")
                login_button = self.page.locator("xpath=" + config['selectors']['login']['log_in_btn'])
                if login_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                    logger.info("👆 Нажатие кнопки логина")
                    login_button.click()
                    logger.info("[WAIT] Ожидание после нажатия кнопки логина...")
                    random_delay()
                else:
                    # Попробуем найти альтернативную кнопку логина
                    logger.info("[SEARCH] Поиск альтернативной кнопки логина...")
                    alt_login_button = self.page.locator("xpath=" + config['selectors']['login']['alternate_log_in_btn'])
                    if alt_login_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                        logger.info("👆 Нажатие альтернативной кнопки логина")
                        alt_login_button.click()
                        logger.info("[WAIT] Ожидание после нажатия альтернативной кнопки логина...")
                        random_delay()
            except Exception as e:
                logger.info(f"[WARN] Кнопка логина не найдена, возможно уже на странице логина: {str(e)}")
                pass

            # Fill in username with realistic typing
            logger.info("[SEARCH] Поиск поля для ввода имени пользователя...")
            username_field = self.page.locator("xpath=" + config['selectors']['login']['username_field'])
            logger.info("[WAIT] Ожидание появления поля для имени пользователя...")
            username_field.wait_for(state="visible", timeout=config['explicit_wait'] * 1000)
            logger.info("[CLEAN] Очистка поля имени пользователя...")
            username_field.clear()
            logger.info(f"⌨️ Ввод имени пользователя: {username}")
            realistic_type(self.page, "xpath=" + config['selectors']['login']['username_field'], username)

            # Fill in password with realistic typing
            logger.info("[SEARCH] Поиск поля для ввода пароля...")
            password_field = self.page.locator("xpath=" + config['selectors']['login']['password_field'])
            logger.info("[WAIT] Ожидание появления поля для пароля...")
            password_field.wait_for(state="visible", timeout=config['explicit_wait'] * 1000)
            logger.info("[CLEAN] Очистка поля пароля...")
            password_field.clear()
            logger.info("⌨️ Ввод пароля")
            realistic_type(self.page, "xpath=" + config['selectors']['login']['password_field'], password)

            # Проверим, активна ли кнопка входа
            logger.info("[SEARCH] Проверка активности кнопки входа")
            login_button = self.page.locator("xpath=" + config['selectors']['login']['login_button'])
            logger.info("[WAIT] Ожидание появления кнопки входа...")
            login_button.wait_for(state="visible", timeout=config['explicit_wait'] * 1000)
            if not login_button.is_enabled():
                logger.info("[WARN] Кнопка входа не активна. Ожидание...")
                random_delay("major")

            # Click login button
            logger.info("👆 Нажатие кнопки входа")
            login_button = self.page.locator("xpath=" + config['selectors']['login']['login_button'])
            if login_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                login_button.click()
                logger.info("[WAIT] Ожидание после нажатия кнопки входа...")
                random_delay("major")
            else:
                # Попробуем найти альтернативную кнопку входа
                logger.info("[SEARCH] Поиск альтернативной кнопки входа...")
                alt_login_button = self.page.locator("xpath=" + config['selectors']['login']['alternate_login_button'])
                if alt_login_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                    logger.info("👆 Нажатие альтернативной кнопки входа")
                    alt_login_button.click()
                    logger.info("[WAIT] Ожидание после нажатия альтернативной кнопки входа...")
                    random_delay("major")
                else:
                    logger.error("[FAIL] Не удалось найти кнопку входа")
                    close_browser(self.browser_data)
                    return None

            logger.info("[WAIT] Длительное ожидание после входа (обработка авторизации)...")
            random_delay((15.0, 25.0))  # Более длительная задержка для обработки авторизации
            
            # Check for verification code requirement
            try:
                logger.info("[SEARCH] Проверка, требуется ли код верификации...")
                code_field = self.page.locator("xpath=" + config['selectors']['login']['email_code_field'])
                if code_field.is_visible(timeout=config['implicitly_wait'] * 1000):
                    logger.info('✉️ Требуется код подтверждения. Проверка почты...')
                    
                    if email_username and email_password:
                        logger.info(f"✉️ Используем учетные данные почты: {email_username}")
                        email = Email(login=email_username, password=email_password)
                        code = email.get_verification_code()
                        
                        if code:
                            logger.info(f"⌨️ Ввод кода подтверждения: {code}")
                            code_field.click()
                            random_delay()
                            realistic_type(self.page, "xpath=" + config['selectors']['login']['email_code_field'], code)
                            random_delay()

                            logger.info("👆 Нажатие кнопки продолжить")
                            continue_button = self.page.locator("xpath=" + config['selectors']['login']['continue_button'])
                            continue_button.click()
                            logger.info("[WAIT] Ожидание после ввода кода подтверждения...")
                            random_delay()
                        else:
                            logger.error("[FAIL] Не удалось получить код подтверждения с почты")
                else:
                    logger.error("[FAIL] Требуется код верификации с почты, но учетные данные почты не указаны")
            except Exception as e:
                logger.info(f"[WARN] Проверка кода верификации пропущена: {str(e)}")
                pass

            # Check for account suspension
            logger.info("[SEARCH] Проверка на блокировку аккаунта...")
            current_url = self.page.url
            if 'suspended' in current_url:
                logger.error(f'[FAIL] Аккаунт {username} заблокирован. Прерывание.')
                close_browser(self.browser_data)
                return None

            # Handle save login info dialogs
            self._handle_save_login_info()

            # Check for TFA (Two-Factor Authentication)
            logger.info("[SEARCH] Проверка, требуется ли двухфакторная аутентификация...")
            try:
                if any(marker in self.page.url for marker in ['challenge', 'twofactor', 'checkpoint']):
                    logger.info("🔐 Двухфакторная аутентификация требуется")
                    
                    # Проверяем наличие кода TFA
                    if self.tfa_secret:
                        logger.info("🔑 Генерация кода двухфакторной аутентификации...")
                        tfa_code = self.tfa_api.get_totp_code(self.tfa_secret)
                        
                        if tfa_code:
                            logger.info(f"🔢 Код двухфакторной аутентификации: {tfa_code}")
                            
                            # Ищем поле для ввода кода
                            security_code_field = self.page.get_by_role("textbox", name="Security Code")
                            if security_code_field.is_visible(timeout=config['implicitly_wait'] * 1000):
                                logger.info("⌨️ Ввод кода двухфакторной аутентификации...")
                                realistic_type(self.page, "//input[@name='verificationCode']", tfa_code)
                                
                                # Нажимаем кнопку подтверждения
                                logger.info("👆 Нажатие кнопки подтверждения")
                                confirm_button = self.page.get_by_role("button", name="Confirm")
                                if confirm_button.is_visible():
                                    confirm_button.click()
                                    logger.info("[WAIT] Ожидание после ввода кода двухфакторной аутентификации...")
                                    random_delay("major")
                                else:
                                    # Пробуем альтернативную кнопку
                                    submit_button = self.page.locator("xpath=" + config['selectors']['login']['alternate_submit_button'])
                                    if submit_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                                        submit_button.click()
                                        logger.info("[WAIT] Ожидание после ввода кода двухфакторной аутентификации...")
                                        random_delay("major")
                                    else:
                                        logger.error("[FAIL] Кнопка подтверждения кода не найдена")
                            else:
                                # Пробуем альтернативное поле ввода кода
                                alt_code_field = self.page.locator("xpath=" + config['selectors']['login']['alternate_email_code_field'])
                                if alt_code_field.is_visible(timeout=config['implicitly_wait'] * 1000):
                                    logger.info("⌨️ Ввод кода двухфакторной аутентификации в альтернативное поле...")
                                    realistic_type(self.page, "xpath=" + config['selectors']['login']['alternate_email_code_field'], tfa_code)
                                    
                                    # Нажимаем альтернативную кнопку подтверждения
                                    logger.info("👆 Нажатие альтернативной кнопки подтверждения")
                                    alt_submit_button = self.page.locator("xpath=" + config['selectors']['login']['alternate_submit_button'])
                                    if alt_submit_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                                        alt_submit_button.click()
                                        logger.info("[WAIT] Ожидание после ввода кода двухфакторной аутентификации...")
                                        random_delay("major")
                                    else:
                                        logger.error("[FAIL] Альтернативная кнопка подтверждения кода не найдена")
                                else:
                                    logger.error("[FAIL] Поле для ввода кода двухфакторной аутентификации не найдено")
                        else:
                            logger.error("[FAIL] Не удалось сгенерировать код двухфакторной аутентификации")
                    else:
                        logger.error("[FAIL] Двухфакторная аутентификация требуется, но секретный ключ не указан")
            except Exception as e:
                logger.info(f"[WARN] Проверка двухфакторной аутентификации пропущена: {str(e)}")

            # Final check if login successful
            try:
                # Увеличиваем время ожидания для обнаружения элементов домашней страницы
                random_delay("major")
                
                # Проверяем наличие кнопки нового поста
                new_post_button = self.page.locator("xpath=" + config['selectors']['upload']['new_post_button'])
                if new_post_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                    logger.info("[OK] Успешный вход в Instagram (найдена кнопка нового поста)")
                    
                    # Save cookies for future use
                    logger.info("🍪 Сохранение cookies...")
                    cookies_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    cookies_dir = os.path.join(cookies_dir, "cookies")
                    os.makedirs(cookies_dir, exist_ok=True)
                    cookies_path = os.path.join(cookies_dir, f"{self.username}_cookies.json")
                    cookies = self.page.context.cookies()
                    with open(cookies_path, "w") as f:
                        json.dump(cookies, f)
                    logger.info(f"🍪 Cookies сохранены в: {cookies_path}")
                    
                    return True
                else:
                    logger.info("[SEARCH] Кнопка нового поста не найдена, пробуем другие методы проверки...")
                    
                    # Check if we are on the home page
                    current_url = self.page.url
                    if current_url.startswith("https://www.instagram.com/") and not any(marker in current_url for marker in ['login', 'accounts/login', 'challenge', 'suspended']):
                        logger.info("[OK] Успешный вход в Instagram (URL указывает на домашнюю страницу)")
                        
                        # Save cookies for future use
                        logger.info("🍪 Сохранение cookies...")
                        cookies_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        cookies_dir = os.path.join(cookies_dir, "cookies")
                        os.makedirs(cookies_dir, exist_ok=True)
                        cookies_path = os.path.join(cookies_dir, f"{self.username}_cookies.json")
                        cookies = self.page.context.cookies()
                        with open(cookies_path, "w") as f:
                            json.dump(cookies, f)
                        logger.info(f"🍪 Cookies сохранены в: {cookies_path}")
                        
                        return True
                    else:
                        logger.error(f"[FAIL] Не удалось войти в Instagram. Текущий URL: {current_url}")
                        return False
            except Exception as e:
                logger.error(f"[FAIL] Ошибка при проверке успешности входа: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"[FAIL] Ошибка при входе в Instagram: {str(e)}")
            return False

    def login(self, cookies_list):
        """
        Login to Instagram using saved cookies
        """
        try:
            self.browser_data = get_browser(headless=False, proxy=self.proxy)
            logger.info("[SEARCH] Браузер запущен в видимом режиме")
            
            self.page = get_page(self.browser_data)
            
            # Load minimal Instagram page first
            logger.info(f"🌐 Переход на страницу Instagram для установки cookies")
            self.page.goto("https://www.instagram.com/robots.txt")
            
            # Set cookies
            logger.info(f"🍪 Установка cookies для аккаунта {self.username}")
            self.browser_data["context"].add_cookies(cookies_list)
            
            # Navigate to main Instagram page
            logger.info(f"🌐 Переход на главную страницу Instagram")
            self.page.goto(config['paths']['main'])
            
            # Handle save login info dialogs
            self._handle_save_login_info()
            
            # Check if we need to re-login
            current_url = self.page.url
            if any(marker in current_url for marker in ['login', 'accounts/login']):
                logger.info("[RETRY] Необходима повторная авторизация через логин и пароль")
                return self.login_with_username_and_password()
                
            # Check for post button to verify successful login
            logger.info("[SEARCH] Проверка успешности входа...")
            new_post_button = self.page.locator("xpath=" + config['selectors']['upload']['new_post_button'])
            if new_post_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                logger.info("[OK] Успешный вход в Instagram через cookies")
                return True
            else:
                logger.info("[WARN] Кнопка нового поста не найдена, возможно требуется повторная авторизация")
                return self.login_with_username_and_password()
        except Exception as e:
            logger.error(f"[FAIL] Ошибка при входе через cookies: {str(e)}")
            logger.info("[RETRY] Пробуем войти через логин и пароль")
            return self.login_with_username_and_password()

    def _click_cookies(self):
        """Handle cookie dialogs"""
        try:
            logger.info("[SEARCH] Поиск диалога о cookies...")
            accept_cookies = self.page.locator("xpath=" + config['selectors']['register']['accept_cookies'])
            
            if accept_cookies.is_visible(timeout=config['implicitly_wait'] * 1000):
                logger.info("👆 Нажатие на кнопку принятия cookies")
                accept_cookies.click()
                random_delay()
                return True
            else:
                # Try alternate cookie button
                alternate_cookies = self.page.locator("xpath=" + config['selectors']['register']['alternate_accept_cookies'])
                if alternate_cookies.is_visible(timeout=config['implicitly_wait'] * 1000):
                    logger.info("👆 Нажатие на альтернативную кнопку принятия cookies")
                    alternate_cookies.click()
                    random_delay()
                    return True
                else:
                    logger.info("ℹ️ Диалог о cookies не найден")
                    return False
        except Exception as e:
            logger.info(f"[WARN] Ошибка при обработке диалога о cookies: {str(e)}")
            return False

    def _handle_save_login_info(self):
        """Handle 'Save Login Info' dialogs"""
        try:
            logger.info("[SEARCH] Поиск диалога сохранения информации для входа...")
            save_button = self.page.locator("xpath=" + config['selectors']['login']['save_session_button'])
            
            if save_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                logger.info("👆 Нажатие на кнопку сохранения информации")
                save_button.click()
                random_delay()
                return True
            else:
                # Try alternate save button
                alt_save_button = self.page.locator("xpath=" + config['selectors']['login']['alternate_save_session_button'])
                if alt_save_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                    logger.info("👆 Нажатие на альтернативную кнопку сохранения информации")
                    alt_save_button.click()
                    random_delay()
                    return True
                
                # Try 'Not Now' button
                not_now_button = self.page.locator("xpath=" + config['selectors']['login']['not_now_button'])
                if not_now_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                    logger.info("👆 Нажатие на кнопку 'Not Now'")
                    not_now_button.click()
                    random_delay()
                    return True
                    
                logger.info("ℹ️ Диалог сохранения информации не найден")
                return False
        except Exception as e:
            logger.info(f"[WARN] Ошибка при обработке диалога сохранения: {str(e)}")
            return False