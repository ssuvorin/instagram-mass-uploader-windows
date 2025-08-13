from __future__ import annotations
from typing import Dict, Optional, Tuple, Callable, List
import logging
import random
import time

from instagrapi import Client  # type: ignore
from instagrapi.exceptions import ChallengeRequired  # type: ignore

from .client_factory import IGClientFactory
from .proxy import build_proxy_url
from .auth_service import IGAuthService
from .session_store import DjangoDeviceSessionStore
from .device_service import ensure_persistent_device

log = logging.getLogger('insta.warmup')


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


class WarmupService:
    def __init__(self, auth_service: IGAuthService) -> None:
        self.auth = auth_service

    def _build_client(
        self,
        device_settings: Dict,
        session_settings: Optional[Dict],
        proxy: Optional[Dict],
        delay_range: Optional[List[int]] = None,
    ) -> Client:
        # Ensure persistent device using _username_hint
        username = getattr(self, '_username_hint', '') or ''
        store = DjangoDeviceSessionStore()
        persisted_settings = session_settings or (store.load(username) if username else None)
        resolved_device, ua_hint = ensure_persistent_device(username, persisted_settings)
        merged_device = dict(resolved_device or {})
        merged_device.update(device_settings or {})
        device_cfg = build_device_config(merged_device)
        proxy_url = build_proxy_url(proxy or {})
        user_agent = (device_settings or {}).get("user_agent") or ua_hint
        country = (merged_device or {}).get("country")
        locale = (merged_device or {}).get("locale")
        cl = IGClientFactory.create_client(
            device_config=device_cfg,
            proxy_url=proxy_url,
            session_settings=persisted_settings,
            user_agent=user_agent,
            country=country,
            locale=locale,
            proxy_dict=proxy or {},
        )
        # Best practices: add randomized small delay between requests
        try:
            if delay_range and len(delay_range) == 2:
                cl.delay_range = delay_range  # type: ignore[attr-defined]
            else:
                cl.delay_range = [1, 3]  # type: ignore[attr-defined]
        except Exception:
            pass
        return cl

    def _sleep(self, a: float, b: float) -> None:
        time.sleep(random.uniform(a, b))

    def perform_warmup(
        self,
        account: Dict,
        device_settings: Dict,
        session_settings: Optional[Dict],
        proxy: Optional[Dict],
        config: Dict,
        follow_usernames: Optional[List[str]] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, Optional[Dict]]:
        username = account.get("username", "")
        password = account.get("password", "")
        if not username or not password:
            if on_log:
                on_log("warmup: missing credentials")
            return False, None

        # Store username hint for client builder
        self._username_hint = username
        cl = self._build_client(
            device_settings,
            session_settings,
            proxy,
            delay_range=config.get('instagrapi_delay_range') or [1, 3],
        )

        if not self.auth.ensure_logged_in(cl, username, password, on_log=on_log):
            if on_log:
                on_log("warmup: auth failed")
            return False, None

        try:
            # Feed scrolls
            feed_scrolls = random.randint(
                int(config.get('feed_scroll_min_count', 1)),
                int(config.get('feed_scroll_max_count', 3))
            )
            for i in range(feed_scrolls):
                if on_log:
                    on_log(f"warmup: feed scroll {i+1}/{feed_scrolls}")
                medias = cl.get_timeline_feed()
                # brief look time
                self._sleep(1.0, 3.0)

            # Likes from last feed page if available
            like_count = random.randint(
                int(config.get('like_min_count', 0)),
                int(config.get('like_max_count', 3))
            )
            if like_count > 0:
                try:
                    # fetch again to ensure medias exist
                    feed_items = cl.get_timeline_feed()
                    media_list = getattr(feed_items, 'items', None) or []
                    # Some versions return a list already
                    if isinstance(feed_items, list):
                        media_list = feed_items
                    random.shuffle(media_list)
                    for media in media_list[:like_count]:
                        media_pk = getattr(media, 'pk', None) or getattr(media, 'id', None)
                        if not media_pk:
                            continue
                        if on_log:
                            on_log(f"warmup: like {media_pk}")
                        try:
                            cl.media_like(str(media_pk))
                        except Exception:
                            pass
                        self._sleep(2.0, 5.0)
                except Exception:
                    pass

            # Stories view (mark as seen)
            stories_to_view = random.randint(
                int(config.get('view_stories_min_count', 0)),
                int(config.get('view_stories_max_count', 3))
            )
            if stories_to_view > 0:
                try:
                    reels = cl.reels_tray()  # tray of available stories
                    tray = getattr(reels, 'tray', None) or []
                    # Some versions return list of trays directly
                    if isinstance(reels, list):
                        tray = reels
                    random.shuffle(tray)
                    viewed = 0
                    for t in tray:
                        if viewed >= stories_to_view:
                            break
                        user_id = getattr(t, 'user_id', None) or getattr(t, 'id', None)
                        if not user_id:
                            continue
                        try:
                            items = cl.user_stories(user_id)  # list of story items
                        except Exception:
                            continue
                        if not items:
                            continue
                        # mark first item as seen with realistic delay
                        item = items[0]
                        try:
                            cl.story_seen([item])  # strictly per instagrapi interface that accepts list
                            viewed += 1
                            if on_log:
                                on_log(f"warmup: story seen for user {user_id}")
                        except Exception:
                            pass
                        self._sleep(2.0, 5.0)
                except Exception:
                    pass

            # Light follow from provided usernames (resolved outside or via FollowService in views)
            if follow_usernames:
                for uname in follow_usernames:
                    if not uname:
                        continue
                    try:
                        info = cl.user_info_by_username(uname)
                        pk = getattr(info, 'pk', None)
                        if pk:
                            if on_log:
                                on_log(f"warmup: follow {uname} ({pk})")
                            try:
                                cl.user_follow(str(pk))
                            except Exception:
                                pass
                            self._sleep(3.0, 8.0)
                    except ChallengeRequired:
                        if on_log:
                            on_log("warmup: follow challenge required (email)")
                        try:
                            code = self.auth.provider.get_challenge_code(username, method="email") or ""
                            if code:
                                cl.challenge_resolve(code)
                        except Exception:
                            pass
                    except Exception:
                        pass

        except Exception as e:
            if on_log:
                on_log(f"warmup: failed: {e}")
            return False, None

        try:
            settings = cl.get_settings()
            try:
                DjangoDeviceSessionStore().save(username, settings)
            except Exception:
                pass
            if on_log:
                on_log("warmup: fetched updated settings")
            return True, settings
        except Exception:
            return True, None
