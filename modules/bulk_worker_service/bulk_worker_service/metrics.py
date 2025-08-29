"""
Comprehensive metrics collection system for production monitoring.

Provides thread-safe metrics collection with support for counters,
gauges, histograms, and timers. Includes Prometheus-compatible export.
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from contextlib import contextmanager
import json

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"  # counter, gauge, histogram, timer


class MetricsRegistry:
    """Thread-safe metrics registry."""
    
    def __init__(self, max_history: int = 1000):
        self._metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._lock = threading.RLock()
        self._max_history = max_history
        self._start_time = time.time()
    
    def counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] += value
            
            point = MetricPoint(
                name=name,
                value=self._counters[key],
                timestamp=time.time(),
                labels=labels or {},
                metric_type="counter"
            )
            
            self._add_point(key, point)
    
    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value."""
        with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value
            
            point = MetricPoint(
                name=name,
                value=value,
                timestamp=time.time(),
                labels=labels or {},
                metric_type="gauge"
            )
            
            self._add_point(key, point)
    
    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Add value to histogram metric."""
        with self._lock:
            key = self._make_key(name, labels)
            self._histograms[key].append(value)
            
            point = MetricPoint(
                name=name,
                value=value,
                timestamp=time.time(),
                labels=labels or {},
                metric_type="histogram"
            )
            
            self._add_point(key, point)
    
    def timer(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None):
        """Record a timer metric."""
        with self._lock:
            key = self._make_key(name, labels)
            self._timers[key].append(duration)
            
            point = MetricPoint(
                name=name,
                value=duration,
                timestamp=time.time(),
                labels=labels or {},
                metric_type="timer"
            )
            
            self._add_point(key, point)
    
    @contextmanager
    def time_it(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.timer(name, duration, labels)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all current metrics."""
        with self._lock:
            now = time.time()
            uptime = now - self._start_time
            
            # Calculate histogram statistics
            histogram_stats = {}
            for key, values in self._histograms.items():
                if values:
                    sorted_values = sorted(values)
                    count = len(sorted_values)
                    histogram_stats[key] = {
                        "count": count,
                        "sum": sum(sorted_values),
                        "min": sorted_values[0],
                        "max": sorted_values[-1],
                        "mean": sum(sorted_values) / count,
                        "p50": sorted_values[int(count * 0.5)],
                        "p90": sorted_values[int(count * 0.9)],
                        "p95": sorted_values[int(count * 0.95)],
                        "p99": sorted_values[int(count * 0.99)] if count >= 100 else sorted_values[-1]
                    }
            
            # Calculate timer statistics
            timer_stats = {}
            for key, durations in self._timers.items():
                if durations:
                    sorted_durations = sorted(durations)
                    count = len(sorted_durations)
                    timer_stats[key] = {
                        "count": count,
                        "total_time": sum(sorted_durations),
                        "min_time": sorted_durations[0],
                        "max_time": sorted_durations[-1],
                        "avg_time": sum(sorted_durations) / count,
                        "p50_time": sorted_durations[int(count * 0.5)],
                        "p90_time": sorted_durations[int(count * 0.9)],
                        "p95_time": sorted_durations[int(count * 0.95)],
                        "p99_time": sorted_durations[int(count * 0.99)] if count >= 100 else sorted_durations[-1]
                    }
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": uptime,
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": histogram_stats,
                "timers": timer_stats,
                "metadata": {
                    "max_history": self._max_history,
                    "total_metrics": len(self._metrics)
                }
            }
    
    def get_metric_history(self, name: str, labels: Optional[Dict[str, str]] = None, limit: int = 100) -> List[MetricPoint]:
        """Get historical data for a specific metric."""
        with self._lock:
            key = self._make_key(name, labels)
            history = self._metrics.get(key, [])
            return history[-limit:] if limit else history
    
    def reset_metric(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Reset a specific metric."""
        with self._lock:
            key = self._make_key(name, labels)
            
            # Reset based on metric type
            if key in self._counters:
                self._counters[key] = 0.0
            if key in self._gauges:
                del self._gauges[key]
            if key in self._histograms:
                self._histograms[key].clear()
            if key in self._timers:
                self._timers[key].clear()
            
            # Clear history
            if key in self._metrics:
                self._metrics[key].clear()
    
    def reset_all(self):
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()
            self._metrics.clear()
            self._start_time = time.time()
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        with self._lock:
            lines = []
            
            # Export counters
            for key, value in self._counters.items():
                name, labels_str = self._parse_key(key)
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name}{labels_str} {value}")
            
            # Export gauges
            for key, value in self._gauges.items():
                name, labels_str = self._parse_key(key)
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name}{labels_str} {value}")
            
            # Export histogram summaries
            for key, values in self._histograms.items():
                if values:
                    name, labels_str = self._parse_key(key)
                    lines.append(f"# TYPE {name} histogram")
                    lines.append(f"{name}_count{labels_str} {len(values)}")
                    lines.append(f"{name}_sum{labels_str} {sum(values)}")
            
            # Export timer summaries
            for key, durations in self._timers.items():
                if durations:
                    name, labels_str = self._parse_key(key)
                    lines.append(f"# TYPE {name}_seconds histogram")
                    lines.append(f"{name}_seconds_count{labels_str} {len(durations)}")
                    lines.append(f"{name}_seconds_sum{labels_str} {sum(durations)}")
            
            return "\n".join(lines)
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create a unique key for metric storage."""
        if not labels:
            return name
        
        # Sort labels for consistent key generation
        label_pairs = sorted(labels.items())
        label_str = ",".join(f"{k}={v}" for k, v in label_pairs)
        return f"{name}[{label_str}]"
    
    def _parse_key(self, key: str) -> tuple[str, str]:
        """Parse metric key back to name and labels string."""
        if "[" not in key:
            return key, ""
        
        name, labels_part = key.split("[", 1)
        labels_part = labels_part.rstrip("]")
        
        if not labels_part:
            return name, ""
        
        # Convert to Prometheus label format
        labels_str = "{" + labels_part + "}"
        return name, labels_str
    
    def _add_point(self, key: str, point: MetricPoint):
        """Add metric point to history."""
        history = self._metrics[key]
        history.append(point)
        
        # Trim history if needed
        if len(history) > self._max_history:
            history[:] = history[-self._max_history:]


class ApplicationMetrics:
    """High-level application metrics collector."""
    
    def __init__(self, registry: Optional[MetricsRegistry] = None):
        self.registry = registry or MetricsRegistry()
        self._start_time = time.time()
    
    # Task-related metrics
    def task_started(self, task_type: str, worker_id: str):
        """Record task start."""
        self.registry.counter("tasks_started_total", labels={"type": task_type, "worker": worker_id})
        self.registry.gauge("tasks_active", 1, labels={"type": task_type, "worker": worker_id})
    
    def task_completed(self, task_type: str, worker_id: str, duration: float, success: bool):
        """Record task completion."""
        status = "success" if success else "failure"
        labels = {"type": task_type, "worker": worker_id, "status": status}
        
        self.registry.counter("tasks_completed_total", labels=labels)
        self.registry.timer("task_duration_seconds", duration, labels={"type": task_type, "worker": worker_id})
        self.registry.gauge("tasks_active", -1, labels={"type": task_type, "worker": worker_id})
    
    def task_error(self, task_type: str, worker_id: str, error_type: str):
        """Record task error."""
        self.registry.counter("task_errors_total", labels={
            "type": task_type, 
            "worker": worker_id, 
            "error_type": error_type
        })
    
    # Account-related metrics
    def account_processed(self, task_type: str, success: bool):
        """Record account processing."""
        status = "success" if success else "failure"
        self.registry.counter("accounts_processed_total", labels={"type": task_type, "status": status})
    
    def upload_result(self, task_type: str, success: bool, file_type: str = "unknown"):
        """Record upload result."""
        status = "success" if success else "failure"
        self.registry.counter("uploads_total", labels={
            "type": task_type, 
            "status": status, 
            "file_type": file_type
        })
    
    # System metrics
    def http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request."""
        self.registry.counter("http_requests_total", labels={
            "method": method,
            "endpoint": endpoint,
            "status": str(status_code)
        })
        self.registry.timer("http_request_duration_seconds", duration, labels={
            "method": method,
            "endpoint": endpoint
        })
    
    def database_query(self, operation: str, table: str, duration: float):
        """Record database query."""
        self.registry.timer("database_query_duration_seconds", duration, labels={
            "operation": operation,
            "table": table
        })
        self.registry.counter("database_queries_total", labels={
            "operation": operation,
            "table": table
        })
    
    def resource_usage(self, cpu_percent: float, memory_mb: float, disk_usage_percent: float):
        """Record resource usage."""
        self.registry.gauge("cpu_usage_percent", cpu_percent)
        self.registry.gauge("memory_usage_mb", memory_mb)
        self.registry.gauge("disk_usage_percent", disk_usage_percent)
    
    def worker_heartbeat(self, worker_id: str, healthy: bool):
        """Record worker heartbeat."""
        self.registry.gauge("worker_healthy", 1.0 if healthy else 0.0, labels={"worker": worker_id})
        self.registry.counter("worker_heartbeats_total", labels={"worker": worker_id})
    
    # Business metrics
    def daily_upload_volume(self, count: int, file_type: str = "all"):
        """Record daily upload volume."""
        self.registry.gauge("daily_uploads", count, labels={"file_type": file_type})
    
    def active_accounts(self, count: int):
        """Record number of active accounts."""
        self.registry.gauge("active_accounts_count", count)
    
    def proxy_health(self, proxy_id: str, healthy: bool, response_time: float):
        """Record proxy health status."""
        self.registry.gauge("proxy_healthy", 1.0 if healthy else 0.0, labels={"proxy": proxy_id})
        if healthy:
            self.registry.timer("proxy_response_time_seconds", response_time, labels={"proxy": proxy_id})
    
    # Custom metrics
    def custom_counter(self, name: str, value: float = 1.0, **labels):
        """Record custom counter."""
        self.registry.counter(f"custom_{name}", value, labels)
    
    def custom_gauge(self, name: str, value: float, **labels):
        """Record custom gauge."""
        self.registry.gauge(f"custom_{name}", value, labels)
    
    def custom_timer(self, name: str, duration: float, **labels):
        """Record custom timer."""
        self.registry.timer(f"custom_{name}", duration, labels)
    
    @contextmanager
    def time_operation(self, operation_name: str, **labels):
        """Time an operation."""
        with self.registry.time_it(f"operation_{operation_name}_seconds", labels):
            yield
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        base_metrics = self.registry.get_metrics()
        
        # Add application-specific summary
        uptime = time.time() - self._start_time
        
        summary = {
            **base_metrics,
            "application": {
                "name": "bulk_worker_service",
                "version": "2.0.0",
                "uptime_seconds": uptime,
                "start_time": datetime.fromtimestamp(self._start_time).isoformat()
            }
        }
        
        return summary


# Global metrics instance
_app_metrics = ApplicationMetrics()


def get_metrics() -> ApplicationMetrics:
    """Get the global metrics instance."""
    return _app_metrics


def reset_metrics():
    """Reset all metrics (for testing)."""
    global _app_metrics
    _app_metrics = ApplicationMetrics()


# Metrics decorator
def track_execution_time(metric_name: str, **labels):
    """Decorator to track function execution time."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with get_metrics().time_operation(metric_name, **labels):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Async metrics decorator
def track_async_execution_time(metric_name: str, **labels):
    """Decorator to track async function execution time."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with get_metrics().time_operation(metric_name, **labels):
                return await func(*args, **kwargs)
        return wrapper
    return decorator