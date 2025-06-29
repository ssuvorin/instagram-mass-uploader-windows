@echo off
echo ========================================
echo CLEANING STATICFILES FOLDER
echo ========================================

if exist "staticfiles" (
    echo 🗑️ Found staticfiles folder, removing...
    rmdir /s /q "staticfiles"
    echo ✅ Staticfiles folder removed
) else (
    echo ℹ️ Staticfiles folder not found (good!)
)

echo.
echo 🧹 Cleanup complete! Now run:
echo    git pull
echo    rebuild_clean.cmd
echo.
pause 