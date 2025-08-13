from __future__ import annotations
import asyncio
import random
from typing import Tuple

from ..ui_client import UiClient
from ..domain import FollowAggregate
from instgrapi_func.services.follow_service import FollowService
from instgrapi_func.services.auth_service import IGAuthService
from instgrapi_func.services.code_providers import CompositeProvider, TOTPProvider, AutoIMAPEmailProvider
from instgrapi_func.services.device_service import ensure_persistent_device
from instgrapi_func.services.session_store import DjangoDeviceSessionStore


async def run_follow_job(ui: UiClient, task_id: int, concurrency: int = 2) -> Tuple[int, int]:
    await ui.update_task_status_generic('follow', task_id, status="RUNNING")
    agg_json = await ui.get_aggregate('follow', task_id)
    agg = FollowAggregate.model_validate(agg_json)

    sem = asyncio.Semaphore(concurrency)
    success = 0
    fail = 0

    async def _process(at):
        nonlocal success, fail
        async with sem:
            try:
                await ui.update_account_status_generic('follow', at.account_task_id, status="RUNNING", log_append=f"follow: start {at.account.username}\n")
                providers = []
                if at.account.tfa_secret:
                    providers.append(TOTPProvider(at.account.tfa_secret))
                if at.account.email_username and at.account.email_password:
                    providers.append(AutoIMAPEmailProvider(at.account.email_username, at.account.email_password))
                provider = CompositeProvider(providers) if providers else None
                auth = IGAuthService(provider)
                service = FollowService(auth_service=auth)

                store = DjangoDeviceSessionStore()
                persisted = store.load(at.account.username) or None
                device_settings, _ua = ensure_persistent_device(at.account.username, persisted)

                # Choose subset of targets within min/max
                min_c = agg.options.follow_min_count
                max_c = agg.options.follow_max_count
                count = random.randint(min_c, max_c)
                chosen = random.sample(agg.targets, count) if agg.targets and count > 0 and len(agg.targets) >= count else (agg.targets or [])

                local_success = 0
                for t in chosen:
                    ok, resolved_user_id, updated = service.follow_target(
                        account={"username": at.account.username, "password": at.account.password, "tfa_secret": at.account.tfa_secret, "email": at.account.email_username, "email_password": at.account.email_password},
                        target_username=t.username,
                        target_user_id=None,
                        device_settings=device_settings,
                        session_settings=persisted,
                        proxy=(at.account.proxy.model_dump(by_alias=True) if at.account.proxy else None),
                        on_log=lambda m: asyncio.create_task(ui.update_account_status_generic('follow', at.account_task_id, log_append=m + "\n")),
                    )
                    if ok:
                        local_success += 1
                if local_success > 0:
                    success += 1
                    await ui.update_account_status_generic('follow', at.account_task_id, status="COMPLETED")
                else:
                    fail += 1
                    await ui.update_account_status_generic('follow', at.account_task_id, status="FAILED")
            except Exception as e:
                fail += 1
                await ui.update_account_status_generic('follow', at.account_task_id, status="FAILED", log_append=f"exc: {e}\n")

    await asyncio.gather(*[_process(at) for at in agg.accounts])
    await ui.update_task_status_generic('follow', task_id, status=("COMPLETED" if fail == 0 else ("FAILED" if success == 0 else "COMPLETED")))
    return success, fail 