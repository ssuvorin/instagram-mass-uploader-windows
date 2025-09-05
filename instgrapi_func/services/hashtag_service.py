from __future__ import annotations
import logging
import random
import time
from typing import Callable, Dict, List, Optional, Tuple

from instagrapi import Client  # type: ignore
from instagrapi.exceptions import ChallengeRequired, PleaseWaitFewMinutes, LoginRequired  # type: ignore

from .client_factory import IGClientFactory
from .proxy import build_proxy_url
from .auth_service import IGAuthService
from .code_providers import TwoFactorProvider
from .device_service import ensure_persistent_device
from .session_store import DjangoDeviceSessionStore


log = logging.getLogger("insta.hashtag")


class HashtagAnalysisResult:
    def __init__(
        self,
        hashtag: str,
        total_medias_reported: int,
        fetched_medias: int,
        total_views: int,
        analyzed_medias: int,
        pages_loaded: int,
    ) -> None:
        self.hashtag = hashtag
        self.total_medias_reported = total_medias_reported
        self.fetched_medias = fetched_medias
        self.total_views = total_views
        self.analyzed_medias = analyzed_medias
        self.pages_loaded = pages_loaded

    def to_dict(self) -> Dict:
        return {
            "hashtag": self.hashtag,
            "total_medias_reported": self.total_medias_reported,
            "fetched_medias": self.fetched_medias,
            "total_views": self.total_views,
            "analyzed_medias": self.analyzed_medias,
            "pages_loaded": self.pages_loaded,
            "average_views": (self.total_views / self.analyzed_medias) if self.analyzed_medias else 0,
        }


class HashtagAnalysisService:
    def __init__(self, provider: Optional[TwoFactorProvider] = None) -> None:
        self.auth = IGAuthService(provider=provider)

    def _human_delay(self, min_s: float = 0.8, max_s: float = 1.8) -> None:
        # Randomized delay to mimic human behavior
        time.sleep(random.uniform(min_s, max_s))

    def _sum_media_views(self, cl: Client, medias: List) -> Tuple[int, int]:
        total_views = 0
        analyzed = 0
        for m in medias:
            try:
                # Try direct attributes first (prefer play_count for reels)
                v = getattr(m, "play_count", None)
                if v is None:
                    v = getattr(m, "view_count", None)
                if v is None:
                    v = getattr(m, "video_view_count", None)
                if v is None:
                    # As a fallback, call media_info for videos/clips only
                    media_type = getattr(m, "media_type", None)
                    if media_type in (2, 13):  # 2=video, 13=clip/reel in some builds
                        try:
                            mi = cl.media_info(getattr(m, "id", None) or getattr(m, "pk", None))
                            v = (
                                getattr(mi, "play_count", None)
                                or getattr(mi, "view_count", None)
                                or getattr(mi, "video_view_count", None)
                            )
                        except Exception:
                            v = None
                if isinstance(v, (int, float)):
                    total_views += int(v)
                    analyzed += 1
            except Exception:
                continue
        return total_views, analyzed

    def _save_session_db(self, username: str, cl: Client, on_log: Optional[Callable[[str], None]]) -> None:
        try:
            from uploader.models import InstagramAccount  # type: ignore
            acc = InstagramAccount.objects.filter(username=username).first()
            if not acc:
                return
            get_settings = getattr(cl, "get_settings", None)
            settings_obj = get_settings() if callable(get_settings) else getattr(cl, "settings", {})
            if not settings_obj:
                return
            # try common field names
            updated = False
            if hasattr(acc, "session_settings"):
                acc.session_settings = settings_obj
                updated = True
            elif hasattr(acc, "insta_session"):
                acc.insta_session = settings_obj
                updated = True
            if updated:
                acc.save(update_fields=["session_settings"] if hasattr(acc, "session_settings") else ["insta_session"])
                if on_log:
                    on_log("hashtag: session saved to DB")
        except Exception:
            pass

    def analyze_hashtag(
        self,
        account_username: str,
        account_password: str,
        hashtag: str,
        proxy: Optional[Dict] = None,
        on_log: Optional[Callable[[str], None]] = None,
        max_pages: int = 50,
        page_size: int = 27,
    ) -> HashtagAnalysisResult:
        hashtag = (hashtag or "").lstrip("#").strip()
        if not hashtag:
            raise ValueError("Empty hashtag")

        if on_log:
            on_log(f"hashtag: start analysis for #{hashtag}")

        # Load persisted session and ensure persistent device like async API flow
        session_store = DjangoDeviceSessionStore()
        persisted_settings = session_store.load(account_username) or None

        device_cfg, user_agent = ensure_persistent_device(account_username, persisted_settings)
        proxy_url = build_proxy_url(proxy) if proxy else None

        cl: Client = IGClientFactory.create_client(
            device_config=device_cfg,
            proxy_url=proxy_url,
            session_settings=persisted_settings,
            user_agent=user_agent,
            proxy_dict=proxy or {},
        )

        # No session restore here: ensure_persistent_device returns (device, user_agent)

        # Auth
        if not self.auth.ensure_logged_in(cl, account_username, account_password, on_log=on_log):
            raise LoginRequired("Login failed or 2FA/Challenge unresolved")
        if on_log:
            on_log(f"hashtag: authenticated as {account_username}")

        # Save refreshed session to store and DB after auth
        try:
            settings = cl.get_settings()  # type: ignore[attr-defined]
            session_store.save(account_username, settings)
            if on_log:
                on_log("hashtag: session saved to store")
        except Exception:
            pass
        # Keep legacy DB save for compatibility
        self._save_session_db(account_username, cl, on_log)

        # Hashtag info
        self._human_delay()
        try:
            if on_log:
                on_log(f"hashtag: fetching info for #{hashtag}")
            hi = cl.hashtag_info(hashtag)
            total_reported = int(getattr(hi, "media_count", 0) or 0)
            # Save raw JSON for inspection
            self._last_info_json = getattr(cl, "last_json", {}) or {}
            if on_log:
                on_log(f"hashtag: info ok, media_count={total_reported}")
        except Exception as e:
            if on_log:
                on_log(f"hashtag: info failed: {e}")
            raise

        # Iterate recent medias via chunked pagination (Private API)
        fetched_total: int = 0
        total_views: int = 0
        analyzed_total: int = 0
        pages_loaded: int = 0
        max_id: Optional[str] = None

        for _ in range(max_pages):
            try:
                if on_log:
                    on_log(f"page {pages_loaded+1}: request recent chunk (max_id={'set' if max_id else 'none'})")
                medias, max_id = cl.hashtag_medias_v1_chunk(
                    hashtag,
                    max_amount=page_size,
                    tab_key="recent",
                    max_id=max_id,
                )
                # No file save: we store only aggregated analytics in DB
            except PleaseWaitFewMinutes as e:
                if on_log:
                    on_log(f"hashtag: rate limit, backing off: {e}")
                time.sleep(random.uniform(60, 120))
                continue
            except ChallengeRequired as e:
                if on_log:
                    on_log(f"hashtag: challenge required: {e}")
                raise
            except Exception as e:
                if on_log:
                    on_log(f"hashtag: chunk error: {e}")
                break

            pages_loaded += 1
            if not medias:
                if on_log:
                    on_log(f"page {pages_loaded}: no medias returned — stop")
                break

            views, analyzed = self._sum_media_views(cl, medias)
            total_views += views
            analyzed_total += analyzed
            fetched_total += len(medias)
            if on_log:
                on_log(
                    f"page {pages_loaded}: got {len(medias)} medias, analyzed={analyzed}, views+={views}, total_views={total_views}, next_max_id={'set' if max_id else 'none'}"
                )

            # Human-like delay between pages
            self._human_delay(0.9, 2.2)

            if not max_id:
                if on_log:
                    on_log(f"page {pages_loaded}: no next cursor — stop")
                break

        if on_log:
            on_log(
                f"done: fetched={fetched_total}, analyzed={analyzed_total}, pages={pages_loaded}, total_views={total_views}"
            )

        result_obj = HashtagAnalysisResult(
            hashtag=hashtag,
            total_medias_reported=total_reported,
            fetched_medias=fetched_total,
            total_views=total_views,
            analyzed_medias=analyzed_total,
            pages_loaded=pages_loaded,
        )
        # Persist analytics
        self.save_analytics(account_username, result_obj, on_log)
        return result_obj

    def save_analytics(self, account_username: str, result: HashtagAnalysisResult, on_log: Optional[Callable[[str], None]] = None) -> None:
        try:
            from uploader.models import HashtagAnalytics  # type: ignore
            obj = HashtagAnalytics.objects.create(
                hashtag=result.hashtag,
                total_medias_reported=result.total_medias_reported,
                fetched_medias=result.fetched_medias,
                analyzed_medias=result.analyzed_medias,
                pages_loaded=result.pages_loaded,
                total_views=result.total_views,
                average_views=(result.total_views / result.analyzed_medias) if result.analyzed_medias else 0,
                info_json=getattr(self, '_last_info_json', None),
            )
            if on_log:
                on_log(f"hashtag: analytics saved id={obj.id}")
        except Exception as e:
            if on_log:
                on_log(f"hashtag: analytics save failed: {e}")



