from __future__ import annotations
import os
from typing import List, Optional

from bot.src.instagram_uploader.dolphin_anty import DolphinAnty

from ..config import settings


def run_cookie_robot(profile_id: str, urls: List[str], headless: bool = True, imageless: bool = False) -> dict:
    api_key = settings.dolphin_api_token
    if not api_key:
        return {"success": False, "error": "Missing DOLPHIN_API_TOKEN"}

    # Ensure API host is set for Windows/Docker environments
    os.environ["DOLPHIN_API_HOST"] = settings.dolphin_api_host

    dolphin = DolphinAnty(api_key=api_key, local_api_base=settings.dolphin_api_host if settings.dolphin_api_host.endswith("/v1.0") else settings.dolphin_api_host.rstrip("/") + "/v1.0")
    result = dolphin.run_cookie_robot_sync(
        profile_id=profile_id,
        urls=urls,
        headless=headless,
        imageless=imageless
    )
    return result 