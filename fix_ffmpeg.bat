@echo off
echo ========================================
echo Исправление установки FFmpeg на Windows
echo ========================================
echo.

REM Проверяем права администратора
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Требуются права администратора!
    echo 💡 Запустите этот файл от имени администратора
    pause
    exit /b 1
)

echo ✅ Права администратора подтверждены
echo.

REM Ищем текущую установку FFmpeg
echo 🔍 Поиск текущей установки FFmpeg...
for /r "%LOCALAPPDATA%" %%i in (ffmpeg.exe) do (
    echo ✅ Найден FFmpeg: %%i
    set "FFMPEG_SOURCE=%%i"
    goto :found_ffmpeg
)

echo ❌ FFmpeg не найден в LOCALAPPDATA
pause
exit /b 1

:found_ffmpeg
echo.

REM Создаем стандартную директорию
echo 📁 Создание директории C:\ffmpeg\bin...
mkdir "C:\ffmpeg\bin" 2>nul

REM Копируем файлы FFmpeg
echo 📋 Копирование файлов FFmpeg...
set "FFMPEG_DIR=%~dp0"
for %%f in ("%FFMPEG_SOURCE%") do set "FFMPEG_SOURCE_DIR=%%~dpf"

copy "%FFMPEG_SOURCE_DIR%ffmpeg.exe" "C:\ffmpeg\bin\" >nul
copy "%FFMPEG_SOURCE_DIR%ffprobe.exe" "C:\ffmpeg\bin\" >nul
copy "%FFMPEG_SOURCE_DIR%ffplay.exe" "C:\ffmpeg\bin\" >nul
copy "%FFMPEG_SOURCE_DIR%*.dll" "C:\ffmpeg\bin\" >nul

if exist "C:\ffmpeg\bin\ffmpeg.exe" (
    echo ✅ Файлы FFmpeg скопированы
) else (
    echo ❌ Ошибка копирования файлов
    pause
    exit /b 1
)

REM Добавляем в системный PATH
echo 🔧 Добавление FFmpeg в системный PATH...
setx PATH "%PATH%;C:\ffmpeg\bin" /M >nul

if %errorlevel% equ 0 (
    echo ✅ FFmpeg добавлен в системный PATH
) else (
    echo ⚠️ Не удалось добавить в системный PATH
)

echo.
echo 🧪 Тестирование установки...

REM Обновляем PATH для текущей сессии
set "PATH=%PATH%;C:\ffmpeg\bin"

REM Тестируем ffmpeg
"C:\ffmpeg\bin\ffmpeg.exe" -version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ ffmpeg работает
) else (
    echo ❌ ffmpeg не работает
)

REM Тестируем ffprobe
"C:\ffmpeg\bin\ffprobe.exe" -version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ ffprobe работает
) else (
    echo ❌ ffprobe не работает
)

echo.
echo 🎉 Установка завершена!
echo 📍 FFmpeg установлен в: C:\ffmpeg\bin
echo 💡 Перезапустите терминал для применения изменений PATH
echo.

pause
