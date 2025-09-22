## Полный аудит функций и классов (UI + Worker)

Дата: 2025-09-18
Назначение: Перечень по каждому файлу/модулю с целью актуализации под текущий Django.

Формат:
- Подпункты по файлам. Для каждой функции/класса — краткая роль и чек соответствия (заполнить в процессе ревью).
- Статусы: OK / Needs Review / Deprecated / Missing in Django.

---

### Web UI Service (`modules FOR INSTAUPLOAD/web_ui_service`)

#### ui_core/views.py
- dashboard(request) — [Status: Needs Review] — Главная панель
- account_list(request) — [Status: Needs Review]
- account_detail(request, account_id) — [Status: Needs Review]
- create_account(request) — [Status: Needs Review]
- bulk_upload_list(request) — [Status: Needs Review]
- bulk_upload_detail(request, task_id) — [Status: Needs Review]
- create_bulk_upload(request) — [Status: Needs Review]
- start_bulk_upload_via_worker(request, task_id) — [Status: Needs Review]
- task_status_api(request, task_id) — [Status: Needs Review]
- health_check(request) — [Status: Needs Review]

#### ui_core/apps.py
- class UiCoreConfig(AppConfig) — [Status: OK]

#### dashboard/views.py
- _worker_headers() — [Status: OK]
- _worker_url(base, path) — [Status: OK]
- _pick_workers() -> list[str] — [Status: Needs Review]
- _dispatch_batches(start_endpoint, task_id) — [Status: Needs Review]
- _acquire_lock(kind, task_id) — [Status: OK]
- start_bulk_upload_via_worker(request, task_id) — [Status: Needs Review]
- start_bulk_login_via_worker(request, task_id) — [Status: Needs Review]
- start_warmup_via_worker(request, task_id) — [Status: Needs Review]
- start_avatar_via_worker(request, task_id) — [Status: Needs Review]
- start_bio_via_worker(request, task_id) — [Status: Needs Review]
- start_follow_via_worker(request, task_id) — [Status: Needs Review]
- start_proxy_diag_via_worker(request, task_id) — [Status: Needs Review]
- start_media_uniq_via_worker(request, task_id) — [Status: Needs Review]
- workers_list(request) — [Status: Needs Review]
- health_poll(request) — [Status: OK]

#### dashboard/monitoring_views.py
- _worker_headers() — [Status: OK]
- _extract_server_info(base_url) — [Status: Needs Review]
- monitoring_dashboard(request) — [Status: Needs Review]
- worker_details(request, worker_id) — [Status: Needs Review]
- system_metrics_api(request) — [Status: OK]
- restart_worker(request, worker_id) — [Status: Needs Review]
- error_logs_view(request) — [Status: Needs Review]
- performance_metrics(request) — [Status: Needs Review]
- enhanced_health_poll(request) — [Status: OK]

#### dashboard/models.py
- class WorkerNode(models.Model) — [Status: OK] — модель воркера
- class TaskLock(models.Model) — [Status: OK] — TTL-локи задач

#### dashboard/api_views.py
- _ip_allowed(request) — [Status: OK]
- _auth_ok(request) — [Status: OK]
- _forbidden() — [Status: OK]
- bulk_task_aggregate(request, task_id) — [Status: Needs Review]
- media_download(request, video_id) — [Status: Needs Review]
- avatar_media_download(request, image_id) — [Status: Needs Review]
- worker_register(request) — [Status: OK]
- worker_heartbeat(request) — [Status: OK]
- bulk_task_status(request, task_id) — [Status: Needs Review]
- bulk_account_status(request, account_task_id) — [Status: Needs Review]
- bulk_account_counters(request, account_task_id) — [Status: Needs Review]
- bulk_login_aggregate(request, task_id) — [Status: Needs Review]
- warmup_aggregate(request, task_id) — [Status: Needs Review]
- avatar_aggregate(request, task_id) — [Status: Needs Review]
- bio_aggregate(request, task_id) — [Status: Needs Review]
- follow_aggregate(request, task_id) — [Status: Needs Review]
- proxy_diag_aggregate(request, task_id) — [Status: Needs Review]
- media_uniq_aggregate(request, task_id) — [Status: Needs Review]
- tiktok_booster_start_api(request) — [Status: UI-only]
- tiktok_booster_status_api(request) — [Status: UI-only]
- _get_task_model(kind) — [Status: OK]
- _get_account_model(kind) — [Status: OK]
- generic_task_status(request, kind, task_id) — [Status: Needs Review]
- generic_account_status(request, kind, account_task_id) — [Status: Needs Review]
- generic_account_counters(request, kind, account_task_id) — [Status: Needs Review]
- create_follow_category_api(request) — [Status: Needs Review]
- add_follow_targets_api(request, category_id) — [Status: Needs Review]
- report_worker_metrics_api(request) — [Status: OK]
- report_worker_error_api(request) — [Status: OK]
- get_worker_status_api(request, worker_id) — [Status: Needs Review]
- get_system_health_api(request) — [Status: OK]
- trigger_worker_restart_api(request, worker_id) — [Status: Needs Review]
- acquire_task_lock_api(request) — [Status: OK]
- release_task_lock_api(request) — [Status: OK]
- media_uniquify_start_api(request) — [Status: Needs Review]
- media_uniquify_status_api(request, task_id) — [Status: Needs Review]
- cookie_robot_start_api(request) — [Status: Needs Review]

---

### Bulk Worker Service (`modules FOR INSTAUPLOAD/bulk_worker_service`)

Ключевые: app.py (эндпойнты), orchestrator_v2.py, services.py, ui_client.py, runners/*, instagram_automation/*.

- tasks/cookie_robot.py: run_cookie_robot(...) — [Status: Needs Review]
- tasks/common.py: build_proxy_payload(...), init_browser_for_account(...), perform_login(...) — [Status: Needs Review]
- services.py:
  - class InMemoryJobRepository — [Status: OK]
  - class SimpleMetricsCollector — [Status: OK]
  - class DefaultUiClientFactory — [Status: OK]
  - class JobManager — [Status: Needs Review]
- runners/*: get_runner(...) и классы раннеров — [Status: Needs Review] по каждому типу
- interfaces.py: интерфейсы IJobManager/ITaskRunner/... — [Status: OK]
- instagrapi_runner.py: _apply_defaults(...), _map_account_payload(...) — [Status: Needs Review]
- instagram_automation/*: крупные функции логина, аплоада, human behavior, utils — [Status: Needs Review]
- media_processing.py: стратегии уникализации — [Status: Needs Review]
- rate_limiter.py: RateLimitMiddleware, декораторы — [Status: OK]
- production_fixes.py: фабрики ресурсов и health — [Status: OK]
- proxy_diagnostics.py: тесты прокси и фиксы — [Status: Needs Review]
- runner.py: пути к скриптам — [Status: Needs Review]

(Примечание: файл `app.py` содержит все REST эндпойнты; рекомендуется отдельная таблица в TESTING.md)

---

## План детальной актуализации
- Пройтись по каждому пункту со статусом «Needs Review» и проверить соответствие текущим моделям и бизнес-логике из `uploader`.
- Обновить агрегаты и маппинг полей при расхождениях; добавить контрактные тесты.

---

## Следующие шаги
- Составить автоматизированные тесты контрактов UI↔Worker (см. TESTING_COVERAGE.md).
- Внедрить брокер заданий (Celery) для UI-сайд долгих операций и ретраев.
