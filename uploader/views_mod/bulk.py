"""Views module: bulk (split from monolith)."""
from .common import *
from django.db.utils import OperationalError
from django.db import close_old_connections


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
    """Assign videos to accounts with proper distribution"""
    videos = list(task.videos.all())
    accounts = list(task.accounts.all())
    
    if not videos or not accounts:
        return
        
    # ИСПРАВЛЕНИЕ: Правильное распределение видео между аккаунтами
    if len(videos) < len(accounts):
        # РЕЖИМ ПОВТОРЕНИЯ: видео меньше чем аккаунтов
        for i, account in enumerate(accounts):
            video_index = i % len(videos)  # Циклическое распределение
            video = videos[video_index]
            video.assigned_to = account
            video.save(update_fields=['assigned_to'])
    else:
        # РЕЖИМ УНИКАЛЬНОГО РАСПРЕДЕЛЕНИЯ: видео больше или равно аккаунтам
        videos_per_account = len(videos) // len(accounts)
        remainder = len(videos) % len(accounts)
        
        video_index = 0
        for account_index, account in enumerate(accounts):
            # Определяем количество видео для этого аккаунта
            account_video_count = videos_per_account + (1 if account_index < remainder else 0)
            
            # Назначаем видео этому аккаунту
            for _ in range(account_video_count):
                if video_index < len(videos):
                    videos[video_index].assigned_to = account
                    videos[video_index].save(update_fields=['assigned_to'])
                    video_index += 1


def all_videos_assigned(task):
    """Check if all videos in a task have been assigned to accounts"""
    videos = task.videos.all()
    return all(video.assigned_to is not None for video in videos)


def all_titles_assigned(task):
    """Check if all videos in a task have titles assigned"""
    videos = task.videos.all()
    return all(hasattr(video, 'title_data') and video.title_data is not None for video in videos)


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
        from uploader.async_bulk_tasks import run_async_bulk_upload_task_sync
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


def start_bulk_upload_api(request, task_id):
    """Start a bulk upload task using instagrapi runner (API-based)."""
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
    
    # Mark engine for this run
    try:
        cache.set(f"bulk_engine_{task.id}", "instagrapi", timeout=3600)
    except Exception:
        pass
    
    # Read feature toggles from query and store to cache (API mode only)
    try:
        rounds = request.GET.get('rounds') == '1'
        init_delay = request.GET.get('init_delay') == '1'
        cache.set(f"bulk_rounds_{task.id}", bool(rounds), timeout=3600)
        cache.set(f"bulk_init_delay_{task.id}", bool(init_delay), timeout=3600)
    except Exception:
        pass
    
    # Initialize WebLogger for this task so background logs are visible immediately
    try:
        from uploader.bulk_tasks_playwright import init_web_logger
        init_web_logger(task.id)
    except Exception:
        pass
    
    # Use async mode - same as default starter
    update_task_status(task, TaskStatus.RUNNING, "Task started in ASYNC mode (API)")
    print(f"[TASK] Changing task {task.id}: {task.name} status to RUNNING [API]")
    
    # Assign videos to accounts if not already done
    if not all_videos_assigned(task):
        assign_videos_to_accounts(task)
        print(f"[TASK] Assigning videos to accounts for task {task.id}: {task.name}")
    
    try:
        from uploader.async_bulk_tasks import run_async_bulk_upload_task_sync
        import threading
        print(f"[TASK] Starting async API task in background for task {task.id}: {task.name}")
        
        def run_async_task():
            try:
                result = run_async_bulk_upload_task_sync(task_id)
                print(f"[TASK] Async API task completed for task {task_id}: {result}")
                # Do not overwrite final status; append a finishing log entry only
                try:
                    from django.utils import timezone
                    ts = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                    msg = f"[{ts}] [FINISH] Async API task {'completed successfully' if result else 'finished with errors'}\n"
                except Exception:
                    msg = "[FINISH] Async API task finished\n"
                try:
                    # Append log without touching status
                    from uploader.task_utils import update_task_log as _utl
                    _utl(task, msg)
                except Exception:
                    pass
            except Exception as e:
                print(f"[TASK] Async API task failed for task {task_id}: {str(e)}")
                update_task_status(task, TaskStatus.FAILED, f"Async API task failed: {str(e)}")
        
        thread = threading.Thread(target=run_async_task, daemon=True)
        thread.start()
        
        messages.success(request, f'Async API bulk upload task "{task.name}" started successfully! You can monitor progress on this page.')
        return redirect('bulk_upload_detail', task_id=task.id)
        
    except Exception as e:
        print(f"[TASK] Failed to start async API task for task {task_id}: {str(e)}")
        messages.error(request, f'Failed to start async API task: {str(e)}')
        update_task_status(task, TaskStatus.FAILED, f"Failed to start async API task: {str(e)}")
        return redirect('bulk_upload_detail', task_id=task.id)


def get_bulk_task_logs(request, task_id):
    """Get logs for a bulk upload task as JSON with real-time updates"""
    from django.core.cache import cache
    import json
    
    # Try to get task with a one-time retry on OperationalError (DB connection dropped)
    try:
        task = get_object_or_404(BulkUploadTask, id=task_id)
    except OperationalError:
        # Reset stale DB connections and retry once
        try:
            close_old_connections()
        except Exception:
            pass
        try:
            task = get_object_or_404(BulkUploadTask, id=task_id)
        except OperationalError:
            # Fallback to cache-only response to avoid 500 for the UI poller
            account_id = request.GET.get('account_id')
            cache_key = f"task_logs_{task_id}"
            if account_id:
                cache_key += f"_account_{account_id}"
            cached_logs = cache.get(cache_key, [])
            formatted_logs = []
            for log_entry in cached_logs:
                if isinstance(log_entry, dict):
                    formatted_logs.append({
                        'timestamp': log_entry.get('timestamp', ''),
                        'level': log_entry.get('level', 'INFO'),
                        'message': log_entry.get('message', ''),
                        'category': log_entry.get('category', 'GENERAL')
                    })
                else:
                    formatted_logs.append({
                        'timestamp': '',
                        'level': 'INFO',
                        'message': str(log_entry),
                        'category': 'LEGACY'
                    })
            response_data = {
                'status': cache.get(f"task_status_{task_id}", 'RUNNING'),
                'logs': formatted_logs,
                'completion_percentage': cache.get(f"task_completion_{task_id}", 0),
                'completed_count': cache.get(f"task_completed_{task_id}", 0),
                'total_count': cache.get(f"task_total_{task_id}", 0),
                'last_update': cache.get(f"task_last_update_{task_id}", ''),
            }
            return JsonResponse(response_data)
    
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
