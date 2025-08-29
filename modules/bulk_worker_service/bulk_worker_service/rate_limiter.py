"""
Rate limiting middleware for FastAPI applications.

Provides configurable rate limiting with Redis backend support
to prevent API abuse and ensure fair resource usage.
"""

import time
import hashlib
import logging
from typing import Dict, Optional, Callable, Tuple
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class InMemoryStore:
    """In-memory rate limiting store (fallback when Redis unavailable)."""
    
    def __init__(self):
        self._store: Dict[str, Tuple[int, float]] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
    
    def increment(self, key: str, window_size: int, limit: int) -> Tuple[int, float]:
        """
        Increment counter for key within time window.
        
        Returns:
            Tuple of (current_count, reset_time)
        """
        now = time.time()
        
        # Periodic cleanup
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired(now)
            self._last_cleanup = now
        
        # Get or create counter
        if key in self._store:
            count, reset_time = self._store[key]
            
            # Check if window has expired
            if now > reset_time:
                count = 1
                reset_time = now + window_size
            else:
                count += 1
        else:
            count = 1
            reset_time = now + window_size
        
        self._store[key] = (count, reset_time)
        return count, reset_time
    
    def _cleanup_expired(self, now: float):
        """Remove expired entries."""
        expired_keys = [
            key for key, (_, reset_time) in self._store.items()
            if now > reset_time
        ]
        for key in expired_keys:
            del self._store[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired rate limit entries")


class RedisStore:
    """Redis-based rate limiting store."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/1"):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        
    def increment(self, key: str, window_size: int, limit: int) -> Tuple[int, float]:
        """
        Increment counter for key within time window using Redis.
        
        Returns:
            Tuple of (current_count, reset_time)
        """
        now = time.time()
        reset_time = now + window_size
        
        pipe = self.redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_size)
        results = pipe.execute()
        
        current_count = results[0]
        return current_count, reset_time


class RateLimitConfig:
    """Rate limit configuration."""
    
    def __init__(
        self,
        requests: int,
        window: int,  # seconds
        per: str = "ip",  # "ip", "user", "endpoint"
        key_func: Optional[Callable[[Request], str]] = None
    ):
        self.requests = requests
        self.window = window
        self.per = per
        self.key_func = key_func or self._default_key_func
    
    def _default_key_func(self, request: Request) -> str:
        """Default key generation based on 'per' setting."""
        if self.per == "ip":
            # Get client IP
            client_ip = request.client.host if request.client else "unknown"
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            return f"ip:{client_ip}"
        
        elif self.per == "user":
            # Extract user from Authorization header
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                # Use hash of token for privacy
                token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
                return f"user:{token_hash}"
            return f"anonymous:{request.client.host if request.client else 'unknown'}"
        
        elif self.per == "endpoint":
            # Rate limit per endpoint
            return f"endpoint:{request.url.path}"
        
        else:
            return f"global:all"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for FastAPI."""
    
    def __init__(
        self,
        app,
        default_config: Optional[RateLimitConfig] = None,
        store: Optional[object] = None,
        skip_on_error: bool = True
    ):
        super().__init__(app)
        self.default_config = default_config or RateLimitConfig(requests=100, window=60)
        self.endpoint_configs: Dict[str, RateLimitConfig] = {}
        self.skip_on_error = skip_on_error
        
        # Initialize store
        if store:
            self.store = store
        elif REDIS_AVAILABLE:
            try:
                self.store = RedisStore()
                logger.info("Using Redis for rate limiting")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis store: {e}")
                self.store = InMemoryStore()
                logger.info("Fallback to in-memory rate limiting")
        else:
            self.store = InMemoryStore()
            logger.info("Using in-memory rate limiting")
    
    def add_endpoint_config(self, path: str, config: RateLimitConfig):
        """Add rate limit configuration for specific endpoint."""
        self.endpoint_configs[path] = config
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting."""
        try:
            # Get configuration for this endpoint
            config = self.endpoint_configs.get(request.url.path, self.default_config)
            
            # Generate rate limit key
            key = config.key_func(request)
            full_key = f"rate_limit:{request.url.path}:{key}"
            
            # Check rate limit
            current_count, reset_time = self.store.increment(
                full_key, config.window, config.requests
            )
            
            # Check if limit exceeded
            if current_count > config.requests:
                # Calculate retry after
                retry_after = int(reset_time - time.time())
                
                # Log rate limit violation
                logger.warning(
                    f"Rate limit exceeded for {key} on {request.url.path}: "
                    f"{current_count}/{config.requests} in {config.window}s"
                )
                
                # Return rate limit error
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": config.requests,
                        "window": config.window,
                        "current": current_count,
                        "retry_after": retry_after
                    },
                    headers={"Retry-After": str(retry_after)}
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            remaining = max(0, config.requests - current_count)
            response.headers["X-RateLimit-Limit"] = str(config.requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(reset_time))
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            
            if self.skip_on_error:
                # Continue without rate limiting on error
                return await call_next(request)
            else:
                raise HTTPException(status_code=500, detail="Rate limiting service unavailable")


# Predefined configurations
STRICT_CONFIG = RateLimitConfig(requests=10, window=60, per="ip")
MODERATE_CONFIG = RateLimitConfig(requests=30, window=60, per="ip")  
LENIENT_CONFIG = RateLimitConfig(requests=100, window=60, per="ip")

# Endpoint-specific configurations
TASK_START_CONFIG = RateLimitConfig(requests=5, window=60, per="user")
HEALTH_CHECK_CONFIG = RateLimitConfig(requests=200, window=60, per="ip")
METRICS_CONFIG = RateLimitConfig(requests=20, window=60, per="user")


def create_rate_limiter(
    redis_url: Optional[str] = None,
    default_requests: int = 100,
    default_window: int = 60
) -> RateLimitMiddleware:
    """
    Create a configured rate limiter.
    
    Args:
        redis_url: Redis connection URL (optional)
        default_requests: Default request limit
        default_window: Default time window in seconds
        
    Returns:
        Configured RateLimitMiddleware
    """
    default_config = RateLimitConfig(requests=default_requests, window=default_window)
    
    store = None
    if redis_url and REDIS_AVAILABLE:
        try:
            store = RedisStore(redis_url)
        except Exception as e:
            logger.warning(f"Failed to create Redis store: {e}")
    
    middleware = RateLimitMiddleware(
        app=None,  # Will be set by FastAPI
        default_config=default_config,
        store=store
    )
    
    # Configure specific endpoints
    middleware.add_endpoint_config("/api/v1/bulk-upload/start", TASK_START_CONFIG)
    middleware.add_endpoint_config("/api/v1/bulk-login/start", TASK_START_CONFIG)
    middleware.add_endpoint_config("/api/v1/warmup/start", TASK_START_CONFIG)
    middleware.add_endpoint_config("/api/v1/avatar/start", TASK_START_CONFIG)
    middleware.add_endpoint_config("/api/v1/bio/start", TASK_START_CONFIG)
    middleware.add_endpoint_config("/api/v1/follow/start", TASK_START_CONFIG)
    middleware.add_endpoint_config("/api/v1/proxy-diagnostics/start", TASK_START_CONFIG)
    middleware.add_endpoint_config("/api/v1/media-uniq/start", TASK_START_CONFIG)
    middleware.add_endpoint_config("/api/v1/cookie-robot/start", TASK_START_CONFIG)
    
    middleware.add_endpoint_config("/api/v1/health", HEALTH_CHECK_CONFIG)
    middleware.add_endpoint_config("/api/v1/health/simple", HEALTH_CHECK_CONFIG)
    middleware.add_endpoint_config("/api/v1/metrics", METRICS_CONFIG)
    
    return middleware


# Rate limiting decorator for individual endpoints
def rate_limit(requests: int, window: int, per: str = "ip", key_func: Optional[Callable] = None):
    """
    Decorator for applying rate limits to individual FastAPI endpoints.
    
    Args:
        requests: Number of requests allowed
        window: Time window in seconds
        per: Rate limit scope ("ip", "user", "endpoint")
        key_func: Custom key generation function
    """
    def decorator(func):
        # Store rate limit config on function
        func._rate_limit_config = RateLimitConfig(requests, window, per, key_func)
        return func
    return decorator