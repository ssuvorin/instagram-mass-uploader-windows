import os.path
import random
import time

from playwright.sync_api import Page, Error

from tiktok_uploader.bot_integration import logger
from tiktok_uploader.bot_integration.tiktok.locators import Pages, Upload, Ads, VideoLinks
from tiktok_uploader.bot_integration.tiktok.video import Video
from tiktok_uploader.bot_integration.tiktok.auth import Auth
from tiktok_uploader.bot_integration.tiktok.utils import delete_video, delete_title, safe_delete_after_upload, safe_delete_with_backup
from tiktok_uploader.bot_integration.tiktok.captcha import solve_captcha


class Uploader:

    def __init__(self, auth: Auth):
        self.auth = auth

    def upload_videos(self, videos: [Video]):
        try:
            page = self.auth.authenticate()
            if page is None or isinstance(page, int):
                logger.info(f'Failed to auth to {self.auth.login}')
                self.auth.profile.stop()
                return
            
            # Проверяем, что page действительно является объектом Page
            if not hasattr(page, 'goto'):
                logger.error(f'Invalid page object returned for {self.auth.login}')
                self.auth.profile.stop()
                return
                
        except Exception as e:
            logger.error(f'Exception during authentication for {self.auth.login}: {e}')
            self.auth.profile.stop()
            return
        time.sleep(2)
        self.__reload_page(page)
        for video in videos:
            try:
                self.upload_video(page, video.name, video.path, video.description, video.music)
            except:
                logger.log_err()
        self.auth.profile.stop()

    def upload_video(self, page, video_name, video, description, music):

        try:
            ads = page.locator(Ads.banner)
            if ads.count() > 0:
                logger.info('Setting ads settings')
                page.locator(Ads.button).click()
        except:
            pass

        logger.info('Navigating to upload page')
        if page.url != Pages.upload:
            page.goto(Pages.upload)
        self.__reload_page(page)
        time.sleep(5)
        solve_captcha(page)
        page.locator(Upload.upload_video).set_input_files(video)
        time.sleep(40)

        self.__pass_copyright(page)

        time.sleep(2)

        if not self._is_uploaded(page):
            return

        if description:
            self._set_description(page, description)
        if music:
            self._set_music(page, music)
        time.sleep(2)
        status = self._post_video(page)
        
        # Используем безопасную функцию удаления с резервным копированием
        safe_delete_with_backup(video_name, description, status, create_backup=True)

    def _set_description(self, page: Page, description: str):
        logger.info(f'Setting description: {description}')
        time.sleep(3)
        description = description.encode('utf-8', 'ignore').decode('utf-8')
        field = page.locator(Upload.description)
        field.click()
        time.sleep(2)
        field.clear()
        time.sleep(2)
        for word in description.split():
            if word[0] == '#':
                field.type(word + ' ', delay=100)
                page.keyboard.press("Backspace")
                time.sleep(3)
                page.keyboard.press('Enter')
            # TODO: Доделать упоминания
            # elif word[0] == '@':
            #     logger.debug('Adding mention: ' + word)
            #     field.type(word + ' ')
            #     time.sleep(3)
            #     page.keyboard.press('Backspace')
            #     mention = page.locator(Upload.mention_box)
            #     found = False
            #     waiting_interval = 0.5
            #     timeout = 5
            #     start_time = time.time()
            #     while not found and (time.time() - start_time < timeout):
            #         user_id_elements = page.locator(Upload.mention_box_user_id).all()
            #         time.sleep(1)
            #         for i in range(len(user_id_elements)):
            #             user_id_element = user_id_elements[i]
            #             if user_id_element and user_id_element.is_enabled:
            #                 username = user_id_element.inner_text().split(" ")[0]
            #                 if username.lower() == word[1:].lower():
            #                     found = True
            #                     logger.debug("Matching User found : Clicking User")
            #                     for j in range(i):
            #                         page.keyboard.press('ArrowDown')
            #                     page.keyboard.press('Enter')
            #                     break
            #             if not found:
            #                 logger.debug(f"No match. Waiting for {waiting_interval} seconds...")
            #                 time.sleep(waiting_interval)
            else:
                field.type(text=word + ' ', delay=random.randint(100, 300))

    def _set_music(self, page, music):
        "TODO: Make adding music"
        pass

    def _post_video(self, page: Page):
        upload_failed = page.locator(Upload.upload_failed)
        if upload_failed.count() > 0:
            logger.error('Video has not been uploaded')
            return False
        logger.debug('Clicking the post button')
        page.mouse.wheel(0, 100000)
        time.sleep(2)
        button = page.locator(Upload.post)
        button.click()
        time.sleep(2)

        self.__pass_content_mb_restricted(page)
        self.__force_post(page)

        post_confirmation = page.locator(Upload.post_confirmation)
        if post_confirmation.count() > 0:
            logger.info('Video posted successfully')
            time.sleep(5)
            videos = page.locator(VideoLinks.video_link)
            if videos.count() > 0:
                last_video_link = videos.all()[0].get_attribute("href")
                with open(os.path.abspath(__file__).replace('src\\tiktok\\upload.py', 'links.txt'), 'a') as f:
                    f.write('https://www.tiktok.com' + last_video_link + '\n')
            return True
        else:
            logger.error('Video was not posted')
            return False

    def _is_uploaded(self, page: Page):
        status = page.locator(Upload.uploading_status).all()
        text = status[0].inner_text()
        if 'Uploaded' in text:
            return True
        return False

    def __pass_copyright(self, page: Page):
        button = page.locator(Upload.copyright_button)
        if button.count() > 0:
            time.sleep(2)
            button.click()

    def __pass_content_mb_restricted(self, page: Page):
        close = page.locator(Upload.content_may_be_restricted)
        if close.count() > 0:
            close.all()[0].click()
            time.sleep(2)
            button = page.locator(Upload.post)
            button.click()
            time.sleep(2)

    def __force_post(self, page: Page):
        post = page.locator(Upload.force_post)
        if post.count() > 0:
            post.click()

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
