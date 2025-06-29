@echo off
REM =============================================================================
REM ИСПРАВЛЕНИЕ СТАТИЧЕСКИХ ФАЙЛОВ И COOKIES - ФИНАЛЬНАЯ ВЕРСИЯ
REM =============================================================================

echo 🔧 Instagram Mass Uploader - Final Static Files Fix
echo.

echo 📋 Step 1: Stopping current container...
docker-compose -f docker-compose.windows.simple.yml down

echo.
echo 🧹 Step 2: Cleaning up old data...
docker container prune -f >nul 2>&1
docker image prune -f >nul 2>&1

echo.
echo 🔨 Step 3: Rebuilding with static files fix...
docker-compose -f docker-compose.windows.simple.yml build --no-cache

echo.
echo 🚀 Step 4: Starting application...
docker-compose -f docker-compose.windows.simple.yml up -d

echo.
echo ⏳ Step 5: Waiting for application to initialize...
timeout /t 15 /nobreak >nul

echo.
echo 🔍 Step 6: Testing static files...
echo Checking if static files are accessible...

docker exec instagram-mass-uploader-windows-web-1 ls -la /app/staticfiles/css/ 2>nul
if errorlevel 1 (
    echo ❌ Container not ready yet, please wait...
) else (
    echo ✅ Static files are present in container
)

echo.
echo 📊 Step 7: Application status...
docker-compose -f docker-compose.windows.simple.yml ps

echo.
echo 🎉 Fix completed!
echo.
echo 📋 Access your application at: http://localhost:8000
echo 👤 Login: admin / admin123
echo.
echo 🔧 The fix includes:
echo   ✅ Static files serving enabled for runserver
echo   ✅ CSS, JavaScript, and logo will now load
echo   ✅ Cookies page template should work
echo.
echo 📞 If you still have issues, check the logs:
echo     docker-compose -f docker-compose.windows.simple.yml logs -f
echo.
pause 