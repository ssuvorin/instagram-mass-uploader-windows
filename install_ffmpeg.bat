@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Цвета для вывода
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "CYAN=[96m"
set "RESET=[0m"

echo %CYAN%📹 Установка FFmpeg для Windows%RESET%
echo ================================================
echo.

:: Проверка прав администратора
net session >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Этот скрипт требует прав администратора%RESET%
    echo Запустите от имени администратора
    pause
    exit /b 1
)

echo %GREEN%✅ Права администратора подтверждены%RESET%

:: Проверка Chocolatey
echo %CYAN%Проверка Chocolatey...%RESET%
choco --version >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️  Chocolatey не найден. Устанавливаю...%RESET%
    powershell -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
    if errorlevel 1 (
        echo %RED%❌ Ошибка установки Chocolatey%RESET%
        echo Установите Chocolatey вручную с https://chocolatey.org/install
        echo Или попробуйте альтернативные способы установки FFmpeg
        pause
        exit /b 1
    )
    echo %GREEN%✅ Chocolatey установлен%RESET%
) else (
    echo %GREEN%✅ Chocolatey найден%RESET%
)

:: Установка FFmpeg
echo %CYAN%Установка FFmpeg...%RESET%
echo %YELLOW%Это может занять несколько минут...%RESET%
echo.

choco install ffmpeg -y
if errorlevel 1 (
    echo %RED%❌ Ошибка установки FFmpeg%RESET%
    echo.
    echo %YELLOW%Альтернативные способы установки:%RESET%
    echo 1. Скачайте с https://ffmpeg.org/download.html
    echo 2. Распакуйте в C:\ffmpeg
    echo 3. Добавьте C:\ffmpeg\bin в PATH
    echo.
    pause
    exit /b 1
)

:: Проверка установки
echo %CYAN%Проверка установки...%RESET%
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ FFmpeg не найден после установки%RESET%
    echo Попробуйте перезапустить командную строку
    echo Или добавьте FFmpeg в PATH вручную
    pause
    exit /b 1
)

echo %GREEN%✅ FFmpeg установлен успешно!%RESET%
echo.
echo %CYAN%Проверка версии:%RESET%
ffmpeg -version

echo.
echo %CYAN%Проверка ffprobe:%RESET%
ffprobe -version

echo.
echo %GREEN%🎉 Установка завершена!%RESET%
echo.
echo %CYAN%Следующие шаги:%RESET%
echo 1. Перезапустите командную строку
echo 2. Запустите start_project.bat
echo 3. Проверьте работу проекта
echo.
pause 