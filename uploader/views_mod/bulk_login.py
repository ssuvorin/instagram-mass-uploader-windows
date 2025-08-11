from .common import *
from ..models import BulkLoginTask, BulkLoginAccount, InstagramAccount, Proxy
from ..forms import BulkLoginTaskForm
from ..constants import TaskStatus

@login_required
def bulk_login_list(request):
    tasks = BulkLoginTask.objects.order_by('-created_at').annotate(
        completed_accounts_count=Coalesce(Sum(Case(
            When(accounts__status='COMPLETED', then=1),
            default=0,
            output_field=IntegerField()
        )), Value(0))
    )
    context = {
        'tasks': tasks,
        'active_tab': 'bulk_login'
    }
    return render(request, 'uploader/bulk_login/list.html', context)

@login_required
def create_bulk_login(request):
    if request.method == 'POST':
        form = BulkLoginTaskForm(request.POST)
        if form.is_valid():
            bulk_task = form.save()
            selected_accounts = form.cleaned_data['selected_accounts']
            for account in selected_accounts:
                proxy = account.proxy
                BulkLoginAccount.objects.create(
                    bulk_task=bulk_task,
                    account=account,
                    proxy=proxy
                )
            messages.success(request, f'Bulk login task "{bulk_task.name}" created with {len(selected_accounts)} accounts!')
            return redirect('bulk_login_detail', task_id=bulk_task.id)
    else:
        form = BulkLoginTaskForm()
    context = {
        'form': form,
        'active_tab': 'bulk_login'
    }
    return render(request, 'uploader/bulk_login/create.html', context)

@login_required
def bulk_login_detail(request, task_id):
    task = get_object_or_404(BulkLoginTask, id=task_id)
    accounts = task.accounts.all().select_related('account', 'proxy')
    context = {
        'task': task,
        'accounts': accounts,
        'active_tab': 'bulk_login'
    }
    return render(request, 'uploader/bulk_login/detail.html', context)

@login_required
def start_bulk_login(request, task_id):
    task = get_object_or_404(BulkLoginTask, id=task_id)
    if task.status == TaskStatus.RUNNING:
        messages.warning(request, f'Task "{task.name}" is already running!')
        return redirect('bulk_login_detail', task_id=task.id)
    if not task.accounts.exists():
        messages.error(request, 'No accounts assigned to this task!')
        return redirect('bulk_login_detail', task_id=task.id)

    update_task_status(task, TaskStatus.RUNNING, "Task started in ASYNC mode")

    try:
        from .bulk_login_runner import run_async_bulk_login_task_sync
        import threading
        def run_async_task():
            try:
                result = run_async_bulk_login_task_sync(task_id)
                if result:
                    update_task_status(task, task.status, "Async login task finished (status preserved)")
                else:
                    update_task_status(task, task.status, "Async login task finished with errors (status preserved)")
            except Exception as e:
                update_task_status(task, TaskStatus.FAILED, f"Async login task failed: {str(e)}")
        thread = threading.Thread(target=run_async_task, daemon=True)
        thread.start()
        messages.success(request, f'Async bulk login task "{task.name}" started. Monitor progress below.')
        return redirect('bulk_login_detail', task_id=task.id)
    except Exception as e:
        messages.error(request, f'Failed to start async task: {str(e)}')
        update_task_status(task, TaskStatus.FAILED, f"Failed to start async task: {str(e)}")
        return redirect('bulk_login_detail', task_id=task.id)

@login_required
def get_bulk_login_logs(request, task_id):
    from django.core.cache import cache
    task = get_object_or_404(BulkLoginTask, id=task_id)
    account_id = request.GET.get('account_id')
    cache_key = f"bulk_login_logs_{task_id}"
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
            formatted_logs.append({'timestamp': '', 'level': 'INFO', 'message': str(log_entry), 'category': 'LEGACY'})

    total_accounts = task.accounts.count()
    completed_accounts = task.accounts.filter(status='COMPLETED').count()
    completion_percentage = int((completed_accounts / total_accounts * 100)) if total_accounts > 0 else 0

    response_data = {
        'status': task.status,
        'logs': formatted_logs,
        'completion_percentage': completion_percentage,
        'completed_count': completed_accounts,
        'total_count': total_accounts,
        'last_update': cache.get(f"bulk_login_last_update_{task_id}", ''),
    }
    if account_id:
        try:
            account_task = task.accounts.get(id=account_id)
            response_data['account_status'] = account_task.status
            response_data['account_username'] = account_task.account.username if account_task.account else f"Account {account_id}"
        except:
            pass
    return JsonResponse(response_data)

@login_required
def delete_bulk_login(request, task_id):
    try:
        task = get_object_or_404(BulkLoginTask, id=task_id)
        if task.status == 'RUNNING' and request.GET.get('force') != '1':
            force_url = reverse('delete_bulk_login', args=[task_id]) + '?force=1'
            messages.warning(request, f'Task "{task.name}" is currently running. <a href="{force_url}" class="btn btn-sm btn-danger ms-3">Force Delete</a>', extra_tags='safe')
            return redirect('bulk_login_detail', task_id=task.id)
        task.accounts.all().delete()
        task.delete()
        messages.success(request, f'Bulk login task "{task.name}" deleted successfully')
    except Exception as e:
        messages.error(request, f"Error deleting task: {str(e)}")
    return redirect('bulk_login_list') 