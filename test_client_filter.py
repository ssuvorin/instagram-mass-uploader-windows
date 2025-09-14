#!/usr/bin/env python
"""
Простой тест для проверки фильтрации аккаунтов по клиенту
"""

import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from uploader.models import InstagramAccount
from uploader.forms import BulkUploadTaskForm

def test_client_filter():
    """Тест фильтрации аккаунтов по клиенту"""
    print("=== Тест фильтрации аккаунтов по клиенту ===")
    
    # Создаем форму
    form = BulkUploadTaskForm()
    
    # Проверяем, что поле client_filter существует
    if 'client_filter' in form.fields:
        print("✓ Поле client_filter найдено в форме")
        
        # Проверяем choices клиентов
        client_choices = form.fields['client_filter'].choices
        if client_choices:
            print(f"✓ Найдено {len(client_choices)} опций фильтрации:")
            for value, label in client_choices:
                if value == '':
                    print(f"  - {label} (показать все)")
                elif value == 'no_client':
                    print(f"  - {label} (аккаунты без клиента)")
                else:
                    try:
                        from cabinet.models import Client
                        client = Client.objects.get(id=value)
                        account_count = client.accounts.count()
                        active_count = client.accounts.filter(status='ACTIVE').count()
                        print(f"  - {label}: {account_count} аккаунтов ({active_count} активных)")
                    except:
                        print(f"  - {label}: клиент не найден")
        else:
            print("⚠ Choices клиентов пусты (возможно, cabinet app недоступен)")
    else:
        print("✗ Поле client_filter не найдено в форме")
    
    # Проверяем аккаунты с клиентами
    accounts_with_client = InstagramAccount.objects.filter(client__isnull=False)
    accounts_without_client = InstagramAccount.objects.filter(client__isnull=True)
    
    print(f"\n=== Статистика аккаунтов ===")
    print(f"Аккаунтов с клиентом: {accounts_with_client.count()}")
    print(f"Аккаунтов без клиента: {accounts_without_client.count()}")
    
    # Показываем примеры аккаунтов с клиентами
    if accounts_with_client.exists():
        print(f"\nПримеры аккаунтов с клиентами:")
        for account in accounts_with_client[:5]:
            print(f"  - {account.username} → {account.client.name}")

if __name__ == "__main__":
    test_client_filter()