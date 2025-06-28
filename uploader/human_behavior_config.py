"""
Конфигурация человеческого поведения для Instagram bulk upload
Позволяет тонкую настройку параметров поведения
"""

import json
import os
from datetime import datetime
from .constants import TimeConstants

class HumanBehaviorConfig:
    """Класс для управления конфигурацией человеческого поведения"""
    
    DEFAULT_CONFIG = {
        # Базовые настройки
        'enabled': True,
        'profile_type': 'normal',  # conservative, normal, aggressive, casual
        'adapt_to_time_of_day': True,
        'enable_fatigue_simulation': True,
        'enable_break_simulation': True,
        
        # Настройки задержек
        'delay_multipliers': {
            'typing': 1.0,
            'clicking': 0.8,
            'thinking': 1.2,
            'resting': 1.5,
            'navigation': 1.0
        },
        
        # Настройки ошибок
        'error_simulation': {
            'enabled': True,
            'base_error_rate': 0.05,
            'fatigue_multiplier': 1.5,
            'frustration_multiplier': 1.3,
            'error_types': ['wrong_char', 'double_char', 'transpose']
        },
        
        # Настройки перерывов
        'break_settings': {
            'micro_break_probability': 0.15,
            'short_break_probability': 0.08,
            'long_break_probability': 0.03,
            'fatigue_break_threshold': 1.8,
            'error_recovery_break': True
        },
        
        # Настройки времени суток
        'time_multipliers': {
            'night': 2.0,      # 23:00 - 6:00
            'morning': 1.5,    # 7:00 - 11:00
            'day': 1.0,        # 12:00 - 17:00
            'evening': 0.8     # 18:00 - 22:00
        },
        
        # Настройки аккаунтов
        'account_settings': {
            'min_delay_between_accounts': 30,
            'max_delay_between_accounts': 120,
            'progressive_delay_factor': 1.1,
            'error_penalty_multiplier': 1.5,
            'batch_processing_delay': 300
        },
        
        # Настройки видео
        'video_settings': {
            'min_delay_between_videos': 180,
            'max_delay_between_videos': 420,
            'fatigue_growth_rate': 0.15,
            'complex_content_multiplier': 1.5,
            'max_video_delay': 1200
        },
        
        # Экспериментальные настройки
        'experimental': {
            'enable_ai_behavior_adaptation': False,
            'use_machine_learning_delays': False,
            'adaptive_error_recovery': True,
            'dynamic_profile_switching': False
        }
    }
    
    def __init__(self, config_path=None):
        self.config_path = config_path or os.path.join('uploader', 'human_behavior_config.json')
        self.config = self.load_config()
        
    def load_config(self):
        """Загрузить конфигурацию из файла"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Обновляем дефолтную конфигурацию загруженными значениями
                    config = self.DEFAULT_CONFIG.copy()
                    self._deep_update(config, loaded_config)
                    return config
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
        
        return self.DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """Сохранить конфигурацию в файл"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"Конфигурация сохранена в {self.config_path}")
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
    
    def _deep_update(self, base_dict, update_dict):
        """Глубокое обновление словаря"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def get(self, key_path, default=None):
        """Получить значение конфигурации по пути (например, 'delay_multipliers.typing')"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path, value):
        """Установить значение конфигурации по пути"""
        keys = key_path.split('.')
        target = self.config
        
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        target[keys[-1]] = value
    
    def reset_to_defaults(self):
        """Сбросить конфигурацию к значениям по умолчанию"""
        self.config = self.DEFAULT_CONFIG.copy()
    
    def create_profile(self, profile_name, base_profile='normal'):
        """Создать новый профиль поведения"""
        profiles = {
            'conservative': {
                'delay_multipliers': {'typing': 1.3, 'clicking': 1.2, 'thinking': 1.5},
                'error_simulation': {'base_error_rate': 0.02},
                'break_settings': {'micro_break_probability': 0.20}
            },
            'normal': {
                'delay_multipliers': {'typing': 1.0, 'clicking': 1.0, 'thinking': 1.0},
                'error_simulation': {'base_error_rate': 0.05},
                'break_settings': {'micro_break_probability': 0.15}
            },
            'aggressive': {
                'delay_multipliers': {'typing': 0.7, 'clicking': 0.6, 'thinking': 0.8},
                'error_simulation': {'base_error_rate': 0.08},
                'break_settings': {'micro_break_probability': 0.10}
            },
            'casual': {
                'delay_multipliers': {'typing': 1.5, 'clicking': 1.3, 'thinking': 1.8},
                'error_simulation': {'base_error_rate': 0.12},
                'break_settings': {'micro_break_probability': 0.25}
            }
        }
        
        if base_profile in profiles:
            profile_config = profiles[base_profile]
            self._deep_update(self.config, profile_config)
            self.set('profile_type', profile_name)
            print(f"Создан профиль '{profile_name}' на базе '{base_profile}'")
        else:
            print(f"Базовый профиль '{base_profile}' не найден")
    
    def optimize_for_time_period(self, start_hour, end_hour):
        """Оптимизировать конфигурацию для определенного времени"""
        current_hour = datetime.now().hour
        
        if start_hour <= current_hour <= end_hour:
            # Активный период - ускоряем
            self.set('delay_multipliers.typing', 0.8)
            self.set('delay_multipliers.clicking', 0.7)
            self.set('break_settings.micro_break_probability', 0.10)
            print(f"Оптимизация для активного периода {start_hour}-{end_hour}")
        else:
            # Неактивный период - замедляем
            self.set('delay_multipliers.typing', 1.3)
            self.set('delay_multipliers.clicking', 1.2)
            self.set('break_settings.micro_break_probability', 0.20)
            print(f"Оптимизация для неактивного периода")
    
    def enable_stealth_mode(self):
        """Включить стелс-режим с максимальной имитацией человека"""
        stealth_config = {
            'delay_multipliers': {
                'typing': 1.4,
                'clicking': 1.3,
                'thinking': 1.6,
                'resting': 2.0
            },
            'error_simulation': {
                'base_error_rate': 0.08,
                'fatigue_multiplier': 2.0
            },
            'break_settings': {
                'micro_break_probability': 0.25,
                'short_break_probability': 0.15,
                'long_break_probability': 0.08
            },
            'account_settings': {
                'min_delay_between_accounts': 60,
                'max_delay_between_accounts': 180,
                'progressive_delay_factor': 1.3
            }
        }
        
        self._deep_update(self.config, stealth_config)
        print("Включен стелс-режим с усиленной имитацией человеческого поведения")
    
    def get_summary(self):
        """Получить сводку текущей конфигурации"""
        return {
            'profile_type': self.get('profile_type'),
            'typing_speed': self.get('delay_multipliers.typing'),
            'error_rate': self.get('error_simulation.base_error_rate'),
            'break_probability': self.get('break_settings.micro_break_probability'),
            'time_adaptation': self.get('adapt_to_time_of_day'),
            'fatigue_simulation': self.get('enable_fatigue_simulation')
        }

# Глобальный экземпляр конфигурации
behavior_config = HumanBehaviorConfig()

def get_behavior_config():
    """Получить глобальную конфигурацию поведения"""
    return behavior_config

def reload_behavior_config():
    """Перезагрузить конфигурацию из файла"""
    global behavior_config
    behavior_config = HumanBehaviorConfig()
    return behavior_config 