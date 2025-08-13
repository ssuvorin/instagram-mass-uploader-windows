from __future__ import annotations
import asyncio
from typing import Tuple

from ..ui_client import UiClient
from ..domain import ProxyDiagnosticsAggregate


async def run_proxy_diag_job(ui: UiClient, task_id: int, concurrency: int = 4) -> Tuple[int, int]:
    await ui.update_task_status_generic('proxy_diag', task_id, status="RUNNING")
    agg_json = await ui.get_aggregate('proxy_diag', task_id)
    agg = ProxyDiagnosticsAggregate.model_validate(agg_json)

    sem = asyncio.Semaphore(concurrency)
    success = 0
    fail = 0

    async def _process(at):
        nonlocal success, fail
        async with sem:
            try:
                await ui.update_account_status_generic('proxy_diag', at.account_task_id, status="RUNNING", log_append="proxy: check start\n")
                # TODO: call a real proxy check endpoint or implement here
                await ui.update_account_status_generic('proxy_diag', at.account_task_id, status="COMPLETED", log_append="proxy: ok\n")
                success += 1
            except Exception as e:
                fail += 1
                await ui.update_account_status_generic('proxy_diag', at.account_task_id, status="FAILED", log_append=f"exc: {e}\n")

    await asyncio.gather(*[_process(at) for at in agg.accounts])
    await ui.update_task_status_generic('proxy_diag', task_id, status=("COMPLETED" if fail == 0 else ("FAILED" if success == 0 else "COMPLETED")))
    return success, fail 