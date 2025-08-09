### Консолидация констант и конфигурации: аудит и план

Цель: централизовать все константы и настройки (URLs, селекторы, таймауты/задержки, режимы headless, пути, retry, внешние сервисы) в одном месте, сохранить текущую логику (поведение не меняется), убрать дубли и хардкоженные значения.

Принципы: один источник правды, чистые импорты из `config.*`, читаемость, SOLID/DRY/CLEAN.

---

### Новая структура конфигурации (единое место)
Создаём пакет `config/` в корне проекта:
- `config/__init__.py` — единая инициализация (например, `load_dotenv()` один раз).
- `config/env.py` — чтение переменных окружения с типами и дефолтами.
- `config/urls.py` — все URL/эндпоинты (Instagram, внешние сервисы, UI, warmup).
- `config/timeouts.py` — все таймауты (навигация, сокеты и т.д.).
- `config/delays.py` — «человеческие» задержки и сценарные паузы.
- `config/retry.py` — общая политика ретраев (попытки, базовые задержки, backoff).
- `config/browser.py` — headless/visible резолвер, Playwright ENV.
- `config/paths.py` — пути и директории (media, videos, временные файлы и т.д.).
- `config/selectors.py` — централизованные селекторы Playwright (CSS/XPath/role).

Замечание: существующие `uploader/selectors_config.py`, `uploader/constants.py` на первом этапе остаются, но постепенно переводятся на импорт из `config/selectors.py` (и далее помечаются deprecated).

---

### Итерация 1 (выполнено)
- Добавлены: `config/env.py`, `config/urls.py`, базовые замены URL.
- Вынесен `DOLPHIN_LOCAL_API` и заменён по коду.
- Убраны прямые переходы на `create/select` — навигация только через UI.

---

### Итерация 2 (таймауты + headless/env) — выполнено аккуратно

Добавлено
- `config/timeouts.py`:
  - `NAV_DEFAULT_MS=30000`, `NAV_SHORT_MS=15000`, `NAV_LONG_MS=60000`, `NET_IDLE_MS=15000`, `DOC_READY_MS=10000`, `SOCKET_DEFAULT_S=5`.
- `config/browser.py`:
  - `apply_playwright_env()` — централизует `PLAYWRIGHT_*` и `DEBUG` с прежними значениями.
  - `resolve_headless(args_visible: bool|None)` — приоритет как раньше: `--visible` → `HEADLESS=0` → `VISIBLE=1` → по умолчанию headless.

Замены (без изменения логики)
- `uploader/bulk_tasks_playwright.py`:
  - `page.goto(..., timeout=60000)` → `timeout=NAV_LONG_MS`.
  - `wait_for_load_state("networkidle", timeout=15000)` → `timeout=NET_IDLE_MS`.
  - `wait_for_function(..., timeout=10000)` → `timeout=DOC_READY_MS`.
  - Cleanup `goto(..., timeout=15000)` → `timeout=NAV_SHORT_MS`.
- `uploader/async_impl/services.py`:
  - Async cleanup `goto(..., timeout=30000)` → `timeout=NAV_DEFAULT_MS`.
- `bot/run_bot_playwright.py`:
  - Вместо разрозненных `os.environ[...]` — `apply_playwright_env()`.
  - Логика headless: `resolve_headless(args.visible)` с тем же приоритетом и сообщением в лог.

Что НЕ меняли в этой итерации
- Случайные `sleep()`/задержки — будут на Итерации 3 (delays).
- Остальные таймауты вне показанных мест — оставлены как есть для минимального риска.

Дальше (план)
- Итерация 3: `config/delays.py` + перенос человеко‑подобных задержек.
- Итерация 4: `config/paths.py` + вынос путей.
- Итерация 5: селекторы → `config/selectors.py` и сведение к единому источнику.
