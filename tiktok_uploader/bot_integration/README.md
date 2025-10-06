# Bot Integration Module

Интеграция бота TikTokUploadCaptcha в Django веб-интерфейс.

## Структура

```
bot_integration/
├── __init__.py              # Инициализация логгера
├── logger.py                # Система логирования
├── telegram_notifier.py     # Telegram уведомления
├── db.py                    # SQLite база данных (для совместимости)
├── services.py              # Сервисный слой для Django
├── sites.json               # Список сайтов для Cookie Robot
├── dolphin/                 # Модули Dolphin Anty
│   ├── __init__.py
│   ├── dolphin.py          # Управление профилями
│   └── profile.py          # Класс профиля
└── tiktok/                  # Модули TikTok
    ├── __init__.py
    ├── auth.py             # Аутентификация
    ├── upload.py           # Загрузка видео
    ├── booster.py          # Прогрев аккаунтов
    ├── video.py            # Класс Video
    ├── getCode.py          # Получение email кодов
    ├── captcha.py          # Решение CAPTCHA
    ├── browser.py          # Управление браузером
    ├── locators.py         # Селекторы элементов
    └── utils.py            # Утилиты
```

## Основные компоненты

### Services Layer (`services.py`)

Адаптер между Django моделями и логикой бота. Основные функции:

#### 1. Dolphin Profile Management

```python
from tiktok_uploader.bot_integration.services import create_dolphin_profile_for_account

# Создание профиля для аккаунта
result = create_dolphin_profile_for_account(account, locale='en_US')
if result['success']:
    profile_id = result['profile_id']
```

#### 2. Bulk Video Upload

```python
from tiktok_uploader.bot_integration.services import run_bulk_upload_task

# Запуск задачи загрузки
result = run_bulk_upload_task(task_id)
# Функция блокирующая, рекомендуется запускать в отдельном потоке
```

#### 3. Account Warmup

```python
from tiktok_uploader.bot_integration.services import run_warmup_task

# Запуск задачи прогрева
result = run_warmup_task(task_id)
```

#### 4. Cookie Management

```python
from tiktok_uploader.bot_integration.services import (
    run_cookie_robot_for_account,
    export_cookies_from_profile
)

# Запуск Cookie Robot
result = run_cookie_robot_for_account(account)

# Экспорт cookies
cookies = export_cookies_from_profile(account)
```

## Использование в Views

### Создание Dolphin профиля

```python
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from tiktok_uploader.bot_integration.services import create_dolphin_profile_for_account
from tiktok_uploader.models import TikTokAccount

def create_profile_view(request, account_id):
    account = get_object_or_404(TikTokAccount, id=account_id)
    
    result = create_dolphin_profile_for_account(account)
    
    if result['success']:
        return JsonResponse({
            'success': True,
            'profile_id': result['profile_id']
        })
    else:
        return JsonResponse({
            'success': False,
            'error': result['error']
        }, status=500)
```

### Запуск задачи загрузки

```python
import threading
from tiktok_uploader.bot_integration.services import run_bulk_upload_task

def start_upload_view(request, task_id):
    # Запускаем в отдельном потоке, чтобы не блокировать HTTP запрос
    def run_in_background():
        try:
            run_bulk_upload_task(task_id)
        except Exception as e:
            print(f"Error: {e}")
    
    thread = threading.Thread(target=run_in_background, daemon=True)
    thread.start()
    
    return JsonResponse({'success': True, 'message': 'Upload started'})
```

## Конфигурация

### Переменные окружения

Необходимо установить следующие переменные окружения:

```env
# Dolphin Anty API Token
TOKEN=your_dolphin_anty_token

# TikTok Captcha Solver API Key
TIKTOK_SOLVER_API_KEY=your_captcha_solver_key

# Telegram уведомления (опционально)
TELEGRAM_TOKEN=your_telegram_bot_token
ADMINS=telegram_user_id1,telegram_user_id2
SERVER_NAME=Production TikTok Bot

# Debug режим
DEBUG=False
```

### Установка Playwright

После установки зависимостей необходимо установить браузеры для Playwright:

```bash
playwright install chromium
```

## Логирование

Логи бота сохраняются в файл `logs/tiktok_bot.log`. Структура логов:

```
[2025-10-04 21:00:00]:[INFO] Dolphin profile created for username123: 123456
[2025-10-04 21:01:00]:[ERROR] Failed to authenticate user456: Invalid credentials
```

Для включения debug режима установите `DEBUG=True` в переменных окружения.

## Важные замечания

### 1. Сохранение логики бота

Вся логика бота сохранена без изменений. Все модули из `TikTokUploadCaptcha/src/` скопированы в `bot_integration/` с минимальными изменениями:

- Обновлены импорты для работы с Django
- Добавлен адаптер `services.py` для интеграции с Django моделями
- Логгер адаптирован для работы в Django окружении

### 2. Блокирующие операции

Функции `run_bulk_upload_task()` и `run_warmup_task()` являются блокирующими и могут выполняться долго (часы). Рекомендуется запускать их:

- В отдельном потоке (threading)
- Через Celery (если настроен)
- Через отдельный процесс (multiprocessing)

### 3. Dolphin Anty

Для работы бота необходим запущенный Dolphin Anty браузер на `localhost:3001`. 

Профили создаются с следующими параметрами:
- Реалистичные fingerprints (WebGL, Canvas, User-Agent)
- Timezone и geolocation по прокси
- Локализация из настроек аккаунта
- Прокси из Django модели

### 4. Прокси

Каждый аккаунт должен иметь настроенный прокси (`TikTokProxy` модель). Прокси используется для:
- Создания Dolphin профиля
- Всех операций с TikTok
- Определения геолокации и timezone

## Примеры использования

### Полный цикл работы с аккаунтом

```python
from django.contrib.auth.models import User
from tiktok_uploader.models import TikTokAccount, TikTokProxy
from tiktok_uploader.bot_integration.services import (
    create_dolphin_profile_for_account,
    run_cookie_robot_for_account
)

# 1. Создать аккаунт
account = TikTokAccount.objects.create(
    username='test_account',
    password='secure_password',
    email='test@example.com',
    email_password='email_password',
    locale='en_US',
    proxy=some_proxy  # TikTokProxy instance
)

# 2. Создать Dolphin профиль
result = create_dolphin_profile_for_account(account)
if result['success']:
    print(f"Profile created: {result['profile_id']}")

# 3. Запустить Cookie Robot (опционально)
cookie_result = run_cookie_robot_for_account(account)
if cookie_result['success']:
    print("Cookie robot completed")

# 4. Теперь аккаунт готов для использования в задачах загрузки или прогрева
```

### Создание и запуск задачи загрузки

```python
import threading
from tiktok_uploader.models import (
    BulkUploadTask, BulkUploadAccount, BulkVideo
)
from tiktok_uploader.bot_integration.services import run_bulk_upload_task

# 1. Создать задачу
task = BulkUploadTask.objects.create(
    name='Test Upload',
    status='PENDING',
    delay_min_sec=30,
    delay_max_sec=60,
    default_caption='Test video',
    default_hashtags='#test, #video'
)

# 2. Добавить аккаунты
for account in TikTokAccount.objects.filter(status='ACTIVE')[:5]:
    BulkUploadAccount.objects.create(
        bulk_task=task,
        account=account,
        status='PENDING'
    )

# 3. Загрузить видео (через Django admin или API)
# ... загрузка файлов ...

# 4. Запустить задачу
def run_upload():
    run_bulk_upload_task(task.id)

thread = threading.Thread(target=run_upload, daemon=True)
thread.start()
```

## Troubleshooting

### Ошибка "No Dolphin profile"

Убедитесь, что:
1. Dolphin Anty запущен на `localhost:3001`
2. Токен `TOKEN` правильно установлен в переменных окружения
3. Профиль был создан через `create_dolphin_profile_for_account()`

### Ошибка аутентификации

Проверьте:
1. Правильность учетных данных аккаунта
2. Email и email_password для получения кодов
3. Прокси настроены и работают
4. Аккаунт не заблокирован TikTok

### CAPTCHA не решается

1. Проверьте `TIKTOK_SOLVER_API_KEY`
2. Убедитесь, что баланс API не исчерпан
3. Проверьте логи на наличие ошибок от solver

## Лицензия

Интеграция использует код из проекта TikTokUploadCaptcha с сохранением всей оригинальной логики.


