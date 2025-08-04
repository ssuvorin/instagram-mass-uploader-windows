@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Цвета для вывода
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "CYAN=[96m"
set "RESET=[0m"

echo %CYAN%🔧 Полная настройка Instagram Mass Uploader для Windows%RESET%
echo ================================================
echo.

:: Проверка системных требований
echo %CYAN%Проверка системных требований...%RESET%

:: Проверка Windows версии
for /f "tokens=4-5" %%a in ('ver') do set WINDOWS_VERSION=%%a %%b
echo %GREEN%✅ Windows версия: %WINDOWS_VERSION%%RESET%

:: Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Python не найден!%RESET%
    echo Установите Python 3.8+ с https://www.python.org/downloads/
    echo Убедитесь что отмечена опция "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %GREEN%✅ Python: %PYTHON_VERSION%%RESET%

:: Проверка pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ pip не найден!%RESET%
    pause
    exit /b 1
)
echo %GREEN%✅ pip найден%RESET%

:: Проверка Git
git --version >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️  Git не найден (опционально)%RESET%
) else (
    for /f "tokens=3" %%i in ('git --version 2^>^&1') do set GIT_VERSION=%%i
    echo %GREEN%✅ Git: %GIT_VERSION%%RESET%
)

:: Проверка Dolphin Anty
echo %CYAN%Проверка Dolphin Anty...%RESET%
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:3001/v1.0/browser_profiles' -TimeoutSec 5; Write-Host 'Dolphin Anty доступен' } catch { Write-Host 'Dolphin Anty недоступен' }" 2>nul
if errorlevel 1 (
    echo %YELLOW%⚠️  Dolphin Anty недоступен%RESET%
    echo Установите Dolphin Anty с https://dolphin-anty.com/
    echo Убедитесь что Local API включен на порту 3001
) else (
    echo %GREEN%✅ Dolphin Anty доступен%RESET%
)

:: Создание структуры проекта
echo.
echo %CYAN%Создание структуры проекта...%RESET%

:: Создание директорий
set DIRECTORIES=logs media staticfiles prepared_videos temp
for %%d in (%DIRECTORIES%) do (
    if not exist "%%d" (
        mkdir "%%d"
        echo %GREEN%✅ Создана директория: %%d%RESET%
    ) else (
        echo %GREEN%✅ Директория существует: %%d%RESET%
    )
)

:: Создание виртуального окружения
echo.
echo %CYAN%Настройка виртуального окружения...%RESET%
if exist "venv" (
    echo %YELLOW%⚠️  Виртуальное окружение уже существует%RESET%
    set /p choice="Пересоздать? (y/N): "
    if /i "!choice!"=="y" (
        echo %CYAN%Удаление старого виртуального окружения...%RESET%
        rmdir /s /q venv
        echo %GREEN%✅ Старое виртуальное окружение удалено%RESET%
    ) else (
        goto :install_deps
    )
)

python -m venv venv
if errorlevel 1 (
    echo %RED%❌ Ошибка создания виртуального окружения%RESET%
    pause
    exit /b 1
)
echo %GREEN%✅ Виртуальное окружение создано%RESET%

:install_deps
:: Активация виртуального окружения
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
echo %GREEN%✅ pip обновлен%RESET%

:: Установка зависимостей
echo.
echo %CYAN%Установка зависимостей...%RESET%
echo Выберите версию зависимостей:
echo 1. requirements-windows.txt (полная версия - рекомендуется)
echo 2. requirements-windows-minimal.txt (минимальная версия)
echo 3. requirements.txt (основная версия)
echo.
set /p choice="Введите номер (1-3): "

if "!choice!"=="1" (
    set REQUIREMENTS_FILE=requirements-windows.txt
    echo %GREEN%Выбрана полная версия%RESET%
) else if "!choice!"=="2" (
    set REQUIREMENTS_FILE=requirements-windows-minimal.txt
    echo %GREEN%Выбрана минимальная версия%RESET%
) else if "!choice!"=="3" (
    set REQUIREMENTS_FILE=requirements.txt
    echo %GREEN%Выбрана основная версия%RESET%
) else (
    set REQUIREMENTS_FILE=requirements-windows.txt
    echo %YELLOW%Используется файл по умолчанию%RESET%
)

echo %CYAN%Установка зависимостей из %REQUIREMENTS_FILE%...%RESET%
echo %YELLOW%Это может занять 5-10 минут...%RESET%
echo.

pip install -r %REQUIREMENTS_FILE%
if errorlevel 1 (
    echo %RED%❌ Ошибка установки зависимостей%RESET%
    echo.
    echo %YELLOW%Возможные решения:%RESET%
    echo 1. Установите Visual C++ Build Tools
    echo 2. Обновите pip: python -m pip install --upgrade pip
    echo 3. Попробуйте другую версию Python
    echo 4. Установите Microsoft Visual C++ Redistributable
    echo.
    pause
    exit /b 1
)

echo %GREEN%✅ Зависимости установлены%RESET%

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

:: Настройка конфигурации
echo.
echo %CYAN%Настройка конфигурации...%RESET%

:: Создание .env файла
if not exist ".env" (
    if exist "windows_deployment.env.example" (
        copy "windows_deployment.env.example" ".env"
        echo %GREEN%✅ Файл .env создан из примера%RESET%
    ) else (
        echo SECRET_KEY=django-insecure-change-this-in-production > .env
        echo DEBUG=True >> .env
        echo ALLOWED_HOSTS=localhost,127.0.0.1 >> .env
        echo DOLPHIN_API_HOST=http://localhost:3001/v1.0 >> .env
        echo %GREEN%✅ Базовый .env файл создан%RESET%
    )
) else (
    echo %GREEN%✅ Файл .env найден%RESET%
)

:: Создание базы данных
echo %CYAN%Настройка базы данных...%RESET%
if not exist "db.sqlite3" (
    python manage.py migrate
    if errorlevel 1 (
        echo %RED%❌ Ошибка создания базы данных%RESET%
        pause
        exit /b 1
    )
    echo %GREEN%✅ База данных создана%RESET%
    
    :: Создание суперпользователя
    echo.
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

:: Проверка установки
echo.
echo %CYAN%Проверка установки...%RESET%
python -c "import django; print('✅ Django:', django.get_version())"
python -c "import playwright; print('✅ Playwright:', playwright.__version__)"
python -c "import requests; print('✅ Requests:', requests.__version__)"
python -c "import psutil; print('✅ psutil:', psutil.__version__)"

:: Создание ярлыков
echo.
echo %CYAN%Создание ярлыков...%RESET%

:: Ярлык для быстрого запуска
echo @echo off > quick_start.bat
echo chcp 65001 ^>nul >> quick_start.bat
echo call venv\Scripts\activate.bat >> quick_start.bat
echo python manage.py runserver 0.0.0.0:8000 >> quick_start.bat
echo %GREEN%✅ Создан quick_start.bat%RESET%

:: Ярлык для админ-панели
echo @echo off > admin_panel.bat
echo chcp 65001 ^>nul >> admin_panel.bat
echo call venv\Scripts\activate.bat >> admin_panel.bat
echo start http://localhost:8000/admin >> admin_panel.bat
echo python manage.py runserver 0.0.0.0:8000 >> admin_panel.bat
echo %GREEN%✅ Создан admin_panel.bat%RESET%

:: Финальная информация
echo.
echo %GREEN%🎉 Настройка завершена успешно!%RESET%
echo.
echo %CYAN%📋 Следующие шаги:%RESET%
echo 1. Отредактируйте файл .env с вашими настройками
echo 2. Запустите quick_start.bat для быстрого старта
echo 3. Откройте http://localhost:8000 в браузере
echo 4. Для админ-панели используйте admin_panel.bat
echo.
echo %CYAN%🔧 Полезные команды:%RESET%
echo - quick_start.bat - быстрый запуск
echo - admin_panel.bat - запуск с админ-панелью
echo - python manage.py createsuperuser - создать админа
echo - python manage.py shell - Django shell
echo.
echo %CYAN%📞 Поддержка:%RESET%
echo При проблемах проверьте:
echo - Логи в папке logs/
echo - Настройки в файле .env
echo - Доступность Dolphin Anty API
echo.
pause 