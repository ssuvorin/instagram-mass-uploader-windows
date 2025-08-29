"""
Comprehensive Proxy Diagnostics System for Distributed Workers
Following SOLID, CLEAN, KISS, DRY, and OOP principles.
"""

from __future__ import annotations
import asyncio
import time
import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ProxyStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SLOW = "SLOW"
    BANNED = "BANNED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


@dataclass
class ProxyTestResult:
    proxy_id: Optional[int]
    proxy_string: str
    status: ProxyStatus
    response_time: float = 0.0
    error_message: Optional[str] = None
    worker_id: Optional[str] = None


@dataclass
class DiagnosticsMetrics:
    total_proxies: int = 0
    active_proxies: int = 0
    slow_proxies: int = 0
    error_proxies: int = 0
    average_response_time: float = 0.0


class IProxyTester(ABC):
    @abstractmethod
    async def test_proxy(self, proxy_config: Dict) -> ProxyTestResult:
        pass
    
    @abstractmethod
    async def test_batch(self, configs: List[Dict], concurrency: int) -> List[ProxyTestResult]:
        pass


class HttpProxyTester(IProxyTester):
    def __init__(self, slow_threshold: float = 5.0):
        self.slow_threshold = slow_threshold
        self.test_url = "https://httpbin.org/ip"
    
    async def test_proxy(self, proxy_config: Dict) -> ProxyTestResult:
        start_time = time.time()
        proxy_string = self._format_proxy(proxy_config)
        
        try:
            proxy_url = self._build_proxy_url(proxy_config)
            
            async with httpx.AsyncClient(
                proxies=proxy_url,
                timeout=30.0,
                verify=False
            ) as client:
                response = await client.get(self.test_url)
                response.raise_for_status()
                
                response_time = time.time() - start_time
                
                if response_time > self.slow_threshold:
                    status = ProxyStatus.SLOW
                else:
                    status = ProxyStatus.ACTIVE
                
                return ProxyTestResult(
                    proxy_id=proxy_config.get('id'),
                    proxy_string=proxy_string,
                    status=status,
                    response_time=response_time
                )
                
        except asyncio.TimeoutError:
            return ProxyTestResult(
                proxy_id=proxy_config.get('id'),
                proxy_string=proxy_string,
                status=ProxyStatus.TIMEOUT,
                response_time=time.time() - start_time,
                error_message="Connection timeout"
            )
        except Exception as e:
            error_msg = str(e)
            status = ProxyStatus.ERROR
            if "403" in error_msg or "banned" in error_msg.lower():
                status = ProxyStatus.BANNED
            
            return ProxyTestResult(
                proxy_id=proxy_config.get('id'),
                proxy_string=proxy_string,
                status=status,
                response_time=time.time() - start_time,
                error_message=error_msg
            )
    
    async def test_batch(self, configs: List[Dict], concurrency: int = 10) -> List[ProxyTestResult]:
        semaphore = asyncio.Semaphore(concurrency)
        
        async def _test_with_semaphore(config: Dict) -> ProxyTestResult:
            async with semaphore:
                return await self.test_proxy(config)
        
        tasks = [_test_with_semaphore(config) for config in configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(ProxyTestResult(
                    proxy_id=configs[i].get('id'),
                    proxy_string=self._format_proxy(configs[i]),
                    status=ProxyStatus.ERROR,
                    error_message=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    def _build_proxy_url(self, config: Dict) -> str:
        scheme = config.get('proxy_type', 'http').lower()
        host = config['host']
        port = config['port']
        username = config.get('username')
        password = config.get('password')
        
        if username and password:
            return f"{scheme}://{username}:{password}@{host}:{port}"
        return f"{scheme}://{host}:{port}"
    
    def _format_proxy(self, config: Dict) -> str:
        scheme = config.get('proxy_type', 'HTTP')
        host = config.get('host', 'unknown')
        port = config.get('port', 'unknown')
        return f"{scheme}://{host}:{port}"


class ProxyDiagnosticsOrchestrator:
    def __init__(self, tester: IProxyTester, worker_id: str, concurrency: int = 10):
        self._tester = tester
        self._worker_id = worker_id
        self._concurrency = concurrency
        self._metrics = DiagnosticsMetrics()
    
    async def diagnose_proxies(
        self, 
        proxy_configs: List[Dict],
        progress_callback: Optional[callable] = None
    ) -> List[ProxyTestResult]:
        start_time = time.time()
        
        results = await self._tester.test_batch(proxy_configs, self._concurrency)
        
        # Update worker ID in results
        for result in results:
            result.worker_id = self._worker_id
        
        self._update_metrics(results)
        
        if progress_callback:
            await progress_callback(len(results), len(proxy_configs), self._metrics)
        
        return results
    
    def _update_metrics(self, results: List[ProxyTestResult]) -> None:
        self._metrics.total_proxies = len(results)
        
        active_count = sum(1 for r in results if r.status == ProxyStatus.ACTIVE)
        slow_count = sum(1 for r in results if r.status == ProxyStatus.SLOW)
        error_count = sum(1 for r in results if r.status in [ProxyStatus.ERROR, ProxyStatus.BANNED, ProxyStatus.TIMEOUT])
        
        self._metrics.active_proxies = active_count
        self._metrics.slow_proxies = slow_count
        self._metrics.error_proxies = error_count
        
        valid_times = [r.response_time for r in results if r.response_time > 0]
        if valid_times:
            self._metrics.average_response_time = sum(valid_times) / len(valid_times)
    
    def get_metrics(self) -> DiagnosticsMetrics:
        return self._metrics


class ProxyDiagnosticsFactory:
    @staticmethod
    def create_orchestrator(
        worker_id: str,
        concurrency: int = 10,
        slow_threshold: float = 5.0
    ) -> ProxyDiagnosticsOrchestrator:
        tester = HttpProxyTester(slow_threshold)
        return ProxyDiagnosticsOrchestrator(tester, worker_id, concurrency)


# Singleton factory instance
proxy_diagnostics_factory = ProxyDiagnosticsFactory()