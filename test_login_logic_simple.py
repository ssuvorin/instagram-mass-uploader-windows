#!/usr/bin/env python3
"""
Простой тест для проверки логики входа и 2FA без Django зависимостей
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Мокаем Django модели для тестирования
class MockModels:
    pass

sys.modules['uploader.models'] = MockModels()

async def test_2fa_api():
    """Тест API для получения 2FA кодов"""
    print("🧪 Тестирование 2FA API...")
    
    try:
        import aiohttp
        
        # Тестируем API для получения 2FA кода
        test_secret = "JBSWY3DPEHPK3PXP"  # Тестовый секрет
        api_url = f"https://2fa.fb.rip/api/otp/{test_secret}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, timeout=10) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        if response_data.get("ok") and response_data.get("data", {}).get("otp"):
                            code = response_data["data"]["otp"]
                            print(f"[OK] 2FA API работает, получен код: {code}")
                            return True
                        else:
                            print(f"[FAIL] 2FA API вернул некорректный ответ: {response_data}")
                            return False
                    else:
                        print(f"[FAIL] 2FA API недоступен, статус: {response.status}")
                        return False
            except asyncio.TimeoutError:
                print("[FAIL] 2FA API таймаут")
                return False
            except Exception as e:
                print(f"[FAIL] Ошибка 2FA API: {str(e)}")
                return False
                
    except ImportError:
        print("[FAIL] aiohttp не установлен")
        return False

def test_email_client():
    """Тест Email клиента"""
    print("\n📧 Тестирование Email клиента...")
    
    try:
        # Добавляем путь к email_client
        sys.path.append(os.path.join(os.path.dirname(__file__), 'bot', 'src', 'instagram_uploader'))
        
        try:
            from email_client import Email
            print("[OK] Email клиент импортирован успешно")
            
            # Тестируем создание клиента
            test_email = "test@gmail.com"
            test_password = "test_password"
            
            try:
                email_client = Email(test_email, test_password)
                print(f"[OK] Email клиент создан для домена: {email_client.domain}")
                print(f"[OK] Конфигурация сервера: {email_client.server_config}")
                return True
            except Exception as e:
                print(f"[FAIL] Ошибка создания Email клиента: {str(e)}")
                return False
                
        except ImportError as e:
            print(f"[FAIL] Не удалось импортировать Email клиент: {str(e)}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Общая ошибка тестирования Email клиента: {str(e)}")
        return False

def test_verification_keywords():
    """Тест ключевых слов для определения типа верификации"""
    print("\n🔍 Тестирование ключевых слов верификации...")
    
    # Тестовые тексты страниц
    test_cases = [
        {
            "text": "Enter the 6-digit code from your authenticator app",
            "expected": "authenticator",
            "description": "Authenticator app verification"
        },
        {
            "text": "We sent you a login code. Enter it below to sign in.",
            "expected": "email_code", 
            "description": "Email code verification"
        },
        {
            "text": "Enter your email address to receive a verification code",
            "expected": "email_field",
            "description": "Email field input"
        },
        {
            "text": "Welcome to Instagram",
            "expected": "unknown",
            "description": "No verification required"
        }
    ]
    
    # Определяем ключевые слова (упрощенная версия)
    EMAIL_VERIFICATION_KEYWORDS = [
        'we sent you a login code', 'мы отправили вам код для входа',
        'login code was sent', 'код для входа отправлен',
        'check your email', 'проверьте почту',
        'sent to your email', 'отправлен на вашу почту'
    ]
    
    NON_EMAIL_VERIFICATION_KEYWORDS = [
        'google authenticator', 'authentication app',
        'authenticator app', 'two-factor app'
    ]
    
    CODE_ENTRY_KEYWORDS = [
        'enter the code', 'введите код',
        'enter the 6-digit code', 'введите 6-значный код'
    ]
    
    results = []
    for case in test_cases:
        text = case["text"].lower()
        
        is_email_verification = any(keyword in text for keyword in EMAIL_VERIFICATION_KEYWORDS)
        is_code_entry = any(keyword in text for keyword in CODE_ENTRY_KEYWORDS)
        is_non_email = any(keyword in text for keyword in NON_EMAIL_VERIFICATION_KEYWORDS)
        
        # Простая логика определения типа
        if is_non_email:
            result = "authenticator"
        elif is_email_verification:
            result = "email_code"
        elif "enter your email" in text:
            result = "email_field"
        else:
            result = "unknown"
        
        success = result == case["expected"]
        status = "[OK]" if success else "[FAIL]"
        
        print(f"{status} {case['description']}: {result} (ожидалось: {case['expected']})")
        results.append(success)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\nТочность определения типа верификации: {success_rate:.1f}%")
    return success_rate > 75

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов логики входа...\n")
    
    tests = [
        ("2FA API", test_2fa_api()),
        ("Email Client", test_email_client()),
        ("Verification Keywords", test_verification_keywords())
    ]
    
    results = []
    for test_name, test_func in tests:
        if asyncio.iscoroutine(test_func):
            result = await test_func
        else:
            result = test_func
        results.append((test_name, result))
    
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print("="*60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nИтого: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно!")
    else:
        print("⚠️  Некоторые тесты не пройдены, требуется исправление")
        
        print("\n📝 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
        for test_name, result in results:
            if not result:
                if test_name == "2FA API":
                    print("- Проверить доступность API https://2fa.fb.rip/api/otp/")
                    print("- Установить aiohttp: pip install aiohttp")
                elif test_name == "Email Client":
                    print("- Проверить путь к модулю email_client")
                    print("- Убедиться что все зависимости установлены")
                elif test_name == "Verification Keywords":
                    print("- Обновить ключевые слова для определения типа верификации")
                    print("- Улучшить логику классификации")

if __name__ == "__main__":
    asyncio.run(main()) 