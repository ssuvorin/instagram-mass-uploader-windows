#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправления FFmpeg на Windows
"""

import os
import sys
import subprocess

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'uploader'))

def test_ffmpeg_detection():
    """Тестирование обнаружения FFmpeg"""
    print("🔍 Тестирование обнаружения FFmpeg...")
    
    try:
        from async_video_uniquifier import check_ffmpeg_availability
        
        # Тестируем функцию проверки доступности FFmpeg
        is_available = check_ffmpeg_availability()
        
        if is_available:
            print("✅ FFmpeg найден и работает!")
            
            # Дополнительная проверка - попробуем запустить ffmpeg
            try:
                result = subprocess.run(["ffmpeg", "-version"], 
                                     capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version_line = result.stdout.split('\n')[0]
                    print(f"📋 Версия FFmpeg: {version_line}")
                    return True
                else:
                    print(f"❌ FFmpeg вернул ошибку: {result.stderr}")
                    return False
            except Exception as e:
                print(f"❌ Ошибка при запуске FFmpeg: {e}")
                return False
        else:
            print("❌ FFmpeg не найден!")
            return False
            
    except ImportError as e:
        print(f"❌ Ошибка импорта модуля: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def test_ffmpeg_paths():
    """Тестирование поиска FFmpeg в различных путях"""
    print("\n🔍 Тестирование поиска FFmpeg в различных путях...")
    
    # Стандартные пути поиска
    ffmpeg_paths = [
        "ffmpeg",  # В PATH
        "ffmpeg.exe",  # Windows в PATH
        os.path.join(os.getcwd(), "ffmpeg.exe"),  # В текущей директории
        r"C:\ffmpeg\bin\ffmpeg.exe",  # Стандартное место установки на Windows
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",  # Альтернативное место
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",  # 32-bit программы
        r"C:\tools\ffmpeg\bin\ffmpeg.exe",  # Chocolatey установка
    ]
    
    # Добавляем поиск в LOCALAPPDATA рекурсивно
    try:
        import glob
        localappdata = os.environ.get('LOCALAPPDATA', r'C:\Users\{}\AppData\Local'.format(os.getenv('USERNAME', 'Admin')))
        if os.path.exists(localappdata):
            print(f"📁 Поиск в LOCALAPPDATA: {localappdata}")
            # Ищем ffmpeg.exe рекурсивно в LOCALAPPDATA
            ffmpeg_patterns = [
                os.path.join(localappdata, "**", "ffmpeg.exe"),
                os.path.join(localappdata, "**", "bin", "ffmpeg.exe"),
            ]
            for pattern in ffmpeg_patterns:
                found_ffmpeg = glob.glob(pattern, recursive=True)
                if found_ffmpeg:
                    print(f"🎯 Найдено в LOCALAPPDATA: {found_ffmpeg[:3]}")
                    ffmpeg_paths.extend(found_ffmpeg[:3])  # Добавляем максимум 3 найденных пути
                    break
    except Exception as e:
        print(f"⚠️ Ошибка поиска в LOCALAPPDATA: {e}")
    
    print(f"📋 Проверяем {len(ffmpeg_paths)} путей...")
    
    found_paths = []
    for path in ffmpeg_paths:
        try:
            if os.path.exists(path) or path in ["ffmpeg", "ffmpeg.exe"]:
                result = subprocess.run([path, "-version"], 
                                     capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    found_paths.append(path)
                    version_line = result.stdout.split('\n')[0]
                    print(f"✅ Найден: {path} - {version_line}")
                else:
                    print(f"❌ Ошибка в {path}: {result.stderr}")
            else:
                print(f"⏭️ Не существует: {path}")
        except Exception as e:
            print(f"❌ Ошибка тестирования {path}: {e}")
    
    if found_paths:
        print(f"\n🎉 Найдено {len(found_paths)} рабочих версий FFmpeg!")
        return True
    else:
        print(f"\n💥 FFmpeg не найден ни в одном из путей!")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование исправления FFmpeg для Windows")
    print("=" * 50)
    
    # Тест 1: Проверка обнаружения FFmpeg
    test1_passed = test_ffmpeg_detection()
    
    # Тест 2: Проверка поиска в различных путях
    test2_passed = test_ffmpeg_paths()
    
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"🔍 Обнаружение FFmpeg: {'✅ ПРОЙДЕН' if test1_passed else '❌ ПРОВАЛЕН'}")
    print(f"📁 Поиск в путях: {'✅ ПРОЙДЕН' if test2_passed else '❌ ПРОВАЛЕН'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! FFmpeg должен работать корректно.")
        return 0
    else:
        print("\n💥 НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ. Требуется дополнительная настройка.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
