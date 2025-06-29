@echo off
REM =============================================================================
REM ЧИСТАЯ ПЕРЕСБОРКА БЕЗ ДУБЛЕЙ - ПРОСТОЕ РЕШЕНИЕ
REM =============================================================================

echo 🔧 Instagram Mass Uploader - Clean Rebuild
echo.

echo 🧹 Step 1: Removing ALL duplicate static files...
echo Удаляем ВСЕ дубли - оставляем только правильные исходники

if exist "staticfiles" (
    rmdir /s /q "staticfiles"
    echo ✅ Removed entire staticfiles directory
) else (
    echo ℹ️ Staticfiles directory not found
)

echo.
echo 🔍 Step 2: Verifying source files exist in uploader/static/...
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

echo.
echo 📋 Step 3: Stopping container...
docker-compose -f docker-compose.windows.simple.yml down

echo.
echo 🧹 Step 4: Complete Docker cleanup...
docker container prune -f >nul 2>&1
docker image prune -f >nul 2>&1
docker volume rm instagram-mass-uploader-windows_db_data 2>nul

echo.
echo 🔨 Step 5: Clean rebuild without duplicates...
echo   📁 Only uploader/static/ files will be used
echo   🎨 Django will collect them correctly
docker-compose -f docker-compose.windows.simple.yml build --no-cache

echo.
echo 🚀 Step 6: Starting application...
docker-compose -f docker-compose.windows.simple.yml up -d

echo.
echo ⏳ Step 7: Waiting for startup...
timeout /t 20 /nobreak >nul

echo.
echo 📊 Step 8: Checking result...
docker-compose -f docker-compose.windows.simple.yml ps

echo.
echo 🔍 Step 9: Checking for duplicates in logs...
echo Checking if Django still reports duplicate files...
timeout /t 3 /nobreak >nul

echo.
echo 🎉 CLEAN REBUILD COMPLETED!
echo.
echo 📋 Access: http://localhost:8000
echo 👤 Login: admin / admin123
echo.
echo ✅ What should work now:
echo   🎨 CSS styling (no more duplicates)
echo   🖼️ Logo display
echo   ⚡ JavaScript functions
echo   🍪 Cookies page
echo.
echo 📞 Check logs for "Found another file" - should be gone!
echo     docker-compose -f docker-compose.windows.simple.yml logs -f
echo.
pause 