"""
Views for YouTube Shorts bulk upload functionality
Following SOLID, OOP, DRY, CLEAN, KISS principles
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.db.models import Sum, Value, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

from ..models import (
    YouTubeAccount,
    YouTubeShortsBulkUploadTask,
    YouTubeShortsBulkUploadAccount,
    YouTubeShortsVideo,
    YouTubeShortsVideoTitle,
    Proxy,
    DolphinCookieRobotTask
)
from ..yt_shorts_forms import (
    YouTubeShortsBulkUploadTaskForm,
    YouTubeShortsVideoUploadForm,
    YouTubeShortsVideoTitleForm,
    YouTubeShortsVideoEditForm,
    YouTubeShortsVideoBulkEditForm,
    YouTubeAccountImportForm,
    YouTubeAccountForm,
    YouTubeAccountBulkActionForm,
    YouTubeCookieRobotForm
)


# ===== Dashboard View =====
@login_required
def yt_shorts_dashboard(request):
    """Main YouTube Shorts dashboard with statistics and recent activity"""
    if not request.user.is_superuser:
        return redirect('cabinet_dashboard')
    
    # Get recent tasks
    recent_tasks = YouTubeShortsBulkUploadTask.objects.order_by('-created_at')[:10]
    
    # Get recent accounts
    recent_accounts = YouTubeAccount.objects.order_by('-last_used')[:10]
    
    # Get counts for dashboard stats
    tasks_count = YouTubeShortsBulkUploadTask.objects.count()
    accounts_count = YouTubeAccount.objects.count()
    videos_count = YouTubeShortsVideo.objects.count()
    completed_tasks_count = YouTubeShortsBulkUploadTask.objects.filter(status='COMPLETED').count()
    
    # Get account stats by status
    account_status_counts = {
        'active': YouTubeAccount.objects.filter(status='ACTIVE').count(),
        'blocked': YouTubeAccount.objects.filter(status='BLOCKED').count(),
        'limited': YouTubeAccount.objects.filter(status='LIMITED').count(),
        'inactive': YouTubeAccount.objects.filter(status='INACTIVE').count(),
    }
    
    # Get proxy stats for YouTube accounts
    accounts_with_proxy = YouTubeAccount.objects.filter(proxy__isnull=False).count()
    accounts_with_dolphin = YouTubeAccount.objects.filter(dolphin_profile_id__isnull=False, dolphin_profile_id__gt='').count()
    
    # Get task stats by status
    task_status_counts = {
        'pending': YouTubeShortsBulkUploadTask.objects.filter(status='PENDING').count(),
        'running': YouTubeShortsBulkUploadTask.objects.filter(status='RUNNING').count(),
        'completed': YouTubeShortsBulkUploadTask.objects.filter(status='COMPLETED').count(),
        'failed': YouTubeShortsBulkUploadTask.objects.filter(status='FAILED').count(),
    }
    
    # Get recent activity (last 24 hours)
    yesterday = timezone.now() - timedelta(days=1)
    recent_activity = {
        'tasks_24h': YouTubeShortsBulkUploadTask.objects.filter(created_at__gte=yesterday).count(),
        'videos_24h': YouTubeShortsVideo.objects.filter(uploaded_at__gte=yesterday).count(),
    }
    
    # Calculate total uploads
    total_uploads = YouTubeShortsBulkUploadAccount.objects.aggregate(
        total=Coalesce(Sum('uploaded_success_count'), Value(0))
    )['total']
    
    total_failed = YouTubeShortsBulkUploadAccount.objects.aggregate(
        total=Coalesce(Sum('uploaded_failed_count'), Value(0))
    )['total']
    
    # Annotate recent tasks with stats
    for task in recent_tasks:
        task.uploaded_success_total = task.accounts.aggregate(
            total=Coalesce(Sum('uploaded_success_count'), Value(0))
        )['total']
        task.uploaded_failed_total = task.accounts.aggregate(
            total=Coalesce(Sum('uploaded_failed_count'), Value(0))
        )['total']
    
    context = {
        'recent_tasks': recent_tasks,
        'recent_accounts': recent_accounts,
        'tasks_count': tasks_count,
        'accounts_count': accounts_count,
        'videos_count': videos_count,
        'completed_tasks_count': completed_tasks_count,
        'account_status_counts': account_status_counts,
        'task_status_counts': task_status_counts,
        'accounts_with_proxy': accounts_with_proxy,
        'accounts_with_dolphin': accounts_with_dolphin,
        'recent_activity': recent_activity,
        'total_uploads': total_uploads,
        'total_failed': total_failed,
        'active_tab': 'yt_shorts_dashboard'
    }
    return render(request, 'uploader/yt_shorts_dashboard.html', context)


# ===== Task Status Helper =====
class TaskStatus:
    """Task status constants following DRY principle"""
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    PARTIALLY_COMPLETED = 'PARTIALLY_COMPLETED'


def update_task_status(task, status, log_message=""):
    """Update task status and log - Single Responsibility Principle"""
    task.status = status
    if log_message:
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        task.log += f"[{timestamp}] {log_message}\n"
    task.save()


# ===== List View =====
@login_required
def yt_shorts_bulk_upload_list(request):
    """List all YouTube Shorts bulk upload tasks"""
    tasks = YouTubeShortsBulkUploadTask.objects.all().order_by('-created_at')
    
    # Annotate with aggregated stats
    for task in tasks:
        task.uploaded_success_total = task.accounts.aggregate(
            total=Coalesce(Sum('uploaded_success_count'), Value(0))
        )['total']
        task.uploaded_failed_total = task.accounts.aggregate(
            total=Coalesce(Sum('uploaded_failed_count'), Value(0))
        )['total']
    
    context = {
        'tasks': tasks,
        'active_tab': 'yt_shorts_bulk_upload'
    }
    return render(request, 'uploader/yt_bulk_upload/list.html', context)


# ===== Create View =====
@login_required
def create_yt_shorts_bulk_upload(request):
    """Create a new YouTube Shorts bulk upload task"""
    if request.method == 'POST':
        form = YouTubeShortsBulkUploadTaskForm(request.POST)
        if form.is_valid():
            # Create bulk upload task
            bulk_task = form.save()
            selected_accounts = form.cleaned_data['selected_accounts']
            
            # Create bulk upload accounts for each selected account
            for account in selected_accounts:
                # Use the proxy that's already assigned to the account
                proxy = account.proxy
                
                # Create bulk upload account
                YouTubeShortsBulkUploadAccount.objects.create(
                    bulk_task=bulk_task,
                    account=account,
                    proxy=proxy
                )
            
            messages.success(
                request,
                f'YouTube Shorts bulk upload task "{bulk_task.name}" created successfully with {len(selected_accounts)} accounts!'
            )
            return redirect('yt_shorts_add_bulk_videos', task_id=bulk_task.id)
    else:
        form = YouTubeShortsBulkUploadTaskForm()
    
    context = {
        'form': form,
        'active_tab': 'yt_shorts_bulk_upload'
    }
    return render(request, 'uploader/yt_bulk_upload/create.html', context)


# ===== Detail View =====
@login_required
def yt_shorts_bulk_upload_detail(request, task_id):
    """View details of a YouTube Shorts bulk upload task"""
    task = get_object_or_404(YouTubeShortsBulkUploadTask, id=task_id)
    accounts = task.accounts.all().select_related('account', 'proxy')
    videos = task.videos.all()
    titles = task.titles.all()
    
    # Calculate aggregated stats
    task.uploaded_success_total = accounts.aggregate(
        total=Coalesce(Sum('uploaded_success_count'), Value(0))
    )['total']
    task.uploaded_failed_total = accounts.aggregate(
        total=Coalesce(Sum('uploaded_failed_count'), Value(0))
    )['total']
    
    context = {
        'task': task,
        'accounts': accounts,
        'videos': videos,
        'titles': titles,
        'active_tab': 'yt_shorts_bulk_upload'
    }
    return render(request, 'uploader/yt_bulk_upload/detail.html', context)


# ===== Add Videos View =====
@login_required
def add_yt_shorts_bulk_videos(request, task_id):
    """Add videos to a YouTube Shorts bulk upload task"""
    task = get_object_or_404(YouTubeShortsBulkUploadTask, id=task_id)
    
    if request.method == 'POST':
        form = YouTubeShortsVideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video_files = request.FILES.getlist('videos')
            
            # Save each video
            for index, video_file in enumerate(video_files):
                YouTubeShortsVideo.objects.create(
                    bulk_task=task,
                    video_file=video_file,
                    order=index
                )
            
            messages.success(request, f'Successfully uploaded {len(video_files)} videos!')
            return redirect('yt_shorts_bulk_upload_detail', task_id=task.id)
    else:
        form = YouTubeShortsVideoUploadForm()
    
    context = {
        'form': form,
        'task': task,
        'active_tab': 'yt_shorts_bulk_upload'
    }
    return render(request, 'uploader/yt_bulk_upload/add_videos.html', context)


# ===== Add Titles View =====
@login_required
def add_yt_shorts_bulk_titles(request, task_id):
    """Add titles/descriptions to YouTube Shorts bulk upload task"""
    task = get_object_or_404(YouTubeShortsBulkUploadTask, id=task_id)
    
    if request.method == 'POST':
        form = YouTubeShortsVideoTitleForm(request.POST, request.FILES)
        if form.is_valid():
            titles_file = request.FILES['titles_file']
            content = titles_file.read().decode('utf-8')
            
            # Parse titles and descriptions
            # Format: Title on first line, description on following lines, blank line separator
            entries = content.strip().split('\n\n')
            
            for entry in entries:
                lines = entry.strip().split('\n')
                if not lines:
                    continue
                
                title = lines[0].strip()[:100]  # Max 100 chars for Shorts
                description = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""
                
                if title:
                    YouTubeShortsVideoTitle.objects.create(
                        bulk_task=task,
                        title=title,
                        description=description
                    )
            
            messages.success(request, f'Successfully imported {len(entries)} titles!')
            return redirect('yt_shorts_bulk_upload_detail', task_id=task.id)
    else:
        form = YouTubeShortsVideoTitleForm()
    
    context = {
        'form': form,
        'task': task,
        'active_tab': 'yt_shorts_bulk_upload'
    }
    return render(request, 'uploader/yt_bulk_upload/add_titles.html', context)


# ===== Delete Task View =====
@login_required
def delete_yt_shorts_bulk_upload(request, task_id):
    """Delete a YouTube Shorts bulk upload task"""
    task = get_object_or_404(YouTubeShortsBulkUploadTask, id=task_id)
    
    # Delete all associated video files
    for video in task.videos.all():
        if video.video_file:
            default_storage.delete(video.video_file.name)
    
    task.delete()
    messages.success(request, f'Task "{task.name}" deleted successfully!')
    return redirect('yt_shorts_bulk_upload_list')


# ===== Start Task View (Placeholder) =====
@login_required
def start_yt_shorts_bulk_upload(request, task_id):
    """Start a YouTube Shorts bulk upload task (placeholder for future implementation)"""
    task = get_object_or_404(YouTubeShortsBulkUploadTask, id=task_id)
    
    # Check if task is already running
    if task.status == TaskStatus.RUNNING:
        messages.warning(request, f'Task "{task.name}" is already running!')
        return redirect('yt_shorts_bulk_upload_detail', task_id=task.id)
    
    # Check if task has videos and accounts
    if not task.videos.exists():
        messages.error(request, 'No videos found for this task!')
        return redirect('yt_shorts_bulk_upload_detail', task_id=task.id)
    
    if not task.accounts.exists():
        messages.error(request, 'No accounts assigned to this task!')
        return redirect('yt_shorts_bulk_upload_detail', task_id=task.id)
    
    # TODO: Implement async upload logic here
    update_task_status(task, TaskStatus.RUNNING, "Task started (upload logic not implemented yet)")
    
    messages.info(request, f'Task "{task.name}" marked as running. Upload logic will be implemented later.')
    return redirect('yt_shorts_bulk_upload_detail', task_id=task.id)


# ===== Get Logs API =====
@login_required
def get_yt_shorts_bulk_task_logs(request, task_id):
    """Get logs for a YouTube Shorts bulk upload task as JSON with real-time updates"""
    task = get_object_or_404(YouTubeShortsBulkUploadTask, id=task_id)
    
    # Get specific account logs if account_id is provided
    account_id = request.GET.get('account_id')
    if account_id:
        try:
            account_task = task.accounts.get(id=account_id)
            return JsonResponse({
                'log': account_task.log,
                'status': account_task.status,
                'uploaded_success_count': account_task.uploaded_success_count,
                'uploaded_failed_count': account_task.uploaded_failed_count,
            })
        except YouTubeShortsBulkUploadAccount.DoesNotExist:
            return JsonResponse({'error': 'Account not found'}, status=404)
    
    # Return main task logs
    return JsonResponse({
        'log': task.log,
        'status': task.status,
        'completion_percentage': task.get_completion_percentage(),
        'completed_count': task.get_completed_count(),
        'total_count': task.get_total_count(),
    })


# ===== Edit Video Settings View =====
@login_required
def edit_yt_shorts_video_settings(request, video_id):
    """Edit individual video settings"""
    video = get_object_or_404(YouTubeShortsVideo, id=video_id)
    task = video.bulk_task
    
    if request.method == 'POST':
        form = YouTubeShortsVideoEditForm(request.POST, instance=video)
        if form.is_valid():
            form.save()
            messages.success(request, 'Video settings updated successfully!')
            return redirect('yt_shorts_bulk_upload_detail', task_id=task.id)
    else:
        form = YouTubeShortsVideoEditForm(instance=video)
    
    context = {
        'form': form,
        'video': video,
        'task': task,
        'active_tab': 'yt_shorts_bulk_upload'
    }
    return render(request, 'uploader/yt_bulk_upload/edit_video.html', context)


# ===== Bulk Edit Videos View =====
@login_required
def bulk_edit_yt_shorts_videos(request, task_id):
    """Bulk edit video settings for all videos in a task"""
    task = get_object_or_404(YouTubeShortsBulkUploadTask, id=task_id)
    
    if request.method == 'POST':
        form = YouTubeShortsVideoBulkEditForm(request.POST)
        if form.is_valid():
            videos = task.videos.all()
            updated_count = 0
            
            for video in videos:
                updated = False
                
                if form.cleaned_data.get('visibility'):
                    video.visibility = form.cleaned_data['visibility']
                    updated = True
                
                if form.cleaned_data.get('category'):
                    video.category = form.cleaned_data['category']
                    updated = True
                
                if form.cleaned_data.get('tags'):
                    video.tags = form.cleaned_data['tags']
                    updated = True
                
                if updated:
                    video.save()
                    updated_count += 1
            
            messages.success(request, f'Updated {updated_count} videos!')
            return redirect('yt_shorts_bulk_upload_detail', task_id=task.id)
    else:
        form = YouTubeShortsVideoBulkEditForm()
    
    context = {
        'form': form,
        'task': task,
        'active_tab': 'yt_shorts_bulk_upload'
    }
    return render(request, 'uploader/yt_bulk_upload/bulk_edit_videos.html', context)


# ===== YouTube Account Management Views =====

@login_required
def yt_accounts_list(request):
    """List all YouTube accounts with filtering and bulk actions"""
    if not request.user.is_superuser:
        return redirect('cabinet_dashboard')
    
    # Get filter parameters
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    client_filter = request.GET.get('client', '')
    
    # Build queryset
    accounts = YouTubeAccount.objects.all()
    
    # Apply filters
    if search_query:
        accounts = accounts.filter(
            Q(email__icontains=search_query) |
            Q(channel_name__icontains=search_query) |
            Q(channel_id__icontains=search_query)
        )
    
    if status_filter:
        accounts = accounts.filter(status=status_filter)
    
    if client_filter:
        if client_filter == 'no_client':
            accounts = accounts.filter(client__isnull=True)
        else:
            accounts = accounts.filter(client_id=client_filter)
    
    # Order by creation date
    accounts = accounts.order_by('-created_at')
    
    # Get statistics
    total_accounts = YouTubeAccount.objects.count()
    active_accounts = YouTubeAccount.objects.filter(status='ACTIVE').count()
    blocked_accounts = YouTubeAccount.objects.filter(status='BLOCKED').count()
    accounts_with_proxy = YouTubeAccount.objects.filter(proxy__isnull=False).count()
    
    context = {
        'accounts': accounts,
        'search_query': search_query,
        'status_filter': status_filter,
        'client_filter': client_filter,
        'total_accounts': total_accounts,
        'active_accounts': active_accounts,
        'blocked_accounts': blocked_accounts,
        'accounts_with_proxy': accounts_with_proxy,
        'active_tab': 'yt_accounts'
    }
    return render(request, 'uploader/yt_accounts/list.html', context)


@login_required
def yt_accounts_import(request):
    """Import YouTube accounts from text file with proxy assignment and Dolphin profile creation"""
    if not request.user.is_superuser:
        return redirect('cabinet_dashboard')
    
    if request.method == 'POST':
        form = YouTubeAccountImportForm(request.POST, request.FILES)
        if form.is_valid():
            parsed_accounts = form.parsed_accounts
            created_count = 0
            skipped_count = 0
            errors = []
            dolphin_created_count = 0
            
            # Get form data
            selected_client = form.cleaned_data.get('client')
            selected_locale = form.cleaned_data.get('locale', 'ru_BY')
            proxy_selection = form.cleaned_data.get('proxy_selection', 'locale_only')
            
            # Check Dolphin API availability
            dolphin_available = False
            dolphin = None
            try:
                import os
                from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
                
                api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
                if not api_key:
                    logger.error("[YT IMPORT] Dolphin API token not found in environment variables")
                    messages.error(request, "Dolphin API token not configured. Please set DOLPHIN_API_TOKEN environment variable.")
                    return redirect('yt_accounts_import')
                
                # Get Dolphin API host from environment (critical for Docker Windows deployment)
                dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
                if not dolphin_api_host.endswith("/v1.0"):
                    dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
                
                dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
                dolphin_available = dolphin.authenticate()
                
                if dolphin_available:
                    logger.info("[YT IMPORT] Dolphin Anty API authenticated successfully")
                else:
                    logger.warning("[YT IMPORT] Dolphin Anty API authentication failed")
                    messages.error(request, "Failed to authenticate with Dolphin Anty API. Check your API token.")
            except Exception as e:
                logger.error(f"[YT IMPORT] Dolphin Anty API error: {e}")
                messages.error(request, f"Dolphin Anty API error: {str(e)}")
            
            # Get available proxies based on selection mode
            base_qs = Proxy.objects.filter(
                is_active=True,
                assigned_account__isnull=True  # Not assigned to Instagram accounts
            ).exclude(
                # Exclude proxies that are already used by YouTube accounts
                id__in=YouTubeAccount.objects.filter(
                    proxy__isnull=False
                ).values_list('proxy_id', flat=True)
            )
            
            # Filter proxies by selection mode
            if proxy_selection == 'locale_only':
                # Filter by locale preference
                if selected_locale == 'ru_BY':
                    available_proxies = base_qs.filter(
                        Q(country__iexact='BY') | Q(country__icontains='Belarus') | Q(city__icontains='Belarus')
                    )
                elif selected_locale == 'en_IN':
                    available_proxies = base_qs.filter(
                        Q(country__iexact='IN') | Q(country__icontains='India') | Q(city__icontains='India')
                    )
                elif selected_locale == 'es_CL':
                    available_proxies = base_qs.filter(
                        Q(country__iexact='CL') | Q(country__icontains='Chile') | Q(city__icontains='Chile')
                    )
                elif selected_locale == 'es_MX':
                    available_proxies = base_qs.filter(
                        Q(country__iexact='MX') | Q(country__icontains='Mexico') | Q(city__icontains='Mexico')
                    )
                elif selected_locale == 'pt_BR':
                    available_proxies = base_qs.filter(
                        Q(country__iexact='BR') | Q(country__icontains='Brazil') | Q(city__icontains='Brazil')
                    )
                elif selected_locale == 'el_GR':
                    available_proxies = base_qs.filter(
                        Q(country__iexact='GR') | Q(country__icontains='Greece') | Q(city__icontains='Greece')
                    )
                elif selected_locale == 'de_DE':
                    available_proxies = base_qs.filter(
                        Q(country__iexact='DE') | Q(country__icontains='Germany') | Q(city__icontains='Germany')
                    )
                else:
                    available_proxies = base_qs
            else:
                # Use any available proxies
                available_proxies = base_qs
            
            available_proxies = available_proxies.order_by('?')
            
            # Log proxy selection info
            proxy_count = available_proxies.count()
            selection_mode = "locale-specific" if proxy_selection == 'locale_only' else "any available"
            logger.info(f"[YT IMPORT] Found {proxy_count} available proxies ({selection_mode}) for locale {selected_locale}")
            
            if not available_proxies.exists():
                if proxy_selection == 'locale_only':
                    messages.error(request, f'No available proxies found for locale {selected_locale}. Please add proxies for this locale or select "Any available proxies" option.')
                else:
                    messages.error(request, 'No available proxies found. Please add proxies before importing accounts.')
                return redirect('yt_accounts_list')
            
            proxy_list = list(available_proxies)
            proxy_index = 0
            
            for account_data in parsed_accounts:
                try:
                    # Check if account already exists
                    if YouTubeAccount.objects.filter(email=account_data['email']).exists():
                        skipped_count += 1
                        continue
                    
                    # Assign proxy
                    assigned_proxy = None
                    if proxy_index < len(proxy_list):
                        assigned_proxy = proxy_list[proxy_index]
                        proxy_index += 1
                    
                    # Create new account
                    account = YouTubeAccount.objects.create(
                        email=account_data['email'],
                        password=account_data['password'],
                        recovery_email=account_data['recovery_email'],
                        status='ACTIVE',
                        client=selected_client,
                        locale=selected_locale,
                        proxy=assigned_proxy,
                        current_proxy=assigned_proxy
                    )
                    
                    # Log proxy assignment (don't update assigned_account field as it's for Instagram only)
                    if assigned_proxy:
                        logger.info(f"[YT IMPORT] Assigned proxy {assigned_proxy} to YouTube account {account.email}")
                    
                    # Create Dolphin profile if API is available
                    if dolphin_available and assigned_proxy:
                        try:
                            import random
                            import string
                            import time
                            
                            # Add delay between profile creations
                            if dolphin_created_count > 0:
                                delay_time = random.uniform(2.0, 4.0)
                                logger.info(f"[YT IMPORT] Adding {delay_time:.1f}s delay before creating next profile")
                                time.sleep(delay_time)
                            
                            # Create profile name
                            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                            profile_name = f"youtube_{account.email.split('@')[0]}_{random_suffix}"
                            logger.info(f"[YT IMPORT] Creating Dolphin profile '{profile_name}' for account {account.email}")
                            
                            # Prepare proxy data
                            proxy_data = assigned_proxy.to_dict()
                            logger.info(f"[YT IMPORT] Using proxy for profile: {proxy_data.get('host')}:{proxy_data.get('port')}")
                            
                            # Create profile
                            response = dolphin.create_profile(
                                name=profile_name,
                                proxy=proxy_data,
                                tags=["youtube", "auto-created", "youtube-import"],
                                locale=selected_locale
                            )
                            
                            # Extract profile ID
                            profile_id = None
                            if response and isinstance(response, dict):
                                profile_id = response.get("browserProfileId")
                                if not profile_id and isinstance(response.get("data"), dict):
                                    profile_id = response["data"].get("id")
                            
                            if profile_id:
                                account.dolphin_profile_id = profile_id
                                account.save(update_fields=['dolphin_profile_id'])
                                dolphin_created_count += 1
                                logger.info(f"[YT IMPORT] Created Dolphin profile {profile_id} for account {account.email}")
                                
                                # Save Dolphin profile snapshot for 1:1 recreation
                                try:
                                    from uploader.services.dolphin_snapshot import save_dolphin_snapshot
                                    save_dolphin_snapshot(account, profile_id, response)
                                except Exception as snap_err:
                                    logger.warning(f"[YT IMPORT] Could not save Dolphin snapshot for {account.email}: {snap_err}")
                                
                                # Import cookies if available
                                if account_data.get('cookies'):
                                    try:
                                        dolphin.import_cookies_local(profile_id, account_data['cookies'])
                                        logger.info(f"[YT IMPORT] Imported {len(account_data['cookies'])} cookies into profile {profile_id}")
                                    except Exception as cookie_err:
                                        logger.warning(f"[YT IMPORT] Failed to import cookies for {account.email}: {cookie_err}")
                            else:
                                logger.warning(f"[YT IMPORT] Failed to extract profile ID from response for account {account.email}")
                                
                        except Exception as e:
                            logger.error(f"[YT IMPORT] Failed to create Dolphin profile for account {account.email}: {e}")
                    
                    # Save browser/device data if available
                    if account_data.get('user_agent') or account_data.get('cookies'):
                        try:
                            from uploader.models import YouTubeDevice, YouTubeCookies
                            
                            # Create or update device data
                            device_obj, _ = YouTubeDevice.objects.get_or_create(account=account)
                            if account_data.get('user_agent'):
                                device_obj.user_agent = account_data['user_agent']
                                device_obj.save(update_fields=['user_agent', 'updated_at'])
                                logger.info(f"[YT IMPORT] Saved User Agent for {account.email}")
                            
                            # Save cookies if available
                            if account_data.get('cookies'):
                                YouTubeCookies.objects.update_or_create(
                                    account=account,
                                    defaults={
                                        'cookies_data': account_data['cookies'],
                                        'is_valid': True
                                    }
                                )
                                logger.info(f"[YT IMPORT] Saved {len(account_data['cookies'])} cookies for {account.email}")
                                
                        except Exception as device_err:
                            logger.warning(f"[YT IMPORT] Failed to save device/cookies data for {account.email}: {device_err}")
                    
                    created_count += 1
                    
                except Exception as e:
                    logger.error(f"[YT IMPORT] Error processing account {account_data['email']}: {e}")
                    errors.append(f"Line {account_data['line']}: {str(e)}")
            
            # Show results
            if created_count > 0:
                messages.success(request, f'Successfully imported {created_count} YouTube accounts!')
            
            if dolphin_created_count > 0:
                messages.success(request, f'Created {dolphin_created_count} Dolphin profiles!')
            
            if skipped_count > 0:
                messages.warning(request, f'Skipped {skipped_count} accounts (already exist)')
            
            if errors:
                for error in errors:
                    messages.error(request, error)
            
            return redirect('yt_accounts_list')
    else:
        form = YouTubeAccountImportForm()
    
    context = {
        'form': form,
        'active_tab': 'yt_accounts'
    }
    return render(request, 'uploader/yt_accounts/import.html', context)


@login_required
def yt_account_detail(request, account_id):
    """View details of a specific YouTube account"""
    if not request.user.is_superuser:
        return redirect('cabinet_dashboard')
    
    account = get_object_or_404(YouTubeAccount, id=account_id)
    
    # Get recent bulk uploads for this account
    recent_uploads = account.bulk_uploads.all().order_by('-bulk_task__created_at')[:10]
    
    # Calculate total uploads
    total_success = account.bulk_uploads.aggregate(
        total=Coalesce(Sum('uploaded_success_count'), Value(0))
    )['total']
    
    total_failed = account.bulk_uploads.aggregate(
        total=Coalesce(Sum('uploaded_failed_count'), Value(0))
    )['total']
    
    context = {
        'account': account,
        'recent_uploads': recent_uploads,
        'total_success': total_success,
        'total_failed': total_failed,
        'active_tab': 'yt_accounts'
    }
    return render(request, 'uploader/yt_accounts/detail.html', context)


@login_required
def yt_account_create(request):
    """Create a new YouTube account"""
    if not request.user.is_superuser:
        return redirect('cabinet_dashboard')
    
    if request.method == 'POST':
        form = YouTubeAccountForm(request.POST)
        if form.is_valid():
            account = form.save()
            messages.success(request, f'YouTube account "{account.email}" created successfully!')
            return redirect('yt_account_detail', account_id=account.id)
    else:
        form = YouTubeAccountForm()
    
    context = {
        'form': form,
        'active_tab': 'yt_accounts'
    }
    return render(request, 'uploader/yt_accounts/create.html', context)


@login_required
def yt_account_edit(request, account_id):
    """Edit a YouTube account"""
    if not request.user.is_superuser:
        return redirect('cabinet_dashboard')
    
    account = get_object_or_404(YouTubeAccount, id=account_id)
    
    if request.method == 'POST':
        form = YouTubeAccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, f'YouTube account "{account.email}" updated successfully!')
            return redirect('yt_account_detail', account_id=account.id)
    else:
        form = YouTubeAccountForm(instance=account)
    
    context = {
        'form': form,
        'account': account,
        'active_tab': 'yt_accounts'
    }
    return render(request, 'uploader/yt_accounts/edit.html', context)


@login_required
def yt_account_delete(request, account_id):
    """Delete a YouTube account"""
    if not request.user.is_superuser:
        return redirect('cabinet_dashboard')
    
    account = get_object_or_404(YouTubeAccount, id=account_id)
    email = account.email
    
    account.delete()
    messages.success(request, f'YouTube account "{email}" deleted successfully!')
    return redirect('yt_accounts_list')


@login_required
def create_yt_dolphin_profile(request, account_id):
    """Create a Dolphin profile for an existing YouTube account"""
    account = get_object_or_404(YouTubeAccount, id=account_id)
    
    # Check if account already has a Dolphin profile
    if account.dolphin_profile_id:
        messages.warning(request, f'YouTube account {account.email} already has a Dolphin profile: {account.dolphin_profile_id}')
        return redirect('yt_account_detail', account_id=account.id)
    
    # Check if account has a proxy
    if not account.proxy:
        messages.error(request, f'YouTube account {account.email} needs a proxy before creating a Dolphin profile. Please assign a proxy first.')
        return redirect('yt_account_edit', account_id=account.id)
    
    # Read UI params
    proxy_selection = request.POST.get('proxy_selection', 'locale_only') if request.method == 'POST' else 'locale_only'
    selected_locale = request.POST.get('profile_locale', 'ru_BY') if request.method == 'POST' else 'ru_BY'
    if selected_locale not in ['ru_BY', 'en_IN', 'es_CL', 'es_MX', 'pt_BR', 'el_GR', 'de_DE']:
        selected_locale = 'ru_BY'
    
    try:
        logger.info(f"[CREATE YT PROFILE] Creating Dolphin profile for YouTube account {account.email}")
        
        # Initialize Dolphin API
        import os
        api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
        if not api_key:
            logger.error("[CREATE YT PROFILE] Dolphin API token not found in environment variables")
            messages.error(request, "Dolphin API token not configured. Please set DOLPHIN_API_TOKEN environment variable.")
            return redirect('yt_account_detail', account_id=account.id)
        
        # Get Dolphin API host from environment (critical for Docker Windows deployment)
        dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
        if not dolphin_api_host.endswith("/v1.0"):
            dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
        
        from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
        dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
        
        # Authenticate with Dolphin
        if not dolphin.authenticate():
            logger.error("[CREATE YT PROFILE] Failed to authenticate with Dolphin Anty API")
            messages.error(request, "Failed to authenticate with Dolphin Anty API. Check your API token.")
            return redirect('yt_account_detail', account_id=account.id)
        
        # Optionally reassign proxy to locale-only BY
        if request.method == 'POST' and proxy_selection == 'locale_only':
            proxy_country = (account.proxy.country or '').strip() if account.proxy else ''
            is_by = proxy_country.upper() == 'BY' or 'belarus' in proxy_country.lower()
            if not is_by:
                available_proxies = Proxy.objects.filter(is_active=True, assigned_account__isnull=True)
                by_proxies = available_proxies.filter(
                    Q(country__iexact='BY') | Q(country__icontains='Belarus') | Q(city__icontains='Belarus')
                )
                if by_proxies.exists():
                    new_proxy = by_proxies.order_by('?').first()
                    # Assign
                    account.proxy = new_proxy
                    account.current_proxy = new_proxy
                    account.save(update_fields=['proxy', 'current_proxy'])
                    logger.info(f"[CREATE YT PROFILE] Reassigned proxy to BY-only {new_proxy} for account {account.email}")
                else:
                    messages.warning(request, 'No available BY proxies found; using current proxy.')
        
        # Create profile name
        import random
        import string
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        profile_name = f"youtube_{account.email.split('@')[0]}_{random_suffix}"
        logger.info(f"[CREATE YT PROFILE] Creating Dolphin profile '{profile_name}'")
        
        # Get proxy data
        proxy_data = account.proxy.to_dict()
        logger.info(f"[CREATE YT PROFILE] Using proxy: {proxy_data.get('host')}:{proxy_data.get('port')}")
        
        # Create Dolphin profile
        response = dolphin.create_profile(
            name=profile_name,
            proxy=proxy_data,
            tags=["youtube", "manual-created"],
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
            logger.info(f"[CREATE YT PROFILE] Successfully created Dolphin profile {profile_id} for account {account.email}")
            
            # Save Dolphin profile snapshot for 1:1 recreation
            try:
                from uploader.services.dolphin_snapshot import save_dolphin_snapshot
                save_dolphin_snapshot(account, profile_id, response)
            except Exception as snap_err:
                logger.warning(f"[CREATE YT PROFILE] Could not save Dolphin snapshot for {account.email}: {snap_err}")
            
            messages.success(request, f'Successfully created Dolphin profile {profile_id} for YouTube account {account.email}!')
        else:
            logger.error(f"[CREATE YT PROFILE] Failed to extract profile ID from response: {response}")
            messages.error(request, f'Failed to create Dolphin profile. Response: {response}')
        
    except Exception as e:
        logger.error(f"[CREATE YT PROFILE] Error creating Dolphin profile for account {account.email}: {str(e)}")
        messages.error(request, f'Error creating Dolphin profile: {str(e)}')
    
    return redirect('yt_account_detail', account_id=account.id)


@login_required
def change_yt_account_proxy(request, account_id):
    """Change proxy for a YouTube account via AJAX"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    account = get_object_or_404(YouTubeAccount, id=account_id)
    
    if request.method == 'POST':
        proxy_id = request.POST.get('proxy_id')
        
        try:
            if proxy_id:
                # Assign the selected proxy
                new_proxy = get_object_or_404(Proxy, id=proxy_id)
                
                # Update the current account's proxy
                old_proxy = account.proxy
                account.proxy = new_proxy
                account.current_proxy = new_proxy
                account.save(update_fields=['proxy', 'current_proxy'])
                
                # Update Dolphin profile proxy if profile exists
                if account.dolphin_profile_id:
                    try:
                        import os
                        from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
                        
                        api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
                        if api_key:
                            # Get Dolphin API host from environment
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
                                    logger.info(f"[CHANGE YT PROXY] Successfully updated Dolphin profile {account.dolphin_profile_id} proxy")
                                    return JsonResponse({
                                        'success': True, 
                                        'message': f'Proxy changed for account {account.email} and Dolphin profile updated successfully!'
                                    })
                                else:
                                    error_msg = result.get("error", "Unknown error")
                                    logger.error(f"[CHANGE YT PROXY] Failed to update Dolphin profile proxy: {error_msg}")
                                    return JsonResponse({
                                        'success': True, 
                                        'message': f'Proxy changed for account {account.email}, but failed to update Dolphin profile: {error_msg}'
                                    })
                            else:
                                logger.error("[CHANGE YT PROXY] Failed to authenticate with Dolphin Anty API")
                                return JsonResponse({
                                    'success': True, 
                                    'message': f'Proxy changed for account {account.email}, but could not authenticate with Dolphin Anty API.'
                                })
                    except Exception as e:
                        logger.error(f"[CHANGE YT PROXY] Error updating Dolphin profile: {str(e)}")
                        return JsonResponse({
                            'success': True, 
                            'message': f'Proxy changed for account {account.email}, but could not update Dolphin profile: {str(e)}'
                        })
                else:
                    return JsonResponse({
                        'success': True, 
                        'message': f'Proxy changed for account {account.email}!'
                    })
            else:
                # Remove proxy assignment
                account.proxy = None
                account.current_proxy = None
                account.save(update_fields=['proxy', 'current_proxy'])
                return JsonResponse({
                    'success': True, 
                    'message': f'Proxy removed from account {account.email}!'
                })
                
        except Exception as e:
            logger.error(f"[CHANGE YT PROXY] Error changing proxy for account {account.email}: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def get_available_proxies_for_yt_account(request, account_id):
    """Get available proxies for a YouTube account via AJAX"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    account = get_object_or_404(YouTubeAccount, id=account_id)
    
    # Get available proxies (not assigned to other YouTube accounts)
    available_proxies = Proxy.objects.filter(
        is_active=True
    ).exclude(
        id__in=YouTubeAccount.objects.filter(
            proxy__isnull=False
        ).exclude(id=account.id).values_list('proxy_id', flat=True)
    ).order_by('host', 'port')
    
    proxies_data = []
    for proxy in available_proxies:
        proxies_data.append({
            'id': proxy.id,
            'host': proxy.host,
            'port': proxy.port,
            'country': proxy.country,
            'city': proxy.city,
            'proxy_type': proxy.proxy_type,
            'is_active': proxy.is_active
        })
    
    return JsonResponse({
        'success': True,
        'proxies': proxies_data
    })


@login_required
def yt_accounts_bulk_action(request):
    """Perform bulk actions on selected YouTube accounts"""
    if not request.user.is_superuser:
        return redirect('cabinet_dashboard')
    
    if request.method == 'POST':
        form = YouTubeAccountBulkActionForm(request.POST)
        if form.is_valid():
            account_ids = request.POST.getlist('account_ids')
            action = form.cleaned_data['action']
            
            if not account_ids:
                messages.error(request, 'No accounts selected!')
                return redirect('yt_accounts_list')
            
            accounts = YouTubeAccount.objects.filter(id__in=account_ids)
            updated_count = 0
            
            if action == 'change_status':
                new_status = form.cleaned_data['new_status']
                if new_status:
                    accounts.update(status=new_status)
                    updated_count = len(accounts)
                    messages.success(request, f'Updated status for {updated_count} accounts!')
            
            elif action == 'assign_proxy':
                new_proxy = form.cleaned_data['new_proxy']
                if new_proxy:
                    accounts.update(proxy=new_proxy, current_proxy=new_proxy)
                    updated_count = len(accounts)
                    messages.success(request, f'Assigned proxy to {updated_count} accounts!')
            
            elif action == 'change_locale':
                new_locale = form.cleaned_data['new_locale']
                if new_locale:
                    accounts.update(locale=new_locale)
                    updated_count = len(accounts)
                    messages.success(request, f'Updated locale for {updated_count} accounts!')
            
            elif action == 'delete':
                count = len(accounts)
                accounts.delete()
                messages.success(request, f'Deleted {count} accounts!')
            
            return redirect('yt_accounts_list')
    else:
        form = YouTubeAccountBulkActionForm()
    
    context = {
        'form': form,
        'active_tab': 'yt_accounts'
    }
    return render(request, 'uploader/yt_accounts/bulk_action.html', context)


# ===== YouTube Cookie Robot Functions =====

@login_required
def yt_cookie_robot_create(request):
    """Create a new YouTube Cookie Robot task"""
    if not request.user.is_superuser:
        return redirect('cabinet_dashboard')
    
    if request.method == 'POST':
        form = YouTubeCookieRobotForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data['account']
            urls = form.cleaned_data['urls']
            headless = form.cleaned_data['headless']
            imageless = form.cleaned_data['imageless']
            
            # Create Cookie Robot task
            task = DolphinCookieRobotTask.objects.create(
                youtube_account=account,
                urls=urls,
                headless=headless,
                imageless=imageless,
                status='PENDING'
            )
            
            # Start the task in background
            try:
                from uploader.tasks_playwright import run_cookie_robot_task
                import threading
                
                # Run in background thread
                thread = threading.Thread(target=run_cookie_robot_task, args=(task.id,))
                thread.daemon = True
                thread.start()
                
                messages.success(request, f'Cookie Robot task created for {account.email}! Task ID: {task.id}')
            except Exception as e:
                logger.error(f"[YT COOKIE ROBOT] Failed to start task: {e}")
                messages.error(request, f'Failed to start Cookie Robot task: {str(e)}')
            
            return redirect('yt_cookie_robot_list')
    else:
        form = YouTubeCookieRobotForm()
    
    context = {
        'form': form,
        'active_tab': 'yt_cookie_robot'
    }
    return render(request, 'uploader/yt_cookie_robot/create.html', context)


@login_required
def yt_cookie_robot_list(request):
    """List all YouTube Cookie Robot tasks"""
    if not request.user.is_superuser:
        return redirect('cabinet_dashboard')
    
    # Get YouTube Cookie Robot tasks
    tasks = DolphinCookieRobotTask.objects.filter(
        youtube_account__isnull=False
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(tasks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'active_tab': 'yt_cookie_robot'
    }
    return render(request, 'uploader/yt_cookie_robot/list.html', context)


@login_required
def yt_cookie_robot_detail(request, task_id):
    """View details of a YouTube Cookie Robot task"""
    if not request.user.is_superuser:
        return redirect('cabinet_dashboard')
    
    task = get_object_or_404(DolphinCookieRobotTask, id=task_id, youtube_account__isnull=False)
    
    context = {
        'task': task,
        'active_tab': 'yt_cookie_robot'
    }
    return render(request, 'uploader/yt_cookie_robot/detail.html', context)


@login_required
def yt_cookie_robot_delete(request, task_id):
    """Delete a YouTube Cookie Robot task"""
    if not request.user.is_superuser:
        return redirect('cabinet_dashboard')
    
    task = get_object_or_404(DolphinCookieRobotTask, id=task_id, youtube_account__isnull=False)
    
    if request.method == 'POST':
        account_email = task.youtube_account.email
        task.delete()
        messages.success(request, f'Cookie Robot task for {account_email} deleted successfully!')
        return redirect('yt_cookie_robot_list')
    
    context = {
        'task': task,
        'active_tab': 'yt_cookie_robot'
    }
    return render(request, 'uploader/yt_cookie_robot/delete.html', context)

