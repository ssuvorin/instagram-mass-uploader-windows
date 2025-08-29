"""
Models for UI Core - Minimal models for distributed architecture.

Since this UI module communicates with backend services via APIs,
most data models are not needed here. Only local UI state if necessary.
"""

from django.db import models

# For now, no local models needed as we use API communication
# This file exists to satisfy Django app requirements