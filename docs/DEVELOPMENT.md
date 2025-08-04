# Руководство по разработке

## 📋 Содержание

- [Архитектура проекта](#архитектура-проекта)
- [Принципы разработки](#принципы-разработки)
- [Структура кода](#структура-кода)
- [Процесс разработки](#процесс-разработки)
- [Тестирование](#тестирование)
- [Отладка](#отладка)
- [Оптимизация](#оптимизация)

## 🏗️ Архитектура проекта

### Общая архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Interface (Django)                   │
├─────────────────────────────────────────────────────────────┤
│                    Business Logic Layer                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │   Task Manager  │  │ Account Manager │  │ Video Proc  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                   Automation Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │  Playwright     │  │  Dolphin Anty   │  │ Human Sim   │  │
│  │  Automation     │  │  Integration    │  │ ulation     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                   External Services                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │   Instagram     │  │  reCAPTCHA API  │  │ Email API   │  │
│  │     Platform    │  │                 │  │             │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Слои приложения

#### 1. Presentation Layer (Django Views)
- **Назначение**: Обработка HTTP запросов и отображение данных
- **Компоненты**: Views, Templates, Forms
- **Принципы**: Тонкие контроллеры, толстые модели

#### 2. Business Logic Layer
- **Назначение**: Основная бизнес-логика приложения
- **Компоненты**: Services, Managers, Utilities
- **Принципы**: Разделение ответственности, инверсия зависимостей

#### 3. Data Access Layer
- **Назначение**: Работа с данными и внешними API
- **Компоненты**: Models, Repositories, API Clients
- **Принципы**: Абстракция данных, единый интерфейс

#### 4. Infrastructure Layer
- **Назначение**: Техническая инфраструктура
- **Компоненты**: Database, Cache, External Services
- **Принципы**: Конфигурируемость, отказоустойчивость

### Модульная архитектура

```
uploader/
├── core/                    # Основные компоненты
│   ├── models.py           # Модели данных
│   ├── views.py            # Представления
│   ├── forms.py            # Формы
│   └── admin.py            # Админ-панель
├── automation/              # Автоматизация
│   ├── instagram_automation.py
│   ├── human_behavior.py
│   ├── browser_utils.py
│   └── captcha_solver.py
├── tasks/                   # Задачи
│   ├── bulk_tasks_playwright.py
│   ├── async_bulk_tasks.py
│   └── task_utils.py
├── services/                # Сервисы
│   ├── account_service.py
│   ├── proxy_service.py
│   └── video_service.py
└── utils/                   # Утилиты
    ├── constants.py
    ├── logging_utils.py
    └── helpers.py
```

## 🎯 Принципы разработки

### SOLID принципы

#### 1. Single Responsibility Principle (SRP)
```python
# ✅ Правильно - каждый класс имеет одну ответственность
class AccountManager:
    def create_account(self, account_data):
        # Только создание аккаунта
        pass

class ProxyManager:
    def assign_proxy(self, account, proxy):
        # Только назначение прокси
        pass

# ❌ Неправильно - класс делает слишком много
class AccountHandler:
    def create_account(self, account_data):
        # Создание аккаунта
        pass
    
    def assign_proxy(self, account, proxy):
        # Назначение прокси
        pass
    
    def send_email(self, account):
        # Отправка email
        pass
```

#### 2. Open/Closed Principle (OCP)
```python
# ✅ Правильно - расширяемо без изменения
class BaseAutomation:
    def execute(self):
        raise NotImplementedError

class InstagramAutomation(BaseAutomation):
    def execute(self):
        # Реализация для Instagram
        pass

class TikTokAutomation(BaseAutomation):
    def execute(self):
        # Реализация для TikTok
        pass
```

#### 3. Liskov Substitution Principle (LSP)
```python
# ✅ Правильно - подклассы могут заменять базовый класс
class BaseUploader:
    def upload(self, video):
        raise NotImplementedError

class InstagramUploader(BaseUploader):
    def upload(self, video):
        # Загрузка в Instagram
        pass

class TikTokUploader(BaseUploader):
    def upload(self, video):
        # Загрузка в TikTok
        pass
```

#### 4. Interface Segregation Principle (ISP)
```python
# ✅ Правильно - специфичные интерфейсы
class VideoProcessor:
    def process_video(self, video):
        pass

class AccountAuthenticator:
    def authenticate(self, account):
        pass

class ProxyManager:
    def manage_proxy(self, proxy):
        pass
```

#### 5. Dependency Inversion Principle (DIP)
```python
# ✅ Правильно - зависимости от абстракций
class UploadService:
    def __init__(self, uploader: BaseUploader, authenticator: BaseAuthenticator):
        self.uploader = uploader
        self.authenticator = authenticator
    
    def upload_video(self, video, account):
        if self.authenticator.authenticate(account):
            return self.uploader.upload(video)
```

### DRY (Don't Repeat Yourself)

```python
# ✅ Правильно - переиспользуемый код
class BaseSelector:
    def find_element(self, selector):
        return self.page.locator(selector)
    
    def click_element(self, selector):
        self.find_element(selector).click()
    
    def fill_element(self, selector, value):
        self.find_element(selector).fill(value)

class InstagramSelector(BaseSelector):
    def login(self, username, password):
        self.fill_element(self.USERNAME_FIELD, username)
        self.fill_element(self.PASSWORD_FIELD, password)
        self.click_element(self.LOGIN_BUTTON)
```

### KISS (Keep It Simple, Stupid)

```python
# ✅ Правильно - простой и понятный код
def upload_video(video_path, account):
    try:
        # 1. Аутентификация
        authenticate(account)
        
        # 2. Загрузка видео
        upload_file(video_path)
        
        # 3. Опубликовать
        publish()
        
        return True
    except Exception as e:
        log_error(e)
        return False

# ❌ Неправильно - излишне сложно
def execute_video_upload_workflow_with_comprehensive_error_handling_and_retry_mechanism(
    video_file_path, 
    account_credentials, 
    retry_count=3, 
    timeout=300
):
    # Сложная логика с множественными проверками
    pass
```

## 📁 Структура кода

### Организация файлов

```
project/
├── instagram_uploader/          # Django проект
│   ├── settings.py             # Настройки
│   ├── urls.py                 # URL маршруты
│   └── wsgi.py                 # WSGI конфигурация
├── uploader/                   # Основное приложение
│   ├── models.py               # Модели данных
│   ├── views.py                # Представления
│   ├── forms.py                # Формы
│   ├── admin.py                # Админ-панель
│   ├── constants.py            # Константы
│   ├── human_behavior.py       # Симуляция поведения
│   ├── instagram_automation.py # Автоматизация
│   ├── bulk_tasks_playwright.py # Массовые задачи
│   ├── async_bulk_tasks.py     # Асинхронные задачи
│   ├── captcha_solver.py       # Решение капчи
│   ├── crop_handler.py         # Обработка обрезки
│   ├── browser_utils.py        # Утилиты браузера
│   ├── task_utils.py           # Утилиты задач
│   ├── account_utils.py        # Утилиты аккаунтов
│   ├── proxy_diagnostics.py    # Диагностика прокси
│   ├── logging_utils.py        # Логирование
│   ├── middleware.py           # Middleware
│   ├── urls.py                 # URL маршруты
│   ├── utils.py                # Общие утилиты
│   ├── selectors_config.py     # Конфигурация селекторов
│   ├── human_behavior_config.py # Конфигурация поведения
│   ├── login_optimized.py      # Оптимизированный логин
│   ├── async_video_uniquifier.py # Уникализация видео
│   └── migrations/             # Миграции БД
├── bot/                        # Автономный бот
│   └── src/instagram_uploader/
│       ├── dolphin_anty.py     # Интеграция с Dolphin
│       ├── upload_playwright.py # Загрузка через Playwright
│       ├── auth_playwright.py  # Аутентификация
│       ├── browser_dolphin.py  # Работа с браузером
│       ├── isolated_cookie_robot.py # Cookie робот
│       ├── email_client.py     # Email клиент
│       ├── tfa_api.py          # 2FA API
│       ├── util.py             # Утилиты
│       ├── config.toml         # Конфигурация
│       └── proxy_auth_extension/ # Расширение прокси
├── docs/                       # Документация
├── media/                      # Медиа файлы
├── prepared_videos/            # Подготовленные видео
├── requirements.txt            # Зависимости Python
├── manage.py                   # Django management
└── README.md                   # Основная документация
```

### Соглашения по именованию

#### Файлы и папки
```python
# ✅ Правильно
instagram_automation.py
human_behavior.py
bulk_tasks_playwright.py
async_bulk_tasks.py

# ❌ Неправильно
InstagramAutomation.py
humanBehavior.py
bulk-tasks-playwright.py
```

#### Классы
```python
# ✅ Правильно - PascalCase
class InstagramAutomation:
    pass

class HumanBehaviorSimulator:
    pass

class BulkUploadTask:
    pass

# ❌ Неправильно
class instagram_automation:
    pass

class humanBehaviorSimulator:
    pass
```

#### Функции и методы
```python
# ✅ Правильно - snake_case
def upload_video(video_path):
    pass

def authenticate_account(account):
    pass

def process_bulk_task(task_id):
    pass

# ❌ Неправильно
def uploadVideo(videoPath):
    pass

def authenticateAccount(account):
    pass
```

#### Переменные
```python
# ✅ Правильно - snake_case
video_path = "/path/to/video.mp4"
account_username = "test_user"
max_retry_attempts = 3

# ❌ Неправильно
videoPath = "/path/to/video.mp4"
accountUsername = "test_user"
maxRetryAttempts = 3
```

#### Константы
```python
# ✅ Правильно - UPPER_SNAKE_CASE
MAX_VIDEOS_PER_ACCOUNT = 50
DEFAULT_TIMEOUT = 30000
HUMAN_DELAY_MIN = 0.5

# ❌ Неправильно
maxVideosPerAccount = 50
defaultTimeout = 30000
humanDelayMin = 0.5
```

### Документация кода

#### Docstrings для классов
```python
class InstagramAutomation:
    """
    Автоматизация загрузки видео в Instagram.
    
    Этот класс предоставляет методы для автоматизации процесса
    загрузки видео в Instagram с использованием Playwright.
    
    Attributes:
        browser: Экземпляр браузера Playwright
        page: Активная страница браузера
        account: Данные аккаунта Instagram
        
    Example:
        >>> automation = InstagramAutomation(account_data)
        >>> automation.upload_video("/path/to/video.mp4")
    """
    
    def __init__(self, account_data):
        """
        Инициализация автоматизации.
        
        Args:
            account_data (dict): Данные аккаунта Instagram
                {
                    'username': 'user_name',
                    'password': 'user_password',
                    'proxy': proxy_data
                }
                
        Raises:
            ValueError: Если данные аккаунта некорректны
        """
        self.account = account_data
        self.browser = None
        self.page = None
```

#### Docstrings для методов
```python
def upload_video(self, video_path, caption=None, location=None):
    """
    Загружает видео в Instagram.
    
    Args:
        video_path (str): Путь к файлу видео
        caption (str, optional): Подпись к видео
        location (str, optional): Локация для видео
        
    Returns:
        bool: True если загрузка успешна, False в противном случае
        
    Raises:
        FileNotFoundError: Если файл видео не найден
        AuthenticationError: Если не удалось аутентифицироваться
        UploadError: Если произошла ошибка при загрузке
        
    Example:
        >>> success = automation.upload_video("/path/to/video.mp4", "My video")
        >>> print(success)
        True
    """
    try:
        # Проверка файла
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Аутентификация
        if not self.authenticate():
            raise AuthenticationError("Failed to authenticate")
        
        # Загрузка видео
        self._navigate_to_upload()
        self._select_video(video_path)
        
        # Настройка параметров
        if caption:
            self._set_caption(caption)
        if location:
            self._set_location(location)
        
        # Публикация
        self._publish_video()
        
        return True
        
    except Exception as e:
        self.logger.error(f"Upload failed: {e}")
        return False
```

#### Inline комментарии
```python
def process_video(self, video_path):
    # Проверяем существование файла
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    # Получаем информацию о видео
    video_info = self._get_video_info(video_path)
    
    # Проверяем формат (только MP4, MOV, AVI)
    if video_info['format'] not in ['mp4', 'mov', 'avi']:
        raise ValueError(f"Unsupported format: {video_info['format']}")
    
    # Проверяем размер (максимум 100MB)
    if video_info['size'] > 100 * 1024 * 1024:  # 100MB в байтах
        raise ValueError(f"Video too large: {video_info['size']} bytes")
    
    # Обрабатываем видео
    processed_path = self._process_video(video_path)
    
    return processed_path
```

## 🔄 Процесс разработки

### Workflow разработки

#### 1. Планирование
```bash
# Создание issue в GitHub
# Описание задачи, требований и критериев приемки
```

#### 2. Создание ветки
```bash
# Создание feature ветки
git checkout -b feature/new-upload-method

# Или bugfix ветки
git checkout -b bugfix/fix-authentication-issue
```

#### 3. Разработка
```python
# Создание новой функциональности
class NewUploadMethod:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def upload(self, video_path):
        # Реализация новой логики загрузки
        pass
```

#### 4. Тестирование
```python
# Написание тестов
class TestNewUploadMethod(TestCase):
    def setUp(self):
        self.uploader = NewUploadMethod()
    
    def test_upload_success(self):
        result = self.uploader.upload("/test/video.mp4")
        self.assertTrue(result)
    
    def test_upload_invalid_file(self):
        with self.assertRaises(FileNotFoundError):
            self.uploader.upload("/nonexistent/video.mp4")
```

#### 5. Code Review
```bash
# Создание Pull Request
git push origin feature/new-upload-method

# Code review через GitHub
# Обсуждение изменений
# Внесение правок при необходимости
```

#### 6. Слияние
```bash
# Слияние в main ветку
git checkout main
git merge feature/new-upload-method
git push origin main
```

### Стандарты кодирования

#### PEP 8 Compliance
```python
# ✅ Правильно - соблюдение PEP 8
import os
import logging
from typing import Optional, Dict, List

class VideoProcessor:
    """Обработчик видео файлов."""
    
    def __init__(self, config: Dict[str, any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def process_video(self, video_path: str) -> Optional[str]:
        """Обрабатывает видео файл."""
        try:
            # Проверка файла
            if not os.path.exists(video_path):
                self.logger.error(f"File not found: {video_path}")
                return None
            
            # Обработка
            result = self._process(video_path)
            return result
            
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            return None
    
    def _process(self, video_path: str) -> str:
        """Внутренний метод обработки."""
        # Реализация обработки
        return f"processed_{video_path}"
```

#### Type Hints
```python
from typing import Optional, Dict, List, Union, Tuple

def upload_video(
    video_path: str,
    account: Dict[str, str],
    options: Optional[Dict[str, any]] = None
) -> Tuple[bool, str]:
    """
    Загружает видео в Instagram.
    
    Args:
        video_path: Путь к видео файлу
        account: Данные аккаунта
        options: Дополнительные опции
        
    Returns:
        Tuple[bool, str]: (успех, сообщение)
    """
    pass

def get_account_status(account_id: int) -> str:
    """Получает статус аккаунта."""
    pass

def process_videos(video_list: List[str]) -> List[bool]:
    """Обрабатывает список видео."""
    pass
```

#### Error Handling
```python
class UploadError(Exception):
    """Исключение для ошибок загрузки."""
    pass

class AuthenticationError(Exception):
    """Исключение для ошибок аутентификации."""
    pass

def upload_with_error_handling(video_path: str) -> bool:
    """Загрузка с обработкой ошибок."""
    try:
        # Попытка загрузки
        result = upload_video(video_path)
        return result
        
    except FileNotFoundError as e:
        logger.error(f"Video file not found: {e}")
        return False
        
    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        return False
        
    except UploadError as e:
        logger.error(f"Upload failed: {e}")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False
```

## 🧪 Тестирование

### Типы тестов

#### 1. Unit Tests
```python
# tests/test_models.py
from django.test import TestCase
from uploader.models import InstagramAccount, Proxy

class InstagramAccountTest(TestCase):
    def setUp(self):
        """Настройка тестовых данных."""
        self.proxy = Proxy.objects.create(
            host='127.0.0.1',
            port=8080,
            proxy_type='HTTP'
        )
        
        self.account = InstagramAccount.objects.create(
            username='test_user',
            password='test_pass',
            proxy=self.proxy
        )
    
    def test_account_creation(self):
        """Тест создания аккаунта."""
        self.assertEqual(self.account.username, 'test_user')
        self.assertEqual(self.account.status, 'ACTIVE')
        self.assertEqual(self.account.proxy, self.proxy)
    
    def test_account_str_representation(self):
        """Тест строкового представления."""
        self.assertEqual(str(self.account), 'test_user')
    
    def test_account_to_dict(self):
        """Тест конвертации в словарь."""
        account_dict = self.account.to_dict()
        self.assertEqual(account_dict['username'], 'test_user')
        self.assertEqual(account_dict['password'], 'test_pass')
```

#### 2. Integration Tests
```python
# tests/test_integration.py
from django.test import TestCase
from uploader.services import UploadService
from uploader.models import InstagramAccount, BulkUploadTask

class UploadServiceIntegrationTest(TestCase):
    def setUp(self):
        """Настройка интеграционных тестов."""
        self.account = InstagramAccount.objects.create(
            username='test_user',
            password='test_pass'
        )
        
        self.task = BulkUploadTask.objects.create(
            name='Test Task'
        )
        
        self.service = UploadService()
    
    def test_complete_upload_workflow(self):
        """Тест полного процесса загрузки."""
        # Создание задачи
        result = self.service.create_task(
            account=self.account,
            video_path='/test/video.mp4'
        )
        
        self.assertTrue(result)
        
        # Проверка статуса
        task = BulkUploadTask.objects.get(id=result)
        self.assertEqual(task.status, 'PENDING')
```

#### 3. Functional Tests
```python
# tests/test_functional.py
from django.test import TestCase, Client
from django.urls import reverse
from uploader.models import InstagramAccount

class FunctionalTest(TestCase):
    def setUp(self):
        """Настройка функциональных тестов."""
        self.client = Client()
        self.account = InstagramAccount.objects.create(
            username='test_user',
            password='test_pass'
        )
    
    def test_bulk_upload_page(self):
        """Тест страницы массовой загрузки."""
        response = self.client.get(reverse('bulk_upload'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Массовая загрузка')
    
    def test_create_bulk_task(self):
        """Тест создания массовой задачи."""
        data = {
            'name': 'Test Task',
            'accounts': [self.account.id],
            'videos': ['/test/video.mp4']
        }
        
        response = self.client.post(
            reverse('create_bulk_task'),
            data
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect
```

### Mocking и Stubbing

```python
from unittest.mock import Mock, patch, MagicMock
from uploader.services import InstagramService

class InstagramServiceTest(TestCase):
    def setUp(self):
        self.service = InstagramService()
    
    @patch('uploader.services.requests.post')
    def test_api_call(self, mock_post):
        """Тест API вызова с моком."""
        # Настройка мока
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_post.return_value = mock_response
        
        # Выполнение теста
        result = self.service.call_api('/test/endpoint')
        
        # Проверки
        self.assertTrue(result)
        mock_post.assert_called_once()
    
    @patch('uploader.services.Playwright')
    def test_browser_automation(self, mock_playwright):
        """Тест автоматизации браузера."""
        # Настройка мока браузера
        mock_browser = Mock()
        mock_page = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        
        # Выполнение теста
        result = self.service.automate_browser()
        
        # Проверки
        self.assertTrue(result)
        mock_page.goto.assert_called_once()
```

### Test Coverage

```bash
# Установка coverage
pip install coverage

# Запуск тестов с покрытием
coverage run --source='.' manage.py test

# Генерация отчета
coverage report

# HTML отчет
coverage html
```

## 🐛 Отладка

### Логирование

#### Настройка логгера
```python
import logging

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Создание handler
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

# Создание formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

# Добавление handler к логгеру
logger.addHandler(handler)
```

#### Использование логгера
```python
class InstagramAutomation:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def upload_video(self, video_path):
        self.logger.info(f"Starting upload for video: {video_path}")
        
        try:
            # Аутентификация
            self.logger.debug("Authenticating account...")
            if not self.authenticate():
                self.logger.error("Authentication failed")
                return False
            
            # Загрузка видео
            self.logger.debug("Uploading video...")
            self._upload_file(video_path)
            
            # Публикация
            self.logger.debug("Publishing video...")
            self._publish()
            
            self.logger.info("Upload completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Upload failed: {e}", exc_info=True)
            return False
```

### Отладочные инструменты

#### pdb (Python Debugger)
```python
import pdb

def complex_function():
    # Некоторые вычисления
    result = calculate_something()
    
    # Точка останова для отладки
    pdb.set_trace()
    
    # Продолжение выполнения
    return process_result(result)
```

#### ipdb (Enhanced Debugger)
```python
import ipdb

def debug_function():
    # Установка точки останова
    ipdb.set_trace()
    
    # Интерактивная отладка
    # Доступны команды: n (next), s (step), c (continue), p (print)
    pass
```

#### Логирование с контекстом
```python
import logging
from contextlib import contextmanager

@contextmanager
def log_context(context_name):
    """Контекстный менеджер для логирования."""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting: {context_name}")
    
    try:
        yield
        logger.info(f"Completed: {context_name}")
    except Exception as e:
        logger.error(f"Failed: {context_name} - {e}")
        raise

# Использование
def upload_process():
    with log_context("Video Upload"):
        # Процесс загрузки
        pass
```

### Профилирование

#### cProfile
```python
import cProfile
import pstats

def profile_function():
    """Профилирование функции."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Выполнение функции
    upload_video("/path/to/video.mp4")
    
    profiler.disable()
    
    # Сохранение результатов
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Топ 10 функций
```

#### memory_profiler
```python
from memory_profiler import profile

@profile
def memory_intensive_function():
    """Функция с профилированием памяти."""
    large_list = []
    
    for i in range(1000000):
        large_list.append(i)
    
    return sum(large_list)
```

## ⚡ Оптимизация

### Производительность

#### Кэширование
```python
from django.core.cache import cache
from functools import lru_cache

# Кэширование в Django
def get_account_status(account_id):
    cache_key = f"account_status_{account_id}"
    
    # Попытка получить из кэша
    status = cache.get(cache_key)
    if status is not None:
        return status
    
    # Получение из БД
    account = InstagramAccount.objects.get(id=account_id)
    status = account.status
    
    # Сохранение в кэш на 5 минут
    cache.set(cache_key, status, 300)
    
    return status

# Кэширование функций
@lru_cache(maxsize=128)
def expensive_calculation(data):
    """Дорогостоящие вычисления с кэшированием."""
    # Сложные вычисления
    return result
```

#### Асинхронная обработка
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_multiple_accounts(accounts):
    """Асинхронная обработка множественных аккаунтов."""
    tasks = []
    
    for account in accounts:
        task = asyncio.create_task(process_account(account))
        tasks.append(task)
    
    # Ожидание завершения всех задач
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results

async def process_account(account):
    """Обработка одного аккаунта."""
    # Асинхронная обработка
    await asyncio.sleep(1)  # Имитация работы
    return f"Processed: {account.username}"
```

#### Оптимизация запросов к БД
```python
# ✅ Правильно - использование select_related
accounts = InstagramAccount.objects.select_related('proxy').all()

# ✅ Правильно - использование prefetch_related
tasks = BulkUploadTask.objects.prefetch_related('accounts', 'videos').all()

# ❌ Неправильно - N+1 проблема
for account in InstagramAccount.objects.all():
    print(account.proxy.host)  # Дополнительный запрос для каждого аккаунта
```

### Оптимизация памяти

#### Генераторы
```python
# ✅ Правильно - использование генераторов
def process_large_file(file_path):
    """Обработка большого файла с использованием генератора."""
    with open(file_path, 'r') as file:
        for line in file:
            yield process_line(line)

# Использование
for processed_line in process_large_file('/large/file.txt'):
    # Обработка каждой строки
    pass

# ❌ Неправильно - загрузка всего файла в память
def process_large_file_wrong(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()  # Загрузка всего файла
        return [process_line(line) for line in lines]
```

#### Контекстные менеджеры
```python
class ResourceManager:
    """Менеджер ресурсов с автоматической очисткой."""
    
    def __init__(self):
        self.resources = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Автоматическая очистка ресурсов
        for resource in self.resources:
            resource.cleanup()
    
    def add_resource(self, resource):
        self.resources.append(resource)

# Использование
with ResourceManager() as manager:
    # Работа с ресурсами
    manager.add_resource(browser)
    manager.add_resource(proxy)
    # Автоматическая очистка при выходе
```

### Мониторинг производительности

#### Метрики
```python
import time
import psutil
import logging

class PerformanceMonitor:
    """Монитор производительности."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def monitor_function(self, func):
        """Декоратор для мониторинга функций."""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            try:
                result = func(*args, **kwargs)
                
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss
                
                execution_time = end_time - start_time
                memory_used = end_memory - start_memory
                
                self.logger.info(
                    f"Function {func.__name__}: "
                    f"Time: {execution_time:.2f}s, "
                    f"Memory: {memory_used / 1024 / 1024:.2f}MB"
                )
                
                return result
                
            except Exception as e:
                self.logger.error(f"Function {func.__name__} failed: {e}")
                raise
        
        return wrapper

# Использование
monitor = PerformanceMonitor()

@monitor.monitor_function
def upload_video(video_path):
    # Загрузка видео
    pass
```

---

**Версия документации**: 2.0  
**Последнее обновление**: 2024  
**Автор**: Instagram Mass Uploader Team 