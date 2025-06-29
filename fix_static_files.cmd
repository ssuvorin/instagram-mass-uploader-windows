@echo off
REM =============================================================================
REM БЫСТРОЕ ИСПРАВЛЕНИЕ СТАТИЧЕСКИХ ФАЙЛОВ
REM =============================================================================

echo 🔧 Instagram Uploader - Static Files Fix
echo.

echo 🛑 Stopping application...
docker-compose -f docker-compose.windows.simple.yml down

echo 🔄 Restarting with fixed static files...
docker-compose -f docker-compose.windows.simple.yml up -d

echo ⏳ Waiting for application to start...
timeout /t 15 /nobreak >nul

echo 📋 Checking logs for static files...
docker-compose -f docker-compose.windows.simple.yml logs --tail=20 web

echo.
echo 🎉 Static files fix applied!
echo 📋 Access your application at: http://localhost:8000
echo.
echo 💡 If issues persist, run: restart_clean.cmd
echo.
pause 