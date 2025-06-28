"""
Асинхронная версия bulk upload tasks для параллельной работы с несколькими аккаунтами
"""

import os
import asyncio
import aiofiles
import json
import time
import traceback
import logging
import random
import math
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
import tempfile
import shutil
import django
from django.db import transaction
from django.utils import timezone
from django.db import connection
from asgiref.sync import sync_to_async

# Import our modules
from .constants import (
    TimeConstants, InstagramTexts, BrowserConfig, Limits, TaskStatus, LogCategories, FilePaths,
    VerboseFilters, InstagramSelectors, APIConstants
)
from .selectors_config import InstagramSelectors as SelectorConfig, SelectorUtils
from .task_utils import (
    update_task_log, update_account_task, update_task_status, get_account_username,
    get_account_from_task, mark_account_as_used, get_task_with_accounts, 
    get_account_tasks, get_assigned_videos, get_all_task_videos, get_all_task_titles,
    handle_verification_error, handle_task_completion, handle_emergency_cleanup,
    process_browser_result, handle_account_task_error, handle_critical_task_error
)
from .account_utils import (
    get_account_details, get_proxy_details, get_account_proxy,
    get_account_dolphin_profile_id, save_dolphin_profile_id
)
from .browser_support import (
    cleanup_hanging_browser_processes, safely_close_all_windows,
    simulate_human_rest_behavior, simulate_normal_browsing_behavior,
    simulate_extended_human_rest_behavior
)
from .instagram_automation import InstagramNavigator, InstagramUploader, InstagramLoginHandler
from .browser_utils import BrowserManager, PageUtils, ErrorHandler, NetworkUtils, FileUtils, DebugUtils
from .models import BulkUploadTask, InstagramAccount, VideoFile, BulkUploadAccount, BulkVideo
from .bulk_tasks_playwright import (
    WebLogger, init_web_logger, get_web_logger, log_info, log_success, log_warning, log_error,
    get_2fa_code, get_email_verification_code, cleanup_temp_files, send_critical_notification,
    set_current_task_id, get_current_task_id
)

logger = logging.getLogger('uploader.async_bulk_tasks')

# Конфигурация для асинхронной обработки
class AsyncConfig:
    MAX_CONCURRENT_ACCOUNTS = 3  # Максимум аккаунтов одновременно
    MAX_CONCURRENT_VIDEOS = 1    # Максимум видео на аккаунт одновременно
    ACCOUNT_DELAY_MIN = 30       # Минимальная задержка между аккаунтами (сек)
    ACCOUNT_DELAY_MAX = 120      # Максимальная задержка между аккаунтами (сек)
    RETRY_ATTEMPTS = 2           # Количество попыток при ошибке
    HEALTH_CHECK_INTERVAL = 60   # Интервал проверки здоровья (сек)

# Асинхронные обертки для Django ORM
@sync_to_async
def get_task_async(task_id):
    """Асинхронно получить задачу"""
    return BulkUploadTask.objects.get(id=task_id)

@sync_to_async
def get_account_tasks_async(task):
    """Асинхронно получить задачи аккаунтов"""
    return list(task.accounts.all().order_by('account__status'))

@sync_to_async
def get_all_task_videos_async(task):
    """Асинхронно получить все видео задачи"""
    from .task_utils import get_all_task_videos
    return get_all_task_videos(task)

@sync_to_async
def get_all_task_titles_async(task):
    """Асинхронно получить все заголовки задачи"""
    from .task_utils import get_all_task_titles
    return get_all_task_titles(task)

@sync_to_async
def update_task_log_async(task, log_message):
    """Асинхронно обновить лог задачи"""
    from .task_utils import update_task_log
    update_task_log(task, log_message)

@sync_to_async
def update_task_status_async(task, status, log_message=""):
    """Асинхронно обновить статус задачи"""
    task.status = status
    if log_message:
        from .task_utils import update_task_log
        update_task_log(task, log_message)

@sync_to_async
def update_account_task_async(account_task, **kwargs):
    """Асинхронно обновить задачу аккаунта"""
    from .task_utils import update_account_task
    update_account_task(account_task, **kwargs)

@sync_to_async
def get_account_details_async(account, proxy):
    """Асинхронно получить детали аккаунта"""
    return get_account_details(account, proxy)

@sync_to_async
def get_account_proxy_async(account_task, account):
    """Асинхронно получить прокси аккаунта"""
    return get_account_proxy(account_task, account)

@sync_to_async
def get_account_from_task_async(account_task):
    """Асинхронно получить аккаунт из задачи"""
    return get_account_from_task(account_task)

@sync_to_async
def save_task_async(task):
    """Асинхронно сохранить задачу"""
    task.save()

@sync_to_async
def save_account_task_async(account_task):
    """Асинхронно сохранить задачу аккаунта"""
    account_task.save()

@sync_to_async
def get_timezone_now():
    """Асинхронно получить текущее время с timezone"""
    return timezone.now()

# Асинхронные обертки для Django cache
@sync_to_async
def cache_set_async(key, value, timeout=None):
    """Асинхронно установить значение в кеш"""
    from django.core.cache import cache
    cache.set(key, value, timeout)

@sync_to_async
def cache_get_async(key, default=None):
    """Асинхронно получить значение из кеша"""
    from django.core.cache import cache
    return cache.get(key, default)

# Асинхронная версия WebLogger
class AsyncWebLogger:
    """Асинхронная версия WebLogger для использования в async контексте"""
    
    def __init__(self, task_id, account_id=None):
        self.task_id = task_id
        self.account_id = account_id
        self.log_buffer = []
        self.critical_events = []
        
    async def log(self, level, message, category=None):
        """Асинхронно логировать сообщение"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Проверяем на verbose сообщения
        from .constants import VerboseFilters
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in VerboseFilters.PLAYWRIGHT_VERBOSE_KEYWORDS):
            return
        
        # Определяем критичность
        is_critical = self._is_critical_event(level, message, category)
        
        # Форматируем сообщение
        formatted_message = self._format_message(message, level, category)
        
        # Создаем запись лога
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': formatted_message,
            'category': category or 'GENERAL',
            'is_critical': is_critical,
            'task_id': self.task_id,
            'account_id': self.account_id
        }
        
        # Добавляем в буфер
        self.log_buffer.append(log_entry)
        
        # Отслеживаем критические события
        if is_critical:
            self.critical_events.append(log_entry)
        
        # Асинхронно сохраняем в кеш
        cache_key = f"task_logs_{self.task_id}"
        if self.account_id:
            cache_key += f"_account_{self.account_id}"
            
        existing_logs = await cache_get_async(cache_key, [])
        existing_logs.append(log_entry)
        
        # Ограничиваем количество записей
        from .constants import Limits
        if len(existing_logs) > Limits.MAX_LOG_ENTRIES:
            existing_logs = existing_logs[-Limits.MAX_LOG_ENTRIES:]
            
        await cache_set_async(cache_key, existing_logs, 3600)
        
        # Сохраняем критические события
        if is_critical:
            critical_cache_key = f"task_critical_{self.task_id}"
            existing_critical = await cache_get_async(critical_cache_key, [])
            existing_critical.append(log_entry)
            if len(existing_critical) > 50:
                existing_critical = existing_critical[-50:]
            await cache_set_async(critical_cache_key, existing_critical, 7200)
        
        # Выводим в консоль важные события
        if level in ['ERROR', 'WARNING', 'SUCCESS'] or is_critical:
            console_prefix = self._get_console_prefix(level, category)
            print(f"[{timestamp}] {console_prefix} {formatted_message}")
    
    def _is_critical_event(self, level, message, category):
        """Определить критичность события"""
        from .constants import LogCategories
        critical_keywords = [
            'verification', 'верификация', 'phone', 'телефон', 'captcha', 'human',
            'blocked', 'заблокирован', 'suspended', 'disabled', 'failed login',
            'error uploading', 'browser error', 'dolphin error'
        ]
        
        critical_categories = [
            LogCategories.VERIFICATION, LogCategories.CAPTCHA, 
            LogCategories.LOGIN, LogCategories.DOLPHIN
        ]
        
        return (
            level in ['ERROR', 'WARNING'] or 
            category in critical_categories or
            any(keyword in message.lower() for keyword in critical_keywords)
        )
    
    def _format_message(self, message, level, category):
        """Форматировать сообщение"""
        from .constants import LogCategories
        category_emojis = {
            LogCategories.VERIFICATION: '🔐',
            LogCategories.CAPTCHA: '🤖',
            LogCategories.LOGIN: '🔑',
            LogCategories.UPLOAD: '📤',
            LogCategories.DOLPHIN: '🐬',
            LogCategories.NAVIGATION: '🧭',
            LogCategories.HUMAN: '👤',
            LogCategories.CLEANUP: '🧹',
            LogCategories.DATABASE: '💾'
        }
        
        emoji = category_emojis.get(category, '📋')
        
        level_indicators = {
            'ERROR': '❌',
            'WARNING': '⚠️',
            'SUCCESS': '✅',
            'INFO': 'ℹ️'
        }
        
        level_emoji = level_indicators.get(level, 'ℹ️')
        
        return f"{level_emoji} {emoji} {message}"
    
    def _get_console_prefix(self, level, category):
        """Получить префикс для консоли"""
        prefixes = {
            'ERROR': '[🔴 ERROR]',
            'WARNING': '[🟡 WARNING]',
            'SUCCESS': '[🟢 SUCCESS]',
            'INFO': '[🔵 INFO]'
        }
        
        prefix = prefixes.get(level, '[INFO]')
        if category:
            prefix += f'[{category}]'
        return prefix

# Глобальный async logger
async_web_logger = None

async def init_async_web_logger(task_id, account_id=None):
    """Инициализировать асинхронный веб-логгер"""
    global async_web_logger
    async_web_logger = AsyncWebLogger(task_id, account_id)
    return async_web_logger

async def log_info_async(message, category=None):
    """Асинхронно логировать info сообщение"""
    if async_web_logger:
        await async_web_logger.log('INFO', message, category)
    else:
        print(f"[INFO] {message}")

async def log_success_async(message, category=None):
    """Асинхронно логировать success сообщение"""
    if async_web_logger:
        await async_web_logger.log('SUCCESS', message, category)
    else:
        print(f"[SUCCESS] {message}")

async def log_warning_async(message, category=None):
    """Асинхронно логировать warning сообщение"""
    if async_web_logger:
        await async_web_logger.log('WARNING', message, category)
    else:
        print(f"[WARNING] {message}")

async def log_error_async(message, category=None):
    """Асинхронно логировать error сообщение"""
    if async_web_logger:
        await async_web_logger.log('ERROR', message, category)
    else:
        print(f"[ERROR] {message}")

class AsyncAccountProcessor:
    """Класс для асинхронной обработки одного аккаунта"""
    
    def __init__(self, account_task, task, all_videos, all_titles, task_id):
        self.account_task = account_task
        self.task = task
        self.all_videos = all_videos
        self.all_titles = all_titles
        self.task_id = task_id
        self.logger = logger
        self.start_time = None
        self.end_time = None
        
    async def process(self):
        """Основной метод обработки аккаунта"""
        self.start_time = time.time()
        
        try:
            await log_info_async(f"🚀 [ASYNC_ACCOUNT] Starting async processing for account task {self.account_task.id}")
            
            # Получаем данные аккаунта асинхронно
            account = await get_account_from_task_async(self.account_task)
            proxy = await get_account_proxy_async(self.account_task, account)
            account_details = await get_account_details_async(account, proxy)
            
            # Подготавливаем видео для аккаунта
            videos_for_account = await self._prepare_videos_for_account()
            
            if not videos_for_account:
                await self._handle_no_videos()
                return 'failed', 0, 1
            
            # Подготавливаем файлы
            temp_files, video_files_to_upload = await self._prepare_video_files(videos_for_account)
            
            if not video_files_to_upload:
                await self._handle_no_files()
                return 'failed', 0, 1
            
            # Запускаем браузер асинхронно
            result = await self._run_browser_async(
                account_details, videos_for_account, video_files_to_upload
            )
            
            # Очищаем временные файлы
            await self._cleanup_temp_files(temp_files)
            
            self.end_time = time.time()
            processing_time = self.end_time - self.start_time
            
            await log_success_async(f"✅ [ASYNC_ACCOUNT] Account task {self.account_task.id} completed in {processing_time:.1f}s")
            
            return result
            
        except Exception as e:
            self.end_time = time.time()
            processing_time = (self.end_time - self.start_time) if self.start_time else 0
            
            await log_error_async(f"❌ [ASYNC_ACCOUNT] Account task {self.account_task.id} failed after {processing_time:.1f}s: {str(e)}")
            
            current_time = await get_timezone_now()
            await update_account_task_async(
                self.account_task,
                status=TaskStatus.FAILED,
                completed_at=current_time,
                log_message=f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ Async processing failed: {str(e)}\n"
            )
            
            return 'failed', 0, 1
    
    async def _prepare_videos_for_account(self):
        """Подготовить видео для аккаунта"""
        try:
            # ✅ ВАЖНО: Каждый аккаунт получает ВСЕ видео задачи, а не только назначенные ему
            # Это означает, что одно видео будет загружено на все аккаунты
            videos_for_account = list(self.all_videos)
            random.shuffle(videos_for_account)
            
            titles_for_account = list(self.all_titles) if self.all_titles else []
            if titles_for_account:
                random.shuffle(titles_for_account)
            
            # Назначаем случайные заголовки видео
            for i, video in enumerate(videos_for_account):
                if titles_for_account:
                    title_index = i % len(titles_for_account)
                    video.title_data = titles_for_account[title_index]
                else:
                    video.title_data = None
            
            await log_info_async(f"📹 [ASYNC_PREP] Prepared {len(videos_for_account)} videos for account task {self.account_task.id}")
            return videos_for_account
            
        except Exception as e:
            await log_error_async(f"❌ [ASYNC_PREP] Error preparing videos: {str(e)}")
            return []
    
    async def _prepare_video_files(self, videos_for_account):
        """Асинхронно подготовить файлы видео"""
        temp_files = []
        video_files_to_upload = []
        
        try:
            for video in videos_for_account:
                video_filename = os.path.basename(video.video_file.name)
                await log_info_async(f"📁 [ASYNC_FILES] Preparing video file: {video_filename}")
                
                # Создаем временный файл асинхронно
                temp_file_path = await self._create_temp_file_async(video, video_filename)
                
                if temp_file_path:
                    temp_files.append(temp_file_path)
                    video_files_to_upload.append(temp_file_path)
                    
                    await update_account_task_async(
                        self.account_task,
                        log_message=f"[{(await get_timezone_now()).strftime('%Y-%m-%d %H:%M:%S')}] ✅ Prepared video file: {video_filename}\n"
                    )
                else:
                    await log_error_async(f"❌ [ASYNC_FILES] Failed to prepare video file: {video_filename}")
            
            await log_success_async(f"✅ [ASYNC_FILES] Prepared {len(video_files_to_upload)} video files")
            return temp_files, video_files_to_upload
            
        except Exception as e:
            await log_error_async(f"❌ [ASYNC_FILES] Error preparing video files: {str(e)}")
            # Очищаем уже созданные файлы при ошибке
            await self._cleanup_temp_files(temp_files)
            return [], []
    
    async def _create_temp_file_async(self, video, video_filename):
        """Асинхронно создать временный файл"""
        try:
            # Создаем временный файл
            temp_file = NamedTemporaryFile(delete=False, suffix=f"_{video_filename}")
            temp_file_path = temp_file.name
            
            # Асинхронно записываем данные
            async with aiofiles.open(temp_file_path, 'wb') as f:
                # Читаем файл чанками для экономии памяти
                for chunk in video.video_file.chunks():
                    await f.write(chunk)
            
            await log_info_async(f"📁 [ASYNC_FILES] Created temp file: {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            await log_error_async(f"❌ [ASYNC_FILES] Error creating temp file for {video_filename}: {str(e)}")
            return None
    
    async def _cleanup_temp_files(self, temp_files):
        """Асинхронно очистить временные файлы"""
        try:
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                        await log_info_async(f"🗑️ [ASYNC_CLEANUP] Removed temp file: {temp_file}")
                except Exception as e:
                    await log_warning_async(f"⚠️ [ASYNC_CLEANUP] Could not remove temp file {temp_file}: {str(e)}")
        except Exception as e:
            await log_error_async(f"❌ [ASYNC_CLEANUP] Error during cleanup: {str(e)}")
    
    async def _run_browser_async(self, account_details, videos, video_files_to_upload):
        """Асинхронно запустить браузер"""
        try:
            await log_info_async(f"🌐 [ASYNC_BROWSER] Starting browser for account: {account_details['username']}")
            
            # Создаем задачу для браузера
            browser_task = asyncio.create_task(
                self._browser_worker(account_details, videos, video_files_to_upload)
            )
            
            # Ждем результат с таймаутом
            result = await asyncio.wait_for(browser_task, timeout=TimeConstants.BROWSER_TIMEOUT)
            
            await log_success_async(f"✅ [ASYNC_BROWSER] Browser task completed for account: {account_details['username']}")
            return result
            
        except asyncio.TimeoutError:
            await log_error_async(f"⏰ [ASYNC_BROWSER] Browser task timed out for account: {account_details['username']}")
            return 'timeout', 0, 1
        except Exception as e:
            await log_error_async(f"❌ [ASYNC_BROWSER] Browser task failed for account: {account_details['username']}: {str(e)}")
            return 'failed', 0, 1
    
    async def _browser_worker(self, account_details, videos, video_files_to_upload):
        """Воркер для работы с браузером"""
        try:
            # Запускаем синхронную функцию браузера в executor
            loop = asyncio.get_event_loop()
            
            # Создаем результат очередь для совместимости
            import queue
            result_queue = queue.Queue()
            
            # Запускаем браузер в отдельном потоке
            from .bulk_tasks_playwright import run_dolphin_browser
            
            await loop.run_in_executor(
                None,
                run_dolphin_browser,
                account_details,
                videos,
                video_files_to_upload,
                result_queue,
                self.task_id,
                self.account_task.id
            )
            
            # Получаем результат
            if not result_queue.empty():
                result = result_queue.get()
                return self._process_browser_result(result)
            else:
                return 'failed', 0, 1
                
        except Exception as e:
            await log_error_async(f"❌ [ASYNC_BROWSER_WORKER] Error in browser worker: {str(e)}")
            return 'failed', 0, 1
    
    def _process_browser_result(self, result):
        """Обработать результат браузера"""
        try:
            if isinstance(result, tuple) and len(result) >= 2:
                result_type, message = result[:2]
                
                if result_type == "SUCCESS":
                    return 'success', 1, 0
                elif result_type in ["LOGIN_ERROR", "VERIFICATION_ERROR", "DOLPHIN_ERROR"]:
                    return result_type.lower(), 0, 1
                else:
                    return 'failed', 0, 1
            else:
                return 'failed', 0, 1
                
        except Exception as e:
            print(f"❌ [ASYNC_RESULT] Error processing browser result: {str(e)}")
            return 'failed', 0, 1
    
    async def _handle_no_videos(self):
        """Обработать случай отсутствия видео"""
        current_time = await get_timezone_now()
        timestamp = current_time.strftime('%Y-%m-%d %H:%M:%S')
        await update_account_task_async(
            self.account_task,
            status=TaskStatus.FAILED,
            completed_at=current_time,
            log_message=f"[{timestamp}] ❌ No videos to process\n"
        )
    
    async def _handle_no_files(self):
        """Обработать случай отсутствия файлов"""
        current_time = await get_timezone_now()
        timestamp = current_time.strftime('%Y-%m-%d %H:%M:%S')
        await update_account_task_async(
            self.account_task,
            status=TaskStatus.FAILED,
            completed_at=current_time,
            log_message=f"[{timestamp}] ❌ No valid video files to upload\n"
        )

class AsyncTaskCoordinator:
    """Координатор для асинхронного выполнения задач"""
    
    def __init__(self, task_id):
        self.task_id = task_id
        self.task = None
        self.account_semaphore = asyncio.Semaphore(AsyncConfig.MAX_CONCURRENT_ACCOUNTS)
        self.results = {}
        self.start_time = None
        self.end_time = None
        
    async def run(self):
        """Основной метод запуска асинхронной задачи"""
        self.start_time = time.time()
        
        try:
            # Устанавливаем текущий ID задачи
            set_current_task_id(self.task_id)
            
            # Получаем задачу
            self.task = await get_task_async(self.task_id)
            
            # Инициализируем асинхронный веб-логгер
            await init_async_web_logger(self.task_id)
            
            # Обновляем статус задачи
            current_time = await get_timezone_now()
            timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
            await update_task_status_async(
                self.task, 
                TaskStatus.RUNNING, 
                f"[{timestamp}] 🚀 Starting ASYNC bulk upload task '{self.task.name}'\n"
            )
            
            await log_info_async(f"🎬 [ASYNC_COORDINATOR] Starting async task '{self.task.name}' with {await self._get_account_count()} accounts")
            
            # Получаем все данные
            account_tasks = await get_account_tasks_async(self.task)
            all_videos = await get_all_task_videos_async(self.task)  # ✅ ВСЕ видео - будут переданы каждому аккаунту
            all_titles = await get_all_task_titles_async(self.task)
            
            if not all_videos:
                error_msg = "No videos found for this task"
                await log_error_async(error_msg)
                await update_task_status_async(self.task, TaskStatus.FAILED, f"[{timestamp}] ❌ {error_msg}\n")
                return False
            
            await log_info_async(f"📹 [ASYNC_COORDINATOR] Found {len(all_videos)} videos and {len(all_titles)} titles")
            
            # Создаем задачи для всех аккаунтов
            tasks = []
            for account_task in account_tasks:
                processor = AsyncAccountProcessor(account_task, self.task, all_videos, all_titles, self.task_id)
                task_coroutine = self._process_account_with_semaphore(processor, account_task)
                tasks.append(task_coroutine)
            
            # Запускаем все задачи параллельно
            await log_info_async(f"🚀 [ASYNC_COORDINATOR] Starting {len(tasks)} account tasks in parallel")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            await self._process_results(results, account_tasks)
            
            # Завершаем задачу
            await self._finalize_task()
            
            self.end_time = time.time()
            total_time = self.end_time - self.start_time
            
            await log_success_async(f"✅ [ASYNC_COORDINATOR] Async task completed in {total_time:.1f}s")
            return True
            
        except Exception as e:
            self.end_time = time.time()
            total_time = (self.end_time - self.start_time) if self.start_time else 0
            
            await log_error_async(f"❌ [ASYNC_COORDINATOR] Async task failed after {total_time:.1f}s: {str(e)}")
            
            if self.task:
                current_time = await get_timezone_now()
                await update_task_status_async(
                    self.task, 
                    TaskStatus.FAILED, 
                    f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ Async task failed: {str(e)}\n"
                )
            
            return False
    
    async def _process_account_with_semaphore(self, processor, account_task):
        """Обработать аккаунт с семафором для ограничения параллельности"""
        async with self.account_semaphore:
            try:
                # Добавляем случайную задержку для распределения нагрузки
                delay = random.uniform(0, AsyncConfig.ACCOUNT_DELAY_MIN)
                await log_info_async(f"⏳ [ASYNC_ACCOUNT] Waiting {delay:.1f}s before processing account task {account_task.id}")
                await asyncio.sleep(delay)
                
                # Обрабатываем аккаунт
                result = await processor.process()
                
                # Добавляем задержку после обработки
                post_delay = random.uniform(AsyncConfig.ACCOUNT_DELAY_MIN, AsyncConfig.ACCOUNT_DELAY_MAX)
                await log_info_async(f"⏳ [ASYNC_ACCOUNT] Waiting {post_delay:.1f}s after processing account task {account_task.id}")
                await asyncio.sleep(post_delay)
                
                return result
                
            except Exception as e:
                await log_error_async(f"❌ [ASYNC_ACCOUNT] Error processing account task {account_task.id}: {str(e)}")
                return 'exception', 0, 1
    
    async def _process_results(self, results, account_tasks):
        """Обработать результаты выполнения"""
        successful_accounts = 0
        failed_accounts = 0
        verification_required_accounts = 0
        
        for i, result in enumerate(results):
            account_task = account_tasks[i]
            
            try:
                if isinstance(result, Exception):
                    await log_error_async(f"❌ [ASYNC_RESULT] Account task {account_task.id} raised exception: {str(result)}")
                    failed_accounts += 1
                elif isinstance(result, tuple) and len(result) >= 3:
                    result_type, completed, failed = result
                    
                    if result_type == 'success':
                        successful_accounts += 1
                        await log_success_async(f"✅ [ASYNC_RESULT] Account task {account_task.id} completed successfully")
                    elif result_type in ['verification_error', 'phone_verification_required', 'human_verification_required']:
                        verification_required_accounts += 1
                        await log_warning_async(f"⚠️ [ASYNC_RESULT] Account task {account_task.id} requires verification")
                    else:
                        failed_accounts += 1
                        await log_error_async(f"❌ [ASYNC_RESULT] Account task {account_task.id} failed: {result_type}")
                else:
                    failed_accounts += 1
                    await log_error_async(f"❌ [ASYNC_RESULT] Account task {account_task.id} returned invalid result: {result}")
                    
            except Exception as e:
                failed_accounts += 1
                await log_error_async(f"❌ [ASYNC_RESULT] Error processing result for account task {account_task.id}: {str(e)}")
        
        # Логируем общую статистику
        total_accounts = len(account_tasks)
        await log_info_async(f"📊 [ASYNC_STATS] Task completed - Total: {total_accounts}, Success: {successful_accounts}, Failed: {failed_accounts}, Verification: {verification_required_accounts}")
        
        # Сохраняем статистику
        self.results = {
            'total': total_accounts,
            'successful': successful_accounts,
            'failed': failed_accounts,
            'verification_required': verification_required_accounts
        }
    
    async def _finalize_task(self):
        """Финализировать задачу"""
        try:
            total = self.results.get('total', 0)
            successful = self.results.get('successful', 0)
            failed = self.results.get('failed', 0)
            verification_required = self.results.get('verification_required', 0)
            
            # Определяем финальный статус
            if successful == total:
                final_status = TaskStatus.COMPLETED
                status_msg = "All accounts processed successfully"
            elif successful > 0:
                final_status = TaskStatus.PARTIALLY_COMPLETED
                status_msg = f"Partially completed: {successful}/{total} accounts successful"
            else:
                final_status = TaskStatus.FAILED
                status_msg = "All accounts failed"
            
            # Создаем финальное сообщение
            current_time = await get_timezone_now()
            timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
            final_message = (
                f"[{timestamp}] 🏁 ASYNC Task completed\n"
                f"📊 Statistics:\n"
                f"  • Total accounts: {total}\n"
                f"  • Successful: {successful}\n"
                f"  • Failed: {failed}\n"
                f"  • Verification required: {verification_required}\n"
                f"  • Success rate: {(successful/total*100):.1f}%\n"
                f"  • Status: {status_msg}\n"
            )
            
            # Обновляем статус задачи
            await update_task_status_async(self.task, final_status, final_message)
            
            await log_success_async(f"✅ [ASYNC_FINALIZE] Task finalized with status: {final_status}")
            
        except Exception as e:
            await log_error_async(f"❌ [ASYNC_FINALIZE] Error finalizing task: {str(e)}")
    
    async def _get_account_count(self):
        """Получить количество аккаунтов"""
        try:
            account_tasks = await get_account_tasks_async(self.task)
            return len(account_tasks)
        except:
            return 0

# Основная функция для запуска асинхронной задачи
async def run_async_bulk_upload_task(task_id):
    """
    Асинхронная версия bulk upload task для параллельной обработки аккаунтов
    
    Преимущества:
    - Параллельная обработка нескольких аккаунтов
    - Лучшее использование ресурсов
    - Контроль параллельности через семафоры
    - Асинхронная работа с файлами
    - Улучшенная обработка ошибок
    """
    try:
        await log_info_async(f"🚀 [ASYNC_MAIN] Starting async bulk upload task {task_id}")
        
        coordinator = AsyncTaskCoordinator(task_id)
        result = await coordinator.run()
        
        if result:
            await log_success_async(f"✅ [ASYNC_MAIN] Async bulk upload task {task_id} completed successfully")
        else:
            await log_error_async(f"❌ [ASYNC_MAIN] Async bulk upload task {task_id} failed")
        
        return result
        
    except Exception as e:
        await log_error_async(f"❌ [ASYNC_MAIN] Critical error in async bulk upload task {task_id}: {str(e)}")
        await log_error_async(f"❌ [ASYNC_MAIN] Traceback: {traceback.format_exc()}")
        return False

# Функция-обертка для запуска из синхронного кода
def run_async_bulk_upload_task_sync(task_id):
    """
    Синхронная обертка для запуска асинхронной задачи
    Используется для совместимости с существующим кодом
    """
    try:
        # Создаем новый event loop если его нет
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Если loop уже запущен, создаем новый
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, run_async_bulk_upload_task(task_id))
                    return future.result()
            else:
                return loop.run_until_complete(run_async_bulk_upload_task(task_id))
        except RuntimeError:
            # Если нет активного loop, создаем новый
            return asyncio.run(run_async_bulk_upload_task(task_id))
            
    except Exception as e:
        print(f"❌ [ASYNC_SYNC_WRAPPER] Error running async task {task_id}: {str(e)}")
        return False

# Конфигурационные функции
def set_async_config(**kwargs):
    """Установить конфигурацию для асинхронной обработки"""
    for key, value in kwargs.items():
        if hasattr(AsyncConfig, key.upper()):
            setattr(AsyncConfig, key.upper(), value)
            print(f"🔧 [ASYNC_CONFIG] Set {key.upper()} = {value}")

def get_async_config():
    """Получить текущую конфигурацию"""
    return {
        'max_concurrent_accounts': AsyncConfig.MAX_CONCURRENT_ACCOUNTS,
        'max_concurrent_videos': AsyncConfig.MAX_CONCURRENT_VIDEOS,
        'account_delay_min': AsyncConfig.ACCOUNT_DELAY_MIN,
        'account_delay_max': AsyncConfig.ACCOUNT_DELAY_MAX,
        'retry_attempts': AsyncConfig.RETRY_ATTEMPTS,
        'health_check_interval': AsyncConfig.HEALTH_CHECK_INTERVAL,
    }

# Утилиты для мониторинга
async def monitor_async_task_health(task_id, check_interval=60):
    """Мониторинг здоровья асинхронной задачи"""
    try:
        while True:
            await asyncio.sleep(check_interval)
            
            # Проверяем статус задачи
            task = await get_task_async(task_id)
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.PARTIALLY_COMPLETED]:
                await log_info_async(f"🏁 [ASYNC_MONITOR] Task {task_id} finished with status: {task.status}")
                break
            
            # Проверяем активность аккаунтов
            account_tasks = await get_account_tasks_async(task)
            active_count = len([at for at in account_tasks if at.status == TaskStatus.RUNNING])
            
            await log_info_async(f"💓 [ASYNC_MONITOR] Task {task_id} health check - {active_count} accounts active")
            
    except Exception as e:
        await log_error_async(f"❌ [ASYNC_MONITOR] Error monitoring task {task_id}: {str(e)}")

# Функция для тестирования асинхронности
async def test_async_performance(task_id):
    """Тестирование производительности асинхронной версии"""
    start_time = time.time()
    
    try:
        result = await run_async_bulk_upload_task(task_id)
        end_time = time.time()
        
        total_time = end_time - start_time
        
        await log_info_async(f"⚡ [ASYNC_TEST] Performance test completed in {total_time:.2f}s")
        await log_info_async(f"⚡ [ASYNC_TEST] Result: {result}")
        
        return {
            'success': result,
            'execution_time': total_time,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        end_time = time.time()
        total_time = end_time - start_time
        
        await log_error_async(f"❌ [ASYNC_TEST] Performance test failed after {total_time:.2f}s: {str(e)}")
        
        return {
            'success': False,
            'execution_time': total_time,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        } 