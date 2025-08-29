from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from .domain import JobStatus, StartOptions


class IJobManager(ABC):
    """Interface for job management operations (Single Responsibility Principle)."""
    
    @abstractmethod
    async def create_job(self, task_id: Optional[int]) -> str:
        """Create a new job and return job ID."""
        pass
    
    @abstractmethod
    async def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get job status by job ID."""
        pass
    
    @abstractmethod
    async def list_jobs(self) -> List[JobStatus]:
        """List all active jobs."""
        pass
    
    @abstractmethod
    async def stop_job(self, job_id: str) -> bool:
        """Stop a running job."""
        pass
    
    @abstractmethod
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job from management."""
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """Get job execution metrics."""
        pass


class ITaskRunner(ABC):
    """Interface for task execution (Single Responsibility Principle)."""
    
    @abstractmethod
    async def run(self, job_id: str, task_id: int, options: Optional[StartOptions] = None) -> Tuple[int, int]:
        """Execute task and return (success_count, failure_count)."""
        pass
    
    @property
    @abstractmethod
    def task_type(self) -> str:
        """Return the task type this runner handles."""
        pass


class ITaskRunnerFactory(ABC):
    """Factory interface for creating task runners (Open/Closed Principle)."""
    
    @abstractmethod
    def create_runner(self, task_type: str) -> ITaskRunner:
        """Create appropriate runner for task type."""
        pass
    
    @abstractmethod
    def register_runner(self, task_type: str, runner_class: type) -> None:
        """Register a new runner type."""
        pass


class IUiClientFactory(ABC):
    """Factory interface for creating UI clients (Dependency Inversion Principle)."""
    
    @abstractmethod
    def create_client(self, base_url: Optional[str] = None, token: Optional[str] = None) -> Any:
        """Create UI client instance."""
        pass


class IMetricsCollector(ABC):
    """Interface for metrics collection (Single Responsibility Principle)."""
    
    @abstractmethod
    async def record_job_start(self, job_id: str, task_type: str) -> None:
        """Record job start event."""
        pass
    
    @abstractmethod
    async def record_job_complete(self, job_id: str, success_count: int, failure_count: int) -> None:
        """Record job completion event."""
        pass
    
    @abstractmethod
    async def record_job_error(self, job_id: str, error: str) -> None:
        """Record job error event."""
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics."""
        pass


class IJobRepository(ABC):
    """Interface for job data persistence (Single Responsibility Principle)."""
    
    @abstractmethod
    async def save_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """Save job data."""
        pass
    
    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data by ID."""
        pass
    
    @abstractmethod
    async def update_job(self, job_id: str, updates: Dict[str, Any]) -> None:
        """Update job data."""
        pass
    
    @abstractmethod
    async def delete_job(self, job_id: str) -> bool:
        """Delete job data."""
        pass
    
    @abstractmethod
    async def list_jobs(self) -> List[Dict[str, Any]]:
        """List all jobs."""
        pass