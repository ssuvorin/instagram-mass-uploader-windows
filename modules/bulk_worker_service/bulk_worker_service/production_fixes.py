"""
Production-ready fixes for critical deployment issues.

This module provides enhanced versions of core components with:
- Robust error handling
- Resource management
- Circuit breakers
- Monitoring capabilities
"""

import asyncio
import logging
import psutil
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open" 
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    timeout_seconds: int = 60
    half_open_max_calls: int = 3


class CircuitBreaker:
    """Circuit breaker pattern implementation for external service calls."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if execution is allowed based on circuit state."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout period has passed
            if (self.last_failure_time and 
                datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.config.timeout_seconds)):
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def on_success(self):
        """Handle successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.half_open_calls = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.CLOSED and self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker reopened during half-open state")
        
        self.half_open_calls += 1


class RobustHttpClient:
    """HTTP client with retry logic, circuit breaker, and proper resource management."""
    
    def __init__(self, base_url: str, token: str, timeout: int = 30):
        self.base_url = base_url
        self.token = token
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker(CircuitBreakerConfig())
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper configuration."""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/json",
                    "User-Agent": "WorkerService/1.0"
                },
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5,
                    keepalive_expiry=30
                )
            )
        return self._client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make POST request with circuit breaker and retry logic."""
        if not self.circuit_breaker.can_execute():
            raise Exception(f"Circuit breaker is {self.circuit_breaker.state.value}")
        
        try:
            client = await self._get_client()
            response = await client.post(url, **kwargs)
            response.raise_for_status()
            self.circuit_breaker.on_success()
            return response
        except Exception as e:
            self.circuit_breaker.on_failure()
            logger.error(f"HTTP request failed: {url} - {e}")
            raise
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make GET request with circuit breaker and retry logic."""
        if not self.circuit_breaker.can_execute():
            raise Exception(f"Circuit breaker is {self.circuit_breaker.state.value}")
        
        try:
            client = await self._get_client()
            response = await client.get(url, **kwargs)
            response.raise_for_status()
            self.circuit_breaker.on_success()
            return response
        except Exception as e:
            self.circuit_breaker.on_failure()
            logger.error(f"HTTP request failed: {url} - {e}")
            raise
    
    async def close(self):
        """Close the HTTP client and release resources."""
        if self._client:
            await self._client.aclose()
            self._client = None


class ResourceMonitor:
    """Monitor system resources and enforce limits."""
    
    def __init__(self, memory_limit_mb: int = 2048, cpu_threshold: float = 80.0):
        self.memory_limit = memory_limit_mb * 1024 * 1024  # Convert to bytes
        self.cpu_threshold = cpu_threshold
        self.process = psutil.Process()
    
    def check_memory(self) -> tuple[bool, float]:
        """Check if memory usage is within limits."""
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        within_limit = memory_info.rss <= self.memory_limit
        
        if not within_limit:
            logger.warning(f"Memory usage {memory_mb:.1f}MB exceeds limit {self.memory_limit/1024/1024:.1f}MB")
        
        return within_limit, memory_mb
    
    def check_cpu(self) -> tuple[bool, float]:
        """Check if CPU usage is within threshold."""
        cpu_percent = self.process.cpu_percent(interval=1)
        within_threshold = cpu_percent <= self.cpu_threshold
        
        if not within_threshold:
            logger.warning(f"CPU usage {cpu_percent:.1f}% exceeds threshold {self.cpu_threshold}%")
        
        return within_threshold, cpu_percent
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get comprehensive resource statistics."""
        memory_info = self.process.memory_info()
        cpu_percent = self.process.cpu_percent()
        
        return {
            "memory_mb": memory_info.rss / 1024 / 1024,
            "memory_limit_mb": self.memory_limit / 1024 / 1024,
            "memory_percent": (memory_info.rss / self.memory_limit) * 100,
            "cpu_percent": cpu_percent,
            "cpu_threshold": self.cpu_threshold,
            "num_threads": self.process.num_threads(),
            "num_fds": self.process.num_fds() if hasattr(self.process, 'num_fds') else 0,
            "timestamp": datetime.utcnow().isoformat()
        }


@asynccontextmanager
async def safe_resource_context(resource_factory, *args, **kwargs):
    """Context manager for safe resource handling with automatic cleanup."""
    resource = None
    try:
        resource = await resource_factory(*args, **kwargs)
        yield resource
    except Exception as e:
        logger.error(f"Error in resource context: {e}")
        raise
    finally:
        if resource and hasattr(resource, 'close'):
            try:
                if asyncio.iscoroutinefunction(resource.close):
                    await resource.close()
                else:
                    resource.close()
            except Exception as e:
                logger.error(f"Error closing resource: {e}")


class TaskLockManager:
    """Manage task locks with TTL and automatic cleanup."""
    
    def __init__(self, default_ttl_seconds: int = 3600):
        self.default_ttl = default_ttl_seconds
        self.locks: Dict[str, datetime] = {}
    
    def acquire_lock(self, lock_key: str, ttl_seconds: Optional[int] = None) -> bool:
        """Acquire a lock with TTL."""
        self._cleanup_expired_locks()
        
        if lock_key in self.locks:
            return False  # Lock already exists
        
        ttl = ttl_seconds or self.default_ttl
        expiry_time = datetime.utcnow() + timedelta(seconds=ttl)
        self.locks[lock_key] = expiry_time
        
        logger.debug(f"Lock acquired: {lock_key} (expires: {expiry_time})")
        return True
    
    def release_lock(self, lock_key: str) -> bool:
        """Release a lock."""
        if lock_key in self.locks:
            del self.locks[lock_key]
            logger.debug(f"Lock released: {lock_key}")
            return True
        return False
    
    def _cleanup_expired_locks(self):
        """Remove expired locks."""
        now = datetime.utcnow()
        expired_keys = [key for key, expiry in self.locks.items() if expiry <= now]
        
        for key in expired_keys:
            del self.locks[key]
            logger.debug(f"Expired lock cleaned up: {key}")
    
    def get_active_locks(self) -> List[str]:
        """Get list of active (non-expired) locks."""
        self._cleanup_expired_locks()
        return list(self.locks.keys())


class HealthChecker:
    """Comprehensive health checking for production deployment."""
    
    def __init__(self, resource_monitor: ResourceMonitor):
        self.resource_monitor = resource_monitor
        self.last_check: Optional[datetime] = None
        self.check_results: Dict[str, Any] = {}
    
    async def check_database_connection(self) -> bool:
        """Check database connectivity."""
        try:
            # Import here to avoid circular dependencies
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def check_external_services(self, services: Dict[str, str]) -> Dict[str, bool]:
        """Check connectivity to external services."""
        results = {}
        
        for service_name, url in services.items():
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(url)
                    results[service_name] = response.status_code == 200
            except Exception as e:
                logger.error(f"Service {service_name} health check failed: {e}")
                results[service_name] = False
        
        return results
    
    async def full_health_check(self, external_services: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        self.last_check = datetime.utcnow()
        
        # Resource checks
        memory_ok, memory_mb = self.resource_monitor.check_memory()
        cpu_ok, cpu_percent = self.resource_monitor.check_cpu()
        
        # Database check
        database_ok = await self.check_database_connection()
        
        # External service checks
        services_ok = {}
        if external_services:
            services_ok = await self.check_external_services(external_services)
        
        # Overall health
        overall_healthy = (
            memory_ok and 
            cpu_ok and 
            database_ok and 
            all(services_ok.values()) if services_ok else True
        )
        
        self.check_results = {
            "healthy": overall_healthy,
            "timestamp": self.last_check.isoformat(),
            "checks": {
                "memory": {"ok": memory_ok, "usage_mb": memory_mb},
                "cpu": {"ok": cpu_ok, "usage_percent": cpu_percent},
                "database": {"ok": database_ok},
                "external_services": services_ok
            },
            "resource_stats": self.resource_monitor.get_resource_stats()
        }
        
        return self.check_results


class GracefulShutdownHandler:
    """Handle graceful shutdown of worker processes."""
    
    def __init__(self):
        self.shutdown_requested = False
        self.active_tasks: set = set()
        self.cleanup_callbacks: List[callable] = []
    
    def request_shutdown(self):
        """Request graceful shutdown."""
        self.shutdown_requested = True
        logger.info("Graceful shutdown requested")
    
    def add_active_task(self, task_id: str):
        """Track active task."""
        self.active_tasks.add(task_id)
    
    def remove_active_task(self, task_id: str):
        """Remove completed task from tracking."""
        self.active_tasks.discard(task_id)
    
    def add_cleanup_callback(self, callback: callable):
        """Add cleanup callback to be called during shutdown."""
        self.cleanup_callbacks.append(callback)
    
    async def wait_for_completion(self, timeout_seconds: int = 300):
        """Wait for active tasks to complete or timeout."""
        start_time = time.time()
        
        while self.active_tasks and (time.time() - start_time) < timeout_seconds:
            logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete...")
            await asyncio.sleep(1)
        
        if self.active_tasks:
            logger.warning(f"Shutdown timeout reached with {len(self.active_tasks)} active tasks")
        else:
            logger.info("All tasks completed successfully")
    
    async def cleanup(self):
        """Execute all cleanup callbacks."""
        for callback in self.cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error in cleanup callback: {e}")


# Global instances for production use
_resource_monitor = ResourceMonitor()
_task_lock_manager = TaskLockManager()
_shutdown_handler = GracefulShutdownHandler()
_health_checker = HealthChecker(_resource_monitor)


def get_resource_monitor() -> ResourceMonitor:
    """Get global resource monitor instance."""
    return _resource_monitor


def get_task_lock_manager() -> TaskLockManager:
    """Get global task lock manager instance."""
    return _task_lock_manager


def get_shutdown_handler() -> GracefulShutdownHandler:
    """Get global shutdown handler instance."""
    return _shutdown_handler


def get_health_checker() -> HealthChecker:
    """Get global health checker instance."""
    return _health_checker