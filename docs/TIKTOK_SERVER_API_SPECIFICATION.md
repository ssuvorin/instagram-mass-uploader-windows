# TikTok Server API Specification

## 📋 Документация API эндпоинтов для FastAPI ботов на серверах

Эта документация описывает все необходимые API эндпоинты, которые должны быть реализованы на FastAPI ботах, работающих на удаленных серверах. Интерфейс Django будет взаимодействовать с серверами через эти эндпоинты.

---

## 🔧 Базовая конфигурация

### Base URL
```
http://{server_host}:{server_port}
```

По умолчанию: `http://localhost:8000`

### Authentication
Опциональная аутентификация через Bearer token:
```
Authorization: Bearer {api_key}
```

### Response Format
Все ответы возвращаются в JSON формате:
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {...}
}
```

---

## 📌 1. ПРОВЕРКА ЗДОРОВЬЯ И ИНФОРМАЦИЯ

### 1.1 Health Check
**Endpoint:** `GET /health`  
**Описание:** Проверка доступности сервера  
**Аутентификация:** Не требуется

**Request:**
```bash
curl http://localhost:8000/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "database": "healthy",
    "dolphin": "healthy"
  },
  "version": "1.0.0"
}
```

---

### 1.2 Server Information
**Endpoint:** `GET /ip-info`  
**Описание:** Получить информацию о сервере  
**Аутентификация:** Опциональна

**Request:**
```bash
curl http://localhost:8000/ip-info
```

**Response (200 OK):**
```json
{
  "client_ip": "127.0.0.1",
  "server_name": "TikTok Server 1",
  "is_allowed": true,
  "timestamp": 1705318200.0,
  "server_info": {
    "cpu_usage": 45.2,
    "memory_usage": 62.8,
    "disk_usage": 35.5
  }
}
```

---

### 1.3 Get Logs
**Endpoint:** `GET /logs`  
**Описание:** Получить логи сервера  
**Аутентификация:** Требуется

**Query Parameters:**
- `lines` (int, optional): Количество строк логов (default: 100, max: 1000)

**Request:**
```bash
curl http://localhost:8000/logs?lines=50
```

**Response (200 OK):**
```json
{
  "logs": [
    "2024-01-15 10:30:00 - INFO - Server started",
    "2024-01-15 10:30:01 - INFO - Database initialized",
    "2024-01-15 10:30:02 - INFO - Dolphin connected"
  ],
  "log_file": "log.txt",
  "lines_requested": 50,
  "lines_returned": 3,
  "server_name": "TikTok Server 1",
  "timestamp": 1705318200.0
}
```

---

## 📊 2. СТАТИСТИКА И МЕТРИКИ

### 2.1 Get Accounts Count
**Endpoint:** `GET /get_accounts_from_db`  
**Описание:** Получить количество аккаунтов в локальной БД сервера  
**Аутентификация:** Требуется

**Request:**
```bash
curl http://localhost:8000/get_accounts_from_db
```

**Response (200 OK):**
```json
{
  "count": 25
}
```

---

### 2.2 Get Videos Count
**Endpoint:** `GET /get_videos`  
**Описание:** Получить количество видео на сервере  
**Аутентификация:** Требуется

**Request:**
```bash
curl http://localhost:8000/get_videos
```

**Response (200 OK):**
```json
{
  "count": 150
}
```

---

### 2.3 Get Dolphin Profiles Count
**Endpoint:** `GET /get_dolphin_profiles`  
**Описание:** Получить количество Dolphin профилей на сервере  
**Аутентификация:** Требуется

**Request:**
```bash
curl http://localhost:8000/get_dolphin_profiles
```

**Response (200 OK):**
```json
{
  "count": 20
}
```

---

## 📤 3. ЗАГРУЗКА ФАЙЛОВ НА СЕРВЕР

### 3.1 Upload Videos
**Endpoint:** `POST /upload/upload_videos/`  
**Описание:** Загрузить видео файлы на сервер  
**Аутентификация:** Требуется  
**Content-Type:** `multipart/form-data`

**Request:**
```bash
curl -X POST http://localhost:8000/upload/upload_videos/ \
  -F "files=@video1.mp4" \
  -F "files=@video2.mp4" \
  -F "files=@video3.mp4"
```

**Response (200 OK):**
```json
{
  "message": "Videos uploaded successfully",
  "uploaded_files": 3,
  "total_size_mb": 125.5
}
```

---

### 3.2 Upload Titles
**Endpoint:** `POST /upload/upload_titles`  
**Описание:** Загрузить файл с заголовками/описаниями  
**Аутентификация:** Требуется  
**Content-Type:** `multipart/form-data`

**Request:**
```bash
curl -X POST http://localhost:8000/upload/upload_titles \
  -F "file=@titles.txt"
```

**Пример содержимого `titles.txt`:**
```
Крутое видео #viral #fyp
Смешной момент дня 😂 #funny
Мотивация на утро! #motivation
```

**Response (200 OK):**
```json
{
  "message": "Titles file uploaded successfully",
  "filename": "titles.txt",
  "titles_count": 3
}
```

---

### 3.3 Upload Accounts (for Boosting)
**Endpoint:** `POST /booster/upload_accounts`  
**Описание:** Загрузить файл с аккаунтами для прогрева  
**Аутентификация:** Требуется  
**Content-Type:** `multipart/form-data`

**Request:**
```bash
curl -X POST http://localhost:8000/booster/upload_accounts \
  -F "file=@accounts.txt"
```

**Форматы аккаунтов в `accounts.txt`:**
```
# Формат 1: username:password:cookies
user1:pass123:{"sessionid": "abc123"}

# Формат 2: username:password:email_username:email_password:cookies
user2:pass456:user2@mail.com:emailpass:{"sessionid": "def456"}

# Формат 3: username:password:email_username:email_password
user3:pass789:user3@mail.com:emailpass

# Формат 4: username:password
user4:pass000
```

**Response (200 OK):**
```json
{
  "message": "Accounts file uploaded successfully",
  "accounts_parsed": 4
}
```

---

### 3.4 Upload Proxies
**Endpoint:** `POST /booster/upload_proxies`  
**Описание:** Загрузить файл с прокси  
**Аутентификация:** Требуется  
**Content-Type:** `multipart/form-data`

**Request:**
```bash
curl -X POST http://localhost:8000/booster/upload_proxies \
  -F "file=@proxies.txt"
```

**Форматы прокси в `proxies.txt`:**
```
# Формат 1: host:port:username:password
185.234.59.17:15626:user1:pass1

# Формат 2: host:port@username:password
185.234.59.18:15627@user2:pass2

# Формат 3: host:port:username:password[change_ip_url]
185.234.59.19:15628:user3:pass3[https://changeip.example.com/?key=abc123]

# Формат 4: host:port (без аутентификации)
185.234.59.20:15629
```

**Response (200 OK):**
```json
{
  "message": "Proxy file uploaded successfully. Validation will occur during account preparation.",
  "total_proxies": 4,
  "file_path": "/path/to/proxies.txt"
}
```

---

## 🚀 4. УПРАВЛЕНИЕ АККАУНТАМИ

### 4.1 Prepare Accounts (для загрузки)
**Endpoint:** `POST /upload/prepare_accounts`  
**Описание:** Получить аккаунты из общей БД и подготовить их на сервере  
**Аутентификация:** Требуется  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "count": 20,
  "client": "ClientName",
  "order": "newest"
}
```

**Parameters:**
- `count` (int): Количество аккаунтов для получения
- `client` (str): Имя клиента
- `order` (str): Порядок сортировки ("newest" или "oldest")

**Request:**
```bash
curl -X POST http://localhost:8000/upload/prepare_accounts \
  -H "Content-Type: application/json" \
  -d '{
    "count": 10,
    "client": "Client1",
    "order": "newest"
  }'
```

**Response (200 OK):**
```json
{
  "message": "Accounts prepared successfully",
  "accounts_imported": 10,
  "dolphin_profiles_created": 10,
  "proxies_assigned": 10
}
```

---

### 4.2 Prepare Booster Accounts
**Endpoint:** `POST /booster/prepare_accounts`  
**Описание:** Подготовить аккаунты для прогрева (из загруженных файлов)  
**Аутентификация:** Требуется  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "use_cookie_robot": false,
  "client": "ClientName"
}
```

**Parameters:**
- `use_cookie_robot` (bool): Использовать ли cookie robot перед прогревом
- `client` (str): Имя клиента

**Request:**
```bash
curl -X POST http://localhost:8000/booster/prepare_accounts \
  -H "Content-Type: application/json" \
  -d '{
    "use_cookie_robot": true,
    "client": "Client1"
  }'
```

**Response (200 OK):**
```json
{
  "message": "Accounts prepared successfully",
  "inserted_accounts": 15,
  "processed_profiles": 15
}
```

---

## 📹 5. ЗАДАЧИ ЗАГРУЗКИ ВИДЕО

### 5.1 Prepare Upload Config
**Endpoint:** `POST /upload/prepare_config`  
**Описание:** Подготовить конфигурацию для загрузки видео  
**Аутентификация:** Требуется  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "upload_cycles": 5,
  "cycle_timeout_minutes": 30,
  "music_name": "Trending Song 2024",
  "location": "Moscow",
  "mentions": ["@user1", "@user2"]
}
```

**Parameters:**
- `upload_cycles` (int): Количество циклов загрузки
- `cycle_timeout_minutes` (int): Таймаут между циклами в минутах
- `music_name` (str, optional): Название музыки для видео
- `location` (str, optional): Геолокация для видео
- `mentions` (list[str], optional): Упоминания пользователей

**Request:**
```bash
curl -X POST http://localhost:8000/upload/prepare_config \
  -H "Content-Type: application/json" \
  -d '{
    "upload_cycles": 3,
    "cycle_timeout_minutes": 30,
    "music_name": "Popular Song",
    "location": "New York"
  }'
```

**Response (200 OK):**
```json
{
  "message": "Config prepared successfully",
  "total_videos_needed": 30,
  "total_accounts": 10,
  "cycles": 3
}
```

**Error Response (502):**
```json
{
  "detail": "Need more 10 videos"
}
```

---

### 5.2 Start Upload
**Endpoint:** `POST /upload/start_upload`  
**Описание:** Запустить процесс загрузки видео  
**Аутентификация:** Требуется  
**Content-Type:** `application/json`

**⚠️ ВАЖНО:** Этот эндпоинт выполняется **асинхронно** и может работать часами!

**Request:**
```bash
curl -X POST http://localhost:8000/upload/start_upload \
  -H "Content-Type: application/json"
```

**Response (200 OK):**
```json
{
  "message": "Upload completed successfully",
  "total_time_minutes": 125.5,
  "videos_uploaded": 30,
  "success_rate": 0.93,
  "failed_videos": 2
}
```

**Error Response (502):**
```json
{
  "detail": "Need config to start upload"
}
```

---

## 🔥 6. ПРОГРЕВ АККАУНТОВ

### 6.1 Start Booster
**Endpoint:** `POST /booster/start_booster`  
**Описание:** Запустить прогрев аккаунтов  
**Аутентификация:** Требуется

**⚠️ ВАЖНО:** Этот эндпоинт выполняется **асинхронно** и может работать часами!

**Request:**
```bash
curl -X POST http://localhost:8000/booster/start_booster
```

**Response (200 OK):**
```json
{
  "message": "Booster finished",
  "accounts_warmed": 15,
  "accounts_failed": 2,
  "total_time_minutes": 180.5,
  "accounts_synced_to_db": 13
}
```

**Error Response (502):**
```json
{
  "detail": "No accounts for booster provided"
}
```

---

## 🔄 7. РАСШИРЕННЫЕ ЭНДПОИНТЫ (РЕКОМЕНДУЕТСЯ)

Эти эндпоинты не обязательны, но сильно улучшают функциональность управления.

### 7.1 Get Account List
**Endpoint:** `GET /accounts/list`  
**Описание:** Получить список аккаунтов на сервере  
**Аутентификация:** Требуется

**Query Parameters:**
- `limit` (int, optional): Ограничение количества (default: 100)
- `offset` (int, optional): Смещение для пагинации (default: 0)
- `status` (str, optional): Фильтр по статусу

**Request:**
```bash
curl http://localhost:8000/accounts/list?limit=10&status=active
```

**Response (200 OK):**
```json
{
  "accounts": [
    {
      "username": "user1",
      "status": "active",
      "last_used": "2024-01-15T10:30:00Z",
      "dolphin_profile_id": "profile_123",
      "proxy": "185.234.59.17:15626"
    }
  ],
  "total": 25,
  "limit": 10,
  "offset": 0
}
```

---

### 7.2 Get Account Details
**Endpoint:** `GET /accounts/{username}`  
**Описание:** Получить детальную информацию об аккаунте  
**Аутентификация:** Требуется

**Request:**
```bash
curl http://localhost:8000/accounts/user1
```

**Response (200 OK):**
```json
{
  "username": "user1",
  "email": "user1@mail.com",
  "status": "active",
  "last_used": "2024-01-15T10:30:00Z",
  "last_warmed": "2024-01-14T15:20:00Z",
  "dolphin_profile_id": "profile_123",
  "proxy": {
    "host": "185.234.59.17",
    "port": 15626,
    "type": "http"
  },
  "cookies_updated": "2024-01-15T10:25:00Z",
  "videos_uploaded": 15
}
```

---

### 7.3 Get Task Status
**Endpoint:** `GET /tasks/{task_id}`  
**Описание:** Получить статус выполняющейся задачи  
**Аутентификация:** Требуется

**Request:**
```bash
curl http://localhost:8000/tasks/task_abc123
```

**Response (200 OK):**
```json
{
  "task_id": "task_abc123",
  "type": "upload",
  "status": "running",
  "progress": 45,
  "started_at": "2024-01-15T10:00:00Z",
  "estimated_completion": "2024-01-15T12:30:00Z",
  "current_step": "Uploading video 15 of 30",
  "errors": []
}
```

---

### 7.4 Cancel Task
**Endpoint:** `POST /tasks/{task_id}/cancel`  
**Описание:** Отменить выполняющуюся задачу  
**Аутентификация:** Требуется

**Request:**
```bash
curl -X POST http://localhost:8000/tasks/task_abc123/cancel
```

**Response (200 OK):**
```json
{
  "message": "Task cancelled successfully",
  "task_id": "task_abc123",
  "status": "cancelled"
}
```

---

### 7.5 Get Dolphin Profiles
**Endpoint:** `GET /dolphin/profiles`  
**Описание:** Получить список Dolphin профилей на сервере  
**Аутентификация:** Требуется

**Request:**
```bash
curl http://localhost:8000/dolphin/profiles
```

**Response (200 OK):**
```json
{
  "profiles": [
    {
      "id": "profile_123",
      "name": "user1",
      "status": "active",
      "proxy_assigned": true,
      "last_used": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 20
}
```

---

### 7.6 Sync Account to Main DB
**Endpoint:** `POST /accounts/{username}/sync`  
**Описание:** Синхронизировать данные аккаунта обратно в главную БД  
**Аутентификация:** Требуется

**Request:**
```bash
curl -X POST http://localhost:8000/accounts/user1/sync
```

**Response (200 OK):**
```json
{
  "message": "Account synced successfully",
  "username": "user1",
  "cookies_updated": true,
  "fingerprint_updated": true,
  "last_sync": "2024-01-15T10:35:00Z"
}
```

---

## 🛡️ 8. БЕЗОПАСНОСТЬ И WHITELIST

### IP Whitelist Middleware
Сервер должен проверять IP адреса входящих запросов:

```python
ALLOWED_IPS = [
    "127.0.0.1",
    "localhost",
    "46.249.27.75",      # Django сервер
    "185.117.119.218",   # Резервный сервер
]

@app.middleware("http")
async def ip_whitelist_middleware(request: Request, call_next):
    client_ip = request.client.host
    
    # Проверка X-Forwarded-For (если за прокси)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    if client_ip not in ALLOWED_IPS:
        return Response(
            content=f"Access denied. Your IP ({client_ip}) is not authorized.",
            status_code=403
        )
    
    response = await call_next(request)
    return response
```

---

## 📝 9. ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### Полный workflow загрузки видео:

```bash
# 1. Загрузить видео на сервер
curl -X POST http://localhost:8000/upload/upload_videos/ \
  -F "files=@video1.mp4" \
  -F "files=@video2.mp4"

# 2. Загрузить заголовки
curl -X POST http://localhost:8000/upload/upload_titles \
  -F "file=@titles.txt"

# 3. Подготовить аккаунты
curl -X POST http://localhost:8000/upload/prepare_accounts \
  -H "Content-Type: application/json" \
  -d '{"count": 10, "client": "Client1", "order": "newest"}'

# 4. Подготовить конфигурацию
curl -X POST http://localhost:8000/upload/prepare_config \
  -H "Content-Type: application/json" \
  -d '{"upload_cycles": 2, "cycle_timeout_minutes": 30}'

# 5. Запустить загрузку
curl -X POST http://localhost:8000/upload/start_upload
```

### Полный workflow прогрева аккаунтов:

```bash
# 1. Загрузить аккаунты
curl -X POST http://localhost:8000/booster/upload_accounts \
  -F "file=@accounts.txt"

# 2. Загрузить прокси
curl -X POST http://localhost:8000/booster/upload_proxies \
  -F "file=@proxies.txt"

# 3. Подготовить аккаунты для прогрева
curl -X POST http://localhost:8000/booster/prepare_accounts \
  -H "Content-Type: application/json" \
  -d '{"use_cookie_robot": true, "client": "Client1"}'

# 4. Запустить прогрев
curl -X POST http://localhost:8000/booster/start_booster
```

---

## ⚠️ ВАЖНЫЕ ЗАМЕЧАНИЯ

1. **Асинхронность**: Эндпоинты `/upload/start_upload` и `/booster/start_booster` выполняются долго. Рекомендуется:
   - Возвращать немедленный ответ с `task_id`
   - Реализовать эндпоинт для проверки статуса задачи
   - Использовать WebSocket для real-time обновлений (опционально)

2. **Обработка ошибок**: Все эндпоинты должны возвращать понятные сообщения об ошибках:
   ```json
   {
     "detail": "Подробное описание ошибки",
     "error_code": "ACCOUNTS_NOT_FOUND",
     "timestamp": "2024-01-15T10:30:00Z"
   }
   ```

3. **Логирование**: Все операции должны логироваться для возможности отладки

4. **Валидация**: Входные данные должны валидироваться с помощью Pydantic моделей

5. **Timeout**: Клиент Django устанавливает большие timeout для долгих операций

6. **Синхронизация**: После завершения задач сервер должен автоматически синхронизировать данные (cookies, fingerprints) обратно в главную БД через API

---

## 🔗 ССЫЛКИ

- **FastAPI документация**: https://fastapi.tiangolo.com/
- **Pydantic**: https://docs.pydantic.dev/
- **Текущая реализация**: `TiktokUploadCaptcha/src/api.py`

---

## 📞 ПОДДЕРЖКА

При возникновении вопросов или необходимости уточнений по API, обращайтесь к команде разработки.

**Версия документации**: 1.0  
**Последнее обновление**: 2024-01-15
