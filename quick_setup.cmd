@echo off
REM =============================================================================
REM БЫСТРАЯ НАСТРОЙКА INSTAGRAM UPLOADER - WINDOWS
REM =============================================================================

echo 🚀 Instagram Mass Uploader - Quick Setup
echo.

echo 📋 Step 1: Setting up environment file...
if not exist ".env" (
    if exist "windows_deployment.env.example" (
        copy windows_deployment.env.example .env
        echo ✅ Created .env file from example
    ) else (
        echo ❌ windows_deployment.env.example not found!
        echo Please download the complete project from GitHub
        pause
        exit /b 1
    )
) else (
    echo ✅ .env file already exists
)

echo.
echo ⚙️ Step 2: Configure your settings in .env file
echo 📝 Edit .env with your settings:
echo   - DOLPHIN_API_TOKEN=your-dolphin-token
echo   - RUCAPTCHA_API_KEY=your-captcha-key
echo   - SECRET_KEY=your-secret-key
echo.
echo 🔧 Opening .env file for editing...
timeout /t 3 /nobreak >nul
notepad .env

echo.
echo 📊 Step 3: Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker not found! Please install Docker Desktop first.
    pause
    exit /b 1
) else (
    echo ✅ Docker is available
)

echo.
echo 🧹 Step 4: Cleaning up old containers...
docker-compose -f docker-compose.windows.simple.yml down 2>nul

echo 🗑️ Removing old containers and images...
docker container prune -f >nul 2>&1
docker image prune -f >nul 2>&1
docker volume rm instagram-mass-uploader-windows_db_data 2>nul

echo.
echo 📁 Step 5: Creating directories...
if not exist "logs" mkdir logs
if not exist "media" mkdir media
if not exist "staticfiles" mkdir staticfiles

echo.
echo 🔨 Step 6: Building application...
docker-compose -f docker-compose.windows.simple.yml build --no-cache

echo.
echo 🚀 Step 7: Starting application...
docker-compose -f docker-compose.windows.simple.yml up -d

echo.
echo ⏳ Waiting for application to start...
timeout /t 20 /nobreak >nul

echo.
echo 📋 Checking application status...
docker-compose -f docker-compose.windows.simple.yml ps

echo.
echo 📊 Recent logs:
docker-compose -f docker-compose.windows.simple.yml logs --tail=15 web

echo.
echo 🎉 Setup completed!
echo.
echo 📋 Access your application at: http://localhost:8000
echo 👤 Default login: admin / admin123
echo.
echo 🔧 Useful commands:
echo   Status:  check_status.cmd
echo   Logs:    docker-compose -f docker-compose.windows.simple.yml logs -f
echo   Stop:    docker-compose -f docker-compose.windows.simple.yml down
echo   Restart: restart_clean.cmd
echo.
echo 📞 If you have issues, check TROUBLESHOOTING.md
echo.
pause 