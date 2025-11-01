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
import json
import base64
from datetime import datetime

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
                # Get views from media object (play_count/view_count already preserved from sections)
                # Media from sections already have play_count/view_count, no need for media_info() fallback
                v = getattr(m, "play_count", None)
                if v is None:
                    v = getattr(m, "view_count", None)
                if v is None:
                    v = getattr(m, "video_view_count", None)
                
                # Get likes/comments from media object (already preserved from sections)
                likes_val = getattr(m, "like_count", None)
                comments_val = getattr(m, "comment_count", None)

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

        # Use library method hashtag_medias_v1 for each tab_key
        # It handles pagination internally and processes all medias correctly
        medias: List = []
        processed_media_codes: set = set()
        skipped_duplicates = 0
        unique_media_links: list = []
        
        # Create debug directory for saving links
        debug_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'debug', 'hashtag_responses')
        os.makedirs(debug_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        tab_keys_to_try: List[str] = ["clips", "recent", "top"]  # Order: clips, recent, top
        
        for tab_key in tab_keys_to_try:
            if on_log:
                on_log(f"DEBUG: Fetching medias for tab_key='{tab_key}'")
            
            try:
                # Use library method - it handles pagination internally
                # Request more than total_reported to ensure we get all media
                library_medias = cl.hashtag_medias_v1(
                    hashtag,
                    amount=total_reported + 100 if total_reported > 0 else 200,  # Request more to get all
                    tab_key=tab_key
                )
                
                if on_log:
                    on_log(f"DEBUG: Library method returned {len(library_medias)} medias for tab_key='{tab_key}'")
                
                # Process medias from library with deduplication
                for lib_media in library_medias:
                    media_code = getattr(lib_media, 'code', None)
                    if media_code:
                        if media_code in processed_media_codes:
                            skipped_duplicates += 1
                            if on_log:
                                on_log(f"DEBUG: Skipping duplicate media code: {media_code}")
                            continue
                        processed_media_codes.add(media_code)
                        link = f"https://www.instagram.com/reel/{media_code}/"
                        unique_media_links.append(link)
                    
                    # Add to medias list for analytics
                    medias.append(lib_media)
                
                # Check if we've collected enough
                if total_reported > 0 and len(medias) >= total_reported:
                    if on_log:
                        on_log(f"DEBUG: Collected {len(medias)}/{total_reported} media, stopping")
                    break
                    
            except Exception as lib_error:
                if on_log:
                    on_log(f"DEBUG: Library method failed for tab_key='{tab_key}': {lib_error}")
                continue
            
            # Human-like delay between different tab_keys
            self._human_delay()
        
        # Process all collected medias for analytics
        pages_loaded = len(tab_keys_to_try)  # Approximate pages count
        views, likes, comments, analyzed = self._sum_media_views(cl, medias)
        total_views = views
        total_likes = likes
        total_comments = comments
        analyzed_total = analyzed
        fetched_total = len(medias)

        # Save unique media links to txt file
        links_file_path = os.path.join(debug_dir, f"hashtag_{hashtag}_{timestamp_str}_links.txt")
        try:
            with open(links_file_path, 'w', encoding='utf-8') as f:
                for link in unique_media_links:
                    f.write(link + '\n')
            if on_log:
                on_log(f"DEBUG: Saved {len(unique_media_links)} unique media links to: {links_file_path}")
        except Exception as links_error:
            if on_log:
                on_log(f"DEBUG: Failed to save links file: {links_error}")
        
        if on_log:
            on_log(
                f"done: fetched={fetched_total}, analyzed={analyzed_total}, pages={pages_loaded}, total_views={total_views}, total_likes={total_likes}, total_comments={total_comments}, skipped_duplicates={skipped_duplicates}"
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



