"""
Django initialization for Worker Service

This module initializes Django for the worker service to enable
database access and model operations.
"""

import os
import django
from django.conf import settings

def init_django():
    """Initialize Django for worker service"""
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bulk_worker_service.django_settings')
        django.setup()

# Auto-initialize when this module is imported
init_django()