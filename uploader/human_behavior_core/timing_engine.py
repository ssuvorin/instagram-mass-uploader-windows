"""
Timing Engine Implementation
Consolidates all timing and delay logic - Single Responsibility Principle
ENHANCED: Now includes TimingManager to replace scattered random.uniform() calls
"""

import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Union
from .interfaces import ITimingEngine
try:
    from ..logging_utils import log_info, log_debug
except ImportError:
    # Fallback logging for testing
    def log_info(msg): print(f"INFO: {msg}")
    def log_debug(msg): print(f"DEBUG: {msg}")


class TimingEngine(ITimingEngine):
    """
    Centralized timing engine for all human behavior delays
    Consolidates scattered random.uniform() calls and hardcoded delays
    """
    
    def __init__(self, profile_config: Optional[Dict] = None):
        self.session_start = datetime.now()
        self.action_count = 0
        self.fatigue_level = 0.0
        self.last_break_time = datetime.now()
        
        # Default timing configuration - can be injected via Dependency Injection
        self.config = profile_config or {
            'base_delays': {
                'typing': 0.1,
                'clicking': 0.5,
                'thinking': 1.5,
                'reading': 1.2,
                'workflow': 2.0,
                'general': 1.0
            },
            'time_multipliers': {
                'morning': (6, 10, 1.3, 1.8),    # (start_hour, end_hour, min_mult, max_mult)
                'day': (10, 17, 0.8, 1.2),
                'evening': (17, 22, 0.6, 1.0),
                'night': (22, 6, 1.5, 2.5)
            },
            'fatigue_settings': {
                'max_session_minutes': 30,
                'max_actions': 100,
                'fatigue_multiplier': 1.5
            },
            'break_settings': {
                'probability_base': 0.1,
                'fatigue_increase': 0.2,
                'min_interval_minutes': 5
            }
        }
    
    def get_delay(self, base_delay: float, variance: float = 0.5, context: str = 'general') -> float:
        """
        Calculate human-like delay with all factors applied
        Replaces scattered delay calculations throughout codebase
        """
        self.action_count += 1
        
        # Get base delay from context or use provided
        context_delay = self.config['base_delays'].get(context, base_delay)
        
        # Apply all multipliers
        time_multiplier = self.get_time_multiplier()
        fatigue_multiplier = self.get_fatigue_multiplier()
        
        # Calculate total multiplier
        total_multiplier = time_multiplier * fatigue_multiplier
        adjusted_delay = context_delay * total_multiplier
        
        # Add variance using normal distribution for realism
        final_delay = random.normalvariate(adjusted_delay, variance * adjusted_delay / 3)
        
        # Clamp to reasonable bounds
        min_delay = context_delay * 0.3
        max_delay = context_delay * 5.0
        final_delay = max(min_delay, min(max_delay, final_delay))
        
        log_debug(f"[TIMING] Context: {context}, Base: {context_delay:.2f}s, "
                 f"Final: {final_delay:.2f}s (Time: {time_multiplier:.2f}x, "
                 f"Fatigue: {fatigue_multiplier:.2f}x)")
        
        return final_delay
    
    def get_time_multiplier(self) -> float:
        """Get time-of-day based multiplier - consolidates duplicate logic"""
        current_hour = datetime.now().hour
        
        for period, (start, end, min_mult, max_mult) in self.config['time_multipliers'].items():
            if start <= end:  # Normal range (e.g., 10-17)
                if start <= current_hour <= end:
                    return random.uniform(min_mult, max_mult)
            else:  # Overnight range (e.g., 22-6)
                if current_hour >= start or current_hour <= end:
                    return random.uniform(min_mult, max_mult)
        
        # Default fallback
        return random.uniform(0.8, 1.2)
    
    def get_fatigue_multiplier(self) -> float:
        """Calculate fatigue-based multiplier - consolidates duplicate logic"""
        session_duration = (datetime.now() - self.session_start).total_seconds() / 60
        
        # Time-based fatigue
        max_minutes = self.config['fatigue_settings']['max_session_minutes']
        time_fatigue = min(session_duration / max_minutes, 1.5)
        
        # Action-based fatigue
        max_actions = self.config['fatigue_settings']['max_actions']
        action_fatigue = min(self.action_count / max_actions, 1.0)
        
        # Combined fatigue
        fatigue_multiplier = self.config['fatigue_settings']['fatigue_multiplier']
        self.fatigue_level = 1.0 + (time_fatigue * 0.4) + (action_fatigue * 0.3)
        
        return min(self.fatigue_level, fatigue_multiplier)
    
    def should_take_break(self) -> bool:
        """Determine if a break should be taken - consolidates break logic"""
        # Check minimum interval
        time_since_break = (datetime.now() - self.last_break_time).total_seconds() / 60
        min_interval = self.config['break_settings']['min_interval_minutes']
        
        if time_since_break < min_interval:
            return False
        
        # Calculate break probability
        base_prob = self.config['break_settings']['probability_base']
        fatigue_increase = self.config['break_settings']['fatigue_increase']
        
        break_probability = base_prob + (self.fatigue_level - 1.0) * fatigue_increase
        
        if random.random() < break_probability:
            self.last_break_time = datetime.now()
            return True
        
        return False
    
    async def take_break(self, break_type: str = 'auto') -> None:
        """Execute a break with appropriate duration"""
        break_durations = {
            'micro': (2, 8),
            'short': (10, 30), 
            'medium': (60, 180),
            'auto': None  # Will be determined by fatigue level
        }
        
        if break_type == 'auto':
            # Determine break type based on fatigue
            if self.fatigue_level < 1.2:
                break_type = 'micro'
            elif self.fatigue_level < 1.5:
                break_type = 'short'
            else:
                break_type = 'medium'
        
        duration_range = break_durations[break_type]
        duration = random.uniform(*duration_range)
        
        log_info(f"[TIMING] Taking {break_type} break for {duration:.1f}s")
        await asyncio.sleep(duration)
        
        # Reduce fatigue after break
        if break_type in ['short', 'medium']:
            self.fatigue_level = max(1.0, self.fatigue_level - 0.3)
    
    def reset_session(self) -> None:
        """Reset session state - useful for new upload sessions"""
        self.session_start = datetime.now()
        self.action_count = 0
        self.fatigue_level = 0.0
        self.last_break_time = datetime.now()
        log_info("[TIMING] Session state reset")
    
    def get_session_stats(self) -> Dict:
        """Get current session statistics"""
        session_duration = (datetime.now() - self.session_start).total_seconds() / 60
        return {
            'session_duration_minutes': session_duration,
            'action_count': self.action_count,
            'fatigue_level': self.fatigue_level,
            'time_multiplier': self.get_time_multiplier(),
            'actions_per_minute': self.action_count / max(session_duration, 1)
        }


class TimingManager:
    """
    ENHANCED: Centralized manager to replace scattered random.uniform() calls
    Consolidates hardcoded delay values with configurable timing parameters
    Applies Dependency Injection for timing configuration across all functions
    """
    
    def __init__(self, timing_engine: Optional[TimingEngine] = None):
        self.timing_engine = timing_engine or TimingEngine()
        
        # Configurable timing parameters to replace hardcoded values
        self.timing_config = {
            # Mouse movement and clicking delays
            'mouse_movement': {
                'base_delay': (0.008, 0.035),  # Replaces scattered 0.01-0.03 values
                'curve_steps': (12, 25),       # Replaces hardcoded step counts
                'position_variance': (0.2, 0.8),  # Replaces hardcoded 0.2-0.8 positioning
                'hover_duration': (0.1, 0.3),     # Replaces scattered hover times
                'click_delay': (0.3, 0.7)         # Replaces post-click delays
            },
            
            # Typing and text input delays
            'typing': {
                'char_delay': (0.02, 0.08),       # Replaces scattered typing delays
                'thinking_pause': (0.8, 3.5),     # Replaces hardcoded thinking pauses
                'error_realization': (0.6, 1.8),  # Replaces error correction delays
                'correction_delay': (0.12, 0.25), # Replaces backspace timing
                'focus_delay': (0.3, 1.2)         # Replaces element focus delays
            },
            
            # Page interaction delays
            'page_interaction': {
                'scan_delay': (0.5, 1.5),         # Replaces page scanning delays
                'scroll_pause': (0.5, 1.5),       # Replaces scroll timing
                'reading_wpm': (200, 250),        # Replaces hardcoded reading speeds
                'workflow_delay': (1.0, 3.0),     # Replaces workflow pauses
                'processing_wait': (2.0, 3.0)     # Replaces processing delays
            },
            
            # Video processing delays
            'video_processing': {
                'crop_delay': (1.5, 2.5),         # Replaces crop operation delays
                'aspect_ratio_wait': (1.5, 2.5),  # Replaces aspect ratio delays
                'upload_processing': (2.0, 5.0),  # Replaces upload wait times
                'initial_wait': (3.0, 5.0)        # Replaces initial page loads
            },
            
            # Account management delays
            'account_management': {
                'account_delay': (4.0, 7.0),      # Replaces account switching delays
                'warmup_delay': (0.0, 5.0),       # Replaces warmup delays
                'verification_delay': (0.5, 1.2), # Replaces verification delays
                'login_delay': (0.8, 1.5)         # Replaces login delays
            },
            
            # Video uniquification parameters
            'video_uniquification': {
                'trim_range': (0.01, 0.05),         # Очень мягкая обрезка начала
                'contrast_range': (0.98, 1.05),      # Очень мягкий контраст
                'hue_range': (-2, 2),                # Очень мягкое изменение цвета
                'brightness_range': (0.001, 0.02),  # Очень мягкая яркость
                'saturation_range': (0.95, 1.05),   # Очень мягкая насыщенность
                'crop_range': (0.98, 0.999),        # Очень мягкая обрезка
                'zoom_range': (1.0, 1.2),           # Replaces zoom values
                'zoom_duration': (0.5, 2.0)         # Replaces zoom duration
            }
        }
    
    def get_delay(self, category: str, subcategory: str, context: str = 'general') -> float:
        """
        Get delay from configurable parameters instead of hardcoded random.uniform()
        Applies timing engine multipliers for realistic behavior
        """
        try:
            delay_range = self.timing_config[category][subcategory]
            base_delay = random.uniform(*delay_range)
            
            # Apply timing engine multipliers for realism
            enhanced_delay = self.timing_engine.get_delay(base_delay, context=context)
            
            log_debug(f"[TIMING_MANAGER] {category}.{subcategory}: {base_delay:.3f}s -> {enhanced_delay:.3f}s")
            return enhanced_delay
            
        except KeyError:
            log_debug(f"[TIMING_MANAGER] Unknown timing category: {category}.{subcategory}")
            # Fallback to timing engine default
            return self.timing_engine.get_delay(1.0, context=context)
    
    def get_range_value(self, category: str, subcategory: str) -> float:
        """
        Get value from range without timing engine multipliers
        Used for non-time values like positioning, percentages, etc.
        """
        try:
            value_range = self.timing_config[category][subcategory]
            return random.uniform(*value_range)
        except KeyError:
            log_debug(f"[TIMING_MANAGER] Unknown range category: {category}.{subcategory}")
            return random.uniform(0.5, 1.5)  # Safe fallback
    
    def get_position_in_element(self, box: Dict) -> Tuple[float, float]:
        """
        Calculate position within element bounds using configurable variance
        Replaces scattered positioning calculations
        """
        variance_range = self.timing_config['mouse_movement']['position_variance']
        
        # Use golden ratio for more natural positioning
        golden_ratio = 0.618
        base_x = box['x'] + box['width'] * golden_ratio
        base_y = box['y'] + box['height'] * golden_ratio
        
        # Apply configurable variance
        var_x = random.uniform(*variance_range)
        var_y = random.uniform(*variance_range)
        
        target_x = box['x'] + box['width'] * var_x
        target_y = box['y'] + box['height'] * var_y
        
        return target_x, target_y
    
    def get_reading_time(self, text_length: int) -> float:
        """
        Calculate reading time using configurable WPM instead of hardcoded values
        """
        wpm_range = self.timing_config['page_interaction']['reading_wpm']
        words_per_minute = random.uniform(*wpm_range)
        
        estimated_words = text_length / 5  # Average word length
        reading_time = (estimated_words / words_per_minute) * 60
        
        # Apply timing engine multipliers
        enhanced_time = self.timing_engine.get_delay(reading_time, context='reading')
        
        return max(1.0, enhanced_time)
    
    def get_curve_steps(self, distance: float) -> int:
        """
        Calculate curve steps based on distance using configurable parameters
        """
        step_range = self.timing_config['mouse_movement']['curve_steps']
        base_steps = max(step_range[0], min(step_range[1], int(distance / 40)))
        
        # Add variation
        variation = random.randint(-2, 3)
        return base_steps + variation
    
    def should_take_thinking_pause(self, context: str = 'general') -> bool:
        """
        Determine if a thinking pause should be taken
        Uses timing engine fatigue and break logic
        """
        # Base probability varies by context
        context_probabilities = {
            'typing': 0.05,      # 5% chance during typing
            'clicking': 0.15,    # 15% chance before clicks
            'reading': 0.25,     # 25% chance during reading
            'workflow': 0.30,    # 30% chance in workflows
            'general': 0.10      # 10% default chance
        }
        
        base_prob = context_probabilities.get(context, 0.10)
        
        # Increase probability with fatigue
        fatigue_multiplier = self.timing_engine.get_fatigue_multiplier()
        adjusted_prob = base_prob * fatigue_multiplier
        
        return random.random() < adjusted_prob
    
    def get_thinking_pause_duration(self, context: str = 'general') -> float:
        """
        Get thinking pause duration using configurable parameters
        """
        return self.get_delay('typing', 'thinking_pause', context)
    
    def inject_config(self, new_config: Dict) -> None:
        """
        Dependency Injection: Allow external configuration of timing parameters
        Enables different timing profiles for different scenarios
        """
        # Deep merge new config with existing
        for category, subcategories in new_config.items():
            if category in self.timing_config:
                self.timing_config[category].update(subcategories)
            else:
                self.timing_config[category] = subcategories
        
        log_info(f"[TIMING_MANAGER] Injected configuration for {len(new_config)} categories")
    
    def get_config_summary(self) -> Dict:
        """
        Get summary of current timing configuration
        Useful for debugging and monitoring
        """
        return {
            'categories': list(self.timing_config.keys()),
            'timing_engine_stats': self.timing_engine.get_session_stats(),
            'total_parameters': sum(len(subcats) for subcats in self.timing_config.values())
        }


# Global timing manager instance for dependency injection
_global_timing_manager: Optional[TimingManager] = None


def get_timing_manager() -> TimingManager:
    """
    Get global timing manager instance
    Creates one if it doesn't exist (lazy initialization)
    """
    global _global_timing_manager
    if _global_timing_manager is None:
        _global_timing_manager = TimingManager()
        log_info("[TIMING_MANAGER] Initialized global timing manager")
    
    return _global_timing_manager


def inject_timing_config(config: Dict) -> None:
    """
    Inject timing configuration into global timing manager
    Enables dependency injection pattern across the application
    """
    timing_manager = get_timing_manager()
    timing_manager.inject_config(config)


def reset_timing_session() -> None:
    """
    Reset timing session state
    Useful when starting new upload sessions
    """
    timing_manager = get_timing_manager()
    timing_manager.timing_engine.reset_session()
    log_info("[TIMING_MANAGER] Session reset")