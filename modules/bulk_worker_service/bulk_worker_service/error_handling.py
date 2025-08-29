"""
Comprehensive Error Handling and Logging System
Following SOLID, CLEAN, KISS, DRY, and OOP principles.
"""

from __future__ import annotations
import os
import sys
import time
import traceback
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
import asyncio


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    NETWORK = "NETWORK"
    DATABASE = "DATABASE" 
    AUTHENTICATION = "AUTHENTICATION"
    VALIDATION = "VALIDATION"
    BUSINESS_LOGIC = "BUSINESS_LOGIC"
    SYSTEM = "SYSTEM"
    EXTERNAL_API = "EXTERNAL_API"


@dataclass
class ErrorContext:
    """Context information for error handling"""
    operation: str
    worker_id: str
    task_id: Optional[int] = None
    account_id: Optional[int] = None
    request_id: Optional[str] = None
    additional_data: Optional[Dict] = None


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: float
    level: LogLevel
    message: str
    operation: str
    worker_id: str
    category: Optional[ErrorCategory] = None
    task_id: Optional[int] = None
    account_id: Optional[int] = None
    error_details: Optional[str] = None
    stack_trace: Optional[str] = None


class ILogger(ABC):
    """Interface for logging operations"""
    
    @abstractmethod
    async def log(self, entry: LogEntry) -> None:
        pass
    
    @abstractmethod
    async def log_error(self, error: Exception, context: ErrorContext) -> None:
        pass
    
    @abstractmethod
    async def log_info(self, message: str, context: ErrorContext) -> None:
        pass


class IErrorHandler(ABC):
    """Interface for error handling operations"""
    
    @abstractmethod
    async def handle_error(
        self, 
        error: Exception, 
        context: ErrorContext,
        retry_count: int = 0
    ) -> bool:
        """Handle error and return True if operation should be retried"""
        pass
    
    @abstractmethod
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize the error type"""
        pass


class StandardLogger(ILogger):
    """Standard logging implementation with file and console output"""
    
    def __init__(self, log_file: Optional[str] = None):
        self.logger = logging.getLogger("worker_logger")
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
    
    async def log(self, entry: LogEntry) -> None:
        """Log structured entry"""
        extra_info = f"[Worker: {entry.worker_id}]"
        if entry.task_id:
            extra_info += f"[Task: {entry.task_id}]"
        if entry.account_id:
            extra_info += f"[Account: {entry.account_id}]"
        if entry.category:
            extra_info += f"[{entry.category.value}]"
        
        log_message = f"{extra_info} {entry.operation}: {entry.message}"
        
        if entry.error_details:
            log_message += f" | Error: {entry.error_details}"
        
        level_map = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }
        
        self.logger.log(level_map[entry.level], log_message)
        
        if entry.stack_trace and entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            self.logger.log(level_map[entry.level], f"Stack trace: {entry.stack_trace}")
    
    async def log_error(self, error: Exception, context: ErrorContext) -> None:
        """Log error with context"""
        entry = LogEntry(
            timestamp=time.time(),
            level=LogLevel.ERROR,
            message=str(error),
            operation=context.operation,
            worker_id=context.worker_id,
            task_id=context.task_id,
            account_id=context.account_id,
            error_details=str(error),
            stack_trace=traceback.format_exc()
        )
        await self.log(entry)
    
    async def log_info(self, message: str, context: ErrorContext) -> None:
        """Log info message with context"""
        entry = LogEntry(
            timestamp=time.time(),
            level=LogLevel.INFO,
            message=message,
            operation=context.operation,
            worker_id=context.worker_id,
            task_id=context.task_id,
            account_id=context.account_id
        )
        await self.log(entry)


class StandardErrorHandler(IErrorHandler):
    """Standard error handler with categorization and retry logic"""
    
    def __init__(self, logger: ILogger, max_retries: int = 3):
        self.logger = logger
        self.max_retries = max_retries
        self.retry_delays = [1, 2, 5, 10]  # Exponential backoff
    
    async def handle_error(
        self, 
        error: Exception, 
        context: ErrorContext,
        retry_count: int = 0
    ) -> bool:
        """Handle error with retry logic"""
        category = self.categorize_error(error)
        
        # Log the error
        log_entry = LogEntry(
            timestamp=time.time(),
            level=LogLevel.ERROR,
            message=str(error),
            operation=context.operation,
            worker_id=context.worker_id,
            category=category,
            task_id=context.task_id,
            account_id=context.account_id,
            error_details=str(error),
            stack_trace=traceback.format_exc()
        )
        await self.logger.log(log_entry)
        
        # Determine if retry is appropriate
        should_retry = self._should_retry(error, category, retry_count)
        
        if should_retry and retry_count < self.max_retries:
            delay = self.retry_delays[min(retry_count, len(self.retry_delays) - 1)]
            await self.logger.log_info(
                f"Retrying operation after {delay}s (attempt {retry_count + 1}/{self.max_retries})",
                context
            )
            await asyncio.sleep(delay)
            return True
        
        return False
    
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error based on type and message"""
        error_str = str(error).lower()
        
        if isinstance(error, (ConnectionError, TimeoutError)) or "timeout" in error_str or "connection" in error_str:
            return ErrorCategory.NETWORK
        elif "database" in error_str or "sql" in error_str:
            return ErrorCategory.DATABASE
        elif "authentication" in error_str or "401" in error_str or "403" in error_str:
            return ErrorCategory.AUTHENTICATION
        elif "validation" in error_str or "invalid" in error_str:
            return ErrorCategory.VALIDATION
        elif "api" in error_str or "http" in error_str:
            return ErrorCategory.EXTERNAL_API
        else:
            return ErrorCategory.SYSTEM
    
    def _should_retry(self, error: Exception, category: ErrorCategory, retry_count: int) -> bool:
        """Determine if error should trigger retry"""
        # Don't retry validation or authentication errors
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.VALIDATION]:
            return False
        
        # Retry network and external API errors
        if category in [ErrorCategory.NETWORK, ErrorCategory.EXTERNAL_API]:
            return True
        
        # Retry database errors with caution
        if category == ErrorCategory.DATABASE and retry_count < 2:
            return True
        
        return False


class ErrorHandlingMixin:
    """Mixin class for adding error handling to other classes"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._error_handler: Optional[IErrorHandler] = None
        self._logger: Optional[ILogger] = None
    
    def set_error_handler(self, error_handler: IErrorHandler) -> None:
        self._error_handler = error_handler
    
    def set_logger(self, logger: ILogger) -> None:
        self._logger = logger
    
    async def handle_error_safely(
        self, 
        error: Exception, 
        context: ErrorContext,
        retry_count: int = 0
    ) -> bool:
        """Handle error safely with fallback"""
        if self._error_handler:
            return await self._error_handler.handle_error(error, context, retry_count)
        else:
            # Fallback logging
            print(f"ERROR in {context.operation}: {str(error)}")
            return False
    
    async def log_safely(self, message: str, context: ErrorContext) -> None:
        """Log message safely with fallback"""
        if self._logger:
            await self._logger.log_info(message, context)
        else:
            print(f"INFO: {message}")


def with_error_handling(
    operation_name: str,
    max_retries: int = 3,
    create_context: Optional[Callable] = None
):
    """Decorator for adding comprehensive error handling to functions"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            worker_id = kwargs.get('worker_id', 'unknown')
            
            if create_context:
                context = create_context(*args, **kwargs)
            else:
                context = ErrorContext(
                    operation=operation_name,
                    worker_id=worker_id
                )
            
            # Get error handler from first argument if it has one
            error_handler = None
            logger = None
            
            if args and hasattr(args[0], '_error_handler'):
                error_handler = args[0]._error_handler
                logger = args[0]._logger
            
            retry_count = 0
            while retry_count <= max_retries:
                try:
                    if logger:
                        await logger.log_info(f"Starting {operation_name}", context)
                    
                    result = await func(*args, **kwargs)
                    
                    if logger:
                        await logger.log_info(f"Completed {operation_name}", context)
                    
                    return result
                    
                except Exception as e:
                    should_retry = False
                    
                    if error_handler:
                        should_retry = await error_handler.handle_error(e, context, retry_count)
                    else:
                        print(f"ERROR in {operation_name}: {str(e)}")
                    
                    if should_retry and retry_count < max_retries:
                        retry_count += 1
                        continue
                    else:
                        raise
            
        return wrapper
    return decorator


class ErrorHandlingFactory:
    """Factory for creating error handling components"""
    
    @staticmethod
    def create_logger(log_file: Optional[str] = None) -> ILogger:
        return StandardLogger(log_file)
    
    @staticmethod
    def create_error_handler(logger: ILogger, max_retries: int = 3) -> IErrorHandler:
        return StandardErrorHandler(logger, max_retries)
    
    @staticmethod
    def create_context(
        operation: str, 
        worker_id: str,
        task_id: Optional[int] = None,
        account_id: Optional[int] = None
    ) -> ErrorContext:
        return ErrorContext(
            operation=operation,
            worker_id=worker_id,
            task_id=task_id,
            account_id=account_id
        )


# Singleton factory instance
error_handling_factory = ErrorHandlingFactory()