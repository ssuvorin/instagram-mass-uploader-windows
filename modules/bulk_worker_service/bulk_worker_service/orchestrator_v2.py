from __future__ import annotations
import asyncio
from typing import Optional, Dict, Any

from .interfaces import IJobManager, ITaskRunnerFactory, IMetricsCollector
from .domain import StartOptions, JobStatus
from .exceptions import (
    JobNotFoundError, InvalidTaskTypeError, JobExecutionError,
    ErrorHandler, handle_exceptions
)


class WorkerOrchestrator:
    """
    Main orchestrator class following SOLID principles:
    - Single Responsibility: Coordinates job execution
    - Open/Closed: Extensible via factory pattern
    - Liskov Substitution: Uses interfaces for dependencies
    - Interface Segregation: Uses specific interfaces
    - Dependency Inversion: Depends on abstractions
    """
    
    def __init__(
        self,
        job_manager: IJobManager,
        task_runner_factory: ITaskRunnerFactory,
        metrics_collector: IMetricsCollector
    ):
        self._job_manager = job_manager
        self._task_runner_factory = task_runner_factory
        self._metrics = metrics_collector
        self._running_jobs: Dict[str, asyncio.Task] = {}
    
    @handle_exceptions
    async def start_task(
        self, 
        task_type: str, 
        task_id: int, 
        options: Optional[StartOptions] = None
    ) -> str:
        """Start a new task execution."""
        # Validate task type
        try:
            runner = self._task_runner_factory.create_runner(task_type)
        except ValueError as e:
            raise InvalidTaskTypeError(f"Invalid task type '{task_type}': {e}")
        
        # Create job
        job_id = await self._job_manager.create_job(task_id)
        
        # Record metrics
        await self._metrics.record_job_start(job_id, task_type)
        
        # Start task execution asynchronously
        task = asyncio.create_task(
            self._execute_job(job_id, task_type, task_id, runner, options)
        )
        self._running_jobs[job_id] = task
        
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get job status."""
        return await self._job_manager.get_job_status(job_id)
    
    async def list_jobs(self) -> list[JobStatus]:
        """List all jobs."""
        return await self._job_manager.list_jobs()
    
    async def stop_job(self, job_id: str) -> bool:
        """Stop a running job."""
        # Cancel the task if it's running
        if job_id in self._running_jobs:
            task = self._running_jobs[job_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._running_jobs[job_id]
        
        # Update job status
        return await self._job_manager.stop_job(job_id)
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job."""
        # Stop first if running
        await self.stop_job(job_id)
        
        # Delete from manager
        return await self._job_manager.delete_job(job_id)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics."""
        base_metrics = await self._metrics.get_metrics()
        
        # Add orchestrator-specific metrics
        orchestrator_metrics = {
            'running_jobs_count': len(self._running_jobs),
            'running_job_ids': list(self._running_jobs.keys())
        }
        
        return {**base_metrics, **orchestrator_metrics}
    
    @handle_exceptions
    async def _execute_job(
        self,
        job_id: str,
        task_type: str,
        task_id: int,
        runner,
        options: Optional[StartOptions]
    ) -> None:
        """Execute a job using the appropriate runner."""
        try:
            # Update job status to running
            if hasattr(self._job_manager, 'update_job_progress'):
                await self._job_manager.update_job_progress(job_id, {
                    'status': 'RUNNING',
                    'task_type': task_type
                })
            
            # Execute the task
            success_count, failure_count = await runner.run(job_id, task_id, options)
            
            # Update job with results
            if hasattr(self._job_manager, 'update_job_progress'):
                await self._job_manager.update_job_progress(job_id, {
                    'status': 'COMPLETED',
                    'successful_accounts': success_count,
                    'failed_accounts': failure_count,
                    'total_uploaded': success_count,  # Simplified mapping
                    'total_failed_uploads': failure_count
                })
            
            # Record metrics
            await self._metrics.record_job_complete(job_id, success_count, failure_count)
            
        except asyncio.CancelledError:
            # Job was cancelled
            if hasattr(self._job_manager, 'update_job_progress'):
                await self._job_manager.update_job_progress(job_id, {
                    'status': 'CANCELLED',
                    'message': 'Job was cancelled'
                })
            raise
            
        except Exception as e:
            # Handle job execution error
            error = ErrorHandler.handle_job_error(job_id, e, {
                'task_type': task_type,
                'task_id': task_id
            })
            
            # Update job status
            if hasattr(self._job_manager, 'update_job_progress'):
                await self._job_manager.update_job_progress(job_id, {
                    'status': 'FAILED',
                    'message': str(error)
                })
            
            # Record error metrics
            await self._metrics.record_job_error(job_id, str(error))
            
            raise error
        
        finally:
            # Cleanup
            if job_id in self._running_jobs:
                del self._running_jobs[job_id]
    
    # Convenience methods for specific task types (maintaining backward compatibility)
    
    async def start_bulk_upload(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start bulk upload task."""
        return await self.start_task('bulk_upload', task_id, options)
    
    async def start_bulk_login(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start bulk login task."""
        return await self.start_task('bulk_login', task_id, options)
    
    async def start_warmup(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start warmup task."""
        return await self.start_task('warmup', task_id, options)
    
    async def start_avatar(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start avatar change task."""
        return await self.start_task('avatar', task_id, options)
    
    async def start_bio(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start bio change task."""
        return await self.start_task('bio', task_id, options)
    
    async def start_follow(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start follow task."""
        return await self.start_task('follow', task_id, options)
    
    async def start_proxy_diagnostics(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start proxy diagnostics task."""
        return await self.start_task('proxy_diag', task_id, options)
    
    async def start_media_uniquification(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start media uniquification task."""
        return await self.start_task('media_uniq', task_id, options)
    
    async def start_cookie_robot(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start cookie robot task."""
        return await self.start_task('cookie_robot', task_id, options)
    
    async def start_account_creation(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start account creation task."""
        return await self.start_task('account_creation', task_id, options)
    
    async def start_account_import(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start account import task."""
        return await self.start_task('account_import', task_id, options)
    
    async def start_bulk_proxy_change(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start bulk proxy change task."""
        return await self.start_task('bulk_proxy_change', task_id, options)
    
    async def start_dolphin_profile_creation(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start Dolphin profile creation task."""
        return await self.start_task('dolphin_profile_creation', task_id, options)
    
    async def start_media_uniq(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start media uniquifier task."""
        return await self.start_task('media_uniq', task_id, options)
    
    async def start_cookie_robot(self, task_id: int, options: Optional[StartOptions] = None) -> str:
        """Start cookie robot task."""
        return await self.start_task('cookie_robot', task_id, options)