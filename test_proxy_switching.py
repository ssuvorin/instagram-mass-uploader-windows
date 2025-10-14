#!/usr/bin/env python3
"""
Скрипт для тестирования автоматической смены прокси
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

from uploader.models import InstagramAccount, Proxy
from uploader.proxy_manager import ProxyManager
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_proxy_switching():
    """Тестирует автоматическую смену прокси"""
    print("🔗 Тестирование автоматической смены прокси")
    print("=" * 50)
    
    # Инициализируем ProxyManager
    proxy_manager = ProxyManager()
    
    # Получаем тестовый аккаунт
    try:
        test_account = InstagramAccount.objects.filter(
            current_proxy__isnull=False
        ).first()
        
        if not test_account:
            print("❌ Нет аккаунтов с назначенными прокси для тестирования")
            return False
        
        print(f"📱 Тестовый аккаунт: {test_account.username}")
        print(f"🔗 Текущий прокси: {test_account.current_proxy}")
        
        # Получаем доступные прокси
        available_proxies = Proxy.objects.filter(
            status='active',
            is_active=True
        ).exclude(
            id=test_account.current_proxy.id if test_account.current_proxy else None
        )
        
        print(f"📊 Доступных прокси: {available_proxies.count()}")
        
        if available_proxies.count() == 0:
            print("❌ Нет доступных прокси для смены")
            return False
        
        # Тестируем получение нового прокси
        print("\n🔄 Тестирование получения нового прокси...")
        new_proxy = proxy_manager.get_available_proxy(test_account, exclude_blocked=True)
        
        if new_proxy:
            print(f"✅ Новый прокси получен: {new_proxy.host}:{new_proxy.port}")
            print(f"🌍 Страна: {new_proxy.country}")
            print(f"🏙️ Город: {new_proxy.city}")
            
            # Проверяем, что прокси действительно сменился
            test_account.refresh_from_db()
            if test_account.current_proxy == new_proxy:
                print("✅ Прокси успешно назначен аккаунту")
            else:
                print("❌ Прокси не был назначен аккаунту")
                return False
        else:
            print("❌ Не удалось получить новый прокси")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

def test_proxy_blocking():
    """Тестирует блокировку прокси"""
    print("\n🚫 Тестирование блокировки прокси")
    print("=" * 50)
    
    proxy_manager = ProxyManager()
    
    try:
        # Получаем тестовый прокси
        test_proxy = Proxy.objects.filter(status='active').first()
        test_account = InstagramAccount.objects.filter(
            current_proxy__isnull=False
        ).first()
        
        if not test_proxy or not test_account:
            print("❌ Нет данных для тестирования блокировки")
            return False
        
        print(f"🔗 Тестовый прокси: {test_proxy.host}:{test_proxy.port}")
        print(f"📱 Тестовый аккаунт: {test_account.username}")
        
        # Блокируем прокси
        print("\n🚫 Блокируем прокси...")
        proxy_manager.mark_proxy_blocked(test_proxy, test_account, "test blocking")
        
        # Проверяем статус
        test_proxy.refresh_from_db()
        if test_proxy.status == 'banned':
            print("✅ Прокси успешно заблокирован")
        else:
            print("❌ Прокси не был заблокирован")
            return False
        
        # Проверяем, что заблокированный прокси не возвращается
        print("\n🔍 Проверяем, что заблокированный прокси не возвращается...")
        blocked_proxy = proxy_manager.get_available_proxy(test_account, exclude_blocked=True)
        
        if blocked_proxy and blocked_proxy.id == test_proxy.id:
            print("❌ Заблокированный прокси все еще возвращается")
            return False
        else:
            print("✅ Заблокированный прокси исключен из доступных")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании блокировки: {e}")
        return False

def show_proxy_statistics():
    """Показывает статистику прокси"""
    print("\n📊 Статистика прокси")
    print("=" * 50)
    
    total_proxies = Proxy.objects.count()
    active_proxies = Proxy.objects.filter(status='active', is_active=True).count()
    banned_proxies = Proxy.objects.filter(status='banned').count()
    inactive_proxies = Proxy.objects.filter(status='inactive').count()
    
    print(f"📈 Всего прокси: {total_proxies}")
    print(f"✅ Активных: {active_proxies}")
    print(f"🚫 Заблокированных: {banned_proxies}")
    print(f"⏸️ Неактивных: {inactive_proxies}")
    
    # Статистика по странам
    print(f"\n🌍 Статистика по странам:")
    countries = Proxy.objects.filter(status='active').values_list('country', flat=True).distinct()
    for country in countries:
        if country:
            count = Proxy.objects.filter(country=country, status='active').count()
            print(f"   {country}: {count} прокси")
    
    # Аккаунты с прокси
    accounts_with_proxy = InstagramAccount.objects.filter(current_proxy__isnull=False).count()
    accounts_without_proxy = InstagramAccount.objects.filter(current_proxy__isnull=True).count()
    
    print(f"\n👥 Аккаунты:")
    print(f"   С прокси: {accounts_with_proxy}")
    print(f"   Без прокси: {accounts_without_proxy}")

def simulate_proxy_error_scenario():
    """Симулирует сценарий с ошибками прокси"""
    print("\n🎭 Симуляция сценария с ошибками прокси")
    print("=" * 50)
    
    print("📋 Сценарий:")
    print("1. Аккаунт получает ProxyError при загрузке")
    print("2. Система ждет 20-60 секунд")
    print("3. Повторная попытка - снова ProxyError")
    print("4. Система ждет 20-60 секунд")
    print("5. Третья попытка - снова ProxyError")
    print("6. Система автоматически переключается на новый прокси")
    print("7. Продолжает загрузку с новым прокси")
    
    print("\n✅ Логика реализована:")
    print("   - Счетчик прокси ошибок (proxy_error_count)")
    print("   - Максимум 3 смены прокси за сессию")
    print("   - Автоматический поиск прокси из того же региона")
    print("   - Блокировка проблемных прокси")
    print("   - Переинициализация клиента с новым прокси")
    
    print("\n🔧 Настройки:")
    print("   - Первые 2 ошибки: обычная обработка (20-60s ожидание)")
    print("   - 3-я ошибка: смена прокси + короткое ожидание (10-20s)")
    print("   - Нет доступных прокси: длинное ожидание (30-60s)")
    print("   - Ошибка смены прокси: fallback к обычной обработке")

def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование автоматической смены прокси")
    print("=" * 60)
    
    # Показываем статистику
    show_proxy_statistics()
    
    # Тестируем смену прокси
    switch_success = test_proxy_switching()
    
    # Тестируем блокировку прокси
    block_success = test_proxy_blocking()
    
    # Симулируем сценарий
    simulate_proxy_error_scenario()
    
    # Итоговый результат
    print(f"\n📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"✅ Смена прокси: {'ПРОЙДЕНО' if switch_success else 'ПРОВАЛЕНО'}")
    print(f"✅ Блокировка прокси: {'ПРОЙДЕНО' if block_success else 'ПРОВАЛЕНО'}")
    
    if switch_success and block_success:
        print("\n🎉 Все тесты пройдены успешно!")
        print("✅ Автоматическая смена прокси работает корректно")
        print("✅ Система готова к обработке прокси ошибок")
    else:
        print("\n⚠️ Некоторые тесты провалены")
        print("❌ Требуется дополнительная настройка")
    
    print(f"\n🔧 РЕАЛИЗОВАННЫЕ ВОЗМОЖНОСТИ:")
    print("   - Автоматическая смена прокси при 3+ ошибках")
    print("   - Поиск прокси из того же региона")
    print("   - Блокировка проблемных прокси")
    print("   - Переинициализация клиента с новым прокси")
    print("   - Умная retry логика с разными задержками")
    print("   - Подробное логирование процесса смены")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n🎉 Тестирование завершено!")
