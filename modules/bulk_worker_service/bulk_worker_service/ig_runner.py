from __future__ import annotations
import os
import time
import random
from dataclasses import dataclass
from typing import List, Optional, Dict

# Rely on PYTHONPATH including repo root
from bot.src.instagram_uploader.browser_dolphin import get_browser, get_page, close_browser
from bot.src.instagram_uploader.auth_playwright import Auth
from bot.src.instagram_uploader.upload_playwright import Upload
from bot.src.instagram_uploader.dolphin_anty import DolphinAnty

from .config import settings
from .domain import BulkVideo, BulkUploadAccountTask
from .ui_client import UiClient

# Reuse existing ffmpeg uniquifier from the main project without changes
from uploader.async_video_uniquifier import AsyncVideoUniquifier


@dataclass
class VideoMeta:
    video_id: int
    file_path: str
    title: Optional[str]
    location: Optional[str]
    mentions: List[str]


def _build_proxy_payload(account_task: BulkUploadAccountTask) -> Optional[Dict[str, str]]:
    proxy = account_task.account.proxy
    if not proxy:
        return None
    return {
        'type': proxy.type,
        'host': proxy.host,
        'port': proxy.port,
        'user': proxy.user or "",
        'pass': proxy.pass_ or "",
    }


def _split_mentions(mentions_text: Optional[str]) -> List[str]:
    if not mentions_text:
        return []
    # Split by newlines/commas/spaces and filter
    raw = [m.strip() for sep in ["\n", ","] for m in mentions_text.replace(sep, "\n").split("\n")]
    cleaned = [m for m in raw if m]
    return cleaned


def _compute_videos_meta(videos: List[BulkVideo], default_location: Optional[str], default_mentions_text: Optional[str], downloaded_paths: Dict[int, str]) -> List[VideoMeta]:
    default_mentions = _split_mentions(default_mentions_text)
    meta_list: List[VideoMeta] = []
    for v in sorted(videos, key=lambda x: x.order):
        effective_location = v.location if v.location else (default_location or None)
        effective_mentions = _split_mentions(v.mentions) if v.mentions else default_mentions
        meta_list.append(VideoMeta(
            video_id=v.id,
            file_path=downloaded_paths[v.id],
            title=v.title or None,
            location=effective_location,
            mentions=effective_mentions,
        ))
    return meta_list


def _human_pause_between_videos(index: int, total: int) -> None:
    if index >= total - 1:
        return
    # Longer pause with some probability
    if random.random() > 0.7:
        delay = random.randint(60, 180)  # 1-3 min
    else:
        delay = random.randint(30, 60)
    time.sleep(delay)


async def run_account_upload_with_metadata(ui: UiClient, task_id: int, account_task: BulkUploadAccountTask, videos: List[BulkVideo], default_location: Optional[str], default_mentions_text: Optional[str], headless: bool, visible: bool) -> tuple[int, int, str, str]:
    """Run upload for a single account using bot classes with full metadata support."""
    await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"[START] {account_task.account.username}\n")

    # Download all videos first
    downloaded: Dict[int, str] = {}
    for v in sorted(videos, key=lambda x: x.order):
        file_path = await ui.download_video_to_temp(v.id, url=getattr(v, 'url', None))
        downloaded[v.id] = file_path

    # Build metadata list
    videos_meta = _compute_videos_meta(videos, default_location, default_mentions_text, downloaded)

    # Per-account uniquification via ffmpeg (as in the main project), before uploads
    uniquifier = AsyncVideoUniquifier()
    for vm in videos_meta:
        try:
            unique_path = await uniquifier.uniquify_video_async(vm.file_path, account_task.account.username, copy_number=1)
            await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"[UNIQUIFY] Prepared unique video for {vm.video_id}\n")
            vm.file_path = unique_path
        except Exception as e:
            # Fallback to original file if uniquification failed
            await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"[UNIQUIFY_FAIL] Using original video for {vm.video_id}: {e}\n")

    # Prepare account and proxy
    account_payload = account_task.account.model_dump(by_alias=True)
    proxy_payload = _build_proxy_payload(account_task)

    # Browser init
    env = os.environ.copy()
    if settings.dolphin_api_token:
        env["DOLPHIN_API_TOKEN"] = settings.dolphin_api_token
    if settings.dolphin_api_host:
        env["DOLPHIN_API_HOST"] = settings.dolphin_api_host

    dolphin_token = env.get("DOLPHIN_API_TOKEN")
    profile_id = account_payload.get('dolphin_profile_id')

    browser = get_browser(
        headless=headless and not visible,
        proxy=proxy_payload,
        api_token=dolphin_token,
        profile_id=profile_id,
        account_data=account_payload if not profile_id else None,
    )

    if not browser:
        await ui.update_account_status(account_task.account_task_id, "FAILED", log_append="[FAIL] Could not initialize browser\n")
        return 0, len(videos_meta), "", "init browser failed"

    page = get_page(browser)
    if not page:
        close_browser(browser)
        await ui.update_account_status(account_task.account_task_id, "FAILED", log_append="[FAIL] Could not get browser page\n")
        return 0, len(videos_meta), "", "get page failed"

    success = 0
    failed = 0
    full_stdout = ""
    full_stderr = ""

    try:
        # Login
        auth = Auth(page, account_payload)
        login_ok = auth.login_with_tfa()
        if not login_ok:
            await ui.update_account_status(account_task.account_task_id, "FAILED", log_append="[FAIL] Login failed\n")
            return 0, len(videos_meta), full_stdout, full_stderr

        uploader = Upload(page)
        total = len(videos_meta)
        for idx, vm in enumerate(videos_meta):
            try:
                await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"[VIDEO {idx+1}/{total}] Upload start (id={vm.video_id})\n")
                ok = uploader.upload_video(
                    video=vm.file_path,
                    title=vm.title if vm.title else vm.file_path,
                    location=vm.location,
                    mentions=vm.mentions if vm.mentions else None,
                )
                if ok:
                    success += 1
                    await ui.increment_counters(account_task.account_task_id, success=1, failed=0)
                    await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"[OK] Video {vm.video_id} uploaded\n")
                else:
                    failed += 1
                    await ui.increment_counters(account_task.account_task_id, success=0, failed=1)
                    await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"[FAIL] Video {vm.video_id} failed\n")
            except Exception as e:
                failed += 1
                await ui.increment_counters(account_task.account_task_id, success=0, failed=1)
                await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"[EXC] {e}\n")
            finally:
                _human_pause_between_videos(idx, total)

        final_status = "COMPLETED" if failed == 0 and success > 0 else ("FAILED" if success == 0 else "COMPLETED")
        await ui.update_account_status(account_task.account_task_id, final_status)
        return success, failed, full_stdout, full_stderr
    except Exception as e:
        await ui.update_account_status(account_task.account_task_id, "FAILED", log_append=f"[CRITICAL] {e}\n")
        return success, failed + (total - (success + failed) if (success + failed) < total else 0), full_stdout, str(e)
    finally:
        try:
            # Try to persist latest cookies via Dolphin API for this profile
            try:
                if profile_id and settings.dolphin_api_token:
                    local_api_base = settings.dolphin_api_host
                    if not local_api_base.endswith("/v1.0"):
                        local_api_base = local_api_base.rstrip("/") + "/v1.0"
                    dolphin = DolphinAnty(api_key=settings.dolphin_api_token, local_api_base=local_api_base)
                    cookies_list = dolphin.get_cookies(profile_id) or []
                    if cookies_list:
                        await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"[COOKIES] Retrieved {len(cookies_list)} cookies from Dolphin profile {profile_id}\n")
                        
                        # Save cookies to database
                        try:
                            from uploader.models import InstagramAccount, InstagramCookies
                            account = InstagramAccount.objects.get(username=account_task.account.username)
                            InstagramCookies.objects.update_or_create(
                                account=account,
                                defaults={'cookies_data': cookies_list, 'is_valid': True}
                            )
                            await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"[COOKIES] Saved {len(cookies_list)} cookies to database for {account.username}\n")
                        except Exception as db_error:
                            await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"[COOKIES] Failed to save cookies to DB: {db_error}\n")
            except Exception:
                pass
        finally:
            try:
                close_browser(browser)
            except Exception:
                pass 