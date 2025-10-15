"""
Server Management Views
=======================

Views для управления удаленными TikTok серверами.
Включает страницу управления, API для переключения серверов и мониторинг.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Q
import json

from tiktok_uploader.models import TikTokServer, ServerAccount, ServerTask, ServerHealthLog
from tiktok_uploader.services.server_api_client import ServerAPIClient, ServerManager
from tiktok_uploader.services.server_logger import server_logger


# ============================================================================
# API ЭНДПОИНТЫ ДЛЯ ПЕРЕКЛЮЧАТЕЛЯ СЕРВЕРОВ
# ============================================================================

@login_required
@require_http_methods(["GET"])
def api_servers_list(request):
    """
    API: Получить список всех активных серверов.
    
    Returns:
        JsonResponse: {
            "success": True,
            "servers": [...],
            "selected_server_id": int or None
        }
    """
    servers = TikTokServer.objects.filter(is_active=True).order_by('priority', 'name')
    selected_server_id = request.session.get('selected_server_id')
    
    servers_data = []
    for server in servers:
        servers_data.append({
            'id': server.id,
            'name': server.name,
            'host': server.host,
            'port': server.port,
            'status': server.status,
            'is_active': server.is_active,
            'priority': server.priority,
            'max_concurrent_tasks': server.max_concurrent_tasks,
            'active_tasks': server.active_tasks,
            'total_accounts': server.total_accounts,
            'last_ping': server.last_ping.isoformat() if server.last_ping else None,
            'response_time_ms': server.response_time_ms,
        })
    
    return JsonResponse({
        'success': True,
        'servers': servers_data,
        'selected_server_id': selected_server_id
    })


@login_required
@require_http_methods(["POST"])
def api_switch_server(request):
    """
    API: Переключить активный сервер.
    
    POST data:
        {
            "server_id": int
        }
    
    Returns:
        JsonResponse: {
            "success": True/False,
            "message": str
        }
    """
    try:
        data = json.loads(request.body)
        server_id = data.get('server_id')
        
        if not server_id:
            return JsonResponse({
                'success': False,
                'message': 'Server ID is required'
            }, status=400)
        
        # Получаем сервер
        server = get_object_or_404(TikTokServer, id=server_id, is_active=True)
        
        # Сохраняем в сессию
        request.session['selected_server_id'] = server.id
        request.session['selected_server_name'] = server.name
        
        return JsonResponse({
            'success': True,
            'message': f'Switched to {server.name}',
            'server': {
                'id': server.id,
                'name': server.name,
                'status': server.status
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# ============================================================================
# СТРАНИЦА УПРАВЛЕНИЯ СЕРВЕРАМИ
# ============================================================================

@login_required
def server_management(request):
    """
    Страница управления серверами.
    
    Отображает:
    - Список всех серверов
    - Статус каждого сервера
    - Статистику по серверам
    - Возможность добавления/редактирования/удаления
    """
    servers = TikTokServer.objects.all().order_by('priority', 'name')
    
    # Статистика для шаблона
    stats = {
        'online_count': servers.filter(status='online').count(),
        'busy_count': servers.filter(status='busy').count(),
        'offline_count': servers.filter(status='offline').count(),
        'total_tasks': ServerTask.objects.count(),
    }
    
    context = {
        'servers': servers,
        'stats': stats,
        'selected_server_id': request.session.get('selected_server_id'),
    }
    
    return render(request, 'tiktok_uploader/servers/management.html', context)


@login_required
def server_add(request):
    """
    Добавить новый сервер.
    """
    if request.method == 'GET':
        return render(request, 'tiktok_uploader/servers/add.html')
    
    try:
        name = request.POST.get('name')
        host = request.POST.get('host')
        port = int(request.POST.get('port', 8000))
        api_key = request.POST.get('api_key', '').strip()
        priority = int(request.POST.get('priority', 1))
        is_active = request.POST.get('is_active') == 'on'
        
        if not name or not host:
            messages.error(request, 'Name and host are required')
            return redirect('tiktok_uploader:server_management')
        
        # Создаем сервер
        server = TikTokServer.objects.create(
            name=name,
            host=host,
            port=port,
            api_key=api_key if api_key else None,
            priority=priority,
            status='offline',
            is_active=is_active
        )
        
        # Проверяем доступность
        try:
            client = ServerAPIClient(server)
            success, result = client.ping()
            client.close()
            
            if success:
                server.status = 'online'
                server.last_health_check = timezone.now()
                server.save()
                server_logger.log_server_added(name, host, port, request.user.username)
                messages.success(request, f'Server "{name}" added successfully and is ONLINE')
            else:
                server_logger.log_server_added(name, host, port, request.user.username)
                messages.warning(request, f'Server "{name}" added but is OFFLINE')
        except Exception as ping_error:
            server_logger.log_server_added(name, host, port, request.user.username)
            server_logger.log_error("server_add_ping", str(ping_error))
            messages.warning(request, f'Server "{name}" added but could not ping')
        
        return redirect('tiktok_uploader:server_detail', server_id=server.id)
        
    except Exception as e:
        messages.error(request, f'Error adding server: {str(e)}')
        return redirect('tiktok_uploader:server_management')


@login_required
def server_edit(request, server_id):
    """
    Редактировать сервер.
    """
    server = get_object_or_404(TikTokServer, id=server_id)
    
    # GET - показать форму редактирования
    if request.method == 'GET':
        return render(request, 'tiktok_uploader/servers/edit.html', {'server': server})
    
    try:
        server.name = request.POST.get('name', server.name)
        server.host = request.POST.get('host', server.host)
        server.port = int(request.POST.get('port', server.port))
        server.api_key = request.POST.get('api_key', '').strip() or None
        server.max_concurrent_tasks = int(request.POST.get('max_concurrent_tasks', server.max_concurrent_tasks))
        server.priority = int(request.POST.get('priority', server.priority))
        server.notes = request.POST.get('notes', server.notes)
        server.is_active = request.POST.get('is_active') == 'on'
        
        server.save()
        
        # Логируем изменения
        changes = {
            'host': server.host,
            'port': server.port,
            'priority': server.priority,
            'is_active': server.is_active
        }
        server_logger.log_server_edited(server.name, changes, request.user.username)
        
        messages.success(request, f'Server "{server.name}" updated successfully')
        
    except Exception as e:
        messages.error(request, f'Error updating server: {str(e)}')
    
    return redirect('tiktok_uploader:server_management')


@login_required
def server_delete(request, server_id):
    """
    Удалить сервер.
    """
    server = get_object_or_404(TikTokServer, id=server_id)
    
    # Только POST для удаления (безопасность)
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('tiktok_uploader:server_detail', server_id=server_id)
    
    # Проверяем, есть ли активные задачи
    active_tasks_count = server.tasks.filter(status__in=['RUNNING', 'QUEUED']).count()
    
    if active_tasks_count > 0:
        messages.error(request, f'Cannot delete server "{server.name}": has {active_tasks_count} active tasks')
        return redirect('tiktok_uploader:server_management')
    
    server_name = server.name
    server.delete()
    
    # Логируем удаление
    server_logger.log_server_deleted(server_name, request.user.username)
    
    # Если это был выбранный сервер, очищаем сессию
    if request.session.get('selected_server_id') == server_id:
        request.session.pop('selected_server_id', None)
        request.session.pop('selected_server_name', None)
    
    messages.success(request, f'Server "{server_name}" deleted successfully')
    return redirect('tiktok_uploader:server_management')


@login_required
def server_ping(request, server_id):
    """
    Проверить доступность сервера.
    """
    server = get_object_or_404(TikTokServer, id=server_id)
    
    try:
        import time
        start_time = time.time()
        
        client = ServerAPIClient(server)
        success, result = client.ping()
        client.close()
        
        response_time = (time.time() - start_time) * 1000  # в миллисекундах
        
        if success:
            server.status = 'online'
            server.last_health_check = timezone.now()
            server.save()
            
            # Создаем запись в логах здоровья
            ServerHealthLog.objects.create(
                server=server,
                is_online=True,
                response_time_ms=int(response_time),
                error_message=""
            )
            
            server_logger.log_ping(server.name, True, response_time)
            messages.success(request, f'Server "{server.name}" is ONLINE ✓ (response: {response_time:.0f}ms)')
        else:
            server.status = 'offline'
            server.save()
            
            error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else str(result)
            
            # Создаем запись в логах здоровья
            ServerHealthLog.objects.create(
                server=server,
                is_online=False,
                response_time_ms=int(response_time),
                error_message=error_msg
            )
            
            server_logger.log_ping(server.name, False, error=error_msg)
            messages.error(request, f'Server "{server.name}" is OFFLINE: {error_msg}')
        
    except Exception as e:
        server.status = 'offline'
        server.save()
        
        # Создаем запись в логах здоровья
        ServerHealthLog.objects.create(
            server=server,
            is_online=False,
            response_time_ms=0,
            error_message=str(e)
        )
        
        server_logger.log_ping(server.name, False, error=str(e))
        messages.error(request, f'Error pinging server: {str(e)}')
    
    return redirect('tiktok_uploader:server_management')


@login_required
def server_ping_all(request):
    """
    Проверить доступность всех серверов.
    """
    try:
        results = ServerManager.ping_all_servers()
        
        online_count = sum(1 for r in results if r['is_online'])
        total_count = len(results)
        offline_count = total_count - online_count
        
        server_logger.log_ping_all(total_count, online_count, offline_count)
        messages.success(request, f'Pinged {total_count} servers. {online_count} online, {offline_count} offline.')
        
    except Exception as e:
        messages.error(request, f'Error pinging servers: {str(e)}')
    
    return redirect('tiktok_uploader:server_management')


@login_required
def server_detail(request, server_id):
    """
    Детальная информация о сервере.
    """
    server = get_object_or_404(TikTokServer, id=server_id)
    
    # Получаем аккаунты на сервере
    assigned_accounts = server.assigned_accounts.select_related('account').all()[:20]
    
    # Получаем задачи на сервере
    active_tasks = server.tasks.filter(status__in=['RUNNING', 'QUEUED']).order_by('-created_at')[:10]
    recent_tasks = server.tasks.order_by('-created_at')[:20]
    
    # Получаем последние логи здоровья
    health_logs = server.health_logs.order_by('-checked_at')[:20]
    
    # Статистика задач
    tasks_stats = {
        'total': server.tasks.count(),
        'running': server.tasks.filter(status='RUNNING').count(),
        'queued': server.tasks.filter(status='QUEUED').count(),
        'completed': server.tasks.filter(status='COMPLETED').count(),
        'failed': server.tasks.filter(status='FAILED').count(),
    }
    
    context = {
        'server': server,
        'assigned_accounts': assigned_accounts,
        'active_tasks': active_tasks,
        'recent_tasks': recent_tasks,
        'health_logs': health_logs,
        'tasks_stats': tasks_stats,
    }
    
    return render(request, 'tiktok_uploader/servers/detail.html', context)


@login_required
def server_logs(request, server_id):
    """
    Показать логи здоровья сервера.
    """
    server = get_object_or_404(TikTokServer, id=server_id)
    
    # Получаем логи здоровья
    health_logs = server.health_logs.order_by('-checked_at')[:100]
    
    # Подсчитываем статистику
    from django.db.models import Avg, Count
    
    total_checks = health_logs.count()
    online_count = health_logs.filter(is_online=True).count()
    offline_count = health_logs.filter(is_online=False).count()
    
    avg_response = health_logs.filter(response_time_ms__gt=0).aggregate(
        avg=Avg('response_time_ms')
    )['avg'] or 0
    
    uptime_percent = (online_count / total_checks * 100) if total_checks > 0 else 0
    
    stats = {
        'online_count': online_count,
        'offline_count': offline_count,
        'avg_response_time': avg_response,
        'uptime_percent': uptime_percent,
    }
    
    context = {
        'server': server,
        'health_logs': health_logs,
        'stats': stats,
    }
    
    return render(request, 'tiktok_uploader/servers/logs.html', context)


@login_required
@require_http_methods(["POST"])
def server_sync_stats(request, server_id):
    """
    Синхронизировать статистику с сервера.
    """
    server = get_object_or_404(TikTokServer, id=server_id)
    
    try:
        ServerManager.update_server_stats(server)
        messages.success(request, f'Statistics synced for "{server.name}"')
        
    except Exception as e:
        messages.error(request, f'Error syncing statistics: {str(e)}')
    
    return redirect('tiktok_uploader:server_detail', server_id=server_id)


@login_required
@require_http_methods(["POST"])
def server_create_health_log(request, server_id):
    """
    Создать запись в логе здоровья сервера.
    """
    server = get_object_or_404(TikTokServer, id=server_id)
    
    try:
        health_log = ServerManager.create_health_log(server)
        
        if health_log.is_online:
            messages.success(request, f'Health check completed: Server is ONLINE')
        else:
            messages.warning(request, f'Health check completed: Server is OFFLINE')
        
    except Exception as e:
        messages.error(request, f'Error creating health log: {str(e)}')
    
    return redirect('tiktok_uploader:server_detail', server_id=server_id)
