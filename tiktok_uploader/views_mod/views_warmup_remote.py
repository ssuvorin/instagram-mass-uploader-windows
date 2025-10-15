"""
Remote Warmup Views for TikTok
================================

Представления для прогрева TikTok аккаунтов через удаленные API серверы.
Полностью переработанный функционал для работы с распределенной архитектурой.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.views.decorators.http import require_http_methods

from tiktok_uploader.models import (
    WarmupTask, WarmupTaskAccount, TikTokAccount,
    TikTokServer, ServerTask, TikTokProxy
)
from tiktok_uploader.services.server_api_client import ServerAPIClient, ServerManager
from tiktok_uploader.services.server_logger import server_logger
from cabinet.models import Client

logger = logging.getLogger('tiktok_uploader')


# ============================================================================
# СПИСОК ЗАДАЧ ПРОГРЕВА
# ============================================================================

@login_required
def warmup_task_list(request):
    """
    Список всех задач прогрева аккаунтов.
    Отображает задачи на всех серверах.
    """
    # Получаем параметры фильтрации
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    server_filter = request.GET.get('server', '')
    
    # Базовый queryset
    tasks = WarmupTask.objects.all().order_by('-created_at')
    
    # Применяем фильтры
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    if search_query:
        tasks = tasks.filter(name__icontains=search_query)
    
    if server_filter:
        tasks = tasks.filter(server_task__server_id=server_filter)
    
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
    
    # Список серверов для фильтра
    servers = TikTokServer.objects.filter(is_active=True).order_by('name')
    
    context = {
        'tasks': tasks,
        'pending_count': pending_count,
        'running_count': running_count,
        'completed_count': completed_count,
        'failed_count': failed_count,
        'status_filter': status_filter,
        'search_query': search_query,
        'server_filter': server_filter,
        'servers': servers,
    }
    
    return render(request, 'tiktok_uploader/warmup/list.html', context)


# ============================================================================
# СОЗДАНИЕ ЗАДАЧИ ПРОГРЕВА (REMOTE)
# ============================================================================

@login_required
def warmup_task_create_remote(request):
    """
    Создание новой задачи прогрева для отправки на удаленный сервер.
    
    POST:
        - name: название задачи
        - client_id: ID клиента
        - tag: тематика аккаунтов
        - accounts_count: количество аккаунтов
        - server_id: ID сервера (или "auto" для автовыбора)
        - delay_min_sec: минимальная задержка
        - delay_max_sec: максимальная задержка
        - concurrency: параллельность
        - feed_scroll_min_count, feed_scroll_max_count: скроллинг ленты
        - like_min_count, like_max_count: лайки
        - watch_video_min_count, watch_video_max_count: просмотр видео
        - follow_min_count, follow_max_count: подписки
        - comment_min_count, comment_max_count: комментарии
    """
    if request.method == 'POST':
        try:
            # Извлекаем данные из формы
            name = request.POST.get('name', f"Warmup {timezone.now().strftime('%Y-%m-%d %H:%M')}")
            client_id = request.POST.get('client_id')
            tag = request.POST.get('tag', '')
            account_ids = request.POST.getlist('account_ids')  # Получаем список выбранных аккаунтов
            server_id = request.POST.get('server_id')
            
            # Параметры прогрева
            delay_min_sec = int(request.POST.get('delay_min_sec', 15))
            delay_max_sec = int(request.POST.get('delay_max_sec', 45))
            concurrency = int(request.POST.get('concurrency', 1))
            
            # Диапазоны действий
            feed_scroll_min = int(request.POST.get('feed_scroll_min_count', 5))
            feed_scroll_max = int(request.POST.get('feed_scroll_max_count', 15))
            like_min = int(request.POST.get('like_min_count', 3))
            like_max = int(request.POST.get('like_max_count', 10))
            watch_min = int(request.POST.get('watch_video_min_count', 5))
            watch_max = int(request.POST.get('watch_video_max_count', 20))
            follow_min = int(request.POST.get('follow_min_count', 0))
            follow_max = int(request.POST.get('follow_max_count', 5))
            comment_min = int(request.POST.get('comment_min_count', 0))
            comment_max = int(request.POST.get('comment_max_count', 3))
            
            # Валидация
            if not account_ids:
                messages.error(request, 'Please select at least 1 account')
                return redirect('tiktok_uploader:warmup_task_create')
            
            # Получаем выбранные аккаунты
            selected_accounts = TikTokAccount.objects.filter(id__in=account_ids, status='ACTIVE')
            if not selected_accounts.exists():
                messages.error(request, 'No valid accounts selected')
                return redirect('tiktok_uploader:warmup_task_create')
            
            # Используем указанный сервер (автовыбор убран)
            if not server_id:
                messages.error(request, 'Please select a server')
                return redirect('tiktok_uploader:warmup_task_create')
            
            server = get_object_or_404(TikTokServer, id=server_id, is_active=True)
            
            # Создаем задачу в Django
            task = WarmupTask.objects.create(
                name=name,
                status='PENDING',
                delay_min_sec=delay_min_sec,
                delay_max_sec=delay_max_sec,
                concurrency=concurrency,
                feed_scroll_min_count=feed_scroll_min,
                feed_scroll_max_count=feed_scroll_max,
                like_min_count=like_min,
                like_max_count=like_max,
                watch_video_min_count=watch_min,
                watch_video_max_count=watch_max,
                follow_min_count=follow_min,
                follow_max_count=follow_max,
                comment_min_count=comment_min,
                comment_max_count=comment_max,
            )
            
            # Отправляем задачу на сервер через API
            client_api = ServerAPIClient(server)
            
            # Подготавливаем параметры задачи для API
            task_settings = {
                'feed_scroll_min': feed_scroll_min,
                'feed_scroll_max': feed_scroll_max,
                'like_min': like_min,
                'like_max': like_max,
                'watch_video_min': watch_min,
                'watch_video_max': watch_max,
                'follow_min': follow_min,
                'follow_max': follow_max,
                'comment_min': comment_min,
                'comment_max': comment_max,
                'delay_min_sec': delay_min_sec,
                'delay_max_sec': delay_max_sec,
                'concurrency': concurrency,
            }
            
            # Получаем клиента
            client_obj = None
            if client_id:
                client_obj = get_object_or_404(Client, id=client_id)
            
            # Готовим полные данные аккаунтов для сервера
            accounts_payload = [acc.to_server_payload() for acc in selected_accounts]

            # Отправляем задачу (включая полные данные аккаунтов)
            success, result = client_api.create_warmup_task(
                client=client_obj.name if client_obj else '',
                accounts_count=selected_accounts.count(),
                tag=tag,
                settings=task_settings,
                use_cookie_robot=False,
                accounts=accounts_payload
            )
            client_api.close()
            
            if not success:
                # Ошибка при создании задачи на сервере
                task.status = 'FAILED'
                task.log = f"[{timezone.now()}] Error creating task on server: {result.get('error', 'Unknown error')}"
                task.save()
                
                server_logger.log_task_failed(server.name, name, result.get('error', 'Unknown error'))
                messages.error(request, f'Failed to create task on server: {result.get("error", "Unknown error")}')
                return redirect('tiktok_uploader:warmup_task_detail', task_id=task.id)
            
            # Успешно создана на сервере
            remote_task_id = result.get('task_id')
            remote_status = result.get('status', 'QUEUED')
            
            # Обновляем статус задачи
            if remote_status == 'RUNNING':
                task.status = 'RUNNING'
                task.started_at = timezone.now()
            else:
                task.status = 'PENDING'  # Или QUEUED
            task.save()
            
            # Создаем ServerTask для связи
            ServerTask.objects.create(
                server=server,
                warmup_task=task,
                remote_task_id=remote_task_id,
                status=remote_status
            )
            
            # Логируем
            server_logger.log_task_created(server.name, 'warmup', name, request.user.username)
            
            queue_position = result.get('queue_position', 'unknown')
            messages.success(
                request,
                f'Warmup task "{name}" created on server "{server.name}" with {selected_accounts.count()} account(s). '
                f'Status: {remote_status}, Queue position: {queue_position}'
            )
            
            return redirect('tiktok_uploader:warmup_task_detail', task_id=task.id)
            
        except Exception as e:
            logger.error(f"Error creating remote warmup task: {str(e)}")
            messages.error(request, f'Error creating warmup task: {str(e)}')
            return redirect('tiktok_uploader:warmup_task_create_remote')
    
    # GET - показываем форму
    clients = Client.objects.all().order_by('name')
    servers = TikTokServer.objects.filter(is_active=True).order_by('priority', 'name')
    
    # Получаем доступные теги
    tags = TikTokAccount.objects.values_list('tag', flat=True).distinct().exclude(tag='').exclude(tag__isnull=True)
    
    # Статистика аккаунтов по тегам
    tag_stats = {}
    for tag_name in tags:
        count = TikTokAccount.objects.filter(tag=tag_name, status='ACTIVE').count()
        tag_stats[tag_name] = count
    
    # Получаем все аккаунты для выбора (включая неактивные для фильтрации)
    accounts = TikTokAccount.objects.select_related('client', 'proxy', 'current_proxy').order_by('username')
    
    # Получаем доступные статусы для фильтрации
    status_choices = TikTokAccount.STATUS_CHOICES
    
    # Получаем уникальные прокси для фильтрации
    proxies = TikTokProxy.objects.filter(
        Q(accounts__isnull=False) | Q(active_accounts__isnull=False)
    ).distinct().order_by('host', 'port')
    
    # Статистика по статусам
    status_stats = {}
    for status_code, status_name in status_choices:
        count = TikTokAccount.objects.filter(status=status_code).count()
        if count > 0:
            status_stats[status_code] = count
    
    context = {
        'clients': clients,
        'servers': servers,
        'tags': tags,
        'tag_stats': tag_stats,
        'accounts': accounts,
        'status_choices': status_choices,
        'status_stats': status_stats,
        'proxies': proxies,
    }
    
    return render(request, 'tiktok_uploader/warmup/create_remote.html', context)


# ============================================================================
# ДЕТАЛИ ЗАДАЧИ ПРОГРЕВА
# ============================================================================

@login_required
def warmup_task_detail(request, task_id):
    """
    Детальная информация о задаче прогрева.
    Получает актуальную информацию с сервера через API.
    """
    task = get_object_or_404(WarmupTask, id=task_id)
    
    # Пытаемся найти ServerTask
    try:
        server_task = ServerTask.objects.get(warmup_task=task)
        server = server_task.server
        has_server = True
        
        # Получаем актуальную информацию с сервера
        if server_task.remote_task_id:
            client = ServerAPIClient(server)
            success, result = client.get_task_status(server_task.remote_task_id)
            client.close()
            
            if success:
                # Обновляем статус задачи
                remote_status = result.get('status')
                if remote_status:
                    task.status = remote_status
                    task.save()
                
                server_task.status = result.get('queue_status', 'UNKNOWN')
                server_task.save()
                
                # Получаем прогресс
                progress = result.get('progress', {})
            else:
                progress = {}
        else:
            progress = {}
    except ServerTask.DoesNotExist:
        has_server = False
        server = None
        server_task = None
        progress = {}
    
    # Получаем аккаунты задачи (если есть)
    task_accounts = task.accounts.select_related('account', 'proxy').all()
    
    # Подсчитываем прогресс
    total = task_accounts.count() or progress.get('total_accounts', 0)
    completed = task_accounts.filter(status='COMPLETED').count() or progress.get('completed', 0)
    running = task_accounts.filter(status='RUNNING').count() or progress.get('running', 0)
    failed = task_accounts.filter(status='FAILED').count() or progress.get('failed', 0)
    pending = task_accounts.filter(status='PENDING').count() or progress.get('pending', 0)
    
    # Прогресс в процентах
    progress_percent = ((completed + failed) / total * 100) if total > 0 else 0
    
    # Определяем доступные действия
    can_start = task.status == 'PENDING' and has_server
    can_stop = task.status == 'RUNNING' and has_server
    can_delete = task.status not in ['RUNNING']
    
    context = {
        'task': task,
        'task_accounts': task_accounts,
        'server': server,
        'server_task': server_task,
        'has_server': has_server,
        'total_accounts': total,
        'completed_accounts': completed,
        'running_accounts': running,
        'failed_accounts': failed,
        'pending_accounts': pending,
        'progress_percent': round(progress_percent, 1),
        'can_start': can_start,
        'can_stop': can_stop,
        'can_delete': can_delete,
    }
    
    return render(request, 'tiktok_uploader/warmup/detail_remote.html', context)


# ============================================================================
# ЗАПУСК ЗАДАЧИ
# ============================================================================

@login_required
@require_http_methods(["POST"])
def warmup_task_start(request, task_id):
    """
    Запуск задачи прогрева на удаленном сервере.
    
    ПРИМЕЧАНИЕ: В API v2 задачи запускаются автоматически когда сервер освобождается.
    Эта функция проверяет статус и переводит задачу в RUNNING если она уже выполняется.
    """
    try:
        task = get_object_or_404(WarmupTask, id=task_id)
        server_task = get_object_or_404(ServerTask, warmup_task=task)
        server = server_task.server
        
        # Получаем актуальный статус с сервера
        client = ServerAPIClient(server)
        success, result = client.get_task_status(server_task.remote_task_id)
        client.close()
        
        if success:
            remote_status = result.get('status', 'UNKNOWN')
            
            # Обновляем локальный статус
            task.status = remote_status
            if remote_status == 'RUNNING' and not task.started_at:
                task.started_at = timezone.now()
            task.save()
            
            server_task.status = result.get('queue_status', remote_status)
            server_task.save()
            
            if remote_status == 'RUNNING':
                messages.success(request, f'Task is now running on server "{server.name}"')
            elif remote_status == 'QUEUED':
                queue_pos = result.get('queue_position', 'unknown')
                messages.info(request, f'Task is queued on server "{server.name}", position: {queue_pos}')
            else:
                messages.info(request, f'Task status: {remote_status}')
        else:
            error_msg = result.get('error', 'Unknown error')
            messages.error(request, f'Failed to get task status: {error_msg}')
        
    except Exception as e:
        logger.error(f"Error checking warmup task {task_id}: {str(e)}")
        messages.error(request, f'Error: {str(e)}')
    
    return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)


# ============================================================================
# ОСТАНОВКА ЗАДАЧИ
# ============================================================================

@login_required
@require_http_methods(["POST"])
def warmup_task_stop(request, task_id):
    """
    Остановка задачи прогрева на удаленном сервере.
    """
    try:
        task = get_object_or_404(WarmupTask, id=task_id)
        server_task = get_object_or_404(ServerTask, warmup_task=task)
        server = server_task.server
        
        # Проверяем статус
        if task.status != 'RUNNING':
            messages.warning(request, f'Task is not running (current status: {task.status})')
            return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
        
        # Отправляем команду на сервер
        client = ServerAPIClient(server)
        success, result = client.stop_task(server_task.remote_task_id)
        client.close()
        
        if success:
            task.status = 'PAUSED'
            task.save()
            
            server_task.status = 'STOPPED'
            server_task.save()
            
            server_logger.log_task_stopped(server.name, task.name, request.user.username)
            messages.success(request, f'Warmup task "{task.name}" stopped on server "{server.name}"')
        else:
            error_msg = result.get('error', 'Unknown error')
            messages.error(request, f'Failed to stop task: {error_msg}')
        
    except Exception as e:
        logger.error(f"Error stopping warmup task {task_id}: {str(e)}")
        messages.error(request, f'Error stopping task: {str(e)}')
    
    return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)


# ============================================================================
# УДАЛЕНИЕ ЗАДАЧИ
# ============================================================================

@login_required
@require_http_methods(["POST"])
def warmup_task_delete(request, task_id):
    """
    Удаление задачи прогрева.
    Также удаляет задачу с удаленного сервера.
    """
    try:
        task = get_object_or_404(WarmupTask, id=task_id)
        
        # Проверяем статус
        if task.status == 'RUNNING':
            messages.error(request, 'Cannot delete a running task. Please stop it first.')
            return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
        
        # Пытаемся удалить с сервера
        try:
            server_task = ServerTask.objects.get(warmup_task=task)
            server = server_task.server
            
            if server_task.remote_task_id:
                client = ServerAPIClient(server)
                success, result = client.delete_task(server_task.remote_task_id)
                client.close()
                
                if not success:
                    logger.warning(f"Could not delete task from server: {result.get('error')}")
        except ServerTask.DoesNotExist:
            pass
        
        task_name = task.name
        task.delete()  # Каскадно удалит WarmupTaskAccount и ServerTask
        
        messages.success(request, f'Warmup task "{task_name}" deleted successfully')
        logger.info(f"Warmup task {task_id} ({task_name}) deleted by user")
        
    except Exception as e:
        logger.error(f"Error deleting warmup task {task_id}: {str(e)}")
        messages.error(request, f'Error deleting task: {str(e)}')
        return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
    
    return redirect('tiktok_uploader:warmup_task_list')


# ============================================================================
# ЛОГИ ЗАДАЧИ (API для AJAX)
# ============================================================================

@login_required
def warmup_task_logs(request, task_id):
    """
    API для получения логов задачи прогрева в реальном времени с сервера.
    """
    try:
        task = get_object_or_404(WarmupTask, id=task_id)
        server_task = ServerTask.objects.get(warmup_task=task)
        server = server_task.server
        
        # Получаем статус с сервера
        if server_task.remote_task_id:
            client = ServerAPIClient(server)
            success, result = client.get_task_status(server_task.remote_task_id)
            client.close()
            
            if success:
                # Обновляем статус
                remote_status = result.get('status')
                if remote_status:
                    task.status = remote_status
                    task.save()
                
                return JsonResponse({
                    'success': True,
                    'task_status': task.status,
                    'logs': result.get('logs', ''),
                    'progress': result.get('progress', {}),
                    'accounts': result.get('accounts', []),
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'error': 'No remote task ID'
            }, status=400)
        
    except ServerTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Task is not assigned to a server'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting warmup logs for task {task_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

