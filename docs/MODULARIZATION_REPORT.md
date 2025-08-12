## Модульная архитектура и план развертывания (Ubuntu UI + Windows Workers)

Цель: отделить все «исполняющие» модули (боты Playwright/инструменты обработки медиа/диагностика прокси/тёплый прогрев и т.д.) от веб-дашборда и фронтенда, чтобы:
- Веб (UI + API + БД + очередь задач) работал на Ubuntu.
- Исполняющие модули масштабировались горизонтально на Windows-серверах.
- Учесть ближайшую миграцию с SQLite на Postgres.
- Соблюдать принципы OOP, CLEAN, DRY, KISS, SOLID, а также правила из Always Applied Workspace Rules (человеческое поведение, устойчивые селекторы, чистая модульная архитектура, централизованный логгинг и ретраи).

Содержимое актуального репозитория (важные узлы):
- Django-проект: `instagram_uploader/` (настройки, URLs)
- Приложение: `uploader/` (модели, views, массовая загрузка, автоматизация, utils)
- Автоматизация Playwright + DolphinAnty: `bot/src/instagram_uploader/*`, `uploader/instagram_automation.py`, `uploader/bulk_tasks_playwright.py` и др.
- Async-имплементация: `uploader/async_impl/*`, `uploader/async_bulk_tasks.py`
- Документация: `docs/*` (в т.ч. SEPARATION_GUIDE_PYTHON.md, ephemeral-dolphin-profiles-and-postgres.md)
- Скрипты: `scripts/`, `*.bat` для Windows, вспомогательные скрипты


## Целевая архитектура (компоненты)

1) UI/API сервис (Ubuntu)
- Django (Gunicorn+Nginx) — отрисовка дашборда, REST API, выдача статических/медиа-файлов.
- Postgres — централизованная БД для всех сервисов.
- Redis — брокер очередей RQ для асинхронных задач, лог-стриминг (pub/sub), кэши.
- Django RQ (или RQ) — очередь задач с приоритетными очередями: `high`, `default`, `low`.
- Канал логирования: структурные логи в Postgres и онлайн-трансляция в UI (SSE/WS на Django Channels или поллинг).
- Хранилище медиа: локально + HTTP загрузка/выдача; опционально S3/MinIO для меж-ОС доступа.

2) Windows Workers (N ≥ 1)
- Лёгкие воркеры RQ: `python manage.py rqworker high default`.
- Установленные Playwright, браузеры, Dolphin Anty клиент.
- Доступ к Ubuntu Redis и Postgres по сети.
- Выполняют задачи: массовая загрузка видео, прогрев, куки-робот, смена аватаров, фолловинг, уникализация видео, диагностика прокси и т.п.
- Соблюдение «человеческого поведения»: рандомные задержки, мягкие движения, предварительные hover/scan; устойчивые селекторы с фоллбэками.

3) Shared Core (общая библиотека кода)
- Пакет общего кода: доменные сервисы, репозитории, конфиги, логирование, селекторы, «человеческое поведение», утилиты.
- Используется и UI (для подготовки задач), и воркерами (для выполнения).

4) Интеграции
- Dolphin Anty (`bot/src/instagram_uploader/dolphin_anty.py`, `browser_dolphin.py`).
- RuCaptcha/CapMonster и пр. — `uploader/captcha_solver.py`.
- Email и 2FA — `uploader/email_verification_async.py`.


## Разделение на пакеты (предлагаемая структура директорий)

- apps/
  - ui/ (Django проект + приложение UI)
    - проект `instagram_uploader/` (как есть)
    - приложение `uploader/` (views, формы, шаблоны) — остаётся для UI и API
    - новый модуль `uploader/api/` (DRF эндпоинты для внешних/внутренних вызовов)
  - worker/ (точки входа воркеров; при желании — отдельное приложение, но воркер поднимается тем же manage.py)
- core/
  - domain/ (датаклассы, валидации, value-объекты)
  - repositories/ (инкапсулируют Django ORM-доступ к моделям)
  - services/
    - automation/ (Playwright-пайплайны: логин, навигация, загрузка; «человеческое поведение»)
    - media/ (обрезка, уникализация, проверка кодеков/битрейтов)
    - proxy/ (диагностика, подбор, health-check)
    - cookie_robot/
    - warmup/
    - follow/
    - avatar/
    - bio/
    - captcha/
    - email_2fa/
  - config/ (YAML/JSON конфиги, в т.ч. селекторы)
  - logging/ (структурные логи, формат, web-handler)
  - selectors/ (конфигурация с фоллбэками, text-based проверки)
  - human_behavior/ (параметризация и фазы задержек/движений)
- infra/
  - rq/ (описание очередей, приоритетов)
  - scripts/ (развёртывание/обновление)
  - migrations/ (миграции Django)

На первом этапе можно не физически переносить файлы, а «логически» выделить слои: сервисы и репозитории как отдельные модули внутри `uploader/` + `bot/`, постепенно выносим в `core/`.


## БД и доменная модель (актуальные модели)

- `Proxy`: тип, статус, host/port/cred, метаданные (страна/город), уникальность (host, port, username, password).
- `InstagramAccount`: username/password, email creds, tfa_secret, proxy/current_proxy, dolphin_profile_id, статус, phone_number и пр.
- `InstagramDevice`: per-account persistent device profile.
- `InstagramCookies`: cookies JSON, is_valid.
- `UploadTask`, `VideoFile` — одиночные задачи загрузки (исторически).
- `BulkUploadTask`, `BulkUploadAccount`, `BulkVideo`, `VideoTitle` — массовые загрузки.
- `AvatarChangeTask`, `AvatarChangeTaskAccount`, `AvatarImage` — смена аватаров.
- `FollowCategory`, `FollowTarget`, `FollowTask`, `FollowTaskAccount` — действия follow.
- `WarmupTask`, `WarmupTaskAccount` — прогрев аккаунтов.
- `DolphinCookieRobotTask` — cookie-робот.

Postgres-заметки:
- Все JSONField поддерживаются нативно.
- Добавить индексы по полям статусов и внешним ключам (часто используемые фильтры).
- Добавить поля блокировки аккаунтов для конкурентного доступа (см. ниже).


## Очереди и каналы

- Redis Queues:
  - `high`: критические задачи UI-триггеров и «тонких» операций (логины, куки, изменения био/аватаров).
  - `default`: массовые загрузки, прогрев, follow.
  - `low`: диагностики, итеративные health-checks, плановые чистки.
- Redis Pub/Sub:
  - Канал логов задач для streaming в UI (по task_id).
  - Каналы метрик воркеров.


## Сетевая модель и безопасность

- Postgres: принятие соединений только с подсети Windows Workers. Роль с ограниченными правами.
- Redis: ограниченный доступ только UI и воркерам.
- Воркеры запускаются с `DJANGO_SETTINGS_MODULE` и с `DATABASE_URL`/`REDIS_URL` на Ubuntu хосты.
- Внутренние API защищены токенами (Service Token), IP allowlist.


## Правила взаимодействия (Data Flow)

1) Пользователь в UI создаёт `BulkUploadTask` и прикрепляет аккаунты + видео/заголовки.
2) UI сохраняет сущности в Postgres и публикует задачу в RQ (в очередь `default`/`high`): `bulk_upload.start(task_id)`.
3) Любой Windows Worker перехватывает задачу, берёт `task_id`, открывает соединение к БД, читает данные, исполняет пайплайн Playwright, обновляет статусы и логи по мере выполнения.
4) UI подписан на канал логов по `task_id` (или периодически опрашивает REST), отображает прогресс.
5) Медиа-файлы: воркер скачивает через защищённый эндпоинт UI (`/api/media/{id}/download?token=...`) или из S3.


## Модульные сервисы и ключевые классы

Ниже — проектирование сервисов с ООП-API. Конкретная реализация будет адаптаторами вокруг уже существующих функций (`uploader/bulk_tasks_playwright.py`, `uploader/instagram_automation.py`, `uploader/login_optimized.py`, `uploader/human_behavior.py`, `uploader/captcha_solver.py`, `uploader/crop_handler.py`, `uploader/proxy_diagnostics.py`, `uploader/email_verification_async.py`, `bot/src/instagram_uploader/*`).

### Core: репозитории (SOLID: SRP + DIP)

- `AccountRepository`
  - get_for_bulk(task_id) → список аккаунтов/прокси
  - acquire_account_lock(account_id, worker_id, ttl)
  - release_account_lock(account_id, worker_id)
  - update_status(account_id, status, log_append=None)
  - mark_used(account_id)

- `BulkUploadRepository`
  - get_task(task_id) → Task aggregate (videos, titles, accounts)
  - update_task_status(task_id, status, log_append=None)
  - increment_counters(account_task_id, success_delta, fail_delta)
  - append_account_log(account_task_id, text)

- `MediaRepository`
  - open_video_stream(video_id) → stream/URL
  - get_title_for_video(video_id)

- `ProxyRepository`
  - pick_active_or_account_proxy(account_id)
  - update_health(proxy_id, status, last_checked, notes)

Все репозитории используют Django ORM, но инкапсулируют детали.

### Core: логирование

- `StructuredLogger`
  - log_info(task_id, category, message, extra)
  - log_warn(task_id, category, message, extra)
  - log_error(task_id, category, message, extra)
  - publish_to_stream(task_id, json_event)

Реализация: `structlog` + Redis pub/sub + запись в БД (агрегированный лог).

### Services: Automation (Playwright)

- `BrowserSessionFactory`
  - create(account, proxy, dolphin_profile_id, headless=False) → контекст/страница Playwright
  - правила: подавление лишних логов, таймауты, включение «человеческого поведения»

- `HumanBehaviorService`
  - simulate_delay(phase, min_ms, max_ms)
  - move_mouse_curve(target, duration_ms)
  - pre_scan(area) → hover/scroll/выбор элементов
  - параметры — из `human_behavior_config.json`

- `SelectorResolver`
  - resolve(selector_key) → список XPath/CSS вариантов
  - verify_visible_text(locator, expected_substrings)
  - конфигурация — `selectors.json` (с фоллбэками, data-атрибутами, aria-ролями)

- `LoginService`
  - check_logged_in()
  - login(username, password, tfa_secret, email_creds?) → распознаёт сценарии `SUSPENDED`, `PHONE_VERIFICATION_REQUIRED`, reCAPTCHA
  - используется `captcha_solver`, `email_verification_async`

- `UploadService`
  - navigate_to_upload()
  - upload_single_video(video_stream/path, title, location, mentions)
    - crop_if_needed()
    - click_next_steps(2)
    - set_description_char_by_char(...)
    - set_location_with_suggestion(...)
    - set_mentions_with_suggestion(...)
    - share_and_verify_success()
  - устойчивые ретраи и откат состояния при ошибках

- `WarmupService`
  - perform_warmup(account, actions_config)

- `CookieRobotService`
  - run_on_profile(dolphin_profile_id, urls, headless, imageless)

- `FollowService`
  - follow_targets(category, ranges)

- `AvatarService`
  - change_avatar(image)

- `BioService`
  - change_link(url)

- `ProxyDiagnosticsService`
  - test(proxy) → latency, geo, блокировки; обновляет статус

### Services: Media

- `VideoUniquifier`
  - make_unique(input_stream) → output_stream (опционально на Windows с ffmpeg/opencv)

- `CropHandler` (адаптирует `uploader/crop_handler.py`)
  - detect_and_apply_crop(page/ui) → корректно приводит к нужным соотношениям


## Задачи (Jobs) и RQ-воркеры

Очередь RQ несёт «тонкие» полезные нагрузки — идентификаторы и опции, а не «толстые» объекты.

- Job: `bulk_upload.start(task_id)`
  - Схема payload: `{ "task_id": int, "options": { "max_concurrency": int, "headless": bool } }`
  - Воркфлоу:
    1. Загрузка агрегата задачи через `BulkUploadRepository`.
    2. Пакетная обработка аккаунтов с ограничением параллелизма (см. `uploader/async_impl/runner.py`).
    3. Для каждого аккаунта: lock → proxy → браузер → login → upload видео* → статус/логи.

- Job: `bulk_login.start(task_id)`
- Job: `warmup.start(task_id)`
- Job: `avatar_change.start(task_id)`
- Job: `bio_change.start(task_id)`
- Job: `cookie_robot.start(task_id)`
- Job: `proxy.validate_all()` (низкий приоритет)

Примечания:
- Для параллельной обработки уже есть заготовки в `uploader/async_impl/*`. Вынести их в сервисы и тонкие job-обёртки.
- На Windows воркерах ставим лимиты параллелизма (ENV): `MAX_CONCURRENT_ACCOUNTS`, `BATCH_SIZE`.


## HTTP/REST API (добавить к существующим путям)

Все эндпоинты защищены сессией/ролями администратора и/или service-токеном. Ответы — JSON. Примеры схем упрощены для краткости.

- POST `/api/bulk-tasks/`
  - Создать задачу, прикрепить аккаунты/видео (списки идентификаторов).
  - Body:
    ```json
    {
      "name": "Upload 2025-08-11",
      "account_ids": [1,2,3],
      "video_ids": [101,102,103],
      "default_location": "Moscow",
      "default_mentions": "@user1\n@user2"
    }
    ```
  - Response: `{ "id": 55, "status": "PENDING" }`

- POST `/api/bulk-tasks/{id}/start`
  - Поставить в очередь `bulk_upload.start`.
  - Response: `{ "enqueued": true, "queue": "default" }`

- GET `/api/bulk-tasks/{id}`
  - Детали, прогресс, счётчики.

- GET `/api/bulk-tasks/{id}/logs?after=<cursor>`
  - Стрим/пагинация логов.

- GET `/api/media/{video_id}/download`
  - Защищённая выдача файла (JWT/ServiceToken + одноразовый signed URL).

- POST `/api/proxies/validate-all`
  - Поставить задачу в `low`.

Аналогичные маршруты для `bulk-login`, `warmup`, `follow`, `avatar-change`, `bio-change`, `cookie-robot`.


## Логика работы модулей (подробно)

Ниже — детализация конкретных пайплайнов. В скобках указаны текущие опорные функции/файлы, которые следует инкапсулировать в классы сервисов.

### 1. Массовая загрузка видео (Bulk Upload)

- Инициализация (UI): создание `BulkUploadTask`, привязка `BulkUploadAccount`, `BulkVideo`, `VideoTitle`. (см. `uploader/models.py`, `uploader/views_mod/bulk.py`).
- Запуск: POST `/api/bulk-tasks/{id}/start` → RQ job.
- Обработка (Worker):
  1) `BulkUploadRepository.get_task(task_id)` — агрегат: аккаунты, видео, заголовки, дефолтные локации/упоминания.
  2) Батчирование аккаунтов с семафором (см. `uploader/async_impl/runner.py::process_account_batch_async`).
  3) Для каждого аккаунта (core алгоритм):
     - `AccountRepository.acquire_account_lock` — взаимное исключение.
     - Получить/назначить прокси (`get_random_proxy`/`current_proxy`).
     - `BrowserSessionFactory.create` — запустить Dolphin профиль/контекст Playwright.
     - `LoginService.login` — учесть reCAPTCHA, 2FA, статус `SUSPENDED`.
     - `UploadService.navigate_to_upload` (см. `bulk_tasks_playwright.py::navigate_to_upload_with_human_behavior`).
     - Для каждого видео:
       - Скачать поток файла через `/api/media/{id}/download` (или S3 signed URL).
       - `UploadService.upload_single_video(...)` — строгая последовательность:
         - выбор файла (send_keys)
         - обработка «ОК»
         - `CropHandler` селекции/кропов
         - 2x Next
         - описание по символам с задержками
         - установка локации с подсказкой
         - установка упоминаний с подсказкой и Done
         - Share + верификация успеха
       - Инкремент счётчиков успехов/ошибок.
     - Обновить статус аккаунта в задаче и снять lock.
  4) По окончании — статус задачи `COMPLETED/FAILED/PARTIALLY_COMPLETED`.
- Основные функции к инкапсуляции: `run_bulk_upload_task`, `perform_instagram_operations`, `upload_video_with_human_behavior`, `click_next_button`, `handle_cookie_consent`, `init_human_behavior` и др. (см. `uploader/bulk_tasks_playwright.py`, `uploader/instagram_automation.py`, `uploader/login_optimized.py`).
- Человеческое поведение: `uploader/human_behavior.py`, `human_behavior_config.py`.
- Устойчивые селекторы: `uploader/selectors_config.py` → вынести в JSON/словарь с фоллбэками.

Ошибки/ретраи:
- Сетевые таймауты навигации → 2-3 ретрая с эксп. бэкоффом.
- Смена селектора (fallback) → альтернативные XPath/CSS + проверка текста.
- reCAPTCHA → `captcha_solver.solve_recaptcha_if_present`.
- Подозрение на бан/человеческую проверку → статусы `HUMAN_VERIFICATION_REQUIRED`/`SUSPENDED` с логом.

Логирование:
- Каждая фаза пишет структурные события: NAVIGATION, LOGIN, UPLOAD, CROPPING, SHARE, VERIFY.
- Периодические heartbeat-сообщения, чтобы UI видел «живой» прогресс.

### 2. Bulk Login

- Аналогично Bulk Upload, но без загрузки видео, только стабильный логин/проверки (см. `uploader/login_optimized.py`, `uploader/views_mod/bulk_login_runner.py`).
- Отрабатывает cookie refresh, снимает бейджи human verification (см. `task_utils.clear_human_verification_badge`).

### 3. Warmup

- Использует `WarmupTask` и `WarmupTaskAccount` с параметрами диапазонов действий (scroll, likes, stories, follow few) — см. `uploader/views_warmup.py`, `uploader/models.py::WarmupTask*`.
- Сервис `WarmupService` применяет сценарии действий с человеческими задержками.

### 4. Avatar Change

- `AvatarChangeTask`/`AvatarImage` — стратегии: random_reuse/one_to_one.
- Сервис `AvatarService.change_avatar(image)` открывает профиль и меняет аватар.

### 5. Bio Change

- `BioLinkChangeTask` — меняет линк, учитывает задержки, верификацию.

### 6. Follow

- `FollowTask` + `FollowCategory`/`FollowTarget`.
- `FollowService` производит небольшие количества follow с задержками, учитывая риски.

### 7. Cookie Robot

- `DolphinCookieRobotTask` использует Dolphin API (см. `uploader/tasks_playwright.py::run_cookie_robot_task`, `bot/src/instagram_uploader/dolphin_anty.py`).
- На Windows — ретраи запуска профиля (`Failed to start profile`, `Missing port or wsEndpoint`).

### 8. Proxy Diagnostics

- Массовые проверки, обновление статусов (`active/inactive/banned/checking`), гео-инфо.

### 9. Media Uniquifier / Crop

- Использовать `opencv`/`ffmpeg` для уникализации (см. `uploader/async_video_uniquifier.py`, `uniq_video_eugene.py`).
- Воркеры Windows могут выполнять CPU bound задачи отдельно в очереди `low`.


## Конфигурация и параметры (внешние файлы)

- `.env` (UI/Ubuntu):
  - `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
  - `DATABASE_URL=postgresql://iguploader:***@db:5432/iguploader`
  - `REDIS_URL=redis://redis:6379/0`
  - `EPHEMERAL_PROFILES=1`, `CONCURRENCY_LIMIT=2`
  - `RUCAPTCHA_API_KEY=...`, `DOLPHIN_API_TOKEN=...`
- `.env` (Worker/Windows):
  - `DJANGO_SETTINGS_MODULE=instagram_uploader.settings`
  - `DATABASE_URL=postgresql://...@UBUNTU_HOST:5432/iguploader`
  - `REDIS_URL=redis://UBUNTU_HOST:6379/0`
  - `DOLPHIN_API_HOST=http://127.0.0.1:3001`
  - `PLAYWRIGHT_QUIET=1`, `PLAYWRIGHT_DISABLE_COLORS=1`
- `core/config/selectors.json`: набор ключей с массивом CSS/XPath вариантов + text-assertions.
- `core/config/human_behavior.json`: диапазоны задержек, параметры движений, вероятность «сканирования».


## Миграция на Postgres (шаги)

1) Зависимости:
   - Добавить: `dj-database-url`, при необходимости `psycopg[binary]` или оставить `psycopg2-binary`.
2) Настройки Django (`instagram_uploader/settings.py`):
   - Парсить `DATABASE_URL` с fallback на SQLite (см. docs/ephemeral-dolphin-profiles-and-postgres.md):
     ```python
     import dj_database_url
     DATABASE_URL = os.environ.get('DATABASE_URL')
     if DATABASE_URL:
         DATABASES = { 'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=False) }
     else:
         # fallback на SQLite для dev
     ```
3) Миграции:
   - `python manage.py makemigrations uploader`
   - `python manage.py migrate`
4) Индексы:
   - Индексы по статусам задач, FK, `InstagramAccount.username`.
5) Блокировки:
   - Добавить в `InstagramAccount`: `locked_by: CharField`, `locked_until: DateTimeField` + репозиторные методы lock/unlock.
6) Тестирование:
   - Смоук-тесты UI + запуск тестового воркера Windows на Postgres.


## Деплой и запуск

Ubuntu/UI:
- Установка Python, Postgres, Redis, Nginx, Gunicorn.
- `pip install -r requirements.txt`, `python manage.py migrate --noinput`.
- Создать суперпользователя; загрузить аккаунты/прокси.
- Запуск Gunicorn + Nginx, открыть `/` дашборд.

Windows/Workers:
- Python 3.12 + `pip install -r requirements.txt` + `playwright install`.
- Настроить `.env` (DB/Redis на Ubuntu), токены.
- Запуск: `python manage.py rqworker high default`.
- Опционально NSSM/SC для Windows-сервиса.


## Политики качества и устойчивости

- Человеческое поведение: строгие «расписания» задержек, mouse-move кривые, pre-scan элементов.
- Селекторы: набор вариантов + текстовые проверки; исключить brittle `nth-child`/динамические id.
- Ретраи: эксп. бэкофф, короткие/длинные таймауты, детектор сетевых сбоев.
- Централизованный логгинг: structlog; кореляция по `task_id`, `account_id`.
- Идемпотентность задач: проверять «уже загружено» перед повтором.
- Очистка ресурсов: закрытие страниц/контекстов; удаление temp-файлов; watchdog на зомби-процессы.


## Карта соответствия текущих функций → сервисы

- `uploader/bulk_tasks_playwright.py`:
  - `run_bulk_upload_task` → `BulkUploadJobHandler.start(task_id)`
  - `navigate_to_upload_with_human_behavior`, `upload_video_with_human_behavior`, `click_next_button` → `UploadService`
  - `init_human_behavior`, `simulate_extended_human_rest_behavior` → `HumanBehaviorService`
  - `handle_cookie_consent`, `perform_instagram_operations` → `UploadService`/`LoginService`
- `uploader/login_optimized.py` → `LoginService` (детектор состояния, 2FA, разбор статуса)
- `uploader/instagram_automation.py` → `BrowserSessionFactory`, `SelectorResolver`
- `uploader/captcha_solver.py` → `CaptchaService`
- `uploader/crop_handler.py` → `CropHandler`
- `uploader/email_verification_async.py` → `Email2FAService`
- `uploader/proxy_diagnostics.py` → `ProxyDiagnosticsService`
- `uploader/async_impl/*`, `uploader/async_bulk_tasks.py` → батч-оркестрация c семафорами
- `uploader/tasks_playwright.py::run_cookie_robot_task` → `CookieRobotService`


## Пример интерфейсов (скелеты классов)

```python
# core/services/automation/upload_service.py
class UploadService:
    def __init__(self, browser_factory, selector_resolver, human_behavior, logger):
        self.browser_factory = browser_factory
        self.selector_resolver = selector_resolver
        self.human_behavior = human_behavior
        self.logger = logger

    def process_account(self, account_task, videos, titles, options):
        # login → navigate → upload loop → counters/logs
        ...

    def upload_single_video(self, page, video_stream, title, location, mentions) -> bool:
        ...
```

```python
# core/repositories/account_repository.py
class AccountRepository:
    def acquire_lock(self, account_id, worker_id, ttl_sec) -> bool: ...
    def release_lock(self, account_id, worker_id) -> None: ...
    def mark_used(self, account_id) -> None: ...
```

```python
# worker/jobs/bulk_upload.py
from rq import get_current_job

def start(task_id: int, options: dict | None = None) -> None:
    job = get_current_job()
    # load aggregate → batch → process
```


## Пошаговый план внедрения

1) Поддержка Postgres в `settings.py` (через `dj-database-url`) + миграции.
2) Добавить Redis и django-rq; задокументировать очереди.
3) Вынести «тонкие» job-функции в `worker/jobs/*`, оставить бизнес-логику в сервисах.
4) Ввести слой репозиториев (минимальные адаптеры над текущими ORM-вызовами).
5) Вынести селекторы и human-config в JSON; реализовать `SelectorResolver` и `HumanBehaviorService`.
6) Реализовать защищённый `/api/media/{id}/download` для воркеров.
7) Включить структурный логгинг и лог-стриминг в UI.
8) Протестировать на одном Windows Worker; затем масштабировать.
9) Поэтапно переносить большие функции в классы сервисов, поддерживая обратную совместимость.


## Краткий чек-лист соответствия правилам

- Mimic Human Behavior: уже используется (`human_behavior.py`), параметризуем через конфигурацию.
- Robust Locators: `selectors_config.py` → JSON со списками локаторов + text-assertions.
- Clean, Modular Code: сервисы, репозитории, тонкие job-обёртки; SOLID.
- Error Handling & Resilience: ретраи, бэкофф, централизованный лог, статус-коды.


## Приложение A — Эндпоинты UI (расширение)

- Accounts/Proxies: уже присутствуют в `uploader/urls.py` (CRUD, импорт, тесты).
- Bulk Upload/UI: `bulk-upload/*` + новый REST `/api/bulk-tasks/*` для воркеров.
- Warmup/Follow/Avatar/Bio/CookieRobot: аналогично добавить `/api/...` старты и статусы.


## Приложение B — ENV примеры

UI/Ubuntu:
```
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=ui.domain,localhost
DATABASE_URL=postgresql://iguploader:STRONG_PASSWORD@DB_HOST:5432/iguploader
REDIS_URL=redis://redis-host:6379/0
EPHEMERAL_PROFILES=1
CONCURRENCY_LIMIT=2
RUCAPTCHA_API_KEY=...
DOLPHIN_API_TOKEN=...
```

Worker/Windows:
```
DJANGO_SETTINGS_MODULE=instagram_uploader.settings
DATABASE_URL=postgresql://iguploader:STRONG_PASSWORD@UBUNTU_HOST:5432/iguploader
REDIS_URL=redis://UBUNTU_HOST:6379/0
DOLPHIN_API_TOKEN=...
DOLPHIN_API_HOST=http://127.0.0.1:3001
PLAYWRIGHT_QUIET=1
PLAYWRIGHT_DISABLE_COLORS=1
PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1
```

---

Документ описывает целевую модульную архитектуру, границы и API модулей, потоки данных, требования к очередям и логированию, а также конкретные шаги миграции на Postgres и поэтапной декомпозиции кода на сервисы/репозитории. Это обеспечит независимое масштабирование Windows-исполнителей и стабильную эксплуатацию UI на Ubuntu. 