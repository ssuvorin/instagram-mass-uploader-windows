"""
API Views for Account Management
=================================

API эндпоинты для управления аккаунтами TikTok.
Используется серверами для получения аккаунтов из общей БД.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone
import json
import logging

from tiktok_uploader.models import TikTokAccount, TikTokProxy, ServerAccount, TikTokServer

logger = logging.getLogger(__name__)


# ============================================================================
# РЕЗЕРВИРОВАНИЕ АККАУНТОВ ДЛЯ СЕРВЕРОВ
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def reserve_accounts(request):
    """
    API: Зарезервировать аккаунты для сервера.
    
    Серверы используют этот эндпоинт для получения аккаунтов из общей БД.
    
    POST data:
        {
            "server_id": int,
            "client": str,
            "tag": str (optional),
            "count": int,
            "status_filter": str (optional, default: "ACTIVE")
        }
    
    Returns:
        {
            "success": true,
            "accounts": [...],
            "count": int
        }
    """
    try:
        data = json.loads(request.body)
        
        server_id = data.get('server_id')
        client = data.get('client')
        tag = data.get('tag')
        count = data.get('count', 10)
        status_filter = data.get('status_filter', 'ACTIVE')
        
        # Валидация
        if not server_id or not client:
            return JsonResponse({
                'success': False,
                'error': 'server_id and client are required'
            }, status=400)
        
        # Проверяем существование сервера
        try:
            server = TikTokServer.objects.get(id=server_id)
        except TikTokServer.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Server with id {server_id} not found'
            }, status=404)
        
        # Получаем аккаунты с учетом фильтров
        with transaction.atomic():
            # Базовый запрос
            accounts_query = TikTokAccount.objects.filter(
                client__name=client,
                status=status_filter
            ).select_related('proxy', 'current_proxy', 'client')
            
            # Фильтр по тематике
            if tag:
                accounts_query = accounts_query.filter(tag=tag)
            
            # Приоритет: аккаунты, которые уже назначены на этот сервер
            # (чтобы не пересоздавать профили Dolphin)
            accounts_on_server = accounts_query.filter(
                server_assignment__server=server
            )[:count]
            
            accounts_list = list(accounts_on_server)
            remaining_count = count - len(accounts_list)
            
            # Если не хватает, берем свободные аккаунты
            if remaining_count > 0:
                free_accounts = accounts_query.filter(
                    server_assignment__isnull=True
                ).order_by('-created_at')[:remaining_count]
                
                accounts_list.extend(free_accounts)
            
            # Если все еще не хватает, берем с других серверов (в крайнем случае)
            if len(accounts_list) < count:
                remaining_count = count - len(accounts_list)
                other_server_accounts = accounts_query.exclude(
                    id__in=[acc.id for acc in accounts_list]
                ).order_by('-created_at')[:remaining_count]
                
                accounts_list.extend(other_server_accounts)
            
            # Назначаем аккаунты на сервер
            for account in accounts_list:
                ServerAccount.objects.update_or_create(
                    account=account,
                    defaults={
                        'server': server,
                        'status': 'ASSIGNED',
                        'assigned_at': timezone.now()
                    }
                )
            
            # Формируем ответ
            accounts_data = []
            for account in accounts_list:
                acc_data = {
                    'id': account.id,
                    'username': account.username,
                    'password': account.password,
                    'email': account.email,
                    'email_password': account.email_password,
                    'phone_number': account.phone_number,
                    'dolphin_profile_id': account.dolphin_profile_id,
                    'locale': account.locale,
                    'status': account.status,
                    'tag': account.tag,
                }
                
                # Прокси
                proxy = account.current_proxy or account.proxy
                if proxy:
                    acc_data['proxy'] = {
                        'host': proxy.host,
                        'port': proxy.port,
                        'username': proxy.username,
                        'password': proxy.password,
                        'type': proxy.proxy_type.lower(),
                        'ip_change_url': proxy.ip_change_url,
                    }
                
                # Информация о назначении на сервер
                try:
                    server_assignment = account.server_assignment
                    acc_data['server_assignment'] = {
                        'dolphin_profile_id_on_server': server_assignment.dolphin_profile_id_on_server,
                        'last_used_at': server_assignment.last_used_at.isoformat() if server_assignment.last_used_at else None,
                    }
                except:
                    acc_data['server_assignment'] = None
                
                accounts_data.append(acc_data)
        
        logger.info(f"Reserved {len(accounts_data)} accounts for server {server.name} (client: {client}, tag: {tag})")
        
        return JsonResponse({
            'success': True,
            'accounts': accounts_data,
            'count': len(accounts_data),
            'server_id': server_id,
            'server_name': server.name
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error reserving accounts: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def release_accounts(request):
    """
    API: Освободить аккаунты после завершения задачи.
    
    POST data:
        {
            "server_id": int,
            "usernames": [str, ...]
        }
    
    Returns:
        {
            "success": true,
            "released_count": int
        }
    """
    try:
        data = json.loads(request.body)
        
        server_id = data.get('server_id')
        usernames = data.get('usernames', [])
        
        if not server_id or not usernames:
            return JsonResponse({
                'success': False,
                'error': 'server_id and usernames are required'
            }, status=400)
        
        # Освобождаем аккаунты
        with transaction.atomic():
            accounts = TikTokAccount.objects.filter(username__in=usernames)
            
            released_count = 0
            for account in accounts:
                try:
                    server_assignment = account.server_assignment
                    if server_assignment and server_assignment.server_id == server_id:
                        # Не удаляем назначение, просто обновляем статус
                        server_assignment.status = 'FREE'
                        server_assignment.last_used_at = timezone.now()
                        server_assignment.save()
                        released_count += 1
                except:
                    pass
        
        logger.info(f"Released {released_count} accounts from server {server_id}")
        
        return JsonResponse({
            'success': True,
            'released_count': released_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error releasing accounts: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def sync_account_data(request):
    """
    API: Синхронизировать данные аккаунта с сервера обратно в БД.
    
    POST data:
        {
            "username": str,
            "server_id": int,
            "dolphin_profile_id": str (optional),
            "cookies": {...} (optional),
            "fingerprint": {...} (optional),
            "status": str (optional),
            "videos_uploaded": int (optional)
        }
    
    Returns:
        {
            "success": true,
            "message": "..."
        }
    """
    try:
        data = json.loads(request.body)
        
        username = data.get('username')
        server_id = data.get('server_id')
        
        if not username or not server_id:
            return JsonResponse({
                'success': False,
                'error': 'username and server_id are required'
            }, status=400)
        
        with transaction.atomic():
            try:
                account = TikTokAccount.objects.get(username=username)
            except TikTokAccount.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Account {username} not found'
                }, status=404)
            
            # Обновляем данные аккаунта
            updated_fields = []
            
            # Профиль Dolphin
            if 'dolphin_profile_id' in data and data['dolphin_profile_id']:
                account.dolphin_profile_id = data['dolphin_profile_id']
                updated_fields.append('dolphin_profile_id')
            
            # Статус
            if 'status' in data and data['status']:
                account.status = data['status']
                updated_fields.append('status')
            
            # Последнее использование
            account.last_used = timezone.now()
            updated_fields.append('last_used')
            
            if updated_fields:
                account.save(update_fields=updated_fields)
            
            # Обновляем ServerAccount
            try:
                server_assignment = account.server_assignment
                
                if 'dolphin_profile_id' in data:
                    server_assignment.dolphin_profile_id_on_server = data['dolphin_profile_id']
                
                if 'cookies' in data:
                    server_assignment.cookies_from_server = data['cookies']
                
                if 'fingerprint' in data:
                    server_assignment.fingerprint_from_server = data['fingerprint']
                
                server_assignment.last_sync_at = timezone.now()
                server_assignment.save()
                
            except Exception as e:
                logger.warning(f"Could not update ServerAccount for {username}: {str(e)}")
        
        logger.info(f"Synced data for account {username} from server {server_id}")
        
        return JsonResponse({
            'success': True,
            'message': f'Account {username} data synced successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error syncing account data: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_available_accounts_count(request):
    """
    API: Получить количество доступных аккаунтов.
    
    Query params:
        - client: название клиента
        - tag: тематика (optional)
        - status: статус (optional, default: ACTIVE)
    
    Returns:
        {
            "count": int,
            "client": str,
            "tag": str or null
        }
    """
    try:
        client = request.GET.get('client')
        tag = request.GET.get('tag')
        status = request.GET.get('status', 'ACTIVE')
        
        if not client:
            return JsonResponse({
                'success': False,
                'error': 'client parameter is required'
            }, status=400)
        
        # Подсчитываем аккаунты
        query = TikTokAccount.objects.filter(
            client__name=client,
            status=status
        )
        
        if tag:
            query = query.filter(tag=tag)
        
        count = query.count()
        
        return JsonResponse({
            'success': True,
            'count': count,
            'client': client,
            'tag': tag,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error getting accounts count: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

