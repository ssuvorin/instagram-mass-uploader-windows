"""
Lightweight in-process metrics counters (non-invasive).
Use metrics.inc("RUNNER:process_account:ok") or metrics.inc("SERVICES:update_account:error").
"""
from typing import Dict
from threading import Lock

class _Metrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Dict[str, int] = {}

    def inc(self, key: str, value: int = 1) -> None:
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counters)

metrics = _Metrics()

__all__ = ["metrics"]
