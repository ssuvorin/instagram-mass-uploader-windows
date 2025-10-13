# -*- coding: utf-8 -*-
"""
Конфигурация для обработки rate limiting и ошибок Instagram API
"""

import random
import time
from typing import Dict, Any

class RateLimitingConfig:
    """Конфигурация для обработки rate limiting"""
    
    # Базовые задержки (в секундах)
    BASE_DELAYS = {
        'user_resolution': (1.0, 3.0),      # Задержка при разрешении пользователей
        'location_search': (1.0, 3.0),      # Задержка при поиске локаций
        'upload_attempt': (10.0, 20.0),     # Увеличена задержка перед загрузкой
        'account_switch': (30.0, 120.0),    # Задержка между аккаунтами
        'video_upload': (180.0, 420.0),     # Задержка между видео
    }
    
    # Retry конфигурация
    RETRY_CONFIG = {
        'max_retries': 3,
        'base_backoff': 10,                 # Базовое время ожидания
        'max_backoff': 300,                 # Максимальное время ожидания (5 минут)
        'exponential_base': 2,              # Основание для экспоненциального backoff
    }
    
    # Специальные задержки для ошибок 429
    RATE_LIMIT_DELAYS = {
        'user_resolution': (60, 180),       # 1-3 минуты для пользователей
        'location_search': (30, 120),       # 30 сек - 2 минуты для локаций
        'upload_attempt': (300, 600),       # 5-10 минут для загрузки (увеличено)
        'account_switch': (600, 1200),      # 10-20 минут между аккаунтами (увеличено)
    }
    
    # Множители для адаптации к времени суток
    TIME_OF_DAY_MULTIPLIERS = {
        'night': 2.0,      # 00:00 - 06:00
        'morning': 1.5,    # 06:00 - 12:00
        'afternoon': 1.0,  # 12:00 - 18:00
        'evening': 0.8,    # 18:00 - 00:00
    }
    
    @classmethod
    def get_delay(cls, operation: str, is_retry: bool = False, is_rate_limited: bool = False) -> float:
        """Получить задержку для операции"""
        if is_rate_limited and operation in cls.RATE_LIMIT_DELAYS:
            min_delay, max_delay = cls.RATE_LIMIT_DELAYS[operation]
        elif operation in cls.BASE_DELAYS:
            min_delay, max_delay = cls.BASE_DELAYS[operation]
        else:
            min_delay, max_delay = 1.0, 5.0
        
        # Применяем множитель для retry
        if is_retry:
            multiplier = cls.RATE_LIMIT_DELAYS.get(operation, (1.0, 1.0))[0] / min_delay
            min_delay *= multiplier
            max_delay *= multiplier
        
        # Применяем множитель времени суток
        time_multiplier = cls.get_time_of_day_multiplier()
        min_delay *= time_multiplier
        max_delay *= time_multiplier
        
        return random.uniform(min_delay, max_delay)
    
    @classmethod
    def get_retry_delay(cls, attempt: int, operation: str = 'default') -> float:
        """Получить задержку для retry с экспоненциальным backoff"""
        base = cls.RETRY_CONFIG['base_backoff']
        max_delay = cls.RETRY_CONFIG['max_backoff']
        exponential_base = cls.RETRY_CONFIG['exponential_base']
        
        # Экспоненциальный backoff
        delay = base * (exponential_base ** attempt)
        delay = min(delay, max_delay)
        
        # Добавляем случайность для избежания thundering herd
        jitter = random.uniform(0.5, 1.5)
        delay *= jitter
        
        return delay
    
    @classmethod
    def get_time_of_day_multiplier(cls) -> float:
        """Получить множитель в зависимости от времени суток"""
        current_hour = time.localtime().tm_hour
        
        if 0 <= current_hour < 6:
            return cls.TIME_OF_DAY_MULTIPLIERS['night']
        elif 6 <= current_hour < 12:
            return cls.TIME_OF_DAY_MULTIPLIERS['morning']
        elif 12 <= current_hour < 18:
            return cls.TIME_OF_DAY_MULTIPLIERS['afternoon']
        else:
            return cls.TIME_OF_DAY_MULTIPLIERS['evening']
    
    @classmethod
    def should_retry(cls, error: Exception, attempt: int) -> bool:
        """Определить, стоит ли повторять попытку"""
        if attempt >= cls.RETRY_CONFIG['max_retries']:
            return False
        
        error_msg = str(error).lower()
        
        # Не повторяем для определенных ошибок
        if any(phrase in error_msg for phrase in [
            'challenge required',
            'verification required',
            'incorrect password',
            'user not found',
            'invalid credentials'
        ]):
            return False
        
        # Повторяем для rate limiting и временных ошибок
        if any(phrase in error_msg for phrase in [
            '429',
            'too many',
            'rate limit',
            'throttled',
            'timeout',
            'connection',
            'network'
        ]):
            return True
        
        # Повторяем для общих ошибок (но меньше раз)
        return attempt < 2

class InstagramAPIErrorHandler:
    """Обработчик ошибок Instagram API"""
    
    @staticmethod
    def is_rate_limit_error(error: Exception) -> bool:
        """Проверить, является ли ошибка rate limiting"""
        error_msg = str(error).lower()
        return any(phrase in error_msg for phrase in [
            '429',
            'too many',
            'rate limit',
            'throttled'
        ])
    
    @staticmethod
    def is_challenge_error(error: Exception) -> bool:
        """Проверить, является ли ошибка challenge/verification"""
        error_msg = str(error).lower()
        return any(phrase in error_msg for phrase in [
            'challenge required',
            'verification required',
            'checkpoint'
        ])
    
    @staticmethod
    def is_network_error(error: Exception) -> bool:
        """Проверить, является ли ошибка сетевой"""
        error_msg = str(error).lower()
        return any(phrase in error_msg for phrase in [
            'timeout',
            'connection',
            'network',
            'unreachable'
        ])
    
    @staticmethod
    def get_error_category(error: Exception) -> str:
        """Получить категорию ошибки"""
        if InstagramAPIErrorHandler.is_rate_limit_error(error):
            return 'rate_limit'
        elif InstagramAPIErrorHandler.is_challenge_error(error):
            return 'challenge'
        elif InstagramAPIErrorHandler.is_network_error(error):
            return 'network'
        else:
            return 'unknown'

