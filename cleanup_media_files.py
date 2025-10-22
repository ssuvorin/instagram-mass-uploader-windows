#!/usr/bin/env python
"""
Скрипт для очистки файлов из media/bot/bulk_videos/
Может использоваться для тестирования и ручной очистки
"""

import os
import sys
import django
from pathlib import Path

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from uploader.models import BulkUploadTask, BulkVideo
from django.utils import timezone
from datetime import timedelta
import logging

# Use centralized logging - all logs go to django.log
logger = logging.getLogger('scripts.cleanup_media_files')

def cleanup_orphaned_files():
    """Очистить orphaned файлы (файлы без связанных объектов в БД)"""
    media_dir = Path("media/bot/bulk_videos")
    
    if not media_dir.exists():
        print("[FOLDER] Директория media/bot/bulk_videos не существует")
        return 0
    
    # Получаем все файлы из директории
    all_files = set(f.name for f in media_dir.glob("*.mp4"))
    print(f"📊 Найдено {len(all_files)} файлов в директории")
    
    # Получаем файлы, которые есть в БД
    db_files = set()
    for video in BulkVideo.objects.all():
        if video.video_file:
            filename = os.path.basename(video.video_file.name)
            db_files.add(filename)
    
    print(f"📊 Найдено {len(db_files)} файлов в базе данных")
    
    # Находим orphaned файлы
    orphaned_files = all_files - db_files
    print(f"[DELETE] Найдено {len(orphaned_files)} orphaned файлов")
    
    deleted_count = 0
    for filename in orphaned_files:
        file_path = media_dir / filename
        try:
            file_path.unlink()
            deleted_count += 1
            print(f"[DELETE] Удален orphaned файл: {filename}")
        except Exception as e:
            print(f"[FAIL] Не удалось удалить {filename}: {str(e)}")
    
    return deleted_count

def cleanup_completed_tasks_files(days_old=7):
    """Очистить файлы завершенных задач старше N дней"""
    cutoff_date = timezone.now() - timedelta(days=days_old)
    
    # Найти завершенные задачи старше указанного количества дней
    old_completed_tasks = BulkUploadTask.objects.filter(
        status__in=['COMPLETED', 'FAILED', 'PARTIALLY_COMPLETED'],
        updated_at__lt=cutoff_date
    )
    
    print(f"📊 Найдено {old_completed_tasks.count()} завершенных задач старше {days_old} дней")
    
    deleted_count = 0
    for task in old_completed_tasks:
        print(f"[CLIPBOARD] Очистка задачи: {task.name} (ID: {task.id}, статус: {task.status})")
        
        for video in task.videos.all():
            if video.video_file:
                try:
                    file_path = video.video_file.path if hasattr(video.video_file, 'path') else None
                    if file_path and os.path.exists(file_path):
                        # БЕЗОПАСНАЯ ПРОВЕРКА: проверяем, не используется ли файл другими активными задачами
                        def is_file_safe_to_delete():
                            filename = os.path.basename(file_path)
                            
                            # Проверяем, есть ли другие BulkVideo объекты с таким же файлом в активных задачах
                            other_videos_with_same_file = BulkVideo.objects.filter(
                                video_file__icontains=filename
                            ).exclude(
                                bulk_task=task  # Исключаем текущую задачу
                            )
                            
                            # Проверяем статусы задач для этих видео
                            for other_video in other_videos_with_same_file:
                                other_task = other_video.bulk_task
                                if other_task.status in ['RUNNING', 'PENDING']:
                                    return False, f'[BLOCK] File {filename} is still used by running task "{other_task.name}" (ID: {other_task.id})'
                            
                            return True, None
                        
                        is_safe, warning_msg = is_file_safe_to_delete()
                        
                        if is_safe:
                            filename = os.path.basename(file_path)
                            os.unlink(file_path)
                            deleted_count += 1
                            print(f"  [DELETE] Удален файл: {filename}")
                        else:
                            print(f"  [PAUSE] Пропущен файл (используется другими задачами): {os.path.basename(file_path)}")
                            if warning_msg:
                                print(f"  [WARN] {warning_msg}")
                        
                except Exception as e:
                    print(f"  [FAIL] Не удалось удалить файл {video.id}: {str(e)}")
    
    return deleted_count

def show_statistics():
    """Показать статистику файлов"""
    media_dir = Path("media/bot/bulk_videos")
    
    if not media_dir.exists():
        print("[FOLDER] Директория media/bot/bulk_videos не существует")
        return
    
    files = list(media_dir.glob("*.mp4"))
    total_size = sum(f.stat().st_size for f in files)
    
    print(f"📊 Статистика директории media/bot/bulk_videos:")
    print(f"   [FOLDER] Всего файлов: {len(files)}")
    print(f"   💾 Общий размер: {total_size / (1024*1024):.1f} MB")
    
    # Статистика по задачам
    total_tasks = BulkUploadTask.objects.count()
    completed_tasks = BulkUploadTask.objects.filter(status='COMPLETED').count()
    failed_tasks = BulkUploadTask.objects.filter(status='FAILED').count()
    
    print(f"📊 Статистика задач:")
    print(f"   [CLIPBOARD] Всего задач: {total_tasks}")
    print(f"   [OK] Завершенных: {completed_tasks}")
    print(f"   [FAIL] Неудачных: {failed_tasks}")
    
    # Статистика по видео в БД
    total_videos = BulkVideo.objects.count()
    print(f"   [VIDEO] Всего видео в БД: {total_videos}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Cleanup media files with safety checks for running tasks")
    parser.add_argument('--orphaned', action='store_true', help='Cleanup orphaned files (files without database records)')
    parser.add_argument('--old-tasks', type=int, metavar='DAYS', help='Cleanup files from completed tasks older than N days')
    parser.add_argument('--stats', action='store_true', help='Show file and task statistics')
    parser.add_argument('--all', action='store_true', help='Run all cleanup operations')
    
    args = parser.parse_args()
    
    if not any([args.orphaned, args.old_tasks, args.stats, args.all]):
        parser.print_help()
        print("\n" + "="*60)
        print("💡 ВАЖНО: Все операции очистки включают проверки безопасности!")
        print("   • Файлы НЕ удаляются, если используются активными задачами")
        print("   • Проверяется статус задач: RUNNING и PENDING")
        print("   • Безопасно запускать во время работы системы")
        print("="*60)
        return
    
    print("[CLEAN] Начинаем очистку файлов media/bot/bulk_videos/")
    print("=" * 60)
    
    if args.stats or args.all:
        show_statistics()
        print("-" * 60)
    
    total_deleted = 0
    
    if args.orphaned or args.all:
        print("[DELETE] Очистка orphaned файлов...")
        deleted = cleanup_orphaned_files()
        total_deleted += deleted
        print(f"[OK] Удалено orphaned файлов: {deleted}")
        print("-" * 60)
    
    if args.old_tasks or args.all:
        days = args.old_tasks if args.old_tasks else 7
        print(f"[DELETE] Очистка файлов задач старше {days} дней...")
        deleted = cleanup_completed_tasks_files(days)
        total_deleted += deleted
        print(f"[OK] Удалено файлов старых задач: {deleted}")
        print("-" * 60)
    
    print(f"[PARTY] Очистка завершена! Всего удалено файлов: {total_deleted}")
    
    if total_deleted > 0:
        print("\n📊 Обновленная статистика:")
        show_statistics()

if __name__ == "__main__":
    main() 