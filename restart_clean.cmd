@echo off
REM =============================================================================
REM ПОЛНАЯ ОЧИСТКА И ПЕРЕЗАПУСК INSTAGRAM UPLOADER
REM =============================================================================

echo 🧹 Instagram Mass Uploader - Complete Clean Restart
echo.

echo 🛑 Stopping all related containers...
docker-compose -f docker-compose.windows.yml down 2>nul
docker-compose -f docker-compose.windows.simple.yml down 2>nul

echo 🔍 Checking for any running containers...
for /f "tokens=1" %%i in ('docker ps -q') do (
    echo Stopping container %%i...
    docker stop %%i
)

echo 🗑️ Removing old containers...
docker container prune -f

echo 🧹 Cleaning up Docker images...
docker image prune -f

echo 📁 Checking local directories...
if not exist "logs" mkdir logs
if not exist "media" mkdir media
if not exist "static" mkdir static
if not exist "staticfiles" mkdir staticfiles

echo 📊 Removing old database volumes...
docker volume rm instagram-mass-uploader-windows_db_data 2>nul

echo 🔨 Building fresh image...
docker-compose -f docker-compose.windows.simple.yml build --no-cache

echo 🚀 Starting application...
docker-compose -f docker-compose.windows.simple.yml up -d

echo.
echo ⏳ Waiting for application to start...
timeout /t 20 /nobreak >nul

echo 📊 Checking application status...
docker-compose -f docker-compose.windows.simple.yml ps

echo.
echo 📋 Application Logs:
docker-compose -f docker-compose.windows.simple.yml logs --tail=30 web

echo.
echo 🎉 Clean restart completed!
echo 📋 Access your application at: http://localhost:8000
echo 👤 Default login: admin / admin123
echo.
echo 🔧 Useful commands:
echo   Logs:    docker-compose -f docker-compose.windows.simple.yml logs -f
echo   Stop:    docker-compose -f docker-compose.windows.simple.yml down
echo   Shell:   docker-compose -f docker-compose.windows.simple.yml exec web bash
echo.
pause 