# TikTok Bot Integration Guide

Руководство по интеграции бота TikTokUploadCaptcha в веб-интерфейс Django.

## ✅ Что было сделано

### 1. Структура интеграции

Создана папка `tiktok_uploader/bot_integration/` со следующей структурой:

```
tiktok_uploader/bot_integration/
├── __init__.py              # Инициализация логгера
├── logger.py                # Система логирования
├── telegram_notifier.py     # Telegram уведомления
├── db.py                    # SQLite база данных
├── services.py              # Сервисный слой для Django ⭐
├── sites.json               # Список сайтов для Cookie Robot
├── dolphin/                 # Модули Dolphin Anty
│   ├── __init__.py
│   ├── dolphin.py          # Управление профилями
│   └── profile.py          # Класс профиля
└── tiktok/                  # Модули TikTok
    ├── __init__.py
    ├── auth.py             # Аутентификация
    ├── upload.py           # Загрузка видео
    ├── booster.py          # Прогрев аккаунтов
    ├── video.py            # Класс Video
    ├── getCode.py          # Получение email кодов
    ├── captcha.py          # Решение CAPTCHA
    ├── browser.py          # Управление браузером
    ├── locators.py         # Селекторы элементов
    └── utils.py            # Утилиты
```

### 2. Скопированные модули

Все модули из `TikTokUploadCaptcha/src/` были скопированы в `bot_integration/` с обновленными импортами:

- ✅ Модули dolphin (управление Dolphin Anty профилями)
- ✅ Модули tiktok (аутентификация, загрузка, прогрев)
- ✅ Вспомогательные модули (logger, db, telegram)
- ✅ Конфигурационные файлы (sites.json)

**Важно:** Логика бота НЕ изменялась! Все модули работают так же, как в оригинале.

### 3. Сервисный слой (services.py)

Создан адаптер между Django моделями и логикой бота. Основные функции:

#### `create_dolphin_profile_for_account(account, locale=None)`
Создает Dolphin профиль для TikTok аккаунта с реалистичными fingerprints.

#### `run_bulk_upload_task(task_id)`
Запускает задачу массовой загрузки видео с использованием оригинальной логики бота.

#### `run_warmup_task(task_id)`
Запускает задачу прогрева аккаунтов через Booster.

#### `run_cookie_robot_for_account(account)`
Запускает Cookie Robot для обновления cookies профиля.

#### `export_cookies_from_profile(account)`
Экспортирует cookies из Dolphin профиля аккаунта.

### 4. Обновленные Views

#### `tiktok_uploader/views.py`
- ✅ `create_dolphin_profile()` - теперь использует `create_dolphin_profile_for_account()`

#### `tiktok_uploader/views_mod/views_bulk.py`
- ✅ `start_bulk_upload_api()` - теперь использует `run_bulk_upload_task()` в фоновом потоке

#### `tiktok_uploader/views_warmup.py`
- ✅ `warmup_task_start()` - теперь использует `run_warmup_task()` в фоновом потоке

### 5. Обновленные зависимости

В `requirements.txt` добавлены:

```txt
# Browser automation
playwright-stealth>=1.0.6
tiktok-captcha-solver>=0.8.2

# Security and authentication
pyzmail36>=1.0.5

# HTTP requests and networking
websockets>=15.0
fake-useragent>=2.0.0

# Video processing
numpy>=2.0.0
```

## 🚀 Установка и настройка

### Шаг 1: Установка зависимостей

```bash
# Установка Python зависимостей
pip install -r requirements.txt

# Установка браузеров Playwright
playwright install chromium
```

### Шаг 2: Установка и настройка Dolphin Anty

1. Скачайте и установите [Dolphin Anty](https://dolphin-anty.com/)
2. Запустите Dolphin Anty на `localhost:3001`
3. Получите API токен в настройках Dolphin Anty

### Шаг 3: Настройка переменных окружения

Создайте или обновите файл `.env`:

```env
# Dolphin Anty API Token (обязательно)
TOKEN=your_dolphin_anty_token_here

# TikTok Captcha Solver API Key (обязательно)
TIKTOK_SOLVER_API_KEY=your_captcha_solver_api_key_here

# Telegram уведомления (опционально)
TELEGRAM_TOKEN=your_telegram_bot_token
ADMINS=123456789,987654321
SERVER_NAME=Production TikTok Bot

# Debug режим (опционально)
DEBUG=False
```

### Шаг 4: Миграции базы данных

```bash
python manage.py migrate
```

### Шаг 5: Создание папки для логов

```bash
mkdir -p logs
```

## 📖 Использование

### 1. Создание аккаунта с Dolphin профилем

```python
from tiktok_uploader.models import TikTokAccount, TikTokProxy
from tiktok_uploader.bot_integration.services import create_dolphin_profile_for_account

# Создать аккаунт
proxy = TikTokProxy.objects.get(id=1)  # Существующий прокси
account = TikTokAccount.objects.create(
    username='my_tiktok',
    password='secure_password',
    email='my_email@example.com',
    email_password='email_password',
    proxy=proxy,
    locale='en_US'
)

# Создать Dolphin профиль
result = create_dolphin_profile_for_account(account)
if result['success']:
    print(f"✅ Dolphin profile created: {result['profile_id']}")
else:
    print(f"❌ Error: {result['error']}")
```

### 2. Запуск задачи загрузки видео

**Через веб-интерфейс:**
1. Перейдите в "Bulk Upload" → "Create Task"
2. Загрузите видео и настройте параметры
3. Добавьте аккаунты к задаче
4. Нажмите "Start Upload"

**Программно:**

```python
import threading
from tiktok_uploader.bot_integration.services import run_bulk_upload_task

def start_upload(task_id):
    # Запускаем в фоновом потоке
    def run():
        try:
            result = run_bulk_upload_task(task_id)
            print(f"Upload completed: {result}")
        except Exception as e:
            print(f"Upload error: {e}")
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

# Запуск
start_upload(task_id=1)
```

### 3. Запуск задачи прогрева

**Через веб-интерфейс:**
1. Перейдите в "Warmup" → "Create Task"
2. Добавьте аккаунты
3. Настройте параметры прогрева
4. Нажмите "Start"

**Программно:**

```python
from tiktok_uploader.bot_integration.services import run_warmup_task

def start_warmup(task_id):
    import threading
    
    def run():
        try:
            result = run_warmup_task(task_id)
            print(f"Warmup completed: {result}")
        except Exception as e:
            print(f"Warmup error: {e}")
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

# Запуск
start_warmup(task_id=1)
```

### 4. Управление cookies

```python
from tiktok_uploader.bot_integration.services import (
    run_cookie_robot_for_account,
    export_cookies_from_profile
)

# Обновить cookies через Cookie Robot
result = run_cookie_robot_for_account(account)
if result['success']:
    print("✅ Cookies updated")

# Экспортировать cookies
cookies = export_cookies_from_profile(account)
if cookies:
    print(f"✅ Exported {len(cookies)} cookies")
```

## 🔍 Проверка работы

### 1. Проверка Dolphin Anty

```bash
# Проверить, что Dolphin запущен
curl http://localhost:3001/v1.0/browser_profiles

# Должен вернуть список профилей или {"data": []}
```

### 2. Проверка создания профиля

```python
from django.contrib.auth.models import User
from tiktok_uploader.models import TikTokAccount, TikTokProxy

# Получить аккаунт
account = TikTokAccount.objects.first()

# Создать профиль
from tiktok_uploader.bot_integration.services import create_dolphin_profile_for_account
result = create_dolphin_profile_for_account(account)

# Проверить результат
print(result)
# Должно быть: {'success': True, 'profile_id': '123456', ...}
```

### 3. Проверка логов

```bash
# Посмотреть логи бота
tail -f logs/tiktok_bot.log

# Должны появляться записи вида:
# [2025-10-04 21:00:00]:[INFO] Dolphin profile created for username: 123456
```

## 🐛 Troubleshooting

### Ошибка: "No Dolphin profile"

**Решение:**
1. Убедитесь, что Dolphin Anty запущен
2. Проверьте токен `TOKEN` в `.env`
3. Создайте профиль через `create_dolphin_profile_for_account()`

### Ошибка: "Failed to authenticate"

**Решение:**
1. Проверьте правильность username и password
2. Убедитесь, что email и email_password указаны (для получения кодов)
3. Проверьте работу прокси
4. Проверьте, что аккаунт не заблокирован TikTok

### Ошибка: "CAPTCHA solving failed"

**Решение:**
1. Проверьте `TIKTOK_SOLVER_API_KEY` в `.env`
2. Убедитесь, что баланс API не исчерпан
3. Проверьте логи на детали ошибки

### Ошибка: "Module not found"

**Решение:**
```bash
# Переустановить зависимости
pip install -r requirements.txt --force-reinstall

# Установить браузеры Playwright
playwright install chromium
```

## 📊 Мониторинг

### Логи бота

Логи сохраняются в `logs/tiktok_bot.log`:

```bash
# Последние 100 строк
tail -n 100 logs/tiktok_bot.log

# Следить за логами в реальном времени
tail -f logs/tiktok_bot.log

# Поиск ошибок
grep ERROR logs/tiktok_bot.log
```

### Telegram уведомления

Если настроены `TELEGRAM_TOKEN` и `ADMINS`, уведомления отправляются при:
- Начале задачи загрузки/прогрева
- Завершении задачи
- Критических ошибках

### Статистика в Django Admin

Вся статистика доступна в Django Admin:
- Аккаунты: `/admin/tiktok_uploader/tiktokaccount/`
- Задачи загрузки: `/admin/tiktok_uploader/bulkuploadtask/`
- Задачи прогрева: `/admin/tiktok_uploader/warmuptask/`

## 🎯 Важные замечания

### 1. Сохранение логики бота

✅ **Вся логика бота сохранена без изменений!**

Все модули из `TikTokUploadCaptcha/src/` скопированы в `bot_integration/` с минимальными изменениями:
- Обновлены только импорты для работы с Django
- Добавлен адаптер `services.py`
- Логика аутентификации, загрузки и прогрева не изменялась

### 2. Блокирующие операции

⚠️ Функции `run_bulk_upload_task()` и `run_warmup_task()` являются **блокирующими** и могут выполняться долго (часы).

**Рекомендации:**
- Запускать в отдельном потоке (threading) ✅
- Использовать Celery для production
- Использовать отдельный процесс (multiprocessing)

### 3. Требования к окружению

- ✅ Python 3.10+
- ✅ Dolphin Anty запущен на `localhost:3001`
- ✅ Playwright браузеры установлены
- ✅ Прокси настроены для каждого аккаунта

### 4. Производительность

Типичная скорость работы:
- **Создание профиля**: ~5-10 секунд
- **Аутентификация**: ~30-60 секунд
- **Загрузка 1 видео**: ~2-5 минут
- **Прогрев аккаунта**: ~10-20 минут

## 📚 Дополнительная документация

- `tiktok_uploader/bot_integration/README.md` - Детальная документация модуля
- `TikTokUploadCaptcha/README.md` - Документация оригинального бота
- `tiktok_uploader/USER_JOURNEY_GUIDE.md` - Руководство пользователя веб-интерфейса

## 🎉 Готово!

Интеграция завершена. Бот полностью интегрирован в веб-интерфейс Django с сохранением всей оригинальной логики.

**Основные возможности:**
- ✅ Создание Dolphin профилей для аккаунтов
- ✅ Массовая загрузка видео через бота
- ✅ Прогрев аккаунтов
- ✅ Управление cookies
- ✅ Telegram уведомления
- ✅ Детальное логирование

**Следующие шаги:**
1. Настроить переменные окружения
2. Установить и запустить Dolphin Anty
3. Создать аккаунты и прокси в Django Admin
4. Создать Dolphin профили для аккаунтов
5. Запустить первую задачу загрузки!

---

*Если возникнут вопросы или проблемы, проверьте логи в `logs/tiktok_bot.log` и разделы Troubleshooting выше.*

