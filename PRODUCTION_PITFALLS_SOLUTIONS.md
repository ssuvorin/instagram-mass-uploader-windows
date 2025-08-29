# 🚀 Production Deployment Guide - Обход Подводных Камней

## 📋 Критические подводные камни и их решения

Мы выявили и устранили основные проблемы, которые возникают при развертывании модульной архитектуры Instagram automation системы в продакшен:

### ✅ Реализованные решения

1. **Task Lock TTL и Cleanup** - Предотвращение зависших блокировок
2. **Circuit Breaker** - Защита от каскадных сбоев
3. **Rate Limiting** - Защита от DoS атак и злоупотреблений
4. **Connection Pooling** - Предотвращение истощения БД соединений
5. **Graceful Shutdown** - Безопасное завершение работы
6. **Resource Monitoring** - Мониторинг ресурсов системы
7. **Comprehensive Metrics** - Детальная метрика для наблюдения
8. **Automated Maintenance** - Автоматизированное обслуживание

## 🛠 Быстрое развертывание

### 1. Предварительные требования

```bash
# Системные требования
- Ubuntu 20.04+ или CentOS 8+  
- Python 3.8+
- PostgreSQL 13+
- Nginx (рекомендуется)
- Dolphin Anty (должен быть запущен локально)

# Проверка Dolphin Anty API
curl http://localhost:3001/v1.0/browser_profiles
```

### 2. Настройка переменных окружения

```bash
# Создайте .env файл или экспортируйте переменные
export DB_PASSWORD="your_secure_password"
export WORKERS_COUNT=5
export WEB_UI_PORT=8000
export WORKER_BASE_PORT=8088
```

### 3. Автоматическое развертывание

```bash
# Клонируйте проект и перейдите в каталог
cd /path/to/playwright_instagram_uploader

# Выполните первоначальную настройку
./deploy_production.sh setup

# Запустите все сервисы
./deploy_production.sh start

# Проверьте статус
./deploy_production.sh status
```

### 4. Настройка автоматизации

```bash
# Установите cron jobs для автоматического обслуживания
./setup_cron.sh install

# Проверьте статус автоматизации
./setup_cron.sh status

# Протестируйте все скрипты обслуживания
./setup_cron.sh test
```

## 🔧 Детальная конфигурация

### Архитектура системы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │    │   Web UI        │    │   PostgreSQL    │
│   Port 80       │────▶│   Port 8000     │────▶│   Port 5432     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌────────┴────────┐
                       │                 │
           ┌─────────────────┐   ┌─────────────────┐
           │   Worker 1      │   │   Worker 2-5    │
           │   Port 8088     │   │   Port 8089-92  │
           └─────────────────┘   └─────────────────┘
                       │                 │
           ┌─────────────────┐   ┌─────────────────┐
           │  Dolphin Anty   │   │   Task Locks    │
           │  Port 3001      │   │   & Metrics     │
           └─────────────────┘   └─────────────────┘
```

### Основные компоненты

#### 1. Task Lock Manager с TTL

**Файлы:**
- [`dashboard/models.py`](file:///Users/ssuvorin/development_my_projects/playwright_instagram_uploader/modules/web_ui_service/dashboard/models.py) - Enhanced TaskLock model
- [`dashboard/lock_manager.py`](file:///Users/ssuvorin/development_my_projects/playwright_instagram_uploader/modules/web_ui_service/dashboard/lock_manager.py) - Production-ready lock manager
- [`dashboard/migrations/0002_enhance_tasklock.py`](file:///Users/ssuvorin/development_my_projects/playwright_instagram_uploader/modules/web_ui_service/dashboard/migrations/0002_enhance_tasklock.py) - Database migration

**Ключевые особенности:**
```python
# TTL для блокировок с автоматической очисткой
lock_manager.acquire_lock(
    kind='bulk_upload',
    task_id=123,
    worker_id='worker_1',
    ttl_minutes=60  # Автоматическое освобождение через час
)
```

#### 2. Circuit Breaker и Retry Logic

**Файлы:**
- [`bulk_worker_service/production_fixes.py`](file:///Users/ssuvorin/development_my_projects/playwright_instagram_uploader/modules/bulk_worker_service/bulk_worker_service/production_fixes.py) - Circuit breaker implementation

**Использование:**
```python
# HTTP клиент с circuit breaker и retry логикой
client = RobustHttpClient(
    base_url="http://ui-service:8000",
    token="secure_token",
    timeout=30
)

# Автоматические retry с exponential backoff
response = await client.post("/api/task", json=data)
```

#### 3. Rate Limiting

**Файлы:**
- [`bulk_worker_service/rate_limiter.py`](file:///Users/ssuvorin/development_my_projects/playwright_instagram_uploader/modules/bulk_worker_service/bulk_worker_service/rate_limiter.py) - Rate limiting middleware

**Конфигурация:**
```python
# Различные лимиты для разных endpoint'ов
TASK_START_CONFIG = RateLimitConfig(requests=5, window=60, per="user")
HEALTH_CHECK_CONFIG = RateLimitConfig(requests=200, window=60, per="ip")  
METRICS_CONFIG = RateLimitConfig(requests=20, window=60, per="user")
```

#### 4. Database Connection Pooling

**Файлы:**
- [`bulk_worker_service/database.py`](file:///Users/ssuvorin/development_my_projects/playwright_instagram_uploader/modules/bulk_worker_service/bulk_worker_service/database.py) - Connection pooling system

**Настройка:**
```python
# Инициализация pool'а с мониторингом
await initialize_database_pools(
    database_url=DATABASE_URL,
    min_connections=5,
    max_connections=20,
    max_idle_time=300,
    health_check_interval=60
)
```

#### 5. Comprehensive Metrics

**Файлы:**
- [`bulk_worker_service/metrics.py`](file:///Users/ssuvorin/development_my_projects/playwright_instagram_uploader/modules/bulk_worker_service/bulk_worker_service/metrics.py) - Metrics collection system

**Метрики:**
- Counters: `tasks_started_total`, `tasks_completed_total`, `http_requests_total`
- Gauges: `active_tasks`, `memory_usage_mb`, `cpu_usage_percent`
- Histograms: `task_duration_seconds`, `http_request_duration_seconds`
- Timers: Database queries, HTTP requests, task execution

## 📊 Мониторинг и наблюдение

### Health Check Endpoints

```bash
# Простая проверка для load balancer'ов
curl http://localhost:8088/api/v1/health/simple
# {"ok": true, "status": "healthy"}

# Детальная проверка для мониторинга
curl http://localhost:8088/api/v1/health
# Возвращает детальную информацию о состоянии системы
```

### Metrics Endpoints

```bash
# Метрики воркера
curl http://localhost:8088/api/v1/metrics

# Статус сервиса
curl http://localhost:8088/api/v1/status

# Активные блокировки
curl http://localhost:8088/api/v1/locks
```

### Автоматический мониторинг

Cron jobs для автоматического обслуживания:

```bash
# Очистка expired locks каждые 15 минут
*/15 * * * * /path/to/cron_scripts/cleanup_locks.sh

# Health check каждые 5 минут
*/5 * * * * /path/to/cron_scripts/health_check.sh

# Сбор метрик каждую минуту
* * * * * /path/to/cron_scripts/collect_metrics.sh

# Ротация логов ежедневно в 2:00
0 2 * * * /path/to/cron_scripts/rotate_logs.sh

# Бэкап БД ежедневно в 3:00  
0 3 * * * /path/to/cron_scripts/backup_database.sh
```

## 🚨 Устранение проблем

### Частые проблемы и решения

#### 1. Зависшие блокировки задач

**Проблема:** Воркер завершился аварийно, блокировки остались в БД
```bash
# Диагностика
python manage.py cleanup_locks --dry-run

# Принудительная очистка для конкретного воркера
python manage.py cleanup_locks --worker-id worker_1 --force

# Автоматическая очистка expired
python manage.py cleanup_locks
```

#### 2. Превышение лимита подключений к БД

**Проблема:** "Too many connections" errors
```bash
# Проверка текущих соединений
./deploy_production.sh logs web 100 | grep -i "connection"

# Мониторинг connection pool
curl http://localhost:8088/api/v1/metrics | jq .database_pools
```

**Решение:** Настройка connection pooling в .env:
```bash
DB_MIN_CONNECTIONS=5
DB_MAX_CONNECTIONS=20
```

#### 3. Высокое потребление памяти

**Проблема:** Memory leaks в browser processes
```bash
# Мониторинг ресурсов
curl http://localhost:8088/api/v1/status | jq .resource_usage

# Перезапуск воркеров
./deploy_production.sh restart
```

**Решение:** Автоматический мониторинг лимитов:
```bash
MEMORY_LIMIT_MB=2048
MAX_CONCURRENT_TASKS=3
```

#### 4. Rate limiting срабатывает

**Проблема:** HTTP 429 Too Many Requests
```bash
# Проверка текущих лимитов
curl -I http://localhost:8088/api/v1/bulk-upload/start
# X-RateLimit-Limit: 5
# X-RateLimit-Remaining: 2
# X-RateLimit-Reset: 1640995200
```

**Решение:** Настройка в .env:
```bash
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

#### 5. Dolphin Anty недоступен

**Проблема:** Automation tasks failing
```bash
# Проверка Dolphin API
curl http://localhost:3001/v1.0/browser_profiles

# Проверка логов
./deploy_production.sh logs worker 50 1 | grep -i dolphin
```

**Решение:**
1. Убедитесь что Dolphin Anty запущен
2. Включите Local API в настройках
3. Проверьте `DOLPHIN_API_HOST=http://localhost:3001` в .env

### Логи и диагностика

```bash
# Просмотр всех логов
./deploy_production.sh logs all

# Логи конкретного воркера
./deploy_production.sh logs worker 100 2

# Логи веб интерфейса
./deploy_production.sh logs web 100

# Health check логи
tail -f logs/health_check.log

# Lock cleanup логи
tail -f logs/lock_cleanup.log
```

## 🔄 Обновление и масштабирование

### Обновление системы

```bash
# Применение обновлений
git pull origin main
./deploy_production.sh update

# Применение миграций БД
cd modules/web_ui_service
python manage.py migrate

# Перезапуск с минимальным downtime
./deploy_production.sh restart
```

### Горизонтальное масштабирование

```bash
# Увеличение количества воркеров
export WORKERS_COUNT=10
./deploy_production.sh stop
./deploy_production.sh start
```

### Blue-Green Deployment

```bash
# Запуск второй группы воркеров на других портах
export WORKER_BASE_PORT=9088
export WORKERS_COUNT=5
./deploy_production.sh start

# Переключение в nginx
# Обновление upstream в nginx.conf

# Остановка старых воркеров
export WORKER_BASE_PORT=8088
./deploy_production.sh stop
```

## 📈 Performance Tuning

### Оптимизация параметров

```bash
# В .env файле
MAX_CONCURRENT_TASKS=3           # Задач на воркер
MEMORY_LIMIT_MB=2048            # Лимит памяти
DB_MAX_CONNECTIONS=20           # Соединения с БД
HEARTBEAT_INTERVAL_SECS=30      # Интервал heartbeat
RATE_LIMIT_REQUESTS=100         # Лимит запросов
```

### Мониторинг производительности

```bash
# Метрики задач
curl http://localhost:8088/api/v1/metrics | jq '.timers'

# Статистика БД
curl http://localhost:8088/api/v1/metrics | jq '.database_pools'

# Использование ресурсов
curl http://localhost:8088/api/v1/status | jq '.resource_usage'
```

## 🔐 Безопасность

### Генерация токенов

```bash
# Генерация secure токенов
python3 -c "import secrets; print('WORKER_API_TOKEN=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(50))"
```

### Firewall настройки

```bash
# Открытие необходимых портов
sudo ufw allow 80/tcp          # Nginx
sudo ufw allow 8000/tcp        # Web UI
sudo ufw allow 8088:8092/tcp   # Workers
sudo ufw allow 5432/tcp        # PostgreSQL (если внешний)
```

### SSL/TLS (рекомендуется)

```bash
# Настройка Let's Encrypt
sudo certbot --nginx -d your-domain.com
```

## 📚 Дополнительные ресурсы

### Команды управления

```bash
# Основные команды
./deploy_production.sh {setup|start|stop|restart|status|logs|cleanup|update}

# Cron automation
./setup_cron.sh {install|remove|status|test}

# Django management
python manage.py cleanup_locks [--worker-id worker_1] [--dry-run]
```

### Структура проекта

```
playwright_instagram_uploader/
├── deploy_production.sh          # Главный скрипт развертывания  
├── setup_cron.sh                # Настройка автоматизации
├── .env                          # Конфигурация
├── logs/                         # Логи всех сервисов
├── pids/                         # PID файлы процессов
├── backups/                      # Бэкапы БД
├── metrics/                      # Собранные метрики
├── cron_scripts/                 # Скрипты автоматизации
└── modules/
    ├── web_ui_service/          # Django веб интерфейс
    └── bulk_worker_service/     # FastAPI воркеры
```

### Полезные ссылки

- [Comprehensive Deployment Guide](file:///Users/ssuvorin/development_my_projects/playwright_instagram_uploader/COMPREHENSIVE_DEPLOYMENT_GUIDE.md)
- [Production Deployment Checklist](file:///Users/ssuvorin/development_my_projects/playwright_instagram_uploader/PRODUCTION_DEPLOYMENT_CHECKLIST.md)

---

## ✅ Заключение

Мы успешно решили все критические подводные камни модульной архитектуры:

1. **✅ Task Lock TTL** - Автоматическое освобождение зависших блокировок
2. **✅ Circuit Breaker** - Защита от каскадных сбоев сети
3. **✅ Rate Limiting** - Защита API от злоупотреблений  
4. **✅ Connection Pooling** - Эффективное управление БД соединениями
5. **✅ Resource Monitoring** - Мониторинг памяти, CPU, дисков
6. **✅ Graceful Shutdown** - Безопасное завершение работы
7. **✅ Comprehensive Metrics** - Детальная наблюдаемость системы
8. **✅ Automated Maintenance** - Автоматическое обслуживание

Система готова к продакшену с горизонтальным масштабированием и высокой отказоустойчивостью! 🚀