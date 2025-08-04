# 🖥️ Развертывание на Windows Server

Подробная инструкция по установке и настройке Instagram Mass Uploader на Windows сервере с использованием Docker.

## 📋 Требования

### Системные требования
- **Windows Server 2019/2022** или **Windows 10/11 Pro**
- **Минимум 8GB RAM** (рекомендуется 16GB)
- **4+ ядра CPU**
- **50GB+ свободного места**
- **Стабильное интернет-соединение**

### Необходимое ПО
- **Docker Desktop for Windows** или **Docker Engine**
- **Dolphin Anty Browser** (обязательно!)
- **Remote Desktop** доступ к серверу
- **PowerShell 5.1+**

## 🚀 Пошаговая установка

### 1. Подготовка Windows сервера

```powershell
# Включите Hyper-V и контейнеры Windows (если еще не включены)
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
Enable-WindowsOptionalFeature -Online -FeatureName Containers -All

# Перезагрузите сервер
Restart-Computer
```

### 2. Установка Docker

```powershell
# Скачайте и установите Docker Desktop for Windows
# https://docs.docker.com/desktop/install/windows-install/

# Или установите Docker Engine через PowerShell:
Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/docker/docker-install/master/install.ps1" -o install-docker.ps1
.\install-docker.ps1

# Проверьте установку
docker --version
docker-compose --version
```

### 3. Установка Dolphin Anty

```powershell
# Скачайте Dolphin Anty для Windows
# https://dolphin-anty.com/download

# Установите и запустите Dolphin Anty
# Получите API токен из настроек программы
```

### 4. Клонирование и настройка проекта

```powershell
# Клонируйте репозиторий
git clone YOUR_REPOSITORY_URL
cd playwright_instagram_uploader

# Скопируйте и настройте переменные окружения
copy windows_deployment.env.example .env

# Отредактируйте .env файл в текстовом редакторе
notepad .env
```

### 5. Настройка переменных окружения

Откройте файл `.env` и настройте следующие параметры:

```env
# Обязательные настройки
SECRET_KEY=your-super-secret-key-change-this
ALLOWED_HOSTS=localhost,127.0.0.1,YOUR_SERVER_IP
DOLPHIN_API_TOKEN=your-dolphin-api-token

# Рекомендуемые настройки
RUCAPTCHA_API_KEY=your-rucaptcha-key
```

### 6. Сборка и запуск

```powershell
# Соберите Docker образ для Windows
docker-compose -f docker-compose.windows.yml build

# Запустите контейнер
docker-compose -f docker-compose.windows.yml up -d

# Проверьте статус
docker-compose -f docker-compose.windows.yml ps
```

### 7. Проверка работы

```powershell
# Откройте браузер и перейдите по адресу:
# http://localhost:8000

# Или проверьте через curl
curl http://localhost:8000
```

## ⚙️ Настройка Dolphin Anty для Windows

### 1. Получение API токена

1. Откройте **Dolphin Anty**
2. Перейдите в **Settings → API**
3. Включите **Local API**
4. Скопируйте **API Token**
5. Добавьте токен в файл `.env`

### 2. Создание профилей

```powershell
# Создайте профили для ваших Instagram аккаунтов в Dolphin Anty
# Рекомендуется использовать прокси для каждого профиля
# Убедитесь, что API порт 3001 доступен
```

### 3. Настройка сетевого доступа

```powershell
# ВАЖНО ДЛЯ DOCKER: Настройте переменную окружения DOLPHIN_API_HOST
# В файле .env установите:
# DOLPHIN_API_HOST=http://host.docker.internal:3001

# Разрешите доступ к Dolphin Anty API из Docker контейнера
# Убедитесь, что Windows Firewall не блокирует порт 3001

# Проверьте доступность API (с хоста Windows):
curl http://localhost:3001/v1.0/browser_profiles

# Проверьте доступность API (из Docker контейнера):
docker exec -it <container_name> curl http://host.docker.internal:3001/v1.0/browser_profiles
```

**🚨 КРИТИЧНО для Docker:** Docker контейнеры не могут обращаться к `localhost` хоста Windows. 
Обязательно используйте `host.docker.internal:3001` в переменной `DOLPHIN_API_HOST`!

## 🔧 Оптимизация для Windows сервера

### 1. Настройка производительности

```powershell
# Увеличьте лимиты памяти для Docker
# Docker Desktop → Settings → Resources → Memory: 8GB+

# Настройте количество CPU cores
# Docker Desktop → Settings → Resources → CPUs: 4+
```

### 2. Настройка автозапуска

Создайте файл `start_instagram_uploader.bat`:

```batch
@echo off
cd /d "C:\path\to\your\project"
docker-compose -f docker-compose.windows.yml up -d
echo Instagram Uploader started successfully!
pause
```

Добавьте в автозагрузку Windows:
```powershell
# Добавьте .bat файл в Task Scheduler для автозапуска при старте системы
```

### 3. Мониторинг и логирование

```powershell
# Просмотр логов
docker-compose -f docker-compose.windows.yml logs -f

# Мониторинг ресурсов
docker stats

# Резервное копирование базы данных
copy db.sqlite3 "C:\backups\db_$(Get-Date -Format 'yyyy-MM-dd').sqlite3"
```

## 🛠️ Устранение проблем

### Проблема 1: Docker не запускается

```powershell
# Проверьте, включен ли Hyper-V
Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V

# Перезапустите Docker службу
Restart-Service Docker
```

### Проблема 2: Dolphin Anty API недоступен

```powershell
# Проверьте, запущен ли Dolphin Anty
Get-Process | Where-Object {$_.ProcessName -like "*dolphin*"}

# Проверьте порт 3001
Test-NetConnection -ComputerName localhost -Port 3001
```

### Проблема 3: Браузер не запускается в контейнере

```powershell
# Проверьте настройки виртуального дисплея
docker-compose -f docker-compose.windows.yml exec web echo $DISPLAY

# Перестройте контейнер с обновленным Dockerfile
docker-compose -f docker-compose.windows.yml build --no-cache
```

### Проблема 4: Недостаточно памяти

```powershell
# Увеличьте лимиты памяти в docker-compose.windows.yml
# Закройте другие ресурсоемкие приложения
# Перезапустите контейнер:
docker-compose -f docker-compose.windows.yml restart
```

## 📊 Мониторинг производительности

### Создайте скрипт мониторинга `monitor.ps1`:

```powershell
# monitor.ps1
while ($true) {
    Clear-Host
    Write-Host "=== Instagram Uploader Monitoring ===" -ForegroundColor Green
    Write-Host "Time: $(Get-Date)" -ForegroundColor Yellow
    
    # Docker контейнер
    Write-Host "`nContainer Status:" -ForegroundColor Cyan
    docker-compose -f docker-compose.windows.yml ps
    
    # Использование ресурсов
    Write-Host "`nResource Usage:" -ForegroundColor Cyan
    docker stats --no-stream
    
    # Логи (последние 10 строк)
    Write-Host "`nRecent Logs:" -ForegroundColor Cyan
    docker-compose -f docker-compose.windows.yml logs --tail=10
    
    Start-Sleep -Seconds 30
}
```

## 🔐 Безопасность для продакшн среды

### 1. Настройка SSL/HTTPS

```powershell
# Используйте reverse proxy (nginx или IIS) для SSL
# Настройте сертификаты Let's Encrypt или корпоративные
```

### 2. Firewall настройки

```powershell
# Откройте только необходимые порты
New-NetFirewallRule -DisplayName "Instagram Uploader" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow

# Заблокируйте прямой доступ к Dolphin Anty извне
New-NetFirewallRule -DisplayName "Block Dolphin API" -Direction Inbound -Protocol TCP -LocalPort 3001 -Action Block -RemoteAddress !127.0.0.1
```

### 3. Backup автоматизация

Создайте `backup.ps1`:

```powershell
$backupDir = "C:\backups\instagram_uploader"
$date = Get-Date -Format "yyyy-MM-dd_HH-mm"

# Создайте директорию если не существует
if (!(Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir
}

# Остановите контейнер
docker-compose -f docker-compose.windows.yml stop

# Скопируйте данные
Copy-Item "db.sqlite3" "$backupDir\db_$date.sqlite3"
Copy-Item "media" "$backupDir\media_$date" -Recurse
Copy-Item ".env" "$backupDir\env_$date.txt"

# Запустите контейнер
docker-compose -f docker-compose.windows.yml start

Write-Host "Backup completed: $backupDir" -ForegroundColor Green
```

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи**: `docker-compose -f docker-compose.windows.yml logs`
2. **Проверьте ресурсы**: `docker stats`
3. **Проверьте Dolphin Anty**: Убедитесь, что API доступен
4. **Перезапустите сервисы**: `docker-compose -f docker-compose.windows.yml restart`

## 🎯 Заключение

После выполнения всех шагов у вас будет:

✅ **Работающий Instagram Uploader на Windows сервере**
✅ **Интеграция с Dolphin Anty**
✅ **Автоматический запуск при старте системы**
✅ **Мониторинг и логирование**
✅ **Автоматическое резервное копирование**

Система готова к работе 24/7 на вашем Windows сервере! 