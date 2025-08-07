"""
Logging utilities for Instagram uploader
Centralized logging functions to avoid circular imports
"""

import logging
import sys
import os

# Setup logger
logger = logging.getLogger('uploader.bulk_tasks')

def safe_encode_message(message):
    """Safely encode message for Windows compatibility"""
    try:
        # Try to encode with UTF-8 first
        return message.encode('utf-8').decode('utf-8')
    except UnicodeEncodeError:
        # If UTF-8 fails, try to replace problematic characters
        try:
            return message.encode('utf-8', errors='replace').decode('utf-8')
        except:
            # Last resort - remove all non-ASCII characters
            return ''.join(char for char in message if ord(char) < 128)

def log_info(message):
    """Log message to both logger and print to console"""
    safe_message = safe_encode_message(message)
    logger.info(safe_message)
    print(f"[BULK TASK] {safe_message}")

def log_success(message):
    """Log success message to both logger and print to console"""
    safe_message = safe_encode_message(message)
    logger.info(safe_message)
    print(f"[BULK TASK SUCCESS] {safe_message}")

def log_error(message):
    """Log error to both logger and print to console"""
    safe_message = safe_encode_message(message)
    logger.error(safe_message)
    print(f"[BULK TASK ERROR] {safe_message}")

def log_debug(message):
    """Log debug message to both logger and print to console"""
    safe_message = safe_encode_message(message)
    logger.debug(safe_message)
    print(f"[BULK TASK DEBUG] {safe_message}")

def log_warning(message):
    """Log warning to both logger and print to console"""
    safe_message = safe_encode_message(message)
    logger.warning(safe_message)
    print(f"[BULK TASK WARNING] {safe_message}") 