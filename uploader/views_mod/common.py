"""
Shared imports and utilities for split views.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Value, Case, When, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.urls import reverse
import json
import os
import threading
import time
import traceback
from datetime import datetime, timedelta
import csv
import io
from ..models import (
    UploadTask, InstagramAccount, VideoFile, BulkUploadTask, 
    BulkUploadAccount, BulkVideo, DolphinCookieRobotTask, InstagramCookies, Proxy, VideoTitle
)
from django.contrib.auth.models import User
from ..constants import TaskStatus
from ..task_utils import (
    get_all_task_videos, get_all_task_titles, update_task_status,
    get_account_tasks, get_assigned_videos, handle_verification_error,
    handle_task_completion, handle_emergency_cleanup, process_browser_result,
    handle_account_task_error, handle_critical_task_error
)
from ..utils import validate_proxy
from ..forms import (
    UploadTaskForm, VideoUploadForm, InstagramAccountForm, ProxyForm,
    BulkUploadTaskForm, BulkVideoUploadForm, BulkTitlesUploadForm,
    BulkVideoLocationMentionsForm
)
from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
from ..tasks_playwright import run_upload_task
import logging
import io
import asyncio
import random
import string
import time
import os
import traceback
import json
import re
from datetime import timedelta
from django.core.cache import cache

logger = logging.getLogger(__name__)

def safe_log_message(message):
    """
    Remove or replace emoji characters that cause encoding issues on Windows
    """
    try:
        # Replace common emoji characters with safe alternatives
        emoji_replacements = {
            '[SEARCH]': '[SEARCH]',
            '[OK]': '[SUCCESS]',
            '[FAIL]': '[ERROR]',
            '[START]': '[START]',
            '[RETRY]': '[PROCESS]',
            '[WARN]': '[WARNING]',
            '[TOOL]': '[TOOL]',
            '🖼️': '[IMAGE]',
            '[CLIPBOARD]': '[LIST]',
            '[DELETE]': '[DELETE]',
            '📧': '[EMAIL]'
        }
        
        # Replace emoji characters with safe alternatives
        for emoji, replacement in emoji_replacements.items():
            message = message.replace(emoji, replacement)
        
        # Ensure the message only contains ASCII characters
        return message.encode('ascii', 'ignore').decode('ascii')
    except Exception:
        # If any error occurs, return a safe fallback
        return str(message).encode('ascii', 'ignore').decode('ascii')
