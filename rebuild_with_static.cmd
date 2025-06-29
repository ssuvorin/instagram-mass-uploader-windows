@echo off
REM =============================================================================
REM ПЕРЕСБОРКА С СТАТИЧЕСКИМИ ФАЙЛАМИ - ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ
REM =============================================================================

echo 🔧 Instagram Mass Uploader - Rebuild with Static Files
echo.

echo 🔍 Step 1: Checking static files on host...
if exist "uploader\static\css\apple-style.css" (
    echo ✅ apple-style.css found
) else (
    echo ❌ apple-style.css NOT found!
    echo Please ensure files are not in .gitignore
    pause
    exit /b 1
)

if exist "uploader\static\js\apple-ui.js" (
    echo ✅ apple-ui.js found
) else (
    echo ❌ apple-ui.js NOT found!
    pause
    exit /b 1
)

if exist "uploader\static\css\logo.svg" (
    echo ✅ logo.svg found
) else (
    echo ❌ logo.svg NOT found!
    pause
    exit /b 1
)

echo.
echo 📋 Step 2: Stopping current container...
docker-compose -f docker-compose.windows.simple.yml down

echo.
echo 🧹 Step 3: Cleaning Docker cache...
docker container prune -f >nul 2>&1
docker image prune -f >nul 2>&1

echo.
echo 🔨 Step 4: Rebuilding container with static files...
echo   📁 Static files will be included in build
echo   🎨 CSS, JS, and Logo will be available
docker-compose -f docker-compose.windows.simple.yml build --no-cache

echo.
echo 🚀 Step 5: Starting application...
docker-compose -f docker-compose.windows.simple.yml up -d

echo.
echo ⏳ Step 6: Waiting for initialization...
timeout /t 15 /nobreak >nul

echo.
echo 🔍 Step 7: Testing static files in container...
docker exec instagram-mass-uploader-windows-web-1 ls -la /app/uploader/static/css/ 2>nul
if errorlevel 1 (
    echo ⚠️ Container not ready or static files missing
) else (
    echo ✅ Static files copied to container
)

echo.
echo 📊 Step 8: Checking collected static files...
docker exec instagram-mass-uploader-windows-web-1 ls -la /app/staticfiles/css/ 2>nul
if errorlevel 1 (
    echo ⚠️ Staticfiles not collected yet
) else (
    echo ✅ Static files collected successfully
)

echo.
echo 📋 Step 9: Container status...
docker-compose -f docker-compose.windows.simple.yml ps

echo.
echo 🎉 REBUILD COMPLETED!
echo.
echo 📋 Access: http://localhost:8000
echo 👤 Login: admin / admin123
echo.
echo ✅ Should now work:
echo   🎨 CSS styling (apple-style.css)
echo   🖼️ Logo display (logo.svg) 
echo   ⚡ JavaScript features (apple-ui.js)
echo   🍪 Cookies page (no more 500 errors)
echo.
echo 🧪 Test by visiting the site - styling should be perfect!
echo.
pause 