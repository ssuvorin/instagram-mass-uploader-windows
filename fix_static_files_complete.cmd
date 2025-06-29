@echo off
echo ================================================
echo    COMPLETE STATIC FILES FIX
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

echo 🔧 Building fresh image...
docker-compose -f docker-compose.windows.simple.yml build --no-cache

echo 🚀 Starting container with fresh setup...
docker-compose -f docker-compose.windows.simple.yml up -d

echo ⏳ Waiting for container to initialize...
timeout /t 30 /nobreak > nul

echo 🔍 Checking static files in container...
docker exec instagram-mass-uploader-windows-web-1 find /app/staticfiles -name "apple-*" -o -name "logo.svg" 2>nul || echo "Files not found yet"

echo ⏳ Waiting for application to start...
timeout /t 15 /nobreak > nul

echo 🌐 Testing application...
curl -s http://localhost:8000/login/ > nul && echo ✅ Application responding || echo ❌ Application not responding

echo 📋 Container logs (last 20 lines):
docker-compose -f docker-compose.windows.simple.yml logs --tail=20

echo ================================================
echo    SETUP COMPLETE
echo ================================================
echo 🌐 Application: http://localhost:8000
echo 👤 Login: admin / admin123
echo 📋 View logs: docker-compose -f docker-compose.windows.simple.yml logs -f
echo ================================================

pause 