from __future__ import annotations
import asyncio
import uuid
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any, Tuple

from .interfaces import (
    IJobManager, ITaskRunner, ITaskRunnerFactory, 
    IUiClientFactory, IMetricsCollector, IJobRepository
)
from .domain import JobStatus, StartOptions
from .ui_client import UiClient


@dataclass
class JobData:
    """Internal job data structure."""
    job_id: str
    task_id: Optional[int]
    task_type: str
    status: str = "PENDING"
    successful_accounts: int = 0
    failed_accounts: int = 0
    total_uploaded: int = 0
    total_failed_uploads: int = 0
    message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    cancel_token: Optional[asyncio.Event] = field(default_factory=lambda: asyncio.Event())


class InMemoryJobRepository(IJobRepository):
    """In-memory implementation of job repository (KISS principle)."""
    
    def __init__(self):
        self._jobs: Dict[str, JobData] = {}
        self._lock = asyncio.Lock()
    
    async def save_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].updated_at = datetime.now()
                for key, value in job_data.items():
                    if hasattr(self._jobs[job_id], key):
                        setattr(self._jobs[job_id], key, value)
            else:
                self._jobs[job_id] = JobData(job_id=job_id, **job_data)
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                return {
                    'job_id': job.job_id,
                    'task_id': job.task_id,
                    'task_type': job.task_type,
                    'status': job.status,
                    'successful_accounts': job.successful_accounts,
                    'failed_accounts': job.failed_accounts,
                    'total_uploaded': job.total_uploaded,
                    'total_failed_uploads': job.total_failed_uploads,
                    'message': job.message,
                    'created_at': job.created_at,
                    'updated_at': job.updated_at
                }
            return None
    
    async def update_job(self, job_id: str, updates: Dict[str, Any]) -> None:
        await self.save_job(job_id, updates)
    
    async def delete_job(self, job_id: str) -> bool:
        async with self._lock:
            if job_id in self._jobs:
                # Cancel the job if it's running
                job = self._jobs[job_id]
                if job.cancel_token:
                    job.cancel_token.set()
                del self._jobs[job_id]
                return True
            return False
    
    async def list_jobs(self) -> List[Dict[str, Any]]:
        async with self._lock:
            return [await self.get_job(job_id) for job_id in self._jobs.keys()]


class SimpleMetricsCollector(IMetricsCollector):
    """Simple metrics collector implementation."""
    
    def __init__(self):
        self._metrics = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'total_accounts_processed': 0,
            'total_uploads_success': 0,
            'total_uploads_failed': 0,
            'jobs_by_type': {},
            'last_updated': datetime.now()
        }
        self._lock = asyncio.Lock()
    
    async def record_job_start(self, job_id: str, task_type: str) -> None:
        async with self._lock:
            self._metrics['total_jobs'] += 1
            if task_type not in self._metrics['jobs_by_type']:
                self._metrics['jobs_by_type'][task_type] = 0
            self._metrics['jobs_by_type'][task_type] += 1
            self._metrics['last_updated'] = datetime.now()
    
    async def record_job_complete(self, job_id: str, success_count: int, failure_count: int) -> None:
        async with self._lock:
            self._metrics['completed_jobs'] += 1
            self._metrics['total_accounts_processed'] += success_count + failure_count
            self._metrics['total_uploads_success'] += success_count
            self._metrics['total_uploads_failed'] += failure_count
            self._metrics['last_updated'] = datetime.now()
    
    async def record_job_error(self, job_id: str, error: str) -> None:
        async with self._lock:
            self._metrics['failed_jobs'] += 1
            self._metrics['last_updated'] = datetime.now()
    
    async def get_metrics(self) -> Dict[str, Any]:
        async with self._lock:
            return self._metrics.copy()


class DefaultUiClientFactory(IUiClientFactory):
    """Default UI client factory implementation."""
    
    def create_client(self, base_url: Optional[str] = None, token: Optional[str] = None) -> UiClient:
        return UiClient(base_url=base_url, token=token)


class JobManager(IJobManager):
    """Main job manager implementation following SOLID principles."""
    
    def __init__(
        self, 
        repository: IJobRepository,
        metrics_collector: IMetricsCollector,
        ui_client_factory: IUiClientFactory
    ):
        self._repository = repository
        self._metrics = metrics_collector
        self._ui_client_factory = ui_client_factory
    
    async def create_job(self, task_id: Optional[int]) -> str:
        job_id = str(uuid.uuid4())
        await self._repository.save_job(job_id, {
            'task_id': task_id,
            'task_type': 'unknown',  # Will be updated when task starts
            'status': 'PENDING'
        })
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        job_data = await self._repository.get_job(job_id)
        if job_data:
            return JobStatus(
                job_id=job_data['job_id'],
                task_id=job_data['task_id'],
                status=job_data['status'],  # type: ignore[arg-type]
                successful_accounts=job_data['successful_accounts'],
                failed_accounts=job_data['failed_accounts'],
                total_uploaded=job_data['total_uploaded'],
                total_failed_uploads=job_data['total_failed_uploads'],
                message=job_data['message']
            )
        return None
    
    async def list_jobs(self) -> List[JobStatus]:
        jobs_data = await self._repository.list_jobs()
        return [
            JobStatus(
                job_id=job['job_id'],
                task_id=job['task_id'],
                status=job['status'],  # type: ignore[arg-type]
                successful_accounts=job['successful_accounts'],
                failed_accounts=job['failed_accounts'],
                total_uploaded=job['total_uploaded'],
                total_failed_uploads=job['total_failed_uploads'],
                message=job['message']
            )
            for job in jobs_data if job
        ]
    
    async def stop_job(self, job_id: str) -> bool:
        job_data = await self._repository.get_job(job_id)
        if job_data and job_data['status'] == 'RUNNING':
            await self._repository.update_job(job_id, {'status': 'CANCELLED'})
            return True
        return False
    
    async def delete_job(self, job_id: str) -> bool:
        return await self._repository.delete_job(job_id)
    
    async def get_metrics(self) -> Dict[str, Any]:
        return await self._metrics.get_metrics()
    
    async def update_job_progress(self, job_id: str, updates: Dict[str, Any]) -> None:
        """Update job progress with new metrics."""
        await self._repository.update_job(job_id, updates)