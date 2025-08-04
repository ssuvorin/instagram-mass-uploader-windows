@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Цвета для вывода
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "CYAN=[96m"
set "RESET=[0m"

echo %CYAN%⚡ Быстрый старт Instagram Mass Uploader%RESET%
echo ================================================
echo.

:: Активация виртуального окружения
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo %GREEN%✅ Виртуальное окружение активировано%RESET%
) else (
    echo %RED%❌ Виртуальное окружение не найдено%RESET%
    echo Запустите install_dependencies.bat для установки
    pause
    exit /b 1
)

:: Проверка зависимостей
python -c "import django" >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Django не установлен%RESET%
    echo Запустите install_dependencies.bat для установки зависимостей
    pause
    exit /b 1
)

:: Проверка .env файла
if not exist ".env" (
    echo %YELLOW%⚠️  Файл .env не найден%RESET%
    if exist "windows_deployment.env.example" (
        copy "windows_deployment.env.example" ".env"
        echo %GREEN%✅ Файл .env создан из примера%RESET%
    ) else (
        echo SECRET_KEY=django-insecure-change-this-in-production > .env
        echo DEBUG=True >> .env
        echo ALLOWED_HOSTS=localhost,127.0.0.1 >> .env
        echo %GREEN%✅ Базовый .env файл создан%RESET%
    )
)

:: Создание директорий
if not exist "logs" mkdir logs
if not exist "media" mkdir media
if not exist "staticfiles" mkdir staticfiles
if not exist "prepared_videos" mkdir prepared_videos

:: Миграции базы данных
if not exist "db.sqlite3" (
    echo %CYAN%Создание базы данных...%RESET%
    python manage.py migrate
    echo %GREEN%✅ База данных создана%RESET%
)

:: Сбор статических файлов
python manage.py collectstatic --noinput >nul 2>&1

:: Запуск сервера
echo.
echo %CYAN%🚀 Запуск сервера...%RESET%
echo %GREEN%✅ Веб-интерфейс: http://localhost:8000%RESET%
echo %CYAN%Для остановки нажмите Ctrl+C%RESET%
echo.

python manage.py runserver 0.0.0.0:8000

echo.
echo %YELLOW%⚠️  Сервер остановлен%RESET%
pause 