from __future__ import annotations
import asyncio
from typing import Tuple

from ..ui_client import UiClient
from ..domain import MediaUniqAggregate
from uploader.async_video_uniquifier import AsyncVideoUniquifier


async def run_media_uniq_job(ui: UiClient, task_id: int) -> Tuple[int, int]:
    await ui.update_task_status_generic('media_uniq', task_id, status="RUNNING")
    agg_json = await ui.get_aggregate('media_uniq', task_id)
    agg = MediaUniqAggregate.model_validate(agg_json)

    uniquifier = AsyncVideoUniquifier()
    success = 0
    fail = 0
    for v in agg.videos:
        try:
            path = await ui.download_video_to_temp(v.id, url=getattr(v, 'url', None))
            out = await uniquifier.uniquify_video_async(path, f"task_{task_id}")
            success += 1
        except Exception:
            fail += 1
    await ui.update_task_status_generic('media_uniq', task_id, status=("COMPLETED" if fail == 0 else ("FAILED" if success == 0 else "COMPLETED")))
    return success, fail 