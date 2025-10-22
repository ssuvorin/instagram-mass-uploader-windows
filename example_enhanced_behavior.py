#!/usr/bin/env python
"""
Пример использования улучшенного человеческого поведения в bulk upload
"""

import sys
import os

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from uploader.human_behavior_config import get_behavior_config
from uploader.human_behavior import get_behavior_monitor
from uploader.constants import TimeConstants

# Use centralized logging - all logs go to django.log
logger = logging.getLogger('scripts.example_enhanced_behavior')

def demo_enhanced_behavior():
    """Демонстрация улучшенного человеческого поведения"""
    
    print("[START] Демонстрация улучшенного человеческого поведения для bulk upload\n")
    
    # 1. Конфигурация поведения
    print("1️⃣ Настройка конфигурации поведения:")
    config = get_behavior_config()
    
    # Показываем текущую конфигурацию
    summary = config.get_summary()
    print(f"   📊 Текущий профиль: {summary['profile_type']}")
    print(f"   ⚡ Скорость печати: {summary['typing_speed']}x")
    print(f"   [FAIL] Частота ошибок: {summary['error_rate']*100:.1f}%")
    print(f"   [PAUSE]  Вероятность перерывов: {summary['break_probability']*100:.1f}%")
    
    # 2. Создание различных профилей
    print("\n2️⃣ Создание профилей поведения:")
    
    profiles = [
        ('stealth', 'Максимальная имитация человека'),
        ('fast_worker', 'Быстрый и эффективный'),
        ('casual_user', 'Неспешный пользователь'),
        ('night_owl', 'Ночная работа')
    ]
    
    for profile_name, description in profiles:
        print(f"   🎭 {profile_name}: {description}")
    
    # 3. Демонстрация стелс-режима
    print("\n3️⃣ Включение стелс-режима:")
    config.enable_stealth_mode()
    
    stealth_summary = config.get_summary()
    print(f"   🥷 Стелс-режим активирован!")
    print(f"   📈 Новая скорость печати: {stealth_summary['typing_speed']}x")
    print(f"   📈 Новая частота ошибок: {stealth_summary['error_rate']*100:.1f}%")
    
    # 4. Адаптация к времени суток
    print("\n4️⃣ Адаптация к времени суток:")
    
    time_scenarios = [
        (2, "Ночь", "Очень медленное поведение"),
        (9, "Утро", "Медленное поведение"),
        (14, "День", "Нормальное поведение"),
        (20, "Вечер", "Быстрое поведение")
    ]
    
    for hour, period, behavior in time_scenarios:
        print(f"   🕐 {hour:02d}:00 ({period}): {behavior}")
    
    # 5. Мониторинг поведения
    print("\n5️⃣ Мониторинг и анализ поведения:")
    monitor = get_behavior_monitor()
    
    # Симулируем некоторые действия
    print("   📊 Симуляция действий...")
    
    for i in range(10):
        success = i % 3 != 0  # 70% успешных действий
        duration = 1.0 + (i * 0.1)  # Увеличивающаяся продолжительность
        monitor.record_action(f'action_{i}', duration, success, {'video_index': i})
    
    # Получаем рекомендации
    recommendations = monitor.get_recommendations()
    print("   💡 Рекомендации по оптимизации:")
    for rec in recommendations:
        print(f"      • {rec}")
    
    # 6. Демонстрация расчета задержек
    print("\n6️⃣ Улучшенный расчет задержек:")
    
    # Примеры расчета задержек для разных сценариев
    scenarios = [
        (1, 5, 0, 0, "Первый аккаунт"),
        (3, 5, 2, 1, "Средний прогресс с ошибками"),
        (5, 5, 3, 2, "Последний аккаунт")
    ]
    
    # Импортируем функцию (в реальности она уже доступна)
    try:
        from uploader.bulk_tasks_playwright import get_enhanced_account_delay
        
        for current, total, success, failed, description in scenarios:
            delay = get_enhanced_account_delay(current, total, success, failed)
            print(f"   ⏱️  {description}: {delay:.1f}s")
    except ImportError:
        print("   [WARN]  Функция расчета задержек не доступна в демо-режиме")
    
    # 7. Оптимизация для определенного времени
    print("\n7️⃣ Оптимизация для рабочего времени:")
    config.optimize_for_time_period(9, 17)  # Рабочие часы
    
    # 8. Сохранение конфигурации
    print("\n8️⃣ Сохранение конфигурации:")
    config.save_config()
    print("   💾 Конфигурация сохранена в human_behavior_config.json")
    
    # 9. Показываем улучшения
    print("\n✨ РЕЗЮМЕ УЛУЧШЕНИЙ:")
    improvements = [
        "[BRAIN] Адаптивные профили пользователей (консервативный, нормальный, агрессивный, случайный)",
        "🕐 Задержки, адаптирующиеся к времени суток",
        "💪 Симуляция усталости и прогрессивного замедления",
        "[TARGET] Интеллектуальные перерывы на основе активности",
        "[FAIL] Улучшенная симуляция ошибок с соседними клавишами",
        "🖱️ Реалистичные движения мыши с законом Фитца",
        "📊 Мониторинг и анализ поведения в реальном времени",
        "⚙️ Гибкая конфигурация через JSON файлы",
        "🎭 Различные профили поведения для разных задач",
        "[RETRY] Адаптивная система, обучающаяся на основе результатов"
    ]
    
    for improvement in improvements:
        print(f"   {improvement}")
    
    print(f"\n[PARTY] Система человеческого поведения значительно улучшена!")
    print(f"[TOOL] Настройки можно изменить в файле uploader/human_behavior_config.json")

if __name__ == "__main__":
    demo_enhanced_behavior() 