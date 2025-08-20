import random
import time

from playwright.sync_api import Page

from src.tiktok.auth import Auth
from src.tiktok.locators import Feed, Ads, Pages, Interests
from src import logger


class Booster:
    """
    Класс, который отвечает за прогрев аккаунта. Просмотр ленты, лайки, подписки и т.д.
    """

    def __init__(self, auth: Auth):
        self.auth = auth

    def start(self, page):
        if not page:
            self.auth.stop_browser()
            self.auth.profile.stop()
            return
        self.scroll_feed(page)
        self.auth.stop_browser()

    def scroll_feed(self, page):
        time.sleep(5)
        self._pass_ads(page)
        time.sleep(5)
        self._pass_interests(page)
        if page.url != Pages.main:
            page.goto(Pages.main)
        time.sleep(random.randint(3, 10))
        times_to_scroll = random.randint(5, 10)
        logger.info(f'Started scrolling feed for {times_to_scroll} times')

        viewport_size = page.viewport_size
        if not viewport_size:
            viewport_size = {'width': 1920, 'height': 1080}

        for _ in range(times_to_scroll):
            page.mouse.click(viewport_size["width"] // 2, viewport_size["height"] // 2)
            page.mouse.wheel(0, 2000)
            wait = random.randint(15, 40)
            logger.info(f'Waiting for {wait} seconds')
            time.sleep(wait)
            if random.randint(1, 2) == 1:
                self.like_video(page)


    def _pass_ads(self, page):
        try:
            ads = page.locator(Ads.banner)
            if ads.count() > 0:
                logger.info('Setting ads settings')
                page.locator(Ads.button).click()
        except:
            pass

    def _pass_interests(self, page: Page):
        try:
            banner = page.locator(Interests.banner)
            if banner.count() > 0:
                logger.info('Passing choosing interests')
                page.locator(Interests.skip).click()
        except:
            pass

    def like_video(self, page: Page):
        like_button = page.locator(Feed.like).all()[0]
        like_button.click()
        logger.info('Liked the video')
        time.sleep(2)
