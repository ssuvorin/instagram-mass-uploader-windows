from __future__ import annotations
from typing import Dict, Optional, Tuple, Callable
from .client_factory import IGClientFactory
from .proxy import build_proxy_url
from .auth_service import IGAuthService
import logging
from instagrapi.exceptions import ChallengeRequired  # type: ignore

log = logging.getLogger('insta.avatar')


def build_device_config(device_settings: Dict) -> Dict:
    return {
        "cpu": device_settings.get("cpu", "exynos9820"),
        "dpi": device_settings.get("dpi", "640dpi"),
        "model": device_settings.get("model", "SM-G973F"),
        "device": device_settings.get("device", "beyond1"),
        "resolution": device_settings.get("resolution", "1440x3040"),
        "app_version": device_settings.get("app_version", "269.0.0.18.75"),
        "manufacturer": device_settings.get("manufacturer", "samsung"),
        "version_code": device_settings.get("version_code", "314665256"),
        "android_release": device_settings.get("android_release", "10"),
        "android_version": device_settings.get("android_version", 29),
        # Optional identifiers
        "uuid": device_settings.get("uuid"),
        "android_device_id": device_settings.get("android_device_id"),
        "phone_id": device_settings.get("phone_id"),
        "client_session_id": device_settings.get("client_session_id"),
    }


class AvatarService:
    def __init__(self, auth_service: IGAuthService) -> None:
        self.auth = auth_service

    def change_avatar(
        self,
        account: Dict,
        image_path: str,
        device_settings: Dict,
        session_settings: Optional[Dict] = None,
        proxy: Optional[Dict] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, Optional[Dict]]:
        username = account.get("username", "")
        password = account.get("password", "")
        if not username or not password:
            log.debug("Missing credentials for avatar change")
            if on_log:
                on_log("avatar: missing credentials")
            return False, None

        device_cfg = build_device_config(device_settings or {})
        proxy_url = build_proxy_url(proxy or {})
        user_agent = (device_settings or {}).get("user_agent")
        country = (device_settings or {}).get("country")
        locale = (device_settings or {}).get("locale")

        log.debug("Build client for %s | proxy=%s", username, proxy_url)
        if on_log:
            on_log(f"avatar: build client (proxy={'yes' if proxy_url else 'no'})")
        cl = IGClientFactory.create_client(
            device_config=device_cfg,
            proxy_url=proxy_url,
            session_settings=session_settings,
            user_agent=user_agent,
            country=country,
            locale=locale,
            proxy_dict=proxy or {},
        )

        if not self.auth.ensure_logged_in(cl, username, password, on_log=on_log):
            log.debug("Auth failed for %s", username)
            if on_log:
                on_log("avatar: auth failed")
            return False, None

        try:
            log.debug("Change profile picture for %s: %s", username, image_path)
            if on_log:
                on_log("avatar: changing profile picture")
            cl.account_change_picture(image_path)
            log.debug("Profile picture changed for %s", username)
            if on_log:
                on_log("avatar: picture changed")
        except ChallengeRequired as e:
            log.debug("ChallengeRequired on change picture for %s: %s", username, e)
            if on_log:
                on_log("avatar: challenge required (email)")
            try:
                code = self.auth.provider.get_challenge_code(username, method="email") or ""
                if not code:
                    log.debug("No challenge code available for %s", username)
                    if on_log:
                        on_log("avatar: no email code available")
                    return False, None
                cl.challenge_resolve(code)
                log.debug("Challenge resolved during avatar change for %s, retrying", username)
                if on_log:
                    on_log("avatar: challenge ok, retry")
                cl.account_change_picture(image_path)
                log.debug("Profile picture changed after challenge for %s", username)
                if on_log:
                    on_log("avatar: picture changed after challenge")
            except Exception as e2:
                log.debug("Challenge resolving/retry failed for %s: %s", username, e2)
                if on_log:
                    on_log(f"avatar: challenge failed: {e2}")
                return False, None
        except Exception as e:
            log.debug("Change picture failed for %s: %s", username, e)
            if on_log:
                on_log(f"avatar: change failed: {e}")
            return False, None

        try:
            settings = cl.get_settings()
            log.debug("Fetched updated settings for %s", username)
            if on_log:
                on_log("avatar: fetched updated settings")
            return True, settings
        except Exception as e:
            log.debug("Fetching settings failed for %s: %s", username, e)
            if on_log:
                on_log(f"avatar: fetch settings failed: {e}")
            return True, None 