from __future__ import annotations
from typing import Dict, Type, Optional, Tuple

from .interfaces import ITaskRunner, ITaskRunnerFactory, IUiClientFactory
from .domain import StartOptions
from .ui_client import UiClient
from .config import settings

# Import all runner functions
from .runners.warmup_runner import run_warmup_job
from .runners.avatar_runner import run_avatar_job
from .runners.bio_runner import run_bio_job
from .runners.follow_runner import run_follow_job
from .runners.proxy_diag_runner import run_proxy_diag_job
from .runners.media_uniq_runner import run_media_uniq_job
from .runners.cookie_robot_runner import run_cookie_robot_job
from .runners.account_management_runner import (
    run_account_creation_job,
    run_account_import_job,
    run_bulk_proxy_change_job,
    run_dolphin_profile_creation_job
)


class BaseTaskRunner(ITaskRunner):
    """Base implementation for task runners (Template Method pattern)."""
    
    def __init__(self, ui_client_factory: IUiClientFactory):
        self._ui_client_factory = ui_client_factory
    
    async def run(self, job_id: str, task_id: int, options: Optional[StartOptions] = None) -> Tuple[int, int]:
        """Template method for running tasks."""
        ui_client = self._ui_client_factory.create_client()
        try:
            return await self._execute_task(ui_client, task_id, options)
        finally:
            await ui_client.aclose()
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        """Abstract method to be implemented by concrete runners."""
        raise NotImplementedError
    
    @property
    def task_type(self) -> str:
        """Return the task type this runner handles."""
        raise NotImplementedError


class BulkUploadTaskRunner(BaseTaskRunner):
    """Runner for bulk upload tasks."""
    
    @property
    def task_type(self) -> str:
        return "bulk_upload"
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        # Import orchestrator functionality for bulk upload
        from .orchestrator import BulkUploadOrchestrator
        orchestrator = BulkUploadOrchestrator()
        
        # Get aggregate data
        agg = await ui_client.get_bulk_task_aggregate(task_id)
        
        # Create temporary job for execution
        temp_job_id = await orchestrator.start(agg, options)
        
        # Wait for completion and return results
        # This is a simplified implementation - in production you'd want proper status tracking
        import asyncio
        await asyncio.sleep(1)  # Allow job to start
        
        # Poll for completion
        while True:
            status = orchestrator.get_job_status(temp_job_id)
            if status and status.status in ['COMPLETED', 'FAILED']:
                return status.successful_accounts, status.failed_accounts
            await asyncio.sleep(5)


class WarmupTaskRunner(BaseTaskRunner):
    """Runner for warmup tasks."""
    
    @property
    def task_type(self) -> str:
        return "warmup"
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        concurrency = options.concurrency if options and options.concurrency else settings.concurrency_limit
        return await run_warmup_job(ui_client, task_id, concurrency)


class AvatarTaskRunner(BaseTaskRunner):
    """Runner for avatar change tasks."""
    
    @property
    def task_type(self) -> str:
        return "avatar"
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        concurrency = options.concurrency if options and options.concurrency else settings.concurrency_limit
        return await run_avatar_job(ui_client, task_id, concurrency)


class BioTaskRunner(BaseTaskRunner):
    """Runner for bio link change tasks."""
    
    @property
    def task_type(self) -> str:
        return "bio"
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        concurrency = options.concurrency if options and options.concurrency else settings.concurrency_limit
        return await run_bio_job(ui_client, task_id, concurrency)


class FollowTaskRunner(BaseTaskRunner):
    """Runner for follow tasks."""
    
    @property
    def task_type(self) -> str:
        return "follow"
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        concurrency = options.concurrency if options and options.concurrency else settings.concurrency_limit
        return await run_follow_job(ui_client, task_id, concurrency)


class ProxyDiagTaskRunner(BaseTaskRunner):
    """Runner for proxy diagnostics tasks."""
    
    @property
    def task_type(self) -> str:
        return "proxy_diag"
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        concurrency = options.concurrency if options and options.concurrency else 4
        return await run_proxy_diag_job(ui_client, task_id, concurrency)


class MediaUniqTaskRunner(BaseTaskRunner):
    """Runner for media uniquifier tasks."""
    
    @property
    def task_type(self) -> str:
        return "media_uniq"
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        return await run_media_uniq_job(ui_client, task_id)


class CookieRobotTaskRunner(BaseTaskRunner):
    """Runner for cookie robot tasks."""
    
    @property
    def task_type(self) -> str:
        return "cookie_robot"
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        concurrency = options.concurrency if options and options.concurrency else 2
        return await run_cookie_robot_job(ui_client, task_id, concurrency)


class BulkLoginTaskRunner(BaseTaskRunner):
    """Runner for bulk login tasks."""
    
    @property
    def task_type(self) -> str:
        return "bulk_login"
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        # Placeholder implementation - would need actual bulk login logic
        await ui_client.update_task_status_generic('bulk_login', task_id, status="RUNNING")
        # TODO: Implement actual bulk login logic
        await ui_client.update_task_status_generic('bulk_login', task_id, status="COMPLETED")
        return 1, 0  # Placeholder return


class AccountCreationTaskRunner(BaseTaskRunner):
    """Runner for account creation tasks."""
    
    @property
    def task_type(self) -> str:
        return "account_creation"
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        # This would receive account data from task aggregate
        accounts_data = []  # TODO: Get from task aggregate
        return await run_account_creation_job(ui_client, accounts_data)


class AccountImportTaskRunner(BaseTaskRunner):
    """Runner for account import tasks."""
    
    @property
    def task_type(self) -> str:
        return "account_import"
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        # This would receive account data from task aggregate
        accounts_data = []  # TODO: Get from task aggregate
        return await run_account_import_job(ui_client, accounts_data)


class BulkProxyChangeTaskRunner(BaseTaskRunner):
    """Runner for bulk proxy change tasks."""
    
    @property
    def task_type(self) -> str:
        return "bulk_proxy_change"
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        # This would receive account IDs and proxy ID from task aggregate
        account_ids = []  # TODO: Get from task aggregate
        proxy_id = None  # TODO: Get from task aggregate
        return await run_bulk_proxy_change_job(ui_client, account_ids, proxy_id)


class DolphinProfileCreationTaskRunner(BaseTaskRunner):
    """Runner for Dolphin profile creation tasks."""
    
    @property
    def task_type(self) -> str:
        return "dolphin_profile_creation"
    
    async def _execute_task(self, ui_client: UiClient, task_id: int, options: Optional[StartOptions]) -> Tuple[int, int]:
        # This would receive account IDs from task aggregate
        account_ids = []  # TODO: Get from task aggregate
        return await run_dolphin_profile_creation_job(ui_client, account_ids)


class TaskRunnerFactory(ITaskRunnerFactory):
    """Factory for creating task runners (Factory pattern)."""
    
    def __init__(self, ui_client_factory: IUiClientFactory):
        self._ui_client_factory = ui_client_factory
        self._runners: Dict[str, Type[ITaskRunner]] = {
            'bulk_upload': BulkUploadTaskRunner,
            'bulk_login': BulkLoginTaskRunner,
            'warmup': WarmupTaskRunner,
            'avatar': AvatarTaskRunner,
            'bio': BioTaskRunner,
            'follow': FollowTaskRunner,
            'proxy_diag': ProxyDiagTaskRunner,
            'media_uniq': MediaUniqTaskRunner,
            'cookie_robot': CookieRobotTaskRunner,
            # New task types
            'account_creation': AccountCreationTaskRunner,
            'account_import': AccountImportTaskRunner,
            'bulk_proxy_change': BulkProxyChangeTaskRunner,
            'dolphin_profile_creation': DolphinProfileCreationTaskRunner,
        }
    
    def create_runner(self, task_type: str) -> ITaskRunner:
        """Create appropriate runner for task type."""
        runner_class = self._runners.get(task_type)
        if not runner_class:
            raise ValueError(f"Unknown task type: {task_type}")
        
        return runner_class(self._ui_client_factory)
    
    def register_runner(self, task_type: str, runner_class: Type[ITaskRunner]) -> None:
        """Register a new runner type (Open/Closed Principle)."""
        self._runners[task_type] = runner_class
    
    def get_supported_types(self) -> list[str]:
        """Get list of supported task types."""
        return list(self._runners.keys())