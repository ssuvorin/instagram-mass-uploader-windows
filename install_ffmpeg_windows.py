#!/usr/bin/env python3
"""
Автоматическая установка FFmpeg для Windows
Поддерживает установку через WinGet, Chocolatey или скачивание вручную
"""

import os
import sys
import subprocess
import requests
import zipfile
import shutil
from pathlib import Path

def check_ffmpeg():
    """Проверяет, установлен ли FFmpeg"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ FFmpeg уже установлен!")
            print(f"Версия: {result.stdout.split('n')[0]}")
            return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False

def install_via_winget():
    """Установка через WinGet"""
    try:
        print("🔄 Попытка установки через WinGet...")
        result = subprocess.run(['winget', 'install', 'Gyan.FFmpeg'], 
                              capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print("✅ FFmpeg успешно установлен через WinGet!")
            return True
        else:
            print(f"❌ WinGet установка не удалась: {result.stderr}")
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"❌ WinGet недоступен: {e}")
    return False

def install_via_chocolatey():
    """Установка через Chocolatey"""
    try:
        print("🔄 Попытка установки через Chocolatey...")
        result = subprocess.run(['choco', 'install', 'ffmpeg', '-y'], 
                              capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print("✅ FFmpeg успешно установлен через Chocolatey!")
            return True
        else:
            print(f"❌ Chocolatey установка не удалась: {result.stderr}")
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"❌ Chocolatey недоступен: {e}")
    return False

def download_ffmpeg_manual():
    """Скачивание FFmpeg вручную"""
    try:
        print("🔄 Скачивание FFmpeg вручную...")
        
        # Создаем папку для FFmpeg
        ffmpeg_dir = Path("C:/ffmpeg")
        ffmpeg_dir.mkdir(exist_ok=True)
        
        # URL для скачивания FFmpeg (последняя стабильная версия)
        ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        
        print(f"📥 Скачивание с {ffmpeg_url}...")
        response = requests.get(ffmpeg_url, stream=True)
        response.raise_for_status()
        
        zip_path = ffmpeg_dir / "ffmpeg.zip"
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print("📦 Распаковка архива...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
        
        # Находим папку с FFmpeg
        extracted_dirs = [d for d in ffmpeg_dir.iterdir() if d.is_dir()]
        if extracted_dirs:
            ffmpeg_build_dir = extracted_dirs[0]
            bin_dir = ffmpeg_build_dir / "bin"
            
            if bin_dir.exists():
                # Копируем файлы в корень ffmpeg
                for file in bin_dir.glob("*.exe"):
                    shutil.copy2(file, ffmpeg_dir / file.name)
                
                # Удаляем временные файлы
                shutil.rmtree(ffmpeg_build_dir)
                zip_path.unlink()
                
                print("✅ FFmpeg успешно скачан и установлен!")
                print(f"📁 Расположение: {ffmpeg_dir}")
                return True
        
        print("❌ Не удалось найти исполняемые файлы FFmpeg в архиве")
        return False
        
    except Exception as e:
        print(f"❌ Ошибка при скачивании FFmpeg: {e}")
        return False

def add_to_path():
    """Добавляет FFmpeg в PATH"""
    ffmpeg_path = "C:\\ffmpeg"
    if os.path.exists(ffmpeg_path):
        print(f"📝 Добавление {ffmpeg_path} в PATH...")
        print("⚠️  ВНИМАНИЕ: Для применения изменений PATH перезапустите терминал!")
        print(f"   Или выполните: setx PATH \"%PATH%;{ffmpeg_path}\"")
        return True
    return False

def main():
    print("🎬 Установщик FFmpeg для Windows")
    print("=" * 50)
    
    # Проверяем, установлен ли уже FFmpeg
    if check_ffmpeg():
        return
    
    print("🔍 FFmpeg не найден, начинаем установку...")
    
    # Пробуем разные способы установки
    success = False
    
    # 1. WinGet
    if not success:
        success = install_via_winget()
    
    # 2. Chocolatey
    if not success:
        success = install_via_chocolatey()
    
    # 3. Ручное скачивание
    if not success:
        success = download_ffmpeg_manual()
    
    if success:
        print("\n🎉 FFmpeg успешно установлен!")
        
        # Проверяем установку
        if check_ffmpeg():
            print("✅ Установка подтверждена!")
        else:
            print("⚠️  FFmpeg установлен, но не найден в PATH")
            add_to_path()
    else:
        print("\n❌ Не удалось установить FFmpeg автоматически")
        print("📋 Ручная установка:")
        print("1. Скачайте FFmpeg с https://ffmpeg.org/download.html")
        print("2. Распакуйте в C:\\ffmpeg\\")
        print("3. Добавьте C:\\ffmpeg\\ в PATH")
        print("4. Перезапустите терминал")

if __name__ == "__main__":
    main()
