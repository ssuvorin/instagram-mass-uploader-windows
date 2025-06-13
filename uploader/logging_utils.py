"""
Logging utilities for Instagram uploader
Centralized logging functions to avoid circular imports
"""

import logging

# Setup logger
logger = logging.getLogger('uploader.bulk_tasks')

def log_info(message):
    """Log message to both logger and print to console"""
    logger.info(message)
    print(f"[BULK TASK] {message}")

def log_success(message):
    """Log success message to both logger and print to console"""
    logger.info(message)
    print(f"[BULK TASK SUCCESS] {message}")

def log_error(message):
    """Log error to both logger and print to console"""
    logger.error(message)
    print(f"[BULK TASK ERROR] {message}")

def log_debug(message):
    """Log debug message to both logger and print to console"""
    logger.debug(message)
    print(f"[BULK TASK DEBUG] {message}")

def log_warning(message):
    """Log warning to both logger and print to console"""
    logger.warning(message)
    print(f"[BULK TASK WARNING] {message}") 