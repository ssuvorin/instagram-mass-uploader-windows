# Bulk Worker Service (Standalone)

Независимый модуль для удалённого запуска задач дашборда на Windows-серверах через HTTP API (без изменения веба). Работает в pull‑режиме: получает агрегаты по API, скачивает медиа, выполняет действия (Playwright + Dolphin), пишет логи/статусы обратно.

## Поддерживаемые задачи (API воркера)
- `POST /api/v1/bulk-tasks/start` — массовая загрузка видео (реализовано полностью)
- `POST /api/v1/bulk-login/start` — массовый логин (каркас; ожидает агрегат из веба)
- `POST /api/v1/warmup/start` — прогрев (каркас)
- `POST /api/v1/avatar/start` — смена аватаров (каркас)
- `POST /api/v1/bio/start` — смена ссылки в био (каркас)
- `POST /api/v1/follow/start` — follow (каркас)
- `POST /api/v1/proxy-diagnostics/start` — диагностика прокси (каркас)
- `POST /api/v1/media-uniq/start` — уникализация видео (каркас)
- `GET /api/v1/jobs`, `GET /api/v1/jobs/{job_id}/status` — статусы задач

Примечание: «каркас» означает, что воркер уже имеет эндпоинт и оркестрацию, ожидает агрегат от веба по pull‑API `/api/{kind}/{task_id}/aggregate`, и после интеграции легко подключается раннер (по аналогии с Bulk Upload).

## Какие агрегаты должен отдавать веб (позже)
- Bulk Upload: `GET /api/bulk-tasks/{id}/aggregate` (указано ранее)
- Bulk Login: `GET /api/bulk_login/{id}/aggregate` (accounts)
- Warmup: `GET /api/warmup/{id}/aggregate` (accounts + actions)
- Avatar: `GET /api/avatar/{id}/aggregate` (accounts + images)
- Bio: `GET /api/bio/{id}/aggregate` (accounts + link_url)
- Follow: `GET /api/follow/{id}/aggregate` (accounts + targets + options)
- Proxy Diagnostics: `GET /api/proxy_diag/{id}/aggregate` (accounts)
- Media Uniq: `GET /api/media_uniq/{id}/aggregate` (videos)

И соответствующие POST-эндпоинты для статусов/логов/счетчиков по каждому виду задач — по аналогии с Bulk Upload (см. `docs/BULK_WORKER_INTEGRATION.md`).

## Реализация Bulk Upload (внутри модуля)
- `ig_runner.py` — Playwright + Dolphin: вход, логин через `Auth`, загрузка через `Upload` с title/location/mentions, человеческие паузы. В конце сессии воркер пытается получить cookies профиля через Dolphin Remote API и пишет в лог их количество (персист сохраняется на стороне веба).
- `instagrapi_runner.py` — загрузка через `instagrapi` с использованием постоянного устройства/сессии (см. `instgrapi_func`), уникализация видео, логи, счётчики.
- `orchestrator.py` — батчирование, параллельность, статусы/логи, выбор раннера.
- `ui_client.py` — загрузка агрегата, медиа, публикация логов/статусов, поддержка абсолютного URL медиа.

### Выбор механизма загрузки
- Можно выбрать метод загрузки:
  - Playwright: браузерный флоу (по умолчанию)
  - Instagrapi: приватный API («как телефон»)
- Способы управления:
  - Глобально через ENV: `UPLOAD_METHOD=playwright|instagrapi`
  - На запрос: `StartRequest.options.upload_method` (перекрывает ENV)

## Заготовки для остальных задач
- Cookie Robot: `tasks/cookie_robot.py` — использует Dolphin API, готов к вызову из API (добавим эндпоинт при интеграции веба).
- Bulk Login/Warmup/Avatar/Bio/Follow/Proxy/MediaUniq — эндпоинты и оркестратор готовы, ожидание агрегатов; подключение раннеров делается по шаблону `ig_runner.py`/`instagrapi_runner.py`.

## Установка и запуск
1) Python 3.12 + Playwright:
   ```bat
   py -3.12 -m venv venv
   venv\Scripts\pip install -r modules\bulk_worker_service\requirements.txt
   venv\Scripts\python -m playwright install
   ```
2) ENV (см. `.env.example`): `UI_API_BASE`, `UI_API_TOKEN`, `DOLPHIN_API_TOKEN`, `DOLPHIN_API_HOST`, `CONCURRENCY_LIMIT`, `HEADLESS`, `VISIBLE_BROWSER`, `UPLOAD_METHOD`.
3) Запуск:
   ```bat
   modules\bulk_worker_service\start_server.bat
   ```

## Масштабирование
- Несколько воркеров; ограничение параллельности; батчи; блокировки на стороне веба.

## Замечания по качеству
- Устойчивые локаторы, человеческие задержки, ретраи, структурные логи — всё как в Bulk Upload. 