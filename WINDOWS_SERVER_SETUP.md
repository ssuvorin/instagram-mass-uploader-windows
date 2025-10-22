# 🚀 Инструкция по запуску Instagram Uploader на Windows сервере

## 📋 Системные требования

### Минимальные требования:
- **Windows Server 2016+** или **Windows 10/11**
- **Python 3.8+** (рекомендуется 3.11)
- **8GB RAM** (минимум 4GB)
- **50GB свободного места** на диске
- **Стабильное интернет-соединение**

### Дополнительные требования:
- **Dolphin Anty** (для обхода блокировок)
- **Docker Desktop** (опционально, для контейнерного развертывания)
- **Visual C++ Build Tools** (для компиляции некоторых пакетов)

## 🔧 Подготовка сервера

### 1. Установка Python

```powershell
# Скачайте Python с https://www.python.org/downloads/
# ВАЖНО: Отметьте "Add Python to PATH" при установке

# Проверка установки
python --version
pip --version
```

### 2. Установка Dolphin Anty

```powershell
# Скачайте с https://dolphin-anty.com/
# Установите и настройте:
# 1. Включите Local API на порту 3001
# 2. Получите API токен в настройках
# 3. Создайте профили браузера
```

### 3. Установка Docker (опционально)

```powershell
# Скачайте Docker Desktop с https://docs.docker.com/desktop/install/windows-install/
# Запустите и дождитесь полной загрузки
```

## 📥 Установка проекта

### Способ 1: Автоматическая установка (рекомендуется)

```powershell
# 1. Скачайте проект на сервер
git clone https://github.com/your-repo/playwright_instagram_uploader.git
cd playwright_instagram_uploader

# 2. Запустите автоматическую установку
.\setup_windows.bat
```

### Способ 2: Ручная установка

```powershell
# 1. Создание виртуального окружения
python -m venv venv
venv\Scripts\activate

# 2. Установка зависимостей
pip install -r requirements-windows.txt

# 3. Установка Playwright браузеров
playwright install

# 4. Настройка конфигурации
copy windows_deployment.env.example .env
# Отредактируйте .env файл

# 5. Создание базы данных
python manage.py migrate

# 6. Создание суперпользователя
python manage.py createsuperuser

# 7. Сбор статических файлов
python manage.py collectstatic --noinput
```

## ⚙️ Настройка конфигурации

### Редактирование .env файла

```env
# Django настройки
SECRET_KEY=your-super-secret-key-for-production
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,YOUR_SERVER_IP

# Dolphin Anty API (ОБЯЗАТЕЛЬНО!)
DOLPHIN_API_TOKEN=your-dolphin-anty-api-token
DOLPHIN_API_HOST=http://localhost:3001

# reCAPTCHA решение (рекомендуется)
RUCAPTCHA_API_KEY=your-rucaptcha-api-key

# Настройки для Windows сервера
TZ=Europe/Moscow
MAX_CONCURRENT_TASKS=2
BROWSER_TIMEOUT=600
PAGE_LOAD_TIMEOUT=60000
```

### Получение API ключей

1. **Dolphin Anty API токен:**
   - Откройте Dolphin Anty
   - Перейдите в Settings → API
   - Скопируйте токен

2. **RuCaptcha API ключ:**
   - Зарегистрируйтесь на https://rucaptcha.com
   - Получите API ключ в личном кабинете

## 🚀 Запуск системы

### Способ 1: Быстрый запуск

```powershell
# Запуск готовой системы
.\quick_start.bat
```

### Способ 2: Полный запуск

```powershell
# Запуск с проверкой всех компонентов
.\start_project.bat
```

### Способ 3: Docker запуск

```powershell
# Запуск через Docker
.\deploy_windows.ps1 -Production
```

### Способ 4: Ручной запуск

```powershell
# Активация окружения
venv\Scripts\activate

# Запуск сервера
python manage.py runserver 0.0.0.0:8000
```

## 🌐 Доступ к системе

После запуска система будет доступна по адресам:

- **Веб-интерфейс:** http://localhost:8000
- **Админ-панель:** http://localhost:8000/admin
- **API:** http://localhost:8000/api/

### Доступ с других компьютеров:

```env
# В .env файле добавьте IP сервера
ALLOWED_HOSTS=localhost,127.0.0.1,YOUR_SERVER_IP
```

## 📊 Мониторинг и управление

### Просмотр логов

```powershell
# Логи Django
type logs\django.log

# Логи системы
type logs\system.log

# Docker логи (если используется)
docker-compose logs -f
```

### Управление системой

```powershell
# Остановка
Ctrl+C  # В консоли запуска

# Перезапуск
.\start_project.bat

# Обновление
git pull
pip install -r requirements-windows.txt
python manage.py migrate
```

## 🔧 Настройка автозапуска

### Способ 1: Task Scheduler

```powershell
# Создание задачи автозапуска
schtasks /create /tn "Instagram Uploader" /tr "C:\path\to\start_project.bat" /sc onstart
```

### Способ 2: Windows Service

```powershell
# Установка как службы Windows
nssm install "Instagram Uploader" "C:\path\to\start_project.bat"
nssm start "Instagram Uploader"
```

## 🛠️ Решение проблем

### Проблема: Python не найден

```powershell
# Решение: Переустановите Python с отметкой "Add to PATH"
# Или добавьте вручную в переменные окружения
```

### Проблема: Ошибки компиляции пакетов

```powershell
# Решение: Установите Visual C++ Build Tools
# Скачайте с https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

### Проблема: Dolphin Anty недоступен

```powershell
# Проверьте:
# 1. Запущен ли Dolphin Anty
# 2. Включен ли Local API на порту 3001
# 3. Правильный ли API токен в .env
```

### Проблема: Ошибки миграций

```powershell
# Решение: Примените миграции вручную
python manage.py migrate --run-syncdb
python manage.py migrate
```

## 📈 Оптимизация производительности

### Настройки для мощного сервера

```env
# Увеличьте количество параллельных задач
MAX_CONCURRENT_TASKS=4

# Уменьшите таймауты
BROWSER_TIMEOUT=300
PAGE_LOAD_TIMEOUT=30000
```

### Настройки для слабого сервера

```env
# Уменьшите количество параллельных задач
MAX_CONCURRENT_TASKS=1

# Увеличьте таймауты
BROWSER_TIMEOUT=900
PAGE_LOAD_TIMEOUT=90000
```

## 🔒 Безопасность

### Настройки безопасности

```env
# Отключите DEBUG в продакшене
DEBUG=False

# Используйте сложный SECRET_KEY
SECRET_KEY=your-very-complex-secret-key-here

# Ограничьте ALLOWED_HOSTS
ALLOWED_HOSTS=your-domain.com,your-server-ip
```

### Firewall настройки

```powershell
# Откройте порт 8000 для веб-интерфейса
netsh advfirewall firewall add rule name="Instagram Uploader" dir=in action=allow protocol=TCP localport=8000

# Закройте порт 3001 от внешнего доступа (Dolphin Anty)
netsh advfirewall firewall add rule name="Dolphin Anty" dir=in action=block protocol=TCP localport=3001
```

## 📞 Поддержка

### Полезные команды для диагностики

```powershell
# Проверка статуса системы
python manage.py check

# Проверка миграций
python manage.py showmigrations

# Очистка кэша
python manage.py clear_cache

# Проверка зависимостей
pip check
```

### Логи для отладки

```powershell
# Включите подробное логирование в .env
LOG_LEVEL=DEBUG
LOG_TO_FILE=True
```

## 🎯 Следующие шаги

1. **Настройте аккаунты Instagram** в веб-интерфейсе
2. **Создайте профили Dolphin Anty** для каждого аккаунта
3. **Загрузите тестовые видео** для проверки работы
4. **Настройте автоматические задачи** в админ-панели
5. **Мониторьте логи** для выявления проблем

---

## 📝 Примечания

- Система использует SQLite по умолчанию для простоты развертывания
- Для продакшена рекомендуется PostgreSQL
- Регулярно обновляйте зависимости для безопасности
- Делайте резервные копии базы данных

**Удачного использования! 🚀**

