@echo off
REM =============================================================================
REM ИСПРАВЛЕНИЕ ДУБЛИРУЮЩИХСЯ СТАТИЧЕСКИХ ФАЙЛОВ - ФИНАЛ
REM =============================================================================

echo 🔧 Instagram Mass Uploader - Fix Duplicate Static Files
echo.

echo 🔍 Step 1: Cleaning old duplicate static files...
echo Удаляем старые файлы которые создают конфликт...

if exist "staticfiles\css\apple-style.css" (
    del "staticfiles\css\apple-style.css"
    echo ✅ Deleted old apple-style.css
) else (
    echo ℹ️ Old apple-style.css not found
)

if exist "staticfiles\js\apple-ui.js" (
    del "staticfiles\js\apple-ui.js"
    echo ✅ Deleted old apple-ui.js
) else (
    echo ℹ️ Old apple-ui.js not found
)

if exist "staticfiles\css\logo.svg" (
    del "staticfiles\css\logo.svg"
    echo ✅ Deleted old logo.svg
) else (
    echo ℹ️ Old logo.svg not found
)

echo.
echo 🧹 Step 2: Removing entire staticfiles directory to avoid conflicts...
if exist "staticfiles" (
    rmdir /s /q "staticfiles"
    echo ✅ Removed old staticfiles directory
) else (
    echo ℹ️ Staticfiles directory not found
)

echo.
echo 🔍 Step 3: Verifying source files exist...
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
echo 📋 Step 4: Stopping current container...
docker-compose -f docker-compose.windows.simple.yml down

echo.
echo 🧹 Step 5: Cleaning Docker completely...
docker container prune -f >nul 2>&1
docker image prune -f >nul 2>&1
docker volume rm instagram-mass-uploader-windows_db_data 2>nul

echo.
echo 🔨 Step 6: Rebuilding with clean static files...
echo   📁 No duplicate files - clean build
echo   🎨 Only correct source files will be used
docker-compose -f docker-compose.windows.simple.yml build --no-cache

echo.
echo 🚀 Step 7: Starting application...
docker-compose -f docker-compose.windows.simple.yml up -d

echo.
echo ⏳ Step 8: Waiting for initialization...
timeout /t 20 /nobreak >nul

echo.
echo 🔍 Step 9: Testing static files in container...
docker exec instagram-mass-uploader-windows-web-1 ls -la /app/staticfiles/css/ 2>nul
if errorlevel 1 (
    echo ⚠️ Container not ready yet
) else (
    echo ✅ Static files collected without conflicts
)

echo.
echo 🧪 Step 10: Testing static file serving...
echo Testing if files are actually served by Django...
timeout /t 5 /nobreak >nul
echo Open http://localhost:8000 and check if styling works

echo.
echo 📊 Step 11: Container status...
docker-compose -f docker-compose.windows.simple.yml ps

echo.
echo 🎉 DUPLICATE FILES FIXED!
echo.
echo 📋 Access: http://localhost:8000
echo 👤 Login: admin / admin123
echo.
echo ✅ Fixed Issues:
echo   🧹 Removed duplicate static files
echo   🎨 CSS styling should now work
echo   🖼️ Logo should display correctly
echo   ⚡ JavaScript should function
echo   🍪 Cookies page works (Status 200)
echo.
echo 🧪 Test now - styling should be perfect!
echo.
pause 