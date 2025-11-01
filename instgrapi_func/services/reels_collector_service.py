"""
Service for collecting Reels links from Instagram accounts.

Uses the same session restoration pattern as hashtag_service.py
"""

from __future__ import annotations
import logging
import random
import time
import os
import re
import sys
from typing import Callable, Dict, List, Optional
from datetime import datetime

from instagrapi import Client  # type: ignore
from instagrapi.exceptions import ChallengeRequired, PleaseWaitFewMinutes, LoginRequired  # type: ignore

from .client_factory import IGClientFactory
from .proxy import build_proxy_url
from .auth_service import IGAuthService
from .code_providers import TwoFactorProvider
from .device_service import ensure_persistent_device
from .session_store import DjangoDeviceSessionStore


log = logging.getLogger("insta.reels.collector")


class ReelsCollectorResult:
    def __init__(
        self,
        total_accounts: int,
        processed_accounts: int,
        failed_accounts: int,
        total_reels_links: int,
        output_file_path: str,
    ) -> None:
        self.total_accounts = total_accounts
        self.processed_accounts = processed_accounts
        self.failed_accounts = failed_accounts
        self.total_reels_links = total_reels_links
        self.output_file_path = output_file_path

    def to_dict(self) -> Dict:
        return {
            "total_accounts": self.total_accounts,
            "processed_accounts": self.processed_accounts,
            "failed_accounts": self.failed_accounts,
            "total_reels_links": self.total_reels_links,
            "output_file_path": self.output_file_path,
        }


class ReelsCollectorService:
    def __init__(self, provider: Optional[TwoFactorProvider] = None) -> None:
        self.auth = IGAuthService(provider=provider)
        # Enhanced delay configuration for better anti-detection (same as hashtag_service)
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
            self.delay_long_every_n = int(os.getenv("IG_DELAY_LONG_EVERY_N", "5"))  # every ~N accounts
        except Exception:
            self.delay_long_every_n = 5
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
        """Randomized delay to mimic human behavior"""
        lo = self.delay_min_s if min_s is None else min_s
        hi = self.delay_max_s if max_s is None else max_s
        if hi < lo:
            hi = lo + 0.2
        delay = random.uniform(lo, hi)
        time.sleep(delay)
        log.debug(f"Human delay: {delay:.2f}s")

    def _human_long_think(self) -> None:
        """Occasional long pause to simulate human thinking/browsing"""
        delay = random.uniform(self.delay_long_min_s, self.delay_long_max_s)
        time.sleep(delay)
        log.debug(f"Long think pause: {delay:.2f}s")

    def _content_reading_pause(self) -> None:
        """Simulate time spent reading/viewing content like a human"""
        delay = random.uniform(self.content_reading_delay_min, self.content_reading_delay_max)
        time.sleep(delay)
        log.debug(f"Content reading pause: {delay:.2f}s")

    def _random_micro_pause(self) -> None:
        """Small random pauses to break request patterns"""
        if random.random() < self.random_pause_probability:
            pause_time = random.uniform(0.5, 2.0)
            time.sleep(pause_time)
            log.debug(f"Random micro pause: {pause_time:.2f}s")

    def _extract_username_from_url(self, url: str) -> Optional[str]:
        """Extract username from Instagram URL"""
        url = url.strip()
        # Match patterns like:
        # https://instagram.com/username
        # https://www.instagram.com/username
        # instagram.com/username
        # @username
        patterns = [
            r'https?://(?:www\.)?instagram\.com/([^/?\s]+)',
            r'instagram\.com/([^/?\s]+)',
            r'@([a-zA-Z0-9._]+)',
            r'^([a-zA-Z0-9._]+)$',  # Just username
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                username = match.group(1).strip()
                # Remove trailing dots or common artifacts
                username = username.rstrip('.')
                return username
        return None

    def _get_user_reels(
        self,
        cl: Client,
        target_username: str,
        on_log: Optional[Callable[[str], None]] = None,
        max_amount: int = 0,  # 0 means all
        fast_mode: bool = False,
    ) -> List[str]:
        """Get all reels links from a user's account using ONLY private API"""
        reels_links = []
        
        try:
            # Get user ID from username using ONLY private API
            user_id = None
            try:
                if on_log:
                    on_log(f"Getting user_id for @{target_username} via private API...")
                # Use private API endpoint directly - no public/GQL fallbacks
                result = cl.private_request(f"users/{target_username}/usernameinfo/")  # type: ignore[attr-defined]
                if isinstance(result, dict):
                    user_id = result.get('user', {}).get('pk')
                    if user_id:
                        user_id = str(user_id)
                        if on_log:
                            on_log(f"Found user_id {user_id} via private API for @{target_username}")
                        log.info(f"Got user_id {user_id} via private API for @{target_username}")
                    else:
                        if on_log:
                            on_log(f"Private API returned no user_id for @{target_username}")
                        log.warning(f"Private API returned no user_id for @{target_username}")
                        return reels_links
                else:
                    if on_log:
                        on_log(f"Private API returned unexpected format for @{target_username}")
                    log.warning(f"Private API returned unexpected format for @{target_username}")
                    return reels_links
            except LoginRequired as e:
                if on_log:
                    on_log(f"Session expired while getting user_id for @{target_username}, attempting restore...")
                raise
            except Exception as e:
                if on_log:
                    on_log(f"Private API failed for @{target_username}: {e}")
                log.error(f"Private API failed for @{target_username}: {e}", exc_info=True)
                return reels_links
            
            if not user_id:
                if on_log:
                    on_log(f"Could not resolve user_id for @{target_username}")
                log.error(f"Could not resolve user_id for @{target_username}")
                return reels_links

            # Human delay before fetching medias (minimal in fast mode)
            if fast_mode:
                time.sleep(random.uniform(0.2, 0.5))
            else:
                self._human_delay()
                self._random_micro_pause()

            # Fetch user clips (reels) using ONLY private API
            try:
                if on_log:
                    on_log(f"Fetching clips/reels for @{target_username} via private API (max: {max_amount if max_amount > 0 else 'all'})...")
                
                # Use private API endpoint directly - clips/user/
                clips_collected = 0
                next_max_id = ""
                all_clips_items = []
                
                while True:
                    try:
                        # Private API call for clips
                        response = cl.private_request(  # type: ignore[attr-defined]
                            "clips/user/",
                            data={
                                "target_user_id": int(user_id),
                                "max_id": next_max_id,
                                "page_size": 12,  # Default page size
                                "include_feed_video": "true",
                            },
                        )
                        
                        items = response.get("items", [])
                        if not items:
                            break
                        
                        # Extract clips from response
                        for item in items:
                            media_data = item.get("media", {})
                            if media_data:
                                # Extract code/shortcode from media
                                code = media_data.get("code") or media_data.get("shortcode")
                                if code:
                                    link = f"https://www.instagram.com/reel/{code}/"
                                    if link not in reels_links:  # Avoid duplicates
                                        reels_links.append(link)
                                        all_clips_items.append(item)
                                        clips_collected += 1
                                        
                                        # Check if we've reached the limit
                                        if max_amount > 0 and clips_collected >= max_amount:
                                            break
                        
                        # Check if we've reached the limit
                        if max_amount > 0 and clips_collected >= max_amount:
                            break
                        
                        # Get next page cursor
                        paging_info = response.get("paging_info", {})
                        next_max_id = paging_info.get("max_id", "")
                        
                        if not next_max_id:
                            break
                        
                        # Small delay between pages (minimal in fast mode)
                        if fast_mode:
                            time.sleep(random.uniform(0.1, 0.3))
                        else:
                            time.sleep(random.uniform(0.5, 1.0))
                        
                    except LoginRequired as e:
                        if on_log:
                            on_log(f"Session expired while fetching clips for @{target_username}")
                        raise
                    except Exception as page_error:
                        if on_log:
                            on_log(f"Error fetching clips page for @{target_username}: {page_error}")
                        log.warning(f"Error fetching clips page for @{target_username}: {page_error}")
                        break
                
                if on_log:
                    on_log(f"Found {len(reels_links)} clips/reels for @{target_username} via private API")
                
                # Simulate reading/viewing content if we got many clips (skip in fast mode)
                if not fast_mode and len(reels_links) > 10:
                    self._content_reading_pause()
                        
            except LoginRequired as e:
                if on_log:
                    on_log(f"Session expired while fetching clips for @{target_username}")
                raise
            except Exception as e:
                if on_log:
                    on_log(f"Error fetching clips for @{target_username}: {e}")
                log.warning(f"Error fetching clips for @{target_username}: {e}", exc_info=True)
                # Fallback: try to get user feed and filter for reels using private API
                try:
                    if on_log:
                        on_log(f"Fallback: fetching user feed via private API for @{target_username}")
                    
                    # Use private API endpoint for user feed
                    feed_items = []
                    next_max_id_feed = ""
                    max_feed_items = max_amount if max_amount > 0 else 120
                    
                    while len(feed_items) < max_feed_items:
                        try:
                            # Build params for feed request
                            feed_params = {
                                "max_id": next_max_id_feed,
                                "count": 33,  # Default page size
                                "ranked_content": "true",
                            }
                            # Add rank_token if available (it's a property that may not exist)
                            try:
                                rank_token = cl.rank_token  # type: ignore[attr-defined]
                                if rank_token:
                                    feed_params["rank_token"] = rank_token
                            except Exception:
                                pass  # rank_token is optional
                            
                            response = cl.private_request(  # type: ignore[attr-defined]
                                f"feed/user/{user_id}/",
                                params=feed_params,
                            )
                            
                            items = response.get("items", [])
                            if not items:
                                break
                            
                            feed_items.extend(items)
                            
                            # Get next page cursor
                            next_max_id_feed = response.get("next_max_id", "")
                            if not next_max_id_feed:
                                break
                            
                            # Small delay between pages
                            if fast_mode:
                                time.sleep(random.uniform(0.1, 0.3))
                            else:
                                time.sleep(random.uniform(0.5, 1.0))
                            
                        except Exception as feed_error:
                            log.warning(f"Error fetching feed page: {feed_error}")
                            break
                    
                    # Filter for reels (media_type 2 = video/reel, 13 = clip/reel)
                    for item in feed_items:
                        try:
                            media_type = item.get("media_type")
                            # Media type 2 is video/reel, type 13 is clip/reel
                            if media_type in (2, 13):
                                code = item.get("code") or item.get("shortcode")
                                if code:
                                    link = f"https://www.instagram.com/reel/{code}/"
                                    if link not in reels_links:  # Avoid duplicates
                                        reels_links.append(link)
                        except Exception:
                            continue
                    
                    if on_log:
                        on_log(f"Fallback: found {len(reels_links)} total reels for @{target_username}")
                except Exception as fallback_error:
                    if on_log:
                        on_log(f"Fallback also failed for @{target_username}: {fallback_error}")
                    log.warning(f"Fallback also failed for @{target_username}: {fallback_error}", exc_info=True)

        except LoginRequired:
            raise
        except Exception as e:
            if on_log:
                on_log(f"Error getting reels for @{target_username}: {e}")
            log.error(f"Error getting reels for @{target_username}: {e}", exc_info=True)
        
        return reels_links

    def collect_reels_from_accounts(
        self,
        account_username: str,
        account_password: str,
        target_usernames: List[str],
        proxy: Optional[Dict] = None,
        on_log: Optional[Callable[[str], None]] = None,
        max_reels_per_account: int = 0,  # 0 means all
        output_dir: Optional[str] = None,
        fast_mode: bool = False,  # Fast mode with minimal delays
    ) -> ReelsCollectorResult:
        """
        Collect reels links from multiple target accounts using one authenticated account.
        
        Args:
            account_username: Instagram account username to use for authentication
            account_password: Instagram account password
            target_usernames: List of target account usernames to collect reels from
            proxy: Optional proxy configuration
            on_log: Optional logging callback
            max_reels_per_account: Maximum reels to collect per account (0 = all)
            output_dir: Directory to save output file (default: media/debug/reels_collector)
            fast_mode: If True, use minimal delays for faster processing (default: False)
        
        Returns:
            ReelsCollectorResult with statistics and output file path
        """
        # Adjust delays for fast mode
        if fast_mode:
            original_delay_min = self.delay_min_s
            original_delay_max = self.delay_max_s
            original_long_every_n = self.delay_long_every_n
            # Use minimal delays in fast mode
            self.delay_min_s = 0.3
            self.delay_max_s = 0.8
            self.delay_long_every_n = 20  # Less frequent long pauses
            if on_log:
                on_log("⚡ Fast mode enabled: using minimal delays")
            log.info("Fast mode enabled: using minimal delays")
        if on_log:
            on_log(f"🚀 Starting reels collection for {len(target_usernames)} accounts")
            mode_str = "⚡ FAST MODE" if fast_mode else "Normal"
            on_log(f"Mode: {mode_str}, delay={self.delay_min_s}-{self.delay_max_s}s, long_pause_every={self.delay_long_every_n} accounts")
        log.info(f"Starting reels collection for {len(target_usernames)} accounts (fast_mode={fast_mode})")
        log.info(f"Anti-detection settings: delay={self.delay_min_s}-{self.delay_max_s}s, long_pause_every={self.delay_long_every_n} accounts")

        # Load persisted session and ensure persistent device like hashtag_service
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

        # Auth
        if on_log:
            on_log(f"Authenticating as @{account_username}...")
        if not self.auth.ensure_logged_in(cl, account_username, account_password, on_log=on_log):
            log.error(f"Login failed for {account_username}")
            raise LoginRequired("Login failed or 2FA/Challenge unresolved")
        
        if on_log:
            on_log(f"✓ Successfully authenticated as @{account_username}")
        log.info(f"Successfully authenticated as @{account_username}")
        
        # Post-login pause like a human reading the screen (minimal in fast mode)
        if fast_mode:
            self._human_delay(min_s=0.2, max_s=0.5)
        else:
            self._human_delay()
            self._random_micro_pause()
            self._content_reading_pause()

        # Save refreshed session after auth
        try:
            settings = cl.get_settings()  # type: ignore[attr-defined]
            session_store.save(account_username, settings)
            if on_log:
                on_log("✓ Session saved to store")
            log.debug("Session saved to store")
        except Exception as save_e:
            log.warning(f"Failed to save session after auth: {save_e}")

        # Prepare output files for immediate writing
        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'media',
                'debug',
                'reels_collector'
            )
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file_path = os.path.join(output_dir, f"reels_links_{timestamp_str}.txt")
        
        # Also save to project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        root_output_file_path = os.path.join(project_root, f"reels_links_{timestamp_str}.txt")
        
        # File for accounts with reels
        accounts_with_reels_file_path = os.path.join(project_root, f"accounts_with_reels_{timestamp_str}.txt")
        
        # Open files for writing
        output_file = None
        root_output_file = None
        accounts_with_reels_file = None
        try:
            output_file = open(output_file_path, 'w', encoding='utf-8')
            root_output_file = open(root_output_file_path, 'w', encoding='utf-8')
            accounts_with_reels_file = open(accounts_with_reels_file_path, 'w', encoding='utf-8')
            if on_log:
                on_log(f"📁 Opened files for writing:")
                on_log(f"   Debug: {output_file_path}")
                on_log(f"   Root: {root_output_file_path}")
                on_log(f"   Accounts with reels: {accounts_with_reels_file_path}")
            print(f"\n{'='*80}")
            print(f"🚀 Starting collection...")
            print(f"📁 Writing to:")
            print(f"   📁 {os.path.abspath(output_file_path)}")
            print(f"   📁 {os.path.abspath(root_output_file_path)}")
            print(f"   📁 Accounts with reels: {os.path.abspath(accounts_with_reels_file_path)}")
            print(f"{'='*80}\n")
        except Exception as e:
            if on_log:
                on_log(f"✗ Failed to open output files: {e}")
            log.error(f"Failed to open output files: {e}", exc_info=True)
            print(f"\n❌ ERROR: Failed to open output files: {e}\n")
            output_file_path = ""
            root_output_file_path = ""
            accounts_with_reels_file_path = ""

        # Process each target account
        all_reels_links = []
        processed_count = 0
        failed_count = 0
        failed_accounts = []

        for idx, target_url_or_username in enumerate(target_usernames, 1):
            target_url_or_username = target_url_or_username.strip()
            if not target_url_or_username:
                continue

            # Extract username from URL or use as-is
            target_username = self._extract_username_from_url(target_url_or_username)
            if not target_username:
                if on_log:
                    on_log(f"Skipping invalid entry: {target_url_or_username}")
                failed_count += 1
                failed_accounts.append(target_url_or_username)
                continue

            if on_log:
                on_log(f"[{idx}/{len(target_usernames)}] Processing account: @{target_username}")
            print(f"[{idx}/{len(target_usernames)}] Processing @{target_username}...", flush=True)

            # Occasional long pause every N accounts to simulate human behavior (skip in fast mode)
            if not fast_mode and idx > 1 and idx % self.delay_long_every_n == 0:
                if on_log:
                    on_log(f"Taking a longer break after {idx} accounts (anti-detection)...")
                self._human_long_think()
            elif fast_mode and idx > 1 and idx % (self.delay_long_every_n * 3) == 0:
                # Even in fast mode, occasional very short pause
                if on_log:
                    on_log(f"Brief pause after {idx} accounts...")
                time.sleep(random.uniform(2.0, 4.0))

            session_restore_attempts = 0
            max_session_restore_attempts = 3
            account_reels = []

            while session_restore_attempts <= max_session_restore_attempts:
                try:
                    # Human delay before processing account (minimal in fast mode)
                    if fast_mode:
                        time.sleep(random.uniform(0.3, 0.7))
                    else:
                        self._human_delay()
                        # Random micro pause for additional randomization
                        self._random_micro_pause()
                    
                    account_reels = self._get_user_reels(
                        cl,
                        target_username,
                        on_log=on_log,
                        max_amount=max_reels_per_account,
                        fast_mode=fast_mode,
                    )
                    all_reels_links.extend(account_reels)
                    processed_count += 1
                    
                    # Write links immediately to files and console
                    if account_reels:
                        # Write account link to accounts_with_reels file
                        account_url = f"https://www.instagram.com/{target_username}/"
                        if accounts_with_reels_file:
                            try:
                                accounts_with_reels_file.write(account_url + '\n')
                                accounts_with_reels_file.flush()
                                print(f"  📌 Account with reels: {account_url}", flush=True)
                            except Exception as write_e:
                                log.warning(f"Failed to write account link {account_url}: {write_e}")
                        
                        # Write reel links to files
                        if output_file and root_output_file:
                            for link in account_reels:
                                try:
                                    output_file.write(link + '\n')
                                    root_output_file.write(link + '\n')
                                    output_file.flush()  # Ensure immediate write
                                    root_output_file.flush()  # Ensure immediate write
                                    # Print to console immediately
                                    print(f"  ✓ {link}", flush=True)
                                except Exception as write_e:
                                    log.warning(f"Failed to write link {link}: {write_e}")
                        else:
                            # If files not opened, just print to console
                            for link in account_reels:
                                print(f"  ✓ {link}", flush=True)
                    
                    if on_log:
                        on_log(f"✓ Successfully collected {len(account_reels)} reels from @{target_username}")
                    log.info(f"Successfully collected {len(account_reels)} reels from @{target_username}")
                    break  # Success, exit retry loop

                except LoginRequired as e:
                    session_restore_attempts += 1
                    if session_restore_attempts > max_session_restore_attempts:
                        if on_log:
                            on_log(f"✗ Max session restore attempts exceeded for @{target_username}")
                        log.error(f"Max session restore attempts exceeded for @{target_username}")
                        failed_count += 1
                        failed_accounts.append(target_username)
                        break

                    if on_log:
                        on_log(f"⚠ Session expired for @{target_username} (attempt {session_restore_attempts}/{max_session_restore_attempts})")
                    log.warning(f"Session expired for @{target_username} (attempt {session_restore_attempts}/{max_session_restore_attempts})")
                    
                    if on_log:
                        on_log(f"Attempting to restore session (attempt {session_restore_attempts}/{max_session_restore_attempts})...")
                    
                    try:
                        if not self.auth.ensure_logged_in(cl, account_username, account_password, on_log=on_log):
                            if on_log:
                                on_log(f"✗ Session restoration failed for @{target_username}")
                            log.error(f"Session restoration failed for @{target_username}")
                            failed_count += 1
                            failed_accounts.append(target_username)
                            break
                        
                        if on_log:
                            on_log("✓ Session restored successfully, retrying...")
                        log.info("Session restored successfully")
                        
                        # Save refreshed session
                        try:
                            settings = cl.get_settings()  # type: ignore[attr-defined]
                            session_store.save(account_username, settings)
                            if on_log:
                                on_log("Session saved to store")
                        except Exception as save_e:
                            log.warning(f"Failed to save session: {save_e}")
                        
                        # Small delay after session restoration
                        self._human_delay(min_s=1.0, max_s=2.0)
                        continue
                    except Exception as restore_e:
                        if on_log:
                            on_log(f"✗ Session restoration error: {restore_e}")
                        log.error(f"Session restoration error: {restore_e}")
                        failed_count += 1
                        failed_accounts.append(target_username)
                        break

                except Exception as e:
                    if on_log:
                        on_log(f"✗ Error processing @{target_username}: {e}")
                    log.error(f"Error processing @{target_username}: {e}", exc_info=True)
                    failed_count += 1
                    failed_accounts.append(target_username)
                    break

            # Human delay between accounts (shorter in fast mode)
            if idx < len(target_usernames):
                if fast_mode:
                    delay = random.uniform(0.5, 1.0)
                else:
                    delay = random.uniform(2.0, 4.0)
                if on_log:
                    on_log(f"Waiting {delay:.1f}s before next account...")
                time.sleep(delay)

        # Close files and show summary
        try:
            if output_file:
                output_file.close()
            if root_output_file:
                root_output_file.close()
            if accounts_with_reels_file:
                accounts_with_reels_file.close()
        except Exception as close_e:
            if on_log:
                on_log(f"⚠ Error closing files: {close_e}")
            log.warning(f"Error closing files: {close_e}")
        
        # Count accounts with reels from file
        accounts_with_reels_count = 0
        if accounts_with_reels_file_path and os.path.exists(accounts_with_reels_file_path):
            try:
                with open(accounts_with_reels_file_path, 'r', encoding='utf-8') as f:
                    accounts_with_reels_count = len([line for line in f if line.strip()])
            except Exception:
                accounts_with_reels_count = 0
        
        if output_file_path and root_output_file_path:
            if on_log:
                on_log(f"✓ Saved {len(all_reels_links)} reels links total")
                on_log(f"   📁 Debug: {output_file_path}")
                on_log(f"   📁 Root: {root_output_file_path}")
                if accounts_with_reels_file_path:
                    on_log(f"   📁 Accounts with reels: {accounts_with_reels_file_path}")
            log.info(f"Saved {len(all_reels_links)} reels links to {output_file_path} and {root_output_file_path}")
            
            # Count accounts with reels from file
            if accounts_with_reels_file_path and os.path.exists(accounts_with_reels_file_path):
                try:
                    with open(accounts_with_reels_file_path, 'r', encoding='utf-8') as f:
                        accounts_with_reels_count = len([line for line in f if line.strip()])
                except Exception:
                    accounts_with_reels_count = 0
            
            # Print summary
            print(f"\n{'='*80}")
            print(f"✅ COLLECTION COMPLETE!")
            print(f"   📹 Total reels collected: {len(all_reels_links)}")
            print(f"   👥 Accounts with reels: {accounts_with_reels_count}")
            print(f"   ✅ Processed accounts: {processed_count}")
            print(f"   ❌ Failed accounts: {failed_count}")
            print(f"\n💾 FILES SAVED:")
            print(f"   📁 Reels links (debug): {os.path.abspath(output_file_path)}")
            print(f"   📁 Reels links (root):  {os.path.abspath(root_output_file_path)}")
            if accounts_with_reels_file_path:
                print(f"   📁 Accounts with reels: {os.path.abspath(accounts_with_reels_file_path)}")
            print(f"{'='*80}\n")

        result = ReelsCollectorResult(
            total_accounts=len(target_usernames),
            processed_accounts=processed_count,
            failed_accounts=failed_count,
            total_reels_links=len(all_reels_links),
            output_file_path=output_file_path if 'output_file_path' in locals() else "",
        )

        if on_log:
            on_log("=" * 60)
            on_log(f"📊 Collection Summary:")
            on_log(f"   Total accounts: {len(target_usernames)}")
            on_log(f"   ✓ Processed: {processed_count}")
            on_log(f"   ✗ Failed: {failed_count}")
            on_log(f"   📹 Total reels collected: {len(all_reels_links)}")
            if failed_accounts:
                on_log(f"   Failed accounts: {', '.join(failed_accounts[:10])}{'...' if len(failed_accounts) > 10 else ''}")
            on_log("=" * 60)
        
        log.info(f"Collection complete: processed={processed_count}, failed={failed_count}, total_reels={len(all_reels_links)}")
        if failed_accounts:
            log.warning(f"Failed accounts: {failed_accounts}")

        return result

