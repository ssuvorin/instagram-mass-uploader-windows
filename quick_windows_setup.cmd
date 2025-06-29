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
docker-compose -f docker-compose.windows.simple.yml down
docker-compose -f docker-compose.windows.simple.yml up -d --build
goto check_status

:full_build
echo 🔨 Building with full configuration...
docker-compose -f docker-compose.windows.yml down
docker-compose -f docker-compose.windows.yml up -d --build
goto check_status

:check_status
echo.
echo ⏳ Waiting for application to start...
timeout /t 10 /nobreak >nul

echo 🔍 Checking container status...
docker ps

echo.
echo 📊 Checking logs...
if "%choice%"=="1" (
    docker-compose -f docker-compose.windows.simple.yml logs --tail=20 web
) else (
    docker-compose -f docker-compose.windows.yml logs --tail=20 web
)

echo.
echo 🎉 Setup completed!
echo 📋 Access your application at: http://localhost:8000
echo.
echo 🔧 Useful commands:
echo   Stop:    docker-compose -f docker-compose.windows.simple.yml down
echo   Start:   docker-compose -f docker-compose.windows.simple.yml up -d
echo   Logs:    docker-compose -f docker-compose.windows.simple.yml logs -f
echo.
pause 