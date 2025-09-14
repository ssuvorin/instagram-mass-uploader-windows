"""
Behavior Profile Implementation
Configurable user behavior profiles - Open/Closed Principle
"""

import random
from typing import Dict, Any
from .interfaces import IBehaviorProfile
try:
    from logging_utils import log_info
except ImportError:
    # Fallback logging for testing
    def log_info(msg): print(f"INFO: {msg}")


class BehaviorProfile(IBehaviorProfile):
    """
    Configurable behavior profile implementation
    Allows extending with new profile types without modifying existing code
    """
    
    # Profile configurations - can be extended without modifying class
    PROFILE_CONFIGS = {
        'careful': {
            'typing_speed': (1.5, 2.5),      # chars per second
            'error_rate': 0.01,              # very few errors
            'pause_frequency': 0.25,         # thinks often
            'mouse_precision': 0.95,         # very precise
            'description': 'Careful user - slow and precise'
        },
        'normal': {
            'typing_speed': (2.5, 4.0),
            'error_rate': 0.03,
            'pause_frequency': 0.15,
            'mouse_precision': 0.85,
            'description': 'Normal user - balanced behavior'
        },
        'fast': {
            'typing_speed': (4.0, 6.0),
            'error_rate': 0.08,
            'pause_frequency': 0.05,
            'mouse_precision': 0.75,
            'description': 'Fast user - quick but less precise'
        },
        'distracted': {
            'typing_speed': (1.0, 3.0),
            'error_rate': 0.12,
            'pause_frequency': 0.30,
            'mouse_precision': 0.70,
            'description': 'Distracted user - inconsistent behavior'
        }
    }
    
    def __init__(self, profile_type: str = None):
        """Initialize with specific profile type or random selection"""
        if profile_type and profile_type in self.PROFILE_CONFIGS:
            self.profile_type = profile_type
        else:
            self.profile_type = random.choice(list(self.PROFILE_CONFIGS.keys()))
        
        self.config = self.PROFILE_CONFIGS[self.profile_type]
        
        # Generate specific values within profile ranges
        self._typing_speed = random.uniform(*self.config['typing_speed'])
        self._error_rate = self.config['error_rate']
        self._pause_frequency = self.config['pause_frequency']
        self._mouse_precision = self.config['mouse_precision']
        
        log_info(f"[PROFILE] Initialized {self.config['description']}")
    
    def get_typing_speed(self) -> float:
        """Get typing speed for this profile"""
        return self._typing_speed
    
    def get_error_rate(self) -> float:
        """Get error rate for this profile"""
        return self._error_rate
    
    def get_pause_frequency(self) -> float:
        """Get pause frequency for this profile"""
        return self._pause_frequency
    
    def get_mouse_precision(self) -> float:
        """Get mouse precision for this profile"""
        return self._mouse_precision
    
    def get_profile_type(self) -> str:
        """Get profile type identifier"""
        return self.profile_type
    
    def get_description(self) -> str:
        """Get profile description"""
        return self.config['description']
    
    @classmethod
    def create_custom_profile(cls, profile_name: str, config: Dict[str, Any]) -> 'BehaviorProfile':
        """
        Create custom profile - Open/Closed Principle
        Allows adding new profiles without modifying existing code
        """
        # Validate required config keys
        required_keys = ['typing_speed', 'error_rate', 'pause_frequency', 'mouse_precision', 'description']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Custom profile missing required key: {key}")
        
        # Add to available profiles
        cls.PROFILE_CONFIGS[profile_name] = config
        
        # Create instance with custom profile
        return cls(profile_name)
    
    @classmethod
    def get_available_profiles(cls) -> Dict[str, str]:
        """Get list of available profiles with descriptions"""
        return {name: config['description'] for name, config in cls.PROFILE_CONFIGS.items()}
    
    def adjust_for_fatigue(self, fatigue_level: float) -> None:
        """Adjust profile parameters based on fatigue level"""
        # Increase error rate with fatigue
        self._error_rate = self.config['error_rate'] * fatigue_level
        
        # Decrease typing speed with fatigue
        base_speed = random.uniform(*self.config['typing_speed'])
        self._typing_speed = base_speed / fatigue_level
        
        # Decrease mouse precision with fatigue
        self._mouse_precision = max(0.5, self.config['mouse_precision'] / fatigue_level)
        
        # Increase pause frequency with fatigue
        self._pause_frequency = min(0.5, self.config['pause_frequency'] * fatigue_level)
    
    def reset_to_baseline(self) -> None:
        """Reset profile to baseline values"""
        self._typing_speed = random.uniform(*self.config['typing_speed'])
        self._error_rate = self.config['error_rate']
        self._pause_frequency = self.config['pause_frequency']
        self._mouse_precision = self.config['mouse_precision']