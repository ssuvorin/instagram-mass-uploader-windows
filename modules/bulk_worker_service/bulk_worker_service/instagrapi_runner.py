from __future__ import annotations
import os
from typing import List, Optional, Dict

from .domain import BulkVideo, BulkUploadAccountTask
from .ui_client import UiClient

# Use the project's async instagrapi uploader
from uploader.async_impl.instagrapi import run_instagrapi_upload_async
from uploader.async_video_uniquifier import AsyncVideoUniquifier


def _apply_defaults(videos: List[BulkVideo], default_location: Optional[str], default_mentions: Optional[str]) -> List[BulkVideo]:
    enriched: List[BulkVideo] = []
    for v in sorted(videos, key=lambda x: x.order):
        enriched.append(BulkVideo(
            id=v.id,
            order=v.order,
            title=v.title,
            location=v.location if v.location else (default_location or None),
            mentions=v.mentions if v.mentions else (default_mentions or None),
            url=getattr(v, 'url', None),
        ))
    return enriched


def _map_account_payload(account_task: BulkUploadAccountTask) -> Dict:
    payload = account_task.account.model_dump(by_alias=True)
    # Align field name expected by instagrapi uploader
    if payload.get('email_username') and not payload.get('email_login'):
        payload['email_login'] = payload['email_username']
    return payload


async def run_account_upload_instagrapi(
    ui: UiClient,
    task_id: int,
    account_task: BulkUploadAccountTask,
    videos: List[BulkVideo],
    default_location: Optional[str],
    default_mentions_text: Optional[str],
    headless: bool,
    visible: bool,
) -> tuple[int, int, str, str]:
    await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"[START][API] {account_task.account.username}\n")

    # Enrich videos with defaults
    eff_videos = _apply_defaults(videos, default_location, default_mentions_text)

    # Download all videos first
    downloaded_paths: List[str] = []
    for v in eff_videos:
        path = await ui.download_video_to_temp(v.id, url=getattr(v, 'url', None))
        downloaded_paths.append(path)

    # Uniquify per account
    uniquifier = AsyncVideoUniquifier()
    unique_paths: List[str] = []
    for idx, p in enumerate(downloaded_paths):
        try:
            u = await uniquifier.uniquify_video_async(p, account_task.account.username, copy_number=1)
            unique_paths.append(u)
            await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"[UNIQUIFY] Prepared unique video for {eff_videos[idx].id}\n")
        except Exception as e:
            unique_paths.append(p)
            await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"[UNIQUIFY_FAIL] Using original for {eff_videos[idx].id}: {e}\n")

    # Build account payload for API uploader
    account_payload = _map_account_payload(account_task)

    # Run upload via instagrapi (async wrapper)
    try:
        status, completed, failed = await run_instagrapi_upload_async(
            account_details=account_payload,
            videos=eff_videos,
            video_files_to_upload=unique_paths,
            task_id=task_id,
            account_task_id=account_task.account_task_id,
            on_log=lambda msg: print(f"[API] {msg}"),
        )
        await ui.increment_counters(account_task.account_task_id, success=completed, failed=failed)
        final_status = "COMPLETED" if failed == 0 and completed > 0 else ("FAILED" if completed == 0 else "COMPLETED")
        await ui.update_account_status(account_task.account_task_id, final_status, log_append=f"[API] Done: {completed} ok, {failed} failed\n")
        return completed, failed, "", ""
    except Exception as e:
        await ui.update_account_status(account_task.account_task_id, "FAILED", log_append=f"[API][EXC] {e}\n")
        return 0, len(eff_videos), "", str(e) 