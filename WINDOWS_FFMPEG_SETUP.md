# Установка FFmpeg для Windows

## Обзор

FFmpeg необходим для обработки и уникализации видео в Instagram Mass Uploader. На Windows его нужно установить отдельно.

## Способы установки

### Способ 1: Chocolatey (Рекомендуется)

1. **Установите Chocolatey** (если еще не установлен):
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   ```

2. **Установите FFmpeg**:
   ```powershell
   choco install ffmpeg
   ```

3. **Перезапустите командную строку** и проверьте установку:
   ```cmd
   ffmpeg -version
   ```

### Способ 2: Scoop

1. **Установите Scoop** (если еще не установлен):
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   irm get.scoop.sh | iex
   ```

2. **Установите FFmpeg**:
   ```powershell
   scoop install ffmpeg
   ```

### Способ 3: Ручная установка

1. **Скачайте FFmpeg** с официального сайта:
   - Перейдите на https://ffmpeg.org/download.html
   - Скачайте Windows версию (static builds)

2. **Распакуйте архив** в удобное место (например, `C:\ffmpeg`)

3. **Добавьте в PATH**:
   - Откройте "Система" → "Дополнительные параметры системы" → "Переменные среды"
   - Найдите переменную "Path" и нажмите "Изменить"
   - Добавьте путь к папке с FFmpeg (например, `C:\ffmpeg\bin`)
   - Нажмите "ОК" во всех окнах

4. **Перезапустите командную строку** и проверьте:
   ```cmd
   ffmpeg -version
   ```

## Проверка установки

После установки проверьте, что FFmpeg работает:

```cmd
ffmpeg -version
ffprobe -version
```

Вы должны увидеть информацию о версии FFmpeg.

## Автоматическая установка через bat файл

Создайте файл `install_ffmpeg.bat`:

```batch
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

:: Проверка Chocolatey
echo %CYAN%Проверка Chocolatey...%RESET%
choco --version >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️  Chocolatey не найден. Устанавливаю...%RESET%
    powershell -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
    if errorlevel 1 (
        echo %RED%❌ Ошибка установки Chocolatey%RESET%
        echo Установите Chocolatey вручную с https://chocolatey.org/install
        pause
        exit /b 1
    )
    echo %GREEN%✅ Chocolatey установлен%RESET%
) else (
    echo %GREEN%✅ Chocolatey найден%RESET%
)

:: Установка FFmpeg
echo %CYAN%Установка FFmpeg...%RESET%
choco install ffmpeg -y
if errorlevel 1 (
    echo %RED%❌ Ошибка установки FFmpeg%RESET%
    pause
    exit /b 1
)

:: Проверка установки
echo %CYAN%Проверка установки...%RESET%
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ FFmpeg не найден после установки%RESET%
    echo Попробуйте перезапустить командную строку
    pause
    exit /b 1
)

echo %GREEN%✅ FFmpeg установлен успешно!%RESET%
echo.
echo %CYAN%Проверка версии:%RESET%
ffmpeg -version

echo.
echo %GREEN%🎉 Установка завершена!%RESET%
pause
```

## Решение проблем

### Проблема: "ffmpeg не является внутренней или внешней командой"

**Решение:**
1. Убедитесь, что FFmpeg добавлен в PATH
2. Перезапустите командную строку
3. Проверьте путь: `echo %PATH%`

### Проблема: Ошибка при установке через Chocolatey

**Решение:**
1. Запустите PowerShell от имени администратора
2. Выполните: `choco install ffmpeg -y --force`

### Проблема: FFmpeg не работает в проекте

**Решение:**
1. Убедитесь, что FFmpeg доступен в системном PATH
2. Перезапустите виртуальное окружение
3. Проверьте в Python:
   ```python
   import subprocess
   result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
   print(result.returncode == 0)
   ```

## Альтернативные варианты

### Использование встроенного FFmpeg

Если у вас есть проблемы с установкой, можно использовать встроенную версию:

1. Скачайте FFmpeg с https://www.gyan.dev/ffmpeg/builds/
2. Распакуйте в папку проекта
3. Обновите переменную окружения:
   ```cmd
   set FFMPEG_PATH=C:\path\to\ffmpeg\bin
   ```

### Docker вариант

Если используете Docker, FFmpeg уже включен в образ:

```dockerfile
RUN apt-get update && apt-get install -y ffmpeg
```

## Проверка в проекте

После установки FFmpeg проверьте его работу в проекте:

```python
from uploader.async_video_uniquifier import check_ffmpeg_availability

if check_ffmpeg_availability():
    print("✅ FFmpeg доступен")
else:
    print("❌ FFmpeg недоступен")
```

## Поддержка

При проблемах с установкой FFmpeg:

1. Проверьте логи в папке `logs/`
2. Убедитесь, что у вас есть права администратора
3. Попробуйте перезагрузить компьютер после установки
4. Проверьте антивирус - он может блокировать FFmpeg 