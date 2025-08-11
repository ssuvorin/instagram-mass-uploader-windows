"""
Logging utilities for Instagram uploader
Centralized logging functions to avoid circular imports
"""

import logging
import sys
import os
from typing import Optional
import asyncio

# Setup logger
logger = logging.getLogger('uploader.bulk_tasks')

# Async logger bridge (used in async mode)
_async_logger = None  # type: ignore

# Console silence flag
SILENT_CONSOLE = os.getenv('SILENT_CONSOLE_LOGS') == '1'

def is_console_enabled():
    return os.getenv('SILENT_CONSOLE_LOGS') != '1'

def set_async_logger(async_logger):
    """Register AsyncLogger-like instance to mirror logs into Django cache in async mode."""
    global _async_logger
    _async_logger = async_logger


def _get_web_logger_safe():
    """Attempt to get WebLogger instance without hard dependency."""
    try:
        # Local import to avoid circular dependency at module import time
        from .bulk_tasks_playwright import get_web_logger  # type: ignore
        return get_web_logger()
    except Exception:
        return None


def safe_encode_message(message):
    """Safely encode message for Windows console compatibility (cp1252, etc.)."""
    try:
        # On Windows consoles (often cp1252), strip to ASCII to avoid UnicodeEncodeError
        if os.name == 'nt':
            return ''.join(char for char in message if ord(char) < 128)
        # Else, use the active stderr/stdout encoding with replacement
        target_encoding = (
            getattr(sys.stderr, 'encoding', None)
            or getattr(sys.stdout, 'encoding', None)
            or os.environ.get('PYTHONIOENCODING')
            or 'utf-8'
        )
        return message.encode(target_encoding, errors='replace').decode(target_encoding, errors='replace')
    except Exception:
        # Last resort - keep only ASCII
        return ''.join(char for char in message if ord(char) < 128)


def _mirror_to_async_logger(level: str, message: str, category: Optional[str] = None):
    """Schedule mirroring to AsyncLogger if configured and event loop is running."""
    if _async_logger is None:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    try:
        loop.create_task(_async_logger.log(level, message, category))
    except Exception:
        pass


def log_info(message: str, category: Optional[str] = None):
    """Log message to both logger, console, and WebLogger/AsyncLogger (if available)."""
    safe_message = safe_encode_message(message)
    try:
        web_logger = _get_web_logger_safe()
        if web_logger:
            web_logger.log('INFO', safe_message, category)
    except Exception:
        pass
    _mirror_to_async_logger('INFO', safe_message, category)
    logger.info(safe_message)
    if not SILENT_CONSOLE:
        print(f"[BULK TASK] {safe_message}")


def log_success(message: str, category: Optional[str] = None):
    """Log success message to both logger, console, and WebLogger/AsyncLogger (if available)."""
    safe_message = safe_encode_message(message)
    try:
        web_logger = _get_web_logger_safe()
        if web_logger:
            web_logger.log('SUCCESS', safe_message, category)
    except Exception:
        pass
    _mirror_to_async_logger('SUCCESS', safe_message, category)
    logger.info(safe_message)
    if not SILENT_CONSOLE:
        print(f"[BULK TASK SUCCESS] {safe_message}")


def log_error(message: str, category: Optional[str] = None):
    """Log error to both logger, console, and WebLogger/AsyncLogger (if available)."""
    safe_message = safe_encode_message(message)
    try:
        web_logger = _get_web_logger_safe()
        if web_logger:
            web_logger.log('ERROR', safe_message, category)
    except Exception:
        pass
    _mirror_to_async_logger('ERROR', safe_message, category)
    logger.error(safe_message)
    if not SILENT_CONSOLE:
        print(f"[BULK TASK ERROR] {safe_message}")


def log_debug(message: str, category: Optional[str] = None):
    """Log debug message to both logger, console, and WebLogger/AsyncLogger (if available)."""
    safe_message = safe_encode_message(message)
    try:
        web_logger = _get_web_logger_safe()
        if web_logger:
            web_logger.log('DEBUG', safe_message, category)
    except Exception:
        pass
    _mirror_to_async_logger('DEBUG', safe_message, category)
    logger.debug(safe_message)
    if not SILENT_CONSOLE:
        print(f"[BULK TASK DEBUG] {safe_message}")


def log_warning(message: str, category: Optional[str] = None):
    """Log warning to both logger, console, and WebLogger/AsyncLogger (if available)."""
    safe_message = safe_encode_message(message)
    try:
        web_logger = _get_web_logger_safe()
        if web_logger:
            web_logger.log('WARNING', safe_message, category)
    except Exception:
        pass
    _mirror_to_async_logger('WARNING', safe_message, category)
    logger.warning(safe_message)
    if not SILENT_CONSOLE:
        print(f"[BULK TASK WARNING] {safe_message}") 