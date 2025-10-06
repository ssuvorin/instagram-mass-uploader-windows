"""
Proxy Views for TikTok Uploader
=================================

Представления для управления прокси-серверами.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count
import requests
import re

from ..models import TikTokProxy, TikTokAccount
from ..forms import TikTokProxyForm, BulkProxyImportForm
from ..utils import validate_proxy, parse_proxy_string


# ============================================================================
# УПРАВЛЕНИЕ ПРОКСИ
# ============================================================================

@login_required
def proxy_list(request):
    """
    Список всех прокси-серверов.
    
    Features:
        - Отображение всех прокси
        - Фильтрация по:
            * Статусу (active, inactive, banned, checking)
            * Типу (HTTP, HTTPS, SOCKS5)
            * Стране
        - Для каждого прокси показывает:
            * Host:Port
            * Тип и статус
            * External IP
            * Страна/Город
            * Привязанные аккаунты (количество)
            * Последняя проверка
            * Кнопки действий (Edit, Test, Change IP, Delete)
        - Общая статистика:
            * Всего прокси
            * Активные
            * Забаненные
            * Без проверки
        - Массовые действия:
            * Validate all
            * Delete inactive
    
    GET параметры:
        - status: фильтр по статусу
        - proxy_type: фильтр по типу
        - country: фильтр по стране
        - search: поиск по host или IP
    
    Context:
        - proxies: QuerySet прокси с аннотациями
        - stats: общая статистика
        - countries: список стран для фильтра
    
    Returns:
        HttpResponse: proxy_list.html
    """
    # Получаем параметры фильтрации
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('proxy_type', '')
    search_query = request.GET.get('q', '')
    
    # Базовый queryset
    proxies = TikTokProxy.objects.all().order_by('-id')
    
    # Применяем фильтры
    if status_filter:
        proxies = proxies.filter(status=status_filter)
    
    if type_filter:
        proxies = proxies.filter(proxy_type=type_filter)
    
    if search_query:
        proxies = proxies.filter(
            Q(host__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(external_ip__icontains=search_query)
        )
    
    # Статистика
    total_proxies = TikTokProxy.objects.count()
    active_proxies = TikTokProxy.objects.filter(status='active').count()
    inactive_proxies = TikTokProxy.objects.filter(status='inactive').count()
    banned_proxies = TikTokProxy.objects.filter(status='banned').count()
    
    context = {
        'proxies': proxies,
        'total_proxies': total_proxies,
        'active_proxies': active_proxies,
        'inactive_proxies': inactive_proxies,
        'banned_proxies': banned_proxies,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'search_query': search_query,
    }
    
    return render(request, 'tiktok_uploader/proxies/proxy_list.html', context)


@login_required
def create_proxy(request):
    """
    Создание нового прокси.
    
    POST:
        - host: IP или домен прокси
        - port: порт (1-65535)
        - username: имя пользователя (опционально)
        - password: пароль (опционально)
        - proxy_type: HTTP, HTTPS, или SOCKS5
        - ip_change_url: URL для смены IP (опционально)
        - notes: заметки
        - test_on_save: протестировать после создания (bool)
    
    Returns:
        GET: create_proxy.html с формой
        POST: redirect на proxy_list
    """
    if request.method == 'POST':
        form = TikTokProxyForm(request.POST)
        if form.is_valid():
            proxy = form.save(commit=False)
            test_on_save = form.cleaned_data.get('test_on_save', True)
            
            # Проверка на дубликат
            existing = TikTokProxy.objects.filter(
                host=proxy.host,
                port=proxy.port,
                username=proxy.username or '',
                password=proxy.password or ''
            ).exists()
            
            if existing:
                messages.error(request, f'Proxy {proxy.host}:{proxy.port} already exists!')
                return render(request, 'tiktok_uploader/proxies/create_proxy.html', {'form': form})
            
            # Тестирование прокси если требуется
            if test_on_save:
                is_valid, message, geo_info = validate_proxy(
                    host=proxy.host,
                    port=proxy.port,
                    username=proxy.username,
                    password=proxy.password,
                    timeout=15,
                    proxy_type=proxy.proxy_type
                )
                
                if not is_valid:
                    messages.warning(request, f'Proxy validation failed: {message}. Saved as inactive.')
                    proxy.status = 'inactive'
                    proxy.is_active = False
                else:
                    proxy.status = 'active'
                    proxy.is_active = True
                    
                    # Обновление геоданных
                    if geo_info:
                        if geo_info.get('country'):
                            proxy.country = geo_info['country']
                        if geo_info.get('city'):
                            proxy.city = geo_info['city']
                        if geo_info.get('external_ip'):
                            proxy.external_ip = geo_info['external_ip']
                    
                    messages.success(request, f'Proxy {proxy.host}:{proxy.port} created and validated successfully!')
                
                proxy.last_checked = timezone.now()
                proxy.last_verified = timezone.now()
            else:
                proxy.status = 'inactive'
                proxy.is_active = False
                messages.info(request, f'Proxy {proxy.host}:{proxy.port} created without testing.')
            
            proxy.save()
            return redirect('tiktok_uploader:proxy_list')
    else:
        form = TikTokProxyForm()
    
    context = {'form': form}
    return render(request, 'tiktok_uploader/proxies/create_proxy.html', context)


@login_required
def edit_proxy(request, proxy_id):
    """
    Редактирование прокси.
    
    Args:
        proxy_id (int): ID прокси
    
    Returns:
        GET: edit_proxy.html с формой
        POST: redirect на proxy_list
    """
    proxy = get_object_or_404(TikTokProxy, id=proxy_id)
    
    if request.method == 'POST':
        form = TikTokProxyForm(request.POST, instance=proxy)
        if form.is_valid():
            updated_proxy = form.save(commit=False)
            test_on_save = form.cleaned_data.get('test_on_save', False)
            
            # Проверка изменились ли критичные поля
            connection_changed = (
                proxy.host != updated_proxy.host or
                proxy.port != updated_proxy.port or
                proxy.username != updated_proxy.username or
                proxy.password != updated_proxy.password or
                proxy.proxy_type != updated_proxy.proxy_type
            )
            
            # Если изменились критичные поля или запрошено тестирование
            if (connection_changed or test_on_save):
                is_valid, message, geo_info = validate_proxy(
                    host=updated_proxy.host,
                    port=updated_proxy.port,
                    username=updated_proxy.username,
                    password=updated_proxy.password,
                    timeout=15,
                    proxy_type=updated_proxy.proxy_type
                )
                
                if not is_valid:
                    messages.warning(request, f'Proxy validation failed: {message}')
                    updated_proxy.status = 'inactive'
                    updated_proxy.is_active = False
                else:
                    updated_proxy.status = 'active'
                    updated_proxy.is_active = True
                    
                    # Обновление геоданных
                    if geo_info:
                        if geo_info.get('country'):
                            updated_proxy.country = geo_info['country']
                        if geo_info.get('city'):
                            updated_proxy.city = geo_info['city']
                        if geo_info.get('external_ip'):
                            updated_proxy.external_ip = geo_info['external_ip']
                    
                    messages.success(request, f'Proxy {updated_proxy.host}:{updated_proxy.port} updated and validated!')
                
                updated_proxy.last_checked = timezone.now()
                updated_proxy.last_verified = timezone.now()
            else:
                messages.success(request, f'Proxy {updated_proxy.host}:{updated_proxy.port} updated!')
            
            updated_proxy.save()
            return redirect('tiktok_uploader:proxy_list')
    else:
        form = TikTokProxyForm(instance=proxy)
    
    context = {
        'form': form,
        'proxy': proxy,
    }
    return render(request, 'tiktok_uploader/proxies/edit_proxy.html', context)


@login_required
def test_proxy(request, proxy_id):
    """
    Тестирование работоспособности прокси.
    
    Args:
        proxy_id (int): ID прокси
    
    Returns:
        redirect: на proxy_list с сообщением о результате
    """
    proxy = get_object_or_404(TikTokProxy, id=proxy_id)
    
    is_valid, message, geo_info = validate_proxy(
        host=proxy.host,
        port=proxy.port,
        username=proxy.username,
        password=proxy.password,
        timeout=15,
        proxy_type=proxy.proxy_type
    )
    
    proxy.last_checked = timezone.now()
    
    if is_valid:
        proxy.status = 'active'
        proxy.is_active = True
        proxy.last_verified = timezone.now()
        
        # Обновление геоданных
        if geo_info:
            if geo_info.get('country'):
                proxy.country = geo_info['country']
            if geo_info.get('city'):
                proxy.city = geo_info['city']
            if geo_info.get('external_ip'):
                proxy.external_ip = geo_info['external_ip']
        
        messages.success(request, f'✅ Proxy {proxy.host}:{proxy.port} is working! {message}')
    else:
        proxy.status = 'inactive'
        proxy.is_active = False
        messages.error(request, f'❌ Proxy {proxy.host}:{proxy.port} failed: {message}')
    
    proxy.save()
    return redirect('tiktok_uploader:proxy_list')


@login_required
def change_proxy_ip(request, proxy_id):
    """
    Смена IP-адреса прокси через API.
    
    Args:
        proxy_id (int): ID прокси
    
    Returns:
        redirect: на proxy_list
    """
    proxy = get_object_or_404(TikTokProxy, id=proxy_id)
    
    if not proxy.ip_change_url:
        messages.error(request, f'Proxy {proxy.host}:{proxy.port} does not have IP change URL configured.')
        return redirect('tiktok_uploader:proxy_list')
    
    old_ip = proxy.external_ip
    
    try:
        # Выполняем запрос на смену IP
        response = requests.get(proxy.ip_change_url, timeout=10)
        
        if response.status_code == 200:
            # Ждем немного для смены IP
            import time
            time.sleep(5)
            
            # Тестируем новый IP
            is_valid, message, geo_info = validate_proxy(
                host=proxy.host,
                port=proxy.port,
                username=proxy.username,
                password=proxy.password,
                timeout=15,
                proxy_type=proxy.proxy_type
            )
            
            if is_valid and geo_info.get('external_ip'):
                new_ip = geo_info['external_ip']
                proxy.external_ip = new_ip
                
                if geo_info.get('country'):
                    proxy.country = geo_info['country']
                if geo_info.get('city'):
                    proxy.city = geo_info['city']
                
                proxy.status = 'active'
                proxy.is_active = True
                proxy.last_verified = timezone.now()
                proxy.save()
                
                messages.success(request, f'✅ IP changed! {old_ip} → {new_ip}')
            else:
                messages.warning(request, f'IP change request sent, but proxy validation failed: {message}')
        else:
            messages.error(request, f'IP change request failed with status {response.status_code}')
            
    except Exception as e:
        messages.error(request, f'Error changing IP: {str(e)}')
    
    return redirect('tiktok_uploader:proxy_list')


@login_required
def delete_proxy(request, proxy_id):
    """
    Удаление прокси.
    
    Args:
        proxy_id (int): ID прокси
    
    Returns:
        redirect: на proxy_list
    """
    proxy = get_object_or_404(TikTokProxy, id=proxy_id)
    
    # Проверка привязанных аккаунтов
    accounts_count = proxy.accounts.count()
    active_accounts_count = proxy.active_accounts.count()
    
    if accounts_count > 0 or active_accounts_count > 0:
        messages.warning(
            request,
            f'Proxy {proxy.host}:{proxy.port} is used by {accounts_count} accounts. '
            f'Please reassign accounts before deleting.'
        )
    else:
        proxy_info = f'{proxy.host}:{proxy.port}'
        proxy.delete()
        messages.success(request, f'Proxy {proxy_info} deleted successfully!')
    
    return redirect('tiktok_uploader:proxy_list')


@login_required
def import_proxies(request):
    """
    Массовый импорт прокси из файла.
    
    Returns:
        GET: proxy_list.html с формой импорта
        POST: redirect на proxy_list с результатами
    """
    if request.method == 'POST':
        form = BulkProxyImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']
            import_format = form.cleaned_data['format']
            default_type = form.cleaned_data['default_type']
            test_on_import = form.cleaned_data['test_on_import']
            
            # Статистика
            stats = {
                'total': 0,
                'added': 0,
                'skipped': 0,
                'errors': 0
            }
            
            # Читаем файл
            try:
                content = file.read().decode('utf-8')
                lines = content.strip().split('\n')
                
                for line in lines:
                    line = line.strip()
                    
                    # Пропускаем пустые строки и комментарии
                    if not line or line.startswith('#'):
                        continue
                    
                    stats['total'] += 1
                    
                    # Парсим прокси
                    proxy_data = parse_proxy_string(line, default_type)
                    
                    if not proxy_data:
                        stats['errors'] += 1
                        continue
                    
                    # Проверка на дубликат
                    existing = TikTokProxy.objects.filter(
                        host=proxy_data['host'],
                        port=proxy_data['port'],
                        username=proxy_data['username'] or '',
                        password=proxy_data['password'] or ''
                    ).exists()
                    
                    if existing:
                        stats['skipped'] += 1
                        continue
                    
                    # Создаем прокси
                    proxy = TikTokProxy(
                        host=proxy_data['host'],
                        port=proxy_data['port'],
                        username=proxy_data['username'],
                        password=proxy_data['password'],
                        proxy_type=proxy_data['proxy_type'],
                        status='inactive',
                        is_active=False
                    )
                    
                    # Тестирование если требуется
                    if test_on_import:
                        is_valid, message, geo_info = validate_proxy(
                            host=proxy.host,
                            port=proxy.port,
                            username=proxy.username,
                            password=proxy.password,
                            timeout=15,
                            proxy_type=proxy.proxy_type
                        )
                        
                        if is_valid:
                            proxy.status = 'active'
                            proxy.is_active = True
                            
                            if geo_info:
                                proxy.country = geo_info.get('country')
                                proxy.city = geo_info.get('city')
                                proxy.external_ip = geo_info.get('external_ip')
                            
                            proxy.last_verified = timezone.now()
                        
                        proxy.last_checked = timezone.now()
                    
                    proxy.save()
                    stats['added'] += 1
                
                messages.success(
                    request,
                    f'✅ Import completed! Added: {stats["added"]}, Skipped: {stats["skipped"]}, '
                    f'Errors: {stats["errors"]} out of {stats["total"]} total.'
                )
                
            except Exception as e:
                messages.error(request, f'Error importing proxies: {str(e)}')
            
            return redirect('tiktok_uploader:proxy_list')
    
    # Для GET запроса показываем форму импорта
    form = BulkProxyImportForm()
    context = {
        'form': form,
    }
    return render(request, 'tiktok_uploader/proxies/import_proxies.html', context)


@login_required
def validate_all_proxies(request):
    """
    Валидация всех прокси.
    
    Returns:
        redirect: на proxy_list с результатами
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # Получаем все прокси или выбранные
    proxy_ids = request.POST.getlist('proxy_ids[]') if request.method == 'POST' else []
    
    if proxy_ids:
        proxies = TikTokProxy.objects.filter(id__in=proxy_ids)
    else:
        proxies = TikTokProxy.objects.all()
    
    if not proxies.exists():
        messages.warning(request, 'No proxies found to validate.')
        return redirect('tiktok_uploader:proxy_list')
    
    total = proxies.count()
    
    # Статистика
    stats = {
        'total': total,
        'active': 0,
        'inactive': 0,
        'errors': 0
    }
    
    def validate_single_proxy(proxy):
        """Валидация одного прокси."""
        try:
            is_valid, message, geo_info = validate_proxy(
                host=proxy.host,
                port=proxy.port,
                username=proxy.username,
                password=proxy.password,
                timeout=15,
                proxy_type=proxy.proxy_type
            )
            
            proxy.last_checked = timezone.now()
            
            if is_valid:
                proxy.status = 'active'
                proxy.is_active = True
                proxy.last_verified = timezone.now()
                
                # Обновление геоданных
                if geo_info:
                    if geo_info.get('country'):
                        proxy.country = geo_info['country']
                    if geo_info.get('city'):
                        proxy.city = geo_info['city']
                    if geo_info.get('external_ip'):
                        proxy.external_ip = geo_info['external_ip']
                
                proxy.save()
                return 'active'
            else:
                proxy.status = 'inactive'
                proxy.is_active = False
                proxy.save()
                return 'inactive'
                
        except Exception as e:
            return 'error'
    
    # Параллельная валидация (максимум 5 потоков одновременно)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(validate_single_proxy, proxy): proxy for proxy in proxies}
        
        for future in as_completed(futures):
            result = future.result()
            if result == 'active':
                stats['active'] += 1
            elif result == 'inactive':
                stats['inactive'] += 1
            else:
                stats['errors'] += 1
    
    # Сообщение с результатами
    messages.success(
        request,
        f'✅ Validation completed! '
        f'Active: {stats["active"]}, '
        f'Inactive: {stats["inactive"]}, '
        f'Errors: {stats["errors"]} '
        f'out of {stats["total"]} total.'
    )
    
    return redirect('tiktok_uploader:proxy_list')


@login_required
def cleanup_inactive_proxies(request):
    """
    Очистка неактивных прокси.
    
    POST:
        - days_inactive: удалить прокси неактивные более N дней
        - only_unused: удалять только не привязанные к аккаунтам (bool)
    
    Process:
        1. Находит прокси со статусом inactive или banned
        2. Фильтрует по последней проверке (> N дней назад)
        3. Опционально фильтрует не привязанные к аккаунтам
        4. Показывает список для подтверждения
        5. После подтверждения удаляет
        6. Логирует удаление
    
    Safety:
        - Требует подтверждение
        - Не удаляет прокси с активными задачами
        - Опционально оставляет прокси, привязанные к аккаунтам
    
    Returns:
        GET: cleanup_inactive_proxies.html с preview
        POST: redirect на proxy_list с результатами
    """
    pass


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _test_proxy_connection(proxy_dict, timeout=10):
    """
    Тестирует прокси подключение.
    
    Args:
        proxy_dict (dict): {type, host, port, user, pass}
        timeout (int): Timeout в секундах
    
    Returns:
        tuple: (success, external_ip, response_time_ms, error)
    """
    pass


def _check_tiktok_access(proxy_dict):
    """
    Проверяет доступность TikTok через прокси.
    
    Args:
        proxy_dict (dict): Данные прокси
    
    Returns:
        bool: True если TikTok доступен
    """
    pass


def _get_proxy_geolocation(ip_address):
    """
    Получает геолокацию IP через ip-api.com.
    
    Args:
        ip_address (str): IP адрес
    
    Returns:
        dict: {country, city, timezone} или None
    """
    pass


def _format_proxy_url(proxy_dict):
    """
    Форматирует прокси в URL строку.
    
    Args:
        proxy_dict (dict): {type, host, port, user, pass}
    
    Returns:
        str: "http://user:pass@host:port" или "socks5://host:port"
    """
    pass


def _parse_proxy_string(proxy_string, default_type='HTTP'):
    """
    Парсит строку прокси в словарь.
    
    Args:
        proxy_string (str): Строка прокси в разных форматах
        default_type (str): Тип по умолчанию
    
    Returns:
        dict: {type, host, port, username, password} или None если invalid
    
    Examples:
        "1.2.3.4:8080" → {type: HTTP, host: 1.2.3.4, port: 8080}
        "1.2.3.4:8080:user:pass" → ... + username, password
        "socks5://1.2.3.4:1080" → {type: SOCKS5, ...}
        "http://user:pass@1.2.3.4:8080" → полные данные
    """
    pass


@login_required
def bulk_delete_proxies(request):
    """
    Массовое удаление прокси.
    """
    if request.method == 'POST':
        proxy_ids = request.POST.getlist('proxy_ids')
        
        if not proxy_ids:
            messages.error(request, 'No proxies selected for deletion.')
            return redirect('tiktok_uploader:proxy_list')
        
        try:
            # Получаем прокси для удаления
            proxies = TikTokProxy.objects.filter(id__in=proxy_ids)
            count = proxies.count()
            
            if count == 0:
                messages.error(request, 'No proxies found to delete.')
                return redirect('tiktok_uploader:proxy_list')
            
            # Сохраняем host:port для сообщения
            proxy_names = [f"{p.host}:{p.port}" for p in proxies]
            
            # Удаляем прокси
            proxies.delete()
            
            # Формируем сообщение
            if count == 1:
                messages.success(request, f'Proxy {proxy_names[0]} has been deleted.')
            elif count <= 5:
                proxies_str = ', '.join(proxy_names)
                messages.success(request, f'{count} proxies deleted: {proxies_str}')
            else:
                messages.success(request, f'{count} proxies have been successfully deleted.')
            
        except Exception as e:
            messages.error(request, f'Error deleting proxies: {str(e)}')
    
    return redirect('tiktok_uploader:proxy_list')


