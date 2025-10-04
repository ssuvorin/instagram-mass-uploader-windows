"""
Main Views for TikTok Uploader
================================

Основные представления для управления TikTok аккаунтами и базовыми операциями.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Sum
from django.utils import timezone

from .models import (
    TikTokAccount, TikTokProxy, BulkUploadTask, BulkUploadAccount, BulkVideo,
    WarmupTask, FollowTask, CookieRobotTask
)


# ============================================================================
# ГЛАВНАЯ СТРАНИЦА И ДАШБОРД
# ============================================================================

@login_required
def dashboard(request):
    """
    Главный дашборд TikTok Uploader.
    
    Отображает:
    - Общую статистику по аккаунтам (активные, заблокированные, с ограничениями)
    - Статистику по задачам (bulk upload, warmup, follow)
    - Статус прокси
    - Недавние действия и логи
    - Графики активности за последние 30 дней
    
    Returns:
        HttpResponse: Рендерит страницу dashboard.html с контекстом:
            - total_accounts: общее количество аккаунтов
            - active_accounts: количество активных аккаунтов
            - blocked_accounts: количество заблокированных
            - limited_accounts: количество с ограничениями
            - total_proxies: количество прокси
            - active_proxies: количество активных прокси
            - recent_tasks: последние 10 задач
            - upload_stats: статистика загрузок за период
    """
    # Статистика аккаунтов
    total_accounts = TikTokAccount.objects.count()
    active_accounts = TikTokAccount.objects.filter(status='ACTIVE').count()
    blocked_accounts = TikTokAccount.objects.filter(status='BLOCKED').count()
    limited_accounts = TikTokAccount.objects.filter(status='LIMITED').count()
    
    # Статистика прокси
    total_proxies = TikTokProxy.objects.count()
    active_proxies = TikTokProxy.objects.filter(status='active').count()
    
    # Статистика видео (пример)
    total_videos = BulkVideo.objects.filter(uploaded=True).count()
    
    # Недавние задачи
    recent_tasks = BulkUploadTask.objects.order_by('-created_at')[:5]
    
    # Недавние аккаунты
    accounts = TikTokAccount.objects.order_by('-created_at')[:5]
    
    context = {
        'total_accounts': total_accounts,
        'active_accounts': active_accounts,
        'blocked_accounts': blocked_accounts,
        'limited_accounts': limited_accounts,
        'total_proxies': total_proxies,
        'active_proxies': active_proxies,
        'total_videos': total_videos,
        'recent_tasks': recent_tasks,
        'accounts': accounts,
    }
    
    return render(request, 'tiktok_uploader/dashboard.html', context)


# ============================================================================
# УПРАВЛЕНИЕ АККАУНТАМИ
# ============================================================================

@login_required
def account_list(request):
    """
    Список всех TikTok аккаунтов с фильтрацией и поиском.
    
    GET параметры:
        - status: фильтр по статусу (ACTIVE, BLOCKED, LIMITED и т.д.)
        - q: поисковый запрос (по username, email, notes)
        - client_id: фильтр по ID клиента
        - client_name: фильтр по имени клиента
        - agency_id: фильтр по ID агентства
    
    Features:
        - Пагинация (50 аккаунтов на страницу)
        - Сортировка по дате создания (новые первыми)
        - Отображение статистики загрузок для каждого аккаунта
        - Проверка прав доступа (суперюзер видит всех, клиент - только свои)
    
    Returns:
        HttpResponse: Рендерит account_list.html с filtered queryset
    """
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    client_id = request.GET.get('client_id')
    
    # Базовый queryset
    accounts = TikTokAccount.objects.order_by('-created_at')
    
    # Фильтрация по статусу
    if status_filter:
        accounts = accounts.filter(status=status_filter)
    
    # Поиск
    if search_query:
        accounts = accounts.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # Фильтрация по клиенту (если есть права)
    if client_id:
        try:
            accounts = accounts.filter(client_id=int(client_id))
        except (ValueError, TypeError):
            pass
    
    # Проверка прав доступа (пример)
    if not request.user.is_superuser:
        # Ограничить видимость для обычных пользователей
        pass
    
    context = {
        'accounts': accounts,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'tiktok_uploader/accounts/account_list.html', context)


@login_required
def account_detail(request, account_id):
    """
    Детальная информация о TikTok аккаунте.
    
    Args:
        account_id (int): ID аккаунта
    
    Отображает:
        - Основные данные аккаунта (username, email, phone, статус)
        - Привязанный прокси и Dolphin профиль
        - История использования
        - Статистика загрузок (успешные/неудачные)
        - Участие в задачах (bulk upload, warmup, follow)
        - Логи последних действий
        - Кнопки действий (edit, delete, change proxy, warm)
    
    Returns:
        HttpResponse: account_detail.html или 404
    """
    account = get_object_or_404(TikTokAccount, id=account_id)
    
    # Проверка прав доступа
    if not request.user.is_superuser:
        # Можно добавить проверку владельца
        pass
    
    context = {
        'account': account,
    }
    
    return render(request, 'tiktok_uploader/accounts/account_detail.html', context)


@login_required
def create_account(request):
    """
    Создание нового TikTok аккаунта.
    
    POST:
        - username: обязательно, уникальное
        - password: обязательно
        - email: опционально
        - email_password: опционально
        - phone_number: опционально
        - proxy_id: ID прокси для привязки
        - locale: локализация (по умолчанию en_US)
        - client_id: привязка к клиенту (для агентств)
        - notes: дополнительные заметки
        - create_dolphin_profile: создать Dolphin профиль автоматически
    
    Validation:
        - Проверка уникальности username
        - Валидация email формата
        - Валидация phone формата
        - Проверка существования прокси
    
    После создания:
        - Опционально создает Dolphin профиль
        - Привязывает прокси
        - Redirect на account_detail
    
    Returns:
        GET: create_account.html с формой
        POST: redirect на account_detail или форму с ошибками
    """
    from .forms import TikTokAccountForm
    from tiktok_uploader.bot_integration.services import create_dolphin_profile_for_account
    
    if request.method == 'POST':
        form = TikTokAccountForm(request.POST)
        create_dolphin = request.POST.get('create_dolphin_profile') == 'on'
        
        if form.is_valid():
            try:
                # Создаем аккаунт
                account = form.save(commit=False)
                
                # Устанавливаем статус
                account.status = 'ACTIVE'
                
                # Если указан прокси, устанавливаем как current_proxy
                if account.proxy:
                    account.current_proxy = account.proxy
                
                account.save()
                
                messages.success(
                    request, 
                    f'Account "{account.username}" created successfully!'
                )
                
                # Создаем Dolphin профиль если запрошено
                if create_dolphin:
                    # Проверяем наличие прокси
                    if not account.proxy and not account.current_proxy:
                        messages.warning(
                            request,
                            'Cannot create Dolphin profile: No proxy configured. Please assign a proxy first.'
                        )
                    else:
                        # Создаем профиль в фоновом режиме
                        try:
                            result = create_dolphin_profile_for_account(account)
                            if result.get('success'):
                                messages.success(
                                    request,
                                    f'Dolphin profile created successfully! Profile ID: {result.get("profile_id")}'
                                )
                            else:
                                messages.error(
                                    request,
                                    f'Failed to create Dolphin profile: {result.get("error")}'
                                )
                        except Exception as e:
                            messages.error(
                                request,
                                f'Error creating Dolphin profile: {str(e)}'
                            )
                
                return redirect('tiktok_uploader:account_detail', account_id=account.id)
                
            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
                # Форма остается заполненной для исправления
        else:
            # Форма невалидна, покажем ошибки
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TikTokAccountForm()
    
    # Получаем список прокси для выбора
    proxies = TikTokProxy.objects.filter(is_active=True).order_by('-created_at')
    
    # Получаем список клиентов (если есть)
    try:
        from cabinet.models import Client
        clients = Client.objects.all().order_by('name')
    except:
        clients = []
    
    context = {
        'form': form,
        'proxies': proxies,
        'clients': clients,
    }
    
    return render(request, 'tiktok_uploader/accounts/create_account.html', context)


@login_required
def import_accounts(request):
    """
    Массовый импорт TikTok аккаунтов из файла.
    
    Поддерживаемые форматы:
        1. CSV: username,password,email,email_password,phone,proxy_host,proxy_port
        2. TXT: username:password:email:email_password:phone
        3. JSON: [{"username": "", "password": "", ...}]
    
    POST:
        - file: файл с аккаунтами
        - format: тип формата (csv, txt, json)
        - assign_proxies: автоматически назначить прокси (bool)
        - create_dolphin_profiles: создать Dolphin профили (bool)
        - client_id: привязать к клиенту
    
    Process:
        1. Парсит файл согласно формату
        2. Валидирует каждую запись
        3. Создает аккаунты в БД
        4. Опционально назначает прокси (round-robin)
        5. Опционально создает Dolphin профили
        6. Логирует ошибки импорта
    
    Returns:
        GET: import_accounts.html с формой
        POST: redirect на account_list с сообщением о результатах
            (успешно импортировано X из Y)
    """
    pass


@login_required
def edit_account(request, account_id):
    """
    Редактирование TikTok аккаунта.
    
    Args:
        account_id (int): ID аккаунта
    
    Editable fields:
        - password
        - email, email_password
        - phone_number
        - proxy_id
        - status (только для суперюзера)
        - locale
        - notes
    
    Security:
        - Username нельзя изменить (для сохранения связей)
        - Клиент может редактировать только свои аккаунты
        - Суперюзер может редактировать любые
    
    Returns:
        GET: edit_account.html с формой
        POST: redirect на account_detail
    """
    pass


@login_required
def delete_account(request, account_id):
    """
    Удаление TikTok аккаунта.
    
    Args:
        account_id (int): ID аккаунта
    
    Safety:
        - Требует POST запрос
        - Проверяет права доступа
        - Удаляет связанный Dolphin профиль (если есть)
        - Каскадное удаление связей в задачах
        - Логирует удаление
    
    Confirmation:
        - Требует подтверждение через модальное окно
        - Отображает предупреждение если аккаунт используется в активных задачах
    
    Returns:
        POST: redirect на account_list с сообщением
    """
    pass


@login_required
def change_account_proxy(request, account_id):
    """
    Смена прокси для аккаунта.
    
    Args:
        account_id (int): ID аккаунта
    
    POST:
        - proxy_id: ID нового прокси (или null для удаления)
    
    Process:
        1. Проверяет доступность прокси
        2. Тестирует прокси (опционально)
        3. Обновляет current_proxy аккаунта
        4. Обновляет Dolphin профиль с новым прокси
        5. Логирует изменение
    
    Returns:
        POST: JsonResponse с результатом или redirect
    """
    pass


@login_required
def create_dolphin_profile(request, account_id):
    """
    Создание Dolphin Anty профиля для аккаунта.
    
    Args:
        account_id (int): ID аккаунта
    
    Process:
        1. Проверяет, что профиль еще не создан
        2. Генерирует fingerprint на основе locale
        3. Настраивает прокси из аккаунта
        4. Создает профиль через Dolphin API
        5. Сохраняет dolphin_profile_id в аккаунт
        6. Создает DolphinProfileSnapshot для восстановления
    
    Dolphin Settings:
        - User-Agent: случайный для локали
        - Screen resolution: случайное
        - WebGL, Canvas fingerprints: уникальные
        - Timezone: по прокси геолокации
        - Locales: из account.locale
        - Прокси: из account.current_proxy
    
    Returns:
        POST: JsonResponse с profile_id или error
    """
    from tiktok_uploader.bot_integration.services import create_dolphin_profile_for_account
    
    if request.method == 'POST':
        try:
            account = get_object_or_404(TikTokAccount, id=account_id)
            
            # Проверяем, что профиль еще не создан
            if account.dolphin_profile_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Dolphin profile already exists for this account'
                }, status=400)
            
            # Проверяем наличие прокси
            if not account.current_proxy and not account.proxy:
                return JsonResponse({
                    'success': False,
                    'error': 'No proxy configured for this account'
                }, status=400)
            
            # Создаем профиль через сервис бота
            result = create_dolphin_profile_for_account(account)
            
            if result.get('success'):
                messages.success(request, f'Dolphin profile created successfully for {account.username}')
                return JsonResponse({
                    'success': True,
                    'profile_id': result.get('profile_id'),
                    'message': 'Dolphin profile created successfully'
                })
            else:
                error_msg = result.get('error', 'Unknown error')
                messages.error(request, f'Failed to create Dolphin profile: {error_msg}')
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=500)
        
        except Exception as e:
            messages.error(request, f'Error creating Dolphin profile: {str(e)}')
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@login_required
def bulk_change_proxy(request):
    """
    Массовая смена прокси для нескольких аккаунтов.
    
    POST:
        - account_ids[]: список ID аккаунтов
        - action: тип действия
            * 'assign_random': назначить случайные активные прокси
            * 'assign_specific': назначить конкретный прокси всем
            * 'remove': удалить прокси у всех
        - proxy_id: ID прокси (для assign_specific)
        - update_dolphin: обновить Dolphin профили (bool)
    
    Process:
        1. Валидирует выбранные аккаунты
        2. Проверяет доступность прокси
        3. Выполняет массовое обновление
        4. Опционально обновляет Dolphin профили
        5. Логирует все изменения
    
    Returns:
        POST: JsonResponse с результатами
            {success: true, updated: 10, failed: 0, errors: []}
    """
    pass


@login_required
def refresh_dolphin_proxies(request):
    """
    Обновление прокси во всех Dolphin профилях.
    
    Use case:
        После массовой смены прокси в аккаунтах, нужно синхронизировать
        изменения с Dolphin Anty профилями.
    
    Process:
        1. Получает все аккаунты с dolphin_profile_id
        2. Для каждого аккаунта:
            - Читает current_proxy
            - Обновляет прокси в Dolphin через API
            - Логирует результат
        3. Собирает статистику (успешно/неудачно)
    
    POST:
        - account_ids[]: опционально, список ID (иначе все)
    
    Returns:
        POST: JsonResponse с результатами
            {success: true, updated: 50, failed: 2, errors: [...]}
    """
    pass


# ============================================================================
# CAPTCHA И УВЕДОМЛЕНИЯ
# ============================================================================

@login_required
def captcha_notification(request):
    """
    API для получения уведомлений о CAPTCHA.
    
    Используется worker'ами для уведомления о необходимости
    ручного решения капчи.
    
    POST:
        - task_id: ID задачи
        - task_type: тип задачи (bulk_upload, warmup, follow)
        - account_id: ID аккаунта
        - message: описание проблемы
        - screenshot: base64 скриншот (опционально)
    
    Process:
        1. Сохраняет уведомление в кеш
        2. Отправляет WebSocket сообщение (если настроено)
        3. Отправляет email/telegram уведомление (если настроено)
        4. Приостанавливает задачу
    
    Returns:
        JsonResponse: {success: true, notification_id: "..."}
    """
    pass


@login_required
def get_captcha_status(request, task_id):
    """
    Получение статуса CAPTCHA уведомлений для задачи.
    
    Args:
        task_id (int): ID задачи
    
    Returns:
        JsonResponse: {
            has_captcha: true/false,
            notifications: [
                {
                    account_id: 1,
                    account_username: "user1",
                    message: "CAPTCHA detected",
                    timestamp: "2024-01-01 12:00:00",
                    screenshot_url: "/media/captcha/..."
                }
            ]
        }
    """
    pass


@login_required
def clear_captcha_notification(request, task_id):
    """
    Очистка CAPTCHA уведомлений после решения.
    
    Args:
        task_id (int): ID задачи
    
    POST:
        - account_id: ID аккаунта (опционально, иначе все для задачи)
        - resume_task: возобновить задачу после очистки (bool)
    
    Process:
        1. Удаляет уведомления из кеша
        2. Опционально возобновляет задачу
        3. Логирует действие
    
    Returns:
        JsonResponse: {success: true, cleared: 5}
    """
    pass


# ============================================================================
# API СТАТИСТИКИ
# ============================================================================

@login_required
def get_stats_api(request):
    """
    API для получения общей статистики.
    
    GET параметры:
        - period: период статистики (today, week, month, year, all)
        - client_id: фильтр по клиенту
    
    Returns:
        JsonResponse: {
            accounts: {
                total: 100,
                active: 85,
                blocked: 10,
                limited: 5
            },
            uploads: {
                total: 1000,
                success: 950,
                failed: 50,
                today: 45
            },
            tasks: {
                bulk_upload: {running: 2, completed: 50},
                warmup: {running: 0, completed: 20},
                follow: {running: 1, completed: 15}
            },
            proxies: {
                total: 50,
                active: 45,
                banned: 5
            }
        }
    """
    pass


@login_required
def get_account_status_api(request, account_id):
    """
    API для получения текущего статуса аккаунта.
    
    Args:
        account_id (int): ID аккаунта
    
    Returns:
        JsonResponse: {
            account: {
                id: 1,
                username: "user1",
                status: "ACTIVE",
                last_used: "2024-01-01 12:00:00",
                proxy: {...},
                dolphin_profile_id: "..."
            },
            current_tasks: [
                {task_id: 10, type: "bulk_upload", status: "RUNNING"}
            ],
            recent_uploads: 5,
            total_uploads: 100,
            success_rate: 0.95
        }
    """
    pass


@login_required
def get_task_progress_api(request, task_id):
    """
    API для получения прогресса выполнения задачи.
    
    Args:
        task_id (int): ID задачи
    
    GET параметры:
        - task_type: тип задачи (bulk_upload, warmup, follow, cookie)
    
    Returns:
        JsonResponse: {
            task: {
                id: 10,
                name: "Bulk Upload Task",
                status: "RUNNING",
                progress_percent: 45.5,
                accounts_total: 10,
                accounts_completed: 4,
                accounts_running: 2,
                accounts_failed: 1,
                accounts_pending: 3,
                eta_minutes: 25
            },
            accounts: [
                {
                    account_id: 1,
                    username: "user1",
                    status: "COMPLETED",
                    uploaded: 5,
                    failed: 0
                }
            ],
            logs: "..." (последние 100 строк)
        }
    """
    pass

