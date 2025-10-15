# TikTok Server API v2 - Simplified Architecture

## 📋 Спецификация API для удаленных TikTok серверов

**Архитектура:** Очередь задач на каждом сервере (Вариант B)

**Принцип работы:**
1. Django интерфейс отправляет задачу на сервер
2. Сервер добавляет задачу в свою внутреннюю очередь
3. Когда сервер свободен - выполняет задачу из очереди
4. Django периодически опрашивает статус задачи

---

## 🔧 Базовая конфигурация

### Base URL
```
http://{server_host}:{server_port}
```

### Authentication (опционально)
```
Authorization: Bearer {api_key}
```

### Response Format
```json
{
  "success": true,
  "message": "...",
  "data": {...}
}
```

---

## 📌 1. ПРОВЕРКА ЗДОРОВЬЯ И СТАТИСТИКА

### 1.1 Health Check
**Endpoint:** `GET /health`  
**Описание:** Проверка доступности сервера

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

### 1.2 Server Statistics
**Endpoint:** `GET /stats`  
**Описание:** Получить статистику сервера

**Response (200 OK):**
```json
{
  "accounts_count": 25,
  "videos_count": 150,
  "dolphin_profiles_count": 20,
  "tasks_count": {
    "queued": 2,
    "running": 1,
    "completed": 45,
    "failed": 3
  },
  "system": {
    "cpu_usage": 45.2,
    "memory_usage": 62.8,
    "disk_usage": 35.5
  }
}
```

---

### 1.3 Get Logs
**Endpoint:** `GET /logs?lines=100`  
**Описание:** Получить последние логи сервера

**Query Parameters:**
- `lines` (int, optional): Количество строк (default: 100, max: 1000)

**Response (200 OK):**
```json
{
  "logs": [
    "2025-01-15 10:30:00 - INFO - Server started",
    "2025-01-15 10:30:01 - INFO - Task completed: task_123"
  ],
  "lines_returned": 2
}
```

---

## 🚀 2. УПРАВЛЕНИЕ ЗАДАЧАМИ (ГЛАВНОЕ!)

### 2.1 Create Upload Task
**Endpoint:** `POST /tasks/upload`  
**Описание:** Создать задачу загрузки видео (ВСЁ В ОДНОМ ЗАПРОСЕ!)

**Request Body:**
```json
{
  "client": "ClientName",
  "tag": "memes",
  "accounts_count": 10,
  "cycles": 3,
  "cycle_timeout_minutes": 30,
  "delay_between_uploads": {
    "min_seconds": 30,
    "max_seconds": 60
  },
  "videos": [
    {
      "filename": "video1.mp4",
      "file_base64": "BASE64_ENCODED_VIDEO_DATA",
      "caption": "Крутое видео #viral #fyp",
      "hashtags": ["viral", "fyp", "memes"],
      "music_name": "Trending Song 2024",
      "location": "Moscow",
      "mentions": ["@user1", "@user2"]
    },
    {
      "filename": "video2.mp4",
      "file_base64": "BASE64_ENCODED_VIDEO_DATA",
      "caption": "Смешной момент дня 😂"
    }
  ],
  "default_settings": {
    "allow_comments": true,
    "allow_duet": true,
    "allow_stitch": true,
    "privacy": "PUBLIC"
  }
}
```

**Параметры:**
- `client` (str): Имя клиента (для фильтрации аккаунтов)
- `tag` (str, optional): Тематика (fim, memes и т.д.)
- `accounts_count` (int): Сколько аккаунтов использовать
- `cycles` (int): Количество циклов загрузки
- `cycle_timeout_minutes` (int): Задержка между циклами
- `delay_between_uploads` (dict): Задержка между загрузками
- `videos` (list): Массив видео с метаданными
- `default_settings` (dict, optional): Настройки по умолчанию

**Response (200 OK):**
```json
{
  "success": true,
  "task_id": "task_abc123def456",
  "status": "QUEUED",
  "message": "Task created and added to queue",
  "estimated_start_time": "2025-01-15T10:35:00Z",
  "queue_position": 2
}
```

**Что делает сервер после получения этого запроса:**
1. Сохраняет видео на диск
2. Получает нужные аккаунты из PostgreSQL (по client и tag)
3. Проверяет, есть ли уже профили Dolphin для этих аккаунтов
4. Если нет - создает новые профили, назначает прокси
5. Добавляет задачу в очередь
6. Возвращает task_id
7. Когда освободится - запускает загрузку

---

### 2.2 Create Warmup Task
**Endpoint:** `POST /tasks/warmup`  
**Описание:** Создать задачу прогрева аккаунтов

**Request Body:**
```json
{
  "client": "ClientName",
  "tag": "memes",
  "accounts_count": 15,
  "accounts": [
    {
      "username": "user1",
      "password": "pass1",
      "email_username": "u1@mail.com",
      "email_password": "mailpass",
      "cookies": [{"name": "sessionid", "value": "...", "domain": ".tiktok.com"}],
      "fingerprint": {"ua": "...", "platform": "Win32"},
      "status": "ACTIVE",
      "last_time_used": "2025-01-10T12:34:56Z",
      "client": "ClientName",
      "tag": "memes",
      "proxy": {
        "type": "http",
        "host": "1.2.3.4",
        "port": 1234,
        "user": "puser",
        "pass": "ppass",
        "country": "US",
        "city": "NY"
      },
      "local_storage": {"someKey": "someValue"},
      "warmup_state": "WARMED",
      "dolphin_profile_id": "abcd1234",
      "locale": "en_US"
    }
  ],
  "settings": {
    "feed_scroll_min": 5,
    "feed_scroll_max": 15,
    "like_min": 3,
    "like_max": 10,
    "watch_video_min": 5,
    "watch_video_max": 20,
    "follow_min": 0,
    "follow_max": 5,
    "comment_min": 0,
    "comment_max": 3,
    "delay_min_sec": 15,
    "delay_max_sec": 45
  },
  "use_cookie_robot": false
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "task_id": "task_warmup_789xyz",
  "status": "QUEUED",
  "message": "Warmup task created",
  "queue_position": 1
}
```

---

### 2.3 Get Task Status
**Endpoint:** `GET /tasks/{task_id}`  
**Описание:** Получить статус и прогресс задачи

**Response (200 OK):**
```json
{
  "task_id": "task_abc123def456",
  "type": "upload",
  "status": "RUNNING",
  "progress": 45,
  "created_at": "2025-01-15T10:30:00Z",
  "started_at": "2025-01-15T10:35:00Z",
  "estimated_completion": "2025-01-15T12:30:00Z",
  "current_step": "Uploading video 15 of 30",
  "accounts_used": 10,
  "videos_uploaded": 14,
  "videos_failed": 1,
  "errors": [
    {
      "account": "user123",
      "video": "video5.mp4",
      "error": "Captcha required"
    }
  ],
  "logs": [
    "10:35:00 - Started task",
    "10:36:12 - Uploaded video 1/30 with account user1",
    "10:37:45 - Uploaded video 2/30 with account user1"
  ]
}
```

**Статусы задачи:**
- `QUEUED` - В очереди, ожидает выполнения
- `RUNNING` - Выполняется
- `COMPLETED` - Завершена успешно
- `FAILED` - Завершена с ошибкой
- `CANCELLED` - Отменена пользователем

---

### 2.4 Stop Task
**Endpoint:** `POST /tasks/{task_id}/stop`  
**Описание:** Остановить выполняющуюся задачу

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Task stopped",
  "task_id": "task_abc123def456",
  "status": "CANCELLED"
}
```

---

### 2.5 Delete Task
**Endpoint:** `DELETE /tasks/{task_id}`  
**Описание:** Удалить задачу (только если завершена или отменена)

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Task deleted"
}
```

**Error (400):**
```json
{
  "success": false,
  "error": "Cannot delete running task"
}
```

---

### 2.6 List All Tasks
**Endpoint:** `GET /tasks`  
**Описание:** Список всех задач на сервере

**Query Parameters:**
- `status` (str, optional): Фильтр по статусу
- `type` (str, optional): Фильтр по типу (upload, warmup)
- `limit` (int, optional): Лимит (default: 50)
- `offset` (int, optional): Смещение (default: 0)

**Response (200 OK):**
```json
{
  "tasks": [
    {
      "task_id": "task_abc123",
      "type": "upload",
      "status": "COMPLETED",
      "created_at": "2025-01-15T09:00:00Z",
      "progress": 100
    },
    {
      "task_id": "task_def456",
      "type": "warmup",
      "status": "RUNNING",
      "created_at": "2025-01-15T10:00:00Z",
      "progress": 67
    }
  ],
  "total": 2,
  "limit": 50,
  "offset": 0
}
```

---

## 👤 3. УПРАВЛЕНИЕ АККАУНТАМИ

### 3.1 Get Accounts List
**Endpoint:** `GET /accounts`  
**Описание:** Получить список аккаунтов на сервере

**Query Parameters:**
- `limit` (int, optional): Лимит (default: 100)
- `offset` (int, optional): Смещение
- `client` (str, optional): Фильтр по клиенту
- `tag` (str, optional): Фильтр по тематике
- `has_dolphin_profile` (bool, optional): Только с профилями Dolphin

**Response (200 OK):**
```json
{
  "accounts": [
    {
      "username": "user1",
      "client": "ClientName",
      "tag": "memes",
      "status": "active",
      "has_dolphin_profile": true,
      "dolphin_profile_id": "profile_123",
      "last_used": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 25,
  "limit": 100,
  "offset": 0
}
```

---

### 3.2 Check Dolphin Profiles
**Endpoint:** `POST /accounts/check-profiles`  
**Описание:** Проверить наличие профилей Dolphin для аккаунтов

**Request Body:**
```json
{
  "usernames": ["user1", "user2", "user3"]
}
```

**Response (200 OK):**
```json
{
  "profiles_found": {
    "user1": "profile_123",
    "user2": "profile_456"
  },
  "profiles_missing": ["user3"],
  "total_found": 2,
  "total_missing": 1
}
```

**Использование:** Django может вызвать этот эндпоинт перед созданием задачи, чтобы выбрать сервер, где уже есть профили для нужных аккаунтов.

---

### 3.3 Sync Account Data
**Endpoint:** `POST /accounts/{username}/sync`  
**Описание:** Синхронизировать данные аккаунта (cookies, fingerprint) обратно в PostgreSQL

**Response (200 OK):**
```json
{
  "success": true,
  "username": "user1",
  "cookies_updated": true,
  "fingerprint_updated": true,
  "last_sync": "2025-01-15T10:35:00Z"
}
```

---

## 🐬 4. DOLPHIN ПРОФИЛИ

### 4.1 Get Dolphin Profiles
**Endpoint:** `GET /dolphin/profiles`  
**Описание:** Список всех профилей Dolphin на сервере

**Response (200 OK):**
```json
{
  "profiles": [
    {
      "id": "profile_123",
      "name": "user1",
      "username": "user1",
      "status": "active",
      "last_used": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 20
}
```

---

## 🔄 5. ВНУТРЕННЯЯ ОЧЕРЕДЬ (ОПЦИОНАЛЬНО)

Эти эндпоинты полезны для мониторинга очереди на сервере:

### 5.1 Get Queue Status
**Endpoint:** `GET /queue/status`  
**Описание:** Состояние очереди задач

**Response (200 OK):**
```json
{
  "queue_length": 3,
  "running_tasks": 1,
  "max_concurrent_tasks": 3,
  "available_slots": 2,
  "queued_tasks": [
    {
      "task_id": "task_123",
      "type": "upload",
      "position": 1,
      "estimated_start": "2025-01-15T11:00:00Z"
    }
  ]
}
```

---

## 📝 6. ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### Workflow: Загрузка видео

#### Шаг 1: Django создает задачу
```python
# Django view
videos_data = []
for video_file in uploaded_files:
    videos_data.append({
        "filename": video_file.name,
        "file_base64": base64.b64encode(video_file.read()).decode(),
        "caption": request.POST.get(f'caption_{video_file.name}')
    })

response = server_client.create_upload_task(
    client="Client1",
    tag="memes",
    accounts_count=10,
    cycles=3,
    videos=videos_data
)

# Сохраняем task_id в БД Django
ServerTask.objects.create(
    server=selected_server,
    remote_task_id=response['task_id'],
    task_type='UPLOAD',
    status='QUEUED'
)
```

#### Шаг 2: Периодическое обновление статуса (Celery Beat или cron)
```python
# Django management command или Celery task
def update_task_statuses():
    running_tasks = ServerTask.objects.filter(
        status__in=['QUEUED', 'RUNNING']
    )
    
    for task in running_tasks:
        client = ServerAPIClient(task.server)
        success, data = client.get_task_status(task.remote_task_id)
        
        if success:
            task.status = data['status']
            task.progress = data['progress']
            task.log = '\n'.join(data.get('logs', []))
            task.save()
```

---

## ⚠️ ВАЖНЫЕ ЗАМЕЧАНИЯ

### 1. Получение аккаунтов через Django API ✅

Сервер получает аккаунты через Django API (безопасный вариант).

#### Django API Endpoints (для серверов):

**Зарезервировать аккаунты:**
```
POST https://your-django-server.com/tiktok/api/accounts/reserve/
```

**Request:**
```json
{
  "server_id": 1,
  "client": "Client1",
  "tag": "memes",
  "count": 10,
  "status_filter": "ACTIVE"
}
```

**Response:**
```json
{
  "success": true,
  "accounts": [
    {
      "id": 123,
      "username": "user1",
      "password": "pass123",
      "email": "user1@mail.com",
      "email_password": "emailpass",
      "phone_number": "+1234567890",
      "dolphin_profile_id": "profile_123",
      "locale": "en_US",
      "status": "ACTIVE",
      "tag": "memes",
      "proxy": {
        "host": "185.123.45.67",
        "port": 8080,
        "username": "proxyuser",
        "password": "proxypass",
        "type": "http",
        "ip_change_url": "https://..."
      },
      "server_assignment": {
        "dolphin_profile_id_on_server": "profile_123",
        "last_used_at": "2025-01-15T10:00:00Z"
      }
    }
  ],
  "count": 10,
  "server_id": 1,
  "server_name": "TikTok Server 1"
}
```

**Освободить аккаунты после завершения:**
```
POST https://your-django-server.com/tiktok/api/accounts/release/
```

**Request:**
```json
{
  "server_id": 1,
  "usernames": ["user1", "user2", "user3"]
}
```

**Синхронизировать данные аккаунта:**
```
POST https://your-django-server.com/tiktok/api/accounts/sync/
```

**Request:**
```json
{
  "username": "user1",
  "server_id": 1,
  "dolphin_profile_id": "profile_123",
  "cookies": {...},
  "fingerprint": {...},
  "status": "ACTIVE"
}
```

**Пример использования на сервере:**
```python
# На FastAPI сервере
import requests

DJANGO_API_URL = "https://your-django-server.com/tiktok"

def get_accounts_from_django(server_id: int, client: str, tag: str, count: int):
    response = requests.post(
        f"{DJANGO_API_URL}/api/accounts/reserve/",
        json={
            "server_id": server_id,
            "client": client,
            "tag": tag,
            "count": count
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return data['accounts']
    else:
        raise Exception(f"Failed to get accounts: {response.text}")

# При создании задачи на сервере:
accounts = get_accounts_from_django(
    server_id=1,
    client="Client1",
    tag="memes",
    count=10
)
```

**Преимущества этого подхода:**
- ✅ Централизованная логика резервирования
- ✅ Автоматическое назначение на сервер
- ✅ Приоритет аккаунтам с существующими профилями Dolphin
- ✅ Безопасность (нет прямого доступа к БД)
- ✅ Логирование всех операций

### 2. Синхронизация данных обратно

После завершения задачи сервер должен синхронизировать:
- Обновленные cookies
- Fingerprint данные
- Статус аккаунта (если был заблокирован)
- Статистику (сколько видео залито)

### 3. Обработка ошибок

Если сервер недоступен, Django должен:
- Отметить сервер как OFFLINE
- Переназначить задачу на другой сервер (если возможно)
- Уведомить администратора

---

## 🔗 ОТЛИЧИЯ ОТ СТАРОЙ ВЕРСИИ

| Старая версия | Новая версия v2 |
|---------------|-----------------|
| Много отдельных запросов | Всё в одном запросе |
| `/upload/prepare_accounts` + `/upload/upload_videos` + `/upload/prepare_config` + `/upload/start_upload` | `/tasks/upload` (всё сразу) |
| Сложная подготовка | Сервер сам всё делает |
| Нет очереди | Встроенная очередь |
| Нет мониторинга | `/tasks/{id}` для отслеживания |

---

## 📞 ДОПОЛНИТЕЛЬНЫЕ ВОПРОСЫ?

**Версия документации**: 2.0  
**Дата**: 2025-01-15  
**Архитектура**: Вариант B (очередь на серверах)
