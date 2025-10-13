#!/usr/bin/env python
"""
Асинхронная версия bulk upload tasks для параллельной работы с несколькими аккаунтами
Следует лучшим практикам async программирования
"""

import os
import sys
import time
import asyncio
import aiofiles
import json
import traceback
import logging
import random
import math
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
import tempfile
import shutil
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager
import aiohttp
from asgiref.sync import sync_to_async
from django.utils import timezone
import signal
import threading

# SSL Configuration - Fix SSL errors with proxies
try:
    import ssl_fix  # Apply SSL fixes immediately
except ImportError:
    # Fallback SSL configuration
    try:
        import ssl
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        ssl._create_default_https_context = ssl._create_unverified_context
        print("[SSL] Fallback SSL configuration applied")
    except Exception as e:
        print(f"[SSL] Warning: Could not configure SSL settings: {e}")

# Windows-specific fixes
try:
    from .windows_fixes import apply_windows_async_context_fix, log_windows_environment, is_windows
    if is_windows():
        apply_windows_async_context_fix()
        log_windows_environment()
except ImportError:
    print("[WARN] Windows fixes module not available")

# Django imports
import django
django.setup()

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
from .bulk_tasks_playwright import prepare_video_files
from .instagram_automation import InstagramNavigator, InstagramUploader, InstagramLoginHandler
from .browser_utils import BrowserManager, PageUtils, ErrorHandler, NetworkUtils, FileUtils, DebugUtils
from .models import BulkUploadTask, InstagramAccount, VideoFile, BulkUploadAccount, BulkVideo
from .async_video_uniquifier import uniquify_video_for_account, cleanup_uniquifier_temp_files
from .logging_utils import set_async_logger

# Engine flag helpers
def _get_engine_for_task(task_id: int) -> Optional[str]:
    try:
        from django.core.cache import cache as _cache
        return _cache.get(f"bulk_engine_{task_id}")
    except Exception:
        return None

def _clear_engine_for_task(task_id: int) -> None:
    try:
        from django.core.cache import cache as _cache
        _cache.delete(f"bulk_engine_{task_id}")
    except Exception:
        pass

# Настройка логирования
logger = logging.getLogger(__name__)

# Конфигурация асинхронной обработки
@dataclass
class AsyncConfig:
    """Конфигурация для асинхронной обработки"""
    MAX_CONCURRENT_ACCOUNTS: int = 3  # Maximum 3 accounts in parallel to avoid Challenge
    MAX_CONCURRENT_VIDEOS: int = 1
    ACCOUNT_DELAY_MIN: float = 30.0  # Increased delay to avoid Challenge
    ACCOUNT_DELAY_MAX: float = 60.0  # Increased delay to avoid Challenge
    RETRY_ATTEMPTS: int = 2
    HEALTH_CHECK_INTERVAL: int = 60
    FILE_CHUNK_SIZE: int = 8192
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB

# Data Transfer Objects
@dataclass
class AccountData:
    """Данные аккаунта для асинхронной обработки"""
    id: int
    username: str
    password: str
    status: str
    proxy: Optional[Dict[str, Any]] = None
    dolphin_profile_id: Optional[str] = None

@dataclass
class VideoData:
    """Данные видео для асинхронной обработки"""
    id: int
    title: str
    description: str
    file_path: str
    file_size: int
    duration: Optional[float] = None
    location: str = ""
    mentions: str = ""

@dataclass
class TaskData:
    """Данные задачи для асинхронной обработки"""
    id: int
    name: str
    status: str
    accounts: List[AccountData]
    videos: List[VideoData]
    titles: List[Any]  # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: VideoTitle объекты, а не строки

# Асинхронные репозитории для работы с данными
class AsyncTaskRepository:
    """Асинхронный репозиторий для работы с задачами"""
    
    @staticmethod
    @sync_to_async(thread_sensitive=False)
    def get_task(task_id: int) -> BulkUploadTask:
        """Получить задачу по ID"""
        return BulkUploadTask.objects.select_related().get(id=task_id)
    
    @staticmethod
    @sync_to_async
    def get_account_tasks(task: BulkUploadTask) -> List[BulkUploadAccount]:
        """Получить аккаунты задачи"""
        return list(task.accounts.select_related('account', 'proxy').all().order_by('account__status'))
    
    @staticmethod
    @sync_to_async
    def get_task_videos(task: BulkUploadTask) -> List['BulkVideo']:
        """Получить видео задачи"""
        return get_all_task_videos(task)
    
    @staticmethod
    @sync_to_async
    def get_task_titles(task: BulkUploadTask) -> List[Any]:
        """Получить заголовки задачи"""
        return get_all_task_titles(task)
    
    @staticmethod
    @sync_to_async(thread_sensitive=False)
    def update_task_status(task: BulkUploadTask, status: str, log_message: str = "") -> None:
        """Обновить статус задачи с авто-повтором при сбое соединения"""
        from django.db import connections
        try:
            update_task_status(task, status, log_message)
        except Exception as e:
            # Попытка авто-восстановления соединения и повтор
            try:
                for conn in connections.all():
                    if conn.connection is not None:
                        conn.close_if_unusable_or_obsolete()
                        conn.close()
                update_task_status(task, status, log_message)
            except Exception:
                raise e
    
    @staticmethod
    @sync_to_async(thread_sensitive=False)
    def update_task_log(task: BulkUploadTask, log_message: str) -> None:
        """Обновить лог задачи с авто-повтором при сбое соединения"""
        from django.db import connections
        try:
            update_task_log(task, log_message)
        except Exception as e:
            try:
                for conn in connections.all():
                    if conn.connection is not None:
                        conn.close_if_unusable_or_obsolete()
                        conn.close()
                update_task_log(task, log_message)
            except Exception:
                raise e
    
    @staticmethod
    @sync_to_async
    def get_task_properties(task: BulkUploadTask) -> Dict[str, Any]:
        """Получить свойства задачи"""
        return {
            'id': task.id,
            'name': task.name,
            'status': task.status
        }
    
    @staticmethod
    @sync_to_async
    def get_account_properties(account_task: BulkUploadAccount) -> Dict[str, Any]:
        """Получить свойства аккаунта"""
        account = account_task.account
        return {
            'id': account.id,
            'username': account.username,
            'password': account.password,
            'status': account.status,
            'proxy': account_task.proxy.to_dict() if account_task.proxy else None
        }
    
    @staticmethod
    @sync_to_async
    def get_video_properties(video: 'BulkVideo') -> Dict[str, Any]:
        """Получить свойства видео"""
        # Проверяем, является ли это BulkVideo
        if hasattr(video, 'bulk_task'):
            # Это BulkVideo
            # CRITICAL FIX: Properly extract title from title_data relationship
            title = ""
            if hasattr(video, 'title_data') and video.title_data:
                title = video.title_data.title or ""
                print(f"[ASYNC_DATA] [OK] Found title from title_data: '{title[:50]}...'")
            else:
                # CRITICAL FIX: If no title_data, try to assign one from task titles
                if hasattr(video, 'bulk_task') and video.bulk_task:
                    all_titles = list(video.bulk_task.titles.all())
                    if all_titles:
                        # Find unassigned titles
                        unassigned_titles = [t for t in all_titles if t.assigned_to is None]
                        if unassigned_titles:
                            # Assign first unassigned title to this video
                            assigned_title = unassigned_titles[0]
                            assigned_title.assigned_to = video
                            assigned_title.used = True
                            assigned_title.save(update_fields=['assigned_to', 'used'])
                            
                            # Set title_data for immediate use
                            video.title_data = assigned_title
                            title = assigned_title.title or ""
                            print(f"[ASYNC_DATA] 🔥 ASSIGNED title '{title[:50]}...' to video {video.id}")
                        else:
                            print(f"[ASYNC_DATA] [WARN] No unassigned titles available for video {video.id}")
            
            # FIXED: Handle location with task defaults (like sync version)
            location = ""
            if hasattr(video, 'location') and video.location:
                location = video.location.strip()
            elif hasattr(video, 'bulk_task') and video.bulk_task:
                if hasattr(video.bulk_task, 'default_location') and video.bulk_task.default_location:
                    location = video.bulk_task.default_location.strip()
            
            # FIXED: Handle mentions with task defaults (like sync version)
            mentions = ""
            if hasattr(video, 'mentions') and video.mentions:
                mentions = video.mentions.strip()
            elif hasattr(video, 'bulk_task') and video.bulk_task:
                if hasattr(video.bulk_task, 'default_mentions') and video.bulk_task.default_mentions:
                    mentions = video.bulk_task.default_mentions.strip()
            
            return {
                'id': video.id,
                'title': title,  # FIXED: Use title from title_data relationship
                'description': video.mentions or "",  # Используем mentions как description
                'file_path': video.video_file.path,
                'file_size': video.video_file.size,
                'location': location,  # FIXED: Use location with task defaults
                'mentions': mentions   # FIXED: Use mentions with task defaults
            }
        else:
            # Это обычное VideoFile
            return {
                'id': video.id,
                'title': video.title or "",
                'description': video.description or "",
                'file_path': video.video_file.path,
                'file_size': video.video_file.size
            }
    
    @staticmethod
    @sync_to_async(thread_sensitive=False)
    def close_django_connections() -> None:
        """Закрыть Django соединения"""
        import platform
        from django.db import connections
        
        try:
            # Закрываем все соединения с базой данных
            for conn in connections.all():
                if conn.connection is not None:
                    conn.close()
            
            # На Windows добавляем дополнительную очистку
            if platform.system().lower() == 'windows':
                import time
                time.sleep(0.1)  # Небольшая задержка для Windows
                
            print("[OK] [DATABASE] All Django connections closed")
        except Exception as e:
            print(f"[WARN] [DATABASE] Error closing Django connections: {str(e)}")
    
    @staticmethod
    @sync_to_async
    def check_videos_empty(videos: List['BulkVideo']) -> bool:
        """Проверить, пустой ли список видео"""
        return len(videos) == 0
    
    @staticmethod
    @sync_to_async
    def get_videos_count(videos: List['BulkVideo']) -> int:
        """Получить количество видео"""
        return len(videos)
    
    @staticmethod
    @sync_to_async
    def get_titles_count(titles: List[str]) -> int:
        """Получить количество заголовков"""
        return len(titles)

class AsyncAccountRepository:
    """Асинхронный репозиторий для работы с аккаунтами"""
    
    @staticmethod
    @sync_to_async(thread_sensitive=False)
    def get_account_details(account: InstagramAccount, proxy: Optional[Dict] = None) -> Dict[str, Any]:
        """Получить детали аккаунта"""
        return get_account_details(account, proxy)
    
    @staticmethod
    @sync_to_async(thread_sensitive=False)
    def get_account_proxy(account_task: BulkUploadAccount, account: InstagramAccount) -> Optional[Dict]:
        """Получить прокси аккаунта"""
        return get_account_proxy(account_task, account)
    
    @staticmethod
    @sync_to_async(thread_sensitive=False)
    def update_account_task(account_task: BulkUploadAccount, **kwargs) -> None:
        """Обновить задачу аккаунта с авто-повтором при сбое соединения"""
        from django.db import connections
        try:
            update_account_task(account_task, **kwargs)
        except Exception as e:
            try:
                for conn in connections.all():
                    if conn.connection is not None:
                        conn.close_if_unusable_or_obsolete()
                        conn.close()
                update_account_task(account_task, **kwargs)
            except Exception:
                raise e

# Асинхронная работа с файлами
class AsyncFileManager:
    """Асинхронный менеджер файлов"""
    
    def __init__(self, chunk_size: int = AsyncConfig.FILE_CHUNK_SIZE):
        self.chunk_size = chunk_size
    
    async def copy_file_async(self, src_path: str, dst_path: str) -> None:
        """Асинхронно скопировать файл"""
        async with aiofiles.open(src_path, 'rb') as src:
            async with aiofiles.open(dst_path, 'wb') as dst:
                while chunk := await src.read(self.chunk_size):
                    await dst.write(chunk)
    
    async def create_temp_file_async(self, video_file, filename: str) -> str:
        """Асинхронно создать временный файл"""
        def create_temp_file():
            with NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp:
                for chunk in video_file.chunks():
                    tmp.write(chunk)
                return tmp.name
        
        # Запускаем создание файла асинхронно
        try:
            # Python 3.9+
            return await asyncio.to_thread(create_temp_file)
        except AttributeError:
            # Fallback для Python < 3.9
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, create_temp_file)
    
    async def create_temp_file_from_path_async(self, file_path: str, filename: str) -> str:
        """Асинхронно создать временный файл из пути к файлу"""
        def create_temp_file():
            with NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp:
                with open(file_path, 'rb') as src:
                    while chunk := src.read(self.chunk_size):
                        tmp.write(chunk)
                return tmp.name
        
        # Запускаем создание файла асинхронно
        try:
            # Python 3.9+
            return await asyncio.to_thread(create_temp_file)
        except AttributeError:
            # Fallback для Python < 3.9
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, create_temp_file)
    
    async def cleanup_temp_files_async(self, file_paths: List[str]) -> None:
        """Асинхронно очистить временные файлы"""
        def cleanup_files():
            for file_path in file_paths:
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    logger.warning(f"Could not delete temp file {file_path}: {str(e)}")
        
        # Запускаем очистку асинхронно
        try:
            # Python 3.9+
            await asyncio.to_thread(cleanup_files)
        except AttributeError:
            # Fallback для Python < 3.9
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, cleanup_files)
    
    async def get_file_size_async(self, file_path: str) -> int:
        """Асинхронно получить размер файла"""
        def get_file_size():
            return os.path.getsize(file_path)
        
        # Запускаем получение размера асинхронно
        try:
            # Python 3.9+
            return await asyncio.to_thread(get_file_size)
        except AttributeError:
            # Fallback для Python < 3.9
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, get_file_size)

# Асинхронный логгер
class AsyncLogger:
    """Асинхронный логгер для задач"""
    
    def __init__(self, task_id: int, account_id: Optional[int] = None, cache_ns: str = "task_logs", persist_db: bool = True):
        self.task_id = task_id
        self.account_id = account_id
        self.task_repo = AsyncTaskRepository()
        self.account_repo = AsyncAccountRepository()
        self.cache_ns = cache_ns
        self.persist_db = persist_db
    
    async def log(self, level: str, message: str, category: Optional[str] = None) -> None:
        """Логировать сообщение"""
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = self._format_message(message, level, category)
        
        # Выводим в консоль
        console_prefix = self._get_console_prefix(level, category)
        print(f"{console_prefix} {formatted_message}")
        
        # Сохраняем в Django cache для веб-интерфейса
        try:
            from django.core.cache import cache
            
            # Создаем структурированную запись лога
            log_entry = {
                'timestamp': timestamp,
                'level': level.upper(),
                'message': formatted_message,
                'category': category or 'GENERAL',
                'is_critical': self._is_critical_event(level, message, category)
            }
            
            # Сохраняем в cache для задачи
            cache_key = f"{self.cache_ns}_{self.task_id}"
            existing_logs = cache.get(cache_key, [])
            existing_logs.append(log_entry)
            
            # Ограничиваем количество логов (последние 1000)
            if len(existing_logs) > 1000:
                existing_logs = existing_logs[-1000:]
            
            cache.set(cache_key, existing_logs, timeout=3600)  # 1 час
            
            # Если есть account_id, сохраняем также в account-specific cache
            if self.account_id:
                account_cache_key = f"{self.cache_ns}_{self.task_id}_account_{self.account_id}"
                account_logs = cache.get(account_cache_key, [])
                account_logs.append(log_entry)
                
                if len(account_logs) > 1000:
                    account_logs = account_logs[-1000:]
                
                cache.set(account_cache_key, account_logs, timeout=3600)
            
            # Обновляем время последнего обновления
            cache.set(f"{self.cache_ns.replace('logs','last_update')}_{self.task_id}", timestamp, timeout=3600)
            
        except Exception as e:
            print(f"[FAIL] [ASYNC_LOGGER] Error saving to cache: {str(e)}")
        
        # Сохраняем в базу данных для критических событий (опционально)
        if self.persist_db and self._is_critical_event(level, message, category):
            try:
                task = await self.task_repo.get_task(self.task_id)
                await self.task_repo.update_task_log(task, f"[{timestamp}] {formatted_message}\n")
            except Exception as e:
                # Attempt a one-shot connection reset and retry (non-blocking)
                try:
                    from django.db import connections
                    for conn in connections.all():
                        if conn.connection is not None:
                            conn.close_if_unusable_or_obsolete()
                    task = await self.task_repo.get_task(self.task_id)
                    await self.task_repo.update_task_log(task, f"[{timestamp}] {formatted_message}\n")
                except Exception:
                    print(f"[FAIL] [ASYNC_LOGGER] Error saving to database: {str(e)}")
    
    def _is_critical_event(self, level: str, message: str, category: Optional[str]) -> bool:
        """Проверяет, является ли событие критическим"""
        # Do not treat routine "verification" messages as critical to avoid DB writes spam
        critical_keywords = ['error', 'failed', 'suspension', 'timeout']
        return (level.upper() in ['ERROR', 'CRITICAL'] or any(kw in message.lower() for kw in critical_keywords))
    
    def _format_message(self, message: str, level: str, category: Optional[str]) -> str:
        """Форматирует сообщение для логирования"""
        if category:
            return f"[{category}] {message}"
        return message
    
    def _get_console_prefix(self, level: str, category: Optional[str]) -> str:
        """Получает префикс для консольного вывода"""
        level_colors = {
            'INFO': '\033[94m',      # Blue
            'SUCCESS': '\033[92m',   # Green
            'WARNING': '\033[93m',   # Yellow
            'ERROR': '\033[91m',     # Red
        }
        
        color = level_colors.get(level.upper(), '\033[0m')
        reset_color = '\033[0m'
        return f"{color}[{level.upper()}]{reset_color}"

# Асинхронный обработчик аккаунта
class AsyncAccountProcessor:
    """Асинхронный обработчик одного аккаунта"""
    
    def __init__(self, account_task, task_data, logger: AsyncLogger):
        self.account_task = account_task
        self.task_data = task_data
        self.logger = logger
        # Share logger globally for logging_utils bridge
        try:
            from .logging_utils import set_async_logger
            set_async_logger(logger)
        except Exception:
            pass
        self.file_manager = AsyncFileManager()
        self.account_repo = AsyncAccountRepository()
        self.start_time = None
        self.end_time = None

        # Create log callback that bridges to async logger
        self.log_callback = self._create_log_callback()

    def _create_log_callback(self):
        """Create a synchronous log callback that bridges to async logger"""
        def log_callback(message: str):
            # Use asyncio.create_task to properly handle the coroutine
            try:
                import asyncio
                # Get current event loop and create task properly
                loop = asyncio.get_running_loop()
                loop.create_task(self.logger.log('INFO', f"[API] {message}"))
            except RuntimeError:
                # No event loop running, use print fallback
                print(f"[API] {message}")
            except Exception:
                # Other exceptions, fallback to print
                print(f"[API] {message}")
        return log_callback

    async def process(self) -> Tuple[str, int, int]:
        """Основной метод обработки аккаунта"""
        self.start_time = time.time()
        
        try:
            await self.logger.log('INFO', f"[START] Starting async processing for account task {self.account_task.id}")
            
            # Получаем данные аккаунта
            account = self.account_task.account
            proxy = await self.account_repo.get_account_proxy(self.account_task, account)
            account_details = await self.account_repo.get_account_details(account, proxy)
            # Provide bulk_upload_id to downstream flows (captcha notifications, etc.)
            try:
                if isinstance(account_details, dict):
                    account_details.setdefault('bulk_upload_id', self.task_data.id)
            except Exception:
                pass
            
            # Логируем статус аккаунта для информации, но не пропускаем
            if account.status != 'ACTIVE':
                await self.logger.log('INFO', f"Account {account.username} has status: {account.status} - will attempt processing")
            
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
            
            # Запускаем браузер
            result = await self._run_browser_async(
                account_details, videos_for_account, video_files_to_upload
            )
            
            # Очищаем временные файлы
            # Важно: не удаляем временные файлы и файлы уникализации на середине выполнения аккаунтов,
            # чтобы не потерять входные данные для следующих аккаунтов.
            # Переносим очистку в финал задачи (_finalize_task).
            
            self.end_time = time.time()
            processing_time = self.end_time - self.start_time
            
            # Проверяем результат браузера
            if isinstance(result, tuple) and len(result) >= 3:
                result_type, completed, failed = result
                # Persist per-account counters
                try:
                    # Use task_utils.update_account_task compatibility hook to pass extra fields
                    from . import task_utils as _tu
                    setattr(_tu.update_account_task, "_extra_fields", {
                        'uploaded_success_count': completed,
                        'uploaded_failed_count': failed,
                    })
                    _tu.update_account_task(
                        self.account_task,
                        status=(TaskStatus.COMPLETED if result_type == 'success' and completed > 0 else self.account_task.status),
                        completed_at=timezone.now()
                    )
                except Exception:
                    pass
                
                if result_type == 'success' and completed > 0:
                    await self.logger.log('SUCCESS', f"Account {account.username} successfully uploaded {completed} videos in {processing_time:.1f}s")
                elif result_type in ['verification_required', 'phone_verification_required', 'human_verification_required']:
                    await self.logger.log('WARNING', f"Account {account.username} requires verification - processed in {processing_time:.1f}s")
                elif result_type == 'suspended':
                    await self.logger.log('ERROR', f"Account {account.username} is suspended - processed in {processing_time:.1f}s")
                else:
                    await self.logger.log('ERROR', f"Account {account.username} failed to upload videos - processed in {processing_time:.1f}s")
            else:
                await self.logger.log('ERROR', f"Account {account.username} processing failed - processed in {processing_time:.1f}s")
            
            return result
            
        except Exception as e:
            self.end_time = time.time()
            processing_time = self.end_time - self.start_time
            
            await self.logger.log('ERROR', f"Error processing account: {str(e)}")
            await self.account_repo.update_account_task(
                self.account_task,
                status=TaskStatus.FAILED,
                completed_at=timezone.now(),
                log_message=f"Error: {str(e)}\n"
            )
            return 'failed', 0, 1
    
    async def _prepare_videos_for_account(self) -> List[VideoData]:
        """Подготавливает видео для аккаунта"""
        videos_for_account = list(self.task_data.videos)
        random.shuffle(videos_for_account)
        
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: titles_for_account содержит VideoTitle объекты, а не строки
        titles_for_account = list(self.task_data.titles) if self.task_data.titles else []
        if titles_for_account:
            random.shuffle(titles_for_account)
        
        # Назначаем случайные заголовки видео
        for i, video in enumerate(videos_for_account):
            if titles_for_account:
                title_index = i % len(titles_for_account)
                # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Извлекаем title из VideoTitle объекта
                title_obj = titles_for_account[title_index]
                if hasattr(title_obj, 'title'):
                    video.title = title_obj.title
                else:
                    # Fallback: если это строка
                    video.title = str(title_obj)
        
        # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Выводим описания видео перед загрузкой
        await self.logger.log('INFO', f"[VIDEO] PREPARING VIDEOS FOR ACCOUNT {self.account_task.account.username}:")
        for i, video in enumerate(videos_for_account):
            video_filename = os.path.basename(video.file_path)
            await self.logger.log('INFO', f"[CAMERA] Video {i+1}: {video_filename}")
            await self.logger.log('INFO', f"[TEXT] Description: '{video.title[:100]}{'...' if len(video.title) > 100 else ''}'")
            if video.location:
                await self.logger.log('INFO', f"[LOCATION] Location: {video.location}")
            if video.mentions:
                await self.logger.log('INFO', f"[USERS] Mentions: {video.mentions}")
        
        await self.logger.log('INFO', f"Prepared {len(videos_for_account)} videos for account")
        return videos_for_account
    
    async def _prepare_video_files(self, videos_for_account: List[VideoData]) -> Tuple[List[str], List[str]]:
        """Подготавливает файлы видео с уникализацией для каждого аккаунта"""
        temp_files = []
        video_files_to_upload = []
        account_username = self.account_task.account.username
        
        await self.logger.log('INFO', f"[VIDEO] Starting video uniquification for account {account_username}")
        
        for i, video in enumerate(videos_for_account):
            video_filename = os.path.basename(video.file_path)
            await self.logger.log('INFO', f"Preparing and uniquifying video: {video_filename}")
            
            try:
                # Сначала создаем временный файл из исходного видео
                original_temp_file = await self.file_manager.create_temp_file_from_path_async(
                    video.file_path, video_filename
                )
                temp_files.append(original_temp_file)
                
                await self.logger.log('INFO', f"Created temporary file: {original_temp_file}")
                
                # Теперь уникализируем видео для этого аккаунта
                try:
                    unique_video_path = await uniquify_video_for_account(
                        original_temp_file, 
                        account_username, 
                        copy_number=i+1
                    )
                    
                    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Обновляем file_path в VideoData
                    video.file_path = unique_video_path
                    
                    # Добавляем уникализированное видео в список для загрузки
                    video_files_to_upload.append(unique_video_path)
                    temp_files.append(unique_video_path)
                    
                    await self.logger.log('SUCCESS', f"[OK] Created unique video for {account_username}: {os.path.basename(unique_video_path)}")
                    
                except Exception as uniquify_error:
                    # Если уникализация не удалась, используем оригинальный файл
                    await self.logger.log('WARNING', f"[WARN] Video uniquification failed: {str(uniquify_error)}, using original file")
                    video_files_to_upload.append(original_temp_file)
                
            except Exception as e:
                await self.logger.log('ERROR', f"[FAIL] Error preparing video file {video_filename}: {str(e)}")
                # Пропускаем это видео и продолжаем с другими
                continue
        
        await self.logger.log('SUCCESS', f"[TARGET] Prepared {len(video_files_to_upload)} unique videos for account {account_username}")
        return temp_files, video_files_to_upload
    
    async def _run_browser_async(self, account_details: Dict, videos: List[VideoData], 
                                video_files_to_upload: List[str]) -> Tuple[str, int, int]:
        """Асинхронно запустить браузер"""
        try:
            await self.logger.log('INFO', f"Starting browser for account: {account_details['username']}")
            
            # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Выводим описания видео перед загрузкой в браузере
            await self.logger.log('INFO', f"[TARGET] FINAL VIDEO DESCRIPTIONS FOR {account_details['username']}:")
            for i, video in enumerate(videos):
                video_filename = os.path.basename(video.file_path)
                await self.logger.log('INFO', f"[CAMERA] Video {i+1}: {video_filename}")
                await self.logger.log('INFO', f"[TEXT] FINAL Description: '{video.title[:100]}{'...' if len(video.title) > 100 else ''}'")
                if video.location:
                    await self.logger.log('INFO', f"[LOCATION] Location: {video.location}")
                if video.mentions:
                    await self.logger.log('INFO', f"[USERS] Mentions: {video.mentions}")
            
            # Логируем информацию о файлах для отладки
            await self.logger.log('INFO', f"[FOLDER] Files to upload: {len(video_files_to_upload)}")
            for i, file_path in enumerate(video_files_to_upload):
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    await self.logger.log('INFO', f"[FILE] File {i+1}: {os.path.basename(file_path)} ({file_size} bytes)")
                else:
                    await self.logger.log('ERROR', f"[FAIL] File {i+1} not found: {file_path}")
            
            # Проверяем соответствие видео и файлов
            if len(videos) != len(video_files_to_upload):
                await self.logger.log('WARNING', f"[WARN] Mismatch: {len(videos)} videos vs {len(video_files_to_upload)} files")
            
            # Импортируем асинхронную версию браузера
            # Выбор движка выполнения: dolphin (по умолчанию) или instagrapi (API)
            engine = None
            try:
                from django.core.cache import cache as _cache
                engine = _cache.get(f"bulk_engine_{self.task_data.id}")
            except Exception:
                engine = None

            if str(engine).lower() == 'instagrapi':
                from .async_impl.instagrapi import run_instagrapi_upload_async
                result = await run_instagrapi_upload_async(
                    account_details,
                    videos,
                    video_files_to_upload,
                    self.task_data.id,
                    self.account_task.id,
                    on_log=self.log_callback
                )
            else:
                from .bulk_tasks_playwright_async import run_dolphin_browser_async
                result = await run_dolphin_browser_async(
                    account_details,
                    videos,
                    video_files_to_upload,
                    self.task_data.id,
                    self.account_task.id
                )
            
            return self._process_browser_result(result)
                
        except Exception as e:
            error_message = str(e)
            await self.logger.log('ERROR', f"Browser task failed for account {account_details['username']}: {error_message}")
            
            # Обрабатываем специальные случаи верификации и блокировок
            if "PHONE_VERIFICATION_REQUIRED" in error_message:
                await self.logger.log('WARNING', f"[PHONE] Phone verification required for account {account_details['username']}")
                return 'phone_verification_required', 0, 1
            elif "HUMAN_VERIFICATION_REQUIRED" in error_message:
                await self.logger.log('WARNING', f"[BOT] Human verification required for account {account_details['username']}")
                return 'human_verification_required', 0, 1
            elif "SUSPENDED" in error_message:
                await self.logger.log('WARNING', f"[BLOCK] Account {account_details['username']} is suspended")
                return 'suspended', 0, 1
            else:
                return 'failed', 0, 1
    
    def _process_browser_result(self, result: Tuple) -> Tuple[str, int, int]:
        """Обрабатывает результат браузера"""
        if isinstance(result, tuple) and len(result) >= 3:
            result_type, completed, failed = result
            # Normalize result type to lowercase to align with aggregator expectations
            try:
                normalized_type = str(result_type).lower()
            except Exception:
                normalized_type = 'failed'
            return normalized_type, completed, failed
        else:
            return 'failed', 0, 1
    
    async def _handle_no_videos(self) -> None:
        """Обрабатывает случай отсутствия видео"""
        await self.logger.log('ERROR', "No videos found for account")
        await self.account_repo.update_account_task(
            self.account_task,
            status=TaskStatus.FAILED,
            completed_at=timezone.now(),
            log_message="No videos found for account\n"
        )
    
    async def _handle_no_files(self) -> None:
        """Обрабатывает случай отсутствия файлов"""
        await self.logger.log('ERROR', "No valid video files to upload")
        await self.account_repo.update_account_task(
            self.account_task,
            status=TaskStatus.FAILED,
            completed_at=timezone.now(),
            log_message="No valid video files to upload\n"
        )

# Координатор асинхронных задач
class AsyncTaskCoordinator:
    """Координатор для асинхронного выполнения задач"""
    
    def __init__(self, task_id: int):
        self.task_id = task_id
        self.task_repo = AsyncTaskRepository()
        self.account_semaphore = asyncio.Semaphore(AsyncConfig.MAX_CONCURRENT_ACCOUNTS)
        self.start_time = None
        self.end_time = None
    
    async def run(self) -> bool:
        """Основной метод запуска асинхронной задачи"""
        self.start_time = time.time()
        
        try:
            # Получаем задачу
            task = await self.task_repo.get_task(self.task_id)
            
            # Инициализируем логгер
            logger = AsyncLogger(self.task_id)
            set_async_logger(logger)
            
            # Обновляем статус задачи
            current_time = timezone.now()
            timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
            task_props = await self.task_repo.get_task_properties(task)
            await self.task_repo.update_task_status(
                task, 
                TaskStatus.RUNNING, 
                f"[{timestamp}] [START] Starting ASYNC bulk upload task '{task_props['name']}'\n"
            )
            
            await logger.log('INFO', f"Starting async task '{task_props['name']}'")
            
            # Получаем все данные
            account_tasks = await self.task_repo.get_account_tasks(task)
            all_videos = await self.task_repo.get_task_videos(task)
            all_titles = await self.task_repo.get_task_titles(task)
            
            if await self.task_repo.check_videos_empty(all_videos):
                error_msg = "No videos found for this task"
                await logger.log('ERROR', error_msg)
                await self.task_repo.update_task_status(task, TaskStatus.FAILED, f"[{timestamp}] [FAIL] {error_msg}\n")
                return False
            
            videos_count = await self.task_repo.get_videos_count(all_videos)
            titles_count = await self.task_repo.get_titles_count(all_titles)
            await logger.log('INFO', f"Found {videos_count} videos and {titles_count} titles")
            
            # Преобразуем данные в DTO
            task_data = await self._create_task_data(task, account_tasks, all_videos, all_titles)
            
            # Determine execution mode: default parallel-per-account or rounds-by-video (API only)
            use_rounds = False
            extra_init_delay = False
            try:
                from django.core.cache import cache as _cache
                use_rounds = bool(_cache.get(f"bulk_rounds_{self.task_id}"))
                extra_init_delay = bool(_cache.get(f"bulk_init_delay_{self.task_id}"))
            except Exception:
                pass

            # Store flags on instance for downstream use
            self.use_rounds = use_rounds
            self.extra_init_delay = extra_init_delay

            if use_rounds:
                await logger.log('INFO', '[MODE] Using rounds-by-video scheduling (API)')
                # In rounds mode: iterate videos; for each video, shuffle accounts and run per-account upload of only that video
                # Build lightweight per-video task data clones
                all_video_datas = list(task_data.videos)
                total_rounds = len(all_video_datas)
                for round_index, video_data in enumerate(all_video_datas, start=1):
                    await logger.log('INFO', f"[ROUND] Starting round {round_index}/{total_rounds}: {os.path.basename(video_data.file_path)}")
                    # Shuffle accounts each round
                    accounts_order = list(account_tasks)
                    random.shuffle(accounts_order)
                    # Build tasks for this round
                    round_tasks = []
                    for account_task in accounts_order:
                        # Clone task_data with only this one video
                        single_video_task_data = TaskData(
                            id=task_data.id,
                            name=task_data.name,
                            status=task_data.status,
                            accounts=task_data.accounts,
                            videos=[video_data],
                            titles=task_data.titles,
                        )
                        processor = AsyncAccountProcessor(account_task, single_video_task_data, logger)
                        coro = self._process_account_with_semaphore(processor, account_task)
                        round_tasks.append(coro)
                    # Run this round with concurrency control
                    await logger.log('INFO', f"[ROUND] Dispatching {len(round_tasks)} accounts for round {round_index}")
                    _ = await asyncio.gather(*round_tasks, return_exceptions=True)
            else:
                # Создаем задачи для всех аккаунтов (default) with staggered start
                tasks = []
                for i, account_task in enumerate(account_tasks):
                    processor = AsyncAccountProcessor(account_task, task_data, logger)
                    task_coroutine = self._process_account_with_semaphore(processor, account_task, start_delay=i * 2.0)
                    tasks.append(task_coroutine)
                
                # Ограничиваем количество параллельных задач до MAX_CONCURRENT_ACCOUNTS
                max_concurrent = AsyncConfig.MAX_CONCURRENT_ACCOUNTS
                if len(tasks) > max_concurrent:
                    await logger.log('INFO', f"Limiting parallel accounts to {max_concurrent} (was {len(tasks)})")
                    tasks = tasks[:max_concurrent]
                
                # Запускаем задачи параллельно с задержками
                await logger.log('INFO', f"Starting {len(tasks)} account tasks in parallel with staggered delays")
                results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            try:
                # If 'results' is undefined due to rounds mode, compute a synthetic list to aggregate
                if 'results' not in locals():
                    # Aggregate per-account status from DB to produce summary
                    await logger.log('INFO', '[ROUND] Aggregating results from account tasks')
                    results = []
                    for at in account_tasks:
                        # approximate: if account completed at least one upload in rounds, mark success 1,0
                        completed = getattr(at, 'uploaded_success_count', 0) or 0
                        failed = getattr(at, 'uploaded_failed_count', 0) or 0
                        res_type = 'success' if completed > 0 else ('failed' if failed > 0 else 'failed')
                        results.append((res_type, int(completed), int(failed)))
                await self._process_results(results, account_tasks, logger)
            except Exception:
                await logger.log('WARNING', 'Result aggregation encountered an issue; continuing to finalize task')
            
            # Завершаем задачу
            await self._finalize_task(task, logger)
            
            self.end_time = time.time()
            total_time = self.end_time - self.start_time
            
            await logger.log('SUCCESS', f"Async task completed in {total_time:.1f}s")
            # Clear engine flag after completion
            try:
                _clear_engine_for_task(self.task_id)
            except Exception:
                pass
            return True
            
        except Exception as e:
            error_msg = f"Critical error in async task: {str(e)}"
            print(error_msg)
            print(f"Traceback: {traceback.format_exc()}")
            
            # ВАЖНО: Обновляем статус задачи на FAILED при критической ошибке
            try:
                task = await self.task_repo.get_task(self.task_id)
                current_time = timezone.now()
                timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
                await self.task_repo.update_task_status(
                    task, 
                    TaskStatus.FAILED, 
                    f"[{timestamp}] [EXPLODE] Critical task error: {error_msg}\n"
                )
                print(f"[OK] Updated task {self.task_id} status to FAILED")
            except Exception as update_error:
                print(f"[FAIL] Failed to update task status: {str(update_error)}")
            
            return False
    
    async def _create_task_data(self, task: BulkUploadTask, account_tasks: List[BulkUploadAccount], 
                               all_videos: List['BulkVideo'], all_titles: List[str]) -> TaskData:
        """Создает DTO с данными задачи"""
        # Получаем свойства задачи
        task_props = await self.task_repo.get_task_properties(task)
        
        # Получаем свойства аккаунтов
        accounts = []
        for account_task in account_tasks:
            account_props = await self.task_repo.get_account_properties(account_task)
            accounts.append(AccountData(
                id=account_props['id'],
                username=account_props['username'],
                password=account_props['password'],
                status=account_props['status'],
                proxy=account_props['proxy']
            ))
        
        # Получаем свойства видео
        videos = []
        for video in all_videos:
            video_props = await self.task_repo.get_video_properties(video)
            videos.append(VideoData(
                id=video_props['id'],
                title=video_props['title'],
                description=video_props['description'],
                file_path=video_props['file_path'],
                file_size=video_props['file_size'],
                location=video_props.get('location', ''),
                mentions=video_props.get('mentions', '')
            ))
        
        return TaskData(
            id=task_props['id'],
            name=task_props['name'],
            status=task_props['status'],
            accounts=accounts,
            videos=videos,
            titles=all_titles
        )
    
    async def _process_account_with_semaphore(self, processor: AsyncAccountProcessor, 
                                            account_task: BulkUploadAccount, start_delay: float = 0.0) -> Tuple[str, int, int]:
        """Обрабатывает аккаунт с ограничением параллельности"""
        async with self.account_semaphore:
            # Initial staggered delay to avoid simultaneous starts
            if start_delay > 0:
                await asyncio.sleep(start_delay)
            
            # Добавляем случайную задержку между аккаунтами
            delay = random.uniform(AsyncConfig.ACCOUNT_DELAY_MIN, AsyncConfig.ACCOUNT_DELAY_MAX)
            await asyncio.sleep(delay)
            # Дополнительная небольшая задержка перед началом (0–5s) по флагу
            try:
                if getattr(self, 'extra_init_delay', False):
                    await asyncio.sleep(random.uniform(0.0, 5.0))
            except Exception:
                pass
            
            return await processor.process()
    
    async def _process_results(self, results: List, account_tasks: List[BulkUploadAccount], 
                             logger: AsyncLogger) -> None:
        """Обрабатывает результаты выполнения задач"""
        successful_accounts = 0
        failed_accounts = 0
        verification_required_accounts = 0
        suspended_accounts = 0
        total_uploaded_videos = 0
        total_failed_videos = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                await logger.log('ERROR', f"Account task {i} failed with exception: {str(result)}")
                failed_accounts += 1
                continue
            
            if isinstance(result, tuple) and len(result) >= 3:
                result_type, completed, failed = result
                
                # Подсчитываем общее количество видео
                total_uploaded_videos += completed
                total_failed_videos += failed
                
                if result_type == 'success' and completed > 0:
                    # Успех только если видео действительно выложились
                    successful_accounts += 1
                    await logger.log('SUCCESS', f"Account {i+1} successfully uploaded {completed} videos")
                    # Update per-account counters in DB
                    try:
                        if i < len(account_tasks):
                            account_task = account_tasks[i]
                            from . import task_utils as _tu
                            setattr(_tu.update_account_task, "_extra_fields", {
                                'uploaded_success_count': completed,
                                'uploaded_failed_count': failed,
                            })
                            # ЯВНО: ставим статус COMPLETED
                            await AsyncAccountRepository.update_account_task(account_task, status=TaskStatus.COMPLETED)
                            _tu.update_account_task(account_task)
                    except Exception:
                        pass
                elif result_type in ['verification_required', 'phone_verification_required', 'human_verification_required']:
                    verification_required_accounts += 1
                    await logger.log('WARNING', f"Account {i+1} requires verification")
                    # Обновляем статус аккаунта в базе данных
                    if i < len(account_tasks):
                        account_task = account_tasks[i]
                        await AsyncAccountRepository.update_account_task(
                            account_task, 
                            status=result_type.upper()
                        )
                        await logger.log('INFO', f"Updated account {account_task.account.username} status to {result_type.upper()}")
                elif result_type == 'suspended':
                    suspended_accounts += 1
                    await logger.log('ERROR', f"Account {i+1} is suspended")
                    # Обновляем статус аккаунта в базе данных
                    if i < len(account_tasks):
                        account_task = account_tasks[i]
                        await AsyncAccountRepository.update_account_task(
                            account_task, 
                            status='SUSPENDED'
                        )
                        await logger.log('INFO', f"Updated account {account_task.account.username} status to SUSPENDED")
                else:
                    failed_accounts += 1
                    await logger.log('ERROR', f"Account {i+1} failed to upload videos")
                    # Update per-account counters on fail path too, and mark FAILED
                    try:
                        if i < len(account_tasks):
                            account_task = account_tasks[i]
                            from . import task_utils as _tu
                            setattr(_tu.update_account_task, "_extra_fields", {
                                'uploaded_success_count': completed,
                                'uploaded_failed_count': failed,
                            })
                            await AsyncAccountRepository.update_account_task(account_task, status=TaskStatus.FAILED)
                            _tu.update_account_task(account_task)
                    except Exception:
                        pass
            else:
                failed_accounts += 1
                await logger.log('ERROR', f"Account {i+1} processing failed")
        
        await logger.log('INFO', f"Results: {successful_accounts} successful ({total_uploaded_videos} videos uploaded), {failed_accounts} failed ({total_failed_videos} videos failed), {verification_required_accounts} verification required, {suspended_accounts} suspended")
        
        # Final task status: all success -> COMPLETED; some -> PARTIALLY_COMPLETED; none -> FAILED
        total_accounts = len(account_tasks)
        if successful_accounts == 0:
            final_status = TaskStatus.FAILED
        elif successful_accounts == total_accounts:
            final_status = TaskStatus.COMPLETED
        else:
            final_status = TaskStatus.PARTIALLY_COMPLETED
        
        task = await self.task_repo.get_task(self.task_id)
        await self.task_repo.update_task_status(task, final_status)
    
    async def _finalize_task(self, task: BulkUploadTask, logger: AsyncLogger) -> None:
        """Завершает задачу"""
        current_time = timezone.now()
        timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Очищаем зависшие FFmpeg процессы
        from .async_video_uniquifier import cleanup_hanging_ffmpeg
        try:
            # Запускаем очистку в отдельном потоке
            try:
                await asyncio.to_thread(cleanup_hanging_ffmpeg)
            except AttributeError:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, cleanup_hanging_ffmpeg)
        except Exception as e:
            await logger.log('WARNING', f'Failed to cleanup FFmpeg processes: {str(e)}')
        
        # Очищаем все временные файлы уникализации
        await cleanup_uniquifier_temp_files()
        await logger.log('INFO', '[CLEAN] Cleaned up all uniquification temp files')
        
        # Очищаем оригинальные файлы видео из media/bot/bulk_videos/
        try:
            deleted_files = await self._cleanup_original_video_files(task, logger)
            if deleted_files > 0:
                await logger.log('INFO', f'[DELETE] Cleaned up {deleted_files} original video files from media directory')
        except Exception as e:
            await logger.log('WARNING', f'Failed to cleanup original video files: {str(e)}')
        
        await self.task_repo.update_task_log(
            task,
            f"[{timestamp}] [FINISH] ASYNC task completed\n"
        )
    
    async def _cleanup_original_video_files(self, task: BulkUploadTask, logger: AsyncLogger) -> int:
        """Очищает оригинальные видео файлы из media/bot/bulk_videos/ для данной задачи"""
        import os
        from django.conf import settings
        from asgiref.sync import sync_to_async
        
        deleted_count = 0
        
        # Получаем все видео файлы для этой задачи
        @sync_to_async
        def get_task_videos():
            return list(task.videos.all())
        
        videos = await get_task_videos()
        
        for video in videos:
            if video.video_file:
                try:
                    # Получаем полный путь к файлу
                    file_path = video.video_file.path if hasattr(video.video_file, 'path') else None
                    
                    if file_path and os.path.exists(file_path):
                        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Удаляем файл независимо от статуса задачи
                        # Проверяем только, что файл не используется другими активными задачами
                        @sync_to_async
                        def is_file_safe_to_delete():
                            filename = os.path.basename(file_path)
                            
                            # Проверяем, есть ли другие BulkVideo объекты с таким же файлом в активных задачах
                            from .models import BulkVideo, BulkUploadTask
                            
                            other_videos_with_same_file = BulkVideo.objects.filter(
                                video_file__icontains=filename
                            ).exclude(
                                bulk_task=task  # Исключаем текущую задачу
                            )
                            
                            # Проверяем статусы задач для этих видео
                            for other_video in other_videos_with_same_file:
                                other_task = other_video.bulk_task
                                if other_task.status in ['RUNNING', 'PENDING']:
                                    return False, f'[BLOCK] File {filename} is still used by running task "{other_task.name}" (ID: {other_task.id})'
                            
                            return True, None
                        
                        is_safe, warning_msg = await is_file_safe_to_delete()
                        
                        if is_safe:
                            # Удаляем файл
                            @sync_to_async
                            def delete_file():
                                os.unlink(file_path)
                                return os.path.basename(file_path)
                            
                            filename = await delete_file()
                            deleted_count += 1
                            await logger.log('INFO', f'[DELETE] Deleted original video file: {filename}')
                        else:
                            await logger.log('INFO', f'[PAUSE] Skipped deleting file (still in use by other tasks): {os.path.basename(file_path)}')
                            if warning_msg:
                                await logger.log('WARNING', warning_msg)
                        
                except Exception as e:
                    await logger.log('WARNING', f'Failed to delete video file {video.id}: {str(e)}')
        
        return deleted_count

# Основная функция для запуска асинхронной задачи
async def run_async_bulk_upload_task(task_id: int) -> bool:
    """
    Асинхронная версия bulk upload task для параллельной обработки аккаунтов
    
    Преимущества:
    - Параллельная обработка нескольких аккаунтов
    - Лучшее использование ресурсов
    - Контроль параллельности через семафоры
    - Асинхронная работа с файлами
    - Улучшенная обработка ошибок
    """
    # Обработчик сигналов для асинхронной функции
    def signal_handler(signum, frame):
        """Обработчик сигналов для корректного завершения"""
        print(f"\n[WARN] Received signal {signum}, gracefully shutting down async task {task_id}...")
        
        # Обработка прерывания сигналом (синхронно, так как обработчики сигналов не могут быть async)
        try:
            from django.utils import timezone
            from .models import BulkUploadTask
            
            task = BulkUploadTask.objects.get(id=task_id)
            current_time = timezone.now()
            timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
            
            task.status = 'FAILED'
            task.log += f"[{timestamp}] [WARN] Async task interrupted by signal {signum}\n"
            task.save()
            
            print(f"[SIGNAL] Task '{task.name}' marked as FAILED due to signal {signum}")
            
        except Exception as db_error:
            print(f"Warning: Failed to update task status in database: {str(db_error)}")
        except Exception as e:
            print(f"Warning: Error handling signal {signum}: {str(e)}")
    
    # Устанавливаем обработчики сигналов только в главном потоке
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Ensure Django is properly configured for this thread
        import django
        from django.conf import settings
        if not settings.configured:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
            django.setup()
        
        print(f"[START] Starting async bulk upload task {task_id}")
        
        coordinator = AsyncTaskCoordinator(task_id)
        result = await coordinator.run()
        
        if result:
            print(f"[OK] Async bulk upload task {task_id} completed successfully")
        else:
            print(f"[FAIL] Async bulk upload task {task_id} failed")
        
        return result
        
    except Exception as e:
        error_msg = f"Critical error in async bulk upload task {task_id}: {str(e)}"
        print(error_msg)
        print(f"Traceback: {traceback.format_exc()}")
        
        # ВАЖНО: Обновляем статус задачи на FAILED при критической ошибке
        try:
            from django.utils import timezone
            from .models import BulkUploadTask
            
            # ИСПРАВЛЕНИЕ: Используем асинхронный метод вместо синхронного Django ORM
            task_repo = AsyncTaskRepository()
            task = await task_repo.get_task(task_id)
            current_time = timezone.now()
            timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Обновляем статус и логи
            await task_repo.update_task_status(task, 'FAILED', f"[{timestamp}] [EXPLODE] Critical task error: {error_msg}\n")
            
            print(f"[OK] Updated task {task_id} status to FAILED")
        except Exception as update_error:
            print(f"[FAIL] Failed to update task status: {str(update_error)}")
        
        return False
    finally:
        # Always cleanup hanging FFmpeg processes
        try:
            from .async_video_uniquifier import cleanup_hanging_ffmpeg
            try:
                await asyncio.to_thread(cleanup_hanging_ffmpeg)
            except AttributeError:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, cleanup_hanging_ffmpeg)
            print("[TOOL] Cleaned up hanging FFmpeg processes")
        except Exception as e:
            print(f"Warning: Failed to cleanup FFmpeg processes: {str(e)}")
        
        # Always cleanup uniquification temp files
        try:
            await cleanup_uniquifier_temp_files()
            print("[CLEAN] Cleaned up uniquification temp files")
        except Exception as e:
            print(f"Warning: Failed to cleanup uniquification temp files: {str(e)}")
        
        # Clear engine flag regardless of result
        try:
            _clear_engine_for_task(task_id)
        except Exception:
            pass
        
        # КРИТИЧЕСКОЕ ДОБАВЛЕНИЕ: Always cleanup original video files from bulk_videos folder
        try:
            from .models import BulkUploadTask
            # ИСПРАВЛЕНИЕ: Используем асинхронный метод вместо синхронного Django ORM
            task_repo = AsyncTaskRepository()
            task = await task_repo.get_task(task_id)
            coordinator = AsyncTaskCoordinator(task_id)
            deleted_count = await coordinator._cleanup_original_video_files(task, AsyncLogger(task_id))
            print(f"[DELETE] Cleaned up {deleted_count} original video files from bulk_videos folder")
        except Exception as e:
            print(f"Warning: Failed to cleanup original video files: {str(e)}")
        
        # Always close Django database connections
        try:
            await AsyncTaskRepository.close_django_connections()
        except Exception as e:
            print(f"Warning: Failed to close Django connections: {str(e)}")

def run_async_bulk_upload_task_sync(task_id: int) -> bool:
    """
    Синхронная обертка для запуска асинхронной задачи
    Используется для совместимости с существующим кодом
    """
    # Глобальная переменная для хранения задачи при прерывании
    current_task = None
    
    def signal_handler(signum, frame):
        """Обработчик сигналов для корректного завершения"""
        nonlocal current_task
        print(f"\n[WARN] Received signal {signum}, gracefully shutting down task {task_id}...")
        
        if current_task:
            try:
                # Обновляем статус задачи на FAILED при прерывании
                from django.utils import timezone
                from .models import BulkUploadTask
                
                task = BulkUploadTask.objects.get(id=task_id)
                task.status = TaskStatus.FAILED
                task.save(update_fields=['status'])
                print(f"Task {task_id} status set to FAILED due to signal {signum}")
            except Exception as e:
                print(f"Error updating task status on signal: {e}")
        sys.exit(1)
    
    # Устанавливаем обработчики сигналов только в главном потоке
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Проверяем, находимся ли мы в async контексте
        import asyncio
        import concurrent.futures
        
        def run_in_thread():
            """Запускает async задачу в отдельном потоке с новым event loop"""
            try:
                # Ensure Django is properly configured for this thread
                import django
                from django.conf import settings
                if not settings.configured:
                    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
                    django.setup()
                
                # Создаем новый event loop для этого потока
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                
                # Запускаем async задачу
                result = new_loop.run_until_complete(run_async_bulk_upload_task(task_id))
                
                # Закрываем loop
                new_loop.close()
                return result
            except Exception as e:
                print(f"[FAIL] Error in thread: {str(e)}")
                return False
        
        # Всегда запускаем в отдельном потоке для Windows совместимости
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
            
    except Exception as e:
        print(f"[FAIL] Error running async task {task_id}: {str(e)}")
        return False

# Конфигурационные функции
def set_async_config(**kwargs) -> None:
    """Установить конфигурацию для асинхронной обработки"""
    for key, value in kwargs.items():
        if hasattr(AsyncConfig, key.upper()):
            setattr(AsyncConfig, key.upper(), value)
            print(f"[TOOL] Set {key.upper()} = {value}")

def get_async_config() -> Dict[str, Any]:
    """Получить текущую конфигурацию"""
    return {
        'max_concurrent_accounts': AsyncConfig.MAX_CONCURRENT_ACCOUNTS,
        'max_concurrent_videos': AsyncConfig.MAX_CONCURRENT_VIDEOS,
        'account_delay_min': AsyncConfig.ACCOUNT_DELAY_MIN,
        'account_delay_max': AsyncConfig.ACCOUNT_DELAY_MAX,
        'retry_attempts': AsyncConfig.RETRY_ATTEMPTS,
        'health_check_interval': AsyncConfig.HEALTH_CHECK_INTERVAL,
    } 