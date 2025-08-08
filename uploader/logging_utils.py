"""
Logging utilities for Instagram uploader
Centralized logging functions to avoid circular imports
"""

import logging
import sys
import os
from typing import Optional

# Setup logger
logger = logging.getLogger('uploader.bulk_tasks')


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
        target_encoding = getattr(sys.stdout, 'encoding', None) or os.environ.get('PYTHONIOENCODING') or 'utf-8'
        # Re-encode to the target console encoding with replacement for unsupported chars
        return message.encode(target_encoding, errors='replace').decode(target_encoding, errors='replace')
    except Exception:
        # Last resort - keep only ASCII to guarantee no encoding errors
        return ''.join(char for char in message if ord(char) < 128)


def log_info(message: str, category: Optional[str] = None):
    """Log message to both logger, console, and WebLogger (if available)."""
    safe_message = safe_encode_message(message)
    try:
        web_logger = _get_web_logger_safe()
        if web_logger:
            web_logger.log('INFO', safe_message, category)
    except Exception:
        pass
    logger.info(safe_message)
    print(f"[BULK TASK] {safe_message}")


def log_success(message: str, category: Optional[str] = None):
    """Log success message to both logger, console, and WebLogger (if available)."""
    safe_message = safe_encode_message(message)
    try:
        web_logger = _get_web_logger_safe()
        if web_logger:
            web_logger.log('SUCCESS', safe_message, category)
    except Exception:
        pass
    logger.info(safe_message)
    print(f"[BULK TASK SUCCESS] {safe_message}")


def log_error(message: str, category: Optional[str] = None):
    """Log error to both logger, console, and WebLogger (if available)."""
    safe_message = safe_encode_message(message)
    try:
        web_logger = _get_web_logger_safe()
        if web_logger:
            web_logger.log('ERROR', safe_message, category)
    except Exception:
        pass
    logger.error(safe_message)
    print(f"[BULK TASK ERROR] {safe_message}")


def log_debug(message: str, category: Optional[str] = None):
    """Log debug message to both logger, console, and WebLogger (if available)."""
    safe_message = safe_encode_message(message)
    try:
        web_logger = _get_web_logger_safe()
        if web_logger:
            web_logger.log('DEBUG', safe_message, category)
    except Exception:
        pass
    logger.debug(safe_message)
    print(f"[BULK TASK DEBUG] {safe_message}")


def log_warning(message: str, category: Optional[str] = None):
    """Log warning to both logger, console, and WebLogger (if available)."""
    safe_message = safe_encode_message(message)
    try:
        web_logger = _get_web_logger_safe()
        if web_logger:
            web_logger.log('WARNING', safe_message, category)
    except Exception:
        pass
    logger.warning(safe_message)
    print(f"[BULK TASK WARNING] {safe_message}") 