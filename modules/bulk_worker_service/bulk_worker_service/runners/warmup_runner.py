from __future__ import annotations
import asyncio
import random
from typing import Tuple

from ..ui_client import UiClient
from ..domain import WarmupAggregate
from instgrapi_func.services.warmup_service import WarmupService
from instgrapi_func.services.auth_service import IGAuthService
from instgrapi_func.services.code_providers import CompositeProvider, TOTPProvider, AutoIMAPEmailProvider
from instgrapi_func.services.device_service import ensure_persistent_device
from instgrapi_func.services.session_store import DjangoDeviceSessionStore


async def run_warmup_job(ui: UiClient, task_id: int, concurrency: int = 2) -> Tuple[int, int]:
    await ui.update_task_status_generic('warmup', task_id, status="RUNNING")
    agg_json = await ui.get_aggregate('warmup', task_id)
    agg = WarmupAggregate.model_validate(agg_json)

    sem = asyncio.Semaphore(concurrency)
    success = 0
    fail = 0

    async def _process(at):
        nonlocal success, fail
        async with sem:
            try:
                await ui.update_account_status_generic('warmup', at.account_task_id, status="RUNNING", log_append=f"warmup: start {at.account.username}\n")
                # Build provider
                providers = []
                if at.account.tfa_secret:
                    providers.append(TOTPProvider(at.account.tfa_secret))
                if at.account.email_username and at.account.email_password:
                    providers.append(AutoIMAPEmailProvider(at.account.email_username, at.account.email_password))
                provider = CompositeProvider(providers) if providers else None
                auth = IGAuthService(provider)
                service = WarmupService(auth_service=auth)

                # Minimal device/session
                store = DjangoDeviceSessionStore()
                persisted = store.load(at.account.username) or None
                device_settings, _ua = ensure_persistent_device(at.account.username, persisted)

                ok, updated = service.perform_warmup(
                    account={"username": at.account.username, "password": at.account.password, "tfa_secret": at.account.tfa_secret, "email": at.account.email_username, "email_password": at.account.email_password},
                    device_settings=device_settings,
                    session_settings=persisted,
                    proxy=(at.account.proxy.model_dump(by_alias=True) if at.account.proxy else None),
                    config={
                        "feed_scroll_min_count": agg.actions.feed_scroll_min_count,
                        "feed_scroll_max_count": agg.actions.feed_scroll_max_count,
                        "like_min_count": agg.actions.like_min_count,
                        "like_max_count": agg.actions.like_max_count,
                        "view_stories_min_count": agg.actions.view_stories_min_count,
                        "view_stories_max_count": agg.actions.view_stories_max_count,
                        "follow_min_count": agg.actions.follow_min_count,
                        "follow_max_count": agg.actions.follow_max_count,
                    },
                    follow_usernames=None,
                    on_log=lambda m: asyncio.create_task(ui.update_account_status_generic('warmup', at.account_task_id, log_append=m + "\n")),
                )
                if ok:
                    success += 1
                    await ui.update_account_status_generic('warmup', at.account_task_id, status="COMPLETED")
                else:
                    fail += 1
                    await ui.update_account_status_generic('warmup', at.account_task_id, status="FAILED")
            except Exception as e:
                fail += 1
                await ui.update_account_status_generic('warmup', at.account_task_id, status="FAILED", log_append=f"exc: {e}\n")

    await asyncio.gather(*[_process(at) for at in agg.accounts])
    await ui.update_task_status_generic('warmup', task_id, status=("COMPLETED" if fail == 0 else ("FAILED" if success == 0 else "COMPLETED")))
    return success, fail 