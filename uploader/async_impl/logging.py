"""Shared logging setup for async_impl"""
import logging
import sys
import os

# Get the project root directory for django.log
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
django_log_path = os.path.join(project_root, 'django.log')

logger = logging.getLogger("uploader")
if not logger.handlers:
    # Console handler
    handler = logging.StreamHandler(stream=sys.stdout)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    
    # File handler - write to django.log
    file_handler = logging.FileHandler(django_log_path, encoding='utf-8')
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    
    logger.setLevel(logging.INFO)
