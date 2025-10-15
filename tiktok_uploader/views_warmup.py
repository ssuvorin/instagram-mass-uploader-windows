"""
Warmup Views for TikTok Uploader
==================================

Представления для прогрева TikTok аккаунтов.
Прогрев имитирует активность реального пользователя для повышения доверия TikTok.
"""

import threading
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q

from .models import WarmupTask, WarmupTaskAccount, TikTokAccount
from .forms import WarmupTaskForm

logger = logging.getLogger('tiktok_uploader')


# ============================================================================
# ЗАДАЧИ ПРОГРЕВА
# ============================================================================

@login_required
def warmup_task_list(request):
    """
    Список всех задач прогрева аккаунтов.
    """
    # Получаем параметры фильтрации
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    # Базовый queryset
    tasks = WarmupTask.objects.all().order_by('-created_at')
    
    # Применяем фильтры
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    if search_query:
        tasks = tasks.filter(name__icontains=search_query)
    
    # Добавляем аннотацию с количеством аккаунтов
    tasks = tasks.annotate(
        total_accounts=Count('accounts'),
        completed_accounts=Count('accounts', filter=Q(accounts__status='COMPLETED')),
        running_accounts=Count('accounts', filter=Q(accounts__status='RUNNING')),
        failed_accounts=Count('accounts', filter=Q(accounts__status='FAILED'))
    )
    
    # Статистика по статусам
    pending_count = WarmupTask.objects.filter(status='PENDING').count()
    running_count = WarmupTask.objects.filter(status='RUNNING').count()
    completed_count = WarmupTask.objects.filter(status='COMPLETED').count()
    failed_count = WarmupTask.objects.filter(status='FAILED').count()
    
    context = {
        'tasks': tasks,
        'pending_count': pending_count,
        'running_count': running_count,
        'completed_count': completed_count,
        'failed_count': failed_count,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'tiktok_uploader/warmup/list.html', context)


@login_required
def warmup_task_create(request):
    """
    Создание новой задачи прогрева аккаунтов.
    """
    if request.method == 'POST':
        form = WarmupTaskForm(request.POST)
        
        if form.is_valid():
            # Сохраняем задачу
            task = form.save(commit=False)
            
            # Генерируем имя если не указано
            if not task.name or task.name == "Warmup Task":
                task.name = f"Warmup {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            
            task.status = 'PENDING'
            task.save()
            
            # Получаем выбранные аккаунты
            selected_accounts = form.cleaned_data['selected_accounts']
            
            # Создаем WarmupTaskAccount для каждого выбранного аккаунта
            for account in selected_accounts:
                WarmupTaskAccount.objects.create(
                    task=task,
                    account=account,
                    proxy=account.proxy or account.current_proxy,  # Используем назначенный прокси
                    status='PENDING'
                )
            
            messages.success(
                request,
                f'Warmup task "{task.name}" created successfully with {len(selected_accounts)} account(s).'
            )
            return redirect('tiktok_uploader:warmup_task_detail', task_id=task.id)
        else:
            # Форма невалидна - показываем ошибки
            messages.error(request, 'Please correct the errors below.')
    else:
        # GET - показываем форму с дефолтными значениями
        form = WarmupTaskForm(initial={
            'delay_min_sec': 15,
            'delay_max_sec': 45,
            'concurrency': 1,
            'feed_scroll_min_count': 5,
            'feed_scroll_max_count': 15,
            'like_min_count': 3,
            'like_max_count': 10,
            'watch_video_min_count': 5,
            'watch_video_max_count': 20,
            'follow_min_count': 2,
            'follow_max_count': 8,
            'comment_min_count': 0,
            'comment_max_count': 3,
        })
    
    # Получаем аккаунты для отображения
    accounts = TikTokAccount.objects.all().order_by('-created_at')
    
    # Статистика аккаунтов
    total_accounts = accounts.count()
    accounts_with_proxy = accounts.filter(Q(proxy__isnull=False) | Q(current_proxy__isnull=False)).count()
    accounts_with_dolphin = accounts.filter(dolphin_profile_id__isnull=False).count()
    
    context = {
        'form': form,
        'accounts': accounts,
        'total_accounts': total_accounts,
        'accounts_with_proxy': accounts_with_proxy,
        'accounts_with_dolphin': accounts_with_dolphin,
    }
    
    return render(request, 'tiktok_uploader/warmup/create.html', context)


@login_required
def warmup_task_detail(request, task_id):
    """
    Детальная информация о задаче прогрева.
    """
    task = get_object_or_404(WarmupTask, id=task_id)
    
    # Получаем аккаунты задачи
    task_accounts = task.accounts.select_related('account', 'proxy').all()
    
    # Подсчитываем прогресс
    total = task_accounts.count()
    completed = task_accounts.filter(status='COMPLETED').count()
    running = task_accounts.filter(status='RUNNING').count()
    failed = task_accounts.filter(status='FAILED').count()
    pending = task_accounts.filter(status='PENDING').count()
    
    # Прогресс = (завершенные + провалившиеся) / общее количество
    # Потому что и completed, и failed - это "обработанные" аккаунты
    progress_percent = ((completed + failed) / total * 100) if total > 0 else 0
    
    # Определяем можно ли запустить задачу
    can_start = task.status == 'PENDING' and total > 0
    can_stop = task.status == 'RUNNING'
    
    context = {
        'task': task,
        'task_accounts': task_accounts,
        'total_accounts': total,
        'completed_accounts': completed,
        'running_accounts': running,
        'failed_accounts': failed,
        'pending_accounts': pending,
        'progress_percent': round(progress_percent, 1),
        'can_start': can_start,
        'can_stop': can_stop,
    }
    
    return render(request, 'tiktok_uploader/warmup/detail.html', context)


@login_required
def warmup_task_start(request, task_id):
    """
    Запуск задачи прогрева аккаунтов.
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
    
    try:
        task = get_object_or_404(WarmupTask, id=task_id)
        
        # Проверяем статус задачи
        if task.status != 'PENDING':
            messages.error(request, f'Task cannot be started from status {task.status}')
            return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
        
        # Проверяем наличие аккаунтов
        if not task.accounts.exists():
            messages.error(request, 'No accounts assigned to this task')
            return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
        
        # DEPRECATED: Этот view больше не используется!
        # Используйте views_warmup_remote.py для работы через API
        messages.error(
            request, 
            'This local warmup functionality is deprecated. '
            'Please use the remote warmup interface at /tiktok/warmup/create/'
        )
        return redirect('tiktok_uploader:warmup_task_list')
        
    except Exception as e:
        logger.error(f"Error starting warmup task {task_id}: {str(e)}")
        messages.error(request, f'Error starting warmup task: {str(e)}')
    
    return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)


@login_required
def warmup_task_logs(request, task_id):
    """
    API для получения логов задачи прогрева в реальном времени.
    """
    try:
        task = get_object_or_404(WarmupTask, id=task_id)
        
        # Получаем аккаунты с их статусами
        task_accounts = task.accounts.select_related('account').all()
        
        accounts_data = []
        for ta in task_accounts:
            accounts_data.append({
                'id': ta.id,
                'username': ta.account.username,
                'status': ta.status,
                'started_at': ta.started_at.strftime('%Y-%m-%d %H:%M:%S') if ta.started_at else None,
                'completed_at': ta.completed_at.strftime('%Y-%m-%d %H:%M:%S') if ta.completed_at else None,
                'log': ta.log[-1000:] if ta.log else '',  # Последние 1000 символов
            })
        
        # Подсчитываем прогресс
        total = len(accounts_data)
        completed = sum(1 for a in accounts_data if a['status'] == 'COMPLETED')
        running = sum(1 for a in accounts_data if a['status'] == 'RUNNING')
        failed = sum(1 for a in accounts_data if a['status'] == 'FAILED')
        pending = sum(1 for a in accounts_data if a['status'] == 'PENDING')
        
        # Прогресс = (завершенные + провалившиеся) / общее количество
        progress_percent = ((completed + failed) / total * 100) if total > 0 else 0
        
        return JsonResponse({
            'success': True,
            'task_status': task.status,
            'logs': task.log[-5000:] if task.log else '',  # Последние 5000 символов
            'progress': {
                'total': total,
                'completed': completed,
                'running': running,
                'failed': failed,
                'pending': pending,
                'percent': round(progress_percent, 1),
            },
            'accounts': accounts_data,
        })
        
    except Exception as e:
        logger.error(f"Error getting warmup logs for task {task_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def force_stop_warmup_task(request, task_id):
    """
    Принудительная остановка зависшей задачи прогрева.
    Используется когда задача имеет статус RUNNING, но фактически не выполняется.
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
    
    try:
        task = get_object_or_404(WarmupTask, id=task_id)
        
        # Проверяем что задача в статусе RUNNING
        if task.status != 'RUNNING':
            messages.warning(request, f'Task is not running (current status: {task.status})')
            return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
        
        # Принудительно останавливаем задачу
        task.status = 'FAILED'
        task.completed_at = timezone.now()
        task.log += f"\n[{timezone.now()}] ⚠️ Task force stopped by {request.user.username}"
        task.save()
        
        # Останавливаем все RUNNING аккаунты в задаче
        stopped_count = 0
        for warmup_account in task.accounts.filter(status='RUNNING'):
            warmup_account.status = 'FAILED'
            warmup_account.completed_at = timezone.now()
            warmup_account.log += f"\n[{timezone.now()}] ⚠️ Force stopped by {request.user.username}"
            warmup_account.save()
            stopped_count += 1
        
        logger.warning(f"Warmup task {task_id} ({task.name}) force stopped by user {request.user.username}")
        messages.warning(
            request,
            f'Task "{task.name}" has been force stopped. '
            f'{stopped_count} running account(s) were also stopped. '
            f'You can now delete or restart the task.'
        )
        
    except Exception as e:
        logger.error(f"Error force stopping warmup task {task_id}: {str(e)}")
        messages.error(request, f'Error stopping task: {str(e)}')
    
    return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)


@login_required
def restart_warmup_task(request, task_id):
    """
    Перезапуск задачи прогрева.
    Сбрасывает статусы и позволяет запустить задачу заново.
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
    
    try:
        task = get_object_or_404(WarmupTask, id=task_id)
        
        # Проверяем что задача не в процессе выполнения
        if task.status == 'RUNNING':
            messages.error(request, 'Cannot restart a task that is currently running.')
            return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
        
        # Сбрасываем статус задачи
        task.status = 'PENDING'
        task.started_at = None
        task.completed_at = None
        task.save(update_fields=['status', 'started_at', 'completed_at'])
        
        # Сбрасываем статусы всех аккаунтов
        for warmup_account in task.accounts.all():
            warmup_account.status = 'PENDING'
            warmup_account.started_at = None
            warmup_account.completed_at = None
            # Добавляем запись о рестарте в лог
            warmup_account.log += f"\n[{timezone.now()}] ========== TASK RESTARTED ==========\n"
            warmup_account.save()
        
        logger.info(f"Warmup task {task_id} ({task.name}) restarted by user")
        messages.success(request, f'Warmup task "{task.name}" has been reset. You can now start it again.')
        
    except Exception as e:
        logger.error(f"Error restarting warmup task {task_id}: {str(e)}")
        messages.error(request, f'Error restarting task: {str(e)}')
    
    return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)


@login_required
def delete_warmup_task(request, task_id):
    """
    Удаление задачи прогрева.
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
    
    try:
        task = get_object_or_404(WarmupTask, id=task_id)
        
        # Проверяем что задача не выполняется
        if task.status == 'RUNNING':
            messages.error(request, 'Cannot delete a running task. Please wait for it to complete.')
            return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
        
        task_name = task.name
        task.delete()  # Каскадно удалит WarmupTaskAccount
        
        messages.success(request, f'Warmup task "{task_name}" deleted successfully.')
        logger.info(f"Warmup task {task_id} ({task_name}) deleted by user")
        
    except Exception as e:
        logger.error(f"Error deleting warmup task {task_id}: {str(e)}")
        messages.error(request, f'Error deleting task: {str(e)}')
        return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
    
    return redirect('tiktok_uploader:warmup_task_list')
