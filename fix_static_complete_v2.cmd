@echo off
echo ================================================
echo    COMPLETE STATIC FILES FIX V2
echo    Fixed Docker container static files serving
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

echo 🔧 Building fresh image with fixes...
docker-compose -f docker-compose.windows.simple.yml build --no-cache

echo 🚀 Starting container with updated configuration...
docker-compose -f docker-compose.windows.simple.yml up -d

echo ⏳ Waiting for container to initialize...
timeout /t 35 /nobreak > nul

echo 🔍 Testing static file access...
echo Testing CSS:
curl -I http://localhost:8000/static/css/apple-style.css
echo.
echo Testing JS:
curl -I http://localhost:8000/static/js/apple-ui.js
echo.
echo Testing SVG:
curl -I http://localhost:8000/static/css/logo.svg
echo.

echo 🌐 Testing main application...
curl -s http://localhost:8000/login/ > nul && echo ✅ Application responding || echo ❌ Application not responding

echo 📋 Container logs (focusing on static files):
docker-compose -f docker-compose.windows.simple.yml logs | findstr /I "static"

echo ================================================
echo    SETUP COMPLETE WITH FIXES
echo ================================================
echo 🌐 Application: http://localhost:8000
echo 👤 Login: admin / admin123
echo 📋 View logs: docker-compose -f docker-compose.windows.simple.yml logs -f
echo.
echo 🔧 Changes made:
echo   - Fixed Docker static files serving condition
echo   - Added DOCKER_CONTAINER environment variable
echo   - Enhanced static files collection process
echo ================================================

pause 