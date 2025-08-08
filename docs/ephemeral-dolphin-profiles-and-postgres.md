### Проектный план: Эфемерные профили Dolphin, централизованные cookies и миграция на PostgreSQL

Этот документ описывает, как из текущего проекта перейти на:
- Эфемерные профили Dolphin{anty} (создаём на время задачи → загружаем cookies → работаем → останавливаем → удаляем);
- Централизованное хранение cookies и параметров профиля в БД (привязка к аккаунту);
- Многосерверный запуск с единой базой аккаунтов;
- Миграцию с SQLite на PostgreSQL на сервере.

Док ниже привязан к текущему коду проекта: `uploader/models.py`, `bot/src/instagram_uploader/dolphin_anty.py`, `bot/src/instagram_uploader/browser_dolphin.py`, `uploader/bulk_tasks_playwright.py`, `uploader/tasks_playwright.py`, `uploader/views.py` и пр.

---

### Цели и ключевые принципы

- **Эфемерный профиль на задачу**: никакого постоянного `dolphin_profile_id` — при запуске задачи профиль создаётся с параметрами из БД, подгружаются cookies, после завершения профиль удаляется (stop → delete). Это снимает лимиты на количество профилей и упрощает горизонтальное масштабирование.
- **Куки в БД**: для каждого аккаунта сохраняем актуальные cookies в таблице `InstagramCookies` (уже есть). Не зависим от файловой системы.
- **Детерминированные отпечатки**: сохраняем «чертёж» профиля (fingerprint/blueprint) на уровне аккаунта, чтобы каждый новый эфемерный профиль создавался с одинаковыми ключевыми параметрами (UA, WebGL, timezone/geo, CPU/MEM и т.д.). Это снижает риск антифрода.
- **Многосерверность**: все сервера читают/пишут в одну БД, берут задания и аккаунты из неё, координируются через блокировки в БД.
- **Надёжность**: обязательный stop/delete профиля при выходе, даже при ошибках, с ретраями и бэкофом.

---

### Текущее состояние (релевантные места)

- **Модели** (`uploader/models.py`):
  - `InstagramAccount` — содержит `dolphin_profile_id` (постоянное). Для эфемерного подхода это поле станет опциональным/необязательным к использованию (сохранять не будем, либо будем хранить последние созданные id для отладки).
  - `InstagramCookies` — `OneToOne` с аккаунтом, `cookies_data JSON` + `last_updated` + `is_valid` — то, что нужно для централизованного хранения.
  - `InstagramDevice` — уже содержит JSON-поля (`device_settings`, `session_settings`) — удобно использовать для хранения «чертежа» браузера под Dolphin.
- **Dolphin API клиент** (`bot/src/instagram_uploader/dolphin_anty.py`):
  - Есть `create_profile`, `start_profile`, `stop_profile`, `delete_profile`.
  - В документации в `docs/Dolphin{anty} Remote API - Detailed Python Documentation.md` описаны `get_cookies`, `update_cookies`, `delete_cookies` — сейчас в классе не реализованы, но их легко добавить.
- **Подключение к профилю** (`bot/src/instagram_uploader/browser_dolphin.py`):
  - `create_profile_for_account` → `connect_to_profile` → Playwright connect over CDP (`ws://127.0.0.1:port/...` или `host.docker.internal` в Docker).
  - `close()` делает stop профиля, но не delete. Для эфемерности после stop нужен delete.
- **Cookies в файлы**: в `bot/src/instagram_uploader/auth_playwright.py` при удачном логине cookies сохраняются на диск. Нам нужно дублировать/перенести сохранение в БД (`InstagramCookies`).
- **DB**: сейчас SQLite (см. `instagram_uploader/settings.py`). В `windows_deployment.env.example` предусмотрен `DATABASE_URL` для PostgreSQL, но настройки ещё не переключались.

---

### Предлагаемая архитектура

- **Blueprint профиля** (персистентно в БД):
  - Где хранить: в `InstagramDevice.device_settings` (или создать отдельное поле/модель `BrowserProfileTemplate` — на ваше усмотрение, чтобы не ломать обратную совместимость можно начать с `device_settings`).
  - Что хранить: минимально необходимое для стабильной идентичности профиля:
    - browserVersion (диапазон), userAgent (строка), platform/os, screen, webrtc_mode, webgl_mode/webgl_info (vendor/renderer/webgl2Maximum), cpu_mode/value, mem_mode/value, fonts_mode/value, audio_mode, timezone, geolocation, locale, resolution, tags; при необходимости proxy policy.
  - Формат: JSON, например:
    ```json
    {
      "locale": "ru_RU",
      "browserVersion": "135",
      "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
      "webgl": {"vendor": "Intel Inc.", "renderer": "Intel Iris", "webgl2Maximum": {"maxTextureSize": 16384}},
      "webrtc_mode": "manual",
      "webgl_mode": "noise",
      "cpu": {"mode": "manual", "value": 4},
      "mem": {"mode": "manual", "value": 8},
      "fonts": {"mode": "manual", "value": ["Arial","Segoe UI","Verdana"]},
      "audio": {"mode": "noise"},
      "timezone": {"mode": "manual", "value": "Europe/Moscow"},
      "geolocation": {"mode": "manual", "latitude": 55.751244, "longitude": 37.618423},
      "screen": "1920x1080",
      "tags": ["instagram","bot_profile"]
    }
    ```

- **Cookies** (персистентно в БД):
  - Храним как список cookie-словари (как возвращает `page.context.cookies()` в Playwright). Важно привести `expires`/`expirationDate` к формату, который принимает Dolphin Remote API (`expirationDate` в секундах epoch). Если атрибут отсутствует — это session cookie.
  - Поля: `cookies_data JSON`, `last_updated`, `is_valid`. При неуспехе авторизации/чекпоинте — `is_valid=false`.

- **Важно: не путать источники данных (Private API vs Dolphin)**:
  - **Private API** (instagrapi/«как с телефона»): сессии и device settings хранить отдельно в `InstagramDevice.session_settings`. Эти данные не смешиваются с браузерными cookies.
  - **Dolphin/браузерные cookies**: хранить в `InstagramCookies`.
  - **Обновление cookies после задачи**: приоритетно читать cookies через Dolphin API (`GET /browser_profiles/{id}/cookies`) как источник истины профиля. Если недоступно/пусто — использовать fallback `page.context.cookies()` и нормализовать формат.

- **Жизненный цикл задачи (новый):**
  1) Взять аккаунт из БД, загрузить его proxy, cookies и blueprint устройства.
  2) Сформировать payload для `create_profile` на основе blueprint (не рандомизировать каждый раз заново, а переиспользовать сохранённые значения, можно с минимальным шумом).
  3) Создать профиль в Dolphin (`POST /browser_profiles`).
  4) Загрузить cookies в профиль до старта браузера:
     - Вариант A (предпочтительно): `PATCH /browser_profiles/{id}/cookies` (Remote API) — добавляет/перезаписывает cookies в профиле.
     - Вариант B: после подключения Playwright выполнить `context.add_cookies(cookies)` — но лучше иметь cookies на уровне профиля, чтобы они сохранились в профильном хранилище Dolphin.
  5) Запустить профиль через Local API (`GET {local}/browser_profiles/{id}/start?automation=1[&headless=1]`).
  6) Подключиться Playwright к CDP и выполнить сценарий (логин/аплоад и т.д.).
  7) Получить актуальные cookies через Dolphin API (`GET /browser_profiles/{id}/cookies`) и сохранить в `InstagramCookies` (при недоступности — fallback к `page.context.cookies()` с нормализацией). Отметить `is_valid=true/false` по результатам.
  8) Корректно закрыть соединение: Playwright `browser.close()` → `stop_profile` → `delete_profile?forceDelete=1`.
  9) Внештатные ситуации: при любой ошибке запускать аварийный cleanup (stop → delete с ретраями).

- **Блокировки и конкуренция** (многосерверный сценарий):
  - Для каждого аккаунта вводим краткосрочную блокировку на время выполнения задачи:
    - Простой вариант — в `InstagramAccount` добавить флаг/поле `locked_until` и `locked_by` (сервер/хост/процесс), выставлять атомарно через транзакцию. При старте задачи проверять, что аккаунт не занят; выставлять `locked_until=now()+TTL`; обновлять периодически; снимать в конце.
    - Улучшенный вариант для PostgreSQL — использовать `select_for_update(skip_locked)` на строке аккаунта в транзакции или `pg_try_advisory_lock` по `account_id`.
  - Это гарантирует, что два сервера не возьмут один и тот же аккаунт одновременно.

---

### Подводные камни и нюансы

- **Удаление профиля (403/права):** на Free плане требуется `forceDelete=1`. В клиенте уже предусмотрено. Удалять после stop.
- **Local API доступность:** проверять `DOLPHIN_API_HOST` и токен. На Windows в Docker используется `host.docker.internal`. Вне Docker — `127.0.0.1`.
- **WS endpoint:** `browser_dolphin.py` корректно строит `ws://{host}:{port}{wsEndpoint}`. Для Docker переключать host.
- **Куки формат:**
  - Dolphin Remote API ожидает `expirationDate` (float сек). Playwright отдаёт `expires` (int сек) — синхронизировать названия/типы.
  - Учитывать `sameSite` и `httpOnly`, домены `.instagram.com` и `www.instagram.com`.
- **Не путать источники:** cookies/сессии Private API ≠ браузерные cookies Dolphin. Хранить и обновлять их раздельно: API-сессии в `InstagramDevice.session_settings`, браузерные cookies — в `InstagramCookies`.
- **Fingerprint стабильность:** если каждый раз рандомизировать — высокий риск антифрода. Поэтому сохраняем blueprint и подставляем его в `create_profile` (вместо полного рандома). Допускать редкие/контролируемые изменения.
- **Падения/зомби-профили:** обязательны ретраи и финальный аварийный уборщик, который распознаёт подвисшие профили и добивает `stop`/`delete`.
- **Cookies из файлов:** сейчас часть кода пишет cookies в файл. Нужно будет дублировать их сохранение в `InstagramCookies` и в долгосрочной перспективе отказаться от файлов.
- **Совместимость с текущими view:** в `uploader/views.py` в некоторых местах ищется `created_at` у cookies, а в модели его нет (есть `last_updated`). При интеграции поправить вывод.

---

### План точечных изменений в кодовой базе (без выполнения сейчас)

- **Сервис профилей Dolphin** `uploader/services/dolphin_profiles.py`:
  - Функции: `build_profile_payload(account, device_blueprint)`, `create_ephemeral_profile(dolphin, payload)`, `import_cookies(dolphin, profile_id, cookies)`, `start_connect(page/browse...)`, `stop_and_delete(dolphin, profile_id)`.
  - Ретраи, бэкоф, подробный лог (консоль + файл).

- **Методы в клиенте Dolphin** (`bot/src/instagram_uploader/dolphin_anty.py`):
  - Добавить `get_cookies(profile_id)`, `update_cookies(profile_id, cookies_data)`, `delete_cookies(profile_id)` по документации из `docs/Dolphin{anty} Remote API - Detailed Python Documentation.md`.
  - В `close()`/cleanup цепочке гарантировать `delete_profile` после `stop_profile`.

- **Куки-сервис** `uploader/services/cookies.py`:
  - `load_account_cookies(account) -> List[dict]` из `InstagramCookies` с валидацией.
  - `save_account_cookies(account, cookies_list, is_valid=True)` — нормализация полей и сохранение.
  - В конце каждой задачи приоритетно вызывать `dolphin.get_cookies(profile_id)` и сохранять результат; если API не вернул cookies — использовать fallback `page.context.cookies()` с нормализацией к формату Remote API.

- **Интеграция в таски** (`uploader/tasks_playwright.py`, `uploader/bulk_tasks_playwright.py`):
  - Вместо постоянного `account.dolphin_profile_id` — вызывать сервис создания эфемерного профиля, загрузку cookies, запуск, работу, затем стоп+удаление, сохранение cookies.

- **Логика логина** (`bot/src/instagram_uploader/auth_playwright.py`):
  - После успешного входа (обнаружена кнопка «новый пост») — дополнительно вызывать `save_account_cookies()` для БД (сейчас сохраняется в файл).

- **Блокировки**:
  - Простой вариант: добавить в `InstagramAccount` поля `locked_by (CharField)`, `locked_until (DateTime)` и обёртки `try_lock(account_id)`/`unlock(account_id)` с TTL и продлением.
  - PostgreSQL вариант: транзакции с `select_for_update(skip_locked)` или advisory locks.

- **Конфигурация**:
  - `.env`: `DOLPHIN_API_TOKEN`, `DOLPHIN_API_HOST`, `DATABASE_URL` (для PostgreSQL), `CONCURRENCY_LIMIT`, `EPHEMERAL_PROFILES=1`.
  - `settings.py`: если есть `DATABASE_URL` — использовать Postgres, иначе SQLite (см. раздел миграции ниже).

- **Соблюдение правил (human-like, селекторы, устойчивость):**
  - Использовать «плавные» задержки, псевдо-сканирование, устойчивые локаторы (role/data-*), ретраи с экспоненциальным бэкофом, централизованный лог (уже реализовано частично).

---

### Миграция на PostgreSQL (пошагово)

- **1) Подготовка сервера PostgreSQL**
  - Установить PostgreSQL 15/16.
  - Создать роль и БД:
    ```bash
    sudo -u postgres psql -c "CREATE USER iguploader WITH PASSWORD 'STRONG_PASSWORD';"
    sudo -u postgres psql -c "CREATE DATABASE iguploader OWNER iguploader;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE iguploader TO iguploader;"
    ```

- **2) Зависимости Python (на сервере)**
  - Добавить драйвер PostgreSQL:
    - Рекомендуется `psycopg` (v3): `pip install psycopg[binary]`
    - Или `psycopg2-binary`
  - Зафиксировать в `requirements.txt` (после внедрения).

- **3) Конфигурация Django**
  - В `instagram_uploader/settings.py` добавить логику чтения `DATABASE_URL` (без изменения сейчас):
    - Пример формата: `postgresql://iguploader:STRONG_PASSWORD@127.0.0.1:5432/iguploader`
    - Если `DATABASE_URL` есть — использовать PostgreSQL, иначе оставаться на SQLite.

- **4) Перенос данных из SQLite**
  - На текущей машине (где SQLite):
    ```bash
    # Создать резервную копию
    python manage.py dumpdata --natural-foreign --natural-primary --indent 2 > dump.json
    ```
  - На сервере (с PostgreSQL в `DATABASE_URL`):
    ```bash
    # Применить миграции на чистой БД
    python manage.py migrate --noinput

    # Загрузить данные
    python manage.py loaddata dump.json
    ```
  - Проверить количество записей в ключевых таблицах (`InstagramAccount`, `InstagramCookies`, `Proxy`, `Bulk*`, `UploadTask`).

- **5) Валидация**
  - Запустить `python manage.py check` и короткий smoke-тест UI.
  - Прогнать `check_env.py` (настройки Dolphin API) и тест подключения к Local API.

- **6) Продакшн-настройки**
  - `.env` на сервере:
    ```
    SECRET_KEY=...
    DEBUG=False
    ALLOWED_HOSTS=...
    DATABASE_URL=postgresql://iguploader:STRONG_PASSWORD@DB_HOST:5432/iguploader
    DOLPHIN_API_TOKEN=...
    DOLPHIN_API_HOST=http://localhost:3001
    ```
  - Настроить бэкапы БД (pg_dump), мониторинг, авто-рестарт сервисов.

---

### Псевдокод рабочих потоков (с учётом надёжности)

- **Создание и использование эфемерного профиля**:
  ```python
  account = lock_and_fetch_account_for_task()
  cookies = load_account_cookies(account)
  device_bp = load_device_blueprint(account)  # InstagramDevice.device_settings

  dolphin = DolphinAnty(api_key=env.DOLPHIN_API_TOKEN, local_api_base=env.DOLPHIN_API_HOST+'/v1.0')

  profile_payload = build_profile_payload(account, device_bp)
  profile_id = dolphin.create_profile(...payload...)

  try:
      if cookies:
          dolphin.update_cookies(profile_id, normalize_cookies(cookies))

      success, automation = dolphin.start_profile(profile_id, headless=HEADLESS)
      page = playwright_connect(automation)

      run_instagram_flow(page, account)  # вход/аплоад

      new_cookies = dolphin.get_cookies(profile_id)
      if not new_cookies:
          new_cookies = page.context.cookies()
      save_account_cookies(account, normalize_cookies(new_cookies), is_valid=True)
  except Exception:
      mark_cookies_if_invalid(account)  # опционально
      raise
  finally:
      safe_playwright_close()
      dolphin.stop_profile(profile_id)
      dolphin.delete_profile(profile_id)
      unlock_account(account)
  ```

- **Ретраи и экспоненциальный бэкоф**: все сетевые операции к Dolphin (start/stop/delete, cookies) оборачивать 3–5 попытками с backoff 1.5–2x.

- **Антифрод/человеческое поведение**: перед кликами — короткая пауза `random.uniform(0.3, 1.2)`, «сканирование» элементов, устойчивые локаторы (role/data-*, `:has-text()`), избегать хрупких `nth-child`.

---

### Многосерверный запуск с единой БД

- **Координация**: таски и аккаунты в БД, сервера берут задания с использованием блокировок (см. выше). Возможна очередь на уровне `UploadTask`/`BulkUploadTask`.
- **Ограничение профилей/конкурентности**: через env `CONCURRENCY_LIMIT` и семафор на сервере.
- **Сетевые различия**: в Docker использовать `host.docker.internal` для WebSocket к Dolphin, вне Docker — `127.0.0.1`.

---

### Чек-лист внедрения

- [ ] Создать сервисы: `dolphin_profiles.py`, `cookies.py`.
- [ ] Добавить методы cookies в `DolphinAnty` клиент (Remote API `PATCH /browser_profiles/{id}/cookies`).
- [ ] Переключить таски на эфемерный жизненный цикл профиля.
- [ ] Сохранение cookies в `InstagramCookies` из Playwright после успешных действий/логина.
- [ ] Ввести блокировки аккаунтов (простая модель или Postgres advisory locks).
- [ ] Добавить в `.env` параметры `DATABASE_URL`, `DOLPHIN_API_*`, `EPHEMERAL_PROFILES`.
- [ ] Миграция данных в PostgreSQL и smoke-тест.

---

### Приложение: полезные эндпоинты Dolphin

- Remote API (по документации):
  - `POST /browser_profiles` — создать профиль.
  - `DELETE /browser_profiles/{id}?forceDelete=1` — удалить профиль.
  - `PATCH /browser_profiles/{id}/cookies` — загрузить/обновить cookies профиля.
- Local API:
  - `GET /browser_profiles/{id}/start?automation=1[&headless=1]`
  - `GET /browser_profiles/{id}/stop`
  - (Расширение) `POST /import/cookies/{id}/robot` — cookie-robot по списку URL (у вас уже используется в логах).

---

### Примечания по безопасности

- Не логировать содержимое cookies и пароли. Маскировать чувствительные поля.
- Рассмотреть шифрование чувствительных JSON в БД (KMS/ключ в ENV, field-level encryption), если требуется политика безопасности.

---

### Результат

После внедрения: каждая задача работает в собственном эфемерном профиле Dolphin, использует cookies из БД, обновляет их по завершении, корректно очищает за собой профили. БД — PostgreSQL, единая для всех серверов, что позволяет горизонтально масштабировать систему и управлять аккаунтами централизованно. 

---

### Пошаговый чеклист правок по файлам (последовательно)

Ниже — конкретные шаги и файлы, которые нужно править/создать. Выполняйте по порядку.

1) Базовая подготовка (флаг и зависимости)
- `requirements.txt`:
  - Добавить драйвер PostgreSQL: либо `psycopg[binary]` (предпочтительно), либо `psycopg2-binary`.
- `.env` / `windows_deployment.env.example`:
  - Добавить: `EPHEMERAL_PROFILES=1`, `CONCURRENCY_LIMIT=2` (пример), `DATABASE_URL=postgresql://user:pass@host:5432/dbname`.

2) Конфигурация БД и фичефлагов
- `instagram_uploader/settings.py`:
  - Научить читать `DATABASE_URL` (если задан — использовать PostgreSQL, иначе SQLite как сейчас).
  - Добавить чтение `EPHEMERAL_PROFILES` и `CONCURRENCY_LIMIT` из ENV.

3) Модель и блокировки аккаунтов
- `uploader/models.py`:
  - В `InstagramAccount` добавить поля: `locked_by = models.CharField(max_length=64, null=True, blank=True)`, `locked_until = models.DateTimeField(null=True, blank=True)`.
  - Использовать уже существующий `InstagramDevice.device_settings` как «blueprint» профиля Dolphin; убедиться, что формат соответствует разделу «Blueprint профиля».
- Миграция:
  - `python manage.py makemigrations uploader && python manage.py migrate` (позже повторить уже на PostgreSQL).

4) Сервис работы с cookies (единая точка)
- СОЗДАТЬ `uploader/services/cookies.py`:
  - `normalize_cookies(cookies_list) -> List[dict]`: привести к формату Dolphin Remote API (`expirationDate` в секундах, корректные поля домена/пути/secure/sameSite/httpOnly).
  - `load_account_cookies(account) -> Optional[List[dict]]`: прочитать `InstagramCookies` и вернуть список cookies.
  - `save_account_cookies(account, cookies_list, is_valid=True)`: сохранить в `InstagramCookies` (создать/обновить), проставить `last_updated`, `is_valid`.

5) Сервис эфемерных профилей Dolphin
- СОЗДАТЬ `uploader/services/dolphin_profiles.py`:
  - `build_profile_payload(account, device_blueprint) -> dict`: собрать payload для `create_profile` строго из blueprint (без лишней рандомизации).
  - `create_ephemeral_profile(dolphin, payload) -> profile_id`.
  - `import_cookies(dolphin, profile_id, cookies_list)`: вызвать `update_cookies` Remote API.
  - `start_profile_and_connect(dolphin, profile_id, headless) -> (browser, context, page, automation_data)`: запустить Local API → соединиться по CDP.
  - `stop_and_delete(dolphin, profile_id)`: гарантированно `stop` → `delete` с ретраями.
  - Все внешние вызовы обернуть ретраями с экспоненциальным бэкофом и подробным логированием.

6) Клиент Dolphin: методы cookies и удобные обёртки
- `bot/src/instagram_uploader/dolphin_anty.py`:
  - ДОБАВИТЬ методы:
    - `get_cookies(profile_id)`: `GET /browser_profiles/{id}/cookies`.
    - `update_cookies(profile_id, cookies_data)`: `PATCH /browser_profiles/{id}/cookies` с `Content-Type: application/json`.
    - `delete_cookies(profile_id)`: `DELETE /browser_profiles/{id}/cookies` (опционально, если понадобится чистка).
  - ДОБАВИТЬ вспомогательную обёртку `stop_and_delete(profile_id)`: последовательный вызов `stop_profile` → `delete_profile` с ретраями.
  - Убедиться, что `start_profile` корректно работает с токеном и обрабатывает ошибки, таймауты и код 401/404 — оставить лог как есть, при необходимости расширить.

7) Коннектор браузера Dolphin
- `bot/src/instagram_uploader/browser_dolphin.py`:
  - В `close()` после `stop_profile` ДОБАВИТЬ вызов `delete_profile(self.dolphin_profile_id)` (или использовать новую обёртку `stop_and_delete`).
  - В `get_browser(...)` при наличии `account_data` использовать путь «создать новый профиль» (эпемерный) по умолчанию; `profile_id` считать legacy-режимом.
  - Убедиться, что хост для WS `127.0.0.1` vs `host.docker.internal` выбирается как сейчас.

8) Логика логина (сохранение cookies в БД)
- `bot/src/instagram_uploader/auth_playwright.py`:
  - После успешного входа не только писать cookies в файл, но и ВЫЗЫВАТЬ сервис: `save_account_cookies(account, normalize_cookies(cookies))`.
  - Важно: не смешивать сессии Private API и браузерные cookies (ничего из `session_settings` сюда не писать).
  - Для лучшей консистентности основной поток сохранения cookies делаем на уровне тасков (см. шаг 9–10) через Dolphin API; в `auth_playwright.py` оставить как fallback.

9) Переход на эфемерность в одиночных тасках
- `uploader/tasks_playwright.py`:
  - В начале задачи: получить блокировку аккаунта (см. шаг 3), прочитать proxy, cookies (`load_account_cookies`), blueprint (`InstagramDevice.device_settings`).
  - Создать клиента `DolphinAnty`; собрать payload через `build_profile_payload`; `create_ephemeral_profile`.
  - Если cookies есть — `import_cookies` (Remote API).
  - `start_profile_and_connect` → Playwright page → выполнить бизнес-логику.
  - По окончании: ПРИОРИТЕТНО `dolphin.get_cookies(profile_id)`; при пустом ответе — fallback `page.context.cookies()`; `save_account_cookies(account, normalize_cookies(...))`.
  - В `finally`: `stop_and_delete` + снять блокировку.

10) Переход на эфемерность в массовых тасках
- `uploader/bulk_tasks_playwright.py`:
  - В функциях запуска браузера/аккаунтов (`run_dolphin_browser`, иные): заменить использование постоянного `dolphin_profile_id` на создание эфемерного профиля по схеме шага 9.
  - Обновить места, где читаются/пишутся cookies, на сервисные вызовы (как в шаге 9).

11) Асинхронная реализация (если используется)
- `uploader/async_impl/dolphin.py`:
  - В `cleanup_browser_session_async` добавить удаление профиля (`delete_profile`) после `stop_profile`.
  - Для асинхронных потоков при невозможности Remote API cookies — оставить fallback `page.context.cookies()` с нормализацией и сохранением в БД.

12) Аварийная уборка профилей
- `uploader/task_utils.py`:
  - В `handle_emergency_cleanup` после `stop_profile` ДОБАВИТЬ попытку `delete_profile` (если известен `profile_id`). Логировать результат.

13) Обновление представлений и UI
- `uploader/views.py`:
  - Страницы cookies: использовать `InstagramCookies.last_updated` (а не несуществующий `created_at`).
  - Вьюхи/кнопки «создать Dolphin профиль» пометить как legacy или скрыть при `EPHEMERAL_PROFILES=1`.
  - В местах, где фильтруются аккаунты «с профилем Dolphin», перейти на эпемерный режим (создавать профиль на лету в обработчике задачи, а не полагаться на поле в аккаунте).

14) Проверки окружения
- `check_env.py`:
  - Добавить проверку `DATABASE_URL` (если планируется PostgreSQL).
  - Проверить связку `DOLPHIN_API_HOST`/Docker (`host.docker.internal` vs `localhost`) — оставить текущую логику предупреждений.

15) Миграция на PostgreSQL (после успешных локальных тестов с SQLite)
- На машине-источнике:
  - `python manage.py dumpdata --natural-foreign --natural-primary --indent 2 > dump.json`
- На сервере (c `DATABASE_URL`):
  - `python manage.py migrate --noinput`
  - `python manage.py loaddata dump.json`
- Прогнать smoke-тесты (логин/аплоад на одном аккаунте), убедиться в обновлении `InstagramCookies`.

16) Производственные параметры и мониторинг
- `.env` на сервере:
  - `EPHEMERAL_PROFILES=1`, корректные `DOLPHIN_API_*`, `CONCURRENCY_LIMIT`, `DATABASE_URL`.
- Логи:
  - Убедиться, что в логах фиксируются: `profile_id` (создан/остановлен/удалён), ошибки Remote/Local API, количество cookies при сохранении.
- Бэкапы БД: настроить регулярный `pg_dump`.

17) Документация и отключение легаси-путей
- Обновить страницы/скрипты, где подразумевается наличие постоянного `dolphin_profile_id`, на новый эпемерный подход.
- Оставить флаг `EPHEMERAL_PROFILES` для быстрого отката при необходимости. 

---

### Полная структура БД (PostgreSQL) после изменений

Ниже представлена результирующая структура доменных таблиц приложения (без стандартных Django-таблиц вроде `auth_*`, `django_*`). Типы и ограничения подобраны под PostgreSQL, JSON-поля — `jsonb`. Имена таблиц соответствуют Django-умолчанию: `app_model`.

Примечание: значения по умолчанию для `created_at/updated_at` устанавливаются на уровне ORM (auto_now/auto_now_add), БД-дефолты умышленно не задаются.

```sql
-- 1) Прокси
CREATE TABLE IF NOT EXISTS public.uploader_proxy (
  id                bigserial PRIMARY KEY,
  host              varchar(39) NOT NULL,
  port              integer NOT NULL,
  username          varchar(200),
  password          varchar(200),
  proxy_type        varchar(10) NOT NULL DEFAULT 'HTTP',
  status            varchar(20) NOT NULL DEFAULT 'inactive',
  last_checked      timestamptz,
  assigned_account_id bigint, -- FK -> uploader_instagramaccount(id)
  is_active         boolean NOT NULL DEFAULT true,
  last_used         timestamptz,
  last_verified     timestamptz,
  notes             text NOT NULL DEFAULT '',
  country           varchar(50),
  city              varchar(100),
  CONSTRAINT uploader_proxy_unique_host_port_user_pass
    UNIQUE (host, port, username, password)
);
CREATE INDEX IF NOT EXISTS idx_uploader_proxy_assigned_account
  ON public.uploader_proxy (assigned_account_id);

-- 2) Аккаунты Instagram
CREATE TABLE IF NOT EXISTS public.uploader_instagramaccount (
  id                bigserial PRIMARY KEY,
  username          varchar(100) NOT NULL UNIQUE,
  password          varchar(100) NOT NULL,
  email_username    varchar(100),
  email_password    varchar(100),
  tfa_secret        varchar(100),
  proxy_id          bigint,       -- FK -> uploader_proxy(id) ON DELETE SET NULL
  current_proxy_id  bigint,       -- FK -> uploader_proxy(id) ON DELETE SET NULL
  dolphin_profile_id varchar(100), -- legacy, может не использоваться в эпемерном режиме
  status            varchar(30) NOT NULL DEFAULT 'ACTIVE',
  last_used         timestamptz,
  last_warmed       timestamptz,
  created_at        timestamptz NOT NULL,
  updated_at        timestamptz NOT NULL,
  notes             text NOT NULL DEFAULT '',
  phone_number      varchar(32),
  -- блокировки для многосерверности
  locked_by         varchar(64),
  locked_until      timestamptz
);
CREATE INDEX IF NOT EXISTS idx_uploader_instagramaccount_proxy
  ON public.uploader_instagramaccount (proxy_id);
CREATE INDEX IF NOT EXISTS idx_uploader_instagramaccount_current_proxy
  ON public.uploader_instagramaccount (current_proxy_id);
CREATE INDEX IF NOT EXISTS idx_uploader_instagramaccount_locked_until
  ON public.uploader_instagramaccount (locked_until);

-- FK связи proxy -> account (assigned_account)
ALTER TABLE public.uploader_proxy
  ADD CONSTRAINT uploader_proxy_assigned_account_fk
  FOREIGN KEY (assigned_account_id)
  REFERENCES public.uploader_instagramaccount(id)
  ON DELETE SET NULL;

-- 3) Устройство/профиль (blueprint и сессии для Private API)
CREATE TABLE IF NOT EXISTS public.uploader_instagramdevice (
  id                bigserial PRIMARY KEY,
  account_id        bigint NOT NULL UNIQUE,  -- OneToOne FK -> uploader_instagramaccount(id)
  device_settings   jsonb NOT NULL DEFAULT '{}'::jsonb, -- blueprint Dolphin
  user_agent        varchar(255) NOT NULL DEFAULT '',
  session_settings  jsonb,                   -- Private API session (instagrapi)
  session_file      varchar(255),
  last_login_at     timestamptz,
  last_avatar_change_at timestamptz,
  created_at        timestamptz NOT NULL,
  updated_at        timestamptz NOT NULL
);
ALTER TABLE public.uploader_instagramdevice
  ADD CONSTRAINT uploader_instagramdevice_account_fk
  FOREIGN KEY (account_id)
  REFERENCES public.uploader_instagramaccount(id)
  ON DELETE CASCADE;

-- 4) Браузерные cookies Dolphin (централизованно)
CREATE TABLE IF NOT EXISTS public.uploader_instagramcookies (
  id                bigserial PRIMARY KEY,
  account_id        bigint NOT NULL UNIQUE,  -- OneToOne FK -> uploader_instagramaccount(id)
  cookies_data      jsonb NOT NULL,
  last_updated      timestamptz NOT NULL,
  is_valid          boolean NOT NULL DEFAULT true
);
ALTER TABLE public.uploader_instagramcookies
  ADD CONSTRAINT uploader_instagramcookies_account_fk
  FOREIGN KEY (account_id)
  REFERENCES public.uploader_instagramaccount(id)
  ON DELETE CASCADE;

-- 5) Cookie Robot задачи (история/панель управления)
CREATE TABLE IF NOT EXISTS public.uploader_dolphincookierobottask (
  id                bigserial PRIMARY KEY,
  account_id        bigint NOT NULL,  -- FK -> uploader_instagramaccount(id)
  status            varchar(20) NOT NULL DEFAULT 'PENDING',
  urls              jsonb NOT NULL DEFAULT '[]'::jsonb,
  headless          boolean NOT NULL DEFAULT true,
  imageless         boolean NOT NULL DEFAULT false,
  log               text NOT NULL DEFAULT '',
  created_at        timestamptz NOT NULL,
  updated_at        timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_uploader_dcrt_account
  ON public.uploader_dolphincookierobottask (account_id);
ALTER TABLE public.uploader_dolphincookierobottask
  ADD CONSTRAINT uploader_dcrt_account_fk
  FOREIGN KEY (account_id)
  REFERENCES public.uploader_instagramaccount(id)
  ON DELETE CASCADE;

-- 6) Обычные задачи загрузки
CREATE TABLE IF NOT EXISTS public.uploader_uploadtask (
  id                bigserial PRIMARY KEY,
  account_id        bigint NOT NULL,  -- FK -> uploader_instagramaccount(id)
  status            varchar(20) NOT NULL DEFAULT 'PENDING',
  log               text NOT NULL DEFAULT '',
  created_at        timestamptz NOT NULL,
  updated_at        timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_uploader_uploadtask_account
  ON public.uploader_uploadtask (account_id);
ALTER TABLE public.uploader_uploadtask
  ADD CONSTRAINT uploader_uploadtask_account_fk
  FOREIGN KEY (account_id)
  REFERENCES public.uploader_instagramaccount(id)
  ON DELETE CASCADE;

-- 7) Файлы видео к задачам
CREATE TABLE IF NOT EXISTS public.uploader_videofile (
  id                bigserial PRIMARY KEY,
  task_id           bigint NOT NULL,  -- FK -> uploader_uploadtask(id)
  video_file        varchar(100) NOT NULL, -- путь/сторадж
  caption           text NOT NULL DEFAULT '',
  uploaded_at       timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_uploader_videofile_task
  ON public.uploader_videofile (task_id);
ALTER TABLE public.uploader_videofile
  ADD CONSTRAINT uploader_videofile_task_fk
  FOREIGN KEY (task_id)
  REFERENCES public.uploader_uploadtask(id)
  ON DELETE CASCADE;

-- 8) Пакетные загрузки (шапка)
CREATE TABLE IF NOT EXISTS public.uploader_bulkuploadtask (
  id                bigserial PRIMARY KEY,
  name              varchar(100) NOT NULL DEFAULT 'Bulk Upload',
  status            varchar(20) NOT NULL DEFAULT 'PENDING',
  created_at        timestamptz NOT NULL,
  updated_at        timestamptz NOT NULL,
  log               text NOT NULL DEFAULT '',
  upload_id         uuid NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_uploader_bulkuploadtask_upload_id
  ON public.uploader_bulkuploadtask (upload_id);

-- 9) Аккаунты в пакетной загрузке
CREATE TABLE IF NOT EXISTS public.uploader_bulkuploadaccount (
  id                bigserial PRIMARY KEY,
  bulk_task_id      bigint NOT NULL,  -- FK -> uploader_bulkuploadtask(id)
  account_id        bigint NOT NULL,  -- FK -> uploader_instagramaccount(id)
  proxy_id          bigint,           -- FK -> uploader_proxy(id) ON DELETE SET NULL
  status            varchar(30) NOT NULL DEFAULT 'PENDING',
  log               text NOT NULL DEFAULT '',
  started_at        timestamptz,
  completed_at      timestamptz,
  uploaded_success_count integer NOT NULL DEFAULT 0,
  uploaded_failed_count  integer NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_uploader_bua_bulk
  ON public.uploader_bulkuploadaccount (bulk_task_id);
CREATE INDEX IF NOT EXISTS idx_uploader_bua_account
  ON public.uploader_bulkuploadaccount (account_id);
CREATE INDEX IF NOT EXISTS idx_uploader_bua_proxy
  ON public.uploader_bulkuploadaccount (proxy_id);
ALTER TABLE public.uploader_bulkuploadaccount
  ADD CONSTRAINT uploader_bua_bulk_fk FOREIGN KEY (bulk_task_id)
  REFERENCES public.uploader_bulkuploadtask(id)
  ON DELETE CASCADE;
ALTER TABLE public.uploader_bulkuploadaccount
  ADD CONSTRAINT uploader_bua_account_fk FOREIGN KEY (account_id)
  REFERENCES public.uploader_instagramaccount(id)
  ON DELETE CASCADE;
ALTER TABLE public.uploader_bulkuploadaccount
  ADD CONSTRAINT uploader_bua_proxy_fk FOREIGN KEY (proxy_id)
  REFERENCES public.uploader_proxy(id)
  ON DELETE SET NULL;

-- 10) Видео в пакетной загрузке
CREATE TABLE IF NOT EXISTS public.uploader_bulkvideo (
  id                bigserial PRIMARY KEY,
  bulk_task_id      bigint NOT NULL,  -- FK -> uploader_bulkuploadtask(id)
  video_file        varchar(100) NOT NULL,
  uploaded_at       timestamptz NOT NULL,
  assigned_to_id    bigint,           -- FK -> uploader_bulkuploadaccount(id) ON DELETE SET NULL
  "order"          integer NOT NULL DEFAULT 0,
  location          varchar(200) NOT NULL DEFAULT '',
  mentions          text NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_uploader_bv_bulk
  ON public.uploader_bulkvideo (bulk_task_id);
CREATE INDEX IF NOT EXISTS idx_uploader_bv_assigned
  ON public.uploader_bulkvideo (assigned_to_id);
CREATE INDEX IF NOT EXISTS idx_uploader_bv_order
  ON public.uploader_bulkvideo ("order");
ALTER TABLE public.uploader_bulkvideo
  ADD CONSTRAINT uploader_bv_bulk_fk FOREIGN KEY (bulk_task_id)
  REFERENCES public.uploader_bulkuploadtask(id)
  ON DELETE CASCADE;
ALTER TABLE public.uploader_bulkvideo
  ADD CONSTRAINT uploader_bv_assigned_fk FOREIGN KEY (assigned_to_id)
  REFERENCES public.uploader_bulkuploadaccount(id)
  ON DELETE SET NULL;
```

Связи (кратко):
- `uploader_proxy.assigned_account_id` → `uploader_instagramaccount.id` (SET NULL)
- `uploader_instagramaccount.proxy_id/current_proxy_id` → `uploader_proxy.id` (SET NULL)
- `uploader_instagramdevice.account_id` → `uploader_instagramaccount.id` (CASCADE, unique)
- `uploader_instagramcookies.account_id` → `uploader_instagramaccount.id` (CASCADE, unique)
- `uploader_dolphincookierobottask.account_id` → `uploader_instagramaccount.id` (CASCADE)
- `uploader_uploadtask.account_id` → `uploader_instagramaccount.id` (CASCADE)
- `uploader_videofile.task_id` → `uploader_uploadtask.id` (CASCADE)
- `uploader_bulkuploadaccount.bulk_task_id` → `uploader_bulkuploadtask.id` (CASCADE)
- `uploader_bulkuploadaccount.account_id` → `uploader_instagramaccount.id` (CASCADE)
- `uploader_bulkuploadaccount.proxy_id` → `uploader_proxy.id` (SET NULL)
- `uploader_bulkvideo.bulk_task_id` → `uploader_bulkuploadtask.id` (CASCADE)
- `uploader_bulkvideo.assigned_to_id` → `uploader_bulkuploadaccount.id` (SET NULL)

Рекомендуемые дополнительные индексы при росте нагрузки:
- На `uploader_instagramcookies (last_updated)` для выборки свежих cookies.
- На `uploader_instagramaccount (status)` если часто фильтруется по статусу.
- На `uploader_proxy (status, is_active)` для быстрого распределения прокси.
- На `uploader_bulkuploadaccount (status)` для мониторинга выполнения массовых задач. 

---

### Подробный пошаговый чеклист внедрения (расширенный)

Ниже — детальные шаги, команды и скелеты функций. Следуйте по порядку. Сначала локально на ветке, затем на сервере.

0) Подготовка
- Создать ветку:
  ```bash
  git checkout -b feature/ephemeral-dolphin-postgres
  ```
- Резервная копия SQLite и статики:
  ```bash
  cp db.sqlite3 db.sqlite3.bak.$(date +%F_%H-%M-%S)
  tar czf media-backup.$(date +%F).tar.gz media/
  ```

1) Зависимости и ENV
- `requirements.txt` — добавить:
  ```
  psycopg[binary]==3.1.19  # или psycopg2-binary==2.9.9
  dj-database-url==2.2.0
  ```
  Установить:
  ```bash
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
- `.env` — добавить переменные:
  ```
  EPHEMERAL_PROFILES=1
  CONCURRENCY_LIMIT=2
  # DATABASE_URL=postgresql://iguploader:STRONG_PASSWORD@127.0.0.1:5432/iguploader
  ```

2) Настройка БД и фичефлагов в `instagram_uploader/settings.py`
- Вверху импортировать dj-database-url:
  ```python
  import dj_database_url
  ```
- Заменить блок DATABASES на автопарсер `DATABASE_URL` с fallback на SQLite:
  ```python
  DATABASE_URL = os.environ.get('DATABASE_URL')
  if DATABASE_URL:
      DATABASES = {
          'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=False)
      }
  else:
      DATABASE_PATH = os.environ.get('DATABASE_PATH', BASE_DIR / 'db.sqlite3')
      DATABASES = {
          'default': {
              'ENGINE': 'django.db.backends.sqlite3',
              'NAME': DATABASE_PATH,
          }
      }
  ```
- Прочитать флаги:
  ```python
  EPHEMERAL_PROFILES = os.environ.get('EPHEMERAL_PROFILES', '0') in ('1','true','yes','on')
  CONCURRENCY_LIMIT = int(os.environ.get('CONCURRENCY_LIMIT', '2'))
  ```

3) Блокировки аккаунтов в `uploader/models.py`
- В `InstagramAccount` добавить поля:
  ```python
  locked_by = models.CharField(max_length=64, null=True, blank=True)
  locked_until = models.DateTimeField(null=True, blank=True)
  ```
- Создать миграции:
  ```bash
  python manage.py makemigrations uploader
  python manage.py migrate
  ```

4) Сервис cookies — СОЗДАТЬ `uploader/services/cookies.py`
- Скелет функций:
  ```python
  from typing import List, Optional
  import time
  from django.utils import timezone
  from uploader.models import InstagramCookies

  SAME_SITE_MAP = {
      'Lax': 'lax',
      'Strict': 'strict',
      'None': 'no_restriction',
      None: 'lax',
  }

  def normalize_cookies(cookies_list: List[dict]) -> List[dict]:
      normalized = []
      for c in cookies_list or []:
          exp = c.get('expirationDate')
          if not exp:
              expires = c.get('expires')
              if isinstance(expires, (int, float)) and expires > 0:
                  exp = float(expires)
          same_site = c.get('sameSite')
          if same_site in ('Lax','Strict','None'):
              same_site = SAME_SITE_MAP.get(same_site)
          normalized.append({
              'name': c.get('name'),
              'value': c.get('value'),
              'domain': c.get('domain'),
              'path': c.get('path', '/'),
              'secure': bool(c.get('secure', False)),
              'httpOnly': bool(c.get('httpOnly', False)),
              'sameSite': same_site,
              'expirationDate': exp,
          })
      return normalized

  def load_account_cookies(account) -> Optional[List[dict]]:
      row = getattr(account, 'cookies', None)
      return row.cookies_data if row and row.cookies_data else None

  def save_account_cookies(account, cookies_list: List[dict], is_valid: bool = True) -> None:
      cookies_list = normalize_cookies(cookies_list or [])
      obj, _ = InstagramCookies.objects.get_or_create(account=account)
      obj.cookies_data = cookies_list
      obj.is_valid = is_valid
      obj.last_updated = timezone.now()
      obj.save(update_fields=['cookies_data','is_valid','last_updated'])
  ```

5) Сервис профилей — СОЗДАТЬ `uploader/services/dolphin_profiles.py`
- Скелет функций и ретрай:
  ```python
  import time, random
  from typing import Tuple, Optional
  from bot.src.instagram_uploader.dolphin_anty import DolphinAnty

  def _retry(fn, attempts=3, base_delay=1.0):
      for i in range(attempts):
          try:
              return fn()
          except Exception:
              if i == attempts-1:
                  raise
              time.sleep(base_delay * (2 ** i) * random.uniform(0.9,1.2))

  def build_profile_payload(account, device_bp: dict) -> dict:
      # Извлечь из device_bp: locale, user-agent, screen, webgl/cpu/mem/fonts/audio/tz/geo и т.д.
      # Вернуть словарь аргументов под существующий create_profile(...)
      return {
          'name': f"Instagram {account.username}",
          'tags': ['instagram','bot_profile'],
          'locale': (device_bp or {}).get('locale', 'ru_RU'),
          # Прочие поля пойдут в сам метод create_profile внутри DolphinAnty
      }

  def create_ephemeral_profile(dolphin: DolphinAnty, payload: dict) -> str:
      resp = _retry(lambda: dolphin.create_profile(
          name=payload['name'], proxy=payload['proxy'], tags=payload['tags'], locale=payload['locale']
      ))
      pid = resp.get('browserProfileId') or (resp.get('data') or {}).get('id')
      if not pid:
          raise RuntimeError('No profile id returned')
      return str(pid)

  def import_cookies(dolphin: DolphinAnty, profile_id: str, cookies_list):
      if not cookies_list:
          return
      _retry(lambda: dolphin.update_cookies(profile_id, cookies_list))

  def start_profile_and_connect(dolphin: DolphinAnty, profile_id: str, headless: bool):
      ok, automation = _retry(lambda: dolphin.start_profile(profile_id, headless=headless))
      if not ok or not automation:
          raise RuntimeError('Failed to start profile')
      # подключение Playwright выполняйте там, где сейчас — через browser_dolphin или напрямую
      return automation

  def stop_and_delete(dolphin: DolphinAnty, profile_id: str):
      try:
          _retry(lambda: dolphin.stop_profile(profile_id))
      finally:
          _retry(lambda: dolphin.delete_profile(profile_id))
  ```

6) Методы cookies в `bot/src/instagram_uploader/dolphin_anty.py`
- Добавить (упрощённые примеры):
  ```python
  def get_cookies(self, profile_id):
      return self._make_request('get', f"/browser_profiles/{profile_id}/cookies")

  def update_cookies(self, profile_id, cookies_data):
      headers = {"Content-Type": "application/json"}
      return self._make_request('patch', f"/browser_profiles/{profile_id}/cookies", data=cookies_data, headers=headers)

  def delete_cookies(self, profile_id):
      return self._make_request('delete', f"/browser_profiles/{profile_id}/cookies")

  def stop_and_delete(self, profile_id):
      try:
          self.stop_profile(profile_id)
      finally:
          self.delete_profile(profile_id)
  ```

7) Удаление профиля при закрытии — `bot/src/instagram_uploader/browser_dolphin.py`
- В `close()` после `stop_profile(...)` добавить `delete_profile(self.dolphin_profile_id)` (или вызвать `stop_and_delete`).

8) Логика логина — `bot/src/instagram_uploader/auth_playwright.py`
- После успешного входа дополнительно (как fallback) вызывать сервис сохранения cookies (при наличии `account` в контексте потока):
  ```python
  from uploader.services.cookies import save_account_cookies, normalize_cookies
  cookies = self.page.context.cookies()
  save_account_cookies(account, normalize_cookies(cookies), is_valid=True)
  ```
  Основной путь сохранения — через Dolphin API в таске (см. ниже), этот — резервный.

9) Одиночные таски — `uploader/tasks_playwright.py`
- В начале задачи:
  - Захватить блокировку аккаунта (см. п. 12 для варианта с select_for_update).
  - Прочитать proxy, cookies (`load_account_cookies`), blueprint (`account.device.device_settings`).
- Создать Dolphin клиент и профиль:
  ```python
  from uploader.services.cookies import load_account_cookies, save_account_cookies, normalize_cookies
  from uploader.services.dolphin_profiles import build_profile_payload, create_ephemeral_profile, import_cookies, start_profile_and_connect, stop_and_delete
  from bot.src.instagram_uploader.dolphin_anty import DolphinAnty

  dolphin = DolphinAnty(api_key=os.environ['DOLPHIN_API_TOKEN'], local_api_base=os.environ['DOLPHIN_API_HOST'].rstrip('/')+'/v1.0')

  payload = build_profile_payload(account, getattr(getattr(account, 'device', None), 'device_settings', {}) )
  payload['proxy'] = (account.current_proxy or account.proxy).to_dict() if (account.current_proxy or account.proxy) else None
  profile_id = create_ephemeral_profile(dolphin, payload)

  cookies = load_account_cookies(account)
  if cookies:
      import_cookies(dolphin, profile_id, normalize_cookies(cookies))

  ok, automation = dolphin.start_profile(profile_id, headless=False)
  # подключить Playwright к CDP как сейчас (browser_dolphin) и выполнить сценарий
  ```
- По завершении:
  ```python
  new_cookies = dolphin.get_cookies(profile_id)
  if not new_cookies:
      new_cookies = page.context.cookies()
  save_account_cookies(account, normalize_cookies(new_cookies), is_valid=True)
  stop_and_delete(dolphin, profile_id)
  ```

10) Массовые таски — `uploader/bulk_tasks_playwright.py`
- Аналогично п.9: заменить постоянный `dolphin_profile_id` на создание эфемерного, импорт cookies, старт, выполнение, чтение cookies через API, stop+delete, сохранение в БД.

11) Асинхронный вариант — `uploader/async_impl/dolphin.py`
- В `cleanup_browser_session_async` убедиться, что после `stop_profile` вызывается `delete_profile`.
- Сохранение cookies: попытаться `get_cookies` через Remote API; fallback — `page.context.cookies()`.

12) Блокировки аккаунтов (варианты)
- Простой (SQLite/PG): поля `locked_by`, `locked_until` + атомарные обновления в транзакции.
- PostgreSQL (рекомендуется):
  ```python
  from django.db import transaction
  from django.utils import timezone
  from datetime import timedelta

  def try_lock_account(account_id, holder: str, ttl_seconds=600):
      from uploader.models import InstagramAccount
      with transaction.atomic():
          qs = InstagramAccount.objects.select_for_update(skip_locked=True).filter(id=account_id)
          acc = qs.first()
          if not acc:
              return None
          now = timezone.now()
          if acc.locked_until and acc.locked_until > now:
              return None
          acc.locked_by = holder
          acc.locked_until = now + timedelta(seconds=ttl_seconds)
          acc.save(update_fields=['locked_by','locked_until'])
          return acc
  ```
- Регулярно продлевать TTL во время долгой задачи; в конце — сбрасывать `locked_by/locked_until`.

13) Представления — `uploader/views.py`
- В местах показа cookies использовать `last_updated` вместо несуществующего `created_at`.
- Кнопки «создать профиль Dolphin» пометить legacy/скрыть при `EPHEMERAL_PROFILES`.

14) Проверки окружения — `check_env.py`
- Добавить вывод и валидацию `DATABASE_URL` при наличии.
- Сохранить текущую логику для `DOLPHIN_API_HOST` (Docker/Windows различия).

15) Локальные тесты
- Миграции:
  ```bash
  python manage.py makemigrations
  python manage.py migrate
  ```
- Smoke:
  - Запустить одиночную задачу на тест-аккаунте.
  - Проверить: создаётся профиль → импортируются cookies → соединение Playwright → после завершения cookies в БД обновились → профиль остановлен и удалён.

16) Миграция на PostgreSQL
- Поднять БД, создать пользователя/базу (см. раздел схемы выше).
- На текущей машине:
  ```bash
  python manage.py dumpdata --natural-foreign --natural-primary --indent 2 > dump.json
  ```
- На сервере с `DATABASE_URL`:
  ```bash
  python manage.py migrate --noinput
  python manage.py loaddata dump.json
  ```
- Прогнать smoke на сервере.

17) Многосерверность
- Настроить единый `DATABASE_URL` для всех инстансов.
- Включить блокировки (вариант с `select_for_update(skip_locked)` предпочтителен).
- Ограничить параллелизм через `CONCURRENCY_LIMIT` и планировщик задач.

18) Наблюдаемость
- Логирование: в ключевых местах (create/start/WS/connect/stop/delete, чтение/запись cookies) писать `profile_id` и статусы.
- Метрики (по желанию): количество успешных/неудачных start/stop/delete, длительность задач, ошибки API.

19) Откат
- Флаг `EPHEMERAL_PROFILES=0` — вернёт поведение к постоянным профилям (если ещё используется), либо использовать временно старые вьюхи.
- При проблемах с PG — временно вернуть `DATABASE_URL` пустым (fallback на SQLite) только для локальной отладки.

20) Слияние и релиз
- PR, код-ревью, деплой на staging → прод.
- Мониторинг в первые дни: подчистка зомби-профилей, корректность обновления cookies, отсутствие гонок за аккаунты. 