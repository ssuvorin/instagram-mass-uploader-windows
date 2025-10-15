"""
Remote Bulk Upload Views for TikTok
====================================

Представления для массовой загрузки видео через удаленные серверы.
Новая архитектура: задачи отправляются на FastAPI серверы.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.files.storage import default_storage
from django.views.decorators.http import require_http_methods
from django.db import transaction
import base64
import json

from tiktok_uploader.models import (
    BulkUploadTask, BulkVideo, VideoCaption,
    TikTokServer, ServerTask, TikTokAccount
)
from tiktok_uploader.services.server_api_client import ServerAPIClient, ServerManager
from cabinet.models import Client


# ============================================================================
# СОЗДАНИЕ ЗАДАЧИ ДЛЯ УДАЛЕННОГО СЕРВЕРА
# ============================================================================

@login_required
def create_remote_bulk_upload(request):
    """
    Создание задачи загрузки для отправки на удаленный сервер.
    
    Новая логика:
    1. Пользователь выбирает клиента и тематику (вместо конкретных аккаунтов)
    2. Указывает количество аккаунтов
    3. Выбирает сервер (или авто-выбор)
    4. Добавляет видео и описания
    5. Задача отправляется на сервер целиком
    
    POST:
        - name: название задачи
        - client_id: ID клиента
        - tag: тематика (fim, memes и т.д.)
        - accounts_count: количество аккаунтов (вместо выбора конкретных!)
        - server_id: ID сервера (или "auto" для автовыбора)
        - cycles: количество циклов загрузки
        - cycle_timeout_minutes: задержка между циклами
        - delay_min_sec: минимальная задержка между загрузками
        - delay_max_sec: максимальная задержка
        - default_caption: описание по умолчанию
        - default_hashtags: хештеги через запятую
        - allow_comments, allow_duet, allow_stitch: настройки видео
    """
    if request.method == 'POST':
        try:
            # Получаем данные формы
            name = request.POST.get('name', '').strip()
            client_id = request.POST.get('client_id')
            tag = request.POST.get('tag', '').strip()
            accounts_count = int(request.POST.get('accounts_count', 5))
            server_id = request.POST.get('server_id')
            cycles = int(request.POST.get('cycles', 1))
            cycle_timeout_minutes = int(request.POST.get('cycle_timeout_minutes', 30))
            delay_min_sec = int(request.POST.get('delay_min_sec', 30))
            delay_max_sec = int(request.POST.get('delay_max_sec', 60))
            
            # Валидация
            if not name:
                messages.error(request, 'Название задачи обязательно')
                return redirect('tiktok_uploader:create_remote_bulk_upload')
            
            if not client_id:
                messages.error(request, 'Выберите клиента')
                return redirect('tiktok_uploader:create_remote_bulk_upload')
            
            if accounts_count < 1:
                messages.error(request, 'Количество аккаунтов должно быть минимум 1')
                return redirect('tiktok_uploader:create_remote_bulk_upload')
            
            # Получаем клиента
            try:
                client = Client.objects.get(id=client_id)
            except Client.DoesNotExist:
                messages.error(request, 'Клиент не найден')
                return redirect('tiktok_uploader:create_remote_bulk_upload')
            
            # Выбор сервера
            if server_id == 'auto':
                # Автоматический выбор лучшего сервера
                server = ServerManager.select_best_server()
                if not server:
                    messages.error(request, 'Нет доступных серверов')
                    return redirect('tiktok_uploader:create_remote_bulk_upload')
            else:
                try:
                    server = TikTokServer.objects.get(id=server_id, is_active=True)
                except TikTokServer.DoesNotExist:
                    messages.error(request, 'Сервер не найден')
                    return redirect('tiktok_uploader:create_remote_bulk_upload')
            
            # Проверяем доступность сервера
            if not server.is_available():
                messages.warning(request, f'Сервер {server.name} перегружен или недоступен. Задача будет добавлена в очередь.')
            
            # Создаем локальную задачу для отслеживания
            with transaction.atomic():
                task = BulkUploadTask.objects.create(
                    name=name,
                    status='PENDING',
                    delay_min_sec=delay_min_sec,
                    delay_max_sec=delay_max_sec,
                    default_caption=request.POST.get('default_caption', ''),
                    default_hashtags=request.POST.get('default_hashtags', ''),
                    default_privacy=request.POST.get('default_privacy', 'PUBLIC'),
                    allow_comments=request.POST.get('allow_comments') == 'on',
                    allow_duet=request.POST.get('allow_duet') == 'on',
                    allow_stitch=request.POST.get('allow_stitch') == 'on',
                )
                
                # Сохраняем параметры для отправки на сервер
                task_params = {
                    'client': client.name,
                    'tag': tag if tag else None,
                    'accounts_count': accounts_count,
                    'cycles': cycles,
                    'cycle_timeout_minutes': cycle_timeout_minutes,
                    'delay_min_sec': delay_min_sec,
                    'delay_max_sec': delay_max_sec,
                }
                
                # Создаем ServerTask для отслеживания
                server_task = ServerTask.objects.create(
                    server=server,
                    task_type='UPLOAD',
                    name=name,
                    status='PENDING',
                    bulk_upload_task=task,
                    parameters=task_params
                )
            
            messages.success(request, f'Задача "{name}" создана! Сервер: {server.name}')
            messages.info(request, 'Теперь добавьте видео для загрузки')
            return redirect('tiktok_uploader:add_remote_bulk_videos', task_id=task.id)
            
        except Exception as e:
            messages.error(request, f'Ошибка создания задачи: {str(e)}')
            return redirect('tiktok_uploader:create_remote_bulk_upload')
    
    # GET - показать форму
    # Получаем доступные серверы
    available_servers = TikTokServer.objects.filter(is_active=True).order_by('priority', 'name')
    
    # Получаем клиентов
    clients = Client.objects.all().order_by('name')
    
    # Получаем теги из модели AccountTag
    from tiktok_uploader.models import AccountTag
    tags = AccountTag.objects.all().order_by('name')
    
    context = {
        'available_servers': available_servers,
        'clients': clients,
        'tags': tags,
    }
    
    return render(request, 'tiktok_uploader/bulk_upload/create_remote.html', context)


@login_required
def add_remote_bulk_videos(request, task_id):
    """
    Добавление видео к задаче загрузки.
    
    Пользователь загружает видео файлы и добавляет описания.
    Видео сохраняются локально, потом будут отправлены на сервер.
    """
    task = get_object_or_404(BulkUploadTask, id=task_id)
    
    if request.method == 'POST':
        uploaded_files = request.FILES.getlist('videos')
        
        if not uploaded_files:
            messages.error(request, 'Выберите хотя бы одно видео')
            return redirect('tiktok_uploader:add_remote_bulk_videos', task_id=task_id)
        
        # Сохраняем видео
        for i, video_file in enumerate(uploaded_files):
            BulkVideo.objects.create(
                bulk_task=task,
                video_file=video_file,
                order=i
            )
        
        messages.success(request, f'Загружено {len(uploaded_files)} видео')
        return redirect('tiktok_uploader:add_remote_bulk_captions', task_id=task_id)
    
    context = {
        'task': task,
        'existing_videos': task.videos.order_by('order'),
    }
    
    return render(request, 'tiktok_uploader/bulk_upload/add_videos_remote.html', context)


@login_required
def add_remote_bulk_captions(request, task_id):
    """
    Добавление описаний к видео.
    
    Можно:
    1. Загрузить файл с описаниями (одно на строку)
    2. Вручную добавить описания для каждого видео
    """
    task = get_object_or_404(BulkUploadTask, id=task_id)
    
    if request.method == 'POST':
        # Вариант 1: Загрузка файла с описаниями
        if 'captions_file' in request.FILES:
            captions_file = request.FILES['captions_file']
            try:
                content = captions_file.read().decode('utf-8')
                captions_list = [line.strip() for line in content.split('\n') if line.strip()]
                
                # Создаем VideoCaption для каждого описания
                for i, caption_text in enumerate(captions_list):
                    VideoCaption.objects.create(
                        bulk_task=task,
                        text=caption_text,
                        order=i
                    )
                
                messages.success(request, f'Загружено {len(captions_list)} описаний')
            except Exception as e:
                messages.error(request, f'Ошибка загрузки файла: {str(e)}')
        
        # Вариант 2: Ручное добавление описаний
        elif 'manual_captions' in request.POST:
            manual_captions = request.POST.get('manual_captions', '').strip()
            if manual_captions:
                captions_list = [line.strip() for line in manual_captions.split('\n') if line.strip()]
                
                for i, caption_text in enumerate(captions_list):
                    VideoCaption.objects.create(
                        bulk_task=task,
                        text=caption_text,
                        order=i
                    )
                
                messages.success(request, f'Добавлено {len(captions_list)} описаний')
        
        return redirect('tiktok_uploader:remote_bulk_upload_review', task_id=task_id)
    
    context = {
        'task': task,
        'videos_count': task.videos.count(),
        'captions_count': task.captions.count(),
    }
    
    return render(request, 'tiktok_uploader/bulk_upload/add_captions_remote.html', context)


@login_required
def remote_bulk_upload_review(request, task_id):
    """
    Просмотр и подтверждение задачи перед отправкой на сервер.
    
    Показывает:
    - Параметры задачи
    - Список видео
    - Сервер назначения
    - Кнопку "Отправить на сервер"
    """
    task = get_object_or_404(BulkUploadTask, id=task_id)
    
    try:
        server_task = task.server_tasks.first()
        server = server_task.server if server_task else None
    except:
        server = None
    
    videos = task.videos.order_by('order')
    captions = task.captions.order_by('order')
    
    # Назначаем описания видео (если их поровну)
    if videos.count() == captions.count():
        for video, caption in zip(videos, captions):
            if not video.assigned_caption:
                caption.assigned_to = video
                caption.save()
    
    context = {
        'task': task,
        'server': server,
        'server_task': server_task,
        'videos': videos,
        'captions': captions,
        'videos_count': videos.count(),
    }
    
    return render(request, 'tiktok_uploader/bulk_upload/review_remote.html', context)


@login_required
@require_http_methods(["POST"])
def start_remote_bulk_upload(request, task_id):
    """
    Отправить задачу на удаленный сервер для выполнения.
    
    Процесс:
    1. Собрать все видео и метаданные
    2. Закодировать видео в base64
    3. Отправить POST /tasks/upload на сервер
    4. Получить remote_task_id
    5. Обновить ServerTask
    6. Перенаправить на страницу мониторинга
    """
    task = get_object_or_404(BulkUploadTask, id=task_id)
    
    try:
        server_task = task.server_tasks.first()
        if not server_task:
            messages.error(request, 'ServerTask не найдена')
            return redirect('tiktok_uploader:bulk_upload_list')
        
        server = server_task.server
        
        # Подготавливаем видео для отправки
        videos_data = []
        for video in task.videos.order_by('order'):
            # Читаем файл и кодируем в base64
            try:
                with video.video_file.open('rb') as f:
                    video_content = f.read()
                    video_base64 = base64.b64encode(video_content).decode('utf-8')
            except Exception as e:
                messages.error(request, f'Ошибка чтения видео {video.video_file.name}: {str(e)}')
                continue
            
            # Получаем описание для этого видео
            caption = video.caption or video.get_effective_caption()
            hashtags_text = video.hashtags or video.get_effective_hashtags()
            hashtags_list = [tag.strip().replace('#', '') for tag in hashtags_text.split(',') if tag.strip()]
            
            video_dict = {
                'filename': video.video_file.name,
                'file_base64': video_base64,
                'caption': caption,
                'hashtags': hashtags_list,
            }
            
            videos_data.append(video_dict)
        
        if not videos_data:
            messages.error(request, 'Нет видео для отправки')
            return redirect('tiktok_uploader:remote_bulk_upload_review', task_id=task_id)
        
        # Подготавливаем настройки
        default_settings = {
            'allow_comments': task.allow_comments,
            'allow_duet': task.allow_duet,
            'allow_stitch': task.allow_stitch,
            'privacy': task.default_privacy,
        }
        
        # Получаем параметры из ServerTask
        params = server_task.parameters
        
        # Отправляем на сервер через API
        client_api = ServerAPIClient(server)
        
        messages.info(request, f'Отправка задачи на сервер {server.name}...')
        
        success, result = client_api.create_upload_task(
            client=params['client'],
            accounts_count=params['accounts_count'],
            cycles=params['cycles'],
            videos_data=videos_data,
            tag=params.get('tag'),
            cycle_timeout_minutes=params.get('cycle_timeout_minutes', 30),
            delay_min_sec=params.get('delay_min_sec', 30),
            delay_max_sec=params.get('delay_max_sec', 60),
            default_settings=default_settings
        )
        
        client_api.close()
        
        if success:
            # Обновляем ServerTask
            server_task.remote_task_id = result.get('task_id')
            server_task.status = result.get('status', 'QUEUED')
            server_task.mark_as_started()
            
            # Обновляем локальную задачу
            task.status = 'RUNNING'
            task.started_at = timezone.now()
            task.save()
            
            messages.success(request, f'Задача успешно отправлена на сервер {server.name}!')
            messages.info(request, f'ID задачи на сервере: {server_task.remote_task_id}')
            messages.info(request, f'Статус: {server_task.status}')
            
            return redirect('tiktok_uploader:remote_task_detail', task_id=server_task.id)
        else:
            error_msg = result.get('error', 'Unknown error')
            messages.error(request, f'Ошибка отправки на сервер: {error_msg}')
            
            server_task.status = 'FAILED'
            server_task.error_message = error_msg
            server_task.save()
            
            return redirect('tiktok_uploader:remote_bulk_upload_review', task_id=task_id)
        
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('tiktok_uploader:remote_bulk_upload_review', task_id=task_id)


@login_required
def remote_task_detail(request, task_id):
    """
    Детальная информация о задаче на сервере.
    
    Показывает:
    - Статус выполнения
    - Прогресс
    - Логи
    - Ошибки
    - Кнопки управления (Stop, Delete)
    """
    server_task = get_object_or_404(ServerTask, id=task_id)
    
    # Обновляем статус с сервера
    if server_task.remote_task_id and server_task.status in ['QUEUED', 'RUNNING']:
        try:
            client = ServerAPIClient(server_task.server)
            success, status_data = client.get_task_status(server_task.remote_task_id)
            client.close()
            
            if success:
                server_task.status = status_data.get('status', server_task.status)
                server_task.progress = status_data.get('progress', 0)
                
                # Обновляем логи
                if 'logs' in status_data:
                    server_task.log = '\n'.join(status_data['logs'])
                
                # Если завершена
                if server_task.status == 'COMPLETED':
                    server_task.mark_as_completed(status_data.get('result'))
                elif server_task.status == 'FAILED':
                    server_task.mark_as_failed(status_data.get('errors', 'Unknown error'))
                else:
                    server_task.save()
                
                # Обновляем локальную задачу
                if server_task.bulk_upload_task:
                    server_task.bulk_upload_task.status = server_task.status
                    server_task.bulk_upload_task.save()
        except Exception as e:
            messages.warning(request, f'Не удалось обновить статус: {str(e)}')
    
    context = {
        'server_task': server_task,
        'task': server_task.bulk_upload_task,
        'server': server_task.server,
    }
    
    return render(request, 'tiktok_uploader/servers/task_detail.html', context)


@login_required
@require_http_methods(["POST"])
def stop_remote_task(request, task_id):
    """Остановить задачу на сервере"""
    server_task = get_object_or_404(ServerTask, id=task_id)
    
    if not server_task.remote_task_id:
        messages.error(request, 'Задача еще не отправлена на сервер')
        return redirect('tiktok_uploader:remote_task_detail', task_id=task_id)
    
    try:
        client = ServerAPIClient(server_task.server)
        success, result = client.stop_task(server_task.remote_task_id)
        client.close()
        
        if success:
            server_task.status = 'CANCELLED'
            server_task.save()
            messages.success(request, 'Задача остановлена')
        else:
            messages.error(request, f'Ошибка остановки: {result.get("error")}')
            
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
    
    return redirect('tiktok_uploader:remote_task_detail', task_id=task_id)

