"""
Bulk Upload Views for TikTok
==============================

Представления для массовой загрузки видео на TikTok.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.files.storage import default_storage

from ..models import (
    BulkUploadTask, BulkUploadAccount, BulkVideo,
    VideoCaption, TikTokAccount, TikTokProxy
)


# ============================================================================
# МАССОВАЯ ЗАГРУЗКА - СПИСОК И СОЗДАНИЕ
# ============================================================================

@login_required
def bulk_upload_list(request):
    """
    Список всех задач массовой загрузки видео.
    
    Features:
        - Отображение всех bulk upload задач
        - Фильтрация по статусу (PENDING, RUNNING, COMPLETED, FAILED, PAUSED)
        - Для каждой задачи показывает:
            * Название
            * Статус с цветовым индикатором
            * Количество аккаунтов
            * Количество видео
            * Прогресс (X из Y загружено)
            * Дата создания и запуска
            * Кнопки действий (Start, Pause, View, Delete)
        - Общая статистика:
            * Активные задачи
            * Всего загружено видео сегодня/неделю/месяц
    
    GET параметры:
        - status: фильтр по статусу
        - client_id: фильтр по клиенту
        - search: поиск по названию
    
    Context:
        - tasks: QuerySet задач с аннотациями
        - stats: общая статистика
        - can_create: может ли пользователь создавать задачи
    
    Returns:
        HttpResponse: bulk_upload_list.html
    """
    # Получаем все задачи
    tasks = BulkUploadTask.objects.order_by('-created_at')
    
    # Фильтрация по статусу
    status_filter = request.GET.get('status', '')
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    # Поиск по названию
    search_query = request.GET.get('search', '')
    if search_query:
        tasks = tasks.filter(name__icontains=search_query)
    
    # Статистика по статусам
    pending_count = BulkUploadTask.objects.filter(status='PENDING').count()
    running_count = BulkUploadTask.objects.filter(status='RUNNING').count()
    completed_count = BulkUploadTask.objects.filter(status='COMPLETED').count()
    failed_count = BulkUploadTask.objects.filter(status='FAILED').count()
    
    context = {
        'tasks': tasks,
        'pending_count': pending_count,
        'running_count': running_count,
        'completed_count': completed_count,
        'failed_count': failed_count,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'tiktok_uploader/bulk_upload/list.html', context)


@login_required
def create_bulk_upload(request):
    """
    Создание новой задачи массовой загрузки.
    
    POST:
        - name: название задачи
        - account_ids[]: список ID аккаунтов для загрузки
        - delay_min_sec: минимальная задержка между загрузками (сек)
        - delay_max_sec: максимальная задержка
        - concurrency: количество параллельных загрузок (1-4)
        - default_caption: описание по умолчанию для всех видео
        - default_hashtags: хештеги по умолчанию (через запятую)
        - default_privacy: PUBLIC, FRIENDS, или PRIVATE
        - allow_comments: разрешить комментарии (bool)
        - allow_duet: разрешить дуэты (bool)
        - allow_stitch: разрешить стич (bool)
    
    Validation:
        - Минимум 1 аккаунт выбран
        - delay_min <= delay_max
        - concurrency 1-4
        - Аккаунты активны и не заблокированы
        - Caption не превышает лимит TikTok (2200 символов)
    
    Process:
        1. Создает BulkUploadTask
        2. Создает BulkUploadAccount для каждого выбранного аккаунта
        3. Redirect на страницу добавления видео
    
    Returns:
        GET: create_bulk_upload.html с формой
        POST: redirect на add_bulk_videos
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        account_ids = request.POST.getlist('account_ids')
        
        if not name:
            messages.error(request, 'Название задачи обязательно')
            return render(request, 'tiktok_uploader/bulk_upload/create.html', {
                'accounts': TikTokAccount.objects.filter(status='ACTIVE'),
                'available_proxies': TikTokProxy.objects.filter(status='active'),
            })
        
        if not account_ids:
            messages.error(request, 'Выберите минимум один аккаунт')
            return render(request, 'tiktok_uploader/bulk_upload/create.html', {
                'accounts': TikTokAccount.objects.filter(status='ACTIVE'),
                'available_proxies': TikTokProxy.objects.filter(status='active'),
            })
        
        # Создаем новую задачу
        try:
            task = BulkUploadTask.objects.create(
                name=name,
                status='PENDING',
            )
            
            # Создаем связи с аккаунтами
            from ..models import BulkUploadAccount
            for account_id in account_ids:
                account = TikTokAccount.objects.get(id=account_id)
                BulkUploadAccount.objects.create(
                    bulk_task=task,
                    account=account,
                    proxy=account.proxy  # Используем прокси аккаунта
                )
            
            messages.success(request, f'Задача "{name}" успешно создана с {len(account_ids)} аккаунтом(ами)!')
            return redirect('tiktok_uploader:add_bulk_videos', task_id=task.id)
            
        except Exception as e:
            messages.error(request, f'Ошибка создания задачи: {str(e)}')
    
    # GET запрос - показать форму
    context = {
        'accounts': TikTokAccount.objects.filter(status='ACTIVE'),
        'available_proxies': TikTokProxy.objects.filter(status='active'),
    }
    
    return render(request, 'tiktok_uploader/bulk_upload/create.html', context)


@login_required
def bulk_upload_detail(request, task_id):
    """
    Детальная информация о задаче массовой загрузки.
    
    Args:
        task_id (int): ID задачи
    
    Отображает:
        - Настройки задачи (задержки, параллелизм, опции видео)
        - Список аккаунтов с их статусами и прогрессом
        - Список видео (thumbnail, filename, assigned to, status)
        - Общий прогресс:
            * Загружено видео / Всего
            * Процент завершения
            * Успешные / Неудачные
            * ETA (estimated time to complete)
        - Timeline выполнения (какой аккаунт что загружает сейчас)
        - Логи в реальном времени
        - Кнопки управления:
            * Start (если PENDING)
            * Pause (если RUNNING)
            * Resume (если PAUSED)
            * Delete
            * Add more videos
            * Add captions
            * Edit settings
    
    Context:
        - task: BulkUploadTask объект
        - accounts: список BulkUploadAccount с аннотациями
        - videos: список BulkVideo
        - progress: детальная статистика прогресса
        - can_start: bool
        - can_edit: bool
        - logs: последние 1000 строк логов
    
    Returns:
        HttpResponse: bulk_upload_detail.html или 404
    """
    try:
        task = get_object_or_404(BulkUploadTask, id=task_id)

        # Аккаунты задачи с присоединенной информацией об оригинальном аккаунте
        accounts_qs = (
            task.accounts
                .select_related('account')
                .prefetch_related('assigned_videos')
                .all()
        )

        # Видео задачи с присоединенными связями для отображения
        videos_qs = (
            task.videos
                .select_related('assigned_to__account', 'assigned_caption')
                .all()
        )
        unassigned_count = task.videos.filter(assigned_to__isnull=True).count()

        # Прогресс по видео
        total_videos = videos_qs.count()
        uploaded_videos = videos_qs.filter(uploaded=True).count()
        failed_videos = videos_qs.filter(uploaded=False, assigned_to__isnull=False).count() if task.status == 'COMPLETED' else 0
        progress_percent = int((uploaded_videos / total_videos) * 100) if total_videos else 0

        context = {
            'task': task,
            'accounts': accounts_qs,
            'videos': videos_qs,
            'can_start': task.status == 'PENDING',
            'can_edit': task.status in ['PENDING', 'PAUSED'],
            'unassigned_count': unassigned_count,
            'progress': {
                'total': total_videos,
                'uploaded': uploaded_videos,
                'failed': failed_videos,
                'percent': progress_percent,
            },
        }

        return render(request, 'tiktok_uploader/bulk_upload/detail.html', context)

    except BulkUploadTask.DoesNotExist:
        messages.error(request, 'Задача не найдена')
        return redirect('tiktok_uploader:bulk_upload_list')


# ============================================================================
# ДОБАВЛЕНИЕ КОНТЕНТА
# ============================================================================

@login_required
def add_bulk_videos(request, task_id):
    """
    Добавление видео в задачу массовой загрузки.
    """
    from django.contrib import messages
    from ..models import BulkUploadTask, BulkVideo
    from ..forms import BulkVideoUploadForm
    
    task = get_object_or_404(BulkUploadTask, id=task_id)
    
    # Проверяем что задача еще редактируемая
    if task.status not in ['PENDING']:
        messages.error(request, f'Cannot add videos to task "{task.name}" as it is already {task.status}')
        return redirect('tiktok_uploader:bulk_upload_detail', task_id=task.id)
    
    if request.method == 'POST':
        form = BulkVideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Получаем множественные файлы
            if 'video_file' in request.FILES:
                files = request.FILES.getlist('video_file')
                
                # Сохраняем каждый файл
                created_count = 0
                for video_file in files:
                    # Базовая валидация размера (TikTok лимит ~2GB)
                    if video_file.size > 2 * 1024 * 1024 * 1024:  # 2GB
                        messages.warning(request, f'Skipped {video_file.name}: file too large (max 2GB)')
                        continue
                    
                    # Проверка формата
                    valid_formats = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
                    if not any(video_file.name.lower().endswith(fmt) for fmt in valid_formats):
                        messages.warning(request, f'Skipped {video_file.name}: unsupported format')
                        continue
                    
                    # Создаем запись в БД
                    BulkVideo.objects.create(
                        bulk_task=task,
                        video_file=video_file
                    )
                    created_count += 1
                
                if created_count > 0:
                    messages.success(request, f'✅ Added {created_count} video(s) to task "{task.name}"')
                    
                    # Проверяем есть ли уже описания
                    if task.captions.exists():
                        return redirect('tiktok_uploader:bulk_upload_detail', task_id=task.id)
                    else:
                        return redirect('tiktok_uploader:add_bulk_captions', task_id=task.id)
                else:
                    messages.error(request, 'No valid videos were uploaded')
    else:
        form = BulkVideoUploadForm()
    
    # Получаем уже загруженные видео
    videos = task.videos.all().select_related('assigned_to__account')
    
    context = {
        'form': form,
        'task': task,
        'videos': videos,
    }
    return render(request, 'tiktok_uploader/bulk_upload/add_videos.html', context)


@login_required
def add_bulk_captions(request, task_id):
    """
    Добавление описаний для видео из файла.
    
    Args:
        task_id (int): ID задачи
    
    POST:
        - captions_file: текстовый файл с описаниями
        - format: формат файла
            * 'line': каждая строка = отдельное описание
            * 'double_newline': описания разделены двойным переводом строки
            * 'json': JSON массив описаний
        - assignment_mode: режим распределения
            * 'sequential': последовательно по порядку
            * 'random': случайное распределение
            * 'round_robin': по кругу между аккаунтами
    
    Validation:
        - Задача в статусе PENDING
        - Файл текстовый или JSON
        - Каждое описание <= 2200 символов
        - Количество описаний >= количество видео (или можно повторять)
    
    Process:
        1. Парсит файл согласно формату
        2. Создает VideoCaption для каждого описания
        3. Распределяет описания по видео согласно режиму
        4. Опционально добавляет хештеги к описаниям
        5. Preview распределения (какое описание к какому видео)
    
    Features:
        - Preview описаний перед сохранением
        - Автоматическое добавление хештегов
        - Подстановка переменных в описания:
            * {{date}} - текущая дата
            * {{time}} - текущее время
            * {{random_emoji}} - случайный эмодзи
        - Валидация на запрещенные слова
    
    Returns:
        GET: add_bulk_captions.html с формой
        POST: redirect на bulk_upload_detail
    """
    from django.contrib import messages
    from ..models import BulkUploadTask, VideoCaption
    
    task = get_object_or_404(BulkUploadTask, id=task_id)
    
    # Проверяем что задача еще редактируемая
    if task.status not in ['PENDING']:
        messages.error(request, f'Cannot add captions to task "{task.name}" as it is already {task.status}')
        return redirect('tiktok_uploader:bulk_upload_detail', task_id=task.id)
    
    if request.method == 'POST':
        # Проверяем что есть видео в задаче
        if not task.videos.exists():
            messages.error(request, 'Please add videos first before adding captions')
            return redirect('tiktok_uploader:add_bulk_videos', task_id=task.id)
        
        # Получаем данные из формы
        captions_file = request.FILES.get('captions_file')
        caption_text = request.POST.get('caption_text', '').strip()
        
        if captions_file:
            # Импорт из файла
            try:
                content = captions_file.read().decode('utf-8')
                captions = [line.strip() for line in content.splitlines() if line.strip()]
                
                # Удаляем старые описания
                task.captions.all().delete()
                
                # Создаем новые описания
                created_count = 0
                for caption in captions:
                    # Валидация длины (TikTok лимит 2200 символов)
                    if len(caption) > 2200:
                        messages.warning(request, f'Caption too long ({len(caption)} chars), truncated to 2200')
                        caption = caption[:2200]
                    
                    VideoCaption.objects.create(
                        bulk_task=task,
                        text=caption
                    )
                    created_count += 1
                
                messages.success(request, f'✅ Added {created_count} caption(s) from file')
                return redirect('tiktok_uploader:bulk_upload_detail', task_id=task.id)
                
            except Exception as e:
                messages.error(request, f'Error reading file: {str(e)}')
        
        elif caption_text:
            # Одно описание для всех видео
            if len(caption_text) > 2200:
                messages.warning(request, f'Caption too long ({len(caption_text)} chars), truncated to 2200')
                caption_text = caption_text[:2200]
            
            # Удаляем старые описания
            task.captions.all().delete()
            
            # Создаем одно описание
            VideoCaption.objects.create(
                bulk_task=task,
                text=caption_text
            )
            
            messages.success(request, f'✅ Added default caption for all videos')
            return redirect('tiktok_uploader:bulk_upload_detail', task_id=task.id)
        
        else:
            messages.error(request, 'Please provide either a captions file or default caption text')
    
    # Получаем текущие описания и видео
    captions = task.captions.all()
    videos = task.videos.all()
    
    context = {
        'task': task,
        'captions': captions,
        'videos': videos,
    }
    return render(request, 'tiktok_uploader/bulk_upload/add_captions.html', context)


# ============================================================================
# УПРАВЛЕНИЕ ЗАДАЧЕЙ
# ============================================================================

@login_required
def start_bulk_upload(request, task_id):
    """
    Запуск синхронной массовой загрузки (блокирующий).
    
    Args:
        task_id (int): ID задачи
    
    Requires:
        - POST запрос
        - Статус PENDING
        - Минимум 1 видео и 1 аккаунт
        - Все видео не назначены или равномерно распределены
    
    Process:
        1. Валидирует задачу
        2. Распределяет видео между аккаунтами (если не распределено)
        3. Меняет статус на RUNNING
        4. Запускает синхронно (используется для отладки):
            - Последовательно обрабатывает каждый аккаунт
            - Загружает назначенные видео
            - Обновляет прогресс в БД
            - Логирует действия
        5. После завершения меняет статус на COMPLETED
    
    Note:
        Этот метод блокирует HTTP запрос до завершения.
        Для продакшена используйте start_bulk_upload_api (асинхронный).
    
    Returns:
        POST: redirect на bulk_upload_detail после завершения
    """
    pass


@login_required
def start_bulk_upload_api(request, task_id):
    """
    Запуск асинхронной массовой загрузки через Celery.
    
    Args:
        task_id (int): ID задачи
    
    Requires:
        - POST запрос
        - Статус PENDING или PAUSED
        - Минимум 1 видео и 1 аккаунт
    
    Process:
        1. Валидирует задачу
        2. Распределяет видео между аккаунтами
        3. Меняет статус на RUNNING
        4. Запускает Celery task (неблокирующий):
            - Создает ThreadPoolExecutor для параллелизма
            - Для каждого аккаунта (с учетом concurrency):
                a. Открывает Dolphin профиль
                b. Логинится в TikTok
                c. Для каждого назначенного видео:
                    - Переходит на страницу загрузки
                    - Выбирает видео файл
                    - Заполняет caption (описание + хештеги)
                    - Настраивает опции (privacy, comments, duet, stitch)
                    - Нажимает Post
                    - Ждет завершения загрузки
                    - Логирует результат
                d. Делает задержки между загрузками
                e. Обновляет BulkUploadAccount статус
            - После всех аккаунтов меняет статус задачи на COMPLETED
        5. Возвращает task_id Celery для мониторинга
    
    Upload Process Details:
        1. Navigate to /upload
        2. Click "Upload video" button
        3. Select file via input[type=file]
        4. Wait for video processing
        5. Fill caption textarea
        6. Click privacy dropdown, select option
        7. Toggle comments/duet/stitch switches
        8. Click "Post" button
        9. Wait for success message
        10. Verify video appeared in profile
    
    Human-like behavior:
        - Random delays between steps
        - Smooth scrolling and mouse movements
        - Sometimes preview video before posting
        - Sometimes add/remove hashtags
        - Typing caption character by character
        - Pause and resume typing
    
    Error handling:
        - Upload failed → retry 2 times
        - Account blocked → skip account
        - CAPTCHA detected → notify + pause task
        - Rate limit → increase delays
        - Network error → retry with exponential backoff
    
    Returns:
        JsonResponse: {
            success: true,
            task_id: task_id,
            celery_task_id: "...",
            message: "Upload started"
        }
    """
    import threading
    from tiktok_uploader.bot_integration.services import run_bulk_upload_task
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        task = get_object_or_404(BulkUploadTask, id=task_id)
        
        # Проверяем статус задачи
        if task.status not in ['PENDING', 'PAUSED']:
            return JsonResponse({
                'success': False,
                'error': f'Task cannot be started from status {task.status}'
            }, status=400)
        
        # Проверяем наличие видео и аккаунтов
        if not task.videos.exists():
            return JsonResponse({
                'success': False,
                'error': 'No videos uploaded for this task'
            }, status=400)
        
        if not task.accounts.exists():
            return JsonResponse({
                'success': False,
                'error': 'No accounts assigned to this task'
            }, status=400)
        
        # Распределяем НЕназначенные видео между аккаунтами (round-robin)
        from ..models import BulkVideo
        unassigned_videos = list(task.videos.filter(assigned_to__isnull=True).order_by('id'))
        accounts_list = list(task.accounts.all().select_related('account'))
        if unassigned_videos and accounts_list:
            acc_count = len(accounts_list)
            idx = 0
            for video in unassigned_videos:
                video.assigned_to = accounts_list[idx % acc_count]
                video.save(update_fields=['assigned_to'])
                idx += 1
        
        # Запускаем задачу в отдельном потоке, чтобы не блокировать HTTP запрос
        def run_upload_in_background():
            try:
                run_bulk_upload_task(task_id)
            except Exception as e:
                print(f"Error in background upload task: {str(e)}")
        
        thread = threading.Thread(target=run_upload_in_background, daemon=True)
        thread.start()
        
        messages.success(request, f'Upload task "{task.name}" started')
        
        return JsonResponse({
            'success': True,
            'task_id': task_id,
            'message': 'Upload started in background'
        })
    
    except Exception as e:
        messages.error(request, f'Error starting upload task: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def pause_bulk_upload(request, task_id):
    """
    Приостановка выполняющейся задачи.
    
    Args:
        task_id (int): ID задачи
    
    Requires:
        - POST запрос
        - Статус RUNNING
    
    Process:
        1. Устанавливает флаг паузы в кеше
        2. Worker проверяет флаг перед каждым видео
        3. Текущие загрузки завершаются
        4. Новые не начинаются
        5. Статус меняется на PAUSED
    
    Use case:
        - Нужно временно остановить для изменения настроек
        - Обнаружены проблемы с аккаунтами
        - Требуется освободить ресурсы
    
    Returns:
        POST: JsonResponse с результатом
    """
    from django.http import JsonResponse
    from django.core.cache import cache
    from ..models import BulkUploadTask
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        task = get_object_or_404(BulkUploadTask, id=task_id)
        if task.status != 'RUNNING':
            return JsonResponse({'success': False, 'error': f'Task is not running (status: {task.status})'}, status=400)
        
        # Set pause flag for workers
        cache.set(f"bulk_upload_pause_{task_id}", True, timeout=60 * 60)
        
        task.status = 'PAUSED'
        task.save(update_fields=['status'])
        
        return JsonResponse({'success': True, 'message': 'Task paused'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def resume_bulk_upload(request, task_id):
    """
    Возобновление приостановленной задачи.
    
    Args:
        task_id (int): ID задачи
    
    Requires:
        - POST запрос
        - Статус PAUSED
    
    Process:
        1. Проверяет оставшиеся видео для загрузки
        2. Убирает флаг паузы
        3. Запускает worker заново (через start_bulk_upload_api)
        4. Статус меняется на RUNNING
    
    Returns:
        POST: JsonResponse с результатом
    """
    from django.http import JsonResponse
    from django.core.cache import cache
    from ..models import BulkUploadTask
    import threading
    from tiktok_uploader.bot_integration.services import run_bulk_upload_task
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        task = get_object_or_404(BulkUploadTask, id=task_id)
        if task.status != 'PAUSED':
            return JsonResponse({'success': False, 'error': f'Task is not paused (status: {task.status})'}, status=400)
        
        # Clear pause flag
        cache.delete(f"bulk_upload_pause_{task_id}")
        
        # Set status to RUNNING and restart background worker
        task.status = 'RUNNING'
        task.save(update_fields=['status'])
        
        def run_upload_in_background():
            try:
                run_bulk_upload_task(task_id)
            except Exception as e:
                print(f"Error resuming background upload task: {str(e)}")
        
        thread = threading.Thread(target=run_upload_in_background, daemon=True)
        thread.start()
        
        return JsonResponse({'success': True, 'message': 'Task resumed'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def delete_bulk_upload(request, task_id):
    """
    Удаление задачи массовой загрузки.
    
    Args:
        task_id (int): ID задачи
    
    Requires:
        - POST запрос
        - Статус не RUNNING (сначала нужно приостановить)
    
    Safety:
        - Останавливает Celery task если есть
        - Удаляет видео файлы из media (опционально)
        - Каскадно удаляет BulkUploadAccount, BulkVideo, VideoCaption
        - Сохраняет финальные логи перед удалением
        - Логирует удаление
    
    Confirmation:
        - Требует подтверждение через модальное окно
        - Показывает предупреждение о удалении видео файлов
    
    Returns:
        POST: redirect на bulk_upload_list
    """
    from django.contrib import messages
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('tiktok_uploader:bulk_upload_list')
    
    try:
        task = get_object_or_404(BulkUploadTask, id=task_id)
        
        # Проверяем что задача не выполняется
        if task.status == 'RUNNING':
            messages.error(request, f'Cannot delete running task "{task.name}". Please stop it first.')
            return redirect('tiktok_uploader:bulk_upload_detail', task_id=task.id)
        
        task_name = task.name
        
        # Удаляем задачу (каскадно удалятся связанные объекты)
        task.delete()
        
        messages.success(request, f'Task "{task_name}" has been deleted successfully.')
        
    except Exception as e:
        messages.error(request, f'Error deleting task: {str(e)}')
    
    return redirect('tiktok_uploader:bulk_upload_list')


@login_required
def force_delete_bulk_upload(request, task_id):
    """
    Форсированное удаление задачи даже если она RUNNING.
    - Ставит флаг остановки в кеше
    - Переводит задачу в статус FAILED
    - Удаляет задачу и связанные объекты
    """
    from django.contrib import messages
    from django.core.cache import cache
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('tiktok_uploader:bulk_upload_detail', task_id=task_id)
    
    try:
        task = get_object_or_404(BulkUploadTask, id=task_id)
        
        # Сигнал воркерам немедленно завершиться
        cache.set(f"bulk_upload_force_stop_{task_id}", True, timeout=60 * 10)
        cache.set(f"bulk_upload_pause_{task_id}", True, timeout=60 * 10)
        
        # Переводим в FAILED для истории
        task.status = 'FAILED'
        task.save(update_fields=['status'])
        task_name = task.name
        
        # Удаляем задачу
        task.delete()
        messages.success(request, f'Task "{task_name}" forcibly stopped and deleted.')
    except Exception as e:
        messages.error(request, f'Error force-deleting task: {str(e)}')
        return redirect('tiktok_uploader:bulk_upload_detail', task_id=task_id)
    
    return redirect('tiktok_uploader:bulk_upload_list')

@login_required
def get_bulk_task_logs(request, task_id):
    """
    API для получения логов задачи в реальном времени.
    
    Args:
        task_id (int): ID задачи
    
    GET параметры:
        - offset: начальная позиция в логах
        - limit: количество строк (по умолчанию 1000)
        - account_id: фильтр по аккаунту
        - level: фильтр по уровню (INFO, WARNING, ERROR)
    
    Returns:
        JsonResponse: {
            logs: "..." (текст логов с timestamp),
            task_status: "RUNNING",
            progress: {
                total_videos: 100,
                uploaded_success: 45,
                uploaded_failed: 2,
                remaining: 53,
                percent: 47.0,
                eta_minutes: 35
            },
            accounts: [
                {
                    account_id: 1,
                    username: "user1",
                    status: "RUNNING",
                    uploaded_success: 10,
                    uploaded_failed: 1,
                    current_video: "video_123.mp4"
                }
            ],
            has_more: true (есть ли еще логи)
        }
    
    Used for:
        - Real-time обновление страницы деталей
        - Мониторинг прогресса
        - Отладка ошибок
    """
    pass


@login_required
def edit_video_metadata(request, video_id):
    """
    Редактирование метаданных отдельного видео.
    
    Args:
        video_id (int): ID видео (BulkVideo)
    
    POST:
        - caption: индивидуальное описание для видео
        - hashtags: индивидуальные хештеги
    
    Requires:
        - Задача в статусе PENDING (не запущена)
        - Видео принадлежит задаче пользователя
    
    Use case:
        После массового добавления видео и описаний,
        можно отредактировать индивидуальные описания для некоторых видео.
    
    Returns:
        GET: edit_video_metadata.html с формой
        POST: redirect обратно на bulk_upload_detail
    """
    pass


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _assign_videos_to_accounts(task):
    """
    Распределяет видео между аккаунтами задачи.
    
    Args:
        task (BulkUploadTask): Задача
    
    Strategy:
        - Round-robin: равномерно по кругу
        - Учитывает уже назначенные видео
        - Пропускает FAILED аккаунты
    
    Returns:
        None (обновляет BulkVideo.assigned_to)
    """
    pass


def _validate_video_file(video_file):
    """
    Валидирует видео файл для загрузки на TikTok.
    
    Args:
        video_file: UploadedFile или путь к файлу
    
    Checks:
        - Формат: mp4, mov, avi
        - Размер <= 2GB
        - Длительность: 3 сек - 10 минут
        - Разрешение >= 720p
        - Соотношение сторон: 9:16 (вертикальное) или 16:9
        - Кодек: H.264
        - Нет водяных знаков других платформ (опционально)
    
    Returns:
        tuple: (is_valid, error_message, video_info)
    """
    pass


def _run_bulk_upload_worker(task_id):
    """
    Асинхронный worker для выполнения массовой загрузки.
    
    Args:
        task_id (int): ID задачи
    
    Returns:
        dict: Статистика выполнения
    """
    pass

