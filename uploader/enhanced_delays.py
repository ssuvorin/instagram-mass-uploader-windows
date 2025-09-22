# -*- coding: utf-8 -*-
"""
Enhanced delay configuration for Instagram automation
Provides intelligent, context-aware delays that mimic human behavior
"""

import random
import time
from datetime import datetime
from typing import Dict, Tuple, Optional


class EnhancedDelayConfig:
    """Enhanced delay configuration with context-aware timing"""
    
    # Base delay configurations by context
    CONTEXT_DELAYS = {
        'auth': (2.0, 5.0),           # Authentication operations
        'session_check': (1.0, 3.0),  # Session validation
        'upload': (5.0, 15.0),        # Video uploads
        'retry': (5.0, 15.0),         # Retry operations
        'challenge': (3.0, 8.0),      # Challenge resolution
        'error_recovery': (10.0, 30.0), # Error recovery
        'rate_limit': (30.0, 120.0),  # Rate limit delays
        'network': (5.0, 15.0),       # Network errors
        'thinking': (2.0, 8.0),       # Human thinking simulation
        'browsing': (10.0, 30.0),     # Browsing simulation
        'between_videos': (30.0, 60.0), # Between video uploads
        'between_accounts': (120.0, 300.0), # Between accounts
    }
    
    # Time-based multipliers
    TIME_MULTIPLIERS = {
        'night': (2.0, 6.0),      # 2 AM - 6 AM
        'early_morning': (1.5, 3.0), # 6 AM - 10 AM  
        'morning': (1.2, 2.0),    # 10 AM - 12 PM
        'afternoon': (1.0, 1.5),  # 12 PM - 6 PM
        'evening': (0.8, 1.2),    # 6 PM - 10 PM
        'late_evening': (1.0, 2.0), # 10 PM - 2 AM
    }
    
    # Fatigue multipliers (increases with session duration)
    FATIGUE_THRESHOLDS = {
        30: 1.0,    # First 30 minutes
        60: 1.2,    # 30-60 minutes
        120: 1.5,   # 1-2 hours
        240: 2.0,   # 2-4 hours
        480: 3.0,   # 4-8 hours
    }
    
    @classmethod
    def get_time_multiplier(cls) -> float:
        """Get time-based delay multiplier based on current hour"""
        current_hour = datetime.now().hour
        
        if 2 <= current_hour < 6:
            period = 'night'
        elif 6 <= current_hour < 10:
            period = 'early_morning'
        elif 10 <= current_hour < 12:
            period = 'morning'
        elif 12 <= current_hour < 18:
            period = 'afternoon'
        elif 18 <= current_hour < 22:
            period = 'evening'
        else:
            period = 'late_evening'
        
        min_mult, max_mult = cls.TIME_MULTIPLIERS[period]
        return random.uniform(min_mult, max_mult)
    
    @classmethod
    def get_fatigue_multiplier(cls, session_duration_minutes: float) -> float:
        """Get fatigue-based delay multiplier based on session duration"""
        for threshold, multiplier in sorted(cls.FATIGUE_THRESHOLDS.items()):
            if session_duration_minutes <= threshold:
                return multiplier
        
        # For sessions longer than 8 hours
        return 4.0
    
    @classmethod
    def get_context_delay(cls, context: str, session_duration_minutes: float = 0) -> float:
        """
        Get intelligent delay based on context, time, and session fatigue
        
        Args:
            context: The context/action being performed
            session_duration_minutes: How long the current session has been running
            
        Returns:
            Delay in seconds
        """
        # Get base delay for context
        if context not in cls.CONTEXT_DELAYS:
            context = 'retry'  # Default fallback
        
        min_delay, max_delay = cls.CONTEXT_DELAYS[context]
        base_delay = random.uniform(min_delay, max_delay)
        
        # Apply time-based multiplier
        time_mult = cls.get_time_multiplier()
        
        # Apply fatigue multiplier
        fatigue_mult = cls.get_fatigue_multiplier(session_duration_minutes)
        
        # Apply jitter for more natural behavior
        jitter = random.uniform(0.8, 1.2)
        
        # Calculate final delay
        final_delay = base_delay * time_mult * fatigue_mult * jitter
        
        # Ensure reasonable bounds
        final_delay = max(0.5, min(final_delay, 600))  # Between 0.5s and 10min
        
        return round(final_delay, 2)
    
    @classmethod
    def get_retry_delay(cls, attempt: int, context: str = 'retry') -> float:
        """
        Get delay for retry attempts with exponential backoff
        
        Args:
            attempt: Current attempt number (0-based)
            context: Context for the retry
            
        Returns:
            Delay in seconds
        """
        base_delay = cls.get_context_delay(context)
        
        # Exponential backoff with jitter
        exponential_factor = min(2 ** attempt, 16)  # Cap at 16x
        jitter = random.uniform(0.8, 1.5)
        
        retry_delay = base_delay * exponential_factor * jitter
        
        # Reasonable bounds for retries
        retry_delay = max(1.0, min(retry_delay, 300))  # Between 1s and 5min
        
        return round(retry_delay, 2)
    
    @classmethod
    def get_rate_limit_delay(cls, attempt: int = 0) -> float:
        """Get delay for rate limiting with exponential backoff"""
        base_delay = random.uniform(60, 180)  # 1-3 minutes base
        
        # Exponential backoff for rate limits
        exponential_factor = min(2 ** attempt, 8)  # Cap at 8x
        jitter = random.uniform(0.8, 1.3)
        
        rate_limit_delay = base_delay * exponential_factor * jitter
        
        # Rate limits can be longer
        rate_limit_delay = max(30, min(rate_limit_delay, 1800))  # Between 30s and 30min
        
        return round(rate_limit_delay, 2)


class HumanBehaviorSimulator:
    """Simulates human-like behavior patterns"""
    
    @staticmethod
    def simulate_typing_delay(text_length: int) -> float:
        """Simulate human typing delay based on text length"""
        # Average human typing speed: 40 WPM = ~200 characters per minute
        base_delay = (text_length / 200) * 60  # Convert to seconds
        
        # Add randomness and thinking time
        thinking_time = random.uniform(1.0, 3.0)
        typing_variance = random.uniform(0.5, 1.5)
        
        total_delay = (base_delay * typing_variance) + thinking_time
        return round(max(0.5, total_delay), 2)
    
    @staticmethod
    def simulate_reading_delay(text_length: int) -> float:
        """Simulate human reading delay based on text length"""
        # Average human reading speed: 200-300 WPM
        words = text_length / 5  # Rough word count
        reading_time = (words / 250) * 60  # Convert to seconds
        
        # Add processing time
        processing_time = random.uniform(0.5, 2.0)
        
        total_delay = reading_time + processing_time
        return round(max(1.0, total_delay), 2)
    
    @staticmethod
    def simulate_mouse_movement_delay(distance_pixels: int) -> float:
        """Simulate mouse movement delay based on distance"""
        # Human mouse movement: ~1000 pixels per second
        movement_time = distance_pixels / 1000
        
        # Add reaction time and natural variation
        reaction_time = random.uniform(0.1, 0.3)
        variance = random.uniform(0.8, 1.2)
        
        total_delay = (movement_time * variance) + reaction_time
        return round(max(0.1, total_delay), 2)
    
    @staticmethod
    def simulate_decision_making_delay(complexity: str = 'medium') -> float:
        """Simulate human decision-making delay"""
        complexity_delays = {
            'simple': (0.5, 2.0),
            'medium': (2.0, 5.0),
            'complex': (5.0, 10.0),
            'very_complex': (10.0, 20.0)
        }
        
        min_delay, max_delay = complexity_delays.get(complexity, complexity_delays['medium'])
        return round(random.uniform(min_delay, max_delay), 2)


# Convenience functions for easy access
def get_delay(context: str, session_duration_minutes: float = 0) -> float:
    """Get intelligent delay for given context"""
    return EnhancedDelayConfig.get_context_delay(context, session_duration_minutes)


def get_retry_delay(attempt: int, context: str = 'retry') -> float:
    """Get delay for retry attempts"""
    return EnhancedDelayConfig.get_retry_delay(attempt, context)


def get_rate_limit_delay(attempt: int = 0) -> float:
    """Get delay for rate limiting"""
    return EnhancedDelayConfig.get_rate_limit_delay(attempt)


def simulate_human_delay(context: str, **kwargs) -> float:
    """Simulate various human delays"""
    if context == 'typing' and 'text_length' in kwargs:
        return HumanBehaviorSimulator.simulate_typing_delay(kwargs['text_length'])
    elif context == 'reading' and 'text_length' in kwargs:
        return HumanBehaviorSimulator.simulate_reading_delay(kwargs['text_length'])
    elif context == 'mouse_movement' and 'distance' in kwargs:
        return HumanBehaviorSimulator.simulate_mouse_movement_delay(kwargs['distance'])
    elif context == 'decision' and 'complexity' in kwargs:
        return HumanBehaviorSimulator.simulate_decision_making_delay(kwargs['complexity'])
    else:
        # Fallback to context delay
        session_duration = kwargs.get('session_duration_minutes', 0)
        return get_delay(context, session_duration)
