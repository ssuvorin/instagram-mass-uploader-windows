"""
Enhanced Hashtag Analysis Service with advanced anti-detection measures.

Environment variables for anti-detection tuning:
- IG_DELAY_MIN_S: Minimum delay between requests (default: 1.5s)
- IG_DELAY_MAX_S: Maximum delay between requests (default: 4.5s)
- IG_DELAY_LONG_EVERY_N: Frequency of long pauses (every N pages, default: 3)
- IG_DELAY_LONG_MIN_S: Minimum long pause duration (default: 8.0s)
- IG_DELAY_LONG_MAX_S: Maximum long pause duration (default: 18.0s)
- IG_RANDOM_PAUSE_PROB: Probability of random micro-pauses (default: 0.15 = 15%)
- IG_CONTENT_READ_MIN: Minimum content reading simulation delay (default: 2.0s)
- IG_CONTENT_READ_MAX: Maximum content reading simulation delay (default: 5.0s)
"""

from __future__ import annotations
import logging
import random
import time
from typing import Callable, Dict, List, Optional, Tuple
import os

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
        total_likes: int,
        total_comments: int,
        analyzed_medias: int,
        pages_loaded: int,
    ) -> None:
        self.hashtag = hashtag
        self.total_medias_reported = total_medias_reported
        self.fetched_medias = fetched_medias
        self.total_views = total_views
        self.total_likes = total_likes
        self.total_comments = total_comments
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
            "total_likes": self.total_likes,
            "total_comments": self.total_comments,
            "engagement_rate": ((self.total_likes + self.total_comments) / self.total_views) if self.total_views else 0,
        }


class HashtagAnalysisService:
    def __init__(self, provider: Optional[TwoFactorProvider] = None) -> None:
        self.auth = IGAuthService(provider=provider)
        # Enhanced delay configuration for better anti-detection
        try:
            self.delay_min_s = float(os.getenv("IG_DELAY_MIN_S", "1.5"))
        except Exception:
            self.delay_min_s = 1.5
        try:
            self.delay_max_s = float(os.getenv("IG_DELAY_MAX_S", "4.5"))
        except Exception:
            self.delay_max_s = 4.5
        # Occasional long think pause configuration
        try:
            self.delay_long_every_n = int(os.getenv("IG_DELAY_LONG_EVERY_N", "3"))  # every ~N pages
        except Exception:
            self.delay_long_every_n = 3
        try:
            self.delay_long_min_s = float(os.getenv("IG_DELAY_LONG_MIN_S", "8.0"))
        except Exception:
            self.delay_long_min_s = 8.0
        try:
            self.delay_long_max_s = float(os.getenv("IG_DELAY_LONG_MAX_S", "18.0"))
        except Exception:
            self.delay_long_max_s = 18.0

        # Additional anti-detection parameters
        try:
            self.random_pause_probability = float(os.getenv("IG_RANDOM_PAUSE_PROB", "0.15"))  # 15% chance
        except Exception:
            self.random_pause_probability = 0.15

        try:
            self.content_reading_delay_min = float(os.getenv("IG_CONTENT_READ_MIN", "2.0"))
        except Exception:
            self.content_reading_delay_min = 2.0

        try:
            self.content_reading_delay_max = float(os.getenv("IG_CONTENT_READ_MAX", "5.0"))
        except Exception:
            self.content_reading_delay_max = 5.0

    def _human_delay(self, min_s: Optional[float] = None, max_s: Optional[float] = None) -> None:
        # Randomized delay to mimic human behavior
        lo = self.delay_min_s if min_s is None else min_s
        hi = self.delay_max_s if max_s is None else max_s
        if hi < lo:
            hi = lo + 0.2
        time.sleep(random.uniform(lo, hi))

    def _human_long_think(self) -> None:
        time.sleep(random.uniform(self.delay_long_min_s, self.delay_long_max_s))

    def _content_reading_pause(self) -> None:
        """Simulate time spent reading/viewing content like a human"""
        time.sleep(random.uniform(self.content_reading_delay_min, self.content_reading_delay_max))

    def _random_micro_pause(self) -> None:
        """Small random pauses to break request patterns"""
        if random.random() < self.random_pause_probability:
            pause_time = random.uniform(0.5, 2.0)
            time.sleep(pause_time)

    def _simulate_content_interaction(self, media_count: int) -> None:
        """Simulate human-like interaction with content"""
        # Occasionally simulate "reading" some content
        if random.random() < 0.3:  # 30% chance to simulate reading
            items_to_read = random.randint(1, min(3, media_count))
            for _ in range(items_to_read):
                self._content_reading_pause()
                # Small pause between items
                time.sleep(random.uniform(0.3, 1.0))

    def _variable_page_size(self, base_size: int = 27) -> int:
        """Return variable page size to avoid patterns"""
        variation = random.randint(-3, 3)  # ±3 items variation
        return max(20, min(35, base_size + variation))  # Keep within reasonable bounds

    def _sum_media_views(self, cl: Client, medias: List) -> Tuple[int, int, int, int]:
        total_views = 0
        total_likes = 0
        total_comments = 0
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
                        except LoginRequired:
                            # Session expired during media info fetch - skip this media
                            continue
                        except Exception:
                            v = None
                # Likes/comments (best-effort)
                likes_val = getattr(m, "like_count", None)
                comments_val = getattr(m, "comment_count", None)
                if not isinstance(likes_val, (int, float)) or not isinstance(comments_val, (int, float)):
                    try:
                        mi2 = cl.media_info(getattr(m, "id", None) or getattr(m, "pk", None))
                        if not isinstance(likes_val, (int, float)):
                            likes_val = getattr(mi2, "like_count", None)
                        if not isinstance(comments_val, (int, float)):
                            comments_val = getattr(mi2, "comment_count", None)
                    except LoginRequired:
                        # Session expired during media info fetch - skip this media
                        continue
                    except Exception:
                        pass

                if isinstance(v, (int, float)):
                    total_views += int(v)
                    analyzed += 1
                if isinstance(likes_val, (int, float)):
                    total_likes += int(likes_val)
                if isinstance(comments_val, (int, float)):
                    total_comments += int(comments_val)
            except LoginRequired:
                # Session expired - skip this media
                continue
            except Exception:
                continue
        return total_views, total_likes, total_comments, analyzed

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
        # Small post-login pause like a human reading the screen
        self._human_delay()
        # Additional random micro-pause for anti-detection
        self._random_micro_pause()

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
        # Simulate user taking time to navigate to hashtag search
        self._content_reading_pause()

        # Hashtag info with retry logic for login_required
        session_restore_attempts = 0
        max_session_restore_attempts = 3
        total_reported = 0
        
        while session_restore_attempts <= max_session_restore_attempts:
            try:
                self._human_delay()
                if on_log:
                    on_log(f"hashtag: fetching info for #{hashtag}")

                try:
                    hi = cl.hashtag_info(hashtag)
                except Exception as hashtag_error:
                    # Handle Pydantic validation errors from incomplete Instagram API responses
                    if "validation error" in str(hashtag_error).lower() or "Field required" in str(hashtag_error):
                        log.warning(f"[VALIDATION_WORKAROUND] Hashtag info validation failed: {hashtag_error}")
                        log.warning("[VALIDATION_WORKAROUND] Creating mock Hashtag object")

                        # Create mock Hashtag object with minimal required fields
                        class MockHashtag:
                            def __init__(self, name, media_count=0):
                                self.name = name
                                self.media_count = media_count
                                self.id = None  # Optional field that caused the error

                        hi = MockHashtag(hashtag, 0)  # Assume 0 if we can't get real count
                        log.warning("[VALIDATION_WORKAROUND] Created mock Hashtag object - proceeding with analysis")
                    else:
                        # Re-raise non-validation errors
                        raise hashtag_error

                total_reported = int(getattr(hi, "media_count", 0) or 0)
                # Save raw JSON for inspection
                self._last_info_json = getattr(cl, "last_json", {}) or {}
                if on_log:
                    on_log(f"hashtag: info ok, media_count={total_reported}")
                break  # Success, exit retry loop
            except LoginRequired as e:
                session_restore_attempts += 1
                if session_restore_attempts > max_session_restore_attempts:
                    if on_log:
                        on_log(f"hashtag: max session restore attempts ({max_session_restore_attempts}) exceeded for hashtag info")
                    raise
                
                if on_log:
                    on_log(f"hashtag: session expired during info fetch, attempting to restore (attempt {session_restore_attempts}/{max_session_restore_attempts})...")
                try:
                    # Attempt to restore session
                    if not self.auth.ensure_logged_in(cl, account_username, account_password, on_log=on_log):
                        if on_log:
                            on_log(f"hashtag: session restoration failed for hashtag info: {e}")
                        raise
                    if on_log:
                        on_log(f"hashtag: session restored successfully for hashtag info, retrying...")
                    # Save refreshed session
                    try:
                        settings = cl.get_settings()  # type: ignore[attr-defined]
                        session_store.save(account_username, settings)
                    except Exception:
                        pass
                    # Continue retry loop
                    continue
                except Exception as restore_e:
                    if on_log:
                        on_log(f"hashtag: session restoration error for hashtag info: {restore_e}")
                    raise
            except Exception as e:
                if on_log:
                    on_log(f"hashtag: info failed: {e}")
                raise

        # Iterate recent medias via chunked pagination (Private API)
        fetched_total: int = 0
        total_views: int = 0
        total_likes: int = 0
        total_comments: int = 0
        analyzed_total: int = 0
        pages_loaded: int = 0
        max_id: Optional[str] = None

        consecutive_empty_pages = 0
        # Reset session restore attempts for pagination (separate from hashtag info)
        session_restore_attempts = 0
        max_session_restore_attempts = 3  # Limit session restoration attempts
        for loop_index in range(max_pages):
            try:
                if on_log:
                    on_log(f"page {pages_loaded+1}: request recent chunk (max_id={'set' if max_id else 'none'})")
                # Enhanced pre-request delays for better anti-detection
                self._human_delay()
                self._random_micro_pause()
                # Get raw response first for debugging
                import json
                import base64
                if on_log:
                    on_log(f"DEBUG: Making API call to tags/{hashtag}/sections/")

                # Use variable page size for better anti-detection
                current_page_size = self._variable_page_size(page_size)

                # Make the API call manually to get raw data
                from instagrapi.mixins.hashtag import HashtagMixin
                data = {
                    "media_recency_filter": "top_recent_posts",
                    "_uuid": cl.uuid,
                    "include_persistent": "false",
                    "rank_token": cl.rank_token,
                }
                if max_id:
                    try:
                        [page_id, nm_ids] = json.loads(base64.b64decode(max_id))
                        data["max_id"] = page_id
                        data["next_media_ids"] = json.dumps(nm_ids)
                    except Exception:
                        pass

                raw_result = cl.private_request(
                    f"tags/{hashtag}/sections/",
                    data=data,
                    with_signature=False,
                )

                if on_log:
                    on_log(f"DEBUG: Raw API response sections count: {len(raw_result.get('sections', []))}")
                    # Log full raw response for debugging
                    on_log(f"DEBUG: Full raw API response (first 2000 chars): {json.dumps(raw_result, indent=2)[:2000]}...")

                # Parse manually with error handling
                medias = []
                try:
                    next_max_id = None
                    if raw_result.get("next_max_id"):
                        np = raw_result.get("next_max_id")
                        ids = raw_result.get("next_media_ids")
                        next_max_id = base64.b64encode(json.dumps([np, ids]).encode()).decode()

                    for section in raw_result["sections"]:
                        layout_content = section.get("layout_content") or {}
                        nodes = layout_content.get("medias") or []
                        for node in nodes:
                            if current_page_size and len(medias) >= current_page_size:
                                break
                            raw_media_data = node["media"]

                            # Log raw media data that contains clips_metadata
                            if raw_media_data.get("clips_metadata") and on_log:
                                clips_meta = raw_media_data["clips_metadata"]
                                if clips_meta.get("original_sound_info"):
                                    orig_sound = clips_meta["original_sound_info"]
                                    if orig_sound.get("ig_artist"):
                                        ig_artist = orig_sound["ig_artist"]
                                        if "profile_pic_id" not in ig_artist:
                                            on_log(f"DEBUG: Found media without profile_pic_id in ig_artist: {json.dumps(ig_artist, indent=2)}")

                            # Try to extract media, but catch validation errors
                            try:
                                from instagrapi.extractors import extract_media_v1
                                media = extract_media_v1(raw_media_data)
                                medias.append(media)
                            except Exception as extract_e:
                                if on_log:
                                    on_log(f"DEBUG: Media extraction failed: {extract_e}")
                                    on_log(f"DEBUG: Raw media data keys: {list(raw_media_data.keys())}")
                                    if "clips_metadata" in raw_media_data:
                                        on_log(f"DEBUG: Has clips_metadata: {bool(raw_media_data.get('clips_metadata'))}")
                                    # Log the full problematic media data
                                    on_log(f"DEBUG: Problematic media data: {json.dumps(raw_media_data, indent=2)[:2000]}...")
                                continue

                    if not raw_result.get("more_available", False):
                        next_max_id = None

                except Exception as parse_e:
                    if on_log:
                        on_log(f"DEBUG: Manual parsing failed: {parse_e}")
                        on_log(f"DEBUG: Raw result keys: {list(raw_result.keys())}")
                    raise

                max_id = next_max_id
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
            except LoginRequired as e:
                session_restore_attempts += 1
                if session_restore_attempts > max_session_restore_attempts:
                    if on_log:
                        on_log(f"hashtag: max session restore attempts ({max_session_restore_attempts}) exceeded, stopping")
                    break
                
                if on_log:
                    on_log(f"hashtag: session expired, attempting to restore (attempt {session_restore_attempts}/{max_session_restore_attempts})...")
                try:
                    # Attempt to restore session
                    if not self.auth.ensure_logged_in(cl, account_username, account_password, on_log=on_log):
                        if on_log:
                            on_log(f"hashtag: session restoration failed: {e}")
                        break
                    if on_log:
                        on_log(f"hashtag: session restored successfully, continuing...")
                    # Save refreshed session
                    try:
                        settings = cl.get_settings()  # type: ignore[attr-defined]
                        session_store.save(account_username, settings)
                    except Exception:
                        pass
                    # Reset counter on successful restoration
                    session_restore_attempts = 0
                    # Continue with the same page
                    continue
                except Exception as restore_e:
                    if on_log:
                        on_log(f"hashtag: session restoration error: {restore_e}")
                    break
            except Exception as e:
                if on_log:
                    on_log(f"hashtag: chunk error: {e}")
                break

            pages_loaded += 1
            
            # Process medias even if empty - we might still have more pages
            views, likes, comments, analyzed = self._sum_media_views(cl, medias)
            total_views += views
            total_likes += likes
            total_comments += comments
            analyzed_total += analyzed
            fetched_total += len(medias)
            if on_log:
                on_log(
                    f"page {pages_loaded}: got {len(medias)} medias, analyzed={analyzed}, views+={views}, total_views={total_views}, next_max_id={'set' if max_id else 'none'}"
                )

            # Simulate human-like content interaction after processing a page
            if medias:
                self._simulate_content_interaction(len(medias))

            # Track consecutive empty pages to avoid infinite loops
            if not medias:
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= 3:  # Stop after 3 consecutive empty pages
                    if on_log:
                        on_log(f"page {pages_loaded}: {consecutive_empty_pages} consecutive empty pages — stop")
                    break
            else:
                consecutive_empty_pages = 0  # Reset counter when we get medias

            # Stop if we've reached or exceeded the total reported media count
            if total_reported > 0 and fetched_total >= total_reported:
                if on_log:
                    on_log(f"page {pages_loaded}: reached total reported media count ({total_reported}) — stop")
                break

            # Stop only if no medias AND no next cursor (truly done)
            if not medias and not max_id:
                if on_log:
                    on_log(f"page {pages_loaded}: no medias and no next cursor — stop")
                break

            # Enhanced human-like delays between pages for better anti-detection
            self._human_delay()
            self._random_micro_pause()

            # Occasionally add a longer "think" pause (more frequently for anti-detection)
            if self.delay_long_every_n > 0 and ((loop_index + 1) % self.delay_long_every_n == 0):
                self._human_long_think()

        if on_log:
            on_log(
                f"done: fetched={fetched_total}, analyzed={analyzed_total}, pages={pages_loaded}, total_views={total_views}, total_likes={total_likes}, total_comments={total_comments}"
            )

        result_obj = HashtagAnalysisResult(
            hashtag=hashtag,
            total_medias_reported=total_reported,
            fetched_medias=fetched_total,
            total_views=total_views,
            total_likes=total_likes,
            total_comments=total_comments,
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
                total_likes=result.total_likes,
                total_comments=result.total_comments,
                engagement_rate=((result.total_likes + result.total_comments) / result.total_views) if result.total_views else 0,
                info_json=getattr(self, '_last_info_json', None),
            )
            if on_log:
                on_log(f"hashtag: analytics saved id={obj.id}")
        except Exception as e:
            if on_log:
                on_log(f"hashtag: analytics save failed: {e}")



