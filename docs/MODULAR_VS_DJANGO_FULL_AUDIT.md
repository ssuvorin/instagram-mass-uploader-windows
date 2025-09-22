## Полный аудит соответствия модульной архитектуры и текущего Django-проекта

Дата: 2025-09-19

- **Цель**: выровнять функционал, UI-страницы, API и функции между модулями (`modules FOR INSTAUPLOAD`) и актуальным Django-проектом (приложения `uploader`, `cabinet`, `personal_cab`, корневые `instagram_uploader`).
- **Результат**: подробная инвентаризация, помаппленная матрица соответствий, список расхождений по эндпоинтам/функциям/шаблонам и конкретные рекомендации к синхронизации.


### Объем и источник правды
- Источник правды: текущий Django-проект в этом репозитории (актуальная версия кода).
- Сопоставляемые части модулей: `modules FOR INSTAUPLOAD/web_ui_service` (UI), `modules FOR INSTAUPLOAD/bulk_worker_service` (бек/воркеры, контракты, интерфейсы).


## 1) Инвентаризация Django (актуальная)

### 1.1 Корневые маршруты `instagram_uploader/urls.py`
- admin/, `uploader.urls`, `cabinet.urls`, login/logout, post-login redirect.
- Логика `post_login_redirect`: редирект на `dashboard`/`cabinet_agency_dashboard`.

### 1.2 Uploader: URL → View → Шаблон
Источник: `uploader/urls.py`, `uploader/views.py` (фасад), `uploader/views_mod/*`.

- Dashboard: name=`dashboard` → `views.dashboard` → `uploader/dashboard.html`.
- Tasks:
  - `tasks/` → `task_list` → `uploader/task_list.html`
  - `tasks/<id>/` → `task_detail` → `uploader/task_detail.html`
  - `tasks/create/` → `create_task` → `uploader/create_task.html`
  - `tasks/<id>/start/` → `start_task`
- Accounts:
  - `accounts/` → `account_list` → `uploader/account_list.html`
  - `accounts/<id>/` → `account_detail` → `uploader/account_detail.html`
  - `accounts/create/` → `create_account` → `uploader/create_account.html`
  - `accounts/import/` → `import_accounts` → `uploader/import_accounts.html`
  - `accounts/import-ua-cookies/` → `import_accounts_ua_cookies` → `uploader/import_accounts_ua_cookies.html`
  - `accounts/import-bundle/` → `import_accounts_bundle` → `uploader/import_accounts_bundle.html`
  - `accounts/<id>/warm/` → `warm_account`
  - `accounts/<id>/edit/` → `edit_account` → `uploader/edit_account.html`
  - `accounts/<id>/change-proxy/` → `change_account_proxy` → `uploader/change_account_proxy.html`
  - `accounts/<id>/create-profile/` → `create_dolphin_profile`
  - `accounts/<id>/delete/` → `delete_account` → `uploader/delete_account.html`
  - `accounts/bulk-change-proxy/` → `bulk_change_proxy` → `uploader/bulk_change_proxy.html`
  - `accounts/refresh-dolphin-proxies/` → `refresh_dolphin_proxies` → `uploader/refresh_dolphin_proxies.html`
- Proxies:
  - `proxies/` → `proxy_list` → `uploader/proxy_list.html`
  - `proxies/create/` → `create_proxy` → `uploader/create_proxy.html`
  - `proxies/<id>/edit/` → `edit_proxy` → `uploader/edit_proxy.html`
  - `proxies/<id>/test/` → `test_proxy`
  - `proxies/<id>/delete/` → `delete_proxy`
  - `proxies/import/` → `import_proxies` → `uploader/import_proxies.html`
  - `proxies/validate-all/` → `validate_all_proxies`
  - `proxies/cleanup-inactive/` → `cleanup_inactive_proxies` → `uploader/cleanup_inactive_proxies.html`
- Bulk Upload:
  - `bulk-upload/` → `bulk_upload_list` → `uploader/bulk_upload/list.html`
  - `bulk-upload/create/` → `create_bulk_upload` → `uploader/bulk_upload/create.html`
  - `bulk-upload/<id>/` → `bulk_upload_detail` → `uploader/bulk_upload/detail.html`
  - `bulk-upload/<id>/add-videos/` → `add_bulk_videos` → `uploader/bulk_upload/add_videos.html`
  - `bulk-upload/<id>/add-titles/` → `add_bulk_titles` → `uploader/bulk_upload/add_titles.html`
  - `bulk-upload/<id>/start/` → `start_bulk_upload`
  - `bulk-upload/<id>/start-api/` → `start_bulk_upload_api`
  - `bulk-upload/<id>/delete/` → `delete_bulk_upload`
  - `bulk-upload/<id>/logs/` → `get_bulk_task_logs`
  - `bulk-upload/*/bulk-edit-location-mentions` → `bulk_edit_location_mentions` → `uploader/bulk_upload/bulk_edit_location_mentions.html`
  - `bulk-upload/video/<id>/edit-location-mentions/` → `edit_video_location_mentions` → `uploader/bulk_upload/edit_video_location_mentions.html`
- Bulk Login:
  - `bulk-login/` (list/create/detail/start/delete/logs) → шаблоны `uploader/bulk_login/*`
- Cookies dashboard:
  - `cookies/` → `cookie_dashboard` → `uploader/cookies/dashboard.html`
  - `cookies/tasks/…` → list/detail/start/stop/delete/logs → `uploader/cookies/*`
  - `cookies/accounts/<id>/` → `account_cookies` → `uploader/cookies/account_cookies.html`
  - `cookies/bulk/` → `bulk_cookie_robot` → `uploader/cookies/bulk_cookie_robot.html`
  - `cookies/bulk/refresh/` → `refresh_cookies_from_profiles`
- Captcha API: `api/captcha-*` → `captcha_notification`/`get_captcha_status`/`clear_captcha_notification`
- TikTok: UI и прокси-API (`misc.*`) → `uploader/tiktok/*` шаблоны
- Hashtag Analyzer: `tools/hashtag/` → `hashtag_analyzer` → `uploader/hashtag/*`
- Avatars/Bio/Follow/Warmup: как в `urls.py` → `uploader/avatars/*`, `uploader/bio/*`, `uploader/follow/*`, `uploader/warmup/*`

Ключевые реализации см. в `uploader/views_mod/accounts.py` (создание/импорт/прокси/Dolphin), `uploader/views_mod/bulk.py`, `uploader/views_mod/cookie_robot.py`, etc.

### 1.3 Personal Cabinet (`personal_cab`)
- Core: `dashboard`, `admin_dashboard`, `agency_dashboard`, `client_dashboard` + AJAX API (`search`, `client_data`, `agency_clients`, `dashboard_data`). Шаблоны: `personal_cab/core/templates/core/*`.
- ig_dashboard/urls.py агрегирует управление агентствами/клиентами/хэштегами и аналитику API.


## 2) Инвентаризация модулей (UI и Worker)

### 2.1 Web UI Service (`modules FOR INSTAUPLOAD/web_ui_service`)
- UI Core (`ui_core/urls.py`, `ui_core/views.py`):
  - `''` → `dashboard` → `templates/uploader/dashboard.html`
  - `accounts/*` → список/деталь/создание → `templates/uploader/*`
  - `bulk-upload/*` → список/деталь/создание/старт через worker → `templates/uploader/bulk_upload/*`
  - API: `api/tasks/<id>/status`, `health/`
  - Взаимодействует с `api_client` (management_api, worker_api) вместо прямого ORM.
- Dashboard override + monitoring (`dashboard/urls.py`, `dashboard/views.py`, `monitoring_views.py`):
  - Переопределения старт-экшенов на вызов воркера: `bulk-upload/<id>/start/`, `bulk-login/<id>/start/`, `warmup/<id>/start/`, `avatars/<id>/start/`, `bio/<id>/start/`, `follow/tasks/<id>/start/`, `proxy_diag/<id>/start/`, `media_uniq/<id>/start/`.
  - Pull-mode API для воркера: `api/bulk-tasks/<id>/aggregate`, status, delete, и т.п.
  - Мониторинг: `monitoring/*` и API для метрик и restart.
  - Управление аккаунтами/прокси через API endpoints (`api_views.py`).
- Шаблоны UI модуля: `web_ui_service/templates/uploader/*` покрывают основной набор страниц Uploader.

### 2.2 Bulk Worker Service
- Контракты, раннеры, оркестратор, задачи Playwright/Instagrapi и пр. Синхронизация идёт через API конечные точки `web_ui_service/dashboard/api_views.py` и worker endpoints `/api/v1/*`.


## 3) Матрица соответствия: Django Uploader ↔ Web UI Service

Ниже — ключевые соответствия (полные списки в разделах 1.2 и 2.1):

- Dashboard: Django `dashboard` ↔ UI Core `dashboard` (шаблон одинаковый `uploader/dashboard.html`).
- Accounts: `account_list/detail/create` ↔ те же пути в UI Core; шаблоны совпадают.
- Bulk Upload: list/detail/create ↔ совпадает; старт задачи в Django — локальный/через фасад; в модуле — форсирован через worker (`start_bulk_upload_via_worker`).
- Bulk Login/Warmup/Avatars/Bio/Follow: в Django присутствуют полные UI и эндпоинты; в модуле — есть старт-эндпоинты, агрегаты статусов, но UI-страницы также присутствуют в шаблонах (`templates/uploader/...`).
- Cookies: Django имеет полный набор UI и действий; модульные шаблоны и API присутствуют, требуется сверка API-вызовов (`api_views.py`).
- Proxies: Django UI + действия; в модуле — API endpoints на создание/импорт/валидацию/cleanup, шаблоны присутствуют.
- TikTok: Django имеет UI и прокси-API под `misc.*`; в модуле — заглушки API (`tiktok_booster_*`) и UI шаблоны `templates/uploader/tiktok/*`. Надо сверить, все ли серверные прокси-эндпоинты реализованы в модуле.

Дополнено (паритет проверен):
- Все корневые шаблоны `uploader/templates/uploader/*` имеют эквиваленты в `web_ui_service/templates/uploader/*` (61/71). Совпадающие: dashboard, accounts CRUD, proxies CRUD, bulk_upload (list/detail/create/add_videos/add_titles/bulk_edit_location_mentions/edit_video_location_mentions), bulk_login (list/detail/create), cookies (dashboard/list/detail/create/delete/account_cookies/bulk_cookie_robot), avatars/bio/follow/warmup, logs, cleanup_inactive_proxies, bulk_change_proxy, change/edit proxy/account. TikTok-раздел синхронизирован: добавлены страницы `uploader/tiktok/base.html`, `videos_upload.html`, `videos_titles.html`, `videos_prepare.html`, `videos_start.html`, `dashboard.html` в модульном UI.
- URL-роуты: в модуле присутствуют все основные: tasks/accounts/proxies/bulk_upload/bulk_login/cookies/avatars/bio/follow/warmup. TikTok эндпоинты присутствуют (booster/videos), реализованы UI-слой выбора сервера (`api/tiktok/set-active-server/`) и AJAX‑polling статусов (booster/videos start).


## 4) Выявленные расхождения и риски

1) Старт задач (Bulk/Bio/Follow/etc.)
   - Django: `uploader/urls.py` маппит `start_*` на локальные view-функции из `views_mod`.
   - Модуль: переопределяет эти `start`-пути на `start_*_via_worker` и использует `_dispatch_batches`, `_acquire_lock` и воркер-пулы.
   - Риск: двойная семантика стартов. Рекомендация: стандартизировать на «через worker» и в Django-фасаде вызывать такие же механизмы блокировок/батчирования.

2) API-ориентированная архитектура
   - Модульная UI использует `api_client` и management/worker API. Django Uploader во многих местах работает напрямую с ORM (например, `views_mod/accounts.py`).
   - Риск: расхождение источников данных и сайд-эффектов. Рекомендация: либо перевести Django UI на API-клиенты, либо в модуле обеспечить тонкие прокси над ORM для полного 1:1.

3) Cookies и Device Session
   - Django: подробная логика импорта (UA+Cookies, Bundle), сохранение в `InstagramCookies` и `InstagramDevice.session_settings`, правила классификации mobile/web, детальное наполнение `session_settings`.
   - Модуль: шаблоны и API есть, но требуется подтвердить, что API реализует тот же набор правил парсинга/классификации/сохранения.
   - Рекомендация: перенести и переиспользовать утилиты парсинга из `views_mod/accounts.py` в общий модуль, задокументировать контракт.

4) TikTok Booster/Video
   - Django: UI + прокси-эндпоинты `misc.*` (upload/proxy/prepare/start/stats/pipeline/release-accounts, set-active-server, ping).
   - Модуль: реализованы API-роуты и диспетчер `TikTokDispatcher`, подключен выбор активного сервера (persist). Шаблоны TikTok (видео) частично отсутствуют (videos_*). 
   - Рекомендация: добавить недостающие TikTok страницы в модульный templates и включить polling статусов.

5) Мониторинг и Lock Management
   - Модуль: расширенные `monitoring_views.py`, метрики и рестарты, TaskLock, worker registry.
   - Django: базовые страницы логов/тасков. 
   - Рекомендация: интегрировать мониторинг и lock manager в Django либо окончательно вынести UI на модульный сервис и подключить маршруты из модуля в основной роутинг.

6) Role-based visibility (Cabinet)
   - Django: `account_list` и другие страницы фильтруют видимость по клиенту/агентству/суперадмину.
   - Модуль: UI Core опирается на management API. Надо гарантировать, что API сервит такие же ограничения.


## 5) Рекомендации к синхронизации (пошагово)

1) Унифицировать слой запуска задач
   - В Django-фасаде (`uploader/views.py` и `views_mod/*`) заменить локальные `start_*` на вызовы «через worker» по образцу модульного `dashboard/views.py`.
   - Ввести единый helper: `_acquire_lock`, `_dispatch_batches`, `_worker_headers`, `_worker_url` в общий модуль (например, `uploader/services/worker_dispatch.py`) и переиспользовать.

2) Выделить парсинг аккаунтов/куки в общий модуль
   - Вынести логику из `views_mod/accounts.py` (UA+Cookies, Bundle, mobile/web классификация, извлечение параметров, создание Dolphin профилей) в `uploader/services/accounts_import.py`.
   - Подключить этот модуль из Django UI и модульного `api_views.py` для одинакового поведения.

3) Согласовать API-контракты
   - Сформировать спецификацию для management/worker API по аккаунтам/прокси/таскам/куки с полями и статусами.
   - В `web_ui_service/dashboard/api_views.py` реализовать все отсутствующие эндпоинты, соответствующие Django `misc.*` (TikTok Booster/Video) и cookies dashboards.

4) Шаблоны UI
   - Подтвердить 1:1 соответствие шаблонов в `uploader/templates/uploader/*` и `web_ui_service/templates/uploader/*` (названия/контекст/полям форм).
   - Выделить общие макросы/partialы для форм и списков, чтобы избежать дрейфа.

5) Ролевые ограничения и фильтрация
   - Прописать в management API фильтрацию по пользователю/клиенту/агентству, чтобы UI Core модуля строго следовал тем же ограничениям, что и Django.

6) Тест-контракты
   - В `modules FOR INSTAUPLOAD/tests/` уже есть тесты UI-локов/интеграций. Добавить тесты контрактов API для аккаунтов/прокси/куки/тик-ток.


## 6) Детальная карта функций (фрагменты, проверенные в текущем аудите)

Ниже перечислены проверенные функции и их ключевые обязанности. Полный перечень очень большой; для поддержания читаемости сгруппировано по областям.

### 6.1 Accounts (Django `uploader/views_mod/accounts.py`)
- `account_list(request)`: фильтры, поиск, аннотации по сумме аплоадов, ролевая видимость клиента/агентства.
- `account_detail(request, account_id)`: сбор `cookie_summary` и `session_summary`, извлечение важных cookie-имен, анализ «instagram_session_active».
- `create_account(request)`: создание аккаунта, подбор прокси с учетом locale, создание Dolphin профиля с снапшотом.
- `import_accounts(request)`: парсер строк разных форматов, mobile/web классификация, заполнение `InstagramDevice.session_settings` и `InstagramCookies`, подбор/линковка прокси, Dolphin профиль + импорт cookies.
- `import_accounts_ua_cookies(request)`: парсинг формата UA|cookies|device_info, приведение к Dolphin cookie-формату, снапшот девайса.
- `import_accounts_bundle(request)`: устойчивый парсер сегментов (creds/ua/device/cookies/proxy), декод `Authorization=Bearer IGT:2:*`, наполнение device settings.
- `edit_account`, `change_account_proxy`, `delete_account`, `warm_account`: корректная синхронизация полей `proxy/current_proxy`, обновление Dolphin, освобождение связей.

Соответствие в модуле:
- UI-страницы совпадают по названиям. Вызовы идут через `management_api`/`api_views` — требуется подтянуть еквивалентную бизнес-логику (особенно парсинг и сохранение).

### 6.2 Bulk Upload/ Bulk Login / Warmup / Avatars / Bio / Follow
- Django: полный CRUD страниц, старт/логи/агрегации через локальные views или API-прокси.
- Модуль: переопределения start в `dashboard/views.py`, агрегации/статусы в `dashboard/api_views.py`.
- Необходимо убедиться, что:
  - Все `get_*_logs`, `*_detail`, списки и удаления реализованы и в модуле API с теми же названиями полей/статусами.

### 6.3 Cookies Dashboard
- Django: `cookie_dashboard`, `cookie_task_list/detail/start/stop/delete/logs`, `account_cookies`, `bulk_cookie_robot`, `refresh_cookies_from_profiles`.
- Модуль: шаблоны присутствуют; нужно подтвердить эндпоинты `api_views.py` для полного набора (start/stop/delete/logs/refresh).

### 6.4 Proxies
- Django: импорт/валидация/cleanup/test, список/создание/редактирование.
- Модуль: API роуты есть (create/import/validate/cleanup/test). Синхронизировать форматы ответов/ошибок и коды статусов.

### 6.5 TikTok Booster / Videos
- Django: богатый набор UI и прокси API через `views_mod/misc.py` (booster/videos + выбор активного сервера).
- Модуль: API реализованы, добавлен `TikTokDispatcher` и выбор активного сервера с persisted‑состоянием; TikTok video‑шаблоны добавлены и подключён AJAX‑polling статусов.

Перечень несовпадений (после синхронизации TikTok):
- Маршруты: проверить контекстные ключи/active_tab на всех TikTok страницах (в работе в задаче «Reconcile routes/contexts»).
- Instagram‑разделы: требуется финальная сверка контекстов форм и имен ключей.


## 7) Instagram E2E Pipeline Map (модульная инфра)

Ниже — сквозная карта для каждой сущности: UI → API (модуль) → Runner/Orchestrator → Статус‑репорты → Шаблоны.

- Bulk Upload (видео Instagram)
  - UI: `uploader/bulk_upload/*` (list/detail/create/add_videos/add_titles)
  - API (UI модуль): `dashboard/api_views.py`: aggregates `api/bulk-tasks/<id>/aggregate`, status `api/bulk-tasks/<id>/status`, account counters
  - Старт: Web UI override → `dashboard/views.py:start_bulk_upload_via_worker` → фан-аут к воркерам `/api/v1/bulk-tasks/start`
  - Worker: `orchestrator_v2.start_bulk_upload()` → `TaskRunnerFactory['bulk_upload']` → `BulkUploadTaskRunner`
  - Статус: worker репорты → UI `bulk_task_status`/`bulk_account_status` (уже реализовано)
  - Templates: `templates/uploader/bulk_upload/*`

- Bulk Login
  - UI: `uploader/bulk_login/*`
  - API (UI модуль): aggregates `api/bulk_login/<id>/aggregate`, delete, status (generic)
  - Старт: `dashboard/views.py:start_bulk_login_via_worker` → `/api/v1/bulk-login/start`
  - Worker: `orchestrator_v2.start_bulk_login()` → `TaskRunnerFactory['bulk_login']`
  - Статус: generic endpoints

- Warmup
  - UI: `uploader/warmup/*`
  - API (UI модуль): `api/warmup/<id>/aggregate`
  - Старт: `start_warmup_via_worker` → `/api/v1/warmup/start`
  - Worker: `orchestrator_v2.start_warmup()` → runner
  - Статус: generic

- Avatars
  - UI: `uploader/avatars/*`
  - API (UI модуль): `api/avatar/<id>/aggregate`
  - Старт: `start_avatar_via_worker` → `/api/v1/avatar/start`
  - Worker: `orchestrator_v2.start_avatar()` → runner
  - Статус: generic

- Bio
  - UI: `uploader/bio/*`
  - API (UI модуль): `api/bio/<id>/aggregate`
  - Старт: `start_bio_via_worker` → `/api/v1/bio/start`
  - Worker: `orchestrator_v2.start_bio()` → runner
  - Статус: generic

- Follow
  - UI: `uploader/follow/*`
  - API (UI модуль): `api/follow/<id>/aggregate` + category mgmt APIs
  - Старт: `start_follow_via_worker` → `/api/v1/follow/start`
  - Worker: `orchestrator_v2.start_follow()` → runner
  - Статус: generic

- Cookies Dashboard
  - UI: `uploader/cookies/*`
  - API (UI модуль): cookies parity endpoints (list/detail/start/stop/delete/logs, account cookies, bulk refresh)
  - Старт: `cookie_robot_start_api` (создание задачи) или через worker `/api/v1/cookie-robot/start`
  - Worker: `orchestrator_v2.start_cookie_robot()` → runner
  - Статус: cookies endpoints / generic

- Proxies
  - UI: `uploader/proxies/*`
  - API (UI модуль): create/import/validate/cleanup/test
  - Worker: используются по месту в раннерах (проверки/диагностика)

- Accounts
  - UI: `uploader/accounts/*`
  - API (UI модуль): `create_account_api`, `import_accounts_api` (поддержка Basic/UA+Cookies/Bundle), `edit_account_api`, `bulk_change_proxy_api`, `create_dolphin_profile_api`
  - Shared: `services/accounts_import.py` — парсер и сборка `InstagramDevice.session_settings`/`InstagramCookies`

- Media Uniq
  - UI: `bulk_worker_service` feature, UI: `api/media_uniq/*`
  - Старт: `start_media_uniq_via_worker` → `/api/v1/media-uniq/start`
  - Worker: `orchestrator_v2.start_media_uniq()` → runner
  - Статус: `media_uniq_aggregate` + generic

Итог: все базовые Instagram пайплайны «проведены» через модульный UI и воркеры; статусы репортятся в уже реализованные API. Далее по отчёту правим расхождения (контекст шаблонов, недостающие страницы, согласование контрактов).


## 7) План внедрения изменений (минимизация рисков)

1) Начать с «тонкого адаптера» в Django, переводящего `start_*` на worker API (без изменения UI/шаблонов).
2) Вынести парсинг аккаунтов и куки в общий модуль и подключить из обоих миров (Django и модульного API).
3) Добавить/синхронизировать TikTok API в модуле, покрыть тестами контрактов.
4) Закрыть различия в Cookies Dashboard (API покрытие), затем Proxies.
5) Провести ревизию контекстов шаблонов: единые имена ключей в `context` для всех страниц.
6) Добавить e2e-тесты UI (Playwright) с «человеческим поведением» (из Always Applied Workspace Rules) и устойчивыми селекторами.


## 8) Чек-лист соответствия (для контроля выполнения)

- [ ] Все `start_*` маршруты используют worker API с lock-менеджером.
- [ ] Парсинг аккаунтов/куки централизован и одинаково работает в Django и модуле.
- [ ] Cookies dashboard: API-паритет, логи и статусы идентичны.
- [ ] Proxies: create/import/validate/test/cleanup — API эквивалентны, шаблоны синхронизированы.
- [x] TikTok: все UI страницы и серверные прокси-эндпоинты добавлены в модуле; контракты совпадают (booster/videos proxy, set-active-server, ping, stats, pipeline, release-accounts).
- [x] TikTok: реализован выбор сервера пользователем UI (persist через `api_tiktok_set_active_server`) и все вызовы идут на выбранный сервер.
- [x] TikTok: добавлен polling статусов на страницах booster/videos.

Подчек-лист TikTok страниц/маршрутов:
- [x] `uploader/tiktok/base.html` — стили/статическая статика/иконки/тема
- [x] `uploader/tiktok/dashboard.html` — селектор сервера, ping, быстрые действия
- [x] `uploader/tiktok/videos_upload.html` — загрузка видео, прогресс
- [x] `uploader/tiktok/videos_titles.html` — загрузка заголовков
- [x] `uploader/tiktok/videos_prepare.html` — параметры загрузки
- [x] `uploader/tiktok/videos_start.html` — старт, release, polling
- [x] `uploader/tiktok/booster.html` — наследование от tiktok/base, паритет стилей
- [ ] Role-based visibility: подтверждена через management API (фильтры как в Django).
- [ ] Шаблоны `templates/uploader/*` синхронизированы по контексту и формам.
- [ ] Тесты контрактов и e2e UI зелёные.


## 9) Приложение: заметки по качеству кода и устойчивости

- Логи: сохранять время, действие, селекторы (для UI), результаты, коды ответов API.
- Ретраи: для внешних вызовов (Dolphin/worker) — экспоненциальный backoff, таймауты.
- Конфигурация: вынести константы (локали, правила классификации) в конфиг.
- Селекторы UI: использовать data-атрибуты вместо nth-child; fallback-ы по тексту.
- Идентичность шаблонов: избегать размножения разметки, выделить общие partials.


---

Примечание: данный документ подготовлен на основе анализа ключевых модулей и маршрутов. Для полного 100% покрытия каждой функции и страницы предлагается выполнить описанный чек-лист и внедрить унификацию кода/контрактов. Это обеспечит «идентичность» поведения между модульной архитектурой и текущим Django-проектом.


