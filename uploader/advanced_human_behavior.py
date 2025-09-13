"""
Advanced Human Behavior Simulation for Instagram Automation
Максимально человеческое поведение для обхода детекции автоматизации
"""

import asyncio
import random
import math
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from .logging_utils import log_info, log_warning, log_error


class HumanBehaviorProfile:
    """Профиль человеческого поведения"""
    
    def __init__(self):
        self.profile_type = random.choice(['careful', 'normal', 'fast', 'distracted'])
        self.typing_speed = self._get_typing_speed()
        self.error_rate = self._get_error_rate()
        self.pause_frequency = self._get_pause_frequency()
        self.mouse_precision = self._get_mouse_precision()
        
    def _get_typing_speed(self) -> float:
        """Скорость печати (символов в секунду)"""
        speeds = {
            'careful': random.uniform(1.5, 2.5),    # Медленная печать
            'normal': random.uniform(2.5, 4.0),     # Обычная печать
            'fast': random.uniform(4.0, 6.0),       # Быстрая печать
            'distracted': random.uniform(1.0, 3.0)  # Непостоянная скорость
        }
        return speeds[self.profile_type]
    
    def _get_error_rate(self) -> float:
        """Частота ошибок при печати"""
        rates = {
            'careful': 0.01,     # Очень мало ошибок
            'normal': 0.03,      # Обычное количество ошибок
            'fast': 0.08,        # Больше ошибок из-за скорости
            'distracted': 0.12   # Много ошибок из-за невнимательности
        }
        return rates[self.profile_type]
    
    def _get_pause_frequency(self) -> float:
        """Частота пауз для размышления"""
        frequencies = {
            'careful': 0.25,     # Часто думает
            'normal': 0.15,      # Иногда думает
            'fast': 0.05,        # Редко останавливается
            'distracted': 0.30   # Часто отвлекается
        }
        return frequencies[self.profile_type]
    
    def _get_mouse_precision(self) -> float:
        """Точность движения мыши"""
        precisions = {
            'careful': 0.95,     # Очень точные движения
            'normal': 0.85,      # Обычная точность
            'fast': 0.75,        # Менее точные из-за скорости
            'distracted': 0.70   # Неточные движения
        }
        return precisions[self.profile_type]


class AdvancedHumanBehavior:
    """Продвинутая симуляция человеческого поведения"""
    
    def __init__(self, page):
        self.page = page
        self.profile = HumanBehaviorProfile()
        self.session_start = datetime.now()
        self.action_count = 0
        self.last_action_time = datetime.now()
        self.fatigue_level = 0.0
        self.recent_errors = []
        
        log_info(f"[HUMAN_PROFILE] Initialized {self.profile.profile_type} user profile")
    
    def _calculate_fatigue(self) -> float:
        """Вычисляет уровень усталости пользователя"""
        session_duration = (datetime.now() - self.session_start).total_seconds() / 60
        
        # Усталость растет со временем и количеством действий
        time_fatigue = min(session_duration / 30, 1.5)  # Максимум 1.5x через 30 минут
        action_fatigue = min(self.action_count / 100, 1.0)  # Максимум 1.0x через 100 действий
        
        self.fatigue_level = 1.0 + (time_fatigue * 0.4) + (action_fatigue * 0.3)
        return self.fatigue_level
    
    def _get_time_of_day_multiplier(self) -> float:
        """Множитель скорости в зависимости от времени суток"""
        hour = datetime.now().hour
        
        if 6 <= hour <= 9:      # Утро - медленнее
            return random.uniform(1.3, 1.8)
        elif 10 <= hour <= 16:  # День - нормально
            return random.uniform(0.9, 1.2)
        elif 17 <= hour <= 22:  # Вечер - активнее
            return random.uniform(0.7, 1.0)
        else:                   # Ночь - очень медленно
            return random.uniform(1.8, 2.5)
    
    def _should_make_error(self) -> bool:
        """Определяет, должен ли пользователь сделать ошибку"""
        base_error_rate = self.profile.error_rate
        fatigue_multiplier = self._calculate_fatigue()
        
        # Увеличиваем вероятность ошибки при усталости
        adjusted_error_rate = base_error_rate * fatigue_multiplier
        
        return random.random() < adjusted_error_rate
    
    def _should_pause_to_think(self) -> bool:
        """Определяет, должен ли пользователь сделать паузу для размышления"""
        return random.random() < self.profile.pause_frequency
    
    async def _thinking_pause(self, context: str = "general") -> None:
        """Пауза для размышления"""
        thinking_time = random.uniform(0.8, 3.5)
        
        # Увеличиваем время размышления при усталости
        thinking_time *= self._calculate_fatigue()
        
        log_info(f"[HUMAN_THINKING] Pausing {thinking_time:.1f}s to think ({context})")
        await asyncio.sleep(thinking_time)
    
    async def _natural_mouse_movement(self, element) -> None:
        """Естественное движение мыши к элементу"""
        try:
            # Получаем текущую позицию мыши (если возможно)
            current_pos = await self.page.evaluate('() => ({ x: window.mouseX || 0, y: window.mouseY || 0 })')
            
            # Получаем позицию целевого элемента
            box = await element.bounding_box()
            if not box:
                return
            
            # Вычисляем целевую позицию с небольшой случайностью
            target_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            target_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
            
            # Добавляем неточность в зависимости от профиля
            precision = self.profile.mouse_precision
            offset_x = (1 - precision) * random.uniform(-10, 10)
            offset_y = (1 - precision) * random.uniform(-10, 10)
            
            target_x += offset_x
            target_y += offset_y
            
            # Движение мыши с кривой траекторией
            await self._curved_mouse_movement(current_pos['x'], current_pos['y'], target_x, target_y)
            
        except Exception as e:
            log_warning(f"[HUMAN_MOUSE] Natural mouse movement failed: {e}")
    
    async def _curved_mouse_movement(self, start_x: float, start_y: float, end_x: float, end_y: float) -> None:
        """Движение мыши по кривой траектории"""
        steps = random.randint(8, 15)
        
        # Создаем контрольные точки для кривой Безье
        control_x = (start_x + end_x) / 2 + random.uniform(-50, 50)
        control_y = (start_y + end_y) / 2 + random.uniform(-30, 30)
        
        for i in range(steps + 1):
            t = i / steps
            
            # Кривая Безье второго порядка
            x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * control_x + t ** 2 * end_x
            y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * control_y + t ** 2 * end_y
            
            # Добавляем небольшие случайные отклонения
            x += random.uniform(-2, 2)
            y += random.uniform(-2, 2)
            
            await self.page.mouse.move(x, y)
            
            # Переменная скорость движения
            move_delay = random.uniform(0.01, 0.03)
            await asyncio.sleep(move_delay)
    
    async def human_click(self, element, context: str = "general") -> bool:
        """Человеческий клик с естественным поведением"""
        try:
            self.action_count += 1
            
            # Пауза для размышления перед кликом
            if self._should_pause_to_think():
                await self._thinking_pause(f"before_click_{context}")
            
            # Естественное движение мыши к элементу
            await self._natural_mouse_movement(element)
            
            # Небольшая пауза перед кликом
            pre_click_delay = random.uniform(0.1, 0.4)
            await asyncio.sleep(pre_click_delay)
            
            # Hover перед кликом (как делают люди)
            await element.hover()
            await asyncio.sleep(random.uniform(0.05, 0.15))
            
            # Клик с небольшой задержкой
            await element.click()
            
            # Пауза после клика
            post_click_delay = random.uniform(0.2, 0.8) * self._get_time_of_day_multiplier()
            await asyncio.sleep(post_click_delay)
            
            log_info(f"[HUMAN_CLICK] Successfully clicked element ({context})")
            return True
            
        except Exception as e:
            log_error(f"[HUMAN_CLICK] Failed to click element: {e}")
            return False
    
    async def human_type(self, element, text: str, context: str = "general") -> bool:
        """Человеческий ввод текста с ошибками и исправлениями"""
        try:
            self.action_count += 1
            
            # Фокус на элементе
            await element.click()
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # Очистка поля человеческим способом (Ctrl+A + Delete)
            await self.page.keyboard.press('Control+a')
            await asyncio.sleep(random.uniform(0.1, 0.2))
            await self.page.keyboard.press('Delete')
            await asyncio.sleep(random.uniform(0.2, 0.4))
            
            # Печать с человеческими ошибками
            i = 0
            while i < len(text):
                char = text[i]
                
                # Пауза для размышления (иногда)
                if self._should_pause_to_think() and i > 0:
                    await self._thinking_pause(f"typing_{context}")
                
                # Проверяем, нужно ли сделать ошибку
                if self._should_make_error() and i < len(text) - 1:
                    # Делаем ошибку
                    wrong_char = self._get_similar_char(char)
                    await self.page.keyboard.type(wrong_char)
                    
                    # Задержка перед осознанием ошибки
                    mistake_delay = random.uniform(0.3, 1.2)
                    await asyncio.sleep(mistake_delay)
                    
                    # Исправляем ошибку
                    await self.page.keyboard.press('Backspace')
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    log_info(f"[HUMAN_TYPE] Made and corrected typing error: {wrong_char} -> {char}")
                
                # Печатаем правильный символ
                await self.page.keyboard.type(char)
                
                # Вариативная скорость печати
                base_delay = 1.0 / self.profile.typing_speed
                delay = base_delay * random.uniform(0.7, 1.5) * self._get_time_of_day_multiplier()
                
                # Увеличиваем задержку при усталости
                delay *= self._calculate_fatigue()
                
                await asyncio.sleep(delay)
                i += 1
            
            log_info(f"[HUMAN_TYPE] Successfully typed text ({len(text)} chars, {context})")
            return True
            
        except Exception as e:
            log_error(f"[HUMAN_TYPE] Failed to type text: {e}")
            return False
    
    def _get_similar_char(self, char: str) -> str:
        """Получить похожий символ для имитации ошибки печати"""
        # Карта похожих символов на клавиатуре
        similar_chars = {
            'a': ['s', 'q', 'w'],
            's': ['a', 'd', 'w', 'e'],
            'd': ['s', 'f', 'e', 'r'],
            'f': ['d', 'g', 'r', 't'],
            'g': ['f', 'h', 't', 'y'],
            'h': ['g', 'j', 'y', 'u'],
            'j': ['h', 'k', 'u', 'i'],
            'k': ['j', 'l', 'i', 'o'],
            'l': ['k', 'o', 'p'],
            'q': ['w', 'a'],
            'w': ['q', 'e', 'a', 's'],
            'e': ['w', 'r', 's', 'd'],
            'r': ['e', 't', 'd', 'f'],
            't': ['r', 'y', 'f', 'g'],
            'y': ['t', 'u', 'g', 'h'],
            'u': ['y', 'i', 'h', 'j'],
            'i': ['u', 'o', 'j', 'k'],
            'o': ['i', 'p', 'k', 'l'],
            'p': ['o', 'l'],
            'z': ['x', 'a'],
            'x': ['z', 'c', 's'],
            'c': ['x', 'v', 'd'],
            'v': ['c', 'b', 'f'],
            'b': ['v', 'n', 'g'],
            'n': ['b', 'm', 'h'],
            'm': ['n', 'j'],
        }
        
        char_lower = char.lower()
        if char_lower in similar_chars:
            similar = random.choice(similar_chars[char_lower])
            return similar.upper() if char.isupper() else similar
        
        return char
    
    async def human_scroll(self, direction: str = "down", amount: int = 3) -> None:
        """Человеческая прокрутка страницы"""
        try:
            for _ in range(amount):
                if direction == "down":
                    await self.page.mouse.wheel(0, random.randint(100, 300))
                else:
                    await self.page.mouse.wheel(0, -random.randint(100, 300))
                
                # Пауза между прокрутками
                await asyncio.sleep(random.uniform(0.3, 0.8))
                
        except Exception as e:
            log_warning(f"[HUMAN_SCROLL] Scroll failed: {e}")
    
    async def simulate_reading(self, element, estimated_words: int = 10) -> None:
        """Симуляция чтения контента"""
        # Средняя скорость чтения: 200-300 слов в минуту
        reading_speed = random.uniform(200, 300)  # слов в минуту
        reading_time = (estimated_words / reading_speed) * 60  # в секундах
        
        # Добавляем случайность
        reading_time *= random.uniform(0.7, 1.5)
        
        # Учитываем усталость
        reading_time *= self._calculate_fatigue()
        
        log_info(f"[HUMAN_READING] Simulating reading for {reading_time:.1f}s ({estimated_words} words)")
        await asyncio.sleep(reading_time)
    
    async def natural_page_scan(self) -> None:
        """Естественное сканирование страницы глазами"""
        try:
            # Случайные движения мыши для имитации сканирования
            viewport = await self.page.viewport_size()
            
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.5, 1.2))
                
        except Exception as e:
            log_warning(f"[HUMAN_SCAN] Page scan failed: {e}")


# Глобальный экземпляр для использования в async функциях
_global_human_behavior: Optional[AdvancedHumanBehavior] = None


def init_advanced_human_behavior(page) -> AdvancedHumanBehavior:
    """Инициализация продвинутого человеческого поведения"""
    global _global_human_behavior
    _global_human_behavior = AdvancedHumanBehavior(page)
    return _global_human_behavior


def get_advanced_human_behavior() -> Optional[AdvancedHumanBehavior]:
    """Получить экземпляр продвинутого человеческого поведения"""
    return _global_human_behavior