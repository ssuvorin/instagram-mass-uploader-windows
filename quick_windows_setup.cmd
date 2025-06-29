@echo off
REM =============================================================================
REM БЫСТРАЯ УСТАНОВКА INSTAGRAM UPLOADER НА WINDOWS
REM =============================================================================

echo 🚀 Instagram Mass Uploader - Quick Windows Setup
echo.

REM Проверяем Docker
echo 🔍 Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker not found! Please install Docker Desktop first.
    echo 📋 Download: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo ✅ Docker found

REM Проверяем Git
echo 🔍 Checking Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Git not found! Please install Git first.
    echo 📋 Download: https://git-scm.com/download/win
    pause
    exit /b 1
)
echo ✅ Git found

REM Создаем .env файл если его нет
if not exist "windows_deployment.env" (
    echo 📝 Creating environment file...
    copy windows_deployment.env.example windows_deployment.env
    echo ⚠️ ВАЖНО: Отредактируйте windows_deployment.env файл!
    echo ⚠️ Укажите ваш DOLPHIN_API_TOKEN и другие настройки
    notepad windows_deployment.env
    pause
)

REM Создаем необходимые директории и файлы
echo 📁 Creating necessary directories...
if not exist "logs" mkdir logs
if not exist "media" mkdir media
if not exist "static" mkdir static
if not exist "staticfiles" mkdir staticfiles

REM Создаем пустую базу данных если её нет
if not exist "db.sqlite3" (
    echo 📊 Creating empty database file...
    echo. > db.sqlite3
)

REM Выбор версии сборки
echo.
echo 🔧 Choose build option:
echo [1] Simple build (recommended for first time)
echo [2] Full build (with all features)
echo.
set /p choice=Enter choice (1 or 2): 

if "%choice%"=="1" goto simple_build
if "%choice%"=="2" goto full_build
echo Invalid choice, using simple build...

:simple_build
echo 🔨 Building with simple configuration...
echo 🛑 Stopping existing containers...
docker-compose -f docker-compose.windows.simple.yml down

echo 🗑️ Cleaning up old images...
docker system prune -f

echo 🔨 Building new image...
docker-compose -f docker-compose.windows.simple.yml build --no-cache

echo 🚀 Starting application...
docker-compose -f docker-compose.windows.simple.yml up -d
goto check_status

:full_build
echo 🔨 Building with full configuration...
echo 🛑 Stopping existing containers...
docker-compose -f docker-compose.windows.yml down

echo 🔨 Building new image...
docker-compose -f docker-compose.windows.yml build --no-cache

echo 🚀 Starting application...
docker-compose -f docker-compose.windows.yml up -d
goto check_status

:check_status
echo.
echo ⏳ Waiting for application to start...
timeout /t 15 /nobreak >nul

echo 🔍 Checking container status...
docker ps

echo.
echo 📊 Checking detailed logs...
if "%choice%"=="1" (
    echo === SIMPLE BUILD LOGS ===
    docker-compose -f docker-compose.windows.simple.yml logs --tail=50 web
    echo.
    echo 🔧 Container info:
    docker-compose -f docker-compose.windows.simple.yml ps
) else (
    echo === FULL BUILD LOGS ===
    docker-compose -f docker-compose.windows.yml logs --tail=50 web
    echo.
    echo 🔧 Container info:
    docker-compose -f docker-compose.windows.yml ps
)

echo.
echo 📁 Checking file permissions...
dir db.sqlite3 logs media

echo.
echo 🎉 Setup completed!
echo 📋 Access your application at: http://localhost:8000
echo 👤 Default login: admin / admin123
echo.
echo 🔧 Useful commands:
if "%choice%"=="1" (
    echo   Stop:    docker-compose -f docker-compose.windows.simple.yml down
    echo   Start:   docker-compose -f docker-compose.windows.simple.yml up -d
    echo   Logs:    docker-compose -f docker-compose.windows.simple.yml logs -f
    echo   Shell:   docker-compose -f docker-compose.windows.simple.yml exec web bash
) else (
    echo   Stop:    docker-compose -f docker-compose.windows.yml down
    echo   Start:   docker-compose -f docker-compose.windows.yml up -d
    echo   Logs:    docker-compose -f docker-compose.windows.yml logs -f
    echo   Shell:   docker-compose -f docker-compose.windows.yml exec web bash
)
echo.
echo 🐛 If you see database errors, run:
echo   docker-compose -f docker-compose.windows.simple.yml exec web python manage.py migrate
echo.
pause 