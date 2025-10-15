# 🚀 Deployment Checklist - Remote Architecture

## ✅ Что было сделано

### 1. Backend (Django)
- ✅ Созданы 4 новые модели: `TikTokServer`, `ServerAccount`, `ServerTask`, `ServerHealthLog`
- ✅ Добавлено поле `tag` в `TikTokAccount`
- ✅ Создан API client для взаимодействия с FastAPI серверами (`ServerAPIClient`, `ServerManager`)
- ✅ Реализован Django API для резервирования аккаунтов (4 endpoint'а)
- ✅ Создано 7 новых views для удаленной загрузки
- ✅ Создано 10+ views для управления серверами
- ✅ Добавлено 20+ новых URL patterns

### 2. Frontend (Templates)
- ✅ Создано 5 новых шаблонов для удаленной загрузки
- ✅ Добавлен переключатель серверов в navbar (с AJAX)
- ✅ Обновлено меню Bulk Upload (новый/старый интерфейс)
- ✅ Шаблон для мониторинга задач на сервере с автообновлением

### 3. Документация
- ✅ `TIKTOK_SERVER_API_V2.md` — полная спецификация API для FastAPI серверов
- ✅ `REMOTE_BULK_UPLOAD_GUIDE.md` — руководство пользователя
- ✅ `REMOTE_ARCHITECTURE_IMPLEMENTATION_SUMMARY.md` — технический обзор

---

## 📋 Checklist перед deployment

### Шаг 1: Миграции базы данных

```bash
# Создать миграции
python manage.py makemigrations tiktok_uploader

# Проверить миграции
python manage.py showmigrations tiktok_uploader

# Применить миграции
python manage.py migrate tiktok_uploader

# Проверить, что все модели созданы
python manage.py shell
>>> from tiktok_uploader.models import TikTokServer, ServerTask, ServerAccount
>>> TikTokServer.objects.all()
```

**Ожидаемый результат**: 4 новые таблицы в БД:
- `tiktok_uploader_tiktokserver`
- `tiktok_uploader_serveraccount`
- `tiktok_uploader_servertask`
- `tiktok_uploader_serverhealthlog`

---

### Шаг 2: Добавить серверы

**Через Django Admin:**
```bash
python manage.py createsuperuser  # если нет админа
python manage.py runserver
```

Перейти на `http://localhost:8000/admin/tiktok_uploader/tiktokserver/`

**Или через интерфейс:**
1. Перейти на `/tiktok/servers/`
2. Нажать "Add Server"
3. Заполнить:
   - Name: `TikTok Server 1`
   - Host: `192.168.1.100`
   - Port: `8000`
   - API Key: `your-secret-key-here`
   - Max Concurrent Tasks: `5`
   - Priority: `1` (чем ниже, тем выше приоритет)
   - Is Active: `True`

**Или через Python shell:**
```python
from tiktok_uploader.models import TikTokServer

server = TikTokServer.objects.create(
    name='TikTok Server 1',
    host='192.168.1.100',
    port=8000,
    api_key='your-secret-key-here',
    max_concurrent_tasks=5,
    priority=1,
    is_active=True
)
```

---

### Шаг 3: Настроить FastAPI серверы

На каждом FastAPI сервере нужно:

1. **Обновить API до версии v2** (согласно `TIKTOK_SERVER_API_V2.md`)
2. **Добавить новые эндпоинты:**
   - `POST /tasks/upload` — создание задачи загрузки
   - `POST /tasks/warmup` — создание задачи прогрева
   - `GET /tasks/{task_id}` — статус задачи
   - `POST /tasks/{task_id}/stop` — остановка задачи
   - `DELETE /tasks/{task_id}` — удаление задачи
   - `GET /tasks` — список всех задач
   - `POST /accounts/check-profiles` — проверка Dolphin профилей

3. **Добавить очередь задач** (например, на Celery или asyncio queue)

4. **Настроить обращения к Django API:**
```python
DJANGO_API_URL = "https://your-django-server.com/tiktok"

# При создании задачи
accounts = requests.post(
    f"{DJANGO_API_URL}/api/accounts/reserve/",
    json={
        "server_id": SERVER_ID,
        "client": "Client1",
        "tag": "memes",
        "count": 10
    }
).json()['accounts']
```

5. **Настроить API Key проверку:**
```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API Key")
```

6. **Добавить IP whitelisting** (в зависимости от вашей инфраструктуры)

---

### Шаг 4: Проверка подключения

**Через интерфейс:**
1. Перейти на `/tiktok/servers/`
2. Нажать "Ping All" — все серверы должны быть `online`

**Или через Python:**
```python
from tiktok_uploader.services.server_api_client import ServerManager

# Пинг всех серверов
results = ServerManager.ping_all_servers()
for server_id, result in results.items():
    print(f"Server {server_id}: {result}")

# Выбрать лучший сервер
best_server = ServerManager.select_best_server()
print(f"Best server: {best_server.name}")
```

**Ожидаемый результат**: Все серверы отвечают `{"status": "online", ...}`

---

### Шаг 5: Первый тестовый запуск

1. **Добавить тестовый тег к аккаунтам:**
```python
from tiktok_uploader.models import TikTokAccount

# Пример: пометить аккаунты
TikTokAccount.objects.filter(id__in=[1,2,3,4,5]).update(tag='test')
```

2. **Создать тестовую задачу:**
   - Перейти: **Bulk Upload → New Remote Task**
   - Название: `Test Upload #1`
   - Клиент: (выбрать любого)
   - Tag: `test`
   - Количество аккаунтов: `2`
   - Сервер: **Автоматический выбор**
   - Циклы: `1`
   - Задержки: `30-60 сек`

3. **Добавить 1 тестовое видео**

4. **Добавить описание** (или пропустить)

5. **Проверить** все параметры

6. **Отправить на сервер**

7. **Мониторинг:**
   - Перейти на страницу задачи
   - Проверить логи
   - Дождаться завершения

**Ожидаемый результат**:
- Задача переходит в статус `QUEUED`
- Затем `RUNNING`
- Прогресс обновляется
- Логи отображаются
- Задача завершается `COMPLETED`

---

## 🔧 Troubleshooting

### Проблема: Миграции не применяются

**Решение:**
```bash
# Проверить список миграций
python manage.py showmigrations

# Если есть unapplied миграции
python manage.py migrate --fake-initial

# Если ошибка с зависимостями
python manage.py migrate --run-syncdb
```

### Проблема: Сервер в статусе OFFLINE

**Проверить:**
1. FastAPI сервер запущен?
2. Доступен ли хост:порт?
3. Правильный ли API ключ?
4. Есть ли IP Django сервера в whitelist?

**Решение:**
```bash
# На FastAPI сервере
curl http://localhost:8000/
curl http://localhost:8000/info

# С Django сервера
curl http://192.168.1.100:8000/
curl -H "X-API-Key: your-key" http://192.168.1.100:8000/info
```

### Проблема: Задача не отправляется

**Проверить:**
1. Есть ли доступные серверы?
2. Есть ли свободные аккаунты с нужным тегом?
3. Есть ли видео?

**Логи Django:**
```bash
tail -f logs/django.log
```

**Логи FastAPI:**
```bash
# На FastAPI сервере
tail -f logs/tiktok_bot.log
```

### Проблема: Аккаунты не резервируются

**Проверить:**
```python
from tiktok_uploader.models import TikTokAccount

# Есть ли аккаунты с нужным тегом?
TikTokAccount.objects.filter(tag='memes', status='ACTIVE').count()

# Не заняты ли они?
from tiktok_uploader.models import ServerAccount
ServerAccount.objects.filter(account__tag='memes').values('account__username', 'server__name')
```

---

## 📊 Мониторинг после deployment

### Health Checks

**Автоматически:**
Можно настроить cron job для периодической проверки:
```bash
# Каждые 5 минут
*/5 * * * * curl http://localhost:8000/tiktok/servers/ping-all/
```

**Вручную:**
```python
from tiktok_uploader.services.server_api_client import ServerManager

# Создать health log для всех серверов
results = ServerManager.ping_all_servers()
for server_id, result in results.items():
    if result.get('success'):
        ServerManager.create_health_log(
            server_id,
            'online',
            result.get('response_time', 0)
        )
    else:
        ServerManager.create_health_log(
            server_id,
            'offline',
            0,
            error=result.get('error')
        )
```

### Логи

**Django:**
```bash
tail -f logs/instagram_uploader.log  # основной лог
tail -f django.log  # если есть
```

**FastAPI серверы:**
```bash
# На каждом сервере
tail -f logs/tiktok_bot.log
```

### Статистика

**Через Django Admin:**
- Перейти: `/admin/tiktok_uploader/tiktokserver/`
- Посмотреть `total_tasks`, `successful_tasks`, `failed_tasks`

**Через Python:**
```python
from tiktok_uploader.models import TikTokServer, ServerTask

# Статистика по серверам
for server in TikTokServer.objects.all():
    print(f"{server.name}: {server.total_tasks} total, {server.successful_tasks} success")

# Статистика по задачам
from django.db.models import Count
ServerTask.objects.values('status').annotate(count=Count('id'))
```

---

## ✅ Финальная проверка

Перед тем, как считать deployment завершенным:

- [ ] Миграции применены
- [ ] Минимум 1 сервер добавлен и в статусе `online`
- [ ] Ping All возвращает успешные ответы
- [ ] Аккаунты имеют тег (хотя бы несколько)
- [ ] Тестовая задача успешно создана
- [ ] Тестовая задача успешно отправлена на сервер
- [ ] Мониторинг задачи работает (логи, прогресс)
- [ ] Переключатель серверов в navbar работает
- [ ] FastAPI серверы реализуют API v2
- [ ] FastAPI серверы могут обращаться к Django API
- [ ] Аккаунты резервируются и освобождаются корректно

---

## 🎉 Успех!

Если все чекбоксы отмечены — система полностью готова к продакшену!

**Что дальше:**
- Добавить больше серверов для масштабирования
- Настроить мониторинг (Prometheus/Grafana)
- Настроить алерты при падении серверов
- Удалить старый локальный функционал (опционально)
- Реализовать умный выбор сервера с проверкой Dolphin профилей (опционально)

---

**Документация:**
- [API Specification](./docs/TIKTOK_SERVER_API_V2.md)
- [User Guide](./docs/REMOTE_BULK_UPLOAD_GUIDE.md)
- [Implementation Summary](./docs/REMOTE_ARCHITECTURE_IMPLEMENTATION_SUMMARY.md)



