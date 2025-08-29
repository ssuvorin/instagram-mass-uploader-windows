from __future__ import annotations
from typing import Dict, Optional, Tuple, Callable
import logging

from instagrapi.exceptions import ChallengeRequired, PleaseWaitFewMinutes, LoginRequired  # type: ignore

from .client_factory import IGClientFactory
from .proxy import build_proxy_url
from .auth_service import IGAuthService
from .session_store import DjangoDeviceSessionStore
from .device_service import ensure_persistent_device

log = logging.getLogger('insta.bio')


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


class BioService:
    def __init__(self, auth_service: IGAuthService) -> None:
        self.auth = auth_service

    def change_external_url(
        self,
        account: Dict,
        link_url: str,
        device_settings: Dict,
        session_settings: Optional[Dict] = None,
        proxy: Optional[Dict] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, Optional[Dict]]:
        username = account.get("username", "")
        password = account.get("password", "")
        if not username or not password:
            log.debug("Missing credentials for bio link change")
            if on_log:
                on_log("bio: missing credentials")
            return False, None

        store = DjangoDeviceSessionStore()
        persisted_settings = session_settings or store.load(username) or None
        resolved_device, ua_hint = ensure_persistent_device(username, persisted_settings)
        merged_device = dict(resolved_device or {})
        merged_device.update(device_settings or {})
        device_cfg = build_device_config(merged_device)
        proxy_url = build_proxy_url(proxy or {})
        user_agent = (device_settings or {}).get("user_agent") or ua_hint
        country = (merged_device or {}).get("country")
        locale = (merged_device or {}).get("locale")

        log.debug("Build client for %s | proxy=%s", username, proxy_url)
        if on_log:
            on_log(f"bio: build client (proxy={'yes' if proxy_url else 'no'})")
        cl = IGClientFactory.create_client(
            device_config=device_cfg,
            proxy_url=proxy_url,
            session_settings=persisted_settings,
            user_agent=user_agent,
            country=country,
            locale=locale,
            proxy_dict=proxy or {},
        )

        if not self.auth.ensure_logged_in(cl, username, password, on_log=on_log):
            log.debug("Auth failed for %s", username)
            if on_log:
                on_log("bio: auth failed")
            return False, None

        try:
            # Short-circuit if the link is already set
            try:
                info = cl.account_info()
                current_url = getattr(info, 'external_url', '')
                if current_url and current_url.strip() == (link_url or '').strip():
                    if on_log:
                        on_log("bio: link already set, skipping")
                    settings = None
                    try:
                        settings = cl.get_settings()
                        try:
                            store.save(username, settings)
                        except Exception:
                            pass
                    except Exception:
                        pass
                    return True, settings
            except Exception:
                pass

            log.debug("Change external_url for %s: %s", username, link_url)
            if on_log:
                on_log("bio: setting external url")

            # Preferred method available in our pinned instagrapi
            try:
                cl.set_external_url(link_url)
            except AttributeError:
                # Fallback via account_edit if method signature changes
                cl.account_edit(external_url=link_url)

            log.debug("External URL changed for %s", username)
            if on_log:
                on_log("bio: external url set")
        except ChallengeRequired as e:
            log.debug("ChallengeRequired on set external url for %s: %s", username, e)
            if on_log:
                on_log("bio: challenge required (email)")
            try:
                code = self.auth.provider.get_challenge_code(username, method="email") or ""
                if not code:
                    log.debug("No challenge code available for %s", username)
                    if on_log:
                        on_log("bio: no email code available")
                    return False, None
                cl.challenge_resolve(code)
                log.debug("Challenge resolved during bio change for %s, retrying", username)
                if on_log:
                    on_log("bio: challenge ok, retry")
                try:
                    cl.set_external_url(link_url)
                except AttributeError:
                    cl.account_edit(external_url=link_url)
                if on_log:
                    on_log("bio: external url set after challenge")
            except Exception as e2:
                log.debug("Challenge resolving/retry failed for %s: %s", username, e2)
                if on_log:
                    on_log(f"bio: challenge failed: {e2}")
                return False, None
        except Exception as e:
            log.debug("Set external url failed for %s: %s", username, e)
            if on_log:
                on_log(f"bio: set failed: {e}")
            return False, None

        try:
            settings = cl.get_settings()
            try:
                store.save(username, settings)
            except Exception:
                pass
            log.debug("Fetched updated settings for %s", username)
            if on_log:
                on_log("bio: fetched updated settings")
            return True, settings
        except Exception as e:
            log.debug("Fetching settings failed for %s: %s", username, e)
            if on_log:
                on_log(f"bio: fetch settings failed: {e}")
            return True, None 