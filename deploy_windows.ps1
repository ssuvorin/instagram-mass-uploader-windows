# Instagram Uploader - Windows Deployment Script
# Автоматизированное развертывание на Windows сервере

param(
    [string]$DolphinToken = "",
    [string]$RuCaptchaKey = "",
    [string]$ServerIP = "localhost",
    [switch]$SkipDolphinCheck,
    [switch]$Production
)

# Цвета для вывода
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"

function Write-Status {
    param([string]$Message, [string]$Color = $Green)
    Write-Host "✅ $Message" -ForegroundColor $Color
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor $Cyan
}

Write-Host @"

🚀 Instagram Mass Uploader - Windows Deployment
===============================================

Этот скрипт поможет развернуть систему на Windows сервере.

"@ -ForegroundColor $Cyan

# 1. Проверка требований
Write-Info "Проверка системных требований..."

# Проверка Windows версии
$windowsVersion = (Get-WmiObject -Class Win32_OperatingSystem).Caption
Write-Info "Версия Windows: $windowsVersion"

# Проверка PowerShell версии
$psVersion = $PSVersionTable.PSVersion
if ($psVersion.Major -lt 5) {
    Write-Error "Требуется PowerShell 5.1 или выше. Текущая версия: $psVersion"
    exit 1
}
Write-Status "PowerShell версия: $psVersion"

# Проверка Docker
Write-Info "Проверка Docker..."
try {
    $dockerVersion = docker --version
    Write-Status "Docker найден: $dockerVersion"
} catch {
    Write-Error "Docker не найден! Установите Docker Desktop for Windows"
    Write-Info "Скачайте с: https://docs.docker.com/desktop/install/windows-install/"
    exit 1
}

try {
    $composeVersion = docker-compose --version
    Write-Status "Docker Compose найден: $composeVersion"
} catch {
    Write-Error "Docker Compose не найден!"
    exit 1
}

# Проверка Dolphin Anty (если не пропущена)
if (-not $SkipDolphinCheck) {
    Write-Info "Проверка Dolphin Anty..."
    
    # Try localhost first (for host), then host.docker.internal (for Docker)
    $dolphinHosts = @(
        "http://localhost:3001/v1.0/browser_profiles",
        "http://host.docker.internal:3001/v1.0/browser_profiles"
    )
    
    $dolphinAvailable = $false
    foreach ($url in $dolphinHosts) {
        try {
            $response = Invoke-WebRequest -Uri $url -TimeoutSec 5 -ErrorAction Stop
            Write-Status "Dolphin Anty API доступен: $url"
            $dolphinAvailable = $true
            break
        } catch {
            # Continue to next URL
        }
    }
    
    if (-not $dolphinAvailable) {
        Write-Warning "Dolphin Anty API недоступен на стандартных портах"
        Write-Info "Проверьте что Dolphin Anty запущен и Local API включен на порту 3001"
        Write-Info "Для Docker развертывания убедитесь что переменная DOLPHIN_API_HOST установлена в http://host.docker.internal:3001"
        
        $continue = Read-Host "Продолжить без Dolphin Anty? (y/N)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            exit 1
        }
    }
}

# 2. Настройка переменных окружения
Write-Info "Настройка переменных окружения..."

if (-not (Test-Path ".env")) {
    if (Test-Path "windows_deployment.env.example") {
        Copy-Item "windows_deployment.env.example" ".env"
        Write-Status "Создан файл .env из примера"
    } else {
        Write-Warning "Файл windows_deployment.env.example не найден"
        Write-Info "Создание базового .env файла..."
        
        $envContent = @"
SECRET_KEY=$(New-Guid)
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,$ServerIP
DOLPHIN_API_TOKEN=$DolphinToken
RUCAPTCHA_API_KEY=$RuCaptchaKey
TZ=Europe/Moscow
MAX_CONCURRENT_TASKS=2
"@
        Set-Content -Path ".env" -Value $envContent
        Write-Status "Создан базовый .env файл"
    }
} else {
    Write-Status "Файл .env уже существует"
}

# Обновление .env файла с переданными параметрами
if ($DolphinToken) {
    (Get-Content ".env") -replace "DOLPHIN_API_TOKEN=.*", "DOLPHIN_API_TOKEN=$DolphinToken" | Set-Content ".env"
    Write-Status "Обновлен DOLPHIN_API_TOKEN"
}

if ($RuCaptchaKey) {
    (Get-Content ".env") -replace "RUCAPTCHA_API_KEY=.*", "RUCAPTCHA_API_KEY=$RuCaptchaKey" | Set-Content ".env"
    Write-Status "Обновлен RUCAPTCHA_API_KEY"
}

if ($ServerIP -ne "localhost") {
    $currentHosts = (Get-Content ".env" | Select-String "ALLOWED_HOSTS=").ToString()
    if ($currentHosts -notlike "*$ServerIP*") {
        (Get-Content ".env") -replace "ALLOWED_HOSTS=(.*)", "ALLOWED_HOSTS=`$1,$ServerIP" | Set-Content ".env"
        Write-Status "Добавлен IP сервера в ALLOWED_HOSTS"
    }
}

# 3. Создание необходимых директорий
Write-Info "Создание директорий..."

$directories = @("logs", "temp", "media", "staticfiles", "prepared_videos")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Status "Создана директория: $dir"
    }
}

# 4. Сборка Docker образа
Write-Info "Сборка Docker образа..."

$composeFile = if ($Production) { "docker-compose.windows.yml" } else { "docker-compose.yml" }

if (-not (Test-Path $composeFile)) {
    Write-Error "Файл $composeFile не найден!"
    exit 1
}

try {
    Write-Info "Собираем образ... (это может занять несколько минут)"
    docker-compose -f $composeFile build
    Write-Status "Docker образ собран успешно"
} catch {
    Write-Error "Ошибка при сборке Docker образа: $_"
    exit 1
}

# 5. Запуск контейнера
Write-Info "Запуск контейнера..."

try {
    docker-compose -f $composeFile up -d
    Write-Status "Контейнер запущен"
} catch {
    Write-Error "Ошибка при запуске контейнера: $_"
    exit 1
}

# 6. Проверка статуса
Write-Info "Проверка статуса сервисов..."

Start-Sleep -Seconds 10

try {
    $status = docker-compose -f $composeFile ps
    Write-Status "Статус контейнеров:"
    Write-Host $status
} catch {
    Write-Warning "Не удалось получить статус контейнеров"
}

# 7. Проверка доступности веб-интерфейса
Write-Info "Проверка доступности веб-интерфейса..."

$maxAttempts = 30
$attempt = 0
$webAvailable = $false

while ($attempt -lt $maxAttempts -and -not $webAvailable) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000" -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $webAvailable = $true
            Write-Status "Веб-интерфейс доступен на http://localhost:8000"
        }
    } catch {
        $attempt++
        if ($attempt -lt $maxAttempts) {
            Write-Host "." -NoNewline
            Start-Sleep -Seconds 2
        }
    }
}

if (-not $webAvailable) {
    Write-Warning "Веб-интерфейс недоступен после $maxAttempts попыток"
    Write-Info "Проверьте логи: docker-compose -f $composeFile logs"
} else {
    Write-Host ""
}

# 8. Создание скриптов управления
Write-Info "Создание скриптов управления..."

# Скрипт запуска
$startScript = @"
@echo off
echo Starting Instagram Uploader...
cd /d "%~dp0"
docker-compose -f $composeFile up -d
echo Instagram Uploader started successfully!
echo Open http://localhost:8000 in your browser
pause
"@
Set-Content -Path "start.bat" -Value $startScript
Write-Status "Создан скрипт start.bat"

# Скрипт остановки
$stopScript = @"
@echo off
echo Stopping Instagram Uploader...
cd /d "%~dp0"
docker-compose -f $composeFile down
echo Instagram Uploader stopped successfully!
pause
"@
Set-Content -Path "stop.bat" -Value $stopScript
Write-Status "Создан скрипт stop.bat"

# Скрипт просмотра логов
$logsScript = @"
@echo off
echo Instagram Uploader Logs...
cd /d "%~dp0"
docker-compose -f $composeFile logs -f
"@
Set-Content -Path "logs.bat" -Value $logsScript
Write-Status "Создан скрипт logs.bat"

# 9. Создание задачи автозапуска
Write-Info "Настройка автозапуска..."

$taskName = "Instagram_Uploader_AutoStart"
$currentPath = Get-Location
$startBatPath = Join-Path $currentPath "start.bat"

try {
    # Проверяем, существует ли задача
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    
    if ($existingTask) {
        Write-Warning "Задача '$taskName' уже существует"
    } else {
        $action = New-ScheduledTaskAction -Execute $startBatPath
        $trigger = New-ScheduledTaskTrigger -AtStartup
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
        
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Auto-start Instagram Uploader on Windows boot" -ErrorAction Stop
        Write-Status "Создана задача автозапуска в Task Scheduler"
    }
} catch {
    Write-Warning "Не удалось создать задачу автозапуска: $_"
    Write-Info "Вы можете добавить start.bat в автозагрузку Windows вручную"
}

# 10. Финальная информация
Write-Host @"

🎉 РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!
============================

✅ Instagram Uploader запущен и готов к работе
🌐 Веб-интерфейс: http://localhost:8000
📁 Файлы проекта: $currentPath

📋 СЛЕДУЮЩИЕ ШАГИ:

1. Откройте http://localhost:8000 в браузере
2. Создайте аккаунты Instagram в системе
3. Настройте профили Dolphin Anty
4. Загрузите видео для тестирования

🛠️  УПРАВЛЕНИЕ СИСТЕМОЙ:

▶️  Запуск:     start.bat
⏹️  Остановка:  stop.bat
📜 Логи:       logs.bat

🔧 ПОЛЕЗНЫЕ КОМАНДЫ:

docker-compose -f $composeFile ps          # Статус контейнеров
docker-compose -f $composeFile logs -f     # Просмотр логов
docker-compose -f $composeFile restart     # Перезапуск

📞 ПОДДЕРЖКА:

При возникновении проблем проверьте:
1. Логи системы (logs.bat)
2. Доступность Dolphin Anty API (http://localhost:3001)
3. Статус Docker контейнеров

"@ -ForegroundColor $Green

# Предложение открыть браузер
$openBrowser = Read-Host "Открыть веб-интерфейс в браузере? (Y/n)"
if ($openBrowser -ne "n" -and $openBrowser -ne "N") {
    Start-Process "http://localhost:8000"
}

Write-Status "Развертывание успешно завершено!" 