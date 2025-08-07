#!/usr/bin/env python3
"""
Быстрый скрипт для тестирования email и 2FA
"""

import os
import sys
import django
import asyncio

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from uploader.tests_email_2fa import Email2FATestCase, EmailServerTestSuite


async def quick_test():
    """Быстрый тест основных функций"""
    print("[START] QUICK EMAIL AND 2FA TEST")
    print("=" * 50)
    
    # Создаем тестовый экземпляр
    test_case = Email2FATestCase()
    test_case.setUp()
    
    # Получаем аккаунты с email
    from uploader.models import InstagramAccount
    from asgiref.sync import sync_to_async
    
    accounts_with_email = await sync_to_async(list)(
        InstagramAccount.objects.filter(
            email_username__isnull=False,
            email_password__isnull=False
        ).exclude(email_username="", email_password="")
    )
    
    if not accounts_with_email:
        print("[FAIL] No accounts with email found")
        return
    
    print(f"📧 Found {len(accounts_with_email)} accounts with email")
    
    # Тестируем первые 3 аккаунта
    test_accounts = accounts_with_email[:3]
    
    for i, account in enumerate(test_accounts, 1):
        print(f"\n🔍 Testing account {i}/{len(test_accounts)}: {account.username}")
        print(f"   Email: {account.email_username}")
        
        # Тест подключения к почте
        email_result = await test_case.test_email_connection_async(account)
        
        # Тест 2FA если есть
        if account.tfa_secret:
            tfa_result = await test_case.test_2fa_api_async(account)
        
        await asyncio.sleep(1)
    
    print("\n[OK] Quick test completed!")


if __name__ == "__main__":
    try:
        asyncio.run(quick_test())
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n[FAIL] Error: {str(e)}")
        import traceback
        traceback.print_exc() 