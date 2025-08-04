@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Цвета для вывода
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "CYAN=[96m"
set "RESET=[0m"

echo %CYAN%🚀 Instagram Mass Uploader - Windows Launcher%RESET%
echo ================================================
echo.

:: Проверка Python
echo %CYAN%Проверка Python...%RESET%
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Python не найден! Установите Python 3.8+%RESET%
    echo Скачайте с: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %GREEN%✅ Python найден: %PYTHON_VERSION%%RESET%

:: Проверка pip
echo %CYAN%Проверка pip...%RESET%
pip --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ pip не найден!%RESET%
    pause
    exit /b 1
)
echo %GREEN%✅ pip найден%RESET%

:: Проверка виртуального окружения
echo %CYAN%Проверка виртуального окружения...%RESET%
if not exist "venv" (
    echo %YELLOW%⚠️  Виртуальное окружение не найдено. Создаю...%RESET%
    python -m venv venv
    if errorlevel 1 (
        echo %RED%❌ Ошибка создания виртуального окружения%RESET%
        pause
        exit /b 1
    )
    echo %GREEN%✅ Виртуальное окружение создано%RESET%
) else (
    echo %GREEN%✅ Виртуальное окружение найдено%RESET%
)

:: Активация виртуального окружения
echo %CYAN%Активация виртуального окружения...%RESET%
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo %RED%❌ Ошибка активации виртуального окружения%RESET%
    pause
    exit /b 1
)
echo %GREEN%✅ Виртуальное окружение активировано%RESET%

:: Проверка зависимостей
echo %CYAN%Проверка зависимостей...%RESET%
pip list | findstr "Django" >nul
if errorlevel 1 (
    echo %YELLOW%⚠️  Зависимости не установлены. Устанавливаю...%RESET%
    
    :: Выбор файла зависимостей
    echo Выберите файл зависимостей:
    echo 1. requirements-windows.txt (полная версия)
    echo 2. requirements-windows-minimal.txt (минимальная версия)
    echo 3. requirements.txt (основная версия)
    set /p choice="Введите номер (1-3): "
    
    if "!choice!"=="1" (
        set REQUIREMENTS_FILE=requirements-windows.txt
    ) else if "!choice!"=="2" (
        set REQUIREMENTS_FILE=requirements-windows-minimal.txt
    ) else if "!choice!"=="3" (
        set REQUIREMENTS_FILE=requirements.txt
    ) else (
        set REQUIREMENTS_FILE=requirements-windows.txt
        echo %YELLOW%Используется файл по умолчанию: requirements-windows.txt%RESET%
    )
    
    echo %CYAN%Установка зависимостей из %REQUIREMENTS_FILE%...%RESET%
    pip install -r %REQUIREMENTS_FILE%
    if errorlevel 1 (
        echo %RED%❌ Ошибка установки зависимостей%RESET%
        echo Попробуйте обновить pip: python -m pip install --upgrade pip
        pause
        exit /b 1
    )
    echo %GREEN%✅ Зависимости установлены%RESET%
) else (
    echo %GREEN%✅ Зависимости уже установлены%RESET%
)

:: Установка Playwright браузеров
echo %CYAN%Проверка Playwright браузеров...%RESET%
playwright install --help >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️  Playwright браузеры не установлены. Устанавливаю...%RESET%
    playwright install
    if errorlevel 1 (
        echo %RED%❌ Ошибка установки Playwright браузеров%RESET%
        pause
        exit /b 1
    )
    echo %GREEN%✅ Playwright браузеры установлены%RESET%
) else (
    echo %GREEN%✅ Playwright браузеры найдены%RESET%
)

:: Проверка файла .env
echo %CYAN%Проверка конфигурации...%RESET%
if not exist ".env" (
    echo %YELLOW%⚠️  Файл .env не найден%RESET%
    if exist "windows_deployment.env.example" (
        echo %CYAN%Копирование примера конфигурации...%RESET%
        copy "windows_deployment.env.example" ".env"
        echo %GREEN%✅ Файл .env создан из примера%RESET%
        echo %YELLOW%⚠️  Отредактируйте файл .env перед использованием%RESET%
    ) else (
        echo %YELLOW%⚠️  Создание базового .env файла...%RESET%
        echo SECRET_KEY=django-insecure-change-this-in-production > .env
        echo DEBUG=True >> .env
        echo ALLOWED_HOSTS=localhost,127.0.0.1 >> .env
        echo %GREEN%✅ Базовый .env файл создан%RESET%
    )
) else (
    echo %GREEN%✅ Файл .env найден%RESET%
)

:: Создание необходимых директорий
echo %CYAN%Создание директорий...%RESET%
if not exist "logs" mkdir logs
if not exist "media" mkdir media
if not exist "staticfiles" mkdir staticfiles
if not exist "prepared_videos" mkdir prepared_videos
echo %GREEN%✅ Директории созданы%RESET%

:: Проверка базы данных
echo %CYAN%Проверка базы данных...%RESET%
if not exist "db.sqlite3" (
    echo %YELLOW%⚠️  База данных не найдена. Создаю...%RESET%
    python manage.py migrate
    if errorlevel 1 (
        echo %RED%❌ Ошибка создания базы данных%RESET%
        pause
        exit /b 1
    )
    echo %GREEN%✅ База данных создана%RESET%
    
    :: Создание суперпользователя
    echo %CYAN%Создание суперпользователя...%RESET%
    echo Создайте суперпользователя для доступа к админ-панели:
    python manage.py createsuperuser
) else (
    echo %GREEN%✅ База данных найдена%RESET%
)

:: Сбор статических файлов
echo %CYAN%Сбор статических файлов...%RESET%
python manage.py collectstatic --noinput
if errorlevel 1 (
    echo %YELLOW%⚠️  Ошибка сбора статических файлов (продолжаем)%RESET%
) else (
    echo %GREEN%✅ Статические файлы собраны%RESET%
)

:: Проверка Dolphin Anty
echo %CYAN%Проверка Dolphin Anty...%RESET%
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:3001/v1.0/browser_profiles' -TimeoutSec 5; Write-Host 'Dolphin Anty доступен' } catch { Write-Host 'Dolphin Anty недоступен' }" 2>nul
if errorlevel 1 (
    echo %YELLOW%⚠️  Dolphin Anty недоступен на localhost:3001%RESET%
    echo Убедитесь что Dolphin Anty запущен и Local API включен
) else (
    echo %GREEN%✅ Dolphin Anty доступен%RESET%
)

:: Запуск сервера
echo.
echo %CYAN%🚀 Запуск Instagram Mass Uploader...%RESET%
echo.
echo %GREEN%✅ Система готова к работе!%RESET%
echo.
echo %CYAN%Веб-интерфейс будет доступен по адресу:%RESET%
echo %YELLOW%http://localhost:8000%RESET%
echo.
echo %CYAN%Для остановки сервера нажмите Ctrl+C%RESET%
echo.

:: Запуск Django сервера
python manage.py runserver 0.0.0.0:8000

:: Обработка выхода
echo.
echo %YELLOW%⚠️  Сервер остановлен%RESET%
pause 