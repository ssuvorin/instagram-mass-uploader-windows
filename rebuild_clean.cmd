@echo off
echo ========================================
echo CLEAN REBUILD - Instagram Uploader
echo ========================================

echo.
echo 🛑 Step 1: Stopping containers...
docker-compose -f docker-compose.windows.simple.yml down

echo.
echo 🧹 Step 2: Cleaning Docker cache...
docker system prune -f

echo.
echo 🏗️ Step 3: Building image (no cache)...
docker-compose -f docker-compose.windows.simple.yml build --no-cache

echo.
echo 🚀 Step 4: Starting containers...
docker-compose -f docker-compose.windows.simple.yml up -d

echo.
echo ⏳ Step 5: Waiting for startup (30 seconds)...
timeout /t 30 /nobreak

echo.
echo 🔍 Step 6: Testing static files...
curl -s -o nul -w "CSS: %%{http_code}" http://localhost:8000/static/css/apple-style.css
echo.
curl -s -o nul -w "JS: %%{http_code}" http://localhost:8000/static/js/apple-ui.js  
echo.
curl -s -o nul -w "Logo: %%{http_code}" http://localhost:8000/static/css/logo.svg
echo.

echo.
echo ✅ Clean rebuild complete!
echo 🌐 Application: http://localhost:8000
echo 🔐 Login: admin / admin123
echo 📋 Logs: docker-compose -f docker-compose.windows.simple.yml logs -f

pause 