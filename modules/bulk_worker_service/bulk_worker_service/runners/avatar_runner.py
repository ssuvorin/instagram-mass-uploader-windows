from __future__ import annotations
import asyncio
from typing import Tuple

from ..ui_client import UiClient
from ..domain import AvatarAggregate
from instgrapi_func.avatar_manager import change_avatar_for_account
from instgrapi_func.services.device_service import ensure_persistent_device
from instgrapi_func.services.session_store import DjangoDeviceSessionStore


async def run_avatar_job(ui: UiClient, task_id: int, concurrency: int = 2) -> Tuple[int, int]:
    await ui.update_task_status_generic('avatar', task_id, status="RUNNING")
    agg_json = await ui.get_aggregate('avatar', task_id)
    agg = AvatarAggregate.model_validate(agg_json)

    sem = asyncio.Semaphore(concurrency)
    success = 0
    fail = 0

    async def _process(at):
        nonlocal success, fail
        async with sem:
            try:
                await ui.update_account_status_generic('avatar', at.account_task_id, status="RUNNING", log_append=f"avatar: start {at.account.username}\n")
                store = DjangoDeviceSessionStore()
                persisted = store.load(at.account.username) or None
                device_settings, _ua = ensure_persistent_device(at.account.username, persisted)

                # For now pick first image by order (UI passes images list)
                # Worker could download image via UI API if needed; here we just log placeholder
                image_id = agg.images[0].id if agg.images else None
                if not image_id:
                    fail += 1
                    await ui.update_account_status_generic('avatar', at.account_task_id, status="FAILED", log_append="no image\n")
                    return
                # Expect UI to provide real file download later; using media download API would require separate endpoint
                # Here we assume a temp path already available (extend later if needed)
                image_path = await ui.download_image_to_temp(image_id)

                ok, updated = change_avatar_for_account(
                    account={"username": at.account.username, "password": at.account.password, "tfa_secret": at.account.tfa_secret, "email": at.account.email_username, "email_password": at.account.email_password},
                    image_path=image_path,
                    device_settings=device_settings,
                    session_settings=persisted,
                    proxy=(at.account.proxy.model_dump(by_alias=True) if at.account.proxy else None),
                    on_log=lambda m: asyncio.create_task(ui.update_account_status_generic('avatar', at.account_task_id, log_append=m + "\n")),
                )
                if ok:
                    success += 1
                    await ui.update_account_status_generic('avatar', at.account_task_id, status="COMPLETED")
                else:
                    fail += 1
                    await ui.update_account_status_generic('avatar', at.account_task_id, status="FAILED")
            except Exception as e:
                fail += 1
                await ui.update_account_status_generic('avatar', at.account_task_id, status="FAILED", log_append=f"exc: {e}\n")

    await asyncio.gather(*[_process(at) for at in agg.accounts])
    await ui.update_task_status_generic('avatar', task_id, status=("COMPLETED" if fail == 0 else ("FAILED" if success == 0 else "COMPLETED")))
    return success, fail 