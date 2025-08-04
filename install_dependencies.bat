@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Цвета для вывода
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "CYAN=[96m"
set "RESET=[0m"

echo %CYAN%📦 Установка зависимостей Instagram Mass Uploader%RESET%
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

:: Создание виртуального окружения
echo %CYAN%Создание виртуального окружения...%RESET%
if exist "venv" (
    echo %YELLOW%⚠️  Виртуальное окружение уже существует%RESET%
    set /p choice="Пересоздать? (y/N): "
    if /i "!choice!"=="y" (
        echo %CYAN%Удаление старого виртуального окружения...%RESET%
        rmdir /s /q venv
        echo %GREEN%✅ Старое виртуальное окружение удалено%RESET%
    ) else (
        echo %YELLOW%Используется существующее виртуальное окружение%RESET%
        goto :activate_venv
    )
)

python -m venv venv
if errorlevel 1 (
    echo %RED%❌ Ошибка создания виртуального окружения%RESET%
    pause
    exit /b 1
)
echo %GREEN%✅ Виртуальное окружение создано%RESET%

:activate_venv
:: Активация виртуального окружения
echo %CYAN%Активация виртуального окружения...%RESET%
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo %RED%❌ Ошибка активации виртуального окружения%RESET%
    pause
    exit /b 1
)
echo %GREEN%✅ Виртуальное окружение активировано%RESET%

:: Обновление pip
echo %CYAN%Обновление pip...%RESET%
python -m pip install --upgrade pip
if errorlevel 1 (
    echo %YELLOW%⚠️  Ошибка обновления pip (продолжаем)%RESET%
) else (
    echo %GREEN%✅ pip обновлен%RESET%
)

:: Выбор файла зависимостей
echo.
echo %CYAN%Выберите файл зависимостей:%RESET%
echo 1. requirements-windows.txt (полная версия - рекомендуется)
echo 2. requirements-windows-minimal.txt (минимальная версия)
echo 3. requirements.txt (основная версия)
echo.
set /p choice="Введите номер (1-3): "

if "!choice!"=="1" (
    set REQUIREMENTS_FILE=requirements-windows.txt
    echo %GREEN%Выбрана полная версия зависимостей%RESET%
) else if "!choice!"=="2" (
    set REQUIREMENTS_FILE=requirements-windows-minimal.txt
    echo %GREEN%Выбрана минимальная версия зависимостей%RESET%
) else if "!choice!"=="3" (
    set REQUIREMENTS_FILE=requirements.txt
    echo %GREEN%Выбрана основная версия зависимостей%RESET%
) else (
    set REQUIREMENTS_FILE=requirements-windows.txt
    echo %YELLOW%Используется файл по умолчанию: requirements-windows.txt%RESET%
)

:: Установка зависимостей
echo.
echo %CYAN%Установка зависимостей из %REQUIREMENTS_FILE%...%RESET%
echo %YELLOW%Это может занять несколько минут...%RESET%
echo.

pip install -r %REQUIREMENTS_FILE%
if errorlevel 1 (
    echo %RED%❌ Ошибка установки зависимостей%RESET%
    echo.
    echo %YELLOW%Возможные решения:%RESET%
    echo 1. Обновите pip: python -m pip install --upgrade pip
    echo 2. Установите Visual C++ Build Tools
    echo 3. Попробуйте другую версию Python
    echo.
    pause
    exit /b 1
)

echo %GREEN%✅ Зависимости установлены успешно%RESET%

:: Установка Playwright браузеров
echo.
echo %CYAN%Установка Playwright браузеров...%RESET%
echo %YELLOW%Это может занять несколько минут...%RESET%
echo.

playwright install
if errorlevel 1 (
    echo %RED%❌ Ошибка установки Playwright браузеров%RESET%
    echo Попробуйте установить вручную: playwright install
    pause
    exit /b 1
)

echo %GREEN%✅ Playwright браузеры установлены%RESET%

:: Проверка установки
echo.
echo %CYAN%Проверка установки...%RESET%
python -c "import django; print('Django:', django.get_version())"
python -c "import playwright; print('Playwright:', playwright.__version__)"
python -c "import requests; print('Requests:', requests.__version__)"

echo.
echo %GREEN%🎉 Установка завершена успешно!%RESET%
echo.
echo %CYAN%Следующие шаги:%RESET%
echo 1. Запустите start_project.bat для запуска проекта
echo 2. Настройте файл .env с вашими параметрами
echo 3. Откройте http://localhost:8000 в браузере
echo.
pause 