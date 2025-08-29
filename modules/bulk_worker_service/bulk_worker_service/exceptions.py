from __future__ import annotations
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class WorkerServiceError(Exception):
    """Base exception for worker service errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class JobNotFoundError(WorkerServiceError):
    """Raised when job is not found."""
    pass


class InvalidTaskTypeError(WorkerServiceError):
    """Raised when task type is not supported."""
    pass


class JobExecutionError(WorkerServiceError):
    """Raised when job execution fails."""
    pass


class ConfigurationError(WorkerServiceError):
    """Raised when configuration is invalid."""
    pass


class UiClientError(WorkerServiceError):
    """Raised when UI client communication fails."""
    pass


class ValidationError(WorkerServiceError):
    """Raised when validation fails."""
    pass


class ResourceNotAvailableError(WorkerServiceError):
    """Raised when required resource is not available."""
    pass


class TimeoutError(WorkerServiceError):
    """Raised when operation times out."""
    pass


class AuthenticationError(WorkerServiceError):
    """Raised when authentication fails."""
    pass


class RateLimitError(WorkerServiceError):
    """Raised when rate limit is exceeded."""
    pass


class ErrorHandler:
    """Centralized error handling and logging."""
    
    @staticmethod
    def handle_job_error(job_id: str, error: Exception, context: Optional[Dict[str, Any]] = None) -> WorkerServiceError:
        """Handle and convert job execution errors."""
        context = context or {}
        
        # Log the error with context
        logger.error(
            f"Job {job_id} failed: {error}",
            extra={
                "job_id": job_id,
                "error_type": type(error).__name__,
                "context": context
            },
            exc_info=True
        )
        
        # Convert to appropriate worker service error
        if isinstance(error, WorkerServiceError):
            return error
        elif isinstance(error, TimeoutError):
            return TimeoutError(f"Job {job_id} timed out: {error}")
        elif isinstance(error, ConnectionError):
            return UiClientError(f"Connection failed for job {job_id}: {error}")
        elif isinstance(error, ValueError):
            return ValidationError(f"Validation failed for job {job_id}: {error}")
        else:
            return JobExecutionError(f"Job {job_id} execution failed: {error}")
    
    @staticmethod
    def handle_validation_error(field: str, value: Any, reason: str) -> ValidationError:
        """Handle validation errors."""
        message = f"Validation failed for {field}: {reason}"
        details = {"field": field, "value": str(value), "reason": reason}
        
        logger.warning(message, extra=details)
        return ValidationError(message, details=details)
    
    @staticmethod
    def handle_configuration_error(config_key: str, reason: str) -> ConfigurationError:
        """Handle configuration errors."""
        message = f"Configuration error for {config_key}: {reason}"
        details = {"config_key": config_key, "reason": reason}
        
        logger.error(message, extra=details)
        return ConfigurationError(message, details=details)
    
    @staticmethod
    def handle_ui_client_error(operation: str, error: Exception) -> UiClientError:
        """Handle UI client communication errors."""
        message = f"UI client operation '{operation}' failed: {error}"
        details = {"operation": operation, "original_error": str(error)}
        
        logger.error(message, extra=details, exc_info=True)
        return UiClientError(message, details=details)


class RetryableError(WorkerServiceError):
    """Base class for errors that can be retried."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, max_retries: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        self.max_retries = max_retries


class NetworkError(RetryableError):
    """Network-related error that can be retried."""
    pass


class TemporaryServiceError(RetryableError):
    """Temporary service error that can be retried."""
    pass


def handle_exceptions(func):
    """Decorator for handling exceptions in async functions."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except WorkerServiceError:
            # Re-raise worker service errors as-is
            raise
        except Exception as e:
            # Convert other exceptions to worker service errors
            logger.exception(f"Unhandled exception in {func.__name__}")
            raise JobExecutionError(f"Unhandled error in {func.__name__}: {e}")
    
    return wrapper


class CircuitBreaker:
    """Circuit breaker pattern for handling repeated failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise TemporaryServiceError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        import time
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed call."""
        import time
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"