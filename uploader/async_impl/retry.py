"""
Async retry helpers.
Not applied by default to avoid behavior changes. Use explicitly where needed.
"""
import asyncio
from typing import Callable, Awaitable, Type, Tuple

async def retry_async(
    fn: Callable[..., Awaitable],
    *args,
    tries: int = 1,
    delay: float = 0.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    **kwargs,
):
    last_exc = None
    for attempt in range(1, max(1, tries) + 1):
        try:
            return await fn(*args, **kwargs)
        except exceptions as e:
            last_exc = e
            if attempt < tries:
                await asyncio.sleep(delay)
    if last_exc:
        raise last_exc

def retryable(tries: int = 1, delay: float = 0.0, exceptions: Tuple[Type[BaseException], ...] = (Exception,)):
    def deco(func: Callable[..., Awaitable]):
        async def wrapper(*args, **kwargs):
            return await retry_async(func, *args, tries=tries, delay=delay, exceptions=exceptions, **kwargs)
        return wrapper
    return deco

__all__ = ["retry_async", "retryable"]
