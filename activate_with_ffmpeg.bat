@echo off
echo ========================================
echo Активация виртуального окружения с FFmpeg
echo ========================================
echo.

REM Проверяем существование виртуального окружения
if not exist ".venv311" (
    echo ❌ Виртуальное окружение .venv311 не найдено!
    echo 💡 Создайте виртуальное окружение: python -m venv .venv311
    pause
    exit /b 1
)

echo ✅ Виртуальное окружение найдено

REM Активируем виртуальное окружение
echo 🔄 Активация виртуального окружения...
call .venv311\Scripts\activate.bat

REM Добавляем FFmpeg в PATH для текущей сессии
echo 🔧 Добавление FFmpeg в PATH...
set "PATH=C:\ffmpeg\bin;%PATH%"

REM Проверяем FFmpeg
echo 🧪 Проверка FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ FFmpeg работает в виртуальном окружении!
    ffmpeg -version | findstr "ffmpeg version"
) else (
    echo ❌ FFmpeg не работает
    echo 💡 Убедитесь, что FFmpeg установлен в C:\ffmpeg\bin
)

echo.
echo 🎉 Виртуальное окружение активировано с FFmpeg!
echo 💡 Теперь можно запускать Python скрипты
echo.

REM Запускаем интерактивную оболочку
cmd /k
