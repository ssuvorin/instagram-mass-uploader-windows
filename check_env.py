#!/usr/bin/env python
"""
Скрипт для проверки настроек окружения для Windows без Docker
"""
import os
import logging
from dotenv import load_dotenv

# Use centralized logging - all logs go to django.log
logger = logging.getLogger('scripts.check_env')

# Загружаем .env файл
load_dotenv()

print("=" * 60)
print("ПРОВЕРКА НАСТРОЕК ДЛЯ WINDOWS БЕЗ DOCKER")
print("=" * 60)

# Проверяем ключевые переменные
dolphin_api_host = os.environ.get("DOLPHIN_API_HOST")
docker_container = os.environ.get("DOCKER_CONTAINER")
dolphin_api_token = os.environ.get("DOLPHIN_API_TOKEN")

print(f"DOLPHIN_API_HOST: {dolphin_api_host}")
print(f"DOCKER_CONTAINER: {docker_container}")
print(f"DOLPHIN_API_TOKEN: {'[SET]' if dolphin_api_token else '[NOT SET]'}")

print("\n" + "=" * 60)
print("ДИАГНОСТИКА")
print("=" * 60)

# Проверяем настройки
errors = []
warnings = []

if dolphin_api_host == "http://host.docker.internal:3001":
    errors.append("[FAIL] DOLPHIN_API_HOST использует Docker настройки!")
    print("[FAIL] ОШИБКА: DOLPHIN_API_HOST=http://host.docker.internal:3001")
    print("   Это настройка для Docker, а вы запускаете без Docker")
    print("   ИСПРАВЛЕНИЕ: Измените на DOLPHIN_API_HOST=http://localhost:3001")
elif dolphin_api_host == "http://localhost:3001":
    print("[OK] DOLPHIN_API_HOST правильно настроен для Windows без Docker")
elif dolphin_api_host == "http://127.0.0.1:3001":
    print("[OK] DOLPHIN_API_HOST правильно настроен для Windows без Docker")
else:
    warnings.append(f"[WARN] Нестандартный DOLPHIN_API_HOST: {dolphin_api_host}")

if docker_container == "1":
    errors.append("[FAIL] DOCKER_CONTAINER установлен в 1!")
    print("[FAIL] ОШИБКА: DOCKER_CONTAINER=1")
    print("   Это говорит системе что вы в Docker контейнере")
    print("   ИСПРАВЛЕНИЕ: Установите DOCKER_CONTAINER=0 или уберите эту переменную")
elif docker_container == "0" or docker_container is None:
    print("[OK] DOCKER_CONTAINER правильно настроен для Windows без Docker")
else:
    warnings.append(f"[WARN] Нестандартное значение DOCKER_CONTAINER: {docker_container}")

if not dolphin_api_token:
    errors.append("[FAIL] DOLPHIN_API_TOKEN не установлен!")
    print("[FAIL] ОШИБКА: DOLPHIN_API_TOKEN не найден")
    print("   ИСПРАВЛЕНИЕ: Получите токен в Dolphin Anty и добавьте в .env")

print("\n" + "=" * 60)
print("РЕЗУЛЬТАТ")
print("=" * 60)

if errors:
    print("[FAIL] НАЙДЕНЫ КРИТИЧЕСКИЕ ОШИБКИ:")
    for error in errors:
        print(f"   {error}")
    print("\nИСПРАВЬТЕ ЭТИ ОШИБКИ В .env ФАЙЛЕ И ПЕРЕЗАПУСТИТЕ DJANGO")
else:
    print("[OK] Все настройки выглядят правильно!")

if warnings:
    print("\n[WARN] ПРЕДУПРЕЖДЕНИЯ:")
    for warning in warnings:
        print(f"   {warning}")

print("\n" + "=" * 60)
print("ТЕСТ ПОДКЛЮЧЕНИЯ К DOLPHIN ANTY")
print("=" * 60)

try:
    import requests
    
    # Определяем хост для подключения
    if docker_container == "1":
        test_host = "http://host.docker.internal:3001"
    else:
        test_host = "http://localhost:3001"
    
    print(f"Тестируем подключение к: {test_host}")
    
    response = requests.get(f"{test_host}/v1.0/browser_profiles", timeout=5)
    if response.status_code == 200:
        print("[OK] Dolphin Anty API отвечает!")
    else:
        print(f"[WARN] Dolphin Anty API вернул статус: {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("[FAIL] Не удается подключиться к Dolphin Anty!")
    print("   Убедитесь что Dolphin Anty запущен и Local API включен")
except Exception as e:
    print(f"[FAIL] Ошибка при подключении: {e}")

print("\n" + "=" * 60)
print("РЕКОМЕНДУЕМЫЙ .env ФАЙЛ ДЛЯ WINDOWS БЕЗ DOCKER")
print("=" * 60)

print("""
# Django настройки
SECRET_KEY=your-super-secret-key-change-this
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,YOUR_SERVER_IP

# Dolphin Anty API (БЕЗ DOCKER!)
DOLPHIN_API_TOKEN=your-dolphin-api-token-here
DOLPHIN_API_HOST=http://localhost:3001
DOCKER_CONTAINER=0

# Опционально
RUCAPTCHA_API_KEY=your-rucaptcha-key
LOG_LEVEL=INFO
MAX_CONCURRENT_TASKS=2
""")

print("=" * 60) 