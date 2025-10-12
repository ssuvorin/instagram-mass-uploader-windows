from __future__ import annotations
import logging
import random
import time
from typing import Optional, Tuple

from instagrapi import Client  # type: ignore
from instagrapi.exceptions import LoginRequired  # type: ignore

from .client_factory import IGClientFactory
from .proxy import build_proxy_url
from .auth_service import IGAuthService
from .device_service import ensure_persistent_device
from .session_store import DjangoDeviceSessionStore


log = logging.getLogger("insta.account.analytics")


class AccountAnalysisService:
    def __init__(self) -> None:
        self.auth = IGAuthService()

    def _human_delay(self, min_s: float = 0.8, max_s: float = 1.8) -> None:
        time.sleep(random.uniform(min_s, max_s))

    def _sum_media_metrics(self, cl: Client, user_id: int, amount: int = 90) -> Tuple[int, int, int, int]:
        """Return (total_views, total_likes, total_comments, total_videos)."""
        total_views = 0
        total_likes = 0
        total_comments = 0
        total_videos = 0

        try:
            medias = cl.user_medias(user_id, amount=amount)
        except LoginRequired as e:
            log.warning(f"account: user_medias failed with LoginRequired: {e}")
            medias = []
        except Exception as e:
            log.warning(f"account: user_medias failed: {e}")
            medias = []

        for m in medias:
            try:
                # Count only videos/reels for views
                media_type = getattr(m, "media_type", None)
                is_video_like = media_type in (2, 13)

                views_val = None
                if is_video_like:
                    views_val = (
                        getattr(m, "play_count", None)
                        or getattr(m, "view_count", None)
                        or getattr(m, "video_view_count", None)
                    )
                if isinstance(views_val, (int, float)):
                    total_views += int(views_val)

                likes_val = getattr(m, "like_count", None)
                comments_val = getattr(m, "comment_count", None)
                if not isinstance(likes_val, (int, float)) or not isinstance(comments_val, (int, float)):
                    try:
                        mi = cl.media_info(getattr(m, "id", None) or getattr(m, "pk", None))
                        if not isinstance(likes_val, (int, float)):
                            likes_val = getattr(mi, "like_count", None)
                        if not isinstance(comments_val, (int, float)):
                            comments_val = getattr(mi, "comment_count", None)
                    except Exception:
                        pass

                if isinstance(likes_val, (int, float)):
                    total_likes += int(likes_val)
                if isinstance(comments_val, (int, float)):
                    total_comments += int(comments_val)

                total_videos += 1
            except Exception:
                continue

        return total_views, total_likes, total_comments, total_videos

    def analyze_account(
        self,
        account_username: str,
        account_password: str,
        proxy: Optional[dict] = None,
        on_log: Optional[callable] = None,
        fetch_amount: int = 120,
    ) -> None:
        """Analyze the logged-in account's last N medias and save snapshot."""
        if on_log:
            on_log(f"account: start analysis for @{account_username}")

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

        if not self.auth.ensure_logged_in(cl, account_username, account_password, on_log=on_log):
            raise LoginRequired("Login failed or 2FA/Challenge unresolved")

        if on_log:
            on_log(f"account: authenticated as {account_username}")

        try:
            settings = cl.get_settings()  # type: ignore[attr-defined]
            session_store.save(account_username, settings)
        except Exception:
            pass

        try:
            user_id = cl.user_id_from_username(account_username)
        except LoginRequired as e:
            if on_log:
                on_log(f"session expired, attempting to restore...")
            try:
                # Attempt to restore session
                if not self.auth.ensure_logged_in(cl, account_username, account_password, on_log=on_log):
                    if on_log:
                        on_log(f"session restoration failed: {e}")
                    return
                if on_log:
                    on_log(f"session restored successfully, retrying...")
                # Retry user_id resolution after session restoration
                user_id = cl.user_id_from_username(account_username)
            except Exception as restore_e:
                if on_log:
                    on_log(f"session restoration error: {restore_e}")
                return
        except Exception as e:
            if on_log:
                on_log(f"account: resolve user_id failed: {e}")
            return

        self._human_delay()
        views, likes, comments, videos = self._sum_media_metrics(cl, user_id, amount=fetch_amount)

        try:
            from uploader.models import InstagramAccount, AccountAnalytics  # type: ignore
            acc = InstagramAccount.objects.filter(username=account_username).first()
            if not acc:
                if on_log:
                    on_log("account: DB account not found, skipping save")
                return
            avg_views = (views / videos) if videos else 0.0
            er = ((likes + comments) / views) if views else 0.0
            AccountAnalytics.objects.create(
                account=acc,
                total_videos=videos,
                total_views=views,
                total_likes=likes,
                total_comments=comments,
                average_views=avg_views,
                engagement_rate=er,
            )
            if on_log:
                on_log("account: analytics saved")
        except Exception as e:
            if on_log:
                on_log(f"account: analytics save failed: {e}")


