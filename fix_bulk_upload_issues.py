#!/usr/bin/env python3
"""
Скрипт для диагностики и исправления проблем с bulk upload
"""

import os
import sys
import django
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from uploader.models import BulkUploadTask, BulkUploadAccount
from django.utils import timezone
import logging

# Use centralized logging - all logs go to django.log
logger = logging.getLogger('scripts.fix_bulk_upload_issues')

def check_bulk_upload_issues():
    """Проверяет и исправляет проблемы с bulk upload"""
    
    print("🔍 Проверка проблем с bulk upload...")
    
    # 1. Проверяем активные задачи
    active_tasks = BulkUploadTask.objects.filter(status='RUNNING')
    if active_tasks.exists():
        print(f"⚠️  Найдено {active_tasks.count()} активных задач:")
        for task in active_tasks:
            print(f"   - Задача {task.id}: {task.name}")
            # Сбрасываем статус на PENDING для перезапуска
            task.status = 'PENDING'
            task.log += f"\n[{timezone.now()}] [AUTO_FIX] Сброшен статус с RUNNING на PENDING для перезапуска"
            task.save()
            print(f"     ✅ Статус сброшен на PENDING")
    
    # 2. Проверяем зависшие аккаунты
    stuck_accounts = BulkUploadAccount.objects.filter(status='RUNNING')
    if stuck_accounts.exists():
        print(f"⚠️  Найдено {stuck_accounts.count()} зависших аккаунтов:")
        for account in stuck_accounts:
            print(f"   - Аккаунт {account.id}: {account.account.username}")
            # Сбрасываем статус на PENDING
            account.status = 'PENDING'
            account.save()
            print(f"     ✅ Статус сброшен на PENDING")
    
    # 3. Проверяем задачи с ошибками
    failed_tasks = BulkUploadTask.objects.filter(status='FAILED')
    if failed_tasks.exists():
        print(f"⚠️  Найдено {failed_tasks.count()} неудачных задач:")
        for task in failed_tasks:
            print(f"   - Задача {task.id}: {task.name}")
            print(f"     Последняя ошибка: {task.log[-200:] if task.log else 'Нет логов'}")
    
    # 4. Проверяем настройки окружения
    print("\n🔧 Проверка настроек окружения...")
    
    required_env_vars = [
        'DOLPHIN_API_TOKEN',
        'DOLPHIN_API_HOST',
        'SECRET_KEY',
        'ALLOWED_HOSTS'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Отсутствуют переменные окружения: {', '.join(missing_vars)}")
    else:
        print("✅ Все необходимые переменные окружения настроены")
    
    # 5. Рекомендации по исправлению
    print("\n📋 Рекомендации по исправлению:")
    print("1. Убедитесь, что Dolphin Anty запущен и доступен")
    print("2. Проверьте настройки прокси для аккаунтов")
    print("3. Убедитесь, что видео файлы существуют и доступны")
    print("4. Проверьте логи на наличие специфических ошибок")
    print("5. Рассмотрите возможность уменьшения количества параллельных аккаунтов")
    
    print("\n✅ Диагностика завершена!")

def fix_common_issues():
    """Исправляет распространенные проблемы"""
    
    print("🔧 Исправление распространенных проблем...")
    
    # 1. Сбрасываем все зависшие задачи
    stuck_tasks = BulkUploadTask.objects.filter(status='RUNNING')
    for task in stuck_tasks:
        task.status = 'PENDING'
        task.log += f"\n[{timezone.now()}] [AUTO_FIX] Автоматический сброс зависшей задачи"
        task.save()
        print(f"✅ Сброшена задача {task.id}: {task.name}")
    
    # 2. Сбрасываем все зависшие аккаунты
    stuck_accounts = BulkUploadAccount.objects.filter(status='RUNNING')
    for account in stuck_accounts:
        account.status = 'PENDING'
        account.save()
        print(f"✅ Сброшен аккаунт {account.id}: {account.account.username}")
    
    # 3. Очищаем старые логи (оставляем только последние 1000 символов)
    tasks_with_long_logs = BulkUploadTask.objects.filter(log__length__gt=1000)
    for task in tasks_with_long_logs:
        task.log = task.log[-1000:] + f"\n[{timezone.now()}] [AUTO_FIX] Лог обрезан для экономии места"
        task.save()
        print(f"✅ Обрезан лог для задачи {task.id}")
    
    print("✅ Исправления применены!")

if __name__ == "__main__":
    print("🚀 Скрипт диагностики и исправления bulk upload")
    print("=" * 50)
    
    try:
        check_bulk_upload_issues()
        print("\n" + "=" * 50)
        fix_common_issues()
        
    except Exception as e:
        print(f"❌ Ошибка при выполнении скрипта: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n🎉 Скрипт выполнен успешно!")
