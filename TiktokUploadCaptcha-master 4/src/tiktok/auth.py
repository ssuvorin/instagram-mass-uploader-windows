import json
import os.path
import random
import time

from playwright.sync_api import BrowserContext, Playwright, Page

from src import logger
from src.db import DataBase
from src.dolphin.profile import Profile
from src.tiktok.browser import get_browser
from src.tiktok.captcha import solve_captcha
from src.tiktok.getCode import Email
from src.tiktok.locators import Pages, Login, Error, CheckAuth


class Auth:

    def __init__(self, login, password, email: Email, profile: Profile, playwright, db: DataBase = None):
        self.login = login
        self.password = password
        self.email = email
        self.profile = profile
        self.playwright = playwright
        self.db = db

    def authenticate(self):
        """
        Auth to TikTok via login and password
        """

        pr_data = self.profile.start()
        if not pr_data:
            return 2
        port, endpoint = pr_data

        self.browser = get_browser(playwright=self.playwright, endpoint_url=f'ws://127.0.0.1:{port}{endpoint}')
        page: Page = self.get_page(self.browser)

        if self.__is_logged(page):
            logger.info(f'Already logged into {self.login}')
            return page
        try:
            return self._auth(page)
        except Exception as e:
            logger.error(f'Failed to log into {self.login}. Reason: {e}')
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
            self.password = str(new_password)
            # self.db.update('Accounts', {"password": self.password}, where="username = ?",
            #                params=(self.login,))
            logger.info(f'Password for {self.login} changed to {new_password}')
        else:
            self.__remake_password()

    def _auth(self, page):
        page.goto(Pages.main)
        time.sleep(2)
        page.reload()
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
        return page

    def __is_logged(self, page) -> bool:
        cookies = self.browser.contexts[0].cookies('https://tiktok.com')
        if self.__check_cookies(cookies):
            logger.debug('Cookies look valid, proceeding to page check')
        else:
            logger.debug('Cookies incomplete, but checking page anyway')

        try:
            page.goto(Pages.main, wait_until="load", timeout=30000)
            time.sleep(random.uniform(2, 5))

            self.__pass_got_it(page)

            # Проверяем activity_button с ожиданием до 15 сек
            try:
                page.wait_for_selector(CheckAuth.activity_button, state="visible", timeout=15000)
                logger.debug('Activity button found: logged in')
                return True
            except TimeoutError:
                logger.debug('Activity button not found within 15s, checking next')

            # Проверяем messages_button с ожиданием до 15 сек
            try:
                page.wait_for_selector(CheckAuth.messages_button, state="visible", timeout=15000)
                logger.debug('Messages button found: logged in')
                return True
            except TimeoutError:
                logger.debug('Messages button not found within 15s')

            logger.debug('Page elements indicate not logged in')
            if os.environ.get('DEBUG'):
                os.makedirs(os.path.abspath(__file__).replace('src\\api.py', 'debug_screenshots'), exist_ok=True)
                page.screenshot(path=os.path.abspath(__file__).replace('src\\api.py', 'debug_screenshots') + str(time.time()))
            return False

        except Exception as e:
            logger.info(f'Page check failed: {e}. Falling back to auth.')
            return False

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
