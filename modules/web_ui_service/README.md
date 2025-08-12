# Remote Web UI (Standalone, API-driven)

Отдельный веб‑модуль (Django), 1-в-1 по UI и функционалу с текущим дашбордом, но:
- Не выполняет локально никакие задачи (никаких RQ/воркеров).
- Запускает все действия через удалённый воркер (`modules/bulk_worker_service`) по HTTP API (pull‑режим).
- Отдаёт необходимые pull‑API для воркера: агрегаты задач и медиастримы, а также принимает статусы/логи/счётчики от воркера.
- Развёртывается отдельно; основной проект не меняется.

## Что внутри
- Проект Django `remote_ui/` + приложение `dashboard/`.
- В `INSTALLED_APPS` включён существующий `uploader` (из корня репозитория) — полностью сохраняет UI/шаблоны/формы/CRUD.
- В `dashboard/urls.py` переопределены только маршруты старта задач (bulk upload/login/warmup/avatar/bio/follow и т.п.) — они вызывают воркер API.
- В `dashboard/api_views.py` реализованы pull‑эндпоинты для воркера (агрегаты/медиа/статусы/логи/счётчики). Защита: Bearer `WORKER_API_TOKEN`.

## Установка
1) Зависимости:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r modules/web_ui_service/requirements.txt
```
2) ENV (пример):
```
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=ui.domain,localhost
# База (Postgres или SQLite для теста)
DATABASE_URL=postgresql://iguploader:PASS@DB_HOST:5432/iguploader
# Внешний воркер
WORKER_BASE_URL=http://worker-host:8088
# Токен для приёма запросов от воркера (pull-режим)
WORKER_API_TOKEN=REPLACE_ME
```
3) Запуск:
```bash
modules/web_ui_service/start_server.sh
```
или
```bat
modules\web_ui_service\start_server.bat
```

## Как это работает
- Пользователь в UI создаёт задачи/аккаунты/медиа (через `uploader`), UI полностью идентичен текущему.
- При нажатии «Старт» UI вызывает `WORKER_BASE_URL` (pull‑режим) → воркер забирает агрегат из этого веб‑модуля (`/api/.../aggregate`), скачивает медиа (`/api/media/.../download`) и шлёт статусы/логи обратно на этот веб‑модуль (`/api/.../status`).
- В результате UI показывает актуальные статусы/логи задач, как сейчас.

## Примечания
- Веб-модуль не изменяет исходный проект; он подключает `uploader` как зависимость (модуль из этого репозитория) и переопределяет только «start»-роуты.
- Шаблоны берутся из `uploader/templates` — UI идентичен.
- Все медиа/файлы передаются по API. 