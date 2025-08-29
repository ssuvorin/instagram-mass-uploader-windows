"""
Account Management Runners for Distributed Workers
Following SOLID, CLEAN, KISS, DRY, and OOP principles.
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
from ..config import settings


class AccountOperationStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class AccountOperationResult:
    operation_id: str
    account_data: Dict
    status: AccountOperationStatus
    execution_time: float = 0.0
    error_message: Optional[str] = None
    worker_id: Optional[str] = None


class IAccountManager(ABC):
    @abstractmethod
    async def create_account(self, account_data: Dict) -> bool:
        pass
    
    @abstractmethod
    async def import_accounts(self, accounts_data: List[Dict]) -> List[bool]:
        pass
    
    @abstractmethod
    async def validate_account_data(self, account_data: Dict) -> bool:
        pass


class StandardAccountManager(IAccountManager):
    def __init__(self, ui_client: UiClient):
        self.ui = ui_client
    
    async def create_account(self, account_data: Dict) -> bool:
        try:
            if not await self.validate_account_data(account_data):
                return False
            
            result = await self.ui.create_account(account_data)
            return result.get('ok', False)
            
        except Exception as e:
            print(f"Error creating account: {str(e)}")
            return False
    
    async def import_accounts(self, accounts_data: List[Dict]) -> List[bool]:
        try:
            result = await self.ui.import_accounts(accounts_data)
            created_count = result.get('created_count', 0)
            total_accounts = len(accounts_data)
            
            # Return boolean list based on success ratio
            return [True] * created_count + [False] * (total_accounts - created_count)
            
        except Exception as e:
            print(f"Error importing accounts: {str(e)}")
            return [False] * len(accounts_data)
    
    async def validate_account_data(self, account_data: Dict) -> bool:
        required_fields = ['username', 'password']
        return all(field in account_data and account_data[field] for field in required_fields)


class AccountCreationRunner:
    """Runner for account creation tasks"""
    
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.manager: Optional[IAccountManager] = None
    
    async def initialize(self, ui_client: UiClient) -> None:
        self.manager = StandardAccountManager(ui_client)
    
    async def run_account_creation_job(
        self, 
        ui: UiClient, 
        accounts_data: List[Dict]
    ) -> Tuple[int, int]:
        if not self.manager:
            await self.initialize(ui)
        
        success_count = 0
        failure_count = 0
        
        for account_data in accounts_data:
            try:
                success = await self.manager.create_account(account_data)
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                    
            except Exception as e:
                failure_count += 1
                print(f"Error processing account {account_data.get('username', 'unknown')}: {str(e)}")
        
        return success_count, failure_count


class AccountImportRunner:
    """Runner for account import tasks"""
    
    def __init__(self, worker_id: str, batch_size: int = 10):
        self.worker_id = worker_id
        self.batch_size = batch_size
        self.manager: Optional[IAccountManager] = None
    
    async def initialize(self, ui_client: UiClient) -> None:
        self.manager = StandardAccountManager(ui_client)
    
    async def run_account_import_job(
        self, 
        ui: UiClient, 
        accounts_data: List[Dict]
    ) -> Tuple[int, int]:
        if not self.manager:
            await self.initialize(ui)
        
        total_success = 0
        total_failure = 0
        
        # Process in batches for better performance
        for i in range(0, len(accounts_data), self.batch_size):
            batch = accounts_data[i:i + self.batch_size]
            
            try:
                results = await self.manager.import_accounts(batch)
                success_count = sum(1 for r in results if r)
                failure_count = len(results) - success_count
                
                total_success += success_count
                total_failure += failure_count
                
            except Exception as e:
                total_failure += len(batch)
                print(f"Error processing batch {i//self.batch_size + 1}: {str(e)}")
        
        return total_success, total_failure


class BulkProxyChangeRunner:
    """Runner for bulk proxy change operations"""
    
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
    
    async def run_bulk_proxy_change_job(
        self, 
        ui: UiClient, 
        account_ids: List[int],
        proxy_id: Optional[int]
    ) -> Tuple[int, int]:
        try:
            result = await ui.bulk_change_proxy(account_ids, proxy_id)
            updated_count = result.get('updated_count', 0)
            failed_count = len(account_ids) - updated_count
            
            return updated_count, failed_count
            
        except Exception as e:
            print(f"Error in bulk proxy change: {str(e)}")
            return 0, len(account_ids)


class DolphinProfileCreationRunner:
    """Runner for Dolphin profile creation"""
    
    def __init__(self, worker_id: str, concurrency: int = 5):
        self.worker_id = worker_id
        self.concurrency = concurrency
    
    async def run_dolphin_profile_creation_job(
        self, 
        ui: UiClient, 
        account_ids: List[int]
    ) -> Tuple[int, int]:
        semaphore = asyncio.Semaphore(self.concurrency)
        
        async def _create_profile(account_id: int) -> bool:
            async with semaphore:
                try:
                    result = await ui.create_dolphin_profile(account_id)
                    return result.get('ok', False)
                except Exception as e:
                    print(f"Error creating profile for account {account_id}: {str(e)}")
                    return False
        
        # Execute profile creation concurrently
        tasks = [_create_profile(account_id) for account_id in account_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if isinstance(r, bool) and r)
        failure_count = len(results) - success_count
        
        return success_count, failure_count


class AccountManagementOrchestrator:
    """Orchestrator for all account management operations"""
    
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.creation_runner = AccountCreationRunner(worker_id)
        self.import_runner = AccountImportRunner(worker_id)
        self.proxy_runner = BulkProxyChangeRunner(worker_id)
        self.dolphin_runner = DolphinProfileCreationRunner(worker_id)
    
    async def execute_account_creation(
        self, 
        ui: UiClient, 
        accounts_data: List[Dict]
    ) -> Tuple[int, int]:
        return await self.creation_runner.run_account_creation_job(ui, accounts_data)
    
    async def execute_account_import(
        self, 
        ui: UiClient, 
        accounts_data: List[Dict]
    ) -> Tuple[int, int]:
        return await self.import_runner.run_account_import_job(ui, accounts_data)
    
    async def execute_bulk_proxy_change(
        self, 
        ui: UiClient, 
        account_ids: List[int],
        proxy_id: Optional[int]
    ) -> Tuple[int, int]:
        return await self.proxy_runner.run_bulk_proxy_change_job(ui, account_ids, proxy_id)
    
    async def execute_dolphin_profile_creation(
        self, 
        ui: UiClient, 
        account_ids: List[int]
    ) -> Tuple[int, int]:
        return await self.dolphin_runner.run_dolphin_profile_creation_job(ui, account_ids)


# Factory for creating account management components
class AccountManagementFactory:
    @staticmethod
    def create_orchestrator(worker_id: str) -> AccountManagementOrchestrator:
        return AccountManagementOrchestrator(worker_id)


# Singleton factory instance
account_management_factory = AccountManagementFactory()


# Legacy interface functions for backward compatibility
async def run_account_creation_job(ui: UiClient, accounts_data: List[Dict]) -> Tuple[int, int]:
    worker_id = getattr(settings, 'WORKER_ID', f"worker_{os.getpid()}")
    orchestrator = account_management_factory.create_orchestrator(worker_id)
    return await orchestrator.execute_account_creation(ui, accounts_data)


async def run_account_import_job(ui: UiClient, accounts_data: List[Dict]) -> Tuple[int, int]:
    worker_id = getattr(settings, 'WORKER_ID', f"worker_{os.getpid()}")
    orchestrator = account_management_factory.create_orchestrator(worker_id)
    return await orchestrator.execute_account_import(ui, accounts_data)


async def run_bulk_proxy_change_job(
    ui: UiClient, 
    account_ids: List[int], 
    proxy_id: Optional[int]
) -> Tuple[int, int]:
    worker_id = getattr(settings, 'WORKER_ID', f"worker_{os.getpid()}")
    orchestrator = account_management_factory.create_orchestrator(worker_id)
    return await orchestrator.execute_bulk_proxy_change(ui, account_ids, proxy_id)


async def run_dolphin_profile_creation_job(ui: UiClient, account_ids: List[int]) -> Tuple[int, int]:
    worker_id = getattr(settings, 'WORKER_ID', f"worker_{os.getpid()}")
    orchestrator = account_management_factory.create_orchestrator(worker_id)
    return await orchestrator.execute_dolphin_profile_creation(ui, account_ids)