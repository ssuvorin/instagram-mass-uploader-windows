@echo off
echo ================================================
echo    COMPLETE STATIC FILES FIX V3
echo    ✅ Fixed static files serving
echo    ✅ Improved Dolphin Anty error handling  
echo ================================================

echo 🛑 Stopping existing container...
docker-compose -f docker-compose.windows.simple.yml down --volumes

echo 🧹 Cleaning Docker system...
docker system prune -f

echo 🗂️ Checking local static files structure...
if exist "uploader\static\css\apple-style.css" (
    echo ✅ Source apple-style.css found
) else (
    echo ❌ Source apple-style.css NOT found!
    pause
    exit /b 1
)

if exist "uploader\static\js\apple-ui.js" (
    echo ✅ Source apple-ui.js found  
) else (
    echo ❌ Source apple-ui.js NOT found!
    pause
    exit /b 1
)

if exist "uploader\static\css\logo.svg" (
    echo ✅ Source logo.svg found
) else (
    echo ❌ Source logo.svg NOT found!
    pause
    exit /b 1
)

echo 🔧 Building fresh image with all fixes...
docker-compose -f docker-compose.windows.simple.yml build --no-cache

echo 🚀 Starting container with updated configuration...
docker-compose -f docker-compose.windows.simple.yml up -d

echo ⏳ Waiting for container to initialize...
timeout /t 40 /nobreak > nul

echo 🔍 Testing static file access...
echo.
echo Testing CSS file:
curl -I http://localhost:8000/static/css/apple-style.css
echo.
echo Testing JS file: 
curl -I http://localhost:8000/static/js/apple-ui.js
echo.
echo Testing SVG logo:
curl -I http://localhost:8000/static/css/logo.svg
echo.

echo 🌐 Testing main application response...
curl -s -o nul -w "HTTP Status: %%{http_code}" http://localhost:8000/login/
echo.

echo 📊 Container stats:
docker stats --no-stream instagram-mass-uploader-windows-web-1

echo 📋 Recent logs (last 15 lines):
docker-compose -f docker-compose.windows.simple.yml logs --tail=15

echo ================================================
echo    SETUP COMPLETE WITH ALL FIXES
echo ================================================
echo 🌐 Application: http://localhost:8000
echo 👤 Login: admin / admin123
echo 📋 View logs: docker-compose -f docker-compose.windows.simple.yml logs -f
echo.
echo 🔧 Applied fixes:
echo   ✅ Static files served without conditions
echo   ✅ Removed Docker container serving condition  
echo   ✅ Enhanced Dolphin Anty error handling
echo   ✅ Added API availability checks before operations
echo   ✅ Reduced WebSocket connection spam in logs
echo.
echo 🐬 Dolphin Anty notes:
echo   - If using Dolphin Anty features, ensure it's running on Windows host
echo   - Verify Local API is enabled on port 3001
echo   - Check DOLPHIN_API_HOST=http://host.docker.internal:3001
echo   - Without Dolphin Anty, basic upload functions still work
echo ================================================

pause 