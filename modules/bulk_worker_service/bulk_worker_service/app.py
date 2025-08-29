from __future__ import annotations
from fastapi import FastAPI, HTTPException, Request
import asyncio
import httpx
import signal
import logging
import time
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Initialize Django for database access
from . import django_init

from .domain import StartRequest, StartResponse, JobStatus, BulkLoginAggregate, WarmupAggregate, AvatarAggregate, BioAggregate, FollowAggregate, ProxyDiagnosticsAggregate, MediaUniqAggregate, CookieRobotAggregate
from .orchestrator import BulkUploadOrchestrator  # Keep for backward compatibility
from .orchestrator_v2 import WorkerOrchestrator
from .container import get_orchestrator, configure_container
from .config import settings
from .exceptions import WorkerServiceError, JobNotFoundError, InvalidTaskTypeError
from .production_fixes import (
    RobustHttpClient, get_resource_monitor, get_health_checker, 
    get_shutdown_handler, get_task_lock_manager
)
from .rate_limiter import create_rate_limiter
from .metrics import get_metrics, track_async_execution_time
from .database import initialize_database_pools, close_database_pools, get_pool_stats

logger = logging.getLogger(__name__)

# Global state
_orchestrator_v2 = None
_orchestrator = None
_heartbeat_task = None
_http_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with production-ready setup."""
    global _orchestrator_v2, _orchestrator, _heartbeat_task, _http_client
    
    # Startup
    logger.info("Starting Bulk Worker Service...")
    
    # Initialize database pools if database URL is configured
    if hasattr(settings, 'database_url') and settings.database_url:
        try:
            await initialize_database_pools(
                database_url=settings.database_url,
                min_connections=getattr(settings, 'db_min_connections', 5),
                max_connections=getattr(settings, 'db_max_connections', 20)
            )
            logger.info("Database connection pools initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize database pools: {e}")
    
    # Configure dependency injection
    configure_container()
    
    # Get orchestrator instances
    _orchestrator_v2 = get_orchestrator()
    _orchestrator = BulkUploadOrchestrator()
    
    # Initialize HTTP client for heartbeat
    if settings.ui_api_base and settings.ui_api_token:
        _http_client = RobustHttpClient(
            base_url=settings.ui_api_base,
            token=settings.ui_api_token,
            timeout=settings.request_timeout_secs
        )
    
    # Set up graceful shutdown handler
    shutdown_handler = get_shutdown_handler()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, requesting graceful shutdown")
        shutdown_handler.request_shutdown()
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start heartbeat task
    _heartbeat_task = asyncio.create_task(_register_and_heartbeat())
    
    # Add cleanup callbacks
    shutdown_handler.add_cleanup_callback(lambda: _http_client.close() if _http_client else None)
    shutdown_handler.add_cleanup_callback(lambda: _heartbeat_task.cancel() if _heartbeat_task else None)
    shutdown_handler.add_cleanup_callback(close_database_pools)
    
    logger.info("Bulk Worker Service started successfully")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down Bulk Worker Service...")
    
    # Request graceful shutdown
    shutdown_handler.request_shutdown()
    
    # Wait for active tasks to complete
    await shutdown_handler.wait_for_completion(timeout_seconds=300)
    
    # Execute cleanup callbacks
    await shutdown_handler.cleanup()
    
    logger.info("Bulk Worker Service shutdown complete")


app = FastAPI(
    title="Bulk Worker Service", 
    version="2.0.0",
    lifespan=lifespan
)

# Add rate limiting middleware
rate_limiter = create_rate_limiter(
    redis_url=getattr(settings, 'redis_url', None),
    default_requests=getattr(settings, 'rate_limit_requests', 100),
    default_window=getattr(settings, 'rate_limit_window', 60)
)
app.add_middleware(rate_limiter.__class__, **rate_limiter.__dict__)

# Add HTTP metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to track HTTP request metrics."""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Track metrics
        metrics = get_metrics()
        metrics.http_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration=duration
        )
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        
        # Track error metrics
        metrics = get_metrics()
        metrics.http_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=500,
            duration=duration
        )
        
        raise


@app.get("/api/v1/health")
@track_async_execution_time("health_check")
async def health() -> dict:
    """Comprehensive health check endpoint."""
    health_checker = get_health_checker()
    
    # Define external services to check
    external_services = {}
    if settings.ui_api_base:
        external_services["ui_service"] = f"{settings.ui_api_base}/api/health"
    
    # Perform full health check
    health_result = await health_checker.full_health_check(external_services)
    
    # Add database pool stats
    pool_stats = get_pool_stats()
    health_result["database_pools"] = pool_stats
    
    # Return appropriate status code
    status_code = 200 if health_result["healthy"] else 503
    
    return JSONResponse(
        content=health_result,
        status_code=status_code
    )


@app.get("/api/v1/health/simple")
async def simple_health() -> dict:
    """Simple health check for load balancers."""
    metrics = get_metrics()
    metrics.custom_counter("health_check_simple_requests")
    return {"ok": True, "status": "healthy"}


@app.get("/api/v1/jobs")
@track_async_execution_time("list_jobs")
async def list_jobs() -> list[JobStatus]:
    """List all jobs using the new orchestrator."""
    try:
        jobs = await _orchestrator_v2.list_jobs()
        get_metrics().custom_gauge("total_jobs_listed", len(jobs))
        return jobs
    except Exception as e:
        get_metrics().custom_counter("list_jobs_errors")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/jobs/{job_id}/status")
@track_async_execution_time("get_job_status")
async def job_status(job_id: str) -> JobStatus:
    """Get job status using the new orchestrator."""
    try:
        status = await _orchestrator_v2.get_job_status(job_id)
        if not status:
            get_metrics().custom_counter("job_not_found_errors")
            raise JobNotFoundError(f"Job {job_id} not found")
        return status
    except WorkerServiceError:
        raise
    except Exception as e:
        get_metrics().custom_counter("get_job_status_errors")
        raise HTTPException(status_code=500, detail=str(e))


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
    """Start bulk login task using new orchestrator."""
    shutdown_handler = get_shutdown_handler()
    
    if shutdown_handler.shutdown_requested:
        raise HTTPException(status_code=503, detail="Service is shutting down")
    
    try:
        job_id = await _orchestrator_v2.start_bulk_login(task_id)
        shutdown_handler.add_active_task(job_id)
        return StartResponse(job_id=job_id, accepted=True)
    except WorkerServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Error starting bulk login task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _register_and_heartbeat():
    """Robust worker registration and heartbeat with retry logic."""
    if not settings.ui_api_base or not settings.ui_api_token or not settings.worker_base_url:
        logger.warning("Heartbeat disabled: missing configuration")
        return
    
    if not _http_client:
        logger.error("HTTP client not initialized for heartbeat")
        return
    
    shutdown_handler = get_shutdown_handler()
    resource_monitor = get_resource_monitor()
    
    # Register worker
    try:
        await _http_client.post("/api/worker/register", json={
            "base_url": settings.worker_base_url,
            "name": settings.worker_name,
            "capacity": settings.worker_capacity,
        })
        logger.info(f"Worker {settings.worker_name} registered successfully")
    except Exception as e:
        logger.error(f"Failed to register worker: {e}")
    
    # Heartbeat loop
    while not shutdown_handler.shutdown_requested:
        try:
            # Get current resource stats
            resource_stats = resource_monitor.get_resource_stats()
            
            # Send heartbeat with resource information
            await _http_client.post("/api/worker/heartbeat", json={
                "base_url": settings.worker_base_url,
                "resource_stats": resource_stats,
                "active_tasks": len(shutdown_handler.active_tasks)
            })
            
            logger.debug(f"Heartbeat sent: {resource_stats['memory_mb']:.1f}MB memory, {resource_stats['cpu_percent']:.1f}% CPU")
            
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
        
        # Wait for next heartbeat
        await asyncio.sleep(max(10, settings.heartbeat_interval_secs))
    
    logger.info("Heartbeat task stopped due to shutdown request")


# Startup and shutdown now handled by lifespan context manager


@app.post("/api/v1/warmup/start", response_model=StartResponse)
async def start_warmup(task_id: int):
    """Start warmup task using new orchestrator."""
    shutdown_handler = get_shutdown_handler()
    
    if shutdown_handler.shutdown_requested:
        raise HTTPException(status_code=503, detail="Service is shutting down")
    
    try:
        job_id = await _orchestrator_v2.start_warmup(task_id)
        shutdown_handler.add_active_task(job_id)
        return StartResponse(job_id=job_id, accepted=True)
    except WorkerServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Error starting warmup task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/avatar/start", response_model=StartResponse)
async def start_avatar(task_id: int):
    """Start avatar task using new orchestrator."""
    shutdown_handler = get_shutdown_handler()
    
    if shutdown_handler.shutdown_requested:
        raise HTTPException(status_code=503, detail="Service is shutting down")
    
    try:
        job_id = await _orchestrator_v2.start_avatar(task_id)
        shutdown_handler.add_active_task(job_id)
        return StartResponse(job_id=job_id, accepted=True)
    except WorkerServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Error starting avatar task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/bio/start", response_model=StartResponse)
async def start_bio(task_id: int):
    """Start bio task using new orchestrator."""
    shutdown_handler = get_shutdown_handler()
    
    if shutdown_handler.shutdown_requested:
        raise HTTPException(status_code=503, detail="Service is shutting down")
    
    try:
        job_id = await _orchestrator_v2.start_bio(task_id)
        shutdown_handler.add_active_task(job_id)
        return StartResponse(job_id=job_id, accepted=True)
    except WorkerServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Error starting bio task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/follow/start", response_model=StartResponse)
async def start_follow(task_id: int):
    """Start follow task using new orchestrator."""
    shutdown_handler = get_shutdown_handler()
    
    if shutdown_handler.shutdown_requested:
        raise HTTPException(status_code=503, detail="Service is shutting down")
    
    try:
        job_id = await _orchestrator_v2.start_follow(task_id)
        shutdown_handler.add_active_task(job_id)
        return StartResponse(job_id=job_id, accepted=True)
    except WorkerServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Error starting follow task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/proxy-diagnostics/start", response_model=StartResponse)
async def start_proxy_diagnostics(task_id: int):
    """Start proxy diagnostics task using new orchestrator."""
    shutdown_handler = get_shutdown_handler()
    
    if shutdown_handler.shutdown_requested:
        raise HTTPException(status_code=503, detail="Service is shutting down")
    
    try:
        job_id = await _orchestrator_v2.start_proxy_diagnostics(task_id)
        shutdown_handler.add_active_task(job_id)
        return StartResponse(job_id=job_id, accepted=True)
    except WorkerServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Error starting proxy diagnostics task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/media-uniq/start", response_model=StartResponse)
async def start_media_uniq(task_id: int):
    """Start media uniquifier task using new orchestrator."""
    shutdown_handler = get_shutdown_handler()
    
    if shutdown_handler.shutdown_requested:
        raise HTTPException(status_code=503, detail="Service is shutting down")
    
    try:
        job_id = await _orchestrator_v2.start_media_uniq(task_id)
        shutdown_handler.add_active_task(job_id)
        return StartResponse(job_id=job_id, accepted=True)
    except WorkerServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Error starting media uniquifier task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/cookie-robot/start", response_model=StartResponse)
async def start_cookie_robot(task_id: int):
    """Start cookie robot task using new orchestrator."""
    shutdown_handler = get_shutdown_handler()
    
    if shutdown_handler.shutdown_requested:
        raise HTTPException(status_code=503, detail="Service is shutting down")
    
    try:
        job_id = await _orchestrator_v2.start_cookie_robot(task_id)
        shutdown_handler.add_active_task(job_id)
        return StartResponse(job_id=job_id, accepted=True)
    except WorkerServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Error starting cookie robot task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Job management endpoints
@app.post("/api/v1/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    """Stop a running job."""
    shutdown_handler = get_shutdown_handler()
    
    try:
        success = await _orchestrator_v2.stop_job(job_id)
        if success:
            shutdown_handler.remove_active_task(job_id)
        return {"job_id": job_id, "stopped": success}
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except WorkerServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Error stopping job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job."""
    shutdown_handler = get_shutdown_handler()
    
    try:
        success = await _orchestrator_v2.delete_job(job_id)
        if success:
            shutdown_handler.remove_active_task(job_id)
        return {"job_id": job_id, "deleted": success}
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except WorkerServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/metrics")
async def get_metrics():
    """Get comprehensive worker metrics including resource usage."""
    try:
        # Get orchestrator metrics
        orchestrator_metrics = await _orchestrator_v2.get_metrics()
        
        # Get resource metrics
        resource_monitor = get_resource_monitor()
        resource_stats = resource_monitor.get_resource_stats()
        
        # Get shutdown handler metrics
        shutdown_handler = get_shutdown_handler()
        
        # Combine all metrics
        combined_metrics = {
            **orchestrator_metrics,
            "resource_usage": resource_stats,
            "service_status": {
                "shutdown_requested": shutdown_handler.shutdown_requested,
                "active_tasks_count": len(shutdown_handler.active_tasks),
                "active_task_ids": list(shutdown_handler.active_tasks)
            }
        }
        
        return combined_metrics
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Additional production endpoints
@app.get("/api/v1/status")
async def service_status():
    """Get detailed service status for monitoring."""
    shutdown_handler = get_shutdown_handler()
    resource_monitor = get_resource_monitor()
    
    return {
        "service": "bulk_worker_service",
        "version": "2.0.0",
        "status": "shutting_down" if shutdown_handler.shutdown_requested else "running",
        "active_tasks": len(shutdown_handler.active_tasks),
        "resource_usage": resource_monitor.get_resource_stats(),
        "configuration": {
            "worker_name": settings.worker_name,
            "worker_capacity": settings.worker_capacity,
            "ui_api_configured": bool(settings.ui_api_base),
            "heartbeat_interval": settings.heartbeat_interval_secs
        }
    }


@app.get("/api/v1/locks")
async def get_active_locks():
    """Get information about active task locks."""
    lock_manager = get_task_lock_manager()
    active_locks = lock_manager.get_active_locks()
    
    return {
        "active_locks": active_locks,
        "count": len(active_locks)
    } 