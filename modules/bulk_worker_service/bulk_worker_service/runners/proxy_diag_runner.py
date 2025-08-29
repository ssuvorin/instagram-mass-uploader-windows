"""Comprehensive Proxy Diagnostics Runner for Distributed Workers

Implements distributed proxy testing with SOLID principles compliance.
"""

from __future__ import annotations
import os
import asyncio
from typing import Tuple, Optional

from ..ui_client import UiClient
from ..domain import ProxyDiagnosticsAggregate
from ..proxy_diagnostics import (
    proxy_diagnostics_factory, ProxyStatus, ProxyDiagnosticsOrchestrator
)
from ..config import settings


class ProxyDiagnosticsRunner:
    """Runner for proxy diagnostics tasks following Single Responsibility Principle"""
    
    def __init__(self, worker_id: str, concurrency: int = 10):
        self.worker_id = worker_id
        self.concurrency = concurrency
        self.orchestrator: Optional[ProxyDiagnosticsOrchestrator] = None
    
    async def initialize(self) -> None:
        """Initialize the diagnostics orchestrator"""
        slow_threshold = getattr(settings, 'PROXY_SLOW_THRESHOLD', 5.0)
        self.orchestrator = proxy_diagnostics_factory.create_orchestrator(
            worker_id=self.worker_id,
            concurrency=self.concurrency,
            slow_threshold=slow_threshold
        )
    
    async def run_job(self, ui: UiClient, task_id: int) -> Tuple[int, int]:
        """Execute proxy diagnostics job with comprehensive testing"""
        if not self.orchestrator:
            await self.initialize()
        
        try:
            # Update task status
            await ui.update_task_status_generic('proxy_diag', task_id, status="RUNNING")
            
            # Get task aggregate data
            agg_json = await ui.get_aggregate('proxy_diag', task_id)
            agg = ProxyDiagnosticsAggregate.model_validate(agg_json)
            
            # Prepare proxy configurations for testing
            proxy_configs = []
            account_proxy_map = {}
            
            for account_task in agg.accounts:
                account_data = account_task.account
                proxy_data = account_data.get('proxy')
                
                if proxy_data:
                    proxy_config = {
                        'id': proxy_data.get('id'),
                        'host': proxy_data.get('host'),
                        'port': proxy_data.get('port'),
                        'username': proxy_data.get('user'),
                        'password': proxy_data.get('pass'),
                        'proxy_type': proxy_data.get('type', 'http')
                    }
                    proxy_configs.append(proxy_config)
                    account_proxy_map[account_task.account_task_id] = proxy_config
            
            if not proxy_configs:
                await ui.update_task_status_generic(
                    'proxy_diag', task_id, status="COMPLETED",
                    log_append="No proxies found to test\n"
                )
                return 0, 0
            
            # Run diagnostics with progress tracking
            results = await self.orchestrator.diagnose_proxies(
                proxy_configs,
                progress_callback=self._create_progress_callback(ui, task_id)
            )
            
            # Update account statuses based on results
            await self._update_account_statuses(ui, results, account_proxy_map)
            
            # Calculate success/failure counts
            success_count = sum(1 for r in results if r.status == ProxyStatus.ACTIVE)
            failure_count = sum(1 for r in results if r.status in [
                ProxyStatus.ERROR, ProxyStatus.BANNED, ProxyStatus.TIMEOUT
            ])
            
            # Update final task status
            final_status = self._determine_final_status(success_count, failure_count)
            await ui.update_task_status_generic('proxy_diag', task_id, status=final_status)
            
            # Log diagnostics metrics
            metrics = self.orchestrator.get_metrics()
            await ui.update_task_status_generic(
                'proxy_diag', 
                task_id, 
                log_append=f"Diagnostics completed: {success_count} active, "
                          f"{failure_count} failed. "
                          f"Average response time: {metrics.average_response_time:.2f}s\n"
            )
            
            return success_count, failure_count
            
        except Exception as e:
            await ui.update_task_status_generic(
                'proxy_diag', 
                task_id, 
                status="FAILED",
                log_append=f"Critical error in proxy diagnostics: {str(e)}\n"
            )
            return 0, len(agg.accounts) if 'agg' in locals() else 1
    
    async def _update_account_statuses(
        self, 
        ui: UiClient, 
        results, 
        account_proxy_map: dict
    ) -> None:
        """Update individual account statuses based on proxy test results"""
        # Create lookup dict for results by proxy ID
        results_by_proxy = {r.proxy_id: r for r in results if r.proxy_id}
        
        for account_task_id, proxy_config in account_proxy_map.items():
            proxy_id = proxy_config.get('id')
            result = results_by_proxy.get(proxy_id)
            
            if result:
                if result.status == ProxyStatus.ACTIVE:
                    await ui.update_account_status_generic(
                        'proxy_diag', account_task_id, status="COMPLETED",
                        log_append=f"Proxy OK: {result.response_time:.2f}s\n"
                    )
                else:
                    await ui.update_account_status_generic(
                        'proxy_diag', account_task_id, status="FAILED",
                        log_append=f"Proxy {result.status.value}: {result.error_message or 'No error'}\n"
                    )
            else:
                await ui.update_account_status_generic(
                    'proxy_diag', account_task_id, status="FAILED",
                    log_append="Proxy test result not found\n"
                )
    
    def _create_progress_callback(self, ui: UiClient, task_id: int):
        """Create progress callback for real-time updates"""
        async def progress_callback(current: int, total: int, metrics):
            percentage = int((current / total) * 100) if total > 0 else 0
            
            await ui.update_task_status_generic(
                'proxy_diag',
                task_id,
                log_append=f"[{percentage}%] Tested {current}/{total} proxies. "
                          f"Active: {metrics.active_proxies}, "
                          f"Errors: {metrics.error_proxies} ({self.worker_id})\n"
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
            return "COMPLETED"  # No proxies to test


# Global runner instance
_runner_instance: Optional[ProxyDiagnosticsRunner] = None


def get_runner(worker_id: str, concurrency: int = 10) -> ProxyDiagnosticsRunner:
    """Get or create runner instance (Singleton pattern)"""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = ProxyDiagnosticsRunner(worker_id, concurrency)
    return _runner_instance


async def run_proxy_diag_job(ui: UiClient, task_id: int, concurrency: int = 10) -> Tuple[int, int]:
    """Legacy interface for backward compatibility"""
    # Get worker ID from settings or generate one
    worker_id = getattr(settings, 'WORKER_ID', f"worker_{os.getpid()}")
    
    runner = get_runner(worker_id, concurrency)
    return await runner.run_job(ui, task_id) 