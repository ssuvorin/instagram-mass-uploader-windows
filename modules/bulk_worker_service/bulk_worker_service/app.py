from __future__ import annotations
from fastapi import FastAPI, HTTPException
import asyncio
import httpx
from fastapi.responses import JSONResponse

from .domain import StartRequest, StartResponse, JobStatus, BulkLoginAggregate, WarmupAggregate, AvatarAggregate, BioAggregate, FollowAggregate, ProxyDiagnosticsAggregate, MediaUniqAggregate
from .orchestrator import BulkUploadOrchestrator
from .config import settings

app = FastAPI(title="Bulk Worker Service", version="1.1.0")
_orchestrator = BulkUploadOrchestrator()
_heartbeat_task = None


@app.get("/api/v1/health")
async def health() -> dict:
    return {"ok": True}


@app.get("/api/v1/jobs")
async def list_jobs() -> list[JobStatus]:
    return _orchestrator.list_jobs()


@app.get("/api/v1/jobs/{job_id}/status")
async def job_status(job_id: str) -> JobStatus:
    status = _orchestrator.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@app.post("/api/v1/bulk-tasks/start", response_model=StartResponse)
async def start_bulk_task(req: StartRequest):
    try:
        if req.mode == "pull":
            if not req.task_id:
                raise HTTPException(status_code=400, detail="task_id is required in pull mode")
            job_id = await _orchestrator.start_pull(task_id=req.task_id, options=req.options)
            return StartResponse(job_id=job_id, accepted=True)
        else:
            if not req.aggregate:
                raise HTTPException(status_code=400, detail="aggregate is required in push mode")
            job_id = await _orchestrator.start(aggregate=req.aggregate, options=req.options)
            return StartResponse(job_id=job_id, accepted=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Placeholders for other tasks (pull-mode only to keep web untouched now) =====

@app.post("/api/v1/bulk-login/start", response_model=StartResponse)
async def start_bulk_login(task_id: int):
    try:
        job_id = await _orchestrator.start_bulk_login_pull(task_id)
        return StartResponse(job_id=job_id, accepted=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _register_and_heartbeat():
    if not settings.ui_api_base or not settings.ui_api_token or not settings.worker_base_url:
        return
    headers = {"Authorization": f"Bearer {settings.ui_api_token}", "Accept": "application/json"}
    async with httpx.AsyncClient(base_url=settings.ui_api_base, headers=headers, timeout=settings.request_timeout_secs, verify=settings.verify_ssl) as client:
        try:
            await client.post("/api/worker/register", json={
                "base_url": settings.worker_base_url,
                "name": settings.worker_name,
                "capacity": settings.worker_capacity,
            })
        except Exception:
            pass
        while True:
            try:
                await client.post("/api/worker/heartbeat", json={"base_url": settings.worker_base_url})
            except Exception:
                pass
            await asyncio.sleep(max(10, settings.heartbeat_interval_secs))


@app.on_event("startup")
async def on_startup():
    global _heartbeat_task
    _heartbeat_task = asyncio.create_task(_register_and_heartbeat())


@app.on_event("shutdown")
async def on_shutdown():
    global _heartbeat_task
    try:
        if _heartbeat_task:
            _heartbeat_task.cancel()
    except Exception:
        pass


@app.post("/api/v1/warmup/start", response_model=StartResponse)
async def start_warmup(task_id: int):
    try:
        job_id = await _orchestrator.start_warmup_pull(task_id)
        return StartResponse(job_id=job_id, accepted=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/avatar/start", response_model=StartResponse)
async def start_avatar(task_id: int):
    try:
        job_id = await _orchestrator.start_avatar_pull(task_id)
        return StartResponse(job_id=job_id, accepted=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/bio/start", response_model=StartResponse)
async def start_bio(task_id: int):
    try:
        job_id = await _orchestrator.start_bio_pull(task_id)
        return StartResponse(job_id=job_id, accepted=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/follow/start", response_model=StartResponse)
async def start_follow(task_id: int):
    try:
        job_id = await _orchestrator.start_follow_pull(task_id)
        return StartResponse(job_id=job_id, accepted=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/proxy-diagnostics/start", response_model=StartResponse)
async def start_proxy_diagnostics(task_id: int):
    try:
        job_id = await _orchestrator.start_proxy_diagnostics_pull(task_id)
        return StartResponse(job_id=job_id, accepted=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/media-uniq/start", response_model=StartResponse)
async def start_media_uniq(task_id: int):
    try:
        job_id = await _orchestrator.start_media_uniq_pull(task_id)
        return StartResponse(job_id=job_id, accepted=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 