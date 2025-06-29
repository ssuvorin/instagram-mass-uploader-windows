@echo off
REM =============================================================================
REM ДИАГНОСТИКА INSTAGRAM UPLOADER
REM =============================================================================

echo 🔍 Instagram Mass Uploader - System Diagnostics
echo.

echo 📊 Docker Status:
docker --version
echo.

echo 🐳 Running Containers:
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.

echo 📁 Project Directories:
echo Logs:        %CD%\logs
echo Media:       %CD%\media  
echo Static:      %CD%\static
echo StaticFiles: %CD%\staticfiles
echo.

echo 📊 Docker Volumes:
docker volume ls | findstr /C:"instagram" 2>nul
if errorlevel 1 echo No Instagram volumes found
echo.

echo 🌐 Network Test:
echo Testing localhost:8000...
curl -I http://localhost:8000 2>nul
if errorlevel 1 (
    echo ❌ Application not responding on localhost:8000
) else (
    echo ✅ Application is responding
)
echo.

echo 📋 Recent Logs (last 20 lines):
docker-compose -f docker-compose.windows.simple.yml logs --tail=20 web 2>nul
if errorlevel 1 echo ❌ No logs available - container may not be running
echo.

echo 🔧 Quick Actions:
echo [1] View live logs:   docker-compose -f docker-compose.windows.simple.yml logs -f
echo [2] Restart:          restart_clean.cmd
echo [3] Stop:             docker-compose -f docker-compose.windows.simple.yml down
echo [4] Shell access:     docker-compose -f docker-compose.windows.simple.yml exec web bash
echo.
pause 