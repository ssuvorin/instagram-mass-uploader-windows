#!/usr/bin/env python3
"""
Скрипт для просмотра всех аккаунтов в bulk upload задаче
"""

import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from uploader.models import BulkUploadTask, BulkUploadAccount
from django.core.cache import cache

def show_task_accounts(task_id):
    """Показать все аккаунты в задаче"""
    try:
        task = BulkUploadTask.objects.get(id=task_id)
        print(f"📋 Задача: {task.name} (ID: {task.id})")
        print(f"   Статус: {task.status}")
        print(f"   Создана: {task.created_at}")
        print("=" * 60)
        
        accounts = task.accounts.all().order_by('id')
        
        if not accounts:
            print("❌ Нет аккаунтов в задаче")
            return
        
        print(f"👥 Аккаунты в задаче ({accounts.count()}):")
        print("-" * 60)
        
        for i, account_task in enumerate(accounts, 1):
            account = account_task.account
            proxy = account_task.proxy
            
            print(f"{i:2d}. ID: {account_task.id}")
            print(f"    👤 Username: {account.username}")
            print(f"    📊 Статус аккаунта: {account.status}")
            print(f"    🔄 Статус задачи: {account_task.status}")
            print(f"    🕐 Начало: {account_task.started_at or 'Не начато'}")
            print(f"    ✅ Завершение: {account_task.completed_at or 'Не завершено'}")
            
            if proxy:
                print(f"    🌐 Прокси: {proxy.host}:{proxy.port} ({proxy.proxy_type})")
            else:
                print(f"    🌐 Прокси: Не назначен")
            
            # Показываем логи аккаунта
            cache_key = f"task_logs_{task_id}_account_{account_task.id}"
            account_logs = cache.get(cache_key, [])
            
            if account_logs:
                print(f"    📝 Логи в кэше: {len(account_logs)} записей")
                # Показываем последние 3 логи
                for j, log in enumerate(account_logs[-3:], 1):
                    if isinstance(log, dict):
                        message = log.get('message', '')[:80]
                        level = log.get('level', 'INFO')
                        print(f"       {j}. [{level}] {message}...")
                    else:
                        print(f"       {j}. {str(log)[:80]}...")
            else:
                print(f"    📝 Логи в кэше: Нет")
            
            # Показываем логи из базы данных
            if account_task.log:
                db_logs = account_task.log.split('\n')[-3:]
                print(f"    🗄️  Логи из БД:")
                for j, log in enumerate(db_logs, 1):
                    if log.strip():
                        print(f"       {j}. {log[:80]}...")
            
            print()
        
        # Общая статистика
        total = accounts.count()
        completed = accounts.filter(status='COMPLETED').count()
        failed = accounts.filter(status='FAILED').count()
        running = accounts.filter(status='RUNNING').count()
        pending = accounts.filter(status='PENDING').count()
        
        print("📊 Общая статистика:")
        print(f"   Всего аккаунтов: {total}")
        print(f"   Завершено: {completed}")
        print(f"   Ошибки: {failed}")
        print(f"   Выполняется: {running}")
        print(f"   Ожидает: {pending}")
        print(f"   Процент завершения: {(completed/total*100):.1f}%" if total > 0 else "0%")
        
    except BulkUploadTask.DoesNotExist:
        print(f"❌ Задача с ID {task_id} не найдена")
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")

def show_last_task():
    """Показать последнюю задачу"""
    try:
        last_task = BulkUploadTask.objects.order_by('-created_at').first()
        if last_task:
            print(f"🔍 Последняя задача: ID {last_task.id}")
            show_task_accounts(last_task.id)
        else:
            print("❌ Нет bulk upload задач")
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")

def main():
    if len(sys.argv) > 1:
        task_id = int(sys.argv[1])
        show_task_accounts(task_id)
    else:
        show_last_task()

if __name__ == "__main__":
    main() 