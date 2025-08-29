from __future__ import annotations
from typing import Dict, Optional, Tuple, Callable
import logging

from instagrapi import Client  # type: ignore
from instagrapi.exceptions import ChallengeRequired, PleaseWaitFewMinutes, LoginRequired  # type: ignore

from .client_factory import IGClientFactory
from .proxy import build_proxy_url
from .auth_service import IGAuthService
from .session_store import DjangoDeviceSessionStore
from .device_service import ensure_persistent_device


log = logging.getLogger('insta.follow')


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


class FollowService:
    def __init__(self, auth_service: IGAuthService) -> None:
        self.auth = auth_service

    def _build_client(
        self,
        device_settings: Dict,
        session_settings: Optional[Dict],
        proxy: Optional[Dict],
    ) -> Client:
        # Ensure persistent device
        username = (self._username_hint or "").strip() if hasattr(self, '_username_hint') else ""
        store = DjangoDeviceSessionStore()
        persisted = session_settings or (store.load(username) if username else None)
        resolved_device, ua_hint = ensure_persistent_device(username, persisted)
        merged_device = dict(resolved_device or {})
        merged_device.update(device_settings or {})
        device_cfg = build_device_config(merged_device)
        proxy_url = build_proxy_url(proxy or {})
        user_agent = (device_settings or {}).get("user_agent") or ua_hint
        country = (merged_device or {}).get("country")
        locale = (merged_device or {}).get("locale")
        log.debug("Build client | proxy=%s", proxy_url)
        cl = IGClientFactory.create_client(
            device_config=device_cfg,
            proxy_url=proxy_url,
            session_settings=persisted,
            user_agent=user_agent,
            country=country,
            locale=locale,
            proxy_dict=proxy or {},
        )
        return cl

    def resolve_user_info(
        self,
        cl: Client,
        username: str,
        on_log: Optional[Callable[[str], None]] = None,
    ) -> Optional[Dict]:
        try:
            if on_log:
                on_log(f"follow: resolve {username}")
            info = cl.user_info_by_username(username)
            data = getattr(info, 'dict', None)
            user_dict = data() if callable(data) else (info if isinstance(info, dict) else None)
            if not user_dict:
                # Fallback minimal dict
                pk = getattr(info, 'pk', None)
                user_dict = {"pk": pk}
            if on_log:
                on_log(f"follow: resolved pk={user_dict.get('pk')}")
            return user_dict
        except Exception as e:
            log.debug("Resolve user info failed for %s: %s", username, e)
            if on_log:
                on_log(f"follow: resolve failed: {e}")
            return None

    def follow_target(
        self,
        account: Dict,
        target_username: str,
        target_user_id: Optional[int],
        device_settings: Dict,
        session_settings: Optional[Dict] = None,
        proxy: Optional[Dict] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, Optional[int], Optional[Dict]]:
        """
        Follow target. If user_id is missing, resolve by username and return it.
        Returns (success, resolved_user_id, updated_session_settings)
        """
        username = account.get("username", "")
        password = account.get("password", "")
        if not username or not password:
            if on_log:
                on_log("follow: missing credentials")
            return False, target_user_id, None

        # Keep username for _build_client to access session/device
        self._username_hint = username
        cl = self._build_client(device_settings, session_settings, proxy)

        if not self.auth.ensure_logged_in(cl, username, password, on_log=on_log):
            if on_log:
                on_log("follow: auth failed")
            return False, target_user_id, None

        resolved_user_id: Optional[int] = target_user_id
        if not resolved_user_id:
            info = self.resolve_user_info(cl, target_username, on_log=on_log)
            if not info or not info.get('pk'):
                return False, None, None
            try:
                resolved_user_id = int(info.get('pk'))
            except Exception:
                resolved_user_id = None

        if not resolved_user_id:
            if on_log:
                on_log("follow: no user_id available after resolve")
            return False, None, None

        try:
            if on_log:
                on_log(f"follow: user_follow({resolved_user_id})")
            ok = cl.user_follow(str(resolved_user_id))
            if not ok:
                if on_log:
                    on_log("follow: instagrapi returned False")
                return False, resolved_user_id, None
        except ChallengeRequired as e:
            # Try resolve email challenge via provider
            if on_log:
                on_log("follow: challenge required (email)")
            try:
                code = self.auth.provider.get_challenge_code(username, method="email") or ""
                if not code:
                    if on_log:
                        on_log("follow: no email code available")
                    return False, resolved_user_id, None
                cl.challenge_resolve(code)
                # retry follow once
                ok = cl.user_follow(str(resolved_user_id))
                if not ok:
                    if on_log:
                        on_log("follow: follow after challenge returned False")
                    return False, resolved_user_id, None
            except Exception as e2:
                log.debug("Challenge resolve/retry failed for %s: %s", username, e2)
                if on_log:
                    on_log(f"follow: challenge failed: {e2}")
                return False, resolved_user_id, None
        except Exception as e:
            log.debug("Follow failed for %s -> %s: %s", username, resolved_user_id, e)
            if on_log:
                on_log(f"follow: failed: {e}")
            return False, resolved_user_id, None

        try:
            settings = cl.get_settings()
            try:
                DjangoDeviceSessionStore().save(username, settings)
            except Exception:
                pass
            if on_log:
                on_log("follow: fetched updated settings")
            return True, resolved_user_id, settings
        except Exception:
            return True, resolved_user_id, None 