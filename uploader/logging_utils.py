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
_async_loop = None  # type: ignore

# Console silence flag
SILENT_CONSOLE = os.getenv('SILENT_CONSOLE_LOGS') == '1'
RAW_LOG_OUTPUT = os.getenv('RAW_LOG_OUTPUT') == '1'

def is_console_enabled():
    return os.getenv('SILENT_CONSOLE_LOGS') != '1'

def set_async_logger(async_logger):
    """Register AsyncLogger-like instance to mirror logs into Django cache in async mode."""
    global _async_logger
    global _async_loop
    _async_logger = async_logger
    # Capture the current running loop so other threads can schedule onto it
    try:
        _async_loop = asyncio.get_running_loop()
    except RuntimeError:
        _async_loop = None


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
    if RAW_LOG_OUTPUT:
        return message
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
    # First try same-thread scheduling
    try:
        loop = asyncio.get_running_loop()
        try:
            loop.create_task(_async_logger.log(level, message, category))
            return
        except Exception:
            pass
    except RuntimeError:
        pass
    # Fallback: schedule onto the stored async loop from any thread
    try:
        if _async_loop is not None:
            import asyncio as _aio
            _aio.run_coroutine_threadsafe(_async_logger.log(level, message, category), _async_loop)
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
        if RAW_LOG_OUTPUT:
            print(message)
        else:
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
        if RAW_LOG_OUTPUT:
            print(message)
        else:
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
        if RAW_LOG_OUTPUT:
            print(message)
        else:
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
        if RAW_LOG_OUTPUT:
            print(message)
        else:
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
        if RAW_LOG_OUTPUT:
            print(message)
        else:
            print(f"[BULK TASK WARNING] {safe_message}")


# ---- Instagrapi → Web UI bridge ----
class _WebUIForwardHandler(logging.Handler):
    """Logging handler that forwards external logger records to Web UI logs."""
    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        # Suppress non-problematic instagrapi output: forward only warnings/errors
        try:
            if record.levelno < logging.WARNING:
                return
        except Exception:
            # If anything odd with record, be conservative and continue
            pass
        try:
            message = self.format(record)
        except Exception:
            try:
                message = record.getMessage()
            except Exception:
                message = str(record)
        safe_message = safe_encode_message(message)
        try:
            web_logger = _get_web_logger_safe()
            if web_logger:
                level = record.levelname if record.levelname else 'INFO'
                category = 'API'
                # Prefix with source logger name to keep context
                prefixed = f"[{record.name}] {safe_message}"
                web_logger.log(level, prefixed, category)
        except Exception:
            pass
        # Also mirror to async logger (UI live stream)
        try:
            _mirror_to_async_logger(record.levelname or 'INFO', f"[{record.name}] {safe_message}", 'API')
        except Exception:
            pass


def attach_instagrapi_web_bridge() -> None:
    """Attach a handler to instagrapi/public/private loggers to forward messages to Web UI.
    Levels can be tuned with env:
      - INSTAGRAPI_LOG_LEVEL (default WARNING to avoid huge JSON dumps)
      - IG_HTTP_LOG_LEVEL (default WARNING)
      - FORWARD_IG_HTTP_TO_WEBUI (default 0)  # if 1, also forward HTTP logs
    """
    try:
        ig_level = os.getenv('INSTAGRAPI_LOG_LEVEL', 'WARNING').upper()  # Changed default to WARNING
        http_level = os.getenv('IG_HTTP_LOG_LEVEL', 'WARNING').upper()
        forward_http = os.getenv('FORWARD_IG_HTTP_TO_WEBUI', '0') == '1'

        handler = _WebUIForwardHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))

        # instagrapi core logger
        ig_logger = logging.getLogger('instagrapi')
        ig_logger.setLevel(getattr(logging, ig_level, logging.INFO))
        ig_logger.addHandler(handler)
        # If console is silenced, do not propagate to root handlers (avoids console spam)
        ig_logger.propagate = is_console_enabled()

        # HTTP request loggers used by instagrapi
        for name in ('public_request', 'private_request'):
            lgr = logging.getLogger(name)
            lgr.setLevel(getattr(logging, http_level, logging.WARNING))
            # Respect console silence flag for HTTP request loggers as well
            lgr.propagate = is_console_enabled()
            if forward_http:
                lgr.addHandler(handler)
    except Exception:
        # Never break main flow due to logging bridge
        pass 