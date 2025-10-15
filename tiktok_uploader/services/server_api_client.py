"""
API клиент для взаимодействия с удаленными TikTok серверами.
Обеспечивает связь между Django интерфейсом и FastAPI ботами на серверах.
"""

import requests
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from django.utils import timezone
from datetime import datetime

logger = logging.getLogger(__name__)


class ServerAPIClient:
    """
    Клиент для взаимодействия с FastAPI ботом на удаленном сервере.
    """
    
    def __init__(self, server):
        """
        Инициализация клиента.
        
        Args:
            server: Экземпляр модели TikTokServer
        """
        self.server = server
        self.base_url = server.get_api_url()
        self.session = requests.Session()
        
        # Настраиваем заголовки как у браузера для обхода middleware
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
        })
        
        # Добавляем API ключ в заголовки если есть
        if server.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {server.api_key}'
            })
        
        # Timeout для запросов
        self.timeout = 30
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Tuple[bool, Any]:
        """
        Выполнить HTTP запрос к серверу.
        
        Args:
            method: HTTP метод (GET, POST, etc.)
            endpoint: API endpoint (например, '/api/servers/')
            data: Данные для отправки
            files: Файлы для загрузки
            timeout: Timeout для запроса
        
        Returns:
            Tuple[bool, Any]: (success, response_data)
        """
        url = f"{self.base_url}{endpoint}"
        timeout = timeout or self.timeout
        
        try:
            start_time = time.time()
            
            # Логируем запрос
            logger.info(f"Making {method} request to {url} with headers: {dict(self.session.headers)}")
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=data, timeout=timeout)
            elif method.upper() == 'POST':
                if files:
                    response = self.session.post(url, data=data, files=files, timeout=timeout)
                else:
                    response = self.session.post(url, json=data, timeout=timeout)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, timeout=timeout)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Записываем время отклика
            response_time = int((time.time() - start_time) * 1000)
            self.server.response_time_ms = response_time
            
            # Логируем ответ
            logger.info(f"Response from {url}: {response.status_code}, time: {response_time}ms, content-length: {len(response.text)}")
            
            # Проверяем статус код
            response.raise_for_status()
            
            # Обновляем статус сервера
            self.server.status = 'ONLINE'
            self.server.last_ping = timezone.now()
            self.server.last_error = ""
            self.server.save(update_fields=['status', 'last_ping', 'last_error', 'response_time_ms'])
            
            # Парсим ответ
            try:
                result = response.json()
                return True, result
            except ValueError:
                return True, response.text
                
        except requests.exceptions.Timeout:
            error_msg = f"Timeout connecting to server {self.server.name}"
            logger.error(error_msg)
            self._update_server_error(error_msg)
            return False, {"error": error_msg}
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error to server {self.server.name}: {str(e)}"
            logger.error(error_msg)
            self._update_server_error(error_msg)
            return False, {"error": error_msg}
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error from server {self.server.name}: {response.status_code} - {response.text}"
            logger.error(error_msg)
            self._update_server_error(error_msg)
            return False, {"error": error_msg, "status_code": response.status_code}
            
        except Exception as e:
            error_msg = f"Unexpected error communicating with server {self.server.name}: {str(e)}"
            logger.error(error_msg)
            self._update_server_error(error_msg)
            return False, {"error": error_msg}
    
    def _update_server_error(self, error_message: str):
        """Обновить статус сервера при ошибке"""
        self.server.status = 'ERROR'
        self.server.last_error = error_message
        self.server.save(update_fields=['status', 'last_error'])
    
    # ========================================================================
    # ПРОВЕРКА ДОСТУПНОСТИ И ЗДОРОВЬЯ
    # ========================================================================
    
    def ping(self) -> [bool, Any]:
        """
        Проверить доступность сервера.
        Пробует разные варианты адресов для локальных серверов.
        
        Returns:
            bool: True если сервер доступен
            Any: JSON ответа
        """
        # Сначала пробуем основной URL
        success, result = self._make_request('GET', '/health', timeout=10)
        
        # Если не удалось подключиться и это 0.0.0.0, пробуем localhost
        if not success and self.server.host == '0.0.0.0':
            logger.info(f"Trying localhost for server {self.server.name}")
            original_url = self.base_url
            self.base_url = f"http://localhost:{self.server.port}"
            
            try:
                success, result = self._make_request('GET', '/health', timeout=10)
                if success:
                    logger.info(f"Successfully connected to {self.server.name} via localhost")
            except Exception as e:
                logger.warning(f"Failed to connect via localhost: {e}")
            finally:
                # Восстанавливаем оригинальный URL
                self.base_url = original_url
        
        return success, result
    
    def get_server_info(self) -> Tuple[bool, Dict]:
        """
        Получить информацию о сервере.
        
        Returns:
            Tuple[bool, Dict]: (success, server_info)
        """
        success, result = self._make_request('GET', '/ip-info')
        return success, result
    
    def get_logs(self, lines: int = 100) -> Tuple[bool, Dict]:
        """
        Получить логи сервера.
        
        Args:
            lines: Количество строк логов
        
        Returns:
            Tuple[bool, Dict]: (success, logs_data)
        """
        success, result = self._make_request('GET', f'/logs?lines={lines}')
        return success, result
    
    # ========================================================================
    # УПРАВЛЕНИЕ АККАУНТАМИ
    # ========================================================================
    
    def prepare_accounts(
        self, 
        count: int, 
        client: str,
        order: str = 'newest'
    ) -> Tuple[bool, Dict]:
        """
        Подготовить аккаунты на сервере (получить из БД и создать профили Dolphin).
        
        Args:
            count: Количество аккаунтов
            client: Имя клиента
            order: Порядок сортировки (newest/oldest)
        
        Returns:
            Tuple[bool, Dict]: (success, result)
        """
        data = {
            'count': count,
            'client': client,
            'order': order
        }
        success, result = self._make_request('POST', '/upload/prepare_accounts', data=data)
        return success, result
    
    def get_accounts_count(self) -> Tuple[bool, int]:
        """
        Получить количество аккаунтов на сервере.
        
        Returns:
            Tuple[bool, int]: (success, count)
        """
        success, result = self._make_request('GET', '/get_accounts_from_db')
        if success and isinstance(result, dict):
            return True, result.get('count', 0)
        return False, 0
    
    def get_videos_count(self) -> Tuple[bool, int]:
        """
        Получить количество видео на сервере.
        
        Returns:
            Tuple[bool, int]: (success, count)
        """
        success, result = self._make_request('GET', '/get_videos')
        if success and isinstance(result, dict):
            return True, result.get('count', 0)
        return False, 0
    
    def get_dolphin_profiles_count(self) -> Tuple[bool, int]:
        """
        Получить количество профилей Dolphin на сервере.
        
        Returns:
            Tuple[bool, int]: (success, count)
        """
        success, result = self._make_request('GET', '/get_dolphin_profiles')
        if success and isinstance(result, dict):
            return True, result.get('count', 0)
        return False, 0
    
    # ========================================================================
    # ЗАГРУЗКА ФАЙЛОВ
    # ========================================================================
    
    def upload_videos(self, video_files: List[Tuple[str, bytes]]) -> Tuple[bool, Dict]:
        """
        Загрузить видео файлы на сервер.
        
        Args:
            video_files: Список кортежей (filename, file_content)
        
        Returns:
            Tuple[bool, Dict]: (success, result)
        """
        files = {}
        for i, (filename, content) in enumerate(video_files):
            files[f'file_{i}'] = (filename, content, 'video/mp4')
        
        success, result = self._make_request('POST', '/upload/upload_videos/', files=files, timeout=300)
        return success, result
    
    def upload_titles(self, titles_content: str, filename: str = 'titles.txt') -> Tuple[bool, Dict]:
        """
        Загрузить файл с заголовками на сервер.
        
        Args:
            titles_content: Содержимое файла с заголовками
            filename: Имя файла
        
        Returns:
            Tuple[bool, Dict]: (success, result)
        """
        files = {
            'file': (filename, titles_content.encode('utf-8'), 'text/plain')
        }
        success, result = self._make_request('POST', '/upload/upload_titles', files=files)
        return success, result
    
    def upload_accounts_for_boosting(self, accounts_content: str, filename: str = 'accounts.txt') -> Tuple[bool, Dict]:
        """
        Загрузить файл с аккаунтами для прогрева.
        
        Args:
            accounts_content: Содержимое файла с аккаунтами
            filename: Имя файла
        
        Returns:
            Tuple[bool, Dict]: (success, result)
        """
        files = {
            'file': (filename, accounts_content.encode('utf-8'), 'text/plain')
        }
        success, result = self._make_request('POST', '/booster/upload_accounts', files=files)
        return success, result
    
    def upload_proxies(self, proxies_content: str, filename: str = 'proxies.txt') -> Tuple[bool, Dict]:
        """
        Загрузить файл с прокси на сервер.
        
        Args:
            proxies_content: Содержимое файла с прокси
            filename: Имя файла
        
        Returns:
            Tuple[bool, Dict]: (success, result)
        """
        files = {
            'file': (filename, proxies_content.encode('utf-8'), 'text/plain')
        }
        success, result = self._make_request('POST', '/booster/upload_proxies', files=files)
        return success, result
    
    # ========================================================================
    # ЗАДАЧИ (API V2)
    # ========================================================================
    
    def create_upload_task(
        self,
        client: str,
        accounts_count: int,
        cycles: int,
        videos_data: List[Dict],
        tag: Optional[str] = None,
        cycle_timeout_minutes: int = 30,
        delay_min_sec: int = 30,
        delay_max_sec: int = 60,
        default_settings: Optional[Dict] = None
    ) -> Tuple[bool, Dict]:
        """
        Создать задачу загрузки видео (API v2 - всё в одном запросе).
        
        Args:
            client: Имя клиента
            accounts_count: Количество аккаунтов для использования
            cycles: Количество циклов загрузки
            videos_data: Список словарей с данными видео:
                {
                    "filename": "video1.mp4",
                    "file_base64": "...",
                    "caption": "Описание",
                    "hashtags": ["tag1", "tag2"],
                    "music_name": "...",
                    "location": "...",
                    "mentions": ["@user1"]
                }
            tag: Тематика аккаунтов (опционально)
            cycle_timeout_minutes: Задержка между циклами
            delay_min_sec: Минимальная задержка между загрузками
            delay_max_sec: Максимальная задержка между загрузками
            default_settings: Настройки по умолчанию (allow_comments и т.д.)
        
        Returns:
            Tuple[bool, Dict]: (success, result with task_id)
        """
        data = {
            'client': client,
            'accounts_count': accounts_count,
            'cycles': cycles,
            'cycle_timeout_minutes': cycle_timeout_minutes,
            'delay_between_uploads': {
                'min_seconds': delay_min_sec,
                'max_seconds': delay_max_sec
            },
            'videos': videos_data
        }
        
        if tag:
            data['tag'] = tag
        
        if default_settings:
            data['default_settings'] = default_settings
        
        # Этот запрос создает задачу и возвращает task_id
        success, result = self._make_request('POST', '/tasks/upload', data=data, timeout=60)
        return success, result
    
    def create_warmup_task(
        self,
        client: str,
        accounts_count: int,
        tag: Optional[str] = None,
        settings: Optional[Dict] = None,
        use_cookie_robot: bool = False,
        accounts: Optional[List[Dict]] = None
    ) -> Tuple[bool, Dict]:
        """
        Создать задачу прогрева аккаунтов.
        
        Args:
            client: Имя клиента
            accounts_count: Количество аккаунтов
            tag: Тематика аккаунтов (опционально)
            settings: Настройки прогрева (количество действий и т.д.)
            use_cookie_robot: Использовать ли cookie robot
        
        Returns:
            Tuple[bool, Dict]: (success, result with task_id)
        """
        data = {
            'client': client,
            'accounts_count': accounts_count,
            'use_cookie_robot': use_cookie_robot
        }
        
        if tag:
            data['tag'] = tag
        
        if settings:
            data['settings'] = settings
        
        # Если переданы аккаунты, отправляем их полные данные на сервер
        if accounts:
            data['accounts'] = accounts
        
        success, result = self._make_request('POST', '/tasks/warmup', data=data, timeout=60)
        return success, result
    
    def get_task_status(self, task_id: str) -> Tuple[bool, Dict]:
        """
        Получить статус задачи.
        
        Args:
            task_id: ID задачи на сервере
        
        Returns:
            Tuple[bool, Dict]: (success, task_status_data)
        """
        success, result = self._make_request('GET', f'/tasks/{task_id}')
        return success, result
    
    def stop_task(self, task_id: str) -> Tuple[bool, Dict]:
        """
        Остановить выполняющуюся задачу.
        
        Args:
            task_id: ID задачи на сервере
        
        Returns:
            Tuple[bool, Dict]: (success, result)
        """
        success, result = self._make_request('POST', f'/tasks/{task_id}/stop')
        return success, result
    
    def delete_task(self, task_id: str) -> Tuple[bool, Dict]:
        """
        Удалить задачу.
        
        Args:
            task_id: ID задачи на сервере
        
        Returns:
            Tuple[bool, Dict]: (success, result)
        """
        success, result = self._make_request('DELETE', f'/tasks/{task_id}')
        return success, result
    
    def get_all_tasks(
        self, 
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[bool, Dict]:
        """
        Получить список всех задач на сервере.
        
        Args:
            status: Фильтр по статусу (QUEUED, RUNNING, COMPLETED, FAILED)
            task_type: Фильтр по типу (upload, warmup)
            limit: Лимит
            offset: Смещение
        
        Returns:
            Tuple[bool, Dict]: (success, tasks_data)
        """
        params = {'limit': limit, 'offset': offset}
        if status:
            params['status'] = status
        if task_type:
            params['type'] = task_type
        
        success, result = self._make_request('GET', '/tasks', data=params)
        return success, result
    
    def check_dolphin_profiles(self, usernames: List[str]) -> Tuple[bool, Dict]:
        """
        Проверить наличие профилей Dolphin для аккаунтов на сервере.
        
        Args:
            usernames: Список username'ов для проверки
        
        Returns:
            Tuple[bool, Dict]: (success, result with profiles_found and profiles_missing)
        """
        data = {'usernames': usernames}
        success, result = self._make_request('POST', '/accounts/check-profiles', data=data)
        return success, result
    
    # ========================================================================
    # ПРОГРЕВ АККАУНТОВ
    # ========================================================================
    
    def prepare_booster_accounts(
        self,
        use_cookie_robot: bool,
        client: str
    ) -> Tuple[bool, Dict]:
        """
        Подготовить аккаунты для прогрева.
        
        Args:
            use_cookie_robot: Использовать ли cookie robot
            client: Имя клиента
        
        Returns:
            Tuple[bool, Dict]: (success, result)
        """
        data = {
            'use_cookie_robot': use_cookie_robot,
            'client': client
        }
        success, result = self._make_request('POST', '/booster/prepare_accounts', data=data)
        return success, result
    
    def start_booster(self) -> Tuple[bool, Dict]:
        """
        Запустить прогрев аккаунтов.
        
        Returns:
            Tuple[bool, Dict]: (success, result)
        """
        # Этот запрос может выполняться очень долго
        success, result = self._make_request('POST', '/booster/start_booster', timeout=7200)
        return success, result
    
    # ========================================================================
    # УТИЛИТЫ
    # ========================================================================
    
    def close(self):
        """Закрыть сессию"""
        self.session.close()


class ServerManager:
    """
    Менеджер для управления множественными серверами.
    Обеспечивает балансировку нагрузки и мониторинг.
    """
    
    @staticmethod
    def get_client(server) -> ServerAPIClient:
        """
        Получить API клиент для сервера.
        
        Args:
            server: Экземпляр модели TikTokServer
        
        Returns:
            ServerAPIClient: Клиент для взаимодействия с сервером
        """
        return ServerAPIClient(server)
    
    @staticmethod
    def ping_all_servers():
        """
        Проверить доступность всех активных серверов.
        Обновляет статусы в базе данных.
        """
        from tiktok_uploader.models import TikTokServer, ServerHealthLog
        from django.utils import timezone
        import time
        
        active_servers = TikTokServer.objects.filter(is_active=True)
        results = []
        
        for server in active_servers:
            try:
                start_time = time.time()
                
                client = ServerAPIClient(server)
                success, result = client.ping()
                client.close()
                
                response_time = (time.time() - start_time) * 1000
                
                if success:
                    server.status = 'online'
                    server.last_health_check = timezone.now()
                    server.save()
                    
                    # Создаем запись в логах
                    ServerHealthLog.objects.create(
                        server=server,
                        is_online=True,
                        response_time_ms=int(response_time),
                        error_message=""
                    )
                else:
                    server.status = 'offline'
                    server.save()
                    
                    error_msg = result.get('error') if isinstance(result, dict) else str(result)
                    
                    # Создаем запись в логах
                    ServerHealthLog.objects.create(
                        server=server,
                        is_online=False,
                        response_time_ms=int(response_time),
                        error_message=error_msg
                    )
                
                results.append({
                    'server': server.name,
                    'server_id': server.id,
                    'is_online': success,
                    'status': server.status,
                    'error': result.get('error') if isinstance(result, dict) and not success else None
                })
            except Exception as e:
                server.status = 'offline'
                server.save()
                
                # Создаем запись в логах
                ServerHealthLog.objects.create(
                    server=server,
                    is_online=False,
                    response_time_ms=0,
                    error_message=str(e)
                )
                
                results.append({
                    'server': server.name,
                    'server_id': server.id,
                    'is_online': False,
                    'status': 'offline',
                    'error': str(e)
                })
        
        return results
    
    @staticmethod
    def get_available_servers():
        """
        Получить список доступных серверов для новых задач.
        
        Returns:
            QuerySet: Доступные серверы, отсортированные по приоритету
        """
        from tiktok_uploader.models import TikTokServer
        
        return TikTokServer.objects.filter(
            is_active=True,
            status='ONLINE'
        ).order_by('priority', 'active_tasks')
    
    @staticmethod
    def select_best_server():
        """
        Выбрать наилучший сервер для новой задачи.
        
        Returns:
            TikTokServer or None: Лучший доступный сервер
        """
        from django.db.models import F
        
        available_servers = ServerManager.get_available_servers()
        
        # Фильтруем серверы с доступной емкостью
        servers_with_capacity = available_servers.filter(
            active_tasks__lt=F('max_concurrent_tasks')
        )
        
        if servers_with_capacity.exists():
            return servers_with_capacity.first()
        
        return None
    
    @staticmethod
    def update_server_stats(server):
        """
        Обновить статистику сервера.
        
        Args:
            server: Экземпляр модели TikTokServer
        """
        client = ServerAPIClient(server)
        
        # Получаем количество аккаунтов
        success, accounts_count = client.get_accounts_count()
        if success:
            server.total_accounts = accounts_count
        
        # Получаем количество видео  
        success, videos_count = client.get_videos_count()
        if success:
            # Можно сохранить в отдельное поле если нужно
            pass
        
        # Получаем количество профилей Dolphin
        success, profiles_count = client.get_dolphin_profiles_count()
        if success:
            # Можно сохранить в отдельное поле если нужно
            pass
        
        server.save(update_fields=['total_accounts'])
        client.close()
    
    @staticmethod
    def create_health_log(server):
        """
        Создать запись в логе здоровья сервера.
        
        Args:
            server: Экземпляр модели TikTokServer
        
        Returns:
            ServerHealthLog: Созданная запись лога
        """
        from tiktok_uploader.models import ServerHealthLog
        
        client = ServerAPIClient(server)
        
        # Проверяем доступность
        is_online = client.ping()
        
        # Получаем статистику
        accounts_count = 0
        videos_count = 0
        profiles_count = 0
        
        if is_online:
            success, count = client.get_accounts_count()
            if success:
                accounts_count = count
            
            success, count = client.get_videos_count()
            if success:
                videos_count = count
            
            success, count = client.get_dolphin_profiles_count()
            if success:
                profiles_count = count
        
        # Создаем запись лога
        health_log = ServerHealthLog.objects.create(
            server=server,
            is_online=is_online,
            response_time_ms=server.response_time_ms,
            error_message=server.last_error if not is_online else "",
            accounts_count=accounts_count,
            videos_count=videos_count,
            dolphin_profiles_count=profiles_count
        )
        
        client.close()
        return health_log
