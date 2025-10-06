import json
import os.path
import random
import time

from playwright.sync_api import BrowserContext, Playwright, Page

from tiktok_uploader.bot_integration import logger
from tiktok_uploader.bot_integration.db import DataBase
from tiktok_uploader.bot_integration.dolphin.profile import Profile
from tiktok_uploader.bot_integration.tiktok.browser import get_browser
from tiktok_uploader.bot_integration.tiktok.captcha import solve_captcha
from tiktok_uploader.bot_integration.tiktok.getCode import Email
from tiktok_uploader.bot_integration.tiktok.locators import Pages, Login, Error, CheckAuth


class Auth:

    def __init__(self, login, password, email: Email, profile: Profile, playwright, db: DataBase = None, password_update_callback=None, status_update_callback=None):
        self.login = login
        self.password = password
        self.email = email
        self.profile = profile
        self.playwright = playwright
        self.db = db
        self.password_update_callback = password_update_callback  # Callback для обновления пароля в Django
        self.status_update_callback = status_update_callback  # Callback для обновления статуса аккаунта

    def authenticate(self):
        """
        Auth to TikTok via login and password
        """

        pr_data = self.profile.start()
        if not pr_data:
            logger.error(f'Failed to start profile for {self.login}')
            return None
        
        try:
            port, endpoint = pr_data
        except (TypeError, ValueError) as e:
            logger.error(f'Invalid profile start data for {self.login}: {pr_data}, error: {e}')
            return None

        self.browser = get_browser(playwright=self.playwright, endpoint_url=f'ws://127.0.0.1:{port}{endpoint}')
        page: Page = self.get_page(self.browser)

        # Align Accept-Language with Dolphin profile locale/language
        try:
            al = self.profile.resolve_accept_language()
            try:
                page.context.set_extra_http_headers({"Accept-Language": al})
                logger.debug(f'Set Accept-Language: {al}')
            except Exception as _:
                pass
        except Exception as _:
            pass

        # Ensure cookies are properly applied before checking login
        try:
            self._ensure_tiktok_cookies(page)
        except Exception as _:
            pass

        if self.__is_logged(page):
            logger.info(f'Already logged into {self.login}')
            return page
        try:
            return self._auth(page)
        except Exception as e:
            error_msg = str(e)
            logger.error(f'Failed to log into {self.login}. Reason: {error_msg}')
            
            # Обновляем статус аккаунта через callback
            if self.status_update_callback:
                try:
                    # Определяем статус на основе ошибки
                    status = 'INACTIVE'
                    if 'suspend' in error_msg.lower() or 'ban' in error_msg.lower():
                        status = 'SUSPENDED'
                    elif 'captcha' in error_msg.lower():
                        status = 'CAPTCHA_REQUIRED'
                    elif 'verification' in error_msg.lower() or 'verify' in error_msg.lower():
                        status = 'PHONE_VERIFICATION_REQUIRED'
                    elif 'block' in error_msg.lower():
                        status = 'BLOCKED'
                    
                    self.status_update_callback(self.login, status, error_msg)
                    logger.warning(f'⚠️ Account {self.login} status updated to {status}')
                except Exception as cb_error:
                    logger.error(f'❌ Failed to update account status for {self.login}: {str(cb_error)}')
            
            return 1

    def _forgot_password(self, page):
        logger.info(f'Changing password for {self.login}')
        page.locator(Login.forgot_password_button).click()
        time.sleep(3)
        field = page.locator(Login.email_field)
        field.type(self.email.login, delay=random.randint(100, 300))
        time.sleep(2)
        page.locator(Login.code_button).click(timeout=2000)
        time.sleep(10)

        try:
            err = page.locator(Error.error_description).inner_text()
            if err:
                logger.error(f'Failed to change password for {self.login}. Reason: {err}')
                return 1
        except:
            pass

        code = self.email.get_code()
        if not code:
            logger.error(f'Failed to change password for {self.login}. Reason: got no code')
            self.profile.stop()
            return 1
        code_field = page.locator(Login.code_field)
        code_field.click()
        code_field.type(code, delay=random.randint(100, 300))
        time.sleep(2)
        self.__remake_password()
        new_password = page.locator(Login.new_password)
        new_password.click()
        new_password.type(self.password, delay=random.randint(100, 300))
        time.sleep(2)
        page.mouse.click(10, 10)
        time.sleep(1)
        login_button = page.locator(Login.login_button)
        login_button.click()
        time.sleep(3)
        solve_captcha(page)
        time.sleep(3)
        try:
            err = page.locator(Error.error_description).inner_text()
            if err:
                logger.error(f'Failed to change password for {self.login}. Reason: {err}')
                self.profile.stop()
                return 1
        except:
            pass
        time.sleep(5)
        return page

    def __remake_password(self):
        new_password = list(self.password)
        random.shuffle(new_password)
        new_password = ''.join(new_password)
        if new_password != self.password:
            old_password = self.password
            self.password = str(new_password)
            
            # Обновляем пароль в Django через callback
            if self.password_update_callback:
                try:
                    self.password_update_callback(self.login, new_password)
                    logger.info(f'✅ Password for {self.login} updated in database: {old_password} -> {new_password}')
                except Exception as e:
                    logger.error(f'❌ Failed to update password in database for {self.login}: {str(e)}')
            else:
                logger.info(f'Password for {self.login} changed to {new_password}')
        else:
            self.__remake_password()

    def _auth(self, page):
        page.goto(Pages.main)
        time.sleep(2)
        self.__reload_page(page)
        time.sleep(3)
        page.goto(Pages.login)

        try:
            logger.info('Passing cookies')
            page.locator(Login.cookies_button).click()
        except Exception as _:
            logger.info('No cookies button is found')
        username_field = page.locator(Login.username_field)
        username_field.click()
        username_field.type(self.login, delay=random.randint(100, 300))
        password_field = page.locator(Login.password_field)
        logger.debug(f'Entering login: {self.login}')
        time.sleep(2)
        password_field.click()
        password_field.type(self.password, delay=random.randint(100, 300))
        logger.debug(f'Entering password: {self.password}')
        time.sleep(2)
        page.locator(Login.login_button).click()
        time.sleep(5)
        solve_captcha(page)
        time.sleep(5)
        logger.info('Checking if email code needed')
        try:
            field = page.locator(Login.code_field)
            if field.count() > 0:
                if not self.email.login or  not self.email.password:
                    logger.debug('No email data provided, unable to get code')
                    return 1
                time.sleep(15)
                code = self.email.get_code()
                if code:
                    field.type(code, delay=100)
                    page.locator(Login.email_next_button).click()
                else:
                    logger.error('Got no code')
                    self.profile.stop()
                    return 1
        except:
            pass

        time.sleep(5)
        solve_captcha(page)
        time.sleep(5)

        logger.info(f'Logging into {self.login}')

        try:
            err = page.locator(Error.error_description).inner_text()
            if err:
                logger.error(f'Failed to log into {self.login}. Reason: {err}')
                
                # Обновляем статус на основе ошибки
                if self.status_update_callback:
                    try:
                        status = 'INACTIVE'
                        if 'suspend' in err.lower() or 'ban' in err.lower():
                            status = 'SUSPENDED'
                        elif 'incorrect' in err.lower() or 'wrong' in err.lower():
                            status = 'BLOCKED'
                        elif 'verification' in err.lower() or 'verify' in err.lower():
                            status = 'PHONE_VERIFICATION_REQUIRED'
                        
                        self.status_update_callback(self.login, status, err)
                        logger.warning(f'⚠️ Account {self.login} status updated to {status}')
                    except Exception as cb_error:
                        logger.error(f'❌ Failed to update account status: {str(cb_error)}')
                
                if ('Maximum number of attempts reached. Try again later.' in err) or (
                        'match our records. Try again.' in err):
                    return self._forgot_password(page)
            self.profile.stop()
            return 1
        except:
            pass

        try:
            page.wait_for_url("https://www.tiktok.com/foryou*",
                              timeout=10000)  # Ожидание редиректа на /foryou (с wildcard для вариаций)
            logger.info(f'Successfully logged into {self.login}')

            return page
        except TimeoutError:
            logger.error(f"Failed to login into {self.login}: No redirect")
            return 1

    @staticmethod
    def get_page(browser: BrowserContext):
        page: Page = browser.contexts[0].pages[0]
        page.set_default_timeout(60000)
        return page

    def __is_logged(self, page) -> bool:
        # Check cookies from both apex and www domains
        ctx = self.browser.contexts[0]
        try:
            cookies_main = ctx.cookies('https://tiktok.com')
        except Exception:
            cookies_main = []
        try:
            cookies_www = ctx.cookies('https://www.tiktok.com')
        except Exception:
            cookies_www = []
        cookies = list({(c['name'], c.get('domain', '')): c for c in (cookies_main + cookies_www)}.values())
        if self.__check_cookies(cookies):
            logger.debug('Cookies look valid, proceeding to page check')
        else:
            logger.debug('Cookies incomplete, but checking page anyway')

        try:
            self.__reload_page(page)
            page.goto(Pages.main, wait_until="load", timeout=60000)
            time.sleep(random.uniform(2, 5))

            self.__pass_got_it(page)

            # Проверяем messages_button с ожиданием до 15 сек
            try:
                page.wait_for_selector(CheckAuth.messages_button, state="visible", timeout=15000)
                logger.debug('Messages button found: logged in')
                return True
            except:
                logger.debug('Messages button not found within 15s')

            # Проверяем activity_button с ожиданием до 15 сек
            try:
                page.wait_for_selector(CheckAuth.activity_button, state="visible", timeout=15000)
                logger.debug('Activity button found: logged in')
                return True
            except:
                logger.debug('Activity button not found within 15s, checking next')

            logger.debug('Page elements indicate not logged in')
            return False

        except Exception as e:
            logger.info(f'Page check failed: {e}. Falling back to auth.')
            return False

    def _ensure_tiktok_cookies(self, page: Page):
        """
        If key cookies not present, try to inject from DB into Playwright with correct domain/url
        and refresh www.tiktok.com once to let them take effect.
        """
        ctx = self.browser.contexts[0]
        # Merge current cookies from both domains
        try:
            current = ctx.cookies('https://tiktok.com') + ctx.cookies('https://www.tiktok.com')
        except Exception:
            current = []
        if self.__check_cookies(current):
            return
        if not self.db:
            return
        try:
            row = self.db.select_one('accounts', where="username = ?", params=(self.login,))
            raw = (row or {}).get('cookies')
            if not raw:
                return
            try:
                source_cookies = json.loads(raw)
            except Exception:
                return
            def to_playwright_cookie(c):
                name = c.get('name') or c.get('key')
                value = c.get('value', '')
                domain = c.get('domain') or '.tiktok.com'
                if not domain.startswith('.') and domain != 'tiktok.com':
                    # normalize to parent domain
                    domain = '.tiktok.com'
                path = c.get('path') or '/'
                secure = True if c.get('secure') is None else bool(c.get('secure'))
                http_only = bool(c.get('httpOnly', False))
                same_site = c.get('sameSite') or 'None'
                expires = c.get('expires')
                cookie = {
                    'name': name,
                    'value': value,
                    'domain': domain,
                    'path': path,
                    'secure': secure,
                    'httpOnly': http_only,
                    'sameSite': same_site,
                }
                if isinstance(expires, (int, float)):
                    cookie['expires'] = expires
                # Playwright also allows url; provide to ensure scoping
                cookie['url'] = 'https://www.tiktok.com'
                return cookie
            pw_cookies = [to_playwright_cookie(c) for c in (source_cookies or []) if (c.get('name') or c.get('key'))]
            if not pw_cookies:
                return
            ctx.add_cookies(pw_cookies)
            # Navigate to www to bind cookies, small wait
            page.goto('https://www.tiktok.com', wait_until='domcontentloaded', timeout=60000)
            time.sleep(2)
        except Exception as _:
            pass

    @staticmethod
    def __check_cookies(cookies: list[dict]) -> bool:
        """
        Проверка наличия ключевых куки (расширенная).
        """
        required_cookies = {'sessionid', 'sessionid_ss', 'tt_webid_v2', 'tt_csrf_token'}
        found = {cookie['name'] for cookie in cookies if cookie['name'] in required_cookies}

        # Если найдено хотя бы 2 ключевые куки — считаем валидными
        if len(found) >= 2:
            logger.debug(f'Found key cookies: {found}')
            return True
        logger.debug('Insufficient key cookies found')
        return False


    @staticmethod
    def __pass_got_it(page: Page):
        button = page.locator(CheckAuth.got_it)
        if button.count() > 0:
            button.click()
            logger.debug('Clicked got it button')

    def stop_browser(self):
        self.profile.stop()

    def export_cookies(self):
        return self.profile.export_cookies()

    def __reload_page(self, page: Page):
        if page.is_closed():
            logger.debug('Page is closed, skipping reload')
            return

        if page.main_frame.is_detached():
            logger.debug('Main frame detached, skipping reload')
            return

        try:
            # Adjust wait_until and timeout as needed; test with 'domcontentloaded' if 'load' is too strict
            page.reload(timeout=60000)  # 60 seconds timeout
            logger.debug('Page reloaded successfully')
        except Error as e:  # Catch Playwright-specific errors
            logger.warning(f'Reload failed due to Playwright error: {e}')
        except Exception as e:  # Fallback for unexpected issues
            logger.error(f'Unexpected error during reload: {e}')
