"""Comprehensive Cookie Robot Runner for Distributed Workers

Implements browser automation for cookie management with SOLID principles.
"""

from __future__ import annotations
import os
import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple, Dict

from ..ui_client import UiClient
from ..domain import CookieRobotAggregate
from ..config import settings

# Import Dolphin automation
try:
    from uploader.async_impl.dolphin import DolphinAutomation
except ImportError:
    DolphinAutomation = None


class CookieRobotStatus(Enum):
    """Cookie robot task status enumeration"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class CookieRobotResult:
    """Result of cookie robot operation"""
    account_task_id: int
    account_username: str
    status: CookieRobotStatus
    urls_visited: int = 0
    execution_time: float = 0.0
    error_message: Optional[str] = None
    worker_id: Optional[str] = None


@dataclass
class CookieRobotMetrics:
    """Cookie robot execution metrics"""
    total_accounts: int = 0
    successful_accounts: int = 0
    failed_accounts: int = 0
    skipped_accounts: int = 0
    total_urls_visited: int = 0
    average_execution_time: float = 0.0


class IBrowserAutomation(ABC):
    """Interface for browser automation operations"""
    
    @abstractmethod
    async def visit_urls(
        self, 
        profile_id: str, 
        urls: List[str],
        options: Dict
    ) -> bool:
        """Visit list of URLs in browser"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup browser resources"""
        pass


class DolphinBrowserAutomation(IBrowserAutomation):
    """Dolphin Anty browser automation implementation"""
    
    def __init__(self):
        self.automation = None
        if DolphinAutomation:
            self.automation = DolphinAutomation()
    
    async def visit_urls(
        self, 
        profile_id: str, 
        urls: List[str],
        options: Dict
    ) -> bool:
        """Visit URLs using Dolphin browser"""
        if not self.automation:
            raise Exception("Dolphin automation not available")
        
        try:
            headless = options.get('headless', True)
            imageless = options.get('imageless', False)
            
            for url in urls:
                await self.automation.visit_url(
                    profile_id=profile_id,
                    url=url,
                    headless=headless,
                    imageless=imageless
                )
                # Small delay between visits
                await asyncio.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"Error visiting URLs: {str(e)}")
            return False
    
    async def cleanup(self) -> None:
        """Cleanup automation resources"""
        if self.automation:
            try:
                await self.automation.close()
            except Exception as e:
                print(f"Error during cleanup: {str(e)}")


class CookieRobotOrchestrator:
    """
    Main orchestrator for cookie robot operations
    Follows Single Responsibility and Dependency Inversion principles
    """
    
    def __init__(
        self,
        browser_automation: IBrowserAutomation,
        worker_id: str,
        concurrency: int = 2
    ):
        self._browser = browser_automation
        self._worker_id = worker_id
        self._concurrency = concurrency
        self._metrics = CookieRobotMetrics()
    
    async def execute_cookie_robot_tasks(
        self, 
        account_tasks: List,
        urls: List[str],
        options: Dict,
        progress_callback: Optional[callable] = None
    ) -> List[CookieRobotResult]:
        """Execute cookie robot tasks for multiple accounts"""
        semaphore = asyncio.Semaphore(self._concurrency)
        
        async def _process_account(account_task) -> CookieRobotResult:
            async with semaphore:
                return await self._process_single_account(
                    account_task, urls, options
                )
        
        # Execute all tasks concurrently
        tasks = [_process_account(at) for at in account_tasks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(CookieRobotResult(
                    account_task_id=account_tasks[i].account_task_id,
                    account_username=account_tasks[i].account.get('username', 'unknown'),
                    status=CookieRobotStatus.FAILED,
                    error_message=str(result),
                    worker_id=self._worker_id
                ))
            else:
                final_results.append(result)
        
        # Update metrics
        self._update_metrics(final_results)
        
        # Call progress callback if provided
        if progress_callback:
            await progress_callback(len(final_results), len(account_tasks), self._metrics)
        
        return final_results
    
    async def _process_single_account(
        self, 
        account_task,
        urls: List[str],
        options: Dict
    ) -> CookieRobotResult:
        """Process cookie robot task for single account"""
        start_time = time.time()
        account_data = account_task.account
        username = account_data.get('username', 'unknown')
        profile_id = account_data.get('dolphin_profile_id')
        
        try:
            # Check if profile ID exists
            if not profile_id:
                return CookieRobotResult(
                    account_task_id=account_task.account_task_id,
                    account_username=username,
                    status=CookieRobotStatus.FAILED,
                    execution_time=time.time() - start_time,
                    error_message="No Dolphin profile ID found",
                    worker_id=self._worker_id
                )
            
            # Execute browser automation
            success = await self._browser.visit_urls(profile_id, urls, options)
            
            execution_time = time.time() - start_time
            
            if success:
                return CookieRobotResult(
                    account_task_id=account_task.account_task_id,
                    account_username=username,
                    status=CookieRobotStatus.COMPLETED,
                    urls_visited=len(urls),
                    execution_time=execution_time,
                    worker_id=self._worker_id
                )
            else:
                return CookieRobotResult(
                    account_task_id=account_task.account_task_id,
                    account_username=username,
                    status=CookieRobotStatus.FAILED,
                    execution_time=execution_time,
                    error_message="Browser automation failed",
                    worker_id=self._worker_id
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            return CookieRobotResult(
                account_task_id=account_task.account_task_id,
                account_username=username,
                status=CookieRobotStatus.FAILED,
                execution_time=execution_time,
                error_message=str(e),
                worker_id=self._worker_id
            )
    
    def _update_metrics(self, results: List[CookieRobotResult]) -> None:
        """Update execution metrics"""
        self._metrics.total_accounts = len(results)
        
        successful = sum(1 for r in results if r.status == CookieRobotStatus.COMPLETED)
        failed = sum(1 for r in results if r.status == CookieRobotStatus.FAILED)
        skipped = sum(1 for r in results if r.status == CookieRobotStatus.SKIPPED)
        
        self._metrics.successful_accounts = successful
        self._metrics.failed_accounts = failed
        self._metrics.skipped_accounts = skipped
        
        total_urls = sum(r.urls_visited for r in results)
        self._metrics.total_urls_visited = total_urls
        
        valid_times = [r.execution_time for r in results if r.execution_time > 0]
        if valid_times:
            self._metrics.average_execution_time = sum(valid_times) / len(valid_times)
    
    def get_metrics(self) -> CookieRobotMetrics:
        """Get current execution metrics"""
        return self._metrics
    
    async def cleanup(self) -> None:
        """Cleanup orchestrator resources"""
        await self._browser.cleanup()


class CookieRobotRunner:
    """Runner for cookie robot tasks following Single Responsibility Principle"""
    
    def __init__(self, worker_id: str, concurrency: int = 2):
        self.worker_id = worker_id
        self.concurrency = concurrency
        self.orchestrator: Optional[CookieRobotOrchestrator] = None
    
    async def initialize(self) -> None:
        """Initialize the cookie robot orchestrator"""
        browser_automation = DolphinBrowserAutomation()
        self.orchestrator = CookieRobotOrchestrator(
            browser_automation=browser_automation,
            worker_id=self.worker_id,
            concurrency=self.concurrency
        )
    
    async def run_job(self, ui: UiClient, task_id: int) -> Tuple[int, int]:
        """Execute cookie robot job with comprehensive automation"""
        if not self.orchestrator:
            await self.initialize()
        
        try:
            # Update task status
            await ui.update_task_status_generic('cookie_robot', task_id, status="RUNNING")
            
            # Get task aggregate data
            agg_json = await ui.get_aggregate('cookie_robot', task_id)
            agg = CookieRobotAggregate.model_validate(agg_json)
            
            # Prepare options
            options = {
                'headless': getattr(agg.config, 'headless', True),
                'imageless': getattr(agg.config, 'imageless', False)
            }
            
            # Execute cookie robot tasks
            results = await self.orchestrator.execute_cookie_robot_tasks(
                account_tasks=agg.accounts,
                urls=agg.config.urls,
                options=options,
                progress_callback=self._create_progress_callback(ui, task_id)
            )
            
            # Update account statuses
            await self._update_account_statuses(ui, results)
            
            # Calculate success/failure counts
            success_count = sum(1 for r in results if r.status == CookieRobotStatus.COMPLETED)
            failure_count = sum(1 for r in results if r.status == CookieRobotStatus.FAILED)
            
            # Update final task status
            final_status = self._determine_final_status(success_count, failure_count)
            await ui.update_task_status_generic('cookie_robot', task_id, status=final_status)
            
            # Log execution metrics
            metrics = self.orchestrator.get_metrics()
            await ui.update_task_status_generic(
                'cookie_robot', 
                task_id, 
                log_append=f"Cookie robot completed: {success_count} successful, "
                          f"{failure_count} failed. "
                          f"URLs visited: {metrics.total_urls_visited}\n"
            )
            
            return success_count, failure_count
            
        except Exception as e:
            await ui.update_task_status_generic(
                'cookie_robot', 
                task_id, 
                status="FAILED",
                log_append=f"Critical error in cookie robot: {str(e)}\n"
            )
            return 0, len(agg.accounts) if 'agg' in locals() else 1
        
        finally:
            # Cleanup resources
            if self.orchestrator:
                await self.orchestrator.cleanup()
    
    async def _update_account_statuses(self, ui: UiClient, results: List[CookieRobotResult]) -> None:
        """Update individual account task statuses"""
        for result in results:
            status_str = "COMPLETED" if result.status == CookieRobotStatus.COMPLETED else "FAILED"
            log_message = f"URLs visited: {result.urls_visited}, Time: {result.execution_time:.2f}s"
            
            if result.error_message:
                log_message += f", Error: {result.error_message}"
            
            await ui.update_account_status_generic(
                'cookie_robot',
                result.account_task_id,
                status=status_str,
                log_append=f"{log_message}\n"
            )
    
    def _create_progress_callback(self, ui: UiClient, task_id: int):
        """Create progress callback for real-time updates"""
        async def progress_callback(current: int, total: int, metrics):
            percentage = int((current / total) * 100) if total > 0 else 0
            
            await ui.update_task_status_generic(
                'cookie_robot',
                task_id,
                log_append=f"[{percentage}%] Processed {current}/{total} accounts. "
                          f"Success: {metrics.successful_accounts}, "
                          f"Failed: {metrics.failed_accounts} ({self.worker_id})\n"
            )
        
        return progress_callback
    
    def _determine_final_status(self, success: int, failed: int) -> str:
        """Determine final task status based on results"""
        if failed == 0 and success > 0:
            return "COMPLETED"
        elif success > 0:
            return "PARTIALLY_COMPLETED"
        elif failed > 0:
            return "FAILED"
        else:
            return "COMPLETED"  # No accounts to process


# Global runner instance
_runner_instance: Optional[CookieRobotRunner] = None


def get_runner(worker_id: str, concurrency: int = 2) -> CookieRobotRunner:
    """Get or create runner instance (Singleton pattern)"""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = CookieRobotRunner(worker_id, concurrency)
    return _runner_instance


async def run_cookie_robot_job(ui: UiClient, task_id: int, concurrency: int = 2) -> Tuple[int, int]:
    """Legacy interface for backward compatibility"""
    # Get worker ID from settings or generate one
    worker_id = getattr(settings, 'WORKER_ID', f"worker_{os.getpid()}")
    
    runner = get_runner(worker_id, concurrency)
    return await runner.run_job(ui, task_id)