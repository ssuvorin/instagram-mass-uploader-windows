"""
Database connection pooling and management for production deployments.

Provides efficient connection pooling with health checks and monitoring
to prevent database connection exhaustion under high load.
"""

import logging
import asyncio
import time
from typing import Optional, Dict, Any, List, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

try:
    import psycopg2
    from psycopg2 import pool as pg_pool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from .metrics import get_metrics

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolConfig:
    """Database connection pool configuration."""
    database_url: str
    min_connections: int = 5
    max_connections: int = 20
    max_idle_time: int = 300  # seconds
    health_check_interval: int = 60  # seconds
    connection_timeout: int = 30  # seconds
    query_timeout: int = 30  # seconds
    retry_attempts: int = 3
    retry_delay: float = 1.0


class DatabaseConnectionPool:
    """Production-ready database connection pool with health monitoring."""
    
    def __init__(self, config: ConnectionPoolConfig):
        self.config = config
        self.pool: Optional[Any] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._last_health_check = 0
        self._connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "failed_connections": 0,
            "queries_executed": 0,
            "avg_query_time": 0.0
        }
        self._metrics = get_metrics()
    
    async def initialize(self):
        """Initialize the connection pool."""
        if not ASYNCPG_AVAILABLE:
            raise RuntimeError("asyncpg is required for connection pooling")
        
        try:
            logger.info(f"Initializing database pool: {self.config.min_connections}-{self.config.max_connections} connections")
            
            self.pool = await asyncpg.create_pool(
                self.config.database_url,
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                max_inactive_connection_lifetime=self.config.max_idle_time,
                command_timeout=self.config.query_timeout,
                server_settings={
                    'jit': 'off',  # Disable JIT for better performance on simple queries
                    'application_name': 'bulk_worker_service'
                }
            )
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            # Test initial connection
            await self.health_check()
            
            logger.info("Database pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self):
        """Close the connection pool."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def acquire_connection(self):
        """Acquire a database connection from the pool."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        connection = None
        start_time = time.time()
        
        try:
            # Acquire connection with timeout
            connection = await asyncio.wait_for(
                self.pool.acquire(),
                timeout=self.config.connection_timeout
            )
            
            self._connection_stats["active_connections"] += 1
            acquisition_time = time.time() - start_time
            
            self._metrics.timer("database_connection_acquisition_seconds", acquisition_time)
            self._metrics.gauge("database_active_connections", self._connection_stats["active_connections"])
            
            logger.debug(f"Acquired database connection in {acquisition_time:.3f}s")
            
            yield connection
            
        except asyncio.TimeoutError:
            self._connection_stats["failed_connections"] += 1
            self._metrics.counter("database_connection_timeouts_total")
            logger.error(f"Database connection acquisition timeout after {self.config.connection_timeout}s")
            raise
        
        except Exception as e:
            self._connection_stats["failed_connections"] += 1
            self._metrics.counter("database_connection_errors_total")
            logger.error(f"Database connection acquisition failed: {e}")
            raise
        
        finally:
            if connection:
                try:
                    await self.pool.release(connection)
                    self._connection_stats["active_connections"] -= 1
                    self._metrics.gauge("database_active_connections", self._connection_stats["active_connections"])
                except Exception as e:
                    logger.error(f"Error releasing database connection: {e}")
    
    async def execute_query(self, query: str, *args, **kwargs) -> Any:
        """Execute a query with connection pooling and metrics."""
        start_time = time.time()
        
        for attempt in range(self.config.retry_attempts):
            try:
                async with self.acquire_connection() as conn:
                    result = await conn.fetch(query, *args, **kwargs)
                    
                    query_time = time.time() - start_time
                    self._connection_stats["queries_executed"] += 1
                    
                    # Update average query time
                    total_queries = self._connection_stats["queries_executed"]
                    current_avg = self._connection_stats["avg_query_time"]
                    self._connection_stats["avg_query_time"] = (
                        (current_avg * (total_queries - 1) + query_time) / total_queries
                    )
                    
                    self._metrics.timer("database_query_duration_seconds", query_time)
                    self._metrics.counter("database_queries_total")
                    
                    logger.debug(f"Query executed in {query_time:.3f}s: {query[:100]}...")
                    
                    return result
                    
            except Exception as e:
                logger.warning(f"Query failed (attempt {attempt + 1}/{self.config.retry_attempts}): {e}")
                
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    self._metrics.counter("database_query_failures_total")
                    raise
    
    async def execute_transaction(self, queries: List[Tuple[str, tuple]]) -> List[Any]:
        """Execute multiple queries in a transaction."""
        start_time = time.time()
        
        async with self.acquire_connection() as conn:
            async with conn.transaction():
                results = []
                for query, args in queries:
                    result = await conn.fetch(query, *args)
                    results.append(result)
                
                transaction_time = time.time() - start_time
                self._metrics.timer("database_transaction_duration_seconds", transaction_time)
                self._metrics.counter("database_transactions_total")
                
                logger.debug(f"Transaction completed in {transaction_time:.3f}s with {len(queries)} queries")
                
                return results
    
    async def health_check(self) -> bool:
        """Check database connectivity and pool health."""
        try:
            async with self.acquire_connection() as conn:
                await conn.fetchval("SELECT 1")
                
            self._last_health_check = time.time()
            self._metrics.gauge("database_healthy", 1.0)
            
            # Update pool statistics
            if hasattr(self.pool, '_queue'):
                self._connection_stats["idle_connections"] = self.pool._queue.qsize()
                self._metrics.gauge("database_idle_connections", self._connection_stats["idle_connections"])
            
            return True
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            self._metrics.gauge("database_healthy", 0.0)
            self._metrics.counter("database_health_check_failures_total")
            return False
    
    async def _health_check_loop(self):
        """Periodic health check loop."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self.health_check()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        pool_stats = {}
        
        if self.pool:
            pool_stats = {
                "size": self.pool.get_size(),
                "min_size": self.pool.get_min_size(),
                "max_size": self.pool.get_max_size(),
                "idle_connections": len(self.pool._holders) if hasattr(self.pool, '_holders') else 0,
            }
        
        return {
            "pool": pool_stats,
            "stats": self._connection_stats,
            "config": {
                "min_connections": self.config.min_connections,
                "max_connections": self.config.max_connections,
                "max_idle_time": self.config.max_idle_time,
                "connection_timeout": self.config.connection_timeout,
                "query_timeout": self.config.query_timeout
            },
            "last_health_check": datetime.fromtimestamp(self._last_health_check).isoformat() if self._last_health_check else None
        }


class SyncConnectionPool:
    """Synchronous connection pool for Django integration."""
    
    def __init__(self, config: ConnectionPoolConfig):
        self.config = config
        self.pool: Optional[Any] = None
        self._metrics = get_metrics()
    
    def initialize(self):
        """Initialize synchronous connection pool."""
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("psycopg2 is required for sync connection pooling")
        
        try:
            logger.info(f"Initializing sync database pool: {self.config.min_connections}-{self.config.max_connections} connections")
            
            self.pool = pg_pool.ThreadedConnectionPool(
                minconn=self.config.min_connections,
                maxconn=self.config.max_connections,
                dsn=self.config.database_url
            )
            
            # Test connection
            conn = self.pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            self.pool.putconn(conn)
            
            logger.info("Sync database pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize sync database pool: {e}")
            raise
    
    def close(self):
        """Close the synchronous connection pool."""
        if self.pool:
            self.pool.closeall()
            logger.info("Sync database pool closed")
    
    @asynccontextmanager
    def acquire_connection(self):
        """Acquire a connection from the sync pool."""
        if not self.pool:
            raise RuntimeError("Sync database pool not initialized")
        
        connection = None
        start_time = time.time()
        
        try:
            connection = self.pool.getconn()
            
            acquisition_time = time.time() - start_time
            self._metrics.timer("database_sync_connection_acquisition_seconds", acquisition_time)
            
            yield connection
            
        except Exception as e:
            self._metrics.counter("database_sync_connection_errors_total")
            logger.error(f"Sync database connection error: {e}")
            raise
        
        finally:
            if connection:
                try:
                    self.pool.putconn(connection)
                except Exception as e:
                    logger.error(f"Error returning sync connection to pool: {e}")


# Global pool instances
_async_pool: Optional[DatabaseConnectionPool] = None
_sync_pool: Optional[SyncConnectionPool] = None


async def initialize_database_pools(
    database_url: str,
    min_connections: int = 5,
    max_connections: int = 20,
    **kwargs
):
    """Initialize global database pools."""
    global _async_pool, _sync_pool
    
    config = ConnectionPoolConfig(
        database_url=database_url,
        min_connections=min_connections,
        max_connections=max_connections,
        **kwargs
    )
    
    # Initialize async pool
    _async_pool = DatabaseConnectionPool(config)
    await _async_pool.initialize()
    
    # Initialize sync pool
    _sync_pool = SyncConnectionPool(config)
    _sync_pool.initialize()
    
    logger.info("Database pools initialized")


async def close_database_pools():
    """Close global database pools."""
    global _async_pool, _sync_pool
    
    if _async_pool:
        await _async_pool.close()
        _async_pool = None
    
    if _sync_pool:
        _sync_pool.close()
        _sync_pool = None
    
    logger.info("Database pools closed")


def get_async_pool() -> Optional[DatabaseConnectionPool]:
    """Get the global async database pool."""
    return _async_pool


def get_sync_pool() -> Optional[SyncConnectionPool]:
    """Get the global sync database pool."""
    return _sync_pool


# Convenience functions
async def execute_query(query: str, *args, **kwargs):
    """Execute query using global async pool."""
    if not _async_pool:
        raise RuntimeError("Async database pool not initialized")
    return await _async_pool.execute_query(query, *args, **kwargs)


async def execute_transaction(queries: List[Tuple[str, tuple]]):
    """Execute transaction using global async pool."""
    if not _async_pool:
        raise RuntimeError("Async database pool not initialized")
    return await _async_pool.execute_transaction(queries)


def get_pool_stats() -> Dict[str, Any]:
    """Get statistics for all pools."""
    stats = {
        "async_pool": None,
        "sync_pool": None
    }
    
    if _async_pool:
        stats["async_pool"] = _async_pool.get_stats()
    
    if _sync_pool:
        stats["sync_pool"] = {
            "config": {
                "min_connections": _sync_pool.config.min_connections,
                "max_connections": _sync_pool.config.max_connections
            }
        }
    
    return stats