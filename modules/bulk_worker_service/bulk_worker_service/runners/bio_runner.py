from __future__ import annotations
import asyncio
from typing import Tuple

from ..ui_client import UiClient
from ..domain import BioAggregate
from instgrapi_func.bio_manager import change_bio_link_for_account
from instgrapi_func.services.device_service import ensure_persistent_device
from instgrapi_func.services.session_store import DjangoDeviceSessionStore


async def run_bio_job(ui: UiClient, task_id: int, concurrency: int = 2) -> Tuple[int, int]:
    await ui.update_task_status_generic('bio', task_id, status="RUNNING")
    agg_json = await ui.get_aggregate('bio', task_id)
    agg = BioAggregate.model_validate(agg_json)

    sem = asyncio.Semaphore(concurrency)
    success = 0
    fail = 0

    async def _process(at):
        nonlocal success, fail
        async with sem:
            try:
                await ui.update_account_status_generic('bio', at.account_task_id, status="RUNNING", log_append=f"bio: start {at.account.username}\n")
                store = DjangoDeviceSessionStore()
                persisted = store.load(at.account.username) or None
                device_settings, _ua = ensure_persistent_device(at.account.username, persisted)

                ok, updated = change_bio_link_for_account(
                    account={"username": at.account.username, "password": at.account.password, "tfa_secret": at.account.tfa_secret, "email": at.account.email_username, "email_password": at.account.email_password},
                    link_url=agg.link_url,
                    device_settings=device_settings,
                    session_settings=persisted,
                    proxy=(at.account.proxy.model_dump(by_alias=True) if at.account.proxy else None),
                    on_log=lambda m: asyncio.create_task(ui.update_account_status_generic('bio', at.account_task_id, log_append=m + "\n")),
                )
                if ok:
                    success += 1
                    await ui.update_account_status_generic('bio', at.account_task_id, status="COMPLETED")
                else:
                    fail += 1
                    await ui.update_account_status_generic('bio', at.account_task_id, status="FAILED")
            except Exception as e:
                fail += 1
                await ui.update_account_status_generic('bio', at.account_task_id, status="FAILED", log_append=f"exc: {e}\n")

    await asyncio.gather(*[_process(at) for at in agg.accounts])
    await ui.update_task_status_generic('bio', task_id, status=("COMPLETED" if fail == 0 else ("FAILED" if success == 0 else "COMPLETED")))
    return success, fail 