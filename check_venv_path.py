#!/usr/bin/env python3
"""
Скрипт для проверки PATH в виртуальном окружении
"""

import os
import sys
import subprocess

def check_path_in_venv():
    """Проверить PATH в виртуальном окружении"""
    print("🔍 Проверка PATH в виртуальном окружении")
    print("=" * 50)
    
    # Проверяем, в виртуальном окружении ли мы
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Находимся в виртуальном окружении")
        print(f"📍 Python prefix: {sys.prefix}")
        print(f"📍 Python base_prefix: {sys.base_prefix}")
    else:
        print("❌ НЕ находимся в виртуальном окружении")
    
    print(f"\n📋 Текущий PATH:")
    path_items = os.environ.get('PATH', '').split(os.pathsep)
    for i, item in enumerate(path_items, 1):
        print(f"{i:2d}. {item}")
    
    print(f"\n🔍 Поиск FFmpeg в PATH:")
    ffmpeg_found = False
    for item in path_items:
        ffmpeg_path = os.path.join(item, "ffmpeg.exe")
        if os.path.exists(ffmpeg_path):
            print(f"✅ Найден: {ffmpeg_path}")
            ffmpeg_found = True
            break
    
    if not ffmpeg_found:
        print("❌ FFmpeg не найден в PATH")
    
    print(f"\n🧪 Тестирование FFmpeg:")
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg работает: {version_line}")
        else:
            print(f"❌ FFmpeg не работает: {result.stderr}")
    except FileNotFoundError:
        print("❌ FFmpeg не найден (FileNotFoundError)")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def fix_venv_path():
    """Исправить PATH в виртуальном окружении"""
    print("\n🔧 Исправление PATH в виртуальном окружении")
    print("=" * 50)
    
    # Добавляем стандартные пути FFmpeg
    ffmpeg_paths = [
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
        r"C:\tools\ffmpeg\bin",
    ]
    
    current_path = os.environ.get('PATH', '')
    added_paths = []
    
    for ffmpeg_path in ffmpeg_paths:
        if os.path.exists(ffmpeg_path) and ffmpeg_path not in current_path:
            os.environ['PATH'] = ffmpeg_path + os.pathsep + current_path
            added_paths.append(ffmpeg_path)
            print(f"✅ Добавлен в PATH: {ffmpeg_path}")
    
    if added_paths:
        print(f"\n🧪 Тестирование после исправления:")
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"✅ FFmpeg теперь работает: {version_line}")
                return True
            else:
                print(f"❌ FFmpeg все еще не работает: {result.stderr}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    else:
        print("ℹ️ Не найдено новых путей для добавления")
    
    return False

def main():
    """Основная функция"""
    print("🚀 Проверка PATH в виртуальном окружении")
    print("=" * 50)
    
    # Проверяем текущее состояние
    check_path_in_venv()
    
    # Пытаемся исправить
    if fix_venv_path():
        print("\n🎉 PATH исправлен! FFmpeg должен работать.")
    else:
        print("\n💥 Не удалось исправить PATH автоматически.")
        print("💡 Попробуйте:")
        print("   1. Перезапустить терминал")
        print("   2. Запустить fix_ffmpeg.bat от имени администратора")
        print("   3. Добавить C:\\ffmpeg\\bin в PATH вручную")

if __name__ == "__main__":
    main()
