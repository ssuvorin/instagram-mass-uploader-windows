from __future__ import annotations
import os
from typing import Optional, Dict

from bot.src.instagram_uploader.browser_dolphin import get_browser, get_page, close_browser
from bot.src.instagram_uploader.auth_playwright import Auth

from ..config import settings
from ..domain import BulkUploadAccountTask


def build_proxy_payload(account_task: BulkUploadAccountTask) -> Optional[Dict[str, str]]:
    proxy = account_task.account.proxy
    if not proxy:
        return None
    return {
        'type': proxy.type,
        'host': proxy.host,
        'port': proxy.port,
        'user': proxy.user or "",
        'pass': proxy.pass_ or "",
    }


def init_browser_for_account(account_payload: dict, proxy_payload: Optional[dict], headless: bool, visible: bool):
    env = os.environ.copy()
    if settings.dolphin_api_token:
        env["DOLPHIN_API_TOKEN"] = settings.dolphin_api_token
    if settings.dolphin_api_host:
        env["DOLPHIN_API_HOST"] = settings.dolphin_api_host

    dolphin_token = env.get("DOLPHIN_API_TOKEN")
    profile_id = account_payload.get('dolphin_profile_id')

    browser = get_browser(
        headless=headless and not visible,
        proxy=proxy_payload,
        api_token=dolphin_token,
        profile_id=profile_id,
        account_data=account_payload if not profile_id else None,
    )
    page = get_page(browser) if browser else None
    return browser, page


def perform_login(page, account_payload: dict) -> bool:
    auth = Auth(page, account_payload)
    return bool(auth.login_with_tfa()) 