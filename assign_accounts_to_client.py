#!/usr/bin/env python
"""
Скрипт для назначения аккаунтов клиенту для тестирования фильтрации
"""

import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from uploader.models import InstagramAccount
import logging

# Use centralized logging - all logs go to django.log
logger = logging.getLogger('scripts.assign_accounts_to_client')

def assign_accounts_to_client():
    """Назначить несколько аккаунтов клиенту для тестирования"""
    try:
        from cabinet.models import Client
        
        # Получаем клиента "pinko"
        client = Client.objects.get(name="pinko")
        print(f"Найден клиент: {client.name}")
        
        # Получаем первые 5 аккаунтов без клиента
        accounts_without_client = InstagramAccount.objects.filter(client__isnull=True)[:5]
        
        if not accounts_without_client:
            print("Нет аккаунтов без клиента")
            return
        
        print(f"Назначаем {len(accounts_without_client)} аккаунтов клиенту '{client.name}':")
        
        for account in accounts_without_client:
            account.client = client
            account.save()
            print(f"  ✓ {account.username} → {client.name}")
        
        # Показываем статистику
        total_with_client = InstagramAccount.objects.filter(client__isnull=False).count()
        total_without_client = InstagramAccount.objects.filter(client__isnull=True).count()
        
        print(f"\n=== Обновленная статистика ===")
        print(f"Аккаунтов с клиентом: {total_with_client}")
        print(f"Аккаунтов без клиента: {total_without_client}")
        
        # Показываем аккаунты клиента
        client_accounts = client.accounts.all()
        print(f"\nАккаунты клиента '{client.name}':")
        for account in client_accounts:
            print(f"  - {account.username} ({account.status})")
            
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    assign_accounts_to_client()