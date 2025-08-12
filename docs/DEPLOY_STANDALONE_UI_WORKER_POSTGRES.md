# Развёртывание Standalone Web UI + Worker (с Postgres)

Этот документ описывает, как развернуть изолированный веб‑модуль (UI) и воркер (Windows), подключить их по API (pull‑режим), и перейти на Postgres.

## 0) Предпосылки
- Веб/UI: Ubuntu 22.04+ (или любая Linux), Python 3.12+, Postgres 14+, Nginx (опц.), Gunicorn.
- Воркер: Windows Server 2019/2022 (или Windows 10/11), Python 3.12+, Playwright + Chromium, Dolphin Anty API.
- Домен/сертификаты: настроить HTTPS для UI; при необходимости — для воркера (или ограничить воркера частной сетью).

## 1) Подготовка Postgres
На сервере БД:
```sql
CREATE ROLE iguploader WITH LOGIN PASSWORD 'STRONG_PASSWORD';
CREATE DATABASE iguploader OWNER iguploader;
\c iguploader
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- опц.
```
Файрволл: открыть порт 5432 для UI и (если нужно) для других клиентов.

## 2) Развёртывание Standalone Web UI
Работаем в репозитории в каталогe проекта.

### 2.1. Установка зависимостей
```bash
cd /path/to/repo
python3 -m venv venv
source venv/bin/activate
pip install -r modules/web_ui_service/requirements.txt
```

### 2.2. Настроить ENV
Создайте файл `.env` в корне репозитория или экспортируйте переменные окружения:
```bash
export SECRET_KEY='REPLACE_ME'
export DEBUG='False'
export ALLOWED_HOSTS='ui.domain,localhost'
export DATABASE_URL='postgresql://iguploader:STRONG_PASSWORD@DB_HOST:5432/iguploader'
export WORKER_BASE_URL='http://WORKER_HOST:8088'
export WORKER_API_TOKEN='REPLACE_ME' # общий токен для запросов воркера к UI API
# Опционально: пул воркеров и параметры диспетчера
export WORKER_POOL='http://w1:8088,http://w2:8088'  # если указано, UI будет рассылать старты в несколько воркеров
export DISPATCH_BATCH_SIZE='5'                       # зарезервировано; UI передаёт batch_index/batch_count
export DISPATCH_CONCURRENCY='2'                      # параллельные HTTP-запросы к воркерам при старте
```

### 2.3. Миграции БД
```bash
# Активируйте venv, как выше
python modules/web_ui_service/manage.py migrate --settings=remote_ui.settings
# Создать суперпользователя (опц.)
python modules/web_ui_service/manage.py createsuperuser --settings=remote_ui.settings
```

Если вы переносите данные со старого SQLite:
```bash
# В старой среде (где текущий UI):
python manage.py dumpdata --natural-foreign --natural-primary --indent 2 > dump.json
# На новой среде (Standalone UI):
python modules/web_ui_service/manage.py loaddata dump.json --settings=remote_ui.settings
```

### 2.4. Запуск UI (для теста)
```bash
# dev-режим
python modules/web_ui_service/manage.py runserver --settings=remote_ui.settings 0.0.0.0:8000
```
Проверьте: UI открывается и формы/шаблоны идентичны текущему.

### 2.5. Prod‑запуск через Gunicorn (опц.)
```bash
pip install gunicorn
export DJANGO_SETTINGS_MODULE=remote_ui.settings
gunicorn -w 3 -b 0.0.0.0:8000 remote_ui.wsgi:application
```
За Nginx настройте reverse proxy и статику (стандартная схема Gunicorn+Nginx).

## 3) Развёртывание Windows Worker
На отдельном Windows сервере:

### 3.1. Установка зависимостей
```bat
cd \path\to\repo
py -3.12 -m venv venv
venv\Scripts\pip install -r modules\bulk_worker_service\requirements.txt
venv\Scripts\python -m playwright install
```

### 3.2. ENV воркера
Создайте `modules\bulk_worker_service\.env` (или задайте переменные окружения):
```
UI_API_BASE=https://ui.domain            # URL Standalone UI (тот, что вы подняли)
UI_API_TOKEN=REPLACE_ME                  # == WORKER_API_TOKEN из UI
DOLPHIN_API_TOKEN=REPLACE_ME
DOLPHIN_API_HOST=http://127.0.0.1:3001   # или http://host.docker.internal:3001
CONCURRENCY_LIMIT=2
BATCH_SIZE=2
HEADLESS=1
VISIBLE_BROWSER=0
REQUEST_TIMEOUT_SECS=60
VERIFY_SSL=1
MEDIA_TEMP_DIR=_tmp_media
```

### 3.3. Запуск воркера (dev)
```bat
modules\bulk_worker_service\start_server.bat
```
Проверьте здоровье:
```bash
curl http://WORKER_HOST:8088/api/v1/health
```
Ожидается: `{ "ok": true }`.

### 3.4. Запуск как сервис (опц., Windows)
Через NSSM:
```bat
choco install nssm -y
nssm install iguploader-worker "C:\path\to\repo\venv\Scripts\uvicorn.exe" ^
  bulk_worker_service.app:app --host 0.0.0.0 --port 8088 --workers 1
nssm set iguploader-worker AppDirectory C:\path\to\repo
nssm start iguploader-worker
```

## 4) Подключение UI ↔ Worker (pull‑режим)
- Токен безопасности: `WORKER_API_TOKEN` должен быть одинаковым на обоих концах (UI — для проверки подписи входящих запросов, Worker — как `UI_API_TOKEN`).
- UI вызывает Start‑эндпоинты воркера:
  - Bulk Upload: `POST http://WORKER_HOST:8088/api/v1/bulk-tasks/start` с телом `{"mode":"pull","task_id":<id>,"options":{"concurrency":2,"headless":true}}`.
  - Остальные задачи: аналогичные эндпоинты `/bulk-login/start`, `/warmup/start`, ... (воркер уже слушает; оркестрация на месте).
- Worker запрашивает у UI агрегаты/медиа и пишет статусы/логи назад:
  - UI pull‑API реализованы в `modules/web_ui_service/dashboard/api_views.py` (защищены токеном).

### 4.1) Масштабирование на несколько воркеров (роутинг стартов)
- Включите переменную `WORKER_POOL` на UI (список адресов воркеров через запятую). Если задана — UI рассылает стартовые запросы на все воркеры по round‑robin.
- UI передаёт в запросы на воркер параметры `batch_index` и `batch_count` (в `options` для Bulk Upload, либо как query для других задач).
  - Это позволит в будущем делить аккаунты/подзадачи между воркерами. Сейчас — интерфейс уже готов, при необходимости расширьте воркер, чтобы обрабатывать только свой поднабор.
- `DISPATCH_CONCURRENCY` управляет степенью параллельности исходящих HTTP‑запросов к воркерам при старте.

## 5) Проверка работоспособности
1) UI доступен по HTTP(S), формы и страницы идентичны текущему дашборду (используются шаблоны `uploader/templates`).
2) Создайте Bulk Upload задачу (аккаунты/видео/титулы/локация/упоминания).
3) Нажмите «Старт» в UI — будет вызван воркер, он заберёт агрегат, скачает медиа и начнёт загрузки.
4) Статусы/логи обновляются в реальном времени (через UI pull‑API, воркер пишет обратно).

## 6) Миграция на Postgres (кратко)
- В Standalone UI уже включён парсинг `DATABASE_URL`. Достаточно выставить переменную окружения и выполнить миграции.
- Резервная копия со старого UI на SQLite:
```bash
python manage.py dumpdata --natural-foreign --natural-primary --indent 2 > dump.json
```
- Загрузка в новый UI (Postgres):
```bash
python modules/web_ui_service/manage.py loaddata dump.json --settings=remote_ui.settings
```
- Медиа: скопируйте директорию `media/` на сервер UI.

## 7) Безопасность
- UI должен работать по HTTPS; ограничьте доступы к UI API (IP‑allowlist для воркеров).
- Используйте сложный `WORKER_API_TOKEN` и не логируйте секреты.
- Для медиа рассмотрите S3 с presigned URL (воркер умеет скачивать по абсолютному URL из агрегата).

## 8) Масштабирование и отладка
- Горизонтально масштабируйте воркеры (Windows) — настройте `CONCURRENCY_LIMIT`/`BATCH_SIZE` с учётом ресурсов.
- Для распределения стартов на несколько воркеров используйте `WORKER_POOL` в UI; UI добавляет `batch_index/batch_count` к вызовам воркера.
- Bulk Upload уже реализован полноценно в воркере: `modules/bulk_worker_service/bulk_worker_service/ig_runner.py`.
- Остальные задачи имеют API/оркестратор (каркасы) и pull‑агрегаты на UI — готовы для быстрого включения раннеров.
- Логи:
  - UI — стандартные Django логи, записи в моделях задач/аккаунтов.
  - Worker — stdout Uvicorn + структурные логи действий загрузки.

## 9) Быстрые команды (шпаргалка)
- UI (dev):
```bash
python modules/web_ui_service/manage.py runserver --settings=remote_ui.settings 0.0.0.0:8000
```
- Worker (Windows):
```bat
modules\bulk_worker_service\start_server.bat
```
- Проверка воркера:
```bash
curl http://WORKER_HOST:8088/api/v1/health
```
- Запуск Bulk Upload без UI (curl):
```bash
curl -X POST "http://WORKER_HOST:8088/api/v1/bulk-tasks/start" \
  -H "Content-Type: application/json" \
  -d '{"mode":"pull","task_id":123,"options":{"concurrency":2,"headless":true}}'
```

---

Вопросы/проблемы:
- Если воркер не может получить агрегат — проверьте UI pull‑API и `WORKER_API_TOKEN`.
- Если Playwright не стартует — проверьте `DOLPHIN_API_TOKEN`, `DOLPHIN_API_HOST`, наличие браузеров (`playwright install`).
- Если UI не видит логи — смотрите POST `/api/bulk-tasks/{id}/status` и записи в моделях. 