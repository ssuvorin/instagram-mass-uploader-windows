## Разделение интерфейса и функциональной части (Playwright Instagram Uploader)

Данный документ описывает целевую архитектуру, детальный план миграции и пошаговые инструкции по деплою системы, где интерфейс запускается на отдельном сервере Ubuntu, а функциональные модули (воркеры Playwright и связанные сервисы обработки заданий) выполняются на Windows-серверах, масштабируясь горизонтально.

Документ ориентирован на безопасное и устойчивое разделение UI и бэкенд-логики, а также на высокую производительность при большом количестве аккаунтов и заданий.

> Внимание: взаимодействие с платформами может подпадать под ограничения их пользовательских соглашений. Убедитесь, что вы соответствуете требованиям Instagram и местному законодательству.

---

### 1) Цели и ключевые принципы

- Полное отделение интерфейса от функциональной части (автоматизация, работа с Playwright и аккаунтами).
- Интерфейс (UI) на отдельном Ubuntu-сервере.
- Воркеры и модульная функциональная часть на отдельных Windows-серверах.
- Горизонтальное масштабирование за счёт добавления Windows-воркеров.
- Централизованные база данных, очередь, логирование и мониторинг.
- Надёжность и устойчивость: механизмы retry, backoff, изоляция сбоев.
- Конфигурация и секреты через .env и/или менеджер секретов; параметры не хардкодятся.
- Чистая архитектура, модульность, SOLID/DRY/KISS. Строгая ответственность слоёв.

---

### 2) Целевая архитектура (общая схема)

```
+--------------------+                 +---------------------------+
|   Ubuntu Server    |                 |   Windows Workers (N)     |
|--------------------|                 |---------------------------|
| UI (Admin Panel)   |  HTTP(S)  --->  | worker-service (Playwright)
| API Gateway/CTRL   |  REST/gRPC      | - Получение задач из Redis
| Nginx/Traefik      | <--- WS/events  | - Playwright сценарии
+---------+----------+                 | - Логи/метрики -> ELK/Prom
          |                            +---------------------------+
          |         +----------------------------------------------+
          |         |         Общая инфраструктура                 |
          v         v                                              |
      +----------------+    +----------------+   +-----------------+|
      |  PostgreSQL    |    |    Redis MQ    |   |  Object Storage ||
      |  (accounts,    |    |  (BullMQ/Rabbit|   |  (S3/MinIO)     ||
      |  jobs, logs)   |    |   queues)      |   |  медиа          ||
      +----------------+    +----------------+   +-----------------+|
                                 ^      ^                           |
                                 |      |                           |
                                 +------+---------------------------+
```

Рекомендация: держать состояние (PostgreSQL/Redis/S3) и API/UI на Ubuntu. Тяжёлую автоматизацию (Playwright) — на Windows-узлах. Это упрощает эксплуатацию и повышает стабильность. При необходимости можно вынести API на отдельный Ubuntu-сервер.

---

### 3) Компоненты и ответственность

- UI (Admin Panel)
  - Панель управления заданиями и аккаунтами: создание, запуск, статус, отчёты.
  - Не содержит Playwright-кода; только UI и вызовы API.
- API Gateway / Controller (Ubuntu)
  - REST/gRPC API для UI.
  - Валидация запросов, проверка прав (RBAC), аудиты.
  - Постановка задач в очередь (Redis/RabbitMQ).
- Account Service (логика аккаунтов)
  - Хранение аккаунтов, прокси, cookie, фингерпринтов, статусов.
  - Шифрование чувствительных данных на уровне БД (KMS/ключ).
- Orchestrator/Scheduler (может быть частью Controller)
  - Планирование, дедупликация, rate-limit по домену/аккаунту.
  - Правила повторов (retry/backoff), карантин проблемных аккаунтов.
- Worker Service (Windows, N экземпляров)
  - Подписка на очередь задач.
  - Исполнение сценариев Playwright по Page Object Model.
  - Имитация человеческого поведения: рандомные паузы, плавные движения, hover.
  - Надёжные локаторы, карта запасных селекторов.
  - Отправка результатов/логов/метрик в бэкенд.
- Infra
  - PostgreSQL: аккаунты, задачи, результаты, аудиты, логи задач.
  - Redis (BullMQ)/RabbitMQ: очереди заданий и событий.
  - Object Storage: медиаконтент для загрузки.
  - Observability: Prometheus/Grafana, ELK/Loki, Sentry.

---

### 4) Рекомендуемый стек

- Язык/Runtime: Node.js 20+ (TypeScript)
- Автоматизация: Playwright 1.45+ с установленными браузерами на Windows
- Очередь: Redis + BullMQ (кросс-платформенно, просто для Windows)
- БД: PostgreSQL 14+
- ORM: Prisma/TypeORM (на выбор)
- Логи: pino/winston + отправка в Loki/ELK
- UI: Next.js/React или любая web-админка + Nginx/Traefik
- Деплой Ubuntu: Docker Compose / systemd
- Деплой Windows: PM2 (windows), NSSM/WinSW как альтернатива

---

### 5) Структура репозитория (монорепо, пример)

```
playwright_instagram_uploader/
  apps/
    ui/                    # интерфейс (Ubuntu)
    controller/            # API + Orchestrator (Ubuntu)
    worker/                # Windows-воркер(а)
  packages/
    automation-core/       # общая логика Playwright (Page Objects, утилиты)
    account-core/          # модели аккаунтов, сервисы, валидации
    shared/                # типы, DTO, клиенты API/Queue, конфиг
  infra/
    docker-compose.yml     # PostgreSQL, Redis, UI, Controller, MinIO (опц.)
    grafana/, prometheus/, loki/  # опционально
  scripts/                 # миграции, bootstrap, генераторы
  SEPARATION_GUIDE.md      # этот документ
```

---

### 6) Минимальная модель данных (SQL, ориентир)

```sql
-- accounts
CREATE TABLE accounts (
  id UUID PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_encrypted TEXT NOT NULL,
  proxy_url TEXT,
  cookie_jar JSONB,
  device_fingerprint JSONB,
  status TEXT NOT NULL DEFAULT 'active',
  last_login_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- jobs
CREATE TABLE jobs (
  id UUID PRIMARY KEY,
  type TEXT NOT NULL, -- e.g. 'login', 'upload_post'
  account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
  payload JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued', -- queued|running|done|failed|retry|cancelled
  attempts INT NOT NULL DEFAULT 0,
  max_attempts INT NOT NULL DEFAULT 3,
  result JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- job_logs (по желанию)
CREATE TABLE job_logs (
  id BIGSERIAL PRIMARY KEY,
  job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
  level TEXT NOT NULL, -- info|warn|error
  message TEXT NOT NULL,
  context JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

### 7) Контракты API (минимально необходимые)

- POST `/api/accounts`
  - body: `{ username, password, proxyUrl?, tags?[] }`
  - resp: `{ id }`
- GET `/api/accounts?status=&tag=` -> список аккаунтов, пагинация
- GET `/api/accounts/:id` -> детали, маскируем чувствительные поля
- PATCH `/api/accounts/:id` -> update proxy/status/tags
- POST `/api/jobs`
  - body: `{ type: 'login'|'upload_post'|..., accountId, payload }`
  - resp: `{ jobId }`
- GET `/api/jobs/:id` -> `{ status, attempts, result }`
- POST `/api/jobs/:id/cancel` -> отмена в очереди
- GET `/api/stats` -> агрегаты для UI

Аутентификация: JWT/Access Token для UI, роль «admin»/«operator». Все эндпоинты логируются и аудируются.

---

### 8) Очереди и полезная нагрузка задач (BullMQ)

- Очередь: `jobs:main`
- Типы задач: `login`, `upload_post`, `check_health`, `rotate_proxy`, `refresh_cookies`
- Общая схема payload:

```json
{
  "jobId": "uuid",
  "type": "upload_post",
  "accountId": "uuid",
  "payload": {
    "mediaUrl": "s3://bucket/path/to/file.jpg",
    "caption": "string",
    "location": "optional",
    "hashtags": ["..."],
    "scheduleAt": "optional ISO8601"
  },
  "meta": {
    "traceId": "uuid",
    "requestedBy": "userId",
    "priority": 1
  }
}
```

Retry policy: экспоненциальный backoff, jitter, лимит попыток `max_attempts` на запись jobs.

---

### 9) Правила имитации человека (обязательно для Worker)

- Рандомизированные паузы между действиями (human-like delays).
- Плавные движения курсора (Bezier/интерполяция) вместо мгновенных прыжков.
- «Сканирование» интерфейса: короткий hover, небольшая пауза перед кликом.
- Надёжные локаторы: `data-*`, `aria-*`, `role` и fallback-локаторы; минимум `nth-child`.
- Текстовая верификация: проверять видимый текст внутри найденного элемента.
- Повтор действий с backoff при нестабильной загрузке.
- Централизованное логирование: время, действие, локатор, исход задачи.

---

### 10) Конфигурация и секреты

- `.env` (Ubuntu/UI+Controller):
```
NODE_ENV=production
POSTGRES_URL=postgres://user:pass@postgres:5432/ig
REDIS_URL=redis://redis:6379
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
JWT_SECRET=...
API_BASE_URL=https://your-ui-domain/api
```
- `.env.worker` (Windows/Worker):
```
NODE_ENV=production
POSTGRES_URL=postgres://user:pass@ubuntu-host-or-vip:5432/ig
REDIS_URL=redis://ubuntu-host-or-vip:6379
S3_ENDPOINT=http://ubuntu-host-or-vip:9000
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
WORKER_CONCURRENCY=2
PLAYWRIGHT_HEADLESS=true
PROXY_POOL_URL=https://... (если внешний пул)
``` 
- Секреты не храним в git. Возможен HashiCorp Vault/Azure Key Vault/AWS Secrets Manager.

---

### 11) Пошаговая миграция (рефакторинг)

1. Подготовка монорепо
   - Создайте директории `apps/ui`, `apps/controller`, `apps/worker`, `packages/*`.
   - Вынесите общие типы и DTO в `packages/shared`.
2. Экстракция доменной логики
   - Перенесите Playwright Page Objects и утилиты в `packages/automation-core`.
   - Вынесите логику учётных записей в `packages/account-core` (валидаторы, шифрование, клиенты БД).
3. Введение БД и ORM
   - Добавьте миграции для таблиц `accounts`, `jobs`, `job_logs`.
   - Обновите код работы с аккаунтами на использование БД.
4. Введение очереди
   - Поднимите Redis, создайте продюсер задач (Controller) и консюмер (Worker).
   - Определите типы задач и схему payload.
5. Реализация API
   - Реализуйте эндпоинты (см. раздел 7) в `apps/controller`.
   - UI переведите на вызовы API вместо прямого вызова Playwright.
6. Реализация Worker (Windows)
   - Подпишитесь на `jobs:main`, реализуйте обработчики `login`, `upload_post`.
   - Добавьте правила имитации человека, надёжные локаторы, retry/backoff.
7. Логи, метрики и трассировка
   - Пишите логи в STDOUT + БД/ELK. Экспортируйте Prometheus-метрики (`/metrics`).
8. Фичи управления
   - Карантин аккаунтов, rate-limits, ограничение параллелизма на аккаунт/прокси/AS.
9. Удаление связей UI↔Playwright
   - Убедитесь, что UI не импортирует ничего из `automation-core` напрямую. Только через API.
10. E2E-тест
   - Прогоните сценарии: создать аккаунт → создать задачу → обработка воркером → статус «done».

---

### 12) Развёртывание (Ubuntu, интерфейс + контроллер + инфраструктура)

1. Установка зависимостей
```
sudo apt update && sudo apt install -y ca-certificates curl gnupg
# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Docker Compose v2 уже в docker-ce
```
2. Создайте каталог `infra/` и `.env`
3. Пример `infra/docker-compose.yml` (минимальный):
```yaml
version: "3.9"
services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: ig
      POSTGRES_USER: ig
      POSTGRES_PASSWORD: igpass
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  redis:
    image: redis:7
    ports:
      - "6379:6379"
  minio:
    image: minio/minio:latest
    command: server /data --console-address :9001
    environment:
      MINIO_ROOT_USER: minio
      MINIO_ROOT_PASSWORD: minio123
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio:/data
  controller:
    image: your-registry/controller:latest
    env_file: .env
    depends_on: [postgres, redis]
    ports:
      - "8080:8080"
  ui:
    image: your-registry/ui:latest
    env_file: .env
    depends_on: [controller]
    ports:
      - "80:3000"
volumes:
  pgdata:
  minio:
```
4. Запуск
```
cd infra
docker compose up -d
```
5. Проверьте `http://<ubuntu-host>/` (UI), `http://<ubuntu-host>:8080/health` (Controller).

---

### 13) Развёртывание (Windows, воркеры)

1. Установите Node.js 20 LTS, Git.
2. Установите Playwright и браузеры:
```
npm i -g npm@latest
npm i
npx playwright install
```
3. Создайте `.env.worker` (см. раздел 10). Убедитесь, что хост Ubuntu доступен по сети.
4. Запуск под PM2:
```
npm i -g pm2
pm2 start dist/apps/worker/main.js --name worker --time --env production --max-memory-restart 1024M
pm2 save
pm2 startup
```
5. Масштабирование: на каждом новом Windows-сервере повторите шаги и добавьте ещё один `pm2`-процесс или несколько с `--instances`.

Примечания:
- Для Windows можно использовать NSSM/WinSW для регистрации как Windows Service.
- Не забывайте `npx playwright install` после обновлений.

---

### 14) Масштабирование и производительность

- Добавление воркеров: просто подключите новый Windows-узел к той же очереди Redis.
- Управление параллелизмом: `WORKER_CONCURRENCY`, семафоры на аккаунт/прокси.
- Rate limiting: правила в Orchestrator, токен-бакеты.
- Кэширование: метаданные профилей/медиаданных — через Redis.
- Холодный старт браузеров: пул контекстов/браузеров, минимизируйте перезапуски.

---

### 15) Надёжность и отказоустойчивость

- Retry с экспоненциальным backoff и jitter.
- Карантин аккаунтов после N неудач; ручной разбан через UI.
- Идёмпотентность: jobId как ключ идемпотентности.
- Хранение чекпоинтов: прогресс в `job_logs`.
- Circuit breaker для внешних сервисов (прокси провайдеры и т.п.).

---

### 16) Логирование и мониторинг

- Логи: уровень, действие, селектор, время, jobId, accountId, traceId. Отправка в Loki/ELK.
- Метрики: количество задач по статусам, время выполнения, ошибка/успех, потребление CPU/RAM.
- Алёрты: SLO по времени выполнения/ошибкам; уведомления (Slack/Telegram).

---

### 17) Безопасность

- Храните пароли только в зашифрованном виде. В рантайме используйте KMS/ключ.
- Ограничьте доступ к БД и Redis по сети (VPC/Firewall). TLS для внешних соединений.
- RBAC в UI и API. Аудит действий пользователей.
- Rate limiting и защита от брута для UI/API.

---

### 18) Тестирование (минимальные сценарии)

- Контрактные тесты API (OpenAPI + тесты на валидацию).
- Интеграционные тесты: постановка задачи → обработка воркером → статус `done`.
- Нагрузочные тесты: 100-1000 задач/час, несколько воркеров.
- Chaos-тесты: перезапуск Redis/воркеров во время загрузки, проверка устойчивости.

---

### 19) План поэтапного запуска в прод

1. Staging: поднять полный контур на тестовых ресурсах.
2. Прогнать e2e-сценарии, убедиться в метриках/логах.
3. Мигрировать часть трафика/аккаунтов на новую архитектуру (канареечный запуск).
4. Постепенно перевести весь трафик, оставить фолбек.

---

### 20) Частые вопросы

- Можно ли держать API на Windows? Можно, но рекомендуется держать состояние (БД/Redis) и API на Ubuntu из соображений стабильности.
- Можно ли заменить Redis на RabbitMQ? Да. Воркеры будут слушать очереди RabbitMQ. Контроллер — отправлять задачи в соответствующий exchange/queue.
- Что с прокси? Рекомендуется на аккаунт свой прокси или пул прокси; закрепляйте прокси в `accounts.proxy_url`.

---

### 21) Чек-лист готовности

- [ ] UI не содержит Playwright-кода и общается только с API
- [ ] Воркеры получают задачи из очереди, нет прямых вызовов из UI
- [ ] БД и Redis доступны, миграции применены
- [ ] Логи и метрики собираются
- [ ] Секреты вне git, есть бэкапы БД
- [ ] Добавление нового Windows-воркера требует только `.env.worker` и `pm2 start`

---

### 22) Следующие шаги

- Принять структуру монорепо, создать базовые каркасы `apps/*` и `packages/*`.
- Реализовать API и очередь для одного типа задачи (например, `login`).
- Поднять один Windows-воркер, проверить сквозной сценарий.
- Добавлять остальные типы задач итеративно (upload, stories, и т. д.).

Если требуется, можно дополнить этот документ конкретными командами для вашего репозитория и CI/CD-конфигурациями (GitHub Actions/GitLab CI) после первичного рефакторинга.
