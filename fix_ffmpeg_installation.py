#!/usr/bin/env python3
"""
Скрипт для правильной установки FFmpeg в стандартное место на Windows
"""

import os
import sys
import subprocess
import shutil
import zipfile
import requests
from pathlib import Path

def find_current_ffmpeg():
    """Найти текущую установку FFmpeg"""
    print("🔍 Поиск текущей установки FFmpeg...")
    
    # Ищем в LOCALAPPDATA
    localappdata = os.environ.get('LOCALAPPDATA', r'C:\Users\{}\AppData\Local'.format(os.getenv('USERNAME', 'Admin')))
    
    try:
        import glob
        ffmpeg_patterns = [
            os.path.join(localappdata, "**", "ffmpeg.exe"),
            os.path.join(localappdata, "**", "bin", "ffmpeg.exe"),
        ]
        
        for pattern in ffmpeg_patterns:
            found_ffmpeg = glob.glob(pattern, recursive=True)
            if found_ffmpeg:
                ffmpeg_path = found_ffmpeg[0]
                print(f"✅ Найден FFmpeg: {ffmpeg_path}")
                return ffmpeg_path
    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
    
    return None

def test_ffmpeg(ffmpeg_path):
    """Тестировать FFmpeg"""
    try:
        result = subprocess.run([ffmpeg_path, "-version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg работает: {version_line}")
            return True
        else:
            print(f"❌ FFmpeg не работает: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Ошибка тестирования FFmpeg: {e}")
        return False

def create_ffmpeg_directory():
    """Создать стандартную директорию для FFmpeg"""
    ffmpeg_dir = r"C:\ffmpeg"
    bin_dir = os.path.join(ffmpeg_dir, "bin")
    
    print(f"📁 Создание директории: {bin_dir}")
    os.makedirs(bin_dir, exist_ok=True)
    
    return bin_dir

def copy_ffmpeg_files(source_path, target_dir):
    """Скопировать файлы FFmpeg в стандартное место"""
    source_dir = os.path.dirname(source_path)
    
    print(f"📋 Копирование файлов из {source_dir} в {target_dir}")
    
    # Список файлов для копирования
    files_to_copy = [
        "ffmpeg.exe",
        "ffprobe.exe", 
        "ffplay.exe",
        "avcodec-*.dll",
        "avdevice-*.dll",
        "avfilter-*.dll",
        "avformat-*.dll",
        "avutil-*.dll",
        "postproc-*.dll",
        "swresample-*.dll",
        "swscale-*.dll"
    ]
    
    copied_files = []
    
    try:
        import glob
        for pattern in files_to_copy:
            files = glob.glob(os.path.join(source_dir, pattern))
            for file in files:
                filename = os.path.basename(file)
                target_file = os.path.join(target_dir, filename)
                shutil.copy2(file, target_file)
                copied_files.append(filename)
                print(f"✅ Скопирован: {filename}")
        
        return len(copied_files) > 0
        
    except Exception as e:
        print(f"❌ Ошибка копирования: {e}")
        return False

def add_to_path(target_dir):
    """Добавить FFmpeg в PATH"""
    print(f"🔧 Добавление {target_dir} в PATH...")
    
    try:
        # Получаем текущий PATH
        current_path = os.environ.get('PATH', '')
        
        if target_dir not in current_path:
            # Добавляем в PATH для текущей сессии
            os.environ['PATH'] = target_dir + os.pathsep + current_path
            
            # Добавляем в системный PATH (требует прав администратора)
            try:
                subprocess.run([
                    'setx', 'PATH', f'{target_dir};{current_path}', '/M'
                ], check=True, capture_output=True)
                print("✅ FFmpeg добавлен в системный PATH")
            except subprocess.CalledProcessError:
                print("⚠️ Не удалось добавить в системный PATH (нужны права администратора)")
                print("💡 Перезапустите терминал или добавьте в PATH вручную")
            
            return True
        else:
            print("✅ FFmpeg уже в PATH")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка добавления в PATH: {e}")
        return False

def test_installation():
    """Тестировать установку"""
    print("\n🧪 Тестирование установки...")
    
    try:
        # Тестируем ffmpeg
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ ffmpeg работает из PATH")
        else:
            print("❌ ffmpeg не работает из PATH")
            return False
        
        # Тестируем ffprobe
        result = subprocess.run(['ffprobe', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ ffprobe работает из PATH")
        else:
            print("❌ ffprobe не работает из PATH")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

def main():
    """Основная функция"""
    print("🚀 Исправление установки FFmpeg на Windows")
    print("=" * 50)
    
    # Шаг 1: Найти текущую установку
    current_ffmpeg = find_current_ffmpeg()
    if not current_ffmpeg:
        print("❌ FFmpeg не найден! Сначала установите FFmpeg.")
        return 1
    
    # Шаг 2: Тестировать текущую установку
    if not test_ffmpeg(current_ffmpeg):
        print("❌ Текущая установка FFmpeg не работает!")
        return 1
    
    # Шаг 3: Создать стандартную директорию
    target_dir = create_ffmpeg_directory()
    
    # Шаг 4: Скопировать файлы
    if not copy_ffmpeg_files(current_ffmpeg, target_dir):
        print("❌ Не удалось скопировать файлы FFmpeg!")
        return 1
    
    # Шаг 5: Добавить в PATH
    if not add_to_path(target_dir):
        print("❌ Не удалось добавить FFmpeg в PATH!")
        return 1
    
    # Шаг 6: Тестировать установку
    if test_installation():
        print("\n🎉 FFmpeg успешно установлен в стандартное место!")
        print(f"📍 Расположение: {target_dir}")
        print("💡 Перезапустите терминал для применения изменений PATH")
        return 0
    else:
        print("\n💥 Установка завершена, но есть проблемы с тестированием")
        print("💡 Попробуйте перезапустить терминал")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
