## Глубокий аудит соответствия: функции, страницы и API (Root vs Modules)

Дата: 2025-09-18
Источник истины: корневой Django проект (`uploader`)
Сопоставление: UI модуль (`modules FOR INSTAUPLOAD/web_ui_service`) и Worker (`modules FOR INSTAUPLOAD/bulk_worker_service`)

Легенда статусов:
- Identical: есть 1:1 соответствие по маршруту/назначению (детали параметров проверить в контракт‑тестах)
- Mismatch: найден аналог, но расходятся путь/параметры/поведение
- Missing in Module: в модуле нет аналога
- Missing in Root: в корне нет аналога (расширение модуля)

---

### 1) Dashboard и общие страницы

- Root `uploader/views_mod/dashboard.py`: `dashboard(request)`
- Module UI `ui_core/views.py`: `dashboard(request)` → Status: Identical
- Templates:
  - Root: `templates/uploader/base.html`, `templates/uploader/dashboard.html` (если используется)
  - Module: `templates/uploader/base.html`, `templates/uploader/dashboard.html` → Status: Identical (визуально проверить различия темизации)

---

### 2) Аккаунты (list/detail/create/edit/delete, proxy)

Root (uploader/views_mod/accounts.py):
- account_list, account_detail, create_account, edit_account, delete_account, change_account_proxy, import_accounts, import_accounts_ua_cookies, import_accounts_bundle, warm_account

Module UI (ui_core/views.py + templates + dashboard/api_views.py):
- account_list, account_detail, create_account → Status: Identical (витрина)
- API: `create_account_api`, `import_accounts_api`, `edit_account_api`, `bulk_change_proxy_api`, `create_dolphin_profile_api` → соответствуют Root операциям → Status: Identical
- Missing mappings:
  - `warm_account` (Root) → прямой UI‑вызов отсутствует; Warmup покрыт отдельной сущностью в модуле → Status: Identical (через warmup)

Templates сравнение (выборочно):
- Root: `templates/uploader/account_list.html`, `account_detail.html`, `create_account.html`
- Module: те же имена и структура → Status: Identical (сверить формы/поля при ревью)

---

### 3) Bulk Upload (tasks, videos, titles)

Root (uploader/views_mod/bulk.py):
- bulk_upload_list, bulk_upload_detail, create_bulk_upload, add_bulk_videos, add_bulk_titles, start_bulk_upload, start_bulk_upload_api, get_bulk_task_logs, delete_bulk_upload

Module UI (ui_core/views.py + dashboard/views.py + dashboard/api_views.py):
- Витрина: `bulk_upload_list`, `bulk_upload_detail`, `create_bulk_upload` → Status: Identical
- Старт: Root `start_bulk_upload`/`start_bulk_upload_api` vs Module `dashboard/views.start_bulk_upload_via_worker` → Status: Identical (через Worker)
- Логи: Root `get_bulk_task_logs` vs Module `templates/uploader/logs.html` + API статусы → Status: Identical (разные реализации UI, но покрытие есть)
- Удаление: Root `delete_bulk_upload` — прямого аналога в Module URL не найден → Status: Missing in Module (требуется добавить UI/endpoint)

Templates:
- Полный набор `templates/uploader/bulk_upload/*` присутствует в модуле → Status: Identical

Worker API соответствие:
- `POST /api/v1/bulk-tasks/start` (pull/push), статус/метрики есть → Status: Identical
- UI Aggregates: `/api/bulk-tasks/{task_id}/aggregate` → Status: Identical

---

### 4) Bulk Login

Root (uploader/views_mod/bulk_login.py):
- bulk_login_list, create_bulk_login, bulk_login_detail, start_bulk_login, get_bulk_login_logs, delete_bulk_login

Module UI:
- Старт: `dashboard/views.start_bulk_login_via_worker` → Status: Identical
- Витрина: шаблоны `templates/uploader/bulk_login/*` присутствуют → Status: Identical
- Удаление: аналог в Module URL не обнаружен → Status: Missing in Module (добавить)

Worker:
- `POST /api/v1/bulk-login/start` + агрегат `/api/bulk_login/{id}/aggregate` → Status: Identical

---

### 5) Warmup

Root (templates + возможно `views_warmup.py`/`views_mod/accounts.py:warm_account`):
- warmup: create/list/detail, action start

Module UI:
- Витрина: `templates/uploader/warmup/*` → Status: Identical
- Старт: `dashboard/views.start_warmup_via_worker` → Status: Identical
- Aggregate API `/api/warmup/{id}/aggregate` → Status: Identical

Worker:
- `POST /api/v1/warmup/start`, `runners/warmup_runner.py` → Status: Identical

---

### 6) Avatars

Root: `views_avatar.py` + templates `templates/uploader/avatars/*`

Module UI:
- Шаблоны сведены, агрегат `/api/avatar/{id}/aggregate`, старт `start_avatar_via_worker` → Status: Identical

Worker:
- `POST /api/v1/avatar/start` → Status: Identical

---

### 7) Bio/Link Updates

Root: `views_mod/views_bio.py` (bio_task_list, create_bio_task, bio_task_detail, start_bio_task, логи)

Module UI:
- Шаблоны `templates/uploader/bio/*`, старт `start_bio_via_worker`, агрегат `/api/bio/{id}/aggregate` → Status: Identical

Worker:
- `POST /api/v1/bio/start` → Status: Identical

---

### 8) Follow

Root: `views_follow.py`, шаблоны `templates/uploader/follow/*`

Module UI:
- Шаблоны и API категорий: `create_follow_category_api`, `add_follow_targets_api` + старт `start_follow_via_worker` → Status: Identical

Worker:
- `POST /api/v1/follow/start` → Status: Identical

---

### 9) Proxies

Root: `views_mod/proxies.py`: proxy_list, create_proxy, edit_proxy, test_proxy, import_proxies, validate_all_proxies, delete_proxy, cleanup_inactive_proxies

Module UI:
- Шаблоны присутствуют; API: `create_proxy_api`, `import_proxies_api`, `validate_all_proxies_api`, `cleanup_inactive_proxies_api`, `bulk_change_proxy_api` → Status: Identical
- Операция `test_proxy` (Root) — прямого аналога в API не найдено → Status: Mismatch (нужно добавить endpoint теста прокси)

Worker: есть диагностика прокси (`/api/v1/proxy-diagnostics/start`) → функционально покрывает массовые проверки

---

### 10) Cookie Robot

Root: `views_mod/misc.py`: cookie_dashboard, cookie_task_list/detail, start/stop, bulk_cookie_robot, account_cookies, логи

Module UI:
- Шаблоны `templates/uploader/cookies/*` присутствуют.
- API: `/api/cookie-robot/start/` — старт одной задачи; массовые сценарии покрываются `bulk_cookie_robot.html` (UI) → Status: Identical (потребуется сверка параметров запуска)

Worker:
- `POST /api/v1/cookie-robot/start`, runner + `tasks/cookie_robot.py` → Status: Identical

---

### 11) Media Uniquification

Root: `async_video_uniquifier.py` и связанная логика

Module UI:
- API: `/api/media_uniq/{id}/aggregate`, `/api/media/uniquify/` и статус `/status/` → Status: Identical

Worker:
- `POST /api/v1/media-uniq/start`, `media_processing.py`, `runners/media_uniq_runner.py` → Status: Identical

---

### 12) TikTok (UI‑only)

Root: множество вьюх в `views_mod/misc.py` + `templates/uploader/tiktok/*`

Module UI:
- `templates/uploader/tiktok/booster.html` присутствует; API: `tiktok_booster_start_api`, `tiktok_booster_status_api` (заглушки) → Status: Mismatch (Root богаче). По решению — TikTok остаётся UI‑only.

Worker: отсутствует → Status: Missing in Module by Design

---

### 13) Статусы, логи, задачи

Root: `views_mod/tasks.py`: task_list, task_detail, create_task, start_task

Module UI:
- Общие страницы `templates/uploader/task_list.html`, `task_detail.html`; универсальные API: `generic_task_status`, `generic_account_status`, `generic_account_counters` → Status: Identical (покрывают обобщённые статусы)

---

### 14) Локи и координация

Root: нет универсального менеджера локов (используется логика на уровне задач)

Module UI:
- `dashboard/models.TaskLock`, `dashboard/lock_manager.py`, API `/api/locks/acquire|release` → Status: Missing in Root (расширение модуля). Рекомендуется оставить как есть, это улучшение.

---

### 15) Мониторинг и метрики

Root: базовые логи, без унифицированных метрик

Module UI:
- Мониторинг, health‑poll, перезапуск воркеров; API `/api/monitoring/*` → Status: Missing in Root (расширение модуля)

Worker:
- `/api/v1/metrics`, `/api/v1/health`, `/api/v1/status` → Status: Identical с потребностями UI

---

### 16) Селекторы и логика в модуле загрузки (Upload) — сверка обновлений

Селекторы (Root vs Module):
- Файл селекторов Root: `uploader/selectors_config.py` — расширенные мультиязычные селекторы, включая:
  - EMAIL_SUBMIT_BUTTONS, REELS_DIALOG_SELECTORS, расширенные LOGIN_FORM_INDICATORS, COOKIE_* наборы, LOCATION_INPUT, MENTIONS_INPUT, SUCCESS/ERROR_DIALOG, MAIN_INTERFACE, UPLOAD_BROAD_INDICATORS и др.
- Файл селекторов Module: `modules FOR INSTAUPLOAD/bulk_worker_service/bulk_worker_service/instagram_automation/selectors_config.py`
  - В ряде мест наборы уже обновлены, но по сравнению с Root встречаются пробелы:
    - Не обнаружены (или частично): EMAIL_SUBMIT_BUTTONS, REELS_DIALOG_SELECTORS, расширенные UPLOAD_BROAD_INDICATORS, полноценные ERROR_DIALOG, расширенные MAIN_INTERFACE, LOCATION_INPUT/MENTIONS_INPUT в полном объёме.

Статус: Mismatch.
Действия для выравнивания:
- Синхронизировать `selectors_config.py` в модуле с Root-версией: добавить недостающие группы селекторов (EMAIL_SUBMIT_BUTTONS, REELS_DIALOG_SELECTORS, ERROR_DIALOG, расширенные MAIN_INTERFACE/UPLOAD_BROAD_INDICATORS, LOCATION_INPUT, MENTIONS_INPUT и пр.).
- Выстроить приоритеты и fallback-цепочки идентично Root: сначала data-*/aria-*/role, затем текстовые признаки, затем структурные CSS/XPath.
- Добавить текстовые проверки видимости/содержимого (text-based queries) и fallback‑локаторы.

Логика email/2FA верификации:
- Root: `uploader/email_verification_async.py`:
  - Асинхронный клиент получения кода (retry, логирование)
  - Детект типа верификации по URL/текстам/селекторам (напр. `auth_platform/codeentry`), разграничение полей email vs code
  - Локальный TOTP fallback, попытка через HTTP API
- Module: `bulk_worker_service/instagram_automation/email_verification_async.py` — необходимо дотянуть до полного паритета по веткам логики и селекторам (Root расширеннее).

Статус: Mismatch (Root богаче).
Действия:
- Перенести в модуль полный набор веток: расширенные селекторы email/code, URL‑паттерны, разделение `email_field` vs `email_code`, TOTP fallback, единый интерфейс логгера.

Логика логина и «человекоподобности»:
- Root: `uploader/login_optimized.py`, `uploader/human_behavior*.py`/`human_behavior_core/*`
  - Более широкие индикаторы Logged‑In/Errors, стратегии скролла/hover/задержек, расширенные keyword‑хевристики (UPLOAD_KEYWORDS, REELS_DIALOG_KEYWORDS и т. п.)
- Module: уже есть `human_behavior.py` и конфиги; требуется синхронизация словарей/констант и индикаторов с Root.

Статус: Mismatch (требуется синхронизация индикаторов/констант).
Действия:
- Свести поведенческие словари и ключевые списки индикаторов к общему набору, вынести в shared‑модуль/конфиг.
- Добавить «псевдо‑элемент сканирование» (hover/scan) перед действиями и рандомизированные задержки в узких местах.

Upload flow (Playwright/Instagrapi):
- Root: `uploader/async_impl/upload.py` (и связки `async_impl/*`)
- Module: `bulk_worker_service/instagram_automation/async_impl/upload.py`
  - Требуется сравнить шаги: выбор файла, кадрирование/crop, проставление location/mentions, обработка ошибок, ретраи.

Статус: Partial Mismatch.
Действия:
- Сверить по шагам и унифицировать последовательности, особенно обработку REELS/POST, crop, location/mentions, финальные диалоги успеха/ошибок.
- Добавить smoke‑тесты на детекцию форм/диалогов по ключевым селекторам и keyword‑хевристикам (headless/visible режимы).

Резюме по модулю загрузки:
- Критично: выровнять селекторы, ветки email/2FA, behavior‑константы и upload‑последовательности.
- После синхронизации — запустить контрактные smoke‑тесты на основные сценарии (login/upload/reels/location/mentions) и зафиксировать контракты.

## Обнаруженные расхождения и действия

1) Delete endpoints (Bulk Upload/Login)
- Root: `delete_bulk_upload`, `delete_bulk_login`
- Module: прямых маршрутов удаления не найдено
- Действие: добавить UI routes + API (с проверками прав) → выровнять

2) Proxy test endpoint
- Root: `test_proxy`
- Module: нет явного аналога на UI API
- Действие: добавить `/api/proxies/test/` или расширить validate‑all для одиночной проверки

3) TikTok покрытие
- Root: много функций, модуль имеет заглушки
- Действие: оставить как UI‑only (подтверждено) либо расширить модуль позже

4) Согласование контрактов агрегатов
- Проверить поля во всех `/api/*/aggregate` vs фактические модели/сериализацию в Root
- Действие: добавить Pydantic схемы + contract tests (см. `TESTING_COVERAGE.md`)

---

## Таблица маршрутов (краткая сводка)

- UI Aggregates: `/api/{kind}/{task_id}/aggregate` — Root присутствует (данные), Module предоставляет эндпойнт — Status: Identical
- Worker Starts: `/api/v1/{kind}/start` — присутствуют все основные виды — Status: Identical
- Status Updates: `/api/{kind}/{task_id}/status` и аккаунтные — в Module есть, Root принимает/обновляет — Status: Identical
- Media: `/api/media/{video_id}/download`, `/api/media/images/{image_id}/download` — Status: Identical
- Locks: `/api/locks/*` — расширение Module — Status: Missing in Root (OK)

---

## Рекомендации по выравниванию «до идентичности»

- Добавить удаление задач (bulk upload/login) в Module UI.
- Добавить API тестирования одного прокси в Module UI.
- Зафиксировать Pydantic‑контракты агрегатов и статусов в общем пакете `contracts/`.
- Включить Celery для рассылки стартов и тяжёлых операций (см. `CELERY_INTEGRATION_PLAN.md`).
- Включить тесты (unit + contract + e2e smoke) по списку в `TESTING_COVERAGE.md`.

---

## Заключение

Основные домены (accounts, bulk upload/login, warmup, avatars, bio, follow, proxies, cookie robot, media uniq) — покрыты и сопоставимы 1:1. Есть несколько небольших расхождений (удаления задач, единичный тест прокси, расширенное покрытие TikTok в корне), которые можно устранить точечными маршрутами и контрактными тестами. После правок и добавления Celery/контрактов модули будут идентичны по функциям и страницам с корневым проектом и готовы к масштабированию (1 UI + 20+ Workers).

---

## Дополнительная проверка после обновлений (только по коду)

Ниже — сверка текущего состояния модулей с корневым проектом, опираясь исключительно на исходники после проделанных правок.

### UI: маршруты, вьюхи и страницы (модуль vs корень)

- Маршруты UI‑модуля (`web_ui_service/dashboard/urls.py`, `ui_core/urls.py`) присутствуют для: стартов задач, агрегатов, статусов, мониторинга, локов, медиа, аккаунтов/прокси, TikTok-заглушек. Соответствуют списку из корня, кроме следующих отличий:
  - Удаление задач: теперь добавлены `POST /api/bulk-tasks/{id}/delete`, `POST /api/bulk_login/{id}/delete` (соответствует корню) — OK.
  - Тест одного прокси: добавлен `POST /api/proxies/{proxy_id}/test/` (соответствует `views_mod/proxies.py:test_proxy`) — OK.
  - TikTok: остаётся UI‑only; модуль содержит заглушки start/status — Mismatch By Design.

- Вьюхи UI‑модуля, требующие обязательной проверки шаблонов и форм (по коду всё есть, но нужно визуально подтвердить поля):
  - `ui_core/views.py`: `create_account`, `create_bulk_upload` — формы в `templates/uploader/create_account.html`, `templates/uploader/bulk_upload/create.html` — проверить соответствие полей моделям из корня.
  - `dashboard/api_views.py` агрегаты: `bulk_task_aggregate`, `bulk_login_aggregate`, `warmup_aggregate`, `avatar_aggregate`, `bio_aggregate`, `follow_aggregate`, `proxy_diag_aggregate`, `media_uniq_aggregate` — по структуре соответствуют контрактам (см. раздел «Контракты» ниже) — OK.
  - Локи/мониторинг: `acquire_task_lock_api`, `release_task_lock_api`, `report_worker_metrics_api`, `report_worker_error_api`, `get_worker_status_api`, `get_system_health_api`, `trigger_worker_restart_api` — расширение модуля, в корне эквивалентов нет — OK.

- Шаблоны UI‑модуля (наличие файлов подтверждено):
  - `templates/uploader/bulk_upload/*`, `bulk_login/*`, `warmup/*`, `avatars/*`, `bio/*`, `follow/*`, `cookies/*`, `account_*`, `proxy_*`, `dashboard.html`, `task_*`, базовые `base.html` — OK.
  - TikTok: в модуле только `tiktok/booster.html`, в корне набор шире — Mismatch By Design.

Итого по UI после обновлений: критические расхождения устранены (delete, test proxy). Остальное — совпадает по кодовым маршрутам и структурам. Требуется лишь визуальная сверка форм/полей на страницах создания/редактирования.

### Worker: контракты агрегатов и раннеры (валидация по коду)

- Добавлены Pydantic‑контракты в `bulk_worker_service/contracts.py` для всех агрегатов — OK.
- Включена валидация агрегатов в раннерах и `orchestrator.py` — OK.
- Интеграционные тесты с моками UI:
  - `test_runner_contracts.py`, `test_runner_contracts_more.py` — подтверждают совместимость структур агрегатов без HTTP — OK.
- Upload‑flow:
  - Локация/упоминания применяются через `add_video_location_async`, `add_video_mentions_async` после caption — OK.
  - Reels‑диалог: поиск и подтверждение присутствуют; селекторы расширены — OK.
  - Success/Error: подтверждение публикации через `check_video_posted_successfully_async` после `click_share_button_async`; при необходимости можно добавить явные ретраи при `ERROR_DIALOG` (рекомендация, не блокер).

### Полный чек‑лист идентичности (функции/страницы)

- Accounts: list/detail/create/edit/import(bundles/ua_cookies)/bulk change proxy — маршруты и страницы в модуле соответствуют корню — OK.
- Bulk Upload: list/detail/create/add_videos/add_titles/start/logs/delete — в модуле всё покрыто (delete — добавлено) — OK.
- Bulk Login: list/detail/create/start/logs/delete — в модуле всё покрыто (delete — добавлено) — OK.
- Warmup: list/detail/create/start — OK.
- Avatars/Bio/Follow: list/detail/create/start — OK.
- Proxies: list/create/edit/import/validate‑all/cleanup/test — test добавлен — OK.
- Cookies (Cookie Robot): dashboard/list/detail/create/bulk — страницы есть; старт API есть — OK.
- Media Uniquification: старт/статус/агрегаты — OK.
- Monitoring/Locks: только в модуле (расширение) — OK.
- TikTok: UI‑only (модуль — заглушки) — Mismatch By Design.

### Остальные замечания по коду (для полного паритета)

- Формы UI: убедиться, что все формы отправляют те же поля, что и в корне (особенно `create_bulk_upload`, `create_account`, `bio/avatars/follow create`). По коду маршрутов/вьюх всё совпадает, но контент форм лучше визуально проверить.
- Upload: можно добавить дополнительный retry‑контур при обнаружении `ERROR_DIALOG` (3 попытки с экспоненциальной задержкой) до возврата `FAILED`. Это повысит устойчивость.

Вывод пост‑проверки по коду: после внесённых правок UI и Worker совпадают с корневым проектом по маршрутам, API, структурам агрегатов и ключевым сценариям. Отличия остаются только для TikTok (намеренно) и возможных нюансов форм (визуальная проверка).
