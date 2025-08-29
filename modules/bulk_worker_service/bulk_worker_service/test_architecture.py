import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from bulk_worker_service.interfaces import (
    IJobManager, ITaskRunner, ITaskRunnerFactory, 
    IMetricsCollector, IJobRepository
)
from bulk_worker_service.services import (
    JobManager, InMemoryJobRepository, SimpleMetricsCollector
)
from bulk_worker_service.factories import TaskRunnerFactory, BaseTaskRunner
from bulk_worker_service.orchestrator_v2 import WorkerOrchestrator
from bulk_worker_service.container import DIContainer, get_container, reset_container
from bulk_worker_service.domain import JobStatus, StartOptions
from bulk_worker_service.exceptions import (
    JobNotFoundError, InvalidTaskTypeError, JobExecutionError
)


@pytest.fixture
def mock_ui_client_factory():
    """Mock UI client factory for testing."""
    factory = Mock()
    ui_client = AsyncMock()
    ui_client.aclose = AsyncMock()
    factory.create_client.return_value = ui_client
    return factory


@pytest.fixture
def mock_task_runner():
    """Mock task runner for testing."""
    runner = Mock(spec=ITaskRunner)
    runner.task_type = "test_task"
    runner.run = AsyncMock(return_value=(5, 2))  # success, failure
    return runner


@pytest.fixture
def mock_task_runner_factory(mock_task_runner):
    """Mock task runner factory for testing."""
    factory = Mock(spec=ITaskRunnerFactory)
    factory.create_runner.return_value = mock_task_runner
    return factory


@pytest.fixture
def repository():
    """Create in-memory repository for testing."""
    return InMemoryJobRepository()


@pytest.fixture
def metrics_collector():
    """Create metrics collector for testing."""
    return SimpleMetricsCollector()


@pytest.fixture
async def job_manager(repository, metrics_collector, mock_ui_client_factory):
    """Create job manager for testing."""
    return JobManager(repository, metrics_collector, mock_ui_client_factory)


@pytest.fixture
async def orchestrator(job_manager, mock_task_runner_factory, metrics_collector):
    """Create orchestrator for testing."""
    return WorkerOrchestrator(job_manager, mock_task_runner_factory, metrics_collector)


class TestInMemoryJobRepository:
    """Test in-memory job repository implementation."""
    
    @pytest.mark.asyncio
    async def test_save_and_get_job(self, repository):
        job_id = "test-job-1"
        job_data = {
            "task_id": 123,
            "task_type": "test_task",
            "status": "PENDING"
        }
        
        await repository.save_job(job_id, job_data)
        retrieved = await repository.get_job(job_id)
        
        assert retrieved is not None
        assert retrieved["job_id"] == job_id
        assert retrieved["task_id"] == 123
        assert retrieved["task_type"] == "test_task"
        assert retrieved["status"] == "PENDING"
    
    @pytest.mark.asyncio
    async def test_update_job(self, repository):
        job_id = "test-job-2"
        initial_data = {"task_id": 456, "task_type": "test_task", "status": "PENDING"}
        
        await repository.save_job(job_id, initial_data)
        await repository.update_job(job_id, {"status": "RUNNING", "successful_accounts": 3})
        
        updated = await repository.get_job(job_id)
        assert updated["status"] == "RUNNING"
        assert updated["successful_accounts"] == 3
    
    @pytest.mark.asyncio
    async def test_delete_job(self, repository):
        job_id = "test-job-3"
        job_data = {"task_id": 789, "task_type": "test_task"}
        
        await repository.save_job(job_id, job_data)
        assert await repository.get_job(job_id) is not None
        
        deleted = await repository.delete_job(job_id)
        assert deleted is True
        assert await repository.get_job(job_id) is None
    
    @pytest.mark.asyncio
    async def test_list_jobs(self, repository):
        jobs = [
            ("job-1", {"task_id": 1, "task_type": "task1"}),
            ("job-2", {"task_id": 2, "task_type": "task2"}),
            ("job-3", {"task_id": 3, "task_type": "task3"})
        ]
        
        for job_id, job_data in jobs:
            await repository.save_job(job_id, job_data)
        
        all_jobs = await repository.list_jobs()
        assert len(all_jobs) == 3
        
        job_ids = [job["job_id"] for job in all_jobs if job]
        assert "job-1" in job_ids
        assert "job-2" in job_ids
        assert "job-3" in job_ids


class TestSimpleMetricsCollector:
    """Test simple metrics collector implementation."""
    
    @pytest.mark.asyncio
    async def test_record_job_start(self, metrics_collector):
        await metrics_collector.record_job_start("job-1", "bulk_upload")
        
        metrics = await metrics_collector.get_metrics()
        assert metrics["total_jobs"] == 1
        assert metrics["jobs_by_type"]["bulk_upload"] == 1
    
    @pytest.mark.asyncio
    async def test_record_job_complete(self, metrics_collector):
        await metrics_collector.record_job_complete("job-1", 5, 2)
        
        metrics = await metrics_collector.get_metrics()
        assert metrics["completed_jobs"] == 1
        assert metrics["total_accounts_processed"] == 7
        assert metrics["total_uploads_success"] == 5
        assert metrics["total_uploads_failed"] == 2
    
    @pytest.mark.asyncio
    async def test_record_job_error(self, metrics_collector):
        await metrics_collector.record_job_error("job-1", "Test error")
        
        metrics = await metrics_collector.get_metrics()
        assert metrics["failed_jobs"] == 1


class TestJobManager:
    """Test job manager implementation."""
    
    @pytest.mark.asyncio
    async def test_create_job(self, job_manager):
        job_id = await job_manager.create_job(task_id=123)
        
        assert job_id is not None
        assert isinstance(job_id, str)
        
        status = await job_manager.get_job_status(job_id)
        assert status is not None
        assert status.task_id == 123
        assert status.status == "PENDING"
    
    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, job_manager):
        status = await job_manager.get_job_status("non-existent-job")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_list_jobs(self, job_manager):
        job_ids = []
        for i in range(3):
            job_id = await job_manager.create_job(task_id=100 + i)
            job_ids.append(job_id)
        
        jobs = await job_manager.list_jobs()
        assert len(jobs) == 3
        
        retrieved_job_ids = [job.job_id for job in jobs]
        for job_id in job_ids:
            assert job_id in retrieved_job_ids
    
    @pytest.mark.asyncio
    async def test_stop_job(self, job_manager):
        job_id = await job_manager.create_job(task_id=456)
        
        # Update to running status first
        await job_manager.update_job_progress(job_id, {"status": "RUNNING"})
        
        stopped = await job_manager.stop_job(job_id)
        assert stopped is True
        
        status = await job_manager.get_job_status(job_id)
        assert status.status == "CANCELLED"
    
    @pytest.mark.asyncio
    async def test_delete_job(self, job_manager):
        job_id = await job_manager.create_job(task_id=789)
        
        deleted = await job_manager.delete_job(job_id)
        assert deleted is True
        
        status = await job_manager.get_job_status(job_id)
        assert status is None


class TestTaskRunnerFactory:
    """Test task runner factory implementation."""
    
    def test_create_runner_valid_type(self, mock_ui_client_factory):
        factory = TaskRunnerFactory(mock_ui_client_factory)
        
        runner = factory.create_runner("warmup")
        assert runner is not None
        assert runner.task_type == "warmup"
    
    def test_create_runner_invalid_type(self, mock_ui_client_factory):
        factory = TaskRunnerFactory(mock_ui_client_factory)
        
        with pytest.raises(ValueError, match="Unknown task type"):
            factory.create_runner("invalid_type")
    
    def test_register_runner(self, mock_ui_client_factory):
        factory = TaskRunnerFactory(mock_ui_client_factory)
        
        class CustomRunner(BaseTaskRunner):
            @property
            def task_type(self) -> str:
                return "custom_task"
            
            async def _execute_task(self, ui_client, task_id, options):
                return 1, 0
        
        factory.register_runner("custom_task", CustomRunner)
        
        runner = factory.create_runner("custom_task")
        assert runner.task_type == "custom_task"
    
    def test_get_supported_types(self, mock_ui_client_factory):
        factory = TaskRunnerFactory(mock_ui_client_factory)
        
        types = factory.get_supported_types()
        assert "bulk_upload" in types
        assert "warmup" in types
        assert "avatar" in types
        assert "bio" in types
        assert "follow" in types


class TestWorkerOrchestrator:
    """Test worker orchestrator implementation."""
    
    @pytest.mark.asyncio
    async def test_start_task_success(self, orchestrator, mock_task_runner):
        job_id = await orchestrator.start_task("test_task", 123)
        
        assert job_id is not None
        
        # Wait a bit for task to complete
        await asyncio.sleep(0.1)
        
        status = await orchestrator.get_job_status(job_id)
        assert status is not None
        assert status.task_id == 123
    
    @pytest.mark.asyncio
    async def test_start_task_invalid_type(self, orchestrator, mock_task_runner_factory):
        mock_task_runner_factory.create_runner.side_effect = ValueError("Unknown task type")
        
        with pytest.raises(InvalidTaskTypeError):
            await orchestrator.start_task("invalid_type", 123)
    
    @pytest.mark.asyncio
    async def test_stop_job(self, orchestrator):
        job_id = await orchestrator.start_task("test_task", 123)
        
        stopped = await orchestrator.stop_job(job_id)
        assert stopped is True
    
    @pytest.mark.asyncio
    async def test_delete_job(self, orchestrator):
        job_id = await orchestrator.start_task("test_task", 123)
        
        deleted = await orchestrator.delete_job(job_id)
        assert deleted is True
        
        status = await orchestrator.get_job_status(job_id)
        assert status is None
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, orchestrator):
        metrics = await orchestrator.get_metrics()
        
        assert "total_jobs" in metrics
        assert "running_jobs_count" in metrics
        assert "running_job_ids" in metrics


class TestDIContainer:
    """Test dependency injection container."""
    
    def setup_method(self):
        """Reset container before each test."""
        reset_container()
    
    def test_auto_wire_repository(self):
        container = DIContainer()
        repository = container.get(IJobRepository)
        
        assert isinstance(repository, InMemoryJobRepository)
    
    def test_auto_wire_metrics_collector(self):
        container = DIContainer()
        metrics = container.get(IMetricsCollector)
        
        assert isinstance(metrics, SimpleMetricsCollector)
    
    def test_auto_wire_task_runner_factory(self):
        container = DIContainer()
        factory = container.get(ITaskRunnerFactory)
        
        assert isinstance(factory, TaskRunnerFactory)
    
    def test_auto_wire_job_manager(self):
        container = DIContainer()
        manager = container.get(IJobManager)
        
        assert isinstance(manager, JobManager)
    
    def test_auto_wire_orchestrator(self):
        container = DIContainer()
        orchestrator = container.get(WorkerOrchestrator)
        
        assert isinstance(orchestrator, WorkerOrchestrator)
    
    def test_register_singleton(self):
        container = DIContainer()
        custom_repo = Mock(spec=IJobRepository)
        
        container.register_singleton(IJobRepository, custom_repo)
        
        retrieved = container.get(IJobRepository)
        assert retrieved is custom_repo
    
    def test_register_factory(self):
        container = DIContainer()
        custom_metrics = Mock(spec=IMetricsCollector)
        
        container.register_factory(IMetricsCollector, lambda: custom_metrics)
        
        retrieved = container.get(IMetricsCollector)
        assert retrieved is custom_metrics
    
    def test_unknown_type_raises_error(self):
        container = DIContainer()
        
        with pytest.raises(ValueError, match="Cannot auto-wire type"):
            container.get(str)  # Random type not supported


class TestStartOptions:
    """Test start options validation and usage."""
    
    def test_start_options_defaults(self):
        options = StartOptions()
        
        assert options.concurrency is None
        assert options.headless is None
        assert options.visible is None
        assert options.batch_index is None
        assert options.batch_count is None
        assert options.upload_method is None
    
    def test_start_options_with_values(self):
        options = StartOptions(
            concurrency=4,
            headless=True,
            visible=False,
            batch_index=2,
            batch_count=5,
            upload_method="playwright"
        )
        
        assert options.concurrency == 4
        assert options.headless is True
        assert options.visible is False
        assert options.batch_index == 2
        assert options.batch_count == 5
        assert options.upload_method == "playwright"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])