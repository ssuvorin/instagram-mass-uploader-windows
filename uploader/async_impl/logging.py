"""Shared logging setup for async_impl"""
import logging
import sys

logger = logging.getLogger("uploader")
if not logger.handlers:
    handler = logging.StreamHandler(stream=sys.stdout)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
