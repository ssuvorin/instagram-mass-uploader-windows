## Разделение интерфейса (Django/UI) и функциональной части (Playwright/аккаунты) на Python

Этот документ — пошаговая инструкция по переходу к архитектуре, где:
- Интерфейс (Django UI + API) развёрнут на отдельном Ubuntu-сервере
- Функциональная часть (воркеры Playwright, работа с аккаунтами, Dolphin Anty) — на отдельных Windows-серверах, масштабируемых горизонтально
- Общая БД (PostgreSQL) и очередь задач (Redis + django-rq/RQ)
- Cookies и «чертёж» профиля (blueprint) централизованно хранятся в БД
- Используются эфемерные профили Dolphin на время задачи

Документ учитывает и расширяет план в `docs/ephemeral-dolphin-profiles-and-postgres.md` (обязательно прочтите этот файл — он конкретизирует логику эфемерных профилей, хранение cookies и миграцию на PostgreSQL).

---

### 1) Целевая архитектура (Python/Django + RQ)

```
+---------------------+              +-------------------------------+
|   Ubuntu Server     |              |     Windows Workers (N)       |
|---------------------|              |-------------------------------|
| Django UI + API     |  REST→       | rqworker (django-rq)          |
| django-rq (enqueue) |  Redis (RQ)  | Playwright + Dolphin Anty     |
| Nginx/Gunicorn      | ← Updates    | Эфемерные профили             |
+---------+-----------+              +-------------------------------+
          |                                      ^
          v                                      |
   +-------------+    +------------------+       |
   | PostgreSQL  |    | Redis (queues)   | <-----+
   | accounts,   |    | rq: default/high |
   | cookies,    |    |                  |
   | tasks, logs |    +------------------+
   +-------------+
```

Ключевая идея: UI формирует задания (через API/панель) и ставит их в очереди Redis. Windows-воркеры забирают задания, запускают сценарии Playwright с учётом «человеческого поведения», эфемерного Dolphin-профиля и по окончании сохраняют cookies и статусы в PostgreSQL.

---

### 2) Зависимости и окружение

- Python 3.12+ (совместимо с вашим проектом)
- Django 5.x (уже используется)
- БД: PostgreSQL 14/15/16
- Очередь: Redis 7.x
- Очередь в Django: django-rq (обёртка над RQ), RQ, redis-py
- Дополнительно: dj-database-url (парсинг DATABASE_URL), psycopg[binary] (драйвер PG)

Добавьте в `requirements.txt` (на Ubuntu и Windows):
```
psycopg[binary]==3.1.19
redis==5.0.5
rq==1.16.2
django-rq==2.10.2
dj-database-url==2.2.0
python-dotenv==1.0.0
```

Playwright для Windows-воркеров (на стороне воркеров):
```
pip install playwright==1.45.0
python -m playwright install
```

---

### 3) Настройки Django (Ubuntu/UI)

Учитывая `docs/ephemeral-dolphin-profiles-and-postgres.md`, включите PostgreSQL и фичефлаги:

```python
# instagram_uploader/settings.py
import os
import dj_database_url

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=False)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

EPHEMERAL_PROFILES = os.environ.get('EPHEMERAL_PROFILES', '0').lower() in ('1','true','yes','on')
CONCURRENCY_LIMIT = int(os.environ.get('CONCURRENCY_LIMIT', '2'))

INSTALLED_APPS += [
    'django_rq',
]

RQ_QUEUES = {
    'default': {
        'URL': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0'),
        'DEFAULT_TIMEOUT': 3600,
    },
    'high': {
        'URL': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0'),
        'DEFAULT_TIMEOUT': 7200,
    },
}
```

В `urls.py` добавьте панель мониторинга django-rq (по желанию, за аутентификацией):
```python
# urls.py
from django.urls import include, path
urlpatterns = [
    # ...
    path('django-rq/', include('django_rq.urls')),
]
```

---

### 4) Миграция на PostgreSQL (короткая)

См. подробный план в `docs/ephemeral-dolphin-profiles-and-postgres.md` (раздел «Миграция на PostgreSQL»). Кратко:

1) Установите PostgreSQL, создайте БД и пользователя.
2) На UI-сервере установите зависимости, укажите `DATABASE_URL` в `.env`:
```
DATABASE_URL=postgresql://iguploader:STRONG_PASSWORD@DB_HOST:5432/iguploader
```
3) Примените миграции и перенесите данные из SQLite (если нужно):
```
python manage.py migrate --noinput
python manage.py dumpdata --natural-foreign --natural-primary --indent 2 > dump.json
python manage.py loaddata dump.json
```

---

### 5) Централизованные cookies и эфемерные профили Dolphin (обязательное)

Опираться на файл `docs/ephemeral-dolphin-profiles-and-postgres.md`:
- Храним cookies в `InstagramCookies` (OneToOne с аккаунтом), поля: `cookies_data JSON`, `last_updated`, `is_valid`
- «Чертёж» профиля (blueprint) храним в `InstagramDevice.device_settings` (JSON)
- Жизненный цикл задачи:
  1) Заблокировать аккаунт (поле/PG advisory lock)
  2) Собрать payload профиля из blueprint
  3) Создать профиль Dolphin (Remote API)
  4) Импортировать cookies в профиль (`PATCH /browser_profiles/{id}/cookies`)
  5) Запустить профиль (Local API) → подключиться Playwright по CDP
  6) Выполнить сценарий (логин/аплоад)
  7) Прочитать cookies через Dolphin Remote API (fallback — `page.context.cookies()`) и сохранить в БД
  8) Закрыть: Playwright close → `stop_profile` → `delete_profile?forceDelete=1`

Создайте сервисы (модули; код можно добавить по шагам):
- `uploader/services/cookies.py` — normalize/load/save cookies (см. скелет в приложении файла `docs/ephemeral-*.md`)
- `uploader/services/dolphin_profiles.py` — `build_profile_payload`, `create_ephemeral_profile`, `import_cookies`, `start_profile_and_connect`, `stop_and_delete` (с ретраями)
- `uploader/services/warmup.py` — прогрев при пустых cookies (Cookie Robot или через Playwright)

В `bot/src/instagram_uploader/dolphin_anty.py` добавьте методы: `get_cookies`, `update_cookies`, `delete_cookies`, `stop_and_delete` (см. примеры в приложенном документе).

В `uploader/tasks_playwright.py` и `uploader/bulk_tasks_playwright.py` замените постоянный `dolphin_profile_id` на эфемерный цикл из шагов выше.

---

### 6) Очереди задач (django-rq/RQ)

- UI/API (Ubuntu) ставит задачи в Redis:
```python
# пример продьюсера
import django_rq
from uploader.jobs import run_upload_job

queue = django_rq.get_queue('default')
job = queue.enqueue(run_upload_job, {'task_id': task_id}, job_timeout=3600)
```

- Воркеры (Windows) запускают `rqworker` с загрузкой Django-окружения:
```
# в каталоге проекта (где manage.py)
python manage.py rqworker high default
```

- Базовый каркас задания (чтобы изолировать Playwright-логику):
```python
# uploader/jobs.py
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from uploader.services.cookies import load_account_cookies, save_account_cookies, normalize_cookies
from uploader.services.dolphin_profiles import (
    build_profile_payload, create_ephemeral_profile, import_cookies,
    start_profile_and_connect, stop_and_delete
)
from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
from uploader.models import BulkUploadTask, InstagramAccount


def run_upload_job(params: dict) -> dict:
    """RQ-задача: выполнить загрузку для аккаунтов в BulkUploadTask."""
    task_id = params['task_id']
    # 1) получить список аккаунтов/видео из БД (используйте текущие модели)
    # 2) для каждого аккаунта выполнить: lock → create/import/start → Playwright сценарий → save cookies → stop+delete
    # 3) обновить статусы в БД, вернуть агрегированный результат
    return {"status": "ok", "task_id": task_id}
```

Примечание: можете завести отдельные типы задач: `login_job`, `upload_post_job`, `warmup_job` и т.п., используя очереди `high/default`.

---

### 7) Конфигурация .env

Ubuntu/UI (Django + Redis + Postgres):
```
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=ui.domain,localhost
DATABASE_URL=postgresql://iguploader:STRONG_PASSWORD@DB_HOST:5432/iguploader
REDIS_URL=redis://redis-host:6379/0
EPHEMERAL_PROFILES=1
CONCURRENCY_LIMIT=2
```

Windows/Worker:
```
DJANGO_SETTINGS_MODULE=instagram_uploader.settings
DATABASE_URL=postgresql://iguploader:STRONG_PASSWORD@UBUNTU_HOST:5432/iguploader
REDIS_URL=redis://UBUNTU_HOST:6379/0
DOLPHIN_API_TOKEN=...
# В Docker на Windows используйте host.docker.internal, без Docker — 127.0.0.1
DOLPHIN_API_HOST=http://127.0.0.1:3001
PLAYWRIGHT_QUIET=1
PLAYWRIGHT_DISABLE_COLORS=1
PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1
``` 

---

### 8) Развёртывание (Ubuntu/UI)

1) Установите Docker (опц.) и/или пакеты Postgres/Redis; либо используйте управляемые сервисы.
2) Установите зависимости Python и примените миграции:
```
pip install -r requirements.txt
python manage.py migrate --noinput
```
3) Запустите Django (Gunicorn + Nginx) или `python manage.py runserver` для тестов.
4) Проверьте `django-rq` панель: `/django-rq/`.

---

### 9) Развёртывание (Windows/Workers)

1) Установите Python 3.12, Git, Redis-клиент не обязателен.
2) Клонируйте репозиторий, создайте venv, установите зависимости:
```
py -3.12 -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\pip install playwright==1.45.0
venv\Scripts\python -m playwright install
```
3) Проверьте доступность Ubuntu/Redis/Postgres по сети. Заполните `.env` (см. выше).
4) Запуск воркера (в каталоге, где `manage.py`):
```
venv\Scripts\python manage.py rqworker high default
```
5) Поднятие как сервис (NSSM):
```
choco install nssm -y
nssm install ig-worker "C:\path\to\repo\venv\Scripts\python.exe" "C:\path\to\repo\manage.py" rqworker high default
nssm set ig-worker AppDirectory "C:\path\to\repo"
nssm set ig-worker AppEnvironmentExtra "DJANGO_SETTINGS_MODULE=instagram_uploader.settings" "DATABASE_URL=..." "REDIS_URL=..." "DOLPHIN_API_*=..."
nssm start ig-worker
```
Масштабирование: запустите несколько сервисов/инстансов на каждом Windows-сервере, либо поднимите дополнительные серверы с теми же настройками.

---

### 10) Имитация человеческого поведения и локаторы

Учитывайте «Always Applied Workspace Rules» и уже реализованные модули:
- Плавные задержки, hover/scan перед кликом (`uploader/async_impl/human.py`)
- Плавные перемещения курсора (Bezier/интерполяции)
- Надёжные локаторы (`data-*`, `aria-*`, `role`), карта запасных селекторов, текстовая верификация
- Ретраи с экспоненциальным бэкофом, логирование действий и селекторов

Эти принципы применяйте внутри задач воркеров и вспомогательных функций (Page Object Model/утилиты DOM).

---

### 11) Блокировки аккаунтов (многосерверность)

Минимально — добавить в `InstagramAccount` поля `locked_by`, `locked_until` и атомарно выставлять их при старте задачи, с TTL и продлением. Рекомендуемо — Postgres `select_for_update(skip_locked)` или advisory locks (см. код в `docs/ephemeral-*.md`).

---

### 12) Логи, мониторинг, устойчивость

- Логи воркеров отправляйте как минимум в файл + STDOUT; дублируйте ключевые события в БД (job_logs) при необходимости
- Метрики: количество задач, время выполнения, ошибки Dolphin/Playwright
- Ретраи: 3–5 попыток на сетевые вызовы (Dolphin), backoff 1.5–2x с jitter
- Аварийный уборщик: распознавание зомби-профилей и принудительное `delete_profile`

---

### 13) Проверочный E2E сценарий

1) В UI создайте тестовую задачу (bulk или одиночную) на один аккаунт
2) UI поставит задачу в очередь `default`
3) Воркеры Windows возьмут задачу, создадут эфемерный профиль, выполнят вход/аплоад
4) Cookies будут обновлены в `InstagramCookies`, профиль закрыт и удалён
5) UI отобразит статус `done` и логи

---

### 14) Чек-лист готовности

- [ ] `DATABASE_URL` настроен, миграции применены, данные перенесены
- [ ] `django-rq` подключён; UI умеет ставить задачи в Redis
- [ ] На Windows-воркерах работают `rqworker high default`, есть связь с Redis/Postgres
- [ ] Внедрены сервисы cookies/dolphin_profiles/warmup и эфемерный жизненный цикл
- [ ] В `dolphin_anty.py` добавлены методы cookies (Remote API)
- [ ] Задачи используют human-like поведение и устойчивые локаторы
- [ ] Логи/метрики собираются; ретраи и аварийный cleanup реализованы

---

### 15) Приложения и ссылки на исходный план

- Следуйте подробным пошаговым примерам кода из `docs/ephemeral-dolphin-profiles-and-postgres.md` — там даны скелеты функций для cookies, профилей, warmup и блокировок.
- Обновления в `uploader/views.py` (отображение cookies `last_updated` вместо несуществующего `created_at`), отключение legacy-кнопок создания постоянного профиля при `EPHEMERAL_PROFILES=1`.
- Проверки окружения — дополнить `check_env.py` проверкой `DATABASE_URL` и различий Docker/Windows для `DOLPHIN_API_HOST`.

---

### 16) Что сделать прямо сейчас (порядок)

1) Добавить зависимости (requirements) и обновить `settings.py` для `DATABASE_URL`, `django-rq`, фичефлагов
2) Поднять PostgreSQL и Redis на Ubuntu, применить миграции, перенести данные (при необходимости)
3) Включить сервисы: `cookies.py`, `dolphin_profiles.py`, `warmup.py`; дописать методы cookies в `dolphin_anty.py`
4) Перевести `tasks_playwright.py`/`bulk_tasks_playwright.py` на эфемерный жизненный цикл
5) Добавить `uploader/jobs.py` и enqueuing из UI; проверить `rqworker` на Windows
6) Прогнать E2E на одном аккаунте; затем масштабировать количество воркеров

После выполнения этих шагов ваш UI будет полностью отделён от функциональной части, а Playwright-воркеры на Windows смогут масштабироваться горизонтально, используя общую БД и очередь.

---

### 16) Пошаговый план (в первую очередь, детально)

Ниже — максимально конкретный план внедрения, разбитый на шаги с командами, файлами и критериями проверки. Выполняйте по порядку. Сначала локально/стейджинг, затем прод.

Шаг 0. Подготовка ветки и бэкапов
- Команды:
  ```bash
  git checkout -b feature/ui-workers-separation
  cp db.sqlite3 db.sqlite3.bak.$(date +%F_%H-%M-%S) || true
  tar czf media-backup.$(date +%F).tar.gz media/ || true
  ```
- Критерий: создана ветка, есть резервная копия SQLite и медиа (если применимо).

Шаг 1. Обновить зависимости (оба окружения: Ubuntu и Windows)
- Файл: `requirements.txt` — добавить строки:
  ```
  psycopg[binary]==3.1.19
  redis==5.0.5
  rq==1.16.2
  django-rq==2.10.2
  dj-database-url==2.2.0
  python-dotenv==1.0.0
  ```
- Команды (Ubuntu/UI):
  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  ```
- Команды (Windows/Workers):
  ```bat
  py -3.12 -m venv venv
  venv\Scripts\pip install -r requirements.txt
  venv\Scripts\pip install playwright==1.45.0
  venv\Scripts\python -m playwright install
  ```
- Критерий: зависимости установлены без ошибок.

Шаг 2. Настроить Django на PostgreSQL и очереди (Ubuntu/UI)
- Файл: `instagram_uploader/settings.py`
  - Добавить парсинг `DATABASE_URL` (dj-database-url) и фичефлаги `EPHEMERAL_PROFILES`, `CONCURRENCY_LIMIT` (пример уже в разделе 3 этого файла).
  - Добавить `django_rq` в `INSTALLED_APPS` и блок `RQ_QUEUES` (пример в разделе 3).
- Файл: `instagram_uploader/urls.py` — добавить:
  ```python
  path('django-rq/', include('django_rq.urls'))
  ```
- Файл: `.env` (на UI-сервере) — добавить/уточнить:
  ```
  DATABASE_URL=postgresql://iguploader:STRONG_PASSWORD@DB_HOST:5432/iguploader
  REDIS_URL=redis://redis-host:6379/0
  EPHEMERAL_PROFILES=1
  CONCURRENCY_LIMIT=2
  ```
- Команды:
  ```bash
  python manage.py check | cat
  ```
- Критерий: `manage.py check` проходит, страница `/django-rq/` открывается (после запуска сервера).

Шаг 3. Поднять PostgreSQL и Redis (Ubuntu/UI)
- Вариант Docker Compose (рекомендуется для быстрого старта):
  - Создать `infra/docker-compose.yml` (см. пример в разделе 8 базового гайда) и запустить:
    ```bash
    cd infra && docker compose up -d
    ```
- Вручную (если без Docker): установить Postgres и Redis пакетным менеджером и запустить сервисы.
- Критерий: UI-сервер видит Postgres и Redis по адресам из `.env`.

Шаг 4. Применить миграции и (при необходимости) перенести данные из SQLite
- Команды (на UI-сервере):
  ```bash
  python manage.py migrate --noinput | cat
  # Если переносите текущие данные из SQLite → PostgreSQL:
  python manage.py dumpdata --natural-foreign --natural-primary --indent 2 > dump.json
  DATABASE_URL=postgresql://... python manage.py loaddata dump.json | cat
  ```
- Критерий: таблицы созданы в PostgreSQL, UI открывается, базовые страницы работают.

Шаг 5. Создать сервисы cookies/dolphin_profiles/warmup (скелеты)
- Файлы (новые):
  - `uploader/services/cookies.py` (normalize/load/save) — см. готовый скелет в `docs/ephemeral-dolphin-profiles-and-postgres.md` (раздел 4) и базовый пример в этом файле.
  - `uploader/services/dolphin_profiles.py` (build_profile_payload/create/import/start/stop+delete с ретраями) — см. скелет в `docs/...` (раздел 5) и пример выше.
  - `uploader/services/warmup.py` (pick_random_warmup_urls и логика прогрева) — см. `docs/...` (раздел 2, метод run_cookie_robot и fallback через Playwright).
- Команды: создать файлы и вставить скелеты функций; убедиться, что импорты Django-моделей и клиентов Dolphin корректны.
- Критерий: модули импортируются без ошибок (`python -c "import uploader.services.cookies, uploader.services.dolphin_profiles"`).

Шаг 6. Добавить методы cookies в Dolphin клиент
- Файл: `bot/src/instagram_uploader/dolphin_anty.py`
  - Добавить методы: `get_cookies(profile_id)`, `update_cookies(profile_id, cookies_data)`, `delete_cookies(profile_id)`, `stop_and_delete(profile_id)` (см. точные сигнатуры и примеры в `docs/ephemeral-*.md`).
- Критерий: `from bot.src.instagram_uploader.dolphin_anty import DolphinAnty` проходит; вызовы методов не падают при заглушечных профилях (ручной smoke через `python -q`).

Шаг 7. Перевести одиночные и массовые таски на эфемерный жизненный цикл
- Файлы для правок:
  - `uploader/tasks_playwright.py`
  - `uploader/bulk_tasks_playwright.py`
  - `uploader/async_impl/dolphin.py` (если используете async)
- Изменения (суммарно):
  - Перед запуском: блокировка аккаунта → загрузка proxy/cookies/blueprint → `create_ephemeral_profile` → `import_cookies` (если есть) → `start_profile_and_connect` → Playwright сценарий.
  - После: `get_cookies` (Remote API) с fallback `page.context.cookies()` → `save_account_cookies` → `stop_and_delete` → снять блокировку.
- Критерий: локально прогоняется один полный цикл для тест-аккаунта без постоянного `dolphin_profile_id`, профиль удаляется после завершения.

Шаг 8. Включить очередь: постановка и выполнение задач
- Файл (новый): `uploader/jobs.py` — завести функцию RQ-задачи, например `run_upload_job(params: dict) -> dict`, которая внутри вызывает логику из Шага 7 для нужного аккаунта/таска.
- Продьюсинг задач из UI:
  - В `uploader/views.py` (или management command) добавить enqueuing через `django_rq.get_queue('default').enqueue(run_upload_job, {...})`.
  - Лимиты: использовать `CONCURRENCY_LIMIT` на уровень воркера и батч-планирование на уровне таски.
- Выполнение на Windows: запустить воркер(ы):
  ```bat
  venv\Scripts\python manage.py rqworker high default
  ```
- Критерий: задача видна в `/django-rq/`, берётся воркером, выполняется, статусы обновляются в БД.

Шаг 9. Прогрев при пустых cookies (обязательно для новых аккаунтов)
- В интеграционных местах (Шаг 7) добавить проверку: если `load_account_cookies(account)` пусто, запускать Cookie Robot (`run_cookie_robot`) или fallback через Playwright (см. примеры в `docs/ephemeral-*.md`).
- После прогрева — прочитать cookies из Remote API и сохранить в БД.
- Критерий: повторный запуск по тому же аккаунту имеет непустые cookies.

Шаг 10. Проверки окружения и UI-правки
- Файл: `check_env.py` — добавить проверку `DATABASE_URL`, сохранить логику Docker/Windows для `DOLPHIN_API_HOST`.
- Файл: `uploader/views.py` — в местах отображения cookies использовать `last_updated` вместо несуществующего `created_at`; скрыть/пометить legacy-кнопки создания постоянного профиля при `EPHEMERAL_PROFILES=1`.
- Критерий: UI корректно отображает cookies и статусы; `check_env.py` не выдаёт ошибок.

Шаг 11. E2E-тест и критерии приёмки
- Тест-кейс: один аккаунт, одна задача (логин или аплоад).
- Ожидания:
  - Профиль создаётся, импортируются cookies (если были), Playwright выполняет сценарий, cookies обновляются в `InstagramCookies`, профиль стоп+удаление.
  - Задача в Redis переходит в `finished`, UI отражает `done`/логи.
- Дополнительно: убедиться, что параллельно 2+ аккаунта выполняются корректно в пределах лимитов.

Шаг 12. Масштабирование воркеров
- Повторить Шаги 1, 6, 8 на дополнительных Windows-серверах.
- Запустить несколько инстансов `rqworker` на каждом сервере (или разные очереди приоритета `high/default`).
- Критерий: линейный рост пропускной способности; отсутствие гонок за аккаунты (блокировки работают).

---

### 17) Быстрый чек-лист «Готов к первому запуску»
- [ ] `requirements.txt` обновлён и установлен на Ubuntu/Windows
- [ ] `DATABASE_URL` и `REDIS_URL` настроены, `django-rq` подключён
- [ ] Созданы сервисы `cookies.py`, `dolphin_profiles.py`, `warmup.py`
- [ ] В `dolphin_anty.py` добавлены методы cookies и `stop_and_delete`
- [ ] Таски переведены на эфемерный жизненный цикл
- [ ] Enqueue из UI работает; `rqworker` на Windows берёт и выполняет
- [ ] E2E на одном аккаунте успешен, профиль удаляется, cookies сохраняются
