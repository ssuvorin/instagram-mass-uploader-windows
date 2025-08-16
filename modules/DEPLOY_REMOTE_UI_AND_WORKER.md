# Развёртывание: Web UI (Django) + Worker (FastAPI) с PostgreSQL

Этот документ описывает полный пошаговый процесс выделения модулей из репозитория, настройки отдельной базы в PostgreSQL и развёртывания `Web UI` и `Worker` на сервере.

## Что в результате
- **Отдельная БД PostgreSQL** для модулей
- **Web UI (Django)** на одном сервере (или том же), подключённый к БД
- **Worker (FastAPI)** на одном или нескольких серверах, общающийся с UI по HTTP

## Предварительные условия
- Доступ к серверу с PostgreSQL (`91.108.227.166:5432`), есть учётка (например, `sergey`)
- На сервере для UI/Worker установлен Python 3.12
- Открытые порты или прокси для UI (например, `:8000`) и Worker (например, `:8088`)
- Репозиторий размещён на сервере (скопируйте весь проект, поскольку UI использует приложение `uploader` из корня)

---

## 1) Подготовка PostgreSQL (создать отдельную БД и пользователя)

Подключитесь к PostgreSQL. Если есть пользователь `sergey`, можно так:

```bash
psql "postgresql://sergey@91.108.227.166:5432/postgres" -W
```

Далее выполните SQL для создания роли и базы (выберите свой сложный пароль):

```sql
-- Замените СЛОЖНЫЙ_ПАРОЛЬ на реальный
CREATE ROLE iguploader WITH LOGIN PASSWORD 'СЛОЖНЫЙ_ПАРОЛЬ';
CREATE DATABASE iguploader WITH OWNER iguploader ENCODING 'UTF8' TEMPLATE template0;
GRANT ALL PRIVILEGES ON DATABASE iguploader TO iguploader;

-- (опционально, для стабильной сессии)
ALTER ROLE iguploader SET client_encoding TO 'UTF8';
ALTER ROLE iguploader SET timezone TO 'UTC';
```

Проверка подключения:

```bash
PGPASSWORD='СЛОЖНЫЙ_ПАРОЛЬ' psql "postgresql://iguploader@91.108.227.166:5432/iguploader" -c 'select 1;'
```

Если вашей учётке не хватает прав на `CREATE ROLE/DATABASE`, выполните команды под суперпользователем (например, `postgres`).

---

## 2) Настройка и запуск Web UI (Django)

Директория модуля: `modules/web_ui_service`

1. Перейдите в корень репозитория и создайте `.env` (UI грузит переменные из текущей рабочей директории благодаря `load_dotenv()`):

```bash
cd /path/to/playwright_instagram_uploader
cat > .env << 'EOF'
SECRET_KEY=заменить
DEBUG=False
ALLOWED_HOSTS=ui.your-domain.com,localhost
DATABASE_URL=postgresql://iguploader:СЛОЖНЫЙ_ПАРОЛЬ@91.108.227.166:5432/iguploader

# Токен для запросов от воркера к UI (pull-режим)
WORKER_API_TOKEN=REPLACE_ME

# URL воркера (или пул через запятую)
WORKER_BASE_URL=http://worker-host:8088
# WORKER_POOL=http://w1:8088,http://w2:8088

# Настройки диспетчера (опционально)
DISPATCH_BATCH_SIZE=5
DISPATCH_CONCURRENCY=2
EOF
```

2. Установите зависимости и выполните миграции:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r modules/web_ui_service/requirements.txt
python modules/web_ui_service/manage.py migrate
python modules/web_ui_service/manage.py collectstatic --noinput
```

3. Создайте суперпользователя (для входа в админку):

```bash
python modules/web_ui_service/manage.py createsuperuser
```

4. Запуск сервера:

- Временный (dev):
```bash
python modules/web_ui_service/manage.py runserver 0.0.0.0:8000
```

- Прод (рекомендуется, через gunicorn):
```bash
gunicorn remote_ui.wsgi:application --bind 0.0.0.0:8000
```

Примечания:
- В `INSTALLED_APPS` подключено приложение `uploader` из корня репозитория. Поэтому **копируйте на сервер весь репозиторий**, не только подмодуль.
- UI использует `dj-database-url` и `psycopg2-binary` для подключения к Postgres по `DATABASE_URL`.
- Для прод‑режима настройте reverse‑proxy (nginx) на порт 8000, пропишите `ALLOWED_HOSTS`.

---

## 3) Настройка и запуск Worker (FastAPI)

Директория модуля: `modules/bulk_worker_service`

1. Создайте/дополните `.env` (в корне репозитория):

```bash
cat >> .env << 'EOF'
# Базовый URL UI (dashboard API смонтированы на корне '/')
UI_API_BASE=http://ui-host:8000
# Должен совпадать с WORKER_API_TOKEN, указанным в UI
UI_API_TOKEN=REPLACE_ME

# Метод загрузки по умолчанию: playwright | instagrapi
UPLOAD_METHOD=playwright

# Параметры параллельности
CONCURRENCY_LIMIT=2
BATCH_SIZE=2
HEADLESS=1
EOF
```

2. Установка зависимостей и браузеров Playwright:

```bash
source venv/bin/activate || (python3 -m venv venv && source venv/bin/activate)
pip install -r modules/bulk_worker_service/requirements.txt
python -m playwright install
```

3. Запуск воркера:

```bash
uvicorn bulk_worker_service.app:app --host 0.0.0.0 --port 8088 --workers 1
```

Проверка здоровья воркера:
```bash
curl http://worker-host:8088/api/v1/health
# {"ok": true}
```

---

## 4) Проверка интеграции UI ↔ Worker

1. Проверьте UI в браузере: `http://ui-host:8000/admin` (войдите суперпользователем)
2. В UI создайте задачу (bulk upload / warmup и т.п.)
3. Нажмите «Старт» в UI — запрос уйдёт на `WORKER_BASE_URL`, воркер в pull‑режиме вызовет агрегат у UI и начнёт работу
4. В реальном времени статусы/логи обновляются на UI через API

---

## 5) Частые проблемы и решения

- 401/403 с воркера на UI → проверьте `UI_API_TOKEN` и `WORKER_API_TOKEN` (должны совпадать)
- `ALLOWED_HOSTS` → добавьте домен/хост UI
- Миграции падают → проверьте доступ к БД, роль/права, `DATABASE_URL`
- Порты/Firewall → откройте 8000 (UI) и 8088 (Worker), либо настройте reverse‑proxy
- Playwright ошибки → выполните `python -m playwright install` на хосте воркера

---

## 6) (Опционально) systemd юниты для прод

UI (`/etc/systemd/system/ig-ui.service`):
```ini
[Unit]
Description=Instagram Uploader UI (Django via gunicorn)
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/playwright_instagram_uploader
Environment=DJANGO_SETTINGS_MODULE=remote_ui.settings
EnvironmentFile=/path/to/playwright_instagram_uploader/.env
ExecStart=/path/to/playwright_instagram_uploader/venv/bin/gunicorn remote_ui.wsgi:application --bind 0.0.0.0:8000
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

Worker (`/etc/systemd/system/ig-worker.service`):
```ini
[Unit]
Description=Instagram Uploader Worker (FastAPI via uvicorn)
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/playwright_instagram_uploader
EnvironmentFile=/path/to/playwright_instagram_uploader/.env
ExecStart=/path/to/playwright_instagram_uploader/venv/bin/uvicorn bulk_worker_service.app:app --host 0.0.0.0 --port 8088 --workers 1
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

Активация:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ig-ui.service
sudo systemctl enable --now ig-worker.service
```

---

## 7) Быстрый чек‑лист

- [ ] Создана роль/БД в Postgres (`iguploader`)
- [ ] Заполнен `.env` в корне репозитория (`DATABASE_URL`, `WORKER_API_TOKEN`, `WORKER_BASE_URL`, `UI_API_BASE`, `UI_API_TOKEN`)
- [ ] Выполнены `migrate` и `collectstatic` для UI
- [ ] UI запущен (gunicorn) и доступен через домен/прокси
- [ ] Worker запущен (uvicorn) и отдаёт `/api/v1/health`
- [ ] В UI стартуют задачи, статусы/логи отображаются корректно 