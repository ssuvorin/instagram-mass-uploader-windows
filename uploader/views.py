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
from .models import (
    UploadTask, InstagramAccount, VideoFile, BulkUploadTask, 
    BulkUploadAccount, BulkVideo, DolphinCookieRobotTask, InstagramCookies, Proxy, VideoTitle
)
from django.contrib.auth.models import User
from .constants import TaskStatus
from .task_utils import (
    get_all_task_videos, get_all_task_titles, update_task_status,
    get_account_tasks, get_assigned_videos, handle_verification_error,
    handle_task_completion, handle_emergency_cleanup, process_browser_result,
    handle_account_task_error, handle_critical_task_error
)
from .utils import validate_proxy
from .forms import (
    UploadTaskForm, VideoUploadForm, InstagramAccountForm, ProxyForm,
    BulkUploadTaskForm, BulkVideoUploadForm, BulkTitlesUploadForm,
    BulkVideoLocationMentionsForm
)
from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
from .tasks_playwright import run_upload_task

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

@login_required
def dashboard(request):
    """Dashboard with recent tasks and accounts"""
    tasks = UploadTask.objects.order_by('-created_at')[:10]
    accounts = InstagramAccount.objects.order_by('-last_used')[:10]
    
    # Get counts for dashboard stats
    tasks_count = UploadTask.objects.count()
    accounts_count = InstagramAccount.objects.count()
    proxies_count = Proxy.objects.count()
    completed_tasks_count = UploadTask.objects.filter(status='COMPLETED').count()
    
    # Get proxy stats
    active_proxies_count = Proxy.objects.filter(is_active=True).count()
    
    # Get proxy stats by status
    proxy_status_counts = {
        'active': Proxy.objects.filter(status='active').count(),
        'inactive': Proxy.objects.filter(status='inactive').count(),
        'banned': Proxy.objects.filter(status='banned').count(),
        'checking': Proxy.objects.filter(status='checking').count()
    }
    
    # Get proxy stats by type
    proxy_type_counts = {
        'http': Proxy.objects.filter(proxy_type='HTTP').count(),
        'socks5': Proxy.objects.filter(proxy_type='SOCKS5').count(),
        'https': Proxy.objects.filter(proxy_type='HTTPS').count()
    }
    
    # Get recently verified proxies
    recently_verified_proxies = Proxy.objects.filter(
        last_verified__isnull=False
    ).order_by('-last_verified')[:5]
    
    # Get inactive proxies statistics for cleanup recommendations
    inactive_proxies_total = Proxy.objects.filter(
        Q(status='inactive') | Q(is_active=False)
    ).count()
    
    inactive_proxies_assigned = Proxy.objects.filter(
        Q(status='inactive') | Q(is_active=False),
        assigned_account__isnull=False
    ).count()
    
    inactive_proxies_unassigned = inactive_proxies_total - inactive_proxies_assigned
    
    context = {
        'tasks': tasks,
        'accounts': accounts,
        'tasks_count': tasks_count,
        'accounts_count': accounts_count,
        'proxies_count': proxies_count,
        'completed_tasks_count': completed_tasks_count,
        'active_proxies_count': active_proxies_count,
        'recently_verified_proxies': recently_verified_proxies,
        'proxy_status_counts': proxy_status_counts,
        'proxy_type_counts': proxy_type_counts,
        'inactive_proxies_total': inactive_proxies_total,
        'inactive_proxies_assigned': inactive_proxies_assigned,
        'inactive_proxies_unassigned': inactive_proxies_unassigned,
        'active_tab': 'dashboard'
    }
    return render(request, 'uploader/dashboard.html', context)

@login_required
def task_list(request):
    """List all tasks with filtering and pagination"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    tasks = UploadTask.objects.order_by('-created_at')
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    if search_query:
        tasks = tasks.filter(
            Q(account__username__icontains=search_query) |
            Q(log__icontains=search_query)
        )
    
    context = {
        'tasks': tasks,
        'status_filter': status_filter,
        'search_query': search_query,
        'active_tab': 'tasks'
    }
    return render(request, 'uploader/task_list.html', context)

@login_required
def task_detail(request, task_id):
    """View details of a specific task"""
    task = get_object_or_404(UploadTask, id=task_id)
    
    context = {
        'task': task,
        'active_tab': 'tasks'
    }
    return render(request, 'uploader/task_detail.html', context)

@login_required
def create_task(request):
    """Create a new upload task"""
    if request.method == 'POST':
        form = UploadTaskForm(request.POST)
        files_form = VideoUploadForm(request.POST, request.FILES)
        
        if form.is_valid() and files_form.is_valid():
            # Create task
            task = form.save(commit=False)
            task.status = 'PENDING'
            task.save()
            
            # Handle video file
            video_file = files_form.cleaned_data['video_file']
            VideoFile.objects.create(
                task=task,
                video_file=video_file,
                caption=form.cleaned_data.get('caption', '')
            )
            
            messages.success(request, f'Task created successfully! Task ID: {task.id}')
            
            # Start task in background thread
            if form.cleaned_data.get('start_immediately', False):
                thread = threading.Thread(target=run_upload_task, args=(task.id,))
                thread.daemon = True
                thread.start()
                messages.info(request, 'Task started in background.')
            
            return redirect('task_detail', task_id=task.id)
    else:
        form = UploadTaskForm()
        files_form = VideoUploadForm()
    
    context = {
        'form': form,
        'files_form': files_form,
        'active_tab': 'create_task'
    }
    return render(request, 'uploader/create_task.html', context)

@require_POST
@login_required
def start_task(request, task_id):
    """Start a pending task"""
    task = get_object_or_404(UploadTask, id=task_id)
    
    if task.status != 'PENDING':
        messages.error(request, 'Only pending tasks can be started.')
        return redirect('task_detail', task_id=task.id)
    
    thread = threading.Thread(target=run_upload_task, args=(task.id,))
    thread.daemon = True
    thread.start()
    
    messages.success(request, f'Task {task.id} started!')
    return redirect('task_detail', task_id=task.id)

@login_required
def account_list(request):
    """List all Instagram accounts"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    # Sort by creation date descending (newest first) for consistency
    accounts = (
        InstagramAccount.objects.order_by('-created_at')
        .annotate(
            uploaded_success_total=Coalesce(Sum('bulk_uploads__uploaded_success_count'), Value(0)),
            uploaded_failed_total=Coalesce(Sum('bulk_uploads__uploaded_failed_count'), Value(0)),
        )
    )
    
    if status_filter:
        accounts = accounts.filter(status=status_filter)
    
    if search_query:
        accounts = accounts.filter(
            Q(username__icontains=search_query) |
            Q(email_username__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    context = {
        'accounts': accounts,
        'status_filter': status_filter,
        'search_query': search_query,
        'active_tab': 'accounts'
    }
    return render(request, 'uploader/account_list.html', context)

@login_required
def account_detail(request, account_id):
    """View details of a specific account"""
    account = get_object_or_404(
        InstagramAccount.objects.annotate(
            uploaded_success_total=Coalesce(Sum('bulk_uploads__uploaded_success_count'), Value(0)),
            uploaded_failed_total=Coalesce(Sum('bulk_uploads__uploaded_failed_count'), Value(0)),
        ),
        id=account_id,
    )
    tasks = account.tasks.order_by('-created_at')
    
    context = {
        'account': account,
        'tasks': tasks,
        'active_tab': 'accounts'
    }
    return render(request, 'uploader/account_detail.html', context)

@login_required
def delete_account(request, account_id):
    """Delete an Instagram account"""
    account = get_object_or_404(InstagramAccount, id=account_id)
    
    if request.method == 'POST':
        # Store account info for message
        account_name = account.username
        dolphin_profile_id = account.dolphin_profile_id
        
        try:
            # Delete Dolphin profile if it exists
            if dolphin_profile_id:
                try:
                    logger.info(f"[DELETE ACCOUNT] Attempting to delete Dolphin profile {dolphin_profile_id} for account {account_name}")
                    api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
                    if api_key:
                        # Get Dolphin API host from environment (critical for Docker Windows deployment)
                        dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
                        if not dolphin_api_host.endswith("/v1.0"):
                            dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
                        
                        dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
                        if dolphin.authenticate():
                            delete_result = dolphin.delete_profile(dolphin_profile_id)
                            if delete_result:
                                logger.info(f"[DELETE ACCOUNT] Successfully deleted Dolphin profile {dolphin_profile_id}")
                            else:
                                logger.warning(f"[DELETE ACCOUNT] Failed to delete Dolphin profile {dolphin_profile_id}, but continuing with account deletion")
                        else:
                            logger.error("[DELETE ACCOUNT] Failed to authenticate with Dolphin API")
                    else:
                        logger.warning("[DELETE ACCOUNT] No Dolphin API token found, skipping profile deletion")
                except Exception as e:
                    logger.error(f"[DELETE ACCOUNT] Error deleting Dolphin profile {dolphin_profile_id}: {str(e)}")
                    # Continue with account deletion even if Dolphin profile deletion fails
            
            # Release proxy if assigned
            if account.proxy:
                proxy = account.proxy
                proxy.assigned_account = None
                proxy.save(update_fields=['assigned_account'])
                logger.info(f"[DELETE ACCOUNT] Released proxy {proxy} from account {account_name}")
            
            # Delete the account
            account.delete()
            logger.info(f"[DELETE ACCOUNT] Successfully deleted account {account_name}")
            
            if dolphin_profile_id:
                messages.success(request, f'Account {account_name} and Dolphin profile {dolphin_profile_id} deleted successfully.')
            else:
                messages.success(request, f'Account {account_name} deleted successfully.')
        except Exception as e:
            logger.error(f"Error deleting account {account_id}: {str(e)}")
            messages.error(request, f'Error deleting account: {str(e)}')
        
        return redirect('account_list')
    
    # Confirm deletion
    context = {
        'account': account,
        'active_tab': 'accounts'
    }
    return render(request, 'uploader/delete_account.html', context)

@login_required
def create_account(request):
    """Create a new Instagram account"""
    if request.method == 'POST':
        form = InstagramAccountForm(request.POST)
        if form.is_valid():
            # Save the account first to get an ID
            account = form.save()
            
            logger.info(f"[CREATE ACCOUNT] Account {account.username} created successfully. Attempting to assign proxy and create Dolphin profile.")
            
            assigned_proxy = None
            dolphin_available = False

            # Step 1: Assign an available proxy
            try:
                available_proxies = Proxy.objects.filter(is_active=True, assigned_account__isnull=True)
                if available_proxies.exists():
                    # Assign a random available proxy
                    assigned_proxy = available_proxies.order_by('?').first()
                    account.proxy = assigned_proxy
                    account.current_proxy = assigned_proxy
                    account.save(update_fields=['proxy', 'current_proxy'])
                    assigned_proxy.assigned_account = account
                    assigned_proxy.save(update_fields=['assigned_account'])
                    logger.info(f"[CREATE ACCOUNT] Assigned proxy {assigned_proxy} to account {account.username}")
                else:
                    logger.warning(f"[CREATE ACCOUNT] No available proxies found for account {account.username}. Skipping proxy assignment.")
                    messages.warning(request, f'Account {account.username} created, but no available proxy could be assigned. Please assign manually.')

            except Exception as e:
                logger.error(f"[CREATE ACCOUNT] Error assigning proxy to account {account.username}: {str(e)}")
                messages.error(request, f'Account {account.username} created, but an error occurred while assigning a proxy: {str(e)}')
            
            # Step 2: Create Dolphin profile if proxy was assigned
            if assigned_proxy:
                try:
                    logger.info(f"[CREATE ACCOUNT] Initializing Dolphin Anty API client for account {account.username}")
                    api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
                    if not api_key:
                        logger.error("[CREATE ACCOUNT] Dolphin API token not found in environment variables")
                        messages.warning(request, f'Account {account.username} created and proxy assigned, but Dolphin API token not configured.')
                        return redirect('account_detail', account_id=account.id)
                    
                    # Get Dolphin API host from environment (critical for Docker Windows deployment)
                    dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
                    if not dolphin_api_host.endswith("/v1.0"):
                        dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
                    
                    dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
                    dolphin_available = dolphin.authenticate()

                    if dolphin_available:
                        logger.info(f"[CREATE ACCOUNT] Authenticated with Dolphin Anty API.")
                        
                        # Create profile name with account username and random suffix
                        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                        profile_name = f"instagram_{account.username}_{random_suffix}"
                        logger.info(f"[CREATE ACCOUNT] Creating Dolphin profile '{profile_name}' for account {account.username}")

                        proxy_data = assigned_proxy.to_dict()
                        logger.info(f"[CREATE ACCOUNT] Using proxy for profile: {proxy_data.get('host')}:{proxy_data.get('port')}")

                        # Using updated create_profile method with proper fingerprint generation
                        # Locale: try to read from POST (if present on the form), else default
                        selected_locale = request.POST.get('profile_locale', 'ru_RU')
                        if selected_locale not in {'en_US','en_IN','ru_RU'}:
                            selected_locale = 'ru_RU'
                        response = dolphin.create_profile(
                            name=profile_name,
                            proxy=proxy_data,
                            tags=["instagram", "auto-created", "single-account-created"],
                            locale=selected_locale
                        )

                        # Extract profile ID from response
                        profile_id = None
                        if response and isinstance(response, dict):
                            profile_id = response.get("browserProfileId")
                            if not profile_id and isinstance(response.get("data"), dict):
                                profile_id = response["data"].get("id")
                                
                        if profile_id:
                            account.dolphin_profile_id = profile_id
                            account.save(update_fields=['dolphin_profile_id'])
                            logger.info(f"[CREATE ACCOUNT] Created Dolphin profile {profile_id} for account {account.username}")
                            messages.success(request, f'Account {account.username} created and Dolphin profile {profile_id} created successfully!')
                        else:
                            error_message = "Unknown error" if not isinstance(response, dict) else response.get("error", "Unknown error during Dolphin profile creation")
                            logger.error(f"[CREATE ACCOUNT] Failed to create Dolphin profile for account {account.username}: {error_message}")
                            messages.warning(request, f'Account {account.username} created and proxy assigned, but failed to create Dolphin profile: {error_message}')
                    else:
                         logger.error(f"[CREATE ACCOUNT] Failed to authenticate with Dolphin Anty API for account {account.username}")
                         messages.warning(request, f'Account {account.username} created and proxy assigned, but could not connect to Dolphin Anty API to create profile. Check API token.')

                except Exception as e:
                    logger.error(f"[CREATE ACCOUNT] Error creating Dolphin profile for account {account.username}: {str(e)}")
                    messages.warning(request, f'Account {account.username} created and proxy assigned, but an error occurred while creating Dolphin profile: {str(e)}')

            messages.success(request, f'Account {account.username} created successfully!')
            return redirect('account_detail', account_id=account.id)
    else:
        form = InstagramAccountForm()
    
    context = {
        'form': form,
        'active_tab': 'accounts'
    }
    return render(request, 'uploader/create_account.html', context)

@login_required
def proxy_list(request):
    """List all proxies"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    proxies = Proxy.objects.all()
    
    if status_filter:
        is_active = status_filter == 'active'
        proxies = proxies.filter(is_active=is_active)
    
    if search_query:
        proxies = proxies.filter(
            Q(host__icontains=search_query) |
            Q(username__icontains=search_query)
        )
    
    # Get total count before pagination
    total_proxies = proxies.count()
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(proxies.order_by('-last_verified', 'host', 'port'), 25)  # 25 proxies per page
    page_number = request.GET.get('page', 1)
    proxies = paginator.get_page(page_number)
    
    context = {
        'proxies': proxies,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_proxies': total_proxies,
        'active_tab': 'proxies'
    }
    return render(request, 'uploader/proxy_list.html', context)

@login_required
def create_proxy(request):
    """Create a new proxy"""
    if request.method == 'POST':
        form = ProxyForm(request.POST)
        if form.is_valid():
            # Create but don't save the proxy instance yet
            proxy = form.save(commit=False)
            
            # Validate the proxy before saving
            is_valid, message, geo_info = validate_proxy(
                host=proxy.host,
                port=proxy.port,
                username=proxy.username,
                password=proxy.password,
                timeout=15,
                proxy_type=proxy.proxy_type
            )
            
            if not is_valid:
                messages.error(request, f'Proxy validation failed: {message}')
                context = {
                    'form': form,
                    'active_tab': 'proxies',
                    'validation_error': message
                }
                return render(request, 'uploader/create_proxy.html', context)
            
            # Set status based on validation result
            proxy.status = 'active' if is_valid else 'inactive'
            proxy.is_active = is_valid
            
            # Update country and city information if available
            if geo_info:
                if geo_info.get('country'):
                    proxy.country = geo_info.get('country')
                if geo_info.get('city'):
                    proxy.city = geo_info.get('city')
            
            # Set verification timestamps
            proxy.last_verified = timezone.now()
            proxy.last_checked = timezone.now()
            
            # Save the valid proxy
            proxy.save()
            messages.success(request, f'Proxy {proxy.host}:{proxy.port} created and validated successfully!')
            return redirect('proxy_list')
    else:
        form = ProxyForm()
    
    context = {
        'form': form,
        'active_tab': 'proxies'
    }
    return render(request, 'uploader/create_proxy.html', context)

@login_required
def import_accounts(request):
    """
    Import Instagram accounts from a text file, create Dolphin profiles,
    assign one proxy per account, and link everything together.
    """
    if request.method == 'POST' and request.FILES.get('accounts_file'):
        accounts_file = request.FILES['accounts_file']
        
        # Locale selection from form
        selected_locale = request.POST.get('profile_locale', 'ru_RU')
        allowed_locales = {'en_US', 'en_IN', 'ru_RU'}
        if selected_locale not in allowed_locales:
            selected_locale = 'ru_RU'
        
        # Counters for status messages
        created_count = 0
        updated_count = 0
        error_count = 0
        dolphin_created_count = 0
        dolphin_error_count = 0
        
        # Initialize Dolphin Anty API client
        try:
            logger.info("[STEP 1/5] Initializing Dolphin Anty API client")
            api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
            if not api_key:
                logger.error("[ERROR] Dolphin API token not found in environment variables")
                messages.error(request, "Dolphin API token not configured. Please set DOLPHIN_API_TOKEN environment variable.")
                return redirect('import_accounts')
            
            # Get Dolphin API host from environment (critical for Docker Windows deployment)
            dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
            if not dolphin_api_host.endswith("/v1.0"):
                dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
            
            dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
            dolphin_available = dolphin.authenticate()
            if dolphin_available:
                logger.info("[SUCCESS] Successfully authenticated with Dolphin Anty API")
            else:
                logger.error("[FAIL] Failed to authenticate with Dolphin Anty API")
                messages.error(request, "Failed to authenticate with Dolphin Anty API. Check your API token.")
        except Exception as e:
            logger.error(f"[ERROR] Error initializing Dolphin Anty API: {str(e)}")
            dolphin_available = False
            messages.error(request, f"Dolphin Anty API error: {str(e)}")
        
        # Read file content
        logger.info("[STEP 2/5] Reading accounts file content")
        content = accounts_file.read().decode('utf-8')
        lines = content.splitlines()
        total_lines = len(lines)
        logger.info(f"[INFO] Found {total_lines} lines in the accounts file")
        
        # Determine how many proxies are actually needed: only for new accounts or existing accounts without proxy
        # Parse usernames from valid lines (username:password...)
        parsed_usernames = []
        for raw in lines:
            s = (raw or '').strip()
            if not s:
                continue
            parts = s.split(':')
            if len(parts) >= 2 and parts[0]:
                parsed_usernames.append(parts[0])
        unique_usernames = list({u for u in parsed_usernames})

        existing_map = {
            acc.username: acc
            for acc in InstagramAccount.objects.filter(username__in=unique_usernames)
        }
        new_usernames = [u for u in unique_usernames if u not in existing_map]
        existing_without_proxy = [
            u for u in unique_usernames
            if u in existing_map and not (getattr(existing_map[u], 'proxy', None) or getattr(existing_map[u], 'current_proxy', None))
        ]
        proxies_needed = len(new_usernames) + len(existing_without_proxy)

        available_proxies = Proxy.objects.filter(is_active=True, assigned_account__isnull=True)
        available_proxy_count = available_proxies.count()
        logger.info(f"[INFO] Proxy requirement: needed={proxies_needed} (new={len(new_usernames)}, existing_without_proxy={len(existing_without_proxy)}), available={available_proxy_count}")
        
        if available_proxy_count < proxies_needed:
            error_message = (
                f"Not enough available proxies. Need {proxies_needed} "
                f"(new: {len(new_usernames)}, missing: {len(existing_without_proxy)}) "
                f"but only have {available_proxy_count}. Please add more proxies before importing accounts."
            )
            logger.error(f"[ERROR] {error_message}")
            messages.error(request, error_message)
            return redirect('import_accounts')
        
        # Process accounts
        logger.info("[STEP 3/5] Processing accounts")
        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                logger.debug(f"[SKIP] Line {line_num}: Empty line, skipping")
                continue  # Skip empty lines
                
            try:
                # Parse line
                logger.info(f"[ACCOUNT {line_num}/{total_lines}] Processing line {line_num}")
                parts = line.strip().split(':')
                
                if len(parts) < 2:
                    logger.warning(f"[ERROR] Line {line_num}: Invalid format. Expected at least username:password")
                    messages.warning(request, f'Line {line_num}: Invalid format. Expected at least username:password')
                    error_count += 1
                    continue
                    
                # Common fields
                username = parts[0]
                password = parts[1]
                logger.info(f"[INFO] Processing account: {username}")
                
                # Default values
                tfa_secret = None
                email_username = None
                email_password = None
                
                # Determine account type based on number of parts
                if len(parts) == 2:
                    # Basic format: username:password (no 2FA, no email verification)
                    logger.info(f"[INFO] Account {username} identified as basic account (no 2FA, no email)")
                
                elif len(parts) == 3:
                    # This could be either a 2FA account or an email verification account
                    # Check if the third part looks like a 2FA secret (usually uppercase letters and numbers)
                    # Remove spaces first to properly detect 2FA keys that may contain spaces
                    import re
                    potential_2fa = re.sub(r'\s+', '', parts[2])
                    if potential_2fa.isupper() and any(c.isdigit() for c in potential_2fa):
                        tfa_secret = potential_2fa  # Already has spaces removed
                        logger.info(f"[INFO] Account {username} identified as 2FA account")
                    else:
                        # Assume it's an email without password
                        email_username = parts[2]
                        logger.info(f"[INFO] Account {username} identified with email (no password)")
                
                elif len(parts) == 4:
                    # This is an email verification account (username:password:email:email_password)
                    email_username = parts[2]
                    email_password = parts[3]
                    logger.info(f"[INFO] Account {username} identified as email verification account")
                
                elif len(parts) == 5:
                    # This is a TFA account (username:password:email:email_password:tfa_secret)
                    email_username = parts[2]
                    email_password = parts[3]
                    import re
                    tfa_secret = re.sub(r'\s+', '', parts[4])  # Remove all whitespace from 2FA key
                    logger.info(f"[INFO] Account {username} identified as TFA account with email")
                
                elif len(parts) > 5:
                    # Extended format with additional fields
                    email_username = parts[2]
                    email_password = parts[3]
                    import re
                    tfa_secret = re.sub(r'\s+', '', parts[4])  # Remove all whitespace from 2FA key
                    logger.info(f"[INFO] Account {username} identified as TFA account with extended format")
                
                
                # Decide proxy assignment strategy
                logger.info(f"[STEP 4/5] Deciding proxy for account: {username}")
                assigned_proxy = None
                try:
                    existing_acc = existing_map.get(username)
                    if existing_acc and (existing_acc.current_proxy or existing_acc.proxy):
                        # Reuse existing proxy assignment, do not grab a new proxy
                        assigned_proxy = existing_acc.current_proxy or existing_acc.proxy
                        logger.info(f"[INFO] Reusing existing proxy for {username}: {assigned_proxy}")
                    else:
                        # Get an unused active proxy
                        available_proxies = Proxy.objects.filter(is_active=True, assigned_account__isnull=True)
                        if not available_proxies.exists():
                            error_message = f"No available proxies left for account {username}. Please add more proxies."
                            logger.error(f"[ERROR] {error_message}")
                            messages.error(request, error_message)
                            return redirect('import_accounts')
                        assigned_proxy = available_proxies.order_by('?').first()
                        logger.info(f"[SUCCESS] Assigned new proxy {assigned_proxy} to account {username}")
                except Exception as e:
                    error_message = f"Error assigning proxy to account {username}: {str(e)}"
                    logger.error(f"[ERROR] {error_message}")
                    messages.error(request, error_message)
                    error_count += 1
                    continue
                
                # Check if account already exists
                logger.info(f"[STEP 5/5] Creating or updating account: {username}")
                # Build defaults without overwriting existing proxy unless we actually selected one
                defaults = {
                    'password': password,
                    'tfa_secret': tfa_secret,
                    'email_username': email_username,
                    'email_password': email_password,
                    'status': 'ACTIVE',
                }
                if assigned_proxy and (not existing_map.get(username) or not (existing_map[username].proxy or existing_map[username].current_proxy)):
                    defaults['proxy'] = assigned_proxy

                account, created = InstagramAccount.objects.update_or_create(
                    username=username,
                    defaults=defaults
                )
                
                if created:
                    logger.info(f"[SUCCESS] Created new account: {username}")
                    created_count += 1
                else:
                    logger.info(f"[SUCCESS] Updated existing account: {username}")
                    updated_count += 1
                    
                # Update proxy assignment only if we assigned a new proxy from pool
                if assigned_proxy and (not existing_map.get(username) or not (existing_map[username].proxy or existing_map[username].current_proxy)):
                    assigned_proxy.assigned_account = account
                    assigned_proxy.save()
                    logger.info(f"[INFO] Updated proxy assignment for account {username}")
                
                # Create Dolphin profile if API is available
                if dolphin_available and (created or not account.dolphin_profile_id):
                    try:
                        # Create profile name with account username and random suffix
                        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                        profile_name = f"instagram_{username}_{random_suffix}"
                        logger.info(f"[DOLPHIN] Creating Dolphin profile for account {username}")
                        
                        # Prepare proxy data if available
                        proxy_data = None
                        if assigned_proxy:
                            proxy_data = assigned_proxy.to_dict()
                            logger.info(f"[DOLPHIN] Using proxy for profile: {assigned_proxy.host}:{assigned_proxy.port}")
                        else:
                            logger.warning(f"[DOLPHIN] No proxy available for profile creation")
                            # This should never happen as we check for proxy availability earlier
                            continue
                        
                        # Add a significant delay between creating each profile to prevent rate limiting
                        # This is especially important since we're generating unique fingerprints
                        if dolphin_created_count > 0:
                            delay_time = random.uniform(4.0, 7.0)  # Random delay between 4-7 seconds
                            logger.info(f"[DOLPHIN] Adding a {delay_time:.1f}-second delay before creating the next profile")
                            time.sleep(delay_time)
                        
                        # Create Dolphin profile with proper fingerprint generation
                        response = dolphin.create_profile(
                            name=profile_name,
                            proxy=proxy_data,
                            tags=["instagram", "auto-created"],
                            locale=selected_locale
                        )
                        
                        # Extract profile ID from response
                        profile_id = None
                        if response and isinstance(response, dict):
                            profile_id = response.get("browserProfileId")
                            if not profile_id and isinstance(response.get("data"), dict):
                                profile_id = response["data"].get("id")
                                
                        if profile_id:
                            account.dolphin_profile_id = profile_id
                            account.save(update_fields=['dolphin_profile_id'])
                            dolphin_created_count += 1
                            logger.info(f"[SUCCESS] Created Dolphin profile {profile_id} for account {username}")
                        else:
                            error_message = response.get("error", "Unknown error")
                            detailed_error = ""
                            
                            # Extract detailed validation errors
                            if isinstance(error_message, dict):
                                if "fields" in error_message:
                                    validation_errors = []
                                    for field_error in error_message.get("fields", []):
                                        field = field_error.get("field", "unknown")
                                        error = field_error.get("error", "unknown error")
                                        values = field_error.get("values", [])
                                        validation_errors.append(f"{field}: {error} (expected: {', '.join(map(str, values))})")
                                    
                                    detailed_error = " | ".join(validation_errors)
                                else:
                                    detailed_error = str(error_message)
                            else:
                                detailed_error = str(error_message)
                            
                            full_error = f"Failed to create Dolphin profile for account {username}: {detailed_error}"
                            logger.error(f"[ERROR] {full_error}")
                            messages.error(request, full_error)
                            dolphin_error_count += 1
                    except Exception as e:
                        dolphin_error_count += 1
                        error_message = f"Error creating Dolphin profile for account {username}: {str(e)}"
                        logger.error(f"[ERROR] {error_message}")
                        messages.error(request, error_message)
                
            except Exception as e:
                error_message = f"Error importing account at line {line_num}: {str(e)}"
                logger.error(f"[ERROR] {error_message}")
                messages.error(request, error_message)
                error_count += 1
        
        # Show summary message
        logger.info(f"[SUMMARY] Import completed - Created: {created_count}, Updated: {updated_count}, Errors: {error_count}")
        if dolphin_available:
            logger.info(f"[SUMMARY] Dolphin profiles - Created: {dolphin_created_count}, Errors: {dolphin_error_count}")
            
        if created_count > 0 or updated_count > 0:
            success_msg = f'Import completed! Created: {created_count}, Updated: {updated_count}, Errors: {error_count}'
            if dolphin_available:
                success_msg += f', Dolphin profiles created: {dolphin_created_count}, Dolphin errors: {dolphin_error_count}'
            messages.success(request, success_msg)
        else:
            messages.warning(request, f'No accounts were imported. Errors: {error_count}')
        
        return redirect('account_list')
        
    context = {
        'active_tab': 'import_accounts'
    }
    return render(request, 'uploader/import_accounts.html', context)

@login_required
def warm_account(request, account_id):
    """Warm up an Instagram account to get fresh cookies"""
    account = get_object_or_404(InstagramAccount, id=account_id)
    
    # In a real implementation, this would start a Playwright process to log in
    # and browse Instagram to warm up the account
    
    # For now, just mark it as warmed
    account.last_warmed = timezone.now()
    account.save(update_fields=['last_warmed'])
    
    messages.success(request, f'Account {account.username} has been warmed up.')
    return redirect('account_detail', account_id=account.id)

@login_required
def edit_account(request, account_id):
    """Edit an existing Instagram account"""
    account = get_object_or_404(InstagramAccount, id=account_id)
    
    if request.method == 'POST':
        form = InstagramAccountForm(request.POST, instance=account)
        if form.is_valid():
            # Preserve Dolphin profile ID explicitly to avoid clearing
            preserved_profile_id = account.dolphin_profile_id
            account = form.save()
            if preserved_profile_id and account.dolphin_profile_id != preserved_profile_id:
                account.dolphin_profile_id = preserved_profile_id
                account.save(update_fields=['dolphin_profile_id'])
            
            # Synchronize proxy and current_proxy fields
            if account.proxy != account.current_proxy:
                account.current_proxy = account.proxy
                account.save(update_fields=['current_proxy'])
                logger.info(f"[EDIT ACCOUNT] Synchronized proxy fields for account {account.username}")
            
            messages.success(request, f'Account {account.username} updated successfully!')
            return redirect('account_detail', account_id=account.id)
    else:
        form = InstagramAccountForm(instance=account)
    
    context = {
        'form': form,
        'account': account,
        'active_tab': 'accounts'
    }
    return render(request, 'uploader/edit_account.html', context)

@login_required
def change_account_proxy(request, account_id):
    """Change the proxy for an Instagram account and update Dolphin profile if exists"""
    account = get_object_or_404(InstagramAccount, id=account_id)
    
    if request.method == 'POST':
        proxy_id = request.POST.get('proxy_id')
        
        try:
            if proxy_id:
                # Assign the selected proxy
                new_proxy = get_object_or_404(Proxy, id=proxy_id)
                
                # If this proxy is assigned to another account, unassign it
                if new_proxy.assigned_account and new_proxy.assigned_account != account:
                    old_account = new_proxy.assigned_account
                    old_account.proxy = None
                    old_account.current_proxy = None
                    old_account.save(update_fields=['proxy', 'current_proxy'])
                
                # Update the current account's proxy - update both proxy and current_proxy fields
                old_proxy = account.proxy
                account.proxy = new_proxy
                account.current_proxy = new_proxy  # Ensure both fields are updated
                account.save(update_fields=['proxy', 'current_proxy'])
                
                # Update the proxy's assigned account
                new_proxy.assigned_account = account
                new_proxy.save(update_fields=['assigned_account'])
                
                # If the old proxy exists, clear its assignment
                if old_proxy:
                    old_proxy.assigned_account = None
                    old_proxy.save(update_fields=['assigned_account'])
                
                # Update Dolphin profile proxy if profile exists
                if account.dolphin_profile_id:
                    try:
                        logger.info(f"[CHANGE PROXY] Updating Dolphin profile {account.dolphin_profile_id} proxy for account {account.username}")
                        
                        # Initialize Dolphin API
                        api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
                        if not api_key:
                            logger.warning("[CHANGE PROXY] Dolphin API token not found in environment variables")
                            messages.warning(request, f'Proxy changed for account {account.username}, but could not update Dolphin profile: API token not configured.')
                        else:
                            # Get Dolphin API host from environment (critical for Docker Windows deployment)
                            dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
                            if not dolphin_api_host.endswith("/v1.0"):
                                dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
                            
                            dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
                            
                            # Authenticate with Dolphin
                            if dolphin.authenticate():
                                # Prepare proxy data for Dolphin
                                proxy_data = new_proxy.to_dict()
                                
                                # Update proxy in Dolphin profile
                                result = dolphin.update_profile_proxy(account.dolphin_profile_id, proxy_data)
                                
                                if result.get("success"):
                                    logger.info(f"[CHANGE PROXY] Successfully updated Dolphin profile {account.dolphin_profile_id} proxy")
                                    region_msg = ""
                                    if old_proxy and old_proxy.country and new_proxy.country and old_proxy.country != new_proxy.country:
                                        region_msg = f" (Region changed from {old_proxy.country} to {new_proxy.country})"
                                    messages.success(request, f'Proxy changed for account {account.username} and Dolphin profile {account.dolphin_profile_id} updated successfully!{region_msg}')
                                else:
                                    error_msg = result.get("error", "Unknown error")
                                    logger.error(f"[CHANGE PROXY] Failed to update Dolphin profile proxy: {error_msg}")
                                    messages.warning(request, f'Proxy changed for account {account.username}, but failed to update Dolphin profile: {error_msg}')
                            else:
                                logger.error("[CHANGE PROXY] Failed to authenticate with Dolphin Anty API")
                                messages.warning(request, f'Proxy changed for account {account.username}, but could not authenticate with Dolphin Anty API.')
                    
                    except Exception as e:
                        logger.error(f"[CHANGE PROXY] Error updating Dolphin profile proxy: {str(e)}")
                        messages.warning(request, f'Proxy changed for account {account.username}, but an error occurred while updating Dolphin profile: {str(e)}')
                else:
                    region_msg = ""
                    if old_proxy and old_proxy.country and new_proxy.country and old_proxy.country != new_proxy.country:
                        region_msg = f" (Region changed from {old_proxy.country} to {new_proxy.country})"
                    messages.success(request, f'Proxy changed for account {account.username}{region_msg}')
            else:
                # Remove proxy assignment - clear both proxy and current_proxy fields
                old_proxy = account.proxy
                account.proxy = None
                account.current_proxy = None
                account.save(update_fields=['proxy', 'current_proxy'])
                
                if old_proxy:
                    old_proxy.assigned_account = None
                    old_proxy.save(update_fields=['assigned_account'])
                
                # Note: We don't remove proxy from Dolphin profile when removing proxy assignment
                # as this would break the profile. User should manually handle this case.
                if account.dolphin_profile_id:
                    messages.warning(request, f'Proxy removed from account {account.username}. Note: Dolphin profile {account.dolphin_profile_id} still has the old proxy configured.')
                else:
                    messages.success(request, f'Proxy removed from account {account.username}')
                
        except Exception as e:
            logger.error(f"[CHANGE PROXY] Error changing proxy for account {account.username}: {str(e)}")
            messages.error(request, f'Error changing proxy: {str(e)}')
        
        return redirect('account_detail', account_id=account.id)
    
    # Get available proxies - prefer same region if account has a proxy with region info
    if account.proxy and account.proxy.country:
        # First, get proxies from the same region
        same_region_proxies = Proxy.objects.filter(
            Q(assigned_account__isnull=True) | Q(assigned_account=account),
            is_active=True,
            country=account.proxy.country
        ).order_by('host', 'port')
        
        # Then, get all other active proxies
        other_proxies = Proxy.objects.filter(
            Q(assigned_account__isnull=True) | Q(assigned_account=account),
            is_active=True
        ).exclude(country=account.proxy.country).order_by('host', 'port')
        
        # Combine: same region first, then others
        available_proxies = list(same_region_proxies) + list(other_proxies)
    else:
        # No region preference, get all available proxies
        available_proxies = Proxy.objects.filter(
            Q(assigned_account__isnull=True) | Q(assigned_account=account),
            is_active=True
        ).order_by('host', 'port')
    
    context = {
        'account': account,
        'available_proxies': available_proxies,
        'active_tab': 'accounts'
    }
    
    return render(request, 'uploader/change_account_proxy.html', context)

@login_required
def edit_proxy(request, proxy_id):
    """Edit an existing proxy"""
    proxy = get_object_or_404(Proxy, id=proxy_id)
    
    if request.method == 'POST':
        form = ProxyForm(request.POST, instance=proxy)
        if form.is_valid():
            # Create but don't save the proxy instance yet
            updated_proxy = form.save(commit=False)
            
            # Validate only if connectivity details have changed
            if (proxy.host != updated_proxy.host or 
                proxy.port != updated_proxy.port or 
                proxy.username != updated_proxy.username or 
                proxy.password != updated_proxy.password or
                proxy.proxy_type != updated_proxy.proxy_type):
                
                # Validate the proxy before saving
                is_valid, message, geo_info = validate_proxy(
                    host=updated_proxy.host,
                    port=updated_proxy.port,
                    username=updated_proxy.username,
                    password=updated_proxy.password,
                    timeout=15,
                    proxy_type=updated_proxy.proxy_type
                )
                
                if not is_valid:
                    messages.error(request, f'Proxy validation failed: {message}')
                    context = {
                        'form': form,
                        'proxy': proxy,
                        'active_tab': 'proxies',
                        'validation_error': message
                    }
                    return render(request, 'uploader/edit_proxy.html', context)
                
                # Set status based on validation result
                updated_proxy.status = 'active' if is_valid else 'inactive'
                updated_proxy.is_active = is_valid
                
                # Set verification timestamps
                updated_proxy.last_verified = timezone.now()
                updated_proxy.last_checked = timezone.now()
                
                # Update country and city information if available
                if geo_info:
                    if geo_info.get('country'):
                        updated_proxy.country = geo_info.get('country')
                    if geo_info.get('city'):
                        updated_proxy.city = geo_info.get('city')
            
            # Save the valid proxy
            updated_proxy.save()
            messages.success(request, f'Proxy {updated_proxy.host}:{updated_proxy.port} updated successfully!')
            return redirect('proxy_list')
    else:
        form = ProxyForm(instance=proxy)
    
    context = {
        'form': form,
        'proxy': proxy,
        'active_tab': 'proxies'
    }
    return render(request, 'uploader/edit_proxy.html', context)

@login_required
def test_proxy(request, proxy_id):
    """Test if a proxy server is working"""
    proxy = get_object_or_404(Proxy, id=proxy_id)
    
    # Test proxy functionality using the validation utility
    is_valid, message, geo_info = validate_proxy(
        host=proxy.host,
        port=proxy.port,
        username=proxy.username,
        password=proxy.password,
        timeout=15,  # Increase timeout for more reliable testing
        proxy_type=proxy.proxy_type
    )
    
    # Update proxy verification timestamp and location data
    proxy.last_verified = timezone.now()
    proxy.last_checked = timezone.now()
    
    # Update status based on validation result
    if is_valid:
        proxy.status = 'active'
        proxy.is_active = True
    else:
        proxy.status = 'inactive'
        proxy.is_active = False
    
    # Update country and city information if available
    if geo_info and is_valid:
        if geo_info.get('country'):
            proxy.country = geo_info.get('country')
        if geo_info.get('city'):
            proxy.city = geo_info.get('city')
    
    proxy.save()
    
    if is_valid:
        messages.success(request, f'Proxy {proxy.host}:{proxy.port} is working! {message}')
    else:
        messages.error(request, f'Proxy {proxy.host}:{proxy.port} failed validation: {message}')
        
    return redirect('proxy_list')

@login_required
def import_proxies(request):
    """Import proxies from a text file"""
    if request.method == 'POST' and request.FILES.get('proxies_file'):
        proxies_file = request.FILES['proxies_file']
        
        # Counters for status messages
        created_count = 0
        updated_count = 0
        error_count = 0
        invalid_count = 0
        
        # Read file content
        content = proxies_file.read().decode('utf-8')
        
        for line_num, line in enumerate(content.splitlines(), 1):
            if not line.strip():
                continue  # Skip empty lines
                
            try:
                # Parse line in format host:port:username:password
                parts = line.strip().split(':')
                
                if len(parts) < 2:
                    messages.warning(request, f'Line {line_num}: Invalid format. Expected at least host:port')
                    error_count += 1
                    continue
                    
                host = parts[0]
                port = parts[1]
                username = parts[2] if len(parts) > 2 else None
                password = parts[3] if len(parts) > 3 else None
                
                # Validate the proxy before importing
                is_valid, validation_message, geo_info = validate_proxy(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=10,
                    proxy_type='HTTP'  # Default to HTTP for imported proxies
                )
                
                if not is_valid:
                    logger.warning(f"Line {line_num}: Proxy validation failed - {validation_message}")
                    messages.warning(request, f'Line {line_num}: Proxy validation failed - {validation_message}')
                    invalid_count += 1
                    continue
                
                # Check if an identical proxy already exists (same host, port, username, password)
                identical_proxy = Proxy.objects.filter(
                    host=host,
                    port=port,
                    username=username,
                    password=password
                ).first()
                
                if identical_proxy:
                    # Update existing proxy
                    identical_proxy.status = 'active' if is_valid else 'inactive'
                    identical_proxy.is_active = is_valid
                    identical_proxy.last_verified = timezone.now()
                    identical_proxy.last_checked = timezone.now()
                    
                    # Update country and city information if available
                    if geo_info:
                        if geo_info.get('country'):
                            identical_proxy.country = geo_info.get('country')
                        if geo_info.get('city'):
                            identical_proxy.city = geo_info.get('city')
                            
                    identical_proxy.save()
                    updated_count += 1
                else:
                    # Create new proxy
                    new_proxy = Proxy(
                        host=host,
                        port=port,
                        username=username,
                        password=password,
                        status='active' if is_valid else 'inactive',
                        is_active=is_valid,
                        last_verified=timezone.now(),
                        last_checked=timezone.now()
                    )
                    
                    # Add country and city information if available
                    if geo_info:
                        if geo_info.get('country'):
                            new_proxy.country = geo_info.get('country')
                        if geo_info.get('city'):
                            new_proxy.city = geo_info.get('city')
                            
                    new_proxy.save()
                    created_count += 1
                    
            except Exception as e:
                logger.error(f"Error importing proxy at line {line_num}: {str(e)}")
                messages.error(request, f'Line {line_num}: Error importing proxy - {str(e)}')
                error_count += 1
        
        # Show summary message
        if created_count > 0 or updated_count > 0:
            messages.success(
                request, 
                f'Import completed! Created: {created_count}, Updated: {updated_count}, Invalid: {invalid_count}, Errors: {error_count}'
            )
        else:
            messages.warning(request, f'No valid proxies were imported. Invalid: {invalid_count}, Errors: {error_count}')
            
        return redirect('proxy_list')
        
    context = {
        'active_tab': 'import_proxies'
    }
    return render(request, 'uploader/import_proxies.html', context)

@login_required
def validate_all_proxies(request):
    """Validate all active proxies in the system"""
    proxies = Proxy.objects.filter(is_active=True)
    
    if not proxies.exists():
        messages.warning(request, 'No active proxies found in the system.')
        return redirect('proxy_list')
    
    # Start the validation in a background thread to avoid timeout
    thread = threading.Thread(
        target=_validate_proxies_background,
        args=(proxies, request.user.id)
    )
    thread.daemon = True
    thread.start()
    
    messages.info(
        request, 
        f'Validation of {proxies.count()} proxies has been started in the background. Please check back in a moment.'
    )
    return redirect('proxy_list')

def _validate_proxies_background(proxies, user_id):
    """Background task to validate proxies"""
    from django.contrib.auth.models import User
    from django.contrib.messages import constants as message_constants
    from django.contrib.messages.storage.fallback import FallbackStorage
    from django.contrib.sessions.backends.db import SessionStore
    from django.http import HttpRequest
    
    # Create a fake request to use for messaging
    request = HttpRequest()
    request.user = User.objects.get(id=user_id)
    request.session = SessionStore()
    request.session.create()
    request._messages = FallbackStorage(request)
    
    valid_count = 0
    invalid_count = 0
    
    # Use multiple threads to validate proxies in parallel
    thread_count = min(10, proxies.count())  # Max 10 threads
    
    if thread_count <= 0:
        return
    
    from concurrent.futures import ThreadPoolExecutor
    
    def validate_proxy_worker(proxy):
        is_valid, _, geo_info = validate_proxy(
            host=proxy.host,
            port=proxy.port,
            username=proxy.username,
            password=proxy.password,
            timeout=10,
            proxy_type=proxy.proxy_type
        )
        
        # Update proxy verification timestamp and location data
        proxy.last_verified = timezone.now()
        proxy.last_checked = timezone.now()
        
        # Update status based on validation result
        proxy.status = 'active' if is_valid else 'inactive'
        proxy.is_active = is_valid
        
        # Update country and city information if available
        if geo_info and is_valid:
            if geo_info.get('country'):
                proxy.country = geo_info.get('country')
            if geo_info.get('city'):
                proxy.city = geo_info.get('city')
        
        proxy.save()
        
        return is_valid
    
    # Execute validation in parallel
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        results = list(executor.map(validate_proxy_worker, proxies))
        
    valid_count = sum(1 for r in results if r)
    invalid_count = sum(1 for r in results if not r)
    
    # Add message to the fake request
    # This will be seen on the next page load
    request._messages.add(
        message_constants.SUCCESS,
        f'Proxy validation complete. Valid: {valid_count}, Invalid: {invalid_count}'
    )

@login_required
def delete_proxy(request, proxy_id):
    """Delete a proxy server"""
    proxy = get_object_or_404(Proxy, id=proxy_id)
    
    # Store proxy info for message
    proxy_str = str(proxy)
    
    try:
        # Delete the proxy
        proxy.delete()
        messages.success(request, f'Proxy {proxy_str} deleted successfully.')
    except Exception as e:
        logger.error(f"Error deleting proxy {proxy_id}: {str(e)}")
        messages.error(request, f'Error deleting proxy: {str(e)}')
    
    return redirect('proxy_list')

@login_required
def bulk_upload_list(request):
    """List all bulk upload tasks"""
    from django.db.models import Sum, Value
    from django.db.models.functions import Coalesce
    tasks = (
        BulkUploadTask.objects
        .order_by('-created_at')
        .annotate(
            uploaded_success_total=Coalesce(Sum('accounts__uploaded_success_count'), Value(0)),
            uploaded_failed_total=Coalesce(Sum('accounts__uploaded_failed_count'), Value(0)),
            completed_accounts_count=Coalesce(Sum(Case(
                When(accounts__status='COMPLETED', then=1),
                default=0,
                output_field=IntegerField()
            )), Value(0))
        )
    )
    
    context = {
        'tasks': tasks,
        'active_tab': 'bulk_upload'
    }
    return render(request, 'uploader/bulk_upload/list.html', context)

@login_required
def create_bulk_upload(request):
    """Create a new bulk upload task with multiple Instagram accounts"""
    if request.method == 'POST':
        form = BulkUploadTaskForm(request.POST)
        if form.is_valid():
            # Create bulk upload task
            bulk_task = form.save()
            selected_accounts = form.cleaned_data['selected_accounts']
            
            # Create bulk upload accounts for each selected account
            for account in selected_accounts:
                # Use the proxy that's already assigned to the account (from Dolphin)
                proxy = account.proxy
                
                # Create bulk upload account
                BulkUploadAccount.objects.create(
                    bulk_task=bulk_task,
                    account=account,
                    proxy=proxy
                )
            
            messages.success(request, f'Bulk upload task "{bulk_task.name}" created successfully with {len(selected_accounts)} accounts!')
            return redirect('add_bulk_videos', task_id=bulk_task.id)
    else:
        form = BulkUploadTaskForm()
    
    context = {
        'form': form,
        'active_tab': 'bulk_upload'
    }
    return render(request, 'uploader/bulk_upload/create.html', context)

@login_required
def bulk_upload_detail(request, task_id):
    """View details of a bulk upload task"""
    task = get_object_or_404(BulkUploadTask, id=task_id)
    accounts = task.accounts.all().select_related('account', 'proxy')
    videos = task.videos.all()
    titles = task.titles.all()
    
    context = {
        'task': task,
        'accounts': accounts,
        'videos': videos,
        'titles': titles,
        'active_tab': 'bulk_upload'
    }
    return render(request, 'uploader/bulk_upload/detail.html', context)

@login_required
def add_bulk_videos(request, task_id):
    """Add videos to a bulk upload task"""
    task = get_object_or_404(BulkUploadTask, id=task_id)
    
    # Check if task is still editable
    if task.status not in ['PENDING']:
        messages.error(request, f'Cannot add videos to task "{task.name}" as it is already {task.status}')
        return redirect('bulk_upload_detail', task_id=task.id)
    
    if request.method == 'POST':
        form = BulkVideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Handle file upload - get the single file or multiple files
            # Input in template will have 'multiple' attribute, so we need to check
            # if we got a list of files or a single file
            if 'video_file' in request.FILES:
                files = request.FILES.getlist('video_file')
                
                # Save each file
                order = 1
                for video_file in files:
                    BulkVideo.objects.create(
                        bulk_task=task,
                        video_file=video_file,
                        order=order
                    )
                    order += 1
                
                messages.success(request, f'Added {len(files)} videos to task "{task.name}"')
                
                # Check if task already has titles
                if task.titles.exists():
                    return redirect('bulk_upload_detail', task_id=task.id)
                else:
                    return redirect('add_bulk_titles', task_id=task.id)
    else:
        form = BulkVideoUploadForm()
    
    # Get already uploaded videos
    videos = task.videos.all()
    
    context = {
        'form': form,
        'task': task,
        'videos': videos,
        'active_tab': 'bulk_upload'
    }
    return render(request, 'uploader/bulk_upload/add_videos.html', context)

@login_required
def add_bulk_titles(request, task_id):
    """Add titles from a text file to a bulk upload task"""
    task = get_object_or_404(BulkUploadTask, id=task_id)
    
    # Check if task is still editable
    if task.status not in ['PENDING']:
        messages.error(request, f'Cannot add titles to task "{task.name}" as it is already {task.status}')
        return redirect('bulk_upload_detail', task_id=task.id)
    
    if request.method == 'POST':
        form = BulkTitlesUploadForm(request.POST, request.FILES)
        if form.is_valid():
            titles_file = request.FILES['titles_file']
            
            # Read file content
            content = titles_file.read().decode('utf-8')
            titles = content.splitlines()
            
            # Clear any existing titles
            task.titles.all().delete()
            
            # Create title objects
            for title in titles:
                if title.strip():  # Skip empty lines
                    VideoTitle.objects.create(
                        bulk_task=task,
                        title=title.strip()
                    )
            
            messages.success(request, f'Added {len(titles)} titles to task "{task.name}"')
            
            # Automatically assign titles to videos
            assign_titles_to_videos(task)
            
            return redirect('bulk_upload_detail', task_id=task.id)
    else:
        form = BulkTitlesUploadForm()
    
    context = {
        'form': form,
        'task': task,
        'active_tab': 'bulk_upload'
    }
    return render(request, 'uploader/bulk_upload/add_titles.html', context)

def assign_titles_to_videos(task):
    """Assign titles to videos in a bulk upload task"""
    videos = task.videos.all()
    available_titles = task.titles.filter(used=False, assigned_to__isnull=True)
    
    if not videos or not available_titles:
        return
    
    # Assign titles to videos that don't have one yet
    for i, video in enumerate(videos):
        # Check if video already has a title assigned
        if hasattr(video, 'title_data') and video.title_data:
            continue
            
        # Get next available title
        if i < len(available_titles):
            title = available_titles[i]
            title.assigned_to = video
            title.used = True
            title.save(update_fields=['assigned_to', 'used'])

def assign_videos_to_accounts(task):
    """Assign ALL videos to ALL accounts in a bulk upload task (each video goes to every account)"""
    videos = task.videos.all()
    accounts = list(task.accounts.all())
    
    if not videos or not accounts:
        return
        
    # Assign each video to ALL accounts (not distribute)
    for video in videos:
        if video.assigned_to is None:  # Only assign if not already assigned
            # For now, we'll assign to the first account to maintain the current database structure
            # But the actual upload logic will handle uploading to all accounts
            video.assigned_to = accounts[0]
            video.save(update_fields=['assigned_to'])
            
    # Note: The actual upload logic in process_account_videos() already uses all_videos
    # which means each account will get all videos regardless of assigned_to field

def all_videos_assigned(task):
    """Check if all videos in a task have been assigned to accounts"""
    videos = task.videos.all()
    return all(video.assigned_to is not None for video in videos)

def all_titles_assigned(task):
    """Check if all videos in a task have titles assigned"""
    videos = task.videos.all()
    return all(hasattr(video, 'title_data') and video.title_data is not None for video in videos)

@login_required
def start_bulk_upload(request, task_id):
    """Start a bulk upload task"""
    task = get_object_or_404(BulkUploadTask, id=task_id)
    
    # Check if task is already running
    if task.status == TaskStatus.RUNNING:
        messages.warning(request, f'Task "{task.name}" is already running!')
        return redirect('bulk_upload_detail', task_id=task.id)
    
    # Check if task has videos and accounts
    if not task.videos.exists():
        messages.error(request, 'No videos found for this task!')
        return redirect('bulk_upload_detail', task_id=task.id)
    
    if not task.accounts.exists():
        messages.error(request, 'No accounts assigned to this task!')
        return redirect('bulk_upload_detail', task_id=task.id)
    
    # Always use async mode
    update_task_status(task, TaskStatus.RUNNING, "Task started in ASYNC mode")
    print(f"[TASK] Changing task {task.id}: {task.name} status to RUNNING")
    
    # Assign videos to accounts if not already done
    if not all_videos_assigned(task):
        assign_videos_to_accounts(task)
        print(f"[TASK] Assigning videos to accounts for task {task.id}: {task.name}")
    
    # Use async version - run in background thread
    try:
        from .async_bulk_tasks import run_async_bulk_upload_task_sync
        import threading
        print(f"[TASK] Starting async task in background for task {task.id}: {task.name}")
        
        # Update task status to RUNNING
        update_task_status(task, TaskStatus.RUNNING, "Async task started")
        
        # Run async task in background thread
        def run_async_task():
            try:
                result = run_async_bulk_upload_task_sync(task_id)
                print(f"[TASK] Async task completed for task {task_id}: {result}")
                # Coordinator already set the final status; preserve it here
                if result:
                    update_task_status(task, task.status, "Async task finished (status preserved)")
                else:
                    update_task_status(task, task.status, "Async task finished with errors (status preserved)")
            except Exception as e:
                print(f"[TASK] Async task failed for task {task_id}: {str(e)}")
                update_task_status(task, TaskStatus.FAILED, f"Async task failed: {str(e)}")
        
        # Start task in background thread
        thread = threading.Thread(target=run_async_task, daemon=True)
        thread.start()
        
        # Immediately redirect to logs page
        messages.success(request, f'Async bulk upload task "{task.name}" started successfully! You can monitor progress on this page.')
        return redirect('bulk_upload_detail', task_id=task.id)
        
    except Exception as e:
        print(f"[TASK] Failed to start async task for task {task_id}: {str(e)}")
        messages.error(request, f'Failed to start async task: {str(e)}')
        update_task_status(task, TaskStatus.FAILED, f"Failed to start async task: {str(e)}")
        return redirect('bulk_upload_detail', task_id=task.id)

@login_required
def get_bulk_task_logs(request, task_id):
    """Get logs for a bulk upload task as JSON with real-time updates"""
    from django.core.cache import cache
    import json
    
    task = get_object_or_404(BulkUploadTask, id=task_id)
    
    # Get account ID if specified for account-specific logs
    account_id = request.GET.get('account_id')
    
    # Get logs from cache (real-time) or fallback to database
    cache_key = f"task_logs_{task_id}"
    if account_id:
        cache_key += f"_account_{account_id}"
    
    # Get real-time logs from cache
    cached_logs = cache.get(cache_key, [])
    
    # Format logs for web display
    formatted_logs = []
    for log_entry in cached_logs:
        if isinstance(log_entry, dict):
            # New format from WebLogger
            formatted_logs.append({
                'timestamp': log_entry.get('timestamp', ''),
                'level': log_entry.get('level', 'INFO'),
                'message': log_entry.get('message', ''),
                'category': log_entry.get('category', 'GENERAL')
            })
        else:
            # Legacy format - plain text
            formatted_logs.append({
                'timestamp': '',
                'level': 'INFO',
                'message': str(log_entry),
                'category': 'LEGACY'
            })
    
    # If no cached logs, get from database as fallback
    if not formatted_logs:
        if account_id:
            try:
                account_task = task.accounts.get(id=account_id)
                db_log = account_task.log or ""
            except:
                db_log = ""
        else:
            db_log = task.log or ""
        
        if db_log:
            # Parse database log into structured format
            for line in db_log.split('\n'):
                if line.strip():
                    formatted_logs.append({
                        'timestamp': '',
                        'level': 'INFO',
                        'message': line.strip(),
                        'category': 'DATABASE'
                    })
    
    # Get task progress information
    total_accounts = task.accounts.count()
    completed_accounts = task.accounts.filter(status='COMPLETED').count()
    completion_percentage = int((completed_accounts / total_accounts * 100)) if total_accounts > 0 else 0
    
    # Prepare response data
    response_data = {
        'status': task.status,
        'logs': formatted_logs,
        'completion_percentage': completion_percentage,
        'completed_count': completed_accounts,
        'total_count': total_accounts,
        'last_update': cache.get(f"task_last_update_{task_id}", ''),
    }
    
    # Add account-specific information if requested
    if account_id:
        try:
            account_task = task.accounts.get(id=account_id)
            response_data['account_status'] = account_task.status
            response_data['account_username'] = account_task.account.username if account_task.account else f"Account {account_id}"
        except:
            pass
    
    return JsonResponse(response_data)

@login_required
def delete_bulk_upload(request, task_id):
    """Delete bulk upload task"""
    try:
        # Detailed logging
        print(f"[DELETE] Received request to delete task {task_id}, URL: {request.get_full_path()}")
        print(f"[DELETE] Request parameters: {request.GET}")
        
        force = request.GET.get('force') == '1'
        print(f"[DELETE] Force parameter: {force}")
        
        # Get task with error handling
        try:
            task = get_object_or_404(BulkUploadTask, id=task_id)
            print(f"[DELETE] Found task: {task.id}, name: {task.name}, status: {task.status}")
        except Exception as e:
            print(f"[DELETE] Error finding task: {str(e)}")
            messages.error(request, f"Error finding task: {str(e)}")
            return redirect('bulk_upload_list')
        
        # If force is not set and task is running, show confirmation
        if task.status == 'RUNNING' and not force:
            force_url = reverse('delete_bulk_upload', args=[task_id]) + '?force=1'
            print(f"[DELETE] Task is running, force not set. Redirecting to confirmation page.")
            messages.warning(request, 
                f'Task "{task.name}" is currently running. <a href="{force_url}" class="btn btn-sm btn-danger ms-3">Force Delete</a>',
                extra_tags='safe')
            return redirect('bulk_upload_detail', task_id=task.id)
        
        # Force delete all related objects
        task_name = task.name
        print(f"[DELETE] Starting to delete task {task_id}: {task_name}, status: {task.status}, force: {force}")
        
        try:
            # Delete related videos
            print(f"[DELETE] Deleting related videos...")
            video_count = task.videos.all().count()
            task.videos.all().delete()
            
            # Delete related account tasks
            print(f"[DELETE] Deleting related account tasks...")
            account_tasks = task.accounts.all()
            account_tasks.delete()
            
            # Delete related bulk upload task
            print(f"[DELETE] Deleting related bulk upload task...")
            task.delete()
            
            print(f"[DELETE] Task {task_id}: {task_name} deleted successfully")
            messages.success(request, f'Bulk upload task "{task_name}" deleted successfully')
        except Exception as e:
            print(f"[DELETE] Error deleting task: {str(e)}")
            messages.error(request, f"Error deleting task: {str(e)}")
            
    except Exception as e:
        print(f"[DELETE] Error in delete_bulk_upload: {str(e)}")
        messages.error(request, f"Error in delete_bulk_upload: {str(e)}")
    
    return redirect('bulk_upload_list')

@login_required
def create_cookie_robot_task(request):
    """Create a new cookie robot task"""
    if request.method == 'POST':
        # Get form data manually
        account_id = request.POST.get('account')
        urls_text = request.POST.get('urls', '')
        headless = request.POST.get('headless', '') == 'on'
        imageless = request.POST.get('imageless', '') == 'on'
        
        # Validate data
        if not account_id:
            logger.error("Cookie Robot task creation failed: No account selected")
            messages.error(request, 'Please select an account')
            return redirect('create_cookie_robot_task')
        
        # Parse URLs
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        if not urls:
            logger.error("Cookie Robot task creation failed: No URLs provided")
            messages.error(request, 'Please enter at least one URL')
            return redirect('create_cookie_robot_task')
        
        # Get account
        try:
            account = InstagramAccount.objects.get(id=account_id)
            logger.info(f"Creating Cookie Robot task for account: {account.username}")
        except InstagramAccount.DoesNotExist:
            logger.error(f"Cookie Robot task creation failed: Account with ID {account_id} not found")
            messages.error(request, 'Account not found')
            return redirect('create_cookie_robot_task')
        
        # Create task - using UploadTask for now
        initial_log = f"Cookie Robot Task\n"
        
        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Task created"
        initial_log += log_message + "\n"
        logger.info(log_message)
        
        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Account: {account.username}"
        initial_log += log_message + "\n"
        logger.info(log_message)
        
        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] URLs: {urls}"
        initial_log += log_message + "\n"
        logger.info(log_message)
        
        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Headless: {headless}"
        initial_log += log_message + "\n"
        logger.info(log_message)
        
        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Imageless: {imageless}"
        initial_log += log_message + "\n"
        logger.info(log_message)
        
        task = UploadTask.objects.create(
            account=account,
            status='PENDING',
            log=initial_log
        )
        
        logger.info(f"Cookie Robot task created successfully! Task ID: {task.id}")
        messages.success(request, f'Cookie Robot task created successfully! Task ID: {task.id}')
        
        # Start task in background thread
        thread = threading.Thread(target=run_cookie_robot_task, args=(task.id, urls, headless, imageless))
        thread.daemon = True
        thread.start()
        logger.info(f"Task {task.id} started in background thread")
        messages.info(request, 'Task started in background.')
        
        return redirect('cookie_task_detail', task_id=task.id)
    else:
        # Get accounts with Dolphin profiles
        accounts = InstagramAccount.objects.filter(dolphin_profile_id__isnull=False)
        logger.info(f"Found {accounts.count()} accounts with Dolphin profiles for Cookie Robot")
        
        # Get account ID from query parameter
        account_id = request.GET.get('account')
        selected_account = None
        if account_id:
            try:
                selected_account = accounts.get(id=account_id)
                logger.info(f"Selected account for Cookie Robot: {selected_account.username}")
            except InstagramAccount.DoesNotExist:
                logger.warning(f"Account with ID {account_id} not found for Cookie Robot")
                pass
        
        context = {
            'accounts': accounts,
            'selected_account': selected_account,
            'active_tab': 'cookies'
        }
        return render(request, 'uploader/cookies/create_task.html', context)

@login_required
def cookie_task_detail(request, task_id):
    """View details of a specific cookie robot task"""
    task = get_object_or_404(UploadTask, id=task_id)
    logger.info(f"Viewing Cookie Robot task detail for task ID: {task_id}")
    
    # Extract URLs from the log
    import re
    urls_match = re.search(r'URLs: \[(.*?)\]', task.log)
    urls = []
    if urls_match:
        urls_text = urls_match.group(1)
        urls = [url.strip().strip("'\"") for url in urls_text.split(',')]
        logger.info(f"Extracted {len(urls)} URLs from task {task_id} log using regex pattern")
    else:
        # Try to extract from new format
        logger.info(f"Trying to extract URLs from new log format for task {task_id}")
        for line in task.log.split('\n'):
            if 'URLs to visit:' in line or 'URLs:' in line:
                urls_text = line.split(':', 1)[1].strip()
                if urls_text.startswith('[') and urls_text.endswith(']'):
                    urls_text = urls_text[1:-1]
                urls = [url.strip().strip("'\"") for url in urls_text.split(',')]
                logger.info(f"Extracted {len(urls)} URLs from task {task_id} log line")
                break
    
    # Extract headless and imageless settings
    headless = 'Headless: True' in task.log
    imageless = 'Imageless: True' in task.log
    logger.info(f"Task {task_id} settings - Headless: {headless}, Imageless: {imageless}")
    
    context = {
        'task': task,
        'urls': urls,
        'headless': headless,
        'imageless': imageless,
        'active_tab': 'cookies'
    }
    return render(request, 'uploader/cookies/task_detail.html', context)

@login_required
def cookie_dashboard(request):
    """Dashboard for cookie robot tasks"""
    # Get recent cookie tasks
    tasks = UploadTask.objects.filter(log__contains='Cookie Robot').order_by('-created_at')[:10]
    
    # Get all cookie robot tasks for statistics
    all_cookie_tasks = UploadTask.objects.filter(log__contains='Cookie Robot')
    
    # Get accounts with Dolphin profiles
    accounts_with_profiles = InstagramAccount.objects.filter(dolphin_profile_id__isnull=False).count()
    total_accounts = InstagramAccount.objects.count()
    
    # Task statistics by status
    task_stats = {
        'total': all_cookie_tasks.count(),
        'pending': all_cookie_tasks.filter(status='PENDING').count(),
        'running': all_cookie_tasks.filter(status='RUNNING').count(),
        'completed': all_cookie_tasks.filter(status='COMPLETED').count(),
        'failed': all_cookie_tasks.filter(status='FAILED').count(),
        'cancelled': all_cookie_tasks.filter(status='CANCELLED').count(),
    }
    
    # Calculate success rate
    finished_tasks = task_stats['completed'] + task_stats['failed'] + task_stats['cancelled']
    task_stats['success_rate'] = round((task_stats['completed'] / finished_tasks * 100) if finished_tasks > 0 else 0, 1)
    
    # Recent activity (last 24 hours)
    yesterday = timezone.now() - timedelta(days=1)
    recent_tasks = all_cookie_tasks.filter(created_at__gte=yesterday)
    
    recent_stats = {
        'total_24h': recent_tasks.count(),
        'completed_24h': recent_tasks.filter(status='COMPLETED').count(),
        'failed_24h': recent_tasks.filter(status='FAILED').count(),
        'running_24h': recent_tasks.filter(status='RUNNING').count(),
    }
    
    # Accounts usage statistics
    accounts_with_tasks = all_cookie_tasks.values('account').distinct().count()
    accounts_stats = {
        'with_tasks': accounts_with_tasks,
        'without_tasks': total_accounts - accounts_with_tasks,
        'usage_rate': round((accounts_with_tasks / total_accounts * 100) if total_accounts > 0 else 0, 1)
    }
    
    context = {
        'tasks': tasks,
        'accounts_with_profiles': accounts_with_profiles,
        'total_accounts': total_accounts,
        'task_stats': task_stats,
        'recent_stats': recent_stats,
        'accounts_stats': accounts_stats,
        'active_tab': 'cookies'
    }
    return render(request, 'uploader/cookies/dashboard.html', context)

@login_required
def cookie_task_list(request):
    """List all cookie robot tasks"""
    tasks = UploadTask.objects.filter(log__contains='Cookie Robot').order_by('-created_at')
    
    context = {
        'tasks': tasks,
        'active_tab': 'cookies'
    }
    return render(request, 'uploader/cookies/task_list.html', context)

@login_required
def start_cookie_task(request, task_id):
    """Start a cookie robot task"""
    task = get_object_or_404(UploadTask, id=task_id)
    
    if task.status != 'PENDING':
        messages.error(request, f'Task {task.id} is already {task.status}')
        return redirect('cookie_task_detail', task_id=task.id)
    
    # Extract URLs from the log
    import re
    urls_match = re.search(r'URLs: \[(.*?)\]', task.log)
    urls = []
    if urls_match:
        urls_text = urls_match.group(1)
        urls = [url.strip().strip("'\"") for url in urls_text.split(',')]
    else:
        # Try to extract from new format
        for line in task.log.split('\n'):
            if 'URLs to visit:' in line or 'URLs:' in line:
                urls_text = line.split(':', 1)[1].strip()
                if urls_text.startswith('[') and urls_text.endswith(']'):
                    urls_text = urls_text[1:-1]
                urls = [url.strip().strip("'\"") for url in urls_text.split(',')]
                break
    
    # Extract headless and imageless settings
    headless = 'Headless: True' in task.log
    imageless = 'Imageless: True' in task.log
    
    # Start task in background thread
    thread = threading.Thread(target=run_cookie_robot_task, args=(task.id, urls, headless, imageless))
    thread.daemon = True
    thread.start()
    
    messages.success(request, f'Cookie Robot task {task.id} started!')
    return redirect('cookie_task_detail', task_id=task.id)

@login_required
def account_cookies(request, account_id):
    """View cookies for a specific account"""
    account = get_object_or_404(InstagramAccount, id=account_id)
    
    # Get cookies from database
    cookies = InstagramCookies.objects.filter(account=account).order_by('-created_at').first()
    
    # Format cookies for display
    formatted_cookies = None
    if cookies and cookies.cookies_data:
        try:
            cookie_data = json.loads(cookies.cookies_data)
            formatted_cookies = json.dumps(cookie_data, indent=2)
        except Exception as e:
            logger.error(f"Error formatting cookies for account {account.username}: {str(e)}")
            formatted_cookies = cookies.cookies_data
    
    context = {
        'account': account,
        'cookies': cookies,
        'formatted_cookies': formatted_cookies,
        'active_tab': 'cookies'
    }
    return render(request, 'uploader/cookies/account_cookies.html', context)

@login_required
def get_cookie_task_logs(request, task_id):
    """Get logs for a cookie robot task as JSON for AJAX updates"""
    task = get_object_or_404(UploadTask, id=task_id)
    
    # Extract URLs from the log for additional context
    import re
    urls_match = re.search(r'URLs: \[(.*?)\]', task.log)
    urls = []
    if urls_match:
        urls_text = urls_match.group(1)
        urls = [url.strip().strip("'\"") for url in urls_text.split(',')]
    else:
        # Try to extract from new format
        for line in task.log.split('\n'):
            if 'URLs to visit:' in line or 'URLs:' in line:
                urls_text = line.split(':', 1)[1].strip()
                if urls_text.startswith('[') and urls_text.endswith(']'):
                    urls_text = urls_text[1:-1]
                urls = [url.strip().strip("'\"") for url in urls_text.split(',')]
                break
    
    # Extract headless and imageless settings
    headless = 'Headless: True' in task.log
    imageless = 'Imageless: True' in task.log
    
    response_data = {
        'status': task.status,
        'log': task.log,
        'updated_at': task.updated_at.isoformat() if task.updated_at else None,
        'urls': urls,
        'headless': headless,
        'imageless': imageless
    }
    
    return JsonResponse(response_data)

@csrf_exempt
@require_POST
def stop_cookie_task(request, task_id):
    """Stop a running cookie robot task"""
    task = get_object_or_404(UploadTask, id=task_id)
    
    # Check if task is in a stoppable state
    if task.status not in ['RUNNING', 'PENDING']:
        messages.error(request, f'Cannot stop task {task.id} - it is {task.status}')
        # Return to referring page or task list if no referrer
        referrer = request.META.get('HTTP_REFERER')
        if referrer:
            return redirect(referrer)
        else:
            return redirect('cookie_task_list')
    
    try:
        # Update task status
        task.status = 'CANCELLED'
        
        # Add cancellation log entry
        cancellation_log = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 🛑 Task manually stopped by user\n"
        task.log += cancellation_log
        logger.info(f"Cookie Robot task {task.id} manually stopped by user")
        
        task.save()
        
        messages.success(request, f'Cookie Robot task {task.id} has been stopped')
        
    except Exception as e:
        logger.error(f"Error stopping Cookie Robot task {task.id}: {str(e)}")
        messages.error(request, f'Error stopping task: {str(e)}')
    
    # Return to referring page (task list, dashboard, etc.) or task detail if no referrer
    referrer = request.META.get('HTTP_REFERER')
    if referrer:
        return redirect(referrer)
    else:
        return redirect('cookie_task_detail', task_id=task.id)

@login_required
def delete_cookie_task(request, task_id):
    """Delete a cookie robot task"""
    task = get_object_or_404(UploadTask, id=task_id)
    
    # Check if this is a Cookie Robot task
    if 'Cookie Robot' not in task.log:
        messages.error(request, 'This is not a Cookie Robot task')
        return redirect('cookie_task_list')
    
    if request.method == 'POST':
        # Check for force parameter
        force = request.POST.get('force') == '1'
        
        # If task is running and force is not set, show warning
        if task.status == 'RUNNING' and not force:
            messages.warning(request, 
                f'Task {task.id} is currently running. Are you sure you want to delete it?'
            )
            
            context = {
                'task': task,
                'confirm_delete': True,
                'active_tab': 'cookies'
            }
            return render(request, 'uploader/cookies/delete_task.html', context)
        
        try:
            # Store task info for message
            task_account = task.account.username if task.account else 'Unknown'
            task_number = task.id
            
            # Update status if running
            if task.status == 'RUNNING':
                task.status = 'CANCELLED'
                log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [DELETE] Task deleted while running"
                safe_message = safe_log_message(log_message)
                task.log += safe_message + "\n"
                task.save()
            
            # Delete the task
            task.delete()
            
            logger.info(f"Cookie Robot task {task_number} for account {task_account} deleted")
            messages.success(request, f'Cookie Robot task {task_number} for account {task_account} deleted successfully')
            
        except Exception as e:
            logger.error(f"Error deleting Cookie Robot task {task_id}: {str(e)}")
            messages.error(request, f'Error deleting task: {str(e)}')
        
        return redirect('cookie_task_list')
    
    # GET request - show confirmation page
    context = {
        'task': task,
        'confirm_delete': False,
        'active_tab': 'cookies'
    }
    return render(request, 'uploader/cookies/delete_task.html', context)

# Global semaphore for Cookie Robot concurrency
_COOKIE_ROBOT_SEMAPHORE = threading.Semaphore(getattr(settings, 'COOKIE_ROBOT_CONCURRENCY', 5))

def run_cookie_robot_task(task_id, urls, headless, imageless):
    """
    Run cookie robot task in background thread
    """
    from django.utils import timezone
    from uploader.models import InstagramAccount
    
    # Concurrency control: ensure not more than N tasks run simultaneously
    acquired = _COOKIE_ROBOT_SEMAPHORE.acquire(timeout=5)
    if not acquired:
        # If cannot acquire immediately, wait a bit longer
        _COOKIE_ROBOT_SEMAPHORE.acquire()
    
    try:
        # Debug information
        logger.info(f"[COOKIE ROBOT TASK] Starting task {task_id}")
        logger.info(f"[COOKIE ROBOT TASK] URLs received: {urls}")
        logger.info(f"[COOKIE ROBOT TASK] Headless: {headless}")
        logger.info(f"[COOKIE ROBOT TASK] Imageless: {imageless}")
        
        # Get the task object
        task = UploadTask.objects.get(id=task_id)
        
        # Check if task was cancelled before starting
        if task.status == 'CANCELLED':
            logger.info(f"Cookie Robot task {task_id} was cancelled before execution")
            return
        
        # Get the associated account
        try:
            account = InstagramAccount.objects.get(id=task.account.id)
        except InstagramAccount.DoesNotExist:
            logger.error(f"Instagram account not found for task {task_id}")
            task.status = 'FAILED'
            task.log += "[ERROR] Instagram account not found\n"
            task.save()
            return
        
        # Check if account has a Dolphin profile
        if not account.dolphin_profile_id:
            error_msg = f"Account {account.username} does not have a Dolphin profile"
            logger.error(f"[COOKIE_ROBOT] {error_msg}")
            task.status = 'FAILED'
            task.log += f"[ERROR] {error_msg}\n"
            task.save()
            return
        
        # Get API token
        api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
        if not api_key:
            error_msg = "Dolphin API token not found in environment variables"
            logger.error(f"[COOKIE_ROBOT] {error_msg}")
            task.status = 'FAILED'
            task.log += f"[ERROR] {error_msg}\n"
            task.save()
            return
        
        # Initialize Dolphin API client
        from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
        
        # Get Dolphin API host from environment (critical for Docker Windows deployment)
        dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
        if not dolphin_api_host.endswith("/v1.0"):
            dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
        
        dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
        
        # Check Dolphin status before proceeding
        dolphin_status = dolphin.check_dolphin_status()
        if not dolphin_status.get("authenticated", False):
            error_msg = f"Dolphin Anty API not available: {dolphin_status.get('error', 'Unknown error')}"
            logger.error(f"[COOKIE_ROBOT] {error_msg}")
            task.status = 'FAILED'
            task.log += f"[ERROR] {error_msg}\n"
            task.log += f"[INFO] Please ensure Dolphin Anty is running and Local API is enabled on port 3001\n"
            task.save()
            return
        
        # Define logging function for the task
        def task_logger_func(message):
            try:
                # Обновляем статус задачи в реальном времени
                task.refresh_from_db()
                if task.status != 'CANCELLED':
                    task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"
                    task.save()
                    logger.info(f"[TASK {task_id}] {message}")
            except Exception as e:
                logger.error(f"Error in task_logger_func: {str(e)}")
        
        # Run the cookie robot
        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [START] Starting Cookie Robot on Dolphin profile {account.dolphin_profile_id}..."
        safe_message = safe_log_message(log_message)
        task.log += safe_message + "\n"
        logger.info(safe_message)
        
        # Обновляем статус на RUNNING
        task.status = 'RUNNING'
        task.save()
        
        # Добавляем информацию о параметрах
        task_logger_func(f"[INFO] Processing {len(urls)} URLs")
        task_logger_func(f"[INFO] Headless mode: {headless}")
        task_logger_func(f"[INFO] Disable images: {imageless}")
        task_logger_func(f"[INFO] Account: {account.username}")
        
        # Execute with internal retries for more robustness
        result = None
        backoffs = [0, 2, 5]  # seconds
        for attempt, delay in enumerate(backoffs, start=1):
            if delay:
                time.sleep(delay)
            result = dolphin.run_cookie_robot_sync(
                profile_id=account.dolphin_profile_id,
                urls=urls,
                headless=headless,
                imageless=imageless,
                task_logger=task_logger_func  # Pass the logger function
            )
            # Stop retry if not profile start/connection related error
            err = (result or {}).get('error', '') or ''
            if not err or 'Failed to start profile' not in err and 'Missing port or wsEndpoint' not in err and 'connect_over_cdp' not in err:
                break
            task_logger_func(f"[RETRY] Attempt {attempt} failed: {err}")
        
        # Refresh task from database to get latest logs and check for cancellation
        task = UploadTask.objects.get(id=task_id)
        
        # If task was cancelled during execution, don't update status
        if task.status == 'CANCELLED':
            logger.info(f"Cookie Robot task {task_id} was cancelled during execution")
            return
        
        # Helper to get success metrics from result
        def extract_success_metrics(res: dict):
            data = res.get('data') or {}
            successful = data.get('successful_visits')
            failed = data.get('failed_visits')
            success_rate = data.get('success_rate')
            return successful, failed, success_rate
        
        # Update task with result
        if result.get('success', False):
            successful, failed, success_rate = extract_success_metrics(result)
            # If success as a whole, keep COMPLETED, but log metrics
            task.status = 'COMPLETED'
            log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] Cookie Robot completed successfully!"
            safe_message = safe_log_message(log_message)
            task.log += safe_message + "\n"
            logger.info(safe_message)
            
            if successful is not None:
                task.log += f"Successful visits: {successful}\n";
            if failed is not None:
                task.log += f"Failed visits: {failed}\n";
            if success_rate is not None:
                task.log += f"Success rate: {success_rate}%\n";
            
            log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Response details:"
            task.log += log_message + "\n"
            logger.info(log_message)
            
            response_json = json.dumps(result.get('data', {}), indent=2)
            task.log += response_json + "\n"
            logger.info(f"Response JSON: {response_json}")
        else:
            # Check for partial success conditions
            successful, failed, success_rate = (None, None, None)
            if isinstance(result, dict):
                successful, failed, success_rate = extract_success_metrics(result)
            
            error_details = result.get('error', 'Unknown error')
            
            # Treat as partial success if more than 10 successes or >= 25% success rate
            partial_condition = False
            if successful is not None and successful >= 10:
                partial_condition = True
            if success_rate is not None:
                try:
                    if float(success_rate) >= 25:
                        partial_condition = True
                except Exception:
                    pass
            
            if partial_condition:
                task.status = 'PARTIALLY_COMPLETED'
                note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] Partial success: visited {successful} sites (failed reason: {error_details})"
                safe_message = safe_log_message(note)
                task.log += safe_message + "\n"
                logger.warning(safe_message)
                
                summary = {
                    'successful_visits': successful,
                    'failed_visits': failed,
                    'success_rate': success_rate,
                    'error': error_details,
                }
                task.log += json.dumps(summary, indent=2) + "\n"
            else:
                # Regular failure
                # Check if it's a human verification error
                if error_details == 'HUMAN_VERIFICATION_REQUIRED':
                    task.status = 'FAILED'
                    log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Human verification required for this account"
                    safe_message = safe_log_message(log_message)
                    task.log += safe_message + "\n"
                    logger.error(safe_message)
                    
                    # Update the Instagram account status
                    try:
                        instagram_account = InstagramAccount.objects.get(username=account.username)
                        instagram_account.status = 'HUMAN_VERIFICATION_REQUIRED'
                        instagram_account.save()
                        
                        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Updated account {account.username} status to HUMAN_VERIFICATION_REQUIRED"
                        safe_message = safe_log_message(log_message)
                        task.log += safe_message + "\n"
                        logger.info(safe_message)
                    except Exception as update_error:
                        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] Could not update account status: {str(update_error)}"
                        safe_message = safe_log_message(log_message)
                        task.log += safe_message + "\n"
                        logger.warning(safe_message)
                else:
                    task.status = 'FAILED'
                    log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Cookie Robot failed: {error_details}"
                    safe_message = safe_log_message(log_message)
                    task.log += safe_message + "\n"
                    logger.error(safe_message)
                    
                    # Add full error details if available
                    if isinstance(error_details, dict):
                        error_json = json.dumps(error_details, indent=2)
                        task.log += f"Full error details:\n{error_json}\n"
                        logger.error(f"Full API error: {error_json}")
        
        task.save()
        
    finally:
        # Release semaphore to allow next task to start
        try:
            _COOKIE_ROBOT_SEMAPHORE.release()
        except Exception:
            pass

@login_required
def bulk_cookie_robot(request):
    """Create and run Cookie Robot tasks on multiple accounts"""
    if request.method == 'POST':
        # Get selected accounts
        account_ids = request.POST.getlist('accounts')
        urls_text = request.POST.get('urls', '')
        headless = request.POST.get('headless', '') == 'on'
        imageless = request.POST.get('imageless', '') == 'on'
        
        # Parse URLs
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        # Debug information
        logger.info(f"[BULK COOKIE ROBOT] Received request:")
        logger.info(f"[BULK COOKIE ROBOT] Account IDs: {account_ids}")
        logger.info(f"[BULK COOKIE ROBOT] URLs text length: {len(urls_text)}")
        logger.info(f"[BULK COOKIE ROBOT] Parsed URLs: {urls}")
        logger.info(f"[BULK COOKIE ROBOT] Headless: {headless}")
        logger.info(f"[BULK COOKIE ROBOT] Imageless: {imageless}")
        
        if not account_ids:
            messages.error(request, 'Please select at least one account')
            return redirect('bulk_cookie_robot')
        
        if not urls:
            messages.error(request, 'Please enter at least one URL')
            return redirect('bulk_cookie_robot')
        
        # Create tasks for each account
        created_tasks = []
        for account_id in account_ids:
            try:
                account = InstagramAccount.objects.get(id=account_id)
                
                # Skip accounts without Dolphin profile
                if not account.dolphin_profile_id:
                    messages.warning(request, f'Account {account.username} skipped: No Dolphin profile')
                    continue
                
                # Create task
                initial_log = f"Cookie Robot Task\n"
                log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] Task created for account: {account.username}"
                safe_message = safe_log_message(log_message)
                initial_log += safe_message + "\n"
                logger.info(safe_message)
                
                log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [LIST] URLs to visit: {urls}"
                safe_message = safe_log_message(log_message)
                initial_log += safe_message + "\n"
                logger.info(safe_message)
                
                log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [TOOL] Headless mode: {headless}"
                safe_message = safe_log_message(log_message)
                initial_log += safe_message + "\n"
                logger.info(safe_message)
                
                log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [IMAGE] Disable images: {imageless}"
                safe_message = safe_log_message(log_message)
                initial_log += safe_message + "\n"
                logger.info(safe_message)
                
                task = UploadTask.objects.create(
                    account=account,
                    status='PENDING',
                    log=initial_log
                )
                
                created_tasks.append(task)
                
            except InstagramAccount.DoesNotExist:
                messages.error(request, f'Account with ID {account_id} not found')
            except Exception as e:
                messages.error(request, f'Error creating task: {str(e)}')
        
        # Start tasks in background
        if created_tasks:
            messages.success(request, f'Created {len(created_tasks)} Cookie Robot tasks')
            
            # Start tasks in background
            for task in created_tasks:
                thread = threading.Thread(target=run_cookie_robot_task, args=(task.id, urls, headless, imageless))
                thread.daemon = True
                thread.start()
                logger.info(f"Started Cookie Robot task {task.id} for account {task.account.username}")
                
            return redirect('cookie_task_list')
        else:
            messages.error(request, 'No tasks were created')
            return redirect('bulk_cookie_robot')
    
    # GET request - show form
    # Get accounts with Dolphin profiles - sort by creation date descending (newest first)
    accounts = InstagramAccount.objects.filter(dolphin_profile_id__isnull=False).order_by('-created_at')
    
    # Default URLs for the form
    default_urls = [
        "https://google.com",
        "https://yandex.ru",
        "https://vk.com",
        "https://twitter.com",
        "https://t.me",
        "https://youtube.com",
        "https://twitch.tv",
        "https://amazon.com",
        "https://ozon.ru",
        "https://wildberries.ru",
        "https://aliexpress.com",
        "https://ebay.com",
        "https://walmart.com",
        "https://etsy.com",
        "https://booking.com",
        "https://airbnb.com",
        "https://netflix.com",
        "https://hulu.com",
        "https://spotify.com",
        "https://apple.com",
        "https://microsoft.com",
        "https://github.com",
        "https://gitlab.com",
        "https://stackoverflow.com",
        "https://medium.com",
        "https://reddit.com",
        "https://quora.com",
        "https://cnn.com",
        "https://bbc.com",
        "https://theguardian.com",
        "https://forbes.com",
        "https://bloomberg.com",
        "https://techcrunch.com",
        "https://cnet.com",
        "https://w3schools.com",
        "https://udemy.com",
        "https://coursera.org",
        "https://linkedin.com",
        "https://wikipedia.org"
    ]
    
    context = {
        'accounts': accounts,
        'default_urls': '\n'.join(default_urls),
        'active_tab': 'cookies'
    }
    return render(request, 'uploader/cookies/bulk_cookie_robot.html', context)

@login_required
def create_dolphin_profile(request, account_id):
    """Create a Dolphin profile for an existing account"""
    account = get_object_or_404(InstagramAccount, id=account_id)
    
    # Check if account already has a Dolphin profile
    if account.dolphin_profile_id:
        messages.warning(request, f'Account {account.username} already has a Dolphin profile: {account.dolphin_profile_id}')
        return redirect('account_detail', account_id=account.id)
    
    # Check if account has a proxy
    if not account.proxy:
        messages.error(request, f'Account {account.username} needs a proxy before creating a Dolphin profile. Please assign a proxy first.')
        return redirect('change_account_proxy', account_id=account.id)
    
    try:
        logger.info(f"[CREATE PROFILE] Creating Dolphin profile for account {account.username}")
        
        # Initialize Dolphin API
        api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
        if not api_key:
            logger.error("[CREATE PROFILE] Dolphin API token not found in environment variables")
            messages.error(request, "Dolphin API token not configured. Please set DOLPHIN_API_TOKEN environment variable.")
            return redirect('account_detail', account_id=account.id)
        
        # Get Dolphin API host from environment (critical for Docker Windows deployment)
        dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
        if not dolphin_api_host.endswith("/v1.0"):
            dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
        
        dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
        
        # Authenticate with Dolphin
        if not dolphin.authenticate():
            logger.error("[CREATE PROFILE] Failed to authenticate with Dolphin Anty API")
            messages.error(request, "Failed to authenticate with Dolphin Anty API. Check your API token.")
            return redirect('account_detail', account_id=account.id)
        
        # Create profile name
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        profile_name = f"instagram_{account.username}_{random_suffix}"
        logger.info(f"[CREATE PROFILE] Creating Dolphin profile '{profile_name}'")
        
        # Get proxy data
        proxy_data = account.proxy.to_dict()
        logger.info(f"[CREATE PROFILE] Using proxy: {proxy_data.get('host')}:{proxy_data.get('port')}")
        
        # Create Dolphin profile
        response = dolphin.create_profile(
            name=profile_name,
            proxy=proxy_data,
            tags=["instagram", "manual-created"],
            locale='ru_RU'
        )
        
        # Extract profile ID from response
        profile_id = None
        if response and isinstance(response, dict):
            profile_id = response.get("browserProfileId")
            if not profile_id and isinstance(response.get("data"), dict):
                profile_id = response["data"].get("id")
        
        if profile_id:
            # Save profile ID to account
            account.dolphin_profile_id = profile_id
            account.save(update_fields=['dolphin_profile_id'])
            
            logger.info(f"[CREATE PROFILE] Successfully created Dolphin profile {profile_id} for account {account.username}")
            messages.success(request, f'Dolphin profile {profile_id} created successfully for account {account.username}!')
        else:
            error_message = response.get("error", "Unknown error") if isinstance(response, dict) else "Unknown error"
            logger.error(f"[CREATE PROFILE] Failed to create Dolphin profile: {error_message}")
            messages.error(request, f'Failed to create Dolphin profile: {error_message}')
    
    except Exception as e:
        logger.error(f"[CREATE PROFILE] Error creating Dolphin profile for account {account.username}: {str(e)}")
        messages.error(request, f'Error creating Dolphin profile: {str(e)}')
    
    return redirect('account_detail', account_id=account.id)

@login_required
def edit_video_location_mentions(request, video_id):
    """Edit location and mentions for a specific video"""
    video = get_object_or_404(BulkVideo, id=video_id)
    task = video.bulk_task
    
    # Check if task is still editable
    if task.status not in ['PENDING']:
        messages.error(request, f'Cannot edit video in task "{task.name}" as it is already {task.status}')
        return redirect('bulk_upload_detail', task_id=task.id)
    
    if request.method == 'POST':
        form = BulkVideoLocationMentionsForm(request.POST, instance=video)
        if form.is_valid():
            form.save()
            messages.success(request, f'Location and mentions updated for video {video.id}')
            return redirect('bulk_upload_detail', task_id=task.id)
    else:
        form = BulkVideoLocationMentionsForm(instance=video)
    
    context = {
        'form': form,
        'video': video,
        'task': task,
        'active_tab': 'bulk_upload'
    }
    return render(request, 'uploader/bulk_upload/edit_video_location_mentions.html', context)

@login_required
def bulk_edit_location_mentions(request, task_id):
    """Bulk edit location and mentions for all videos in a task"""
    task = get_object_or_404(BulkUploadTask, id=task_id)
    
    # Check if task is still editable
    if task.status not in ['PENDING']:
        messages.error(request, f'Cannot edit videos in task "{task.name}" as it is already {task.status}')
        return redirect('bulk_upload_detail', task_id=task.id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        location = request.POST.get('location', '').strip()
        mentions = request.POST.get('mentions', '').strip()
        
        if action == 'apply_to_all':
            # Apply to all videos
            videos = task.videos.all()
            updated_count = 0
            for video in videos:
                video.location = location
                video.mentions = mentions
                video.save(update_fields=['location', 'mentions'])
                updated_count += 1
            
            messages.success(request, f'Location and mentions updated for {updated_count} videos')
            
        elif action == 'apply_to_selected':
            # Apply to selected videos
            selected_video_ids = request.POST.getlist('selected_videos')
            if selected_video_ids:
                videos = task.videos.filter(id__in=selected_video_ids)
                updated_count = 0
                for video in videos:
                    video.location = location
                    video.mentions = mentions
                    video.save(update_fields=['location', 'mentions'])
                    updated_count += 1
                
                messages.success(request, f'Location and mentions updated for {updated_count} selected videos')
            else:
                messages.warning(request, 'No videos selected')
        
        return redirect('bulk_upload_detail', task_id=task.id)
    
    videos = task.videos.all()
    
    context = {
        'task': task,
        'videos': videos,
        'active_tab': 'bulk_upload'
    }
    return render(request, 'uploader/bulk_upload/bulk_edit_location_mentions.html', context)

@login_required
def bulk_change_proxy(request):
    """Bulk change proxies for multiple accounts"""
    if request.method == 'POST':
        account_ids = request.POST.getlist('account_ids')
        action = request.POST.get('action')
        
        if not account_ids:
            messages.error(request, 'No accounts selected')
            return redirect('account_list')
        
        accounts = InstagramAccount.objects.filter(id__in=account_ids)
        
        if action == 'auto_assign':
            # Auto-assign available proxies to selected accounts
            # Try to match regions when possible
            available_proxies = list(Proxy.objects.filter(
                assigned_account__isnull=True,
                is_active=True
            ).order_by('host', 'port'))
            
            if len(available_proxies) < len(accounts):
                messages.warning(request, f'Only {len(available_proxies)} proxies available for {len(accounts)} accounts. Some accounts will not get a proxy.')
            
            success_count = 0
            error_count = 0
            region_mismatch_count = 0
            
            for account in accounts:
                if not available_proxies:
                    # No more proxies available
                    break
                    
                proxy = None
                old_proxy = account.proxy
                
                # Try to find a proxy from the same region first if account has a proxy with region
                if old_proxy and old_proxy.country:
                    same_region_proxies = [p for p in available_proxies if p.country == old_proxy.country]
                    if same_region_proxies:
                        proxy = same_region_proxies[0]
                        available_proxies.remove(proxy)
                        logger.info(f"[BULK CHANGE] Found same region proxy for {account.username}: {old_proxy.country}")
                    else:
                        # No same region proxy available, use any available proxy (force)
                        proxy = available_proxies.pop(0)
                        region_mismatch_count += 1
                        logger.warning(f"[BULK CHANGE] No same region proxy for {account.username}, using different region: {old_proxy.country} -> {proxy.country if proxy.country else 'Unknown'}")
                else:
                    # Account has no region info or no current proxy, just assign any available proxy
                    proxy = available_proxies.pop(0)
                
                if proxy:
                    try:
                        # Update account proxy - update both proxy and current_proxy fields
                        account.proxy = proxy
                        account.current_proxy = proxy
                        account.save(update_fields=['proxy', 'current_proxy'])
                        
                        # Update proxy assignment
                        proxy.assigned_account = account
                        proxy.save(update_fields=['assigned_account'])
                        
                        # Clear old proxy assignment
                        if old_proxy:
                            old_proxy.assigned_account = None
                            old_proxy.save(update_fields=['assigned_account'])
                        
                        # Update Dolphin profile if exists
                        if account.dolphin_profile_id:
                            try:
                                api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
                                if api_key:
                                    from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
                                    dolphin = DolphinAnty(api_key=api_key)
                                    
                                    if dolphin.authenticate():
                                        proxy_data = proxy.to_dict()
                                        result = dolphin.update_profile_proxy(account.dolphin_profile_id, proxy_data)
                                        
                                        if not result.get("success"):
                                            logger.warning(f"[BULK CHANGE] Failed to update Dolphin profile {account.dolphin_profile_id} for account {account.username}")
                            except Exception as e:
                                logger.error(f"[BULK CHANGE] Error updating Dolphin profile for account {account.username}: {str(e)}")
                        
                        success_count += 1
                        region_info = ""
                        if old_proxy and old_proxy.country and proxy.country:
                            if old_proxy.country != proxy.country:
                                region_info = f" (region changed: {old_proxy.country} -> {proxy.country})"
                            else:
                                region_info = f" (same region: {old_proxy.country})"
                        logger.info(f"[BULK CHANGE] Successfully assigned proxy {proxy} to account {account.username}{region_info}")
                        
                    except Exception as e:
                        error_count += 1
                        logger.error(f"[BULK CHANGE] Error assigning proxy to account {account.username}: {str(e)}")
            
            success_message = f'Successfully assigned proxies to {success_count} accounts'
            if region_mismatch_count > 0:
                success_message += f' ({region_mismatch_count} accounts got different region proxies due to availability)'
            if success_count > 0:
                messages.success(request, success_message)
            if error_count > 0:
                messages.error(request, f'Failed to assign proxies to {error_count} accounts')
                
        elif action == 'remove_all':
            # Remove proxies from all selected accounts - clear both proxy and current_proxy fields
            success_count = 0
            error_count = 0
            
            for account in accounts:
                try:
                    old_proxy = account.proxy
                    account.proxy = None
                    account.current_proxy = None
                    account.save(update_fields=['proxy', 'current_proxy'])
                    
                    if old_proxy:
                        old_proxy.assigned_account = None
                        old_proxy.save(update_fields=['assigned_account'])
                    
                    success_count += 1
                    logger.info(f"[BULK CHANGE] Successfully removed proxy from account {account.username}")
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"[BULK CHANGE] Error removing proxy from account {account.username}: {str(e)}")
            
            if success_count > 0:
                messages.success(request, f'Successfully removed proxies from {success_count} accounts')
            if error_count > 0:
                messages.error(request, f'Failed to remove proxies from {error_count} accounts')
        
        return redirect('account_list')
    
    # GET request - show form
    accounts = InstagramAccount.objects.all().order_by('username')
    available_proxies_count = Proxy.objects.filter(
        assigned_account__isnull=True,
        is_active=True
    ).count()
    
    context = {
        'accounts': accounts,
        'available_proxies_count': available_proxies_count,
        'active_tab': 'accounts'
    }
    return render(request, 'uploader/bulk_change_proxy.html', context)

@login_required
def refresh_dolphin_proxies(request):
    """Refresh proxies in all Dolphin profiles to match current account proxy assignments"""
    if request.method == 'POST':
        # Get all accounts with Dolphin profiles and proxies
        accounts_with_profiles = InstagramAccount.objects.filter(
            dolphin_profile_id__isnull=False,
            proxy__isnull=False
        )
        
        if not accounts_with_profiles.exists():
            messages.warning(request, 'No accounts found with both Dolphin profiles and assigned proxies')
            return redirect('account_list')
        
        # Initialize Dolphin API
        api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
        if not api_key:
            messages.error(request, 'Dolphin API token not configured. Please set DOLPHIN_API_TOKEN environment variable.')
            return redirect('account_list')
        
        try:
            from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
            dolphin = DolphinAnty(api_key=api_key)
            
            if not dolphin.authenticate():
                messages.error(request, 'Failed to authenticate with Dolphin Anty API. Check your API token.')
                return redirect('account_list')
            
            success_count = 0
            error_count = 0
            
            for account in accounts_with_profiles:
                try:
                    proxy_data = account.proxy.to_dict()
                    result = dolphin.update_profile_proxy(account.dolphin_profile_id, proxy_data)
                    
                    if result.get("success"):
                        success_count += 1
                        logger.info(f"[REFRESH PROXIES] Successfully updated Dolphin profile {account.dolphin_profile_id} for account {account.username}")
                    else:
                        error_count += 1
                        error_msg = result.get("error", "Unknown error")
                        logger.error(f"[REFRESH PROXIES] Failed to update Dolphin profile {account.dolphin_profile_id} for account {account.username}: {error_msg}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"[REFRESH PROXIES] Error updating Dolphin profile for account {account.username}: {str(e)}")
            
            if success_count > 0:
                messages.success(request, f'Successfully updated {success_count} Dolphin profiles')
            if error_count > 0:
                messages.error(request, f'Failed to update {error_count} Dolphin profiles')
                
        except Exception as e:
            logger.error(f"[REFRESH PROXIES] Error initializing Dolphin API: {str(e)}")
            messages.error(request, f'Error connecting to Dolphin API: {str(e)}')
        
        return redirect('account_list')
    
    # GET request - show confirmation
    accounts_with_profiles = InstagramAccount.objects.filter(
        dolphin_profile_id__isnull=False,
        proxy__isnull=False
    ).order_by('username')
    
    context = {
        'accounts_with_profiles': accounts_with_profiles,
        'active_tab': 'accounts'
    }
    return render(request, 'uploader/refresh_dolphin_proxies.html', context)

@login_required
def cleanup_inactive_proxies(request):
    """Clean up inactive proxies with options to handle assigned accounts"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Get inactive proxies
        inactive_proxies = Proxy.objects.filter(
            Q(status='inactive') | Q(is_active=False)
        )
        
        if not inactive_proxies.exists():
            messages.info(request, 'No inactive proxies found to clean up')
            return redirect('proxy_list')
        
        # Get accounts that would be affected
        affected_accounts = InstagramAccount.objects.filter(
            proxy__in=inactive_proxies
        )
        
        if action == 'delete_only_unassigned':
            # Delete only unassigned inactive proxies
            unassigned_inactive = inactive_proxies.filter(assigned_account__isnull=True)
            deleted_count = unassigned_inactive.count()
            unassigned_inactive.delete()
            
            messages.success(request, f'Deleted {deleted_count} unassigned inactive proxies')
            if affected_accounts.exists():
                messages.warning(request, f'{affected_accounts.count()} accounts still have inactive proxies assigned')
        
        elif action == 'reassign_and_delete':
            # Try to reassign accounts to active proxies, then delete inactive ones
            # First, try to match regions when possible
            available_active_proxies = list(Proxy.objects.filter(
                status='active',
                is_active=True,
                assigned_account__isnull=True
            ).order_by('host', 'port'))
            
            reassigned_count = 0
            unassigned_count = 0
            region_mismatch_count = 0
            
            # Initialize Dolphin API for updating profiles
            api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
            dolphin = None
            if api_key:
                try:
                    from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
                    dolphin = DolphinAnty(api_key=api_key)
                    if not dolphin.authenticate():
                        dolphin = None
                        logger.warning("[CLEANUP] Failed to authenticate with Dolphin API")
                except Exception as e:
                    logger.error(f"[CLEANUP] Error initializing Dolphin API: {str(e)}")
                    dolphin = None
            
            for account in affected_accounts:
                if not available_active_proxies:
                    # No more active proxies available
                    account.proxy = None
                    account.current_proxy = None
                    account.save(update_fields=['proxy', 'current_proxy'])
                    unassigned_count += 1
                    logger.warning(f"[CLEANUP] No active proxy available for account {account.username}, removed proxy assignment")
                    continue
                
                old_proxy = account.proxy
                new_proxy = None
                
                # Try to find a proxy from the same region first
                if old_proxy and old_proxy.country:
                    same_region_proxies = [p for p in available_active_proxies if p.country == old_proxy.country]
                    if same_region_proxies:
                        new_proxy = same_region_proxies[0]
                        available_active_proxies.remove(new_proxy)
                        logger.info(f"[CLEANUP] Found same region proxy for {account.username}: {old_proxy.country}")
                    else:
                        # No same region proxy available, use any available proxy (force)
                        new_proxy = available_active_proxies.pop(0)
                        region_mismatch_count += 1
                        logger.warning(f"[CLEANUP] No same region proxy for {account.username}, using different region: {old_proxy.country} -> {new_proxy.country if new_proxy.country else 'Unknown'}")
                else:
                    # Account has no region info, just assign any available proxy
                    new_proxy = available_active_proxies.pop(0)
                
                if new_proxy:
                    try:
                        # Update account - update both proxy and current_proxy fields
                        account.proxy = new_proxy
                        account.current_proxy = new_proxy
                        account.save(update_fields=['proxy', 'current_proxy'])
                        
                        # Update proxy assignment
                        new_proxy.assigned_account = account
                        new_proxy.save(update_fields=['assigned_account'])
                        
                        # Update Dolphin profile if exists
                        if account.dolphin_profile_id and dolphin:
                            try:
                                proxy_data = new_proxy.to_dict()
                                result = dolphin.update_profile_proxy(account.dolphin_profile_id, proxy_data)
                                if not result.get("success"):
                                    logger.warning(f"[CLEANUP] Failed to update Dolphin profile {account.dolphin_profile_id}")
                            except Exception as e:
                                logger.error(f"[CLEANUP] Error updating Dolphin profile for {account.username}: {str(e)}")
                        
                        reassigned_count += 1
                        region_info = ""
                        if old_proxy and old_proxy.country and new_proxy.country:
                            if old_proxy.country != new_proxy.country:
                                region_info = f" (region changed: {old_proxy.country} -> {new_proxy.country})"
                            else:
                                region_info = f" (same region: {old_proxy.country})"
                        logger.info(f"[CLEANUP] Reassigned account {account.username} from {old_proxy} to {new_proxy}{region_info}")
                        
                    except Exception as e:
                        logger.error(f"[CLEANUP] Error reassigning proxy for account {account.username}: {str(e)}")
                        unassigned_count += 1
            
            # Now delete all inactive proxies
            deleted_count = inactive_proxies.count()
            inactive_proxies.delete()
            
            success_message = f'Cleanup completed: {deleted_count} inactive proxies deleted, {reassigned_count} accounts reassigned to active proxies'
            if region_mismatch_count > 0:
                success_message += f' ({region_mismatch_count} accounts got different region proxies due to availability)'
            messages.success(request, success_message)
            
            if unassigned_count > 0:
                messages.warning(request, f'{unassigned_count} accounts left without proxies (no active proxies available)')
        
        elif action == 'force_delete':
            # Force delete all inactive proxies, leaving accounts without proxies
            affected_count = affected_accounts.count()
            
            # Remove proxy assignments from accounts - clear both proxy and current_proxy fields
            affected_accounts.update(proxy=None, current_proxy=None)
            
            # Delete inactive proxies
            deleted_count = inactive_proxies.count()
            inactive_proxies.delete()
            
            messages.success(request, f'Force deleted {deleted_count} inactive proxies')
            if affected_count > 0:
                messages.warning(request, f'{affected_count} accounts are now without proxies and may need manual assignment')
        
        return redirect('proxy_list')
    
    # GET request - show cleanup options
    inactive_proxies = Proxy.objects.filter(
        Q(status='inactive') | Q(is_active=False)
    )
    
    # Get statistics
    total_inactive = inactive_proxies.count()
    unassigned_inactive = inactive_proxies.filter(assigned_account__isnull=True).count()
    assigned_inactive = inactive_proxies.filter(assigned_account__isnull=False).count()
    
    # Get affected accounts
    affected_accounts = InstagramAccount.objects.filter(
        proxy__in=inactive_proxies
    ).select_related('proxy')
    
    # Get available active proxies for reassignment
    available_active_proxies = Proxy.objects.filter(
        status='active',
        is_active=True,
        assigned_account__isnull=True
    ).count()
    
    context = {
        'total_inactive': total_inactive,
        'unassigned_inactive': unassigned_inactive,
        'assigned_inactive': assigned_inactive,
        'affected_accounts': affected_accounts,
        'available_active_proxies': available_active_proxies,
        'can_reassign_all': available_active_proxies >= assigned_inactive,
        'active_tab': 'proxies'
    }
    return render(request, 'uploader/cleanup_inactive_proxies.html', context)

def bulk_upload_logs(request, task_id):
    """Get bulk upload logs for a specific task"""
    try:
        task = get_object_or_404(BulkUploadTask, id=task_id)
        
        # Get logs from cache or file
        logs_key = f"bulk_upload_logs_{task_id}"
        logs = cache.get(logs_key, [])
        
        return JsonResponse({
            'logs': logs,
            'status': task.status,
            'completion_percentage': task.get_completion_percentage,
            'completed_count': task.get_completed_count,
            'total_count': task.get_total_count
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'logs': [],
            'status': 'ERROR'
        })


@csrf_exempt
@require_POST
def captcha_notification(request):
    """API endpoint for captcha notifications"""
    try:
        data = json.loads(request.body)
        bulk_upload_id = data.get('bulk_upload_id')
        message = data.get('message', 'CAPTCHA detected!')
        
        # Store captcha notification in cache
        cache_key = f"captcha_notification_{bulk_upload_id}"
        cache.set(cache_key, {
            'message': message,
            'timestamp': time.time(),
            'active': True
        }, timeout=300)  # 5 minutes timeout
        
        return JsonResponse({
            'status': 'success',
            'message': 'Captcha notification stored'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
def get_captcha_status(request, task_id):
    """Get captcha status for a bulk upload task"""
    try:
        cache_key = f"captcha_notification_{task_id}"
        notification = cache.get(cache_key)
        
        if notification and notification.get('active'):
            return JsonResponse({
                'captcha_detected': True,
                'message': notification.get('message'),
                'timestamp': notification.get('timestamp')
            })
        else:
            return JsonResponse({
                'captcha_detected': False
            })
            
    except Exception as e:
        return JsonResponse({
            'captcha_detected': False,
            'error': str(e)
        })


@csrf_exempt
@require_POST
def clear_captcha_notification(request, task_id):
    """Clear captcha notification for a bulk upload task (called after resolution/dismiss)."""
    try:
        cache_key = f"captcha_notification_{task_id}"
        cache.delete(cache_key)
        return JsonResponse({ 'status': 'cleared' })
    except Exception as e:
        return JsonResponse({ 'status': 'error', 'message': str(e) }, status=400)

