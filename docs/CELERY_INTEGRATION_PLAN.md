## План интеграции Celery (UI как диспетчер задач)

Цели:
- Убрать блокирующие операции из UI (агрегаты большого объёма, подготовка медиа, массовые импорты, рассылка команд воркерам).
- Централизованный ретрай и дедупликация.

### Топология
- Брокер: Redis (или RabbitMQ).
- Celery app: в Django UI (`web_ui_service`), модуль `dashboard.tasks`.
- Очереди:
  - default — фоновые операции UI
  - dispatch — рассылка стартов задач воркерам
  - cleanup — очистка локов/временных ресурсов

### Шаги внедрения
1) Зависимости
```bash
pip install celery[redis] django-celery-beat django-celery-results
```

2) Конфигурация Django (`remote_ui/settings.py`)
```python
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_TIME_LIMIT = 1200
CELERY_TASK_SOFT_TIME_LIMIT = 900
```

3) Инициализация Celery (`web_ui_service/remote_ui/celery.py`)
```python
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "remote_ui.settings")
app = Celery("remote_ui")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

4) Точки задач (`dashboard/tasks.py`)
- `dispatch_task_to_workers(task_kind, task_id, options)` — расщепляет на батчи и вызывает воркеры (бывший `_dispatch_batches`).
- `cleanup_expired_locks()` — периодическая задача.
- `prepare_large_aggregate(task_id)` — сбор тяжёлых агрегатов (опционально с кэшем Redis).

5) Замена синхронных вызовов
- В `dashboard/views.py` при нажатии «Старт» — вместо прямого вызова `_dispatch_batches` → `dispatch_task_to_workers.delay(kind, task_id, options)`.

6) Планировщик
- Включить `django-celery-beat` для периодических задач: очистка локов, health‑poll, отчёты.

7) Запуск воркеров Celery
```bash
celery -A remote_ui.celery:app worker -l info -Q default,dispatch,cleanup -c 2
celery -A remote_ui.celery:app beat -l info
```

### Дополнительно: Очередь на стороне Worker (опционально)
- Для локальной буферизации входящих команд можно использовать `arq`/`rq`/Celery в самом воркере, но предпочтительнее оставить воркер stateless и обрабатывать вход по REST.

### Ретраи и идемпотентность
- Все задачи должны быть идемпотентными: использовать `TaskLock` и ключи дедупликации.
- Ретраи — через `autoretry_for`, `max_retries`, `retry_backoff=True`.

### Мониторинг
- Экспорт метрик Celery (flower/Prometheus), алёрты по росту очередей и времени выполнения.
