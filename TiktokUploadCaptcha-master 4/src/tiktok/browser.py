from playwright.sync_api import Playwright, BrowserContext


def get_browser(playwright, endpoint_url=None) -> [BrowserContext, Playwright]:
    browser = playwright.chromium.connect_over_cdp(endpoint_url)
    return browser
