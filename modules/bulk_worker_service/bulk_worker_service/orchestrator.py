from __future__ import annotations
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import random

from .config import settings
from .domain import BulkTaskAggregate, StartOptions, JobStatus
from .ui_client import UiClient
from .runner import run_account_upload
from .ig_runner import run_account_upload_with_metadata
from .domain import BulkLoginAggregate, WarmupAggregate, AvatarAggregate, BioAggregate, FollowAggregate, ProxyDiagnosticsAggregate, MediaUniqAggregate
from .instagrapi_runner import run_account_upload_instagrapi
from .runners.warmup_runner import run_warmup_job
from .runners.avatar_runner import run_avatar_job
from .runners.bio_runner import run_bio_job
from .runners.follow_runner import run_follow_job
from .runners.proxy_diag_runner import run_proxy_diag_job
from .runners.media_uniq_runner import run_media_uniq_job


@dataclass
class _Job:
    job_id: str
    task_id: Optional[int]
    status: str = "PENDING"
    successful_accounts: int = 0
    failed_accounts: int = 0
    total_uploaded: int = 0
    total_failed_uploads: int = 0
    message: Optional[str] = None


class BulkUploadOrchestrator:
    def __init__(self) -> None:
        self._jobs: Dict[str, _Job] = {}
        self._lock = asyncio.Lock()

    def _new_job(self, task_id: Optional[int]) -> _Job:
        job = _Job(job_id=str(uuid.uuid4()), task_id=task_id)
        self._jobs[job.job_id] = job
        return job

    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        return JobStatus(
            job_id=job.job_id,
            task_id=job.task_id,
            status=job.status,  # type: ignore[arg-type]
            successful_accounts=job.successful_accounts,
            failed_accounts=job.failed_accounts,
            total_uploaded=job.total_uploaded,
            total_failed_uploads=job.total_failed_uploads,
            message=job.message,
        )

    def list_jobs(self) -> List[JobStatus]:
        return [self.get_job_status(jid) for jid in self._jobs.keys() if self.get_job_status(jid)]  # type: ignore[list-item]

    async def start(self, aggregate: BulkTaskAggregate, options: Optional[StartOptions] = None) -> str:
        job = self._new_job(aggregate.id)
        asyncio.create_task(self._run(job.job_id, aggregate, options))
        return job.job_id

    async def start_pull(self, task_id: int, ui_base: Optional[str] = None, ui_token: Optional[str] = None, options: Optional[StartOptions] = None) -> str:
        job = self._new_job(task_id)
        asyncio.create_task(self._run_pull(job.job_id, task_id, ui_base, ui_token, options))
        return job.job_id

    # ===== Other tasks (pull-mode) =====
    async def start_bulk_login_pull(self, task_id: int) -> str:
        job = self._new_job(task_id)
        asyncio.create_task(self._run_bulk_login(job.job_id, task_id))
        return job.job_id

    async def start_warmup_pull(self, task_id: int) -> str:
        job = self._new_job(task_id)
        asyncio.create_task(self._run_warmup(job.job_id, task_id))
        return job.job_id

    async def start_avatar_pull(self, task_id: int) -> str:
        job = self._new_job(task_id)
        asyncio.create_task(self._run_avatar(job.job_id, task_id))
        return job.job_id

    async def start_bio_pull(self, task_id: int) -> str:
        job = self._new_job(task_id)
        asyncio.create_task(self._run_bio(job.job_id, task_id))
        return job.job_id

    async def start_follow_pull(self, task_id: int) -> str:
        job = self._new_job(task_id)
        asyncio.create_task(self._run_follow(job.job_id, task_id))
        return job.job_id

    async def start_proxy_diagnostics_pull(self, task_id: int) -> str:
        job = self._new_job(task_id)
        asyncio.create_task(self._run_proxy_diag(job.job_id, task_id))
        return job.job_id

    async def start_media_uniq_pull(self, task_id: int) -> str:
        job = self._new_job(task_id)
        asyncio.create_task(self._run_media_uniq(job.job_id, task_id))
        return job.job_id

    async def _run_pull(self, job_id: str, task_id: int, ui_base: Optional[str], ui_token: Optional[str], options: Optional[StartOptions]) -> None:
        ui = UiClient(base_url=ui_base, token=ui_token)
        try:
            await ui.update_task_status(task_id, "RUNNING")
            agg = await ui.get_bulk_task_aggregate(task_id)
            await self._run(job_id, agg, options, ui)
        except Exception as e:
            job = self._jobs[job_id]
            job.status = "FAILED"
            job.message = str(e)
            await ui.update_task_status(task_id, "FAILED", log=f"{e}")
        finally:
            await ui.aclose()

    async def _run_simple_pull(self, job_id: str, task_id: int, kind: str) -> None:
        job = self._jobs[job_id]
        job.status = "RUNNING"
        ui = UiClient()
        try:
            # Placeholder aggregate fetch endpoints per kind (to be implemented in UI later):
            # /api/{kind}/{task_id}/aggregate
            agg_endpoint = f"/api/{kind}/{task_id}/aggregate"
            resp = await ui._client.get(agg_endpoint)
            resp.raise_for_status()
            aggregate = resp.json()
            # For now, just mark as completed to keep interface stable.
            job.status = "COMPLETED"
            await ui.update_task_status(task_id, "COMPLETED", log=f"[{kind}] Completed (stub)\n")
        except Exception as e:
            job.status = "FAILED"
            job.message = str(e)
            try:
                await ui.update_task_status(task_id, "FAILED", log=f"[{kind}] {e}\n")
            except Exception:
                pass
        finally:
            await ui.aclose()

    async def _run(self, job_id: str, aggregate: BulkTaskAggregate, options: Optional[StartOptions], ui_client: Optional[UiClient] = None) -> None:
        job = self._jobs[job_id]
        job.status = "RUNNING"
        headless = options.headless if options and options.headless is not None else settings.headless
        visible = options.visible if options and options.visible is not None else settings.visible_browser
        concurrency = options.concurrency if options and options.concurrency else settings.concurrency_limit
        batch_size = settings.batch_size
        batch_index = options.batch_index if options and options.batch_index is not None else None
        batch_count = options.batch_count if options and options.batch_count is not None else None
        upload_method = (options.upload_method if options and options.upload_method is not None else settings.upload_method).lower()

        ui = ui_client or UiClient()
        try:
            await ui.update_task_status(aggregate.id, "RUNNING")
            await ui.append_task_log(aggregate.id, f"[RUNNER] Upload method: {upload_method}\n")
            # Split accounts among workers if batch routing is provided
            accounts = aggregate.accounts
            if batch_index is not None and batch_count and batch_count > 1:
                accounts = [acc for i, acc in enumerate(accounts) if (i % batch_count) == batch_index]
            # Local batching within this worker
            batches = [accounts[i:i+batch_size] for i in range(0, len(accounts), batch_size)]
            for b_idx, batch in enumerate(batches, start=1):
                semaphore = asyncio.Semaphore(concurrency)

                async def _process_account(account_task):
                    async with semaphore:
                        if upload_method == "instagrapi":
                            success, fail, _out, _err = await run_account_upload_instagrapi(
                                ui=ui,
                                task_id=aggregate.id,
                                account_task=account_task,
                                videos=aggregate.videos,
                                default_location=aggregate.default_location,
                                default_mentions_text=aggregate.default_mentions,
                                headless=headless,
                                visible=visible,
                            )
                        else:
                            success, fail, _out, _err = await run_account_upload_with_metadata(
                                ui=ui,
                                task_id=aggregate.id,
                                account_task=account_task,
                                videos=aggregate.videos,
                                default_location=aggregate.default_location,
                                default_mentions_text=aggregate.default_mentions,
                                headless=headless,
                                visible=visible,
                            )
                        job.successful_accounts += 1 if fail == 0 and success > 0 else 0
                        job.failed_accounts += 1 if success == 0 else 0
                        job.total_uploaded += success
                        job.total_failed_uploads += fail

                await asyncio.gather(*[_process_account(a) for a in batch])
                # Human-like pause between batches
                if b_idx < len(batches):
                    await ui.update_task_status(aggregate.id, "RUNNING", log=f"[BATCH] Completed {b_idx}/{len(batches)}\n")
                    await asyncio.sleep(random.randint(20, 45))

            overall_status = "COMPLETED" if job.failed_accounts == 0 else ("FAILED" if job.successful_accounts == 0 else "COMPLETED")
            job.status = overall_status
            await ui.update_task_status(aggregate.id, overall_status)
        except Exception as e:
            job.status = "FAILED"
            job.message = str(e)
            await ui.update_task_status(aggregate.id, "FAILED", log=f"{e}")
        finally:
            if not ui_client:
                await ui.aclose()

    # ===== Dedicated runners for other kinds =====
    async def _run_bulk_login(self, job_id: str, task_id: int) -> None:
        job = self._jobs[job_id]
        job.status = "RUNNING"
        ui = UiClient()
        try:
            # For now, treat bulk_login as a fast-pass that marks accounts as completed (auth-only runner can be added)
            await ui.update_task_status_generic('bulk_login', task_id, status="RUNNING")
            agg = await ui.get_aggregate('bulk_login', task_id)
            parsed = BulkLoginAggregate.model_validate(agg)
            success = 0
            fail = 0
            for at in parsed.accounts:
                await ui.update_account_status_generic('bulk_login', at.account_task_id, status="COMPLETED", log_append="login: skipped (placeholder)\n")
                success += 1
            job.successful_accounts = success
            job.failed_accounts = fail
            job.status = "COMPLETED"
            await ui.update_task_status_generic('bulk_login', task_id, status="COMPLETED")
        except Exception as e:
            job.status = "FAILED"
            job.message = str(e)
            try:
                await ui.update_task_status_generic('bulk_login', task_id, status="FAILED", log=str(e))
            except Exception:
                pass
        finally:
            await ui.aclose()

    async def _run_warmup(self, job_id: str, task_id: int) -> None:
        job = self._jobs[job_id]
        job.status = "RUNNING"
        ui = UiClient()
        try:
            success, fail = await run_warmup_job(ui, task_id, concurrency=settings.concurrency_limit)
            job.successful_accounts = success
            job.failed_accounts = fail
            job.status = "COMPLETED" if fail == 0 else ("FAILED" if success == 0 else "COMPLETED")
        except Exception as e:
            job.status = "FAILED"
            job.message = str(e)
            try:
                await ui.update_task_status_generic('warmup', task_id, status="FAILED", log=str(e))
            except Exception:
                pass
        finally:
            await ui.aclose()

    async def _run_avatar(self, job_id: str, task_id: int) -> None:
        job = self._jobs[job_id]
        job.status = "RUNNING"
        ui = UiClient()
        try:
            success, fail = await run_avatar_job(ui, task_id, concurrency=settings.concurrency_limit)
            job.successful_accounts = success
            job.failed_accounts = fail
            job.status = "COMPLETED" if fail == 0 else ("FAILED" if success == 0 else "COMPLETED")
        except Exception as e:
            job.status = "FAILED"
            job.message = str(e)
            try:
                await ui.update_task_status_generic('avatar', task_id, status="FAILED", log=str(e))
            except Exception:
                pass
        finally:
            await ui.aclose()

    async def _run_bio(self, job_id: str, task_id: int) -> None:
        job = self._jobs[job_id]
        job.status = "RUNNING"
        ui = UiClient()
        try:
            success, fail = await run_bio_job(ui, task_id, concurrency=settings.concurrency_limit)
            job.successful_accounts = success
            job.failed_accounts = fail
            job.status = "COMPLETED" if fail == 0 else ("FAILED" if success == 0 else "COMPLETED")
        except Exception as e:
            job.status = "FAILED"
            job.message = str(e)
            try:
                await ui.update_task_status_generic('bio', task_id, status="FAILED", log=str(e))
            except Exception:
                pass
        finally:
            await ui.aclose()

    async def _run_follow(self, job_id: str, task_id: int) -> None:
        job = self._jobs[job_id]
        job.status = "RUNNING"
        ui = UiClient()
        try:
            success, fail = await run_follow_job(ui, task_id, concurrency=settings.concurrency_limit)
            job.successful_accounts = success
            job.failed_accounts = fail
            job.status = "COMPLETED" if fail == 0 else ("FAILED" if success == 0 else "COMPLETED")
        except Exception as e:
            job.status = "FAILED"
            job.message = str(e)
            try:
                await ui.update_task_status_generic('follow', task_id, status="FAILED", log=str(e))
            except Exception:
                pass
        finally:
            await ui.aclose()

    async def _run_proxy_diag(self, job_id: str, task_id: int) -> None:
        job = self._jobs[job_id]
        job.status = "RUNNING"
        ui = UiClient()
        try:
            success, fail = await run_proxy_diag_job(ui, task_id, concurrency=settings.concurrency_limit)
            job.successful_accounts = success
            job.failed_accounts = fail
            job.status = "COMPLETED" if fail == 0 else ("FAILED" if success == 0 else "COMPLETED")
        except Exception as e:
            job.status = "FAILED"
            job.message = str(e)
            try:
                await ui.update_task_status_generic('proxy_diag', task_id, status="FAILED", log=str(e))
            except Exception:
                pass
        finally:
            await ui.aclose()

    async def _run_media_uniq(self, job_id: str, task_id: int) -> None:
        job = self._jobs[job_id]
        job.status = "RUNNING"
        ui = UiClient()
        try:
            success, fail = await run_media_uniq_job(ui, task_id)
            job.total_uploaded = success
            job.total_failed_uploads = fail
            job.status = "COMPLETED" if fail == 0 else ("FAILED" if success == 0 else "COMPLETED")
        except Exception as e:
            job.status = "FAILED"
            job.message = str(e)
            try:
                await ui.update_task_status_generic('media_uniq', task_id, status="FAILED", log=str(e))
            except Exception:
                pass
        finally:
            await ui.aclose() 