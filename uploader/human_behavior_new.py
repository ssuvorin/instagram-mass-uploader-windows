"""
Unified Human Behavior System for Instagram Automation
SIMPLIFIED: Single file with all human behavior functionality
Consolidates human_behavior.py, advanced_human_behavior.py, and human_behavior_unified.py
"""

import asyncio
import random
import math
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from .logging_utils import log_info, log_warning, log_error


class HumanBehavior:
    """
    Unified Human Behavior class - consolidates all previous implementations
    Provides both sync and async methods for maximum compatibility
    """
    
    def __init__(self, page):
        self.page = page
        
        # Core behavior settings
        self.typing_speed_base = 0.1
        self.typing_speed_variance = 0.05
        self.mouse_movement_speed = 1.0
        
        # Session tracking
        self.session_start_time = datetime.now()
        self.action_count = 0
        self.fatigue_level = 1.0
        self.last_error_time = None
        self.last_break_time = datetime.now()
        
        # Generate user profile
        self.user_profile = self._generate_user_profile()
        
        # Initialize timing engine
        self._init_timing_engine()
        
        log_info(f"[HUMAN_BEHAVIOR] Initialized: {self.user_profile['description']}")
    
    def _generate_user_profile(self) -> Dict:
        """Generate user profile for personalized behavior"""
        profiles = [
            {
                'type': 'careful',
                'speed_multiplier': 1.3,
                'error_rate': 0.02,
                'pause_probability': 0.15,
                'description': 'Careful user - slow and precise'
            },
            {
                'type': 'normal',
                'speed_multiplier': 1.0,
                'error_rate': 0.05,
                'pause_probability': 0.10,
                'description': 'Normal user - balanced behavior'
            },
            {
                'type': 'fast',
                'speed_multiplier': 0.7,
                'error_rate': 0.08,
                'pause_probability': 0.05,
                'description': 'Fast user - quick but more errors'
            },
            {
                'type': 'distracted',
                'speed_multiplier': 1.5,
                'error_rate': 0.12,
                'pause_probability': 0.25,
                'description': 'Distracted user - slow with many pauses'
            }
        ]
        
        return random.choice(profiles)
    
    def _init_timing_engine(self):
        """Initialize timing engine with user profile"""
        try:
            from .human_behavior_core.timing_engine import get_timing_manager
            self.timing_manager = get_timing_manager()
            
            # Configure timing based on user profile
            profile_config = {
                'base_delays': {
                    'typing': 0.1 * self.user_profile['speed_multiplier'],
                    'clicking': 0.5 * self.user_profile['speed_multiplier'],
                    'thinking': 1.5 * self.user_profile['speed_multiplier'],
                    'reading': 1.2 * self.user_profile['speed_multiplier'],
                    'workflow': 2.0 * self.user_profile['speed_multiplier'],
                    'general': 1.0 * self.user_profile['speed_multiplier']
                }
            }
            
            self.timing_manager.inject_config({'base_delays': profile_config['base_delays']})
            
        except ImportError:
            log_warning("[HUMAN_BEHAVIOR] Timing engine not available, using fallback")
            self.timing_manager = None
    
    # =============================================================================
    # CORE DELAY AND TIMING METHODS
    # =============================================================================
    
    def get_human_delay(self, base_delay: float = 1.0, variance: float = 0.5, context: str = 'general') -> float:
        """
        Get human-like delay with all factors applied
        Consolidates all delay calculation logic
        """
        self.action_count += 1
        
        if self.timing_manager:
            return self.timing_manager.get_delay('base_delays', context, context)
        
        # Fallback calculation
        time_multiplier = self.get_time_based_multiplier()
        fatigue_multiplier = self.calculate_fatigue_level()
        profile_multiplier = self.user_profile['speed_multiplier']
        
        # Apply all multipliers
        adjusted_delay = base_delay * time_multiplier * fatigue_multiplier * profile_multiplier
        
        # Add variance
        final_delay = adjusted_delay + random.uniform(-variance, variance)
        
        return max(0.1, final_delay)  # Minimum 100ms delay
    
    def get_time_based_multiplier(self) -> float:
        """Get time-of-day based multiplier"""
        if self.timing_manager:
            return self.timing_manager.timing_engine.get_time_multiplier()
        
        # Fallback time-based calculation
        current_hour = datetime.now().hour
        
        if 6 <= current_hour <= 10:  # Morning - slower
            return random.uniform(1.2, 1.8)
        elif 11 <= current_hour <= 17:  # Day - normal
            return random.uniform(0.8, 1.2)
        elif 18 <= current_hour <= 22:  # Evening - faster
            return random.uniform(0.6, 1.0)
        else:  # Night - very slow
            return random.uniform(1.5, 2.5)
    
    def calculate_fatigue_level(self) -> float:
        """Calculate current fatigue level"""
        if self.timing_manager:
            self.timing_manager.timing_engine.action_count = self.action_count
            self.fatigue_level = self.timing_manager.timing_engine.get_fatigue_multiplier()
            return self.fatigue_level
        
        # Fallback fatigue calculation
        session_duration = (datetime.now() - self.session_start_time).total_seconds() / 60
        
        # Time-based fatigue
        time_fatigue = min(session_duration / 30, 2.0)  # Max 2x after 30 minutes
        
        # Action-based fatigue
        action_fatigue = min(self.action_count / 50, 1.5)  # Max 1.5x after 50 actions
        
        self.fatigue_level = 1.0 + (time_fatigue * 0.3) + (action_fatigue * 0.2)
        return self.fatigue_level
    
    def should_take_break(self) -> bool:
        """Determine if a break should be taken"""
        if self.timing_manager:
            return self.timing_manager.timing_engine.should_take_break()
        
        # Fallback break logic
        time_since_break = (datetime.now() - self.last_break_time).total_seconds() / 60
        
        if time_since_break < 5:  # Minimum 5 minutes between breaks
            return False
        
        # Higher fatigue = higher break probability
        break_probability = 0.1 + (self.fatigue_level - 1.0) * 0.2
        
        if random.random() < break_probability:
            self.last_break_time = datetime.now()
            return True
        
        return False
    
    # =============================================================================
    # MOUSE BEHAVIOR METHODS
    # =============================================================================
    
    def get_element_position(self, box: Dict) -> Tuple[float, float]:
        """Get position within element bounds"""
        if self.timing_manager:
            return self.timing_manager.get_position_in_element(box)
        
        # Fallback positioning
        variance_x = random.uniform(0.2, 0.8)
        variance_y = random.uniform(0.2, 0.8)
        
        target_x = box['x'] + box['width'] * variance_x
        target_y = box['y'] + box['height'] * variance_y
        
        return target_x, target_y
    
    def natural_mouse_movement(self, target_element):
        """Simulate natural mouse movement to element"""
        try:
            box = target_element.bounding_box()
            if not box:
                return
            
            # Get target position
            target_x, target_y = self.get_element_position(box)
            
            # Get current position
            current_x, current_y = 0, 0  # Simplified - would need actual mouse position
            
            # Calculate distance and movement time
            distance = math.sqrt((target_x - current_x)**2 + (target_y - current_y)**2)
            movement_delay = self.get_human_delay(0.1, 0.05, 'mouse_movement')
            movement_time = 0.1 + (distance / 1000) * movement_delay
            
            # Move through intermediate points for naturalness
            steps = max(3, int(distance / 100))
            
            for step in range(steps):
                progress = (step + 1) / steps
                
                # Add small deviations for naturalness
                deviation_x = random.uniform(-5, 5) * (1 - progress)
                deviation_y = random.uniform(-5, 5) * (1 - progress)
                
                intermediate_x = current_x + (target_x - current_x) * progress + deviation_x
                intermediate_y = current_y + (target_y - current_y) * progress + deviation_y
                
                self.page.mouse.move(intermediate_x, intermediate_y)
                time.sleep(movement_time / steps)
            
            # Small pause after movement
            time.sleep(self.get_human_delay(0.1, 0.05, 'mouse_pause'))
            
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Mouse movement failed: {str(e)}")
    
    async def natural_mouse_movement_async(self, target_element):
        """Async version of natural mouse movement"""
        try:
            box = await target_element.bounding_box()
            if not box:
                return
            
            target_x, target_y = self.get_element_position(box)
            
            # Simplified async movement
            await self.page.mouse.move(target_x, target_y)
            
            movement_delay = self.get_human_delay(0.1, 0.05, 'mouse_movement')
            await asyncio.sleep(movement_delay)
            
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Async mouse movement failed: {str(e)}")
    
    # =============================================================================
    # CLICKING METHODS
    # =============================================================================
    
    def human_click(self, element, context: str = "general") -> bool:
        """Human-like click with error handling"""
        try:
            # Move mouse to element
            self.natural_mouse_movement(element)
            
            # Hover delay
            hover_delay = self.get_human_delay(0.2, 0.1, 'hover')
            time.sleep(hover_delay)
            
            # Click
            element.click()
            
            # Post-click delay
            click_delay = self.get_human_delay(0.5, 0.2, 'click')
            time.sleep(click_delay)
            
            return True
            
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Click failed: {str(e)}")
            
            # Fallback to simple click
            try:
                element.click()
                return True
            except Exception:
                return False
    
    async def human_click_async(self, element, context: str = "general") -> bool:
        """Async human-like click with error handling"""
        try:
            # Move mouse to element
            await self.natural_mouse_movement_async(element)
            
            # Hover delay
            hover_delay = self.get_human_delay(0.2, 0.1, 'hover')
            await asyncio.sleep(hover_delay)
            
            # Click with timeout
            await asyncio.wait_for(element.click(), timeout=5.0)
            
            # Post-click delay
            click_delay = self.get_human_delay(0.5, 0.2, 'click')
            await asyncio.sleep(click_delay)
            
            return True
            
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Async click failed: {str(e)}")
            
            # Fallback to simple click
            try:
                await element.click()
                return True
            except Exception:
                return False
    
    # =============================================================================
    # TYPING METHODS
    # =============================================================================
    
    def get_reading_time(self, text_length: int) -> float:
        """Calculate reading time for text"""
        if self.timing_manager:
            return self.timing_manager.get_reading_time(text_length)
        
        # Fallback reading time calculation
        words_per_minute = random.uniform(200, 250)
        estimated_words = text_length / 5
        reading_time = (estimated_words / words_per_minute) * 60
        
        # Add variance and minimum time
        reading_time = max(1.0, reading_time * random.uniform(0.8, 1.2))
        
        return reading_time
    
    def human_typing(self, element, text: str, simulate_mistakes: bool = True):
        """Human-like typing with mistakes and corrections"""
        try:
            # Click on element first
            element.click()
            time.sleep(self.get_human_delay(0.3, 0.1, 'focus'))
            
            # Clear field
            element.fill('')
            time.sleep(self.get_human_delay(0.2, 0.1, 'clear'))
            
            if simulate_mistakes:
                self._type_with_mistakes(element, text)
            else:
                self._type_simple(element, text)
            
            return True
            
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Typing failed: {str(e)}")
            
            # Fallback to simple typing
            try:
                element.fill(text)
                return True
            except Exception:
                return False
    
    async def human_typing_async(self, element, text: str, simulate_mistakes: bool = True) -> bool:
        """Async human-like typing"""
        try:
            # Click on element first
            await element.click()
            focus_delay = self.get_human_delay(0.3, 0.1, 'focus')
            await asyncio.sleep(focus_delay)
            
            # Clear field
            await element.fill('')
            clear_delay = self.get_human_delay(0.2, 0.1, 'clear')
            await asyncio.sleep(clear_delay)
            
            if simulate_mistakes:
                await self._type_with_mistakes_async(element, text)
            else:
                await self._type_simple_async(element, text)
            
            return True
            
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Async typing failed: {str(e)}")
            
            # Fallback to simple typing
            try:
                await element.fill(text)
                return True
            except Exception:
                return False
    
    def _type_simple(self, element, text: str):
        """Simple typing without mistakes"""
        for char in text:
            element.type(char)
            
            # Character delay based on user profile
            char_delay = self.typing_speed_base * self.user_profile['speed_multiplier']
            char_delay += random.uniform(-self.typing_speed_variance, self.typing_speed_variance)
            
            time.sleep(max(0.02, char_delay))
            
            # Occasional thinking pause
            if random.random() < self.user_profile['pause_probability']:
                thinking_delay = self.get_human_delay(0.5, 0.3, 'thinking')
                time.sleep(thinking_delay)
    
    async def _type_simple_async(self, element, text: str):
        """Async simple typing without mistakes"""
        for char in text:
            await element.type(char)
            
            # Character delay based on user profile
            char_delay = self.typing_speed_base * self.user_profile['speed_multiplier']
            char_delay += random.uniform(-self.typing_speed_variance, self.typing_speed_variance)
            
            await asyncio.sleep(max(0.02, char_delay))
            
            # Occasional thinking pause
            if random.random() < self.user_profile['pause_probability']:
                thinking_delay = self.get_human_delay(0.5, 0.3, 'thinking')
                await asyncio.sleep(thinking_delay)
    
    def _type_with_mistakes(self, element, text: str):
        """Typing with realistic mistakes and corrections"""
        i = 0
        while i < len(text):
            char = text[i]
            
            # Should we make a mistake?
            if random.random() < self.user_profile['error_rate']:
                # Make a mistake
                wrong_char = self._get_similar_char(char)
                element.type(wrong_char)
                
                # Realize mistake after a delay
                time.sleep(random.uniform(0.3, 0.8))
                
                # Correct the mistake
                element.press('Backspace')
                time.sleep(random.uniform(0.1, 0.3))
                
                # Type correct character
                element.type(char)
                
                # Record error for fatigue calculation
                self.last_error_time = datetime.now()
            else:
                # Type normally
                element.type(char)
            
            # Character delay
            char_delay = self.typing_speed_base * self.user_profile['speed_multiplier']
            char_delay += random.uniform(-self.typing_speed_variance, self.typing_speed_variance)
            time.sleep(max(0.02, char_delay))
            
            # Thinking pause
            if random.random() < self.user_profile['pause_probability']:
                thinking_delay = self.get_human_delay(0.5, 0.3, 'thinking')
                time.sleep(thinking_delay)
            
            i += 1
    
    async def _type_with_mistakes_async(self, element, text: str):
        """Async typing with mistakes and corrections"""
        i = 0
        while i < len(text):
            char = text[i]
            
            # Should we make a mistake?
            if random.random() < self.user_profile['error_rate']:
                # Make a mistake
                wrong_char = self._get_similar_char(char)
                await element.type(wrong_char)
                
                # Realize mistake after a delay
                await asyncio.sleep(random.uniform(0.3, 0.8))
                
                # Correct the mistake
                await element.press('Backspace')
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # Type correct character
                await element.type(char)
                
                # Record error for fatigue calculation
                self.last_error_time = datetime.now()
            else:
                # Type normally
                await element.type(char)
            
            # Character delay
            char_delay = self.typing_speed_base * self.user_profile['speed_multiplier']
            char_delay += random.uniform(-self.typing_speed_variance, self.typing_speed_variance)
            await asyncio.sleep(max(0.02, char_delay))
            
            # Thinking pause
            if random.random() < self.user_profile['pause_probability']:
                thinking_delay = self.get_human_delay(0.5, 0.3, 'thinking')
                await asyncio.sleep(thinking_delay)
            
            i += 1
    
    def _get_similar_char(self, char: str) -> str:
        """Get similar character for typing mistakes"""
        # QWERTY keyboard layout for realistic mistakes
        keyboard_layout = {
            'q': ['w', 'a'], 'w': ['q', 'e', 's'], 'e': ['w', 'r', 'd'],
            'r': ['e', 't', 'f'], 't': ['r', 'y', 'g'], 'y': ['t', 'u', 'h'],
            'u': ['y', 'i', 'j'], 'i': ['u', 'o', 'k'], 'o': ['i', 'p', 'l'],
            'p': ['o', 'l'], 'a': ['q', 's', 'z'], 's': ['w', 'a', 'd', 'x'],
            'd': ['e', 's', 'f', 'c'], 'f': ['r', 'd', 'g', 'v'],
            'g': ['t', 'f', 'h', 'b'], 'h': ['y', 'g', 'j', 'n'],
            'j': ['u', 'h', 'k', 'm'], 'k': ['i', 'j', 'l'],
            'l': ['o', 'k', 'p'], 'z': ['a', 's', 'x'], 'x': ['z', 's', 'd', 'c'],
            'c': ['x', 'd', 'f', 'v'], 'v': ['c', 'f', 'g', 'b'],
            'b': ['v', 'g', 'h', 'n'], 'n': ['b', 'h', 'j', 'm'],
            'm': ['n', 'j', 'k']
        }
        
        char_lower = char.lower()
        if char_lower in keyboard_layout:
            similar_chars = keyboard_layout[char_lower]
            similar = random.choice(similar_chars)
            return similar.upper() if char.isupper() else similar
        
        return char  # Return original if no similar char found
    
    # =============================================================================
    # SCROLLING AND PAGE INTERACTION
    # =============================================================================
    
    def human_scroll(self, direction: str = "down", amount: int = 3):
        """Human-like scrolling"""
        try:
            delta_y = 300 if direction == "down" else -300
            
            for _ in range(amount):
                self.page.mouse.wheel(0, delta_y)
                
                # Pause between scrolls
                scroll_delay = self.get_human_delay(0.3, 0.2, 'scroll')
                time.sleep(scroll_delay)
                
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Scroll failed: {str(e)}")
    
    async def human_scroll_async(self, direction: str = "down", amount: int = 3):
        """Async human-like scrolling"""
        try:
            delta_y = 300 if direction == "down" else -300
            
            for _ in range(amount):
                await self.page.mouse.wheel(0, delta_y)
                
                # Pause between scrolls
                scroll_delay = self.get_human_delay(0.3, 0.2, 'scroll')
                await asyncio.sleep(scroll_delay)
                
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Async scroll failed: {str(e)}")
    
    def simulate_page_scanning(self):
        """Simulate human page scanning behavior"""
        try:
            # Random mouse movements to simulate reading
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                self.page.mouse.move(x, y)
                
                scan_delay = self.get_human_delay(0.5, 0.3, 'scanning')
                time.sleep(scan_delay)
                
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Page scanning failed: {str(e)}")
    
    async def simulate_page_scanning_async(self):
        """Async simulate human page scanning behavior"""
        try:
            # Random mouse movements to simulate reading
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await self.page.mouse.move(x, y)
                
                scan_delay = self.get_human_delay(0.5, 0.3, 'scanning')
                await asyncio.sleep(scan_delay)
                
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Async page scanning failed: {str(e)}")
    
    # =============================================================================
    # BREAK AND SESSION MANAGEMENT
    # =============================================================================
    
    def take_break(self, break_type: str = 'auto'):
        """Take a break based on fatigue level"""
        break_durations = {
            'micro': (2, 8),
            'short': (10, 30),
            'medium': (60, 180),
            'auto': None
        }
        
        if break_type == 'auto':
            if self.fatigue_level < 1.2:
                break_type = 'micro'
            elif self.fatigue_level < 1.5:
                break_type = 'short'
            else:
                break_type = 'medium'
        
        duration_range = break_durations[break_type]
        duration = random.uniform(*duration_range)
        
        log_info(f"[HUMAN_BEHAVIOR] Taking {break_type} break for {duration:.1f}s")
        time.sleep(duration)
        
        # Reduce fatigue after break
        if break_type in ['short', 'medium']:
            self.fatigue_level = max(1.0, self.fatigue_level - 0.3)
        
        self.last_break_time = datetime.now()
    
    async def take_break_async(self, break_type: str = 'auto'):
        """Async take a break based on fatigue level"""
        if self.timing_manager:
            await self.timing_manager.timing_engine.take_break(break_type)
            return
        
        # Fallback break logic
        break_durations = {
            'micro': (2, 8),
            'short': (10, 30),
            'medium': (60, 180),
            'auto': None
        }
        
        if break_type == 'auto':
            if self.fatigue_level < 1.2:
                break_type = 'micro'
            elif self.fatigue_level < 1.5:
                break_type = 'short'
            else:
                break_type = 'medium'
        
        duration_range = break_durations[break_type]
        duration = random.uniform(*duration_range)
        
        log_info(f"[HUMAN_BEHAVIOR] Taking {break_type} break for {duration:.1f}s")
        await asyncio.sleep(duration)
        
        # Reduce fatigue after break
        if break_type in ['short', 'medium']:
            self.fatigue_level = max(1.0, self.fatigue_level - 0.3)
        
        self.last_break_time = datetime.now()
    
    def reset_session(self):
        """Reset session state for new upload session"""
        self.session_start_time = datetime.now()
        self.action_count = 0
        self.fatigue_level = 1.0
        self.last_error_time = None
        self.last_break_time = datetime.now()
        
        if self.timing_manager:
            self.timing_manager.timing_engine.reset_session()
        
        log_info("[HUMAN_BEHAVIOR] Session reset")
    
    def get_session_stats(self) -> Dict:
        """Get current session statistics"""
        session_duration = (datetime.now() - self.session_start_time).total_seconds() / 60
        
        return {
            'session_duration_minutes': session_duration,
            'action_count': self.action_count,
            'fatigue_level': self.fatigue_level,
            'user_profile': self.user_profile['type'],
            'time_multiplier': self.get_time_based_multiplier(),
            'actions_per_minute': self.action_count / max(session_duration, 1)
        }


# =============================================================================
# GLOBAL INSTANCE MANAGEMENT
# =============================================================================

_global_human_behavior: Optional[HumanBehavior] = None


def init_human_behavior(page) -> HumanBehavior:
    """Initialize global human behavior instance"""
    global _global_human_behavior
    _global_human_behavior = HumanBehavior(page)
    log_info("[HUMAN_BEHAVIOR] Global instance initialized")
    return _global_human_behavior


def get_human_behavior() -> Optional[HumanBehavior]:
    """Get global human behavior instance"""
    return _global_human_behavior


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# =============================================================================

# For backward compatibility with existing code
AdvancedHumanBehavior = HumanBehavior
UnifiedHumanBehavior = HumanBehavior

# Legacy function aliases
init_advanced_human_behavior = init_human_behavior
get_advanced_human_behavior = get_human_behavior
init_unified_human_behavior = init_human_behavior
get_unified_human_behavior = get_human_behavior


# Legacy profile class for backward compatibility
class HumanBehaviorProfile:
    """Legacy profile class - redirects to new system"""
    
    def __init__(self):
        self.profile_type = "normal"
        self.typing_speed = 0.1
        self.error_rate = 0.05
        self.pause_frequency = 0.10
        self.mouse_precision = 0.8
        
        log_info("[LEGACY_PROFILE] Using compatibility profile")