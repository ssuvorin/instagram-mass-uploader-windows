"""
Provider registry for file input discovery strategies.
Existing functions remain unchanged. v2 uses this registry.
"""
from typing import Callable, List, Awaitable, Any

Strategy = Callable[..., Awaitable[Any]]
_registry: List[Strategy] = []

def register(provider: Strategy) -> None:
    _registry.append(provider)

def strategies() -> List[Strategy]:
    return list(_registry)

__all__ = ["register", "strategies", "Strategy"]
