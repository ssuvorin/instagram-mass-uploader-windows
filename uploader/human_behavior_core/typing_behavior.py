"""
Typing Behavior Implementation
Handles all typing behavior including errors and corrections - Single Responsibility Principle
"""

import asyncio
import random
from typing import Any, Dict, List
from datetime import datetime
from .interfaces import ITypingBehavior, ITimingEngine, IBehaviorProfile
try:
    from logging_utils import log_info, log_warning, log_debug
except ImportError:
    # Fallback logging for testing
    def log_info(msg): print(f"INFO: {msg}")
    def log_warning(msg): print(f"WARNING: {msg}")
    def log_debug(msg): print(f"DEBUG: {msg}")


class TypingBehavior(ITypingBehavior):
    """
    Consolidated typing behavior implementation
    Eliminates duplication between sync and async typing implementations
    """
    
    def __init__(self, timing_engine: ITimingEngine, profile: IBehaviorProfile):
        self.timing_engine = timing_engine
        self.profile = profile
        self.last_error_time: Optional[datetime] = None
        self.recent_errors: List[datetime] = []
        
        # Keyboard layout for realistic errors - consolidates duplicate layouts
        self.keyboard_layout = {
            # QWERTY layout adjacency map
            'q': ['w', 'a'], 'w': ['q', 'e', 's'], 'e': ['w', 'r', 'd'],
            'r': ['e', 't', 'f'], 't': ['r', 'y', 'g'], 'y': ['t', 'u', 'h'],
            'u': ['y', 'i', 'j'], 'i': ['u', 'o', 'k'], 'o': ['i', 'p', 'l'],
            'p': ['o', 'l'], 'a': ['q', 's', 'z'], 's': ['w', 'a', 'd', 'x'],
            'd': ['e', 's', 'f', 'c'], 'f': ['r', 'd', 'g', 'v'],
            'g': ['t', 'f', 'h', 'b'], 'h': ['y', 'g', 'j', 'n'],
            'j': ['u', 'h', 'k', 'm'], 'k': ['i', 'j', 'l'], 'l': ['o', 'k', 'p'],
            'z': ['a', 's', 'x'], 'x': ['z', 's', 'd', 'c'], 'c': ['x', 'd', 'f', 'v'],
            'v': ['c', 'f', 'g', 'b'], 'b': ['v', 'g', 'h', 'n'],
            'n': ['b', 'h', 'j', 'm'], 'm': ['n', 'j', 'k']
        }
    
    async def type_text(self, page: Any, element: Any, text: str, context: str = 'general') -> bool:
        """
        Type text with human-like behavior including errors
        Consolidates human_type and _type_like_human_async logic
        """
        try:
            # Focus on element
            await element.click()
            focus_delay = self.timing_engine.get_delay(0.3, 0.1, 'clicking')
            await asyncio.sleep(focus_delay)
            
            # Clear existing content human-like way
            await self._clear_field_naturally(page, element)
            
            # Type text with human behavior
            await self._type_with_errors_and_corrections(page, element, text, context)
            
            # Final pause after typing
            final_delay = self.timing_engine.get_delay(0.5, 0.2, context)
            await asyncio.sleep(final_delay)
            
            log_debug(f"[TYPING] Successfully typed {len(text)} characters ({context})")
            return True
            
        except Exception as e:
            log_warning(f"[TYPING] Type text failed: {e}")
            # Fallback to simple typing
            try:
                await element.fill(text)
                return True
            except Exception:
                return False
    
    def should_make_error(self) -> bool:
        """
        Determine if typing error should be made
        Consolidates error probability logic with fatigue and frustration factors
        """
        base_error_rate = self.profile.get_error_rate()
        
        # Apply fatigue multiplier
        fatigue_multiplier = self.timing_engine.get_fatigue_multiplier()
        adjusted_error_rate = base_error_rate * fatigue_multiplier
        
        # Increase error rate after recent errors (frustration effect)
        if self.last_error_time and (datetime.now() - self.last_error_time).seconds < 30:
            adjusted_error_rate *= 1.5
        
        # Clean up old errors from recent list
        now = datetime.now()
        self.recent_errors = [err_time for err_time in self.recent_errors 
                             if (now - err_time).seconds < 60]
        
        # Increase error rate with multiple recent errors
        if len(self.recent_errors) > 2:
            adjusted_error_rate *= 1.3
        
        return random.random() < adjusted_error_rate
    
    def get_similar_char(self, char: str) -> str:
        """
        Get similar character for typing errors
        Consolidates _get_similar_char and _get_adjacent_key logic
        """
        char_lower = char.lower()
        
        if char_lower in self.keyboard_layout:
            similar_chars = self.keyboard_layout[char_lower]
            similar = random.choice(similar_chars)
            return similar.upper() if char.isupper() else similar
        
        # Fallback for non-English characters
        if ord(char) > 127:  # Non-ASCII (e.g., Russian)
            fallback_chars = ['ф', 'в', 'а', 'п', 'р', 'о', 'л', 'д', 'ж', 'э']
            return random.choice(fallback_chars)
        
        return char  # Return original if no similar char found
    
    async def simulate_correction(self, page: Any, element: Any, error_length: int) -> None:
        """Simulate error correction behavior"""
        try:
            # Pause to "realize" the error
            realization_delay = self.timing_engine.get_delay(0.4, 0.3, 'thinking')
            await asyncio.sleep(realization_delay)
            
            # Delete wrong characters
            for _ in range(error_length):
                await page.keyboard.press('Backspace')
                backspace_delay = self.timing_engine.get_delay(0.1, 0.05, 'typing')
                await asyncio.sleep(backspace_delay)
            
            # Pause before correction
            correction_delay = self.timing_engine.get_delay(0.2, 0.1, 'thinking')
            await asyncio.sleep(correction_delay)
            
        except Exception as e:
            log_warning(f"[TYPING] Error correction failed: {e}")
    
    async def _clear_field_naturally(self, page: Any, element: Any) -> None:
        """Clear field using human-like method (Ctrl+A + Delete)"""
        try:
            await page.keyboard.press('Control+a')
            await asyncio.sleep(random.uniform(0.1, 0.2))
            await page.keyboard.press('Delete')
            clear_delay = self.timing_engine.get_delay(0.3, 0.1, 'typing')
            await asyncio.sleep(clear_delay)
        except Exception as e:
            log_warning(f"[TYPING] Field clearing failed: {e}")
    
    async def _type_with_errors_and_corrections(self, page: Any, element: Any, 
                                              text: str, context: str) -> None:
        """
        Type text with realistic errors and corrections
        Consolidates advanced_error_simulation and human typing logic
        """
        i = 0
        while i < len(text):
            char = text[i]
            
            # Thinking pause (occasionally)
            if random.random() < self.profile.get_pause_frequency():
                thinking_delay = self.timing_engine.get_delay(1.0, 0.5, 'thinking')
                await asyncio.sleep(thinking_delay)
            
            # Check for error
            if self.should_make_error() and i > 0 and i < len(text) - 1:
                await self._make_typing_error(page, element, char, text, i)
                self.last_error_time = datetime.now()
                self.recent_errors.append(datetime.now())
            else:
                # Normal typing
                await page.keyboard.type(char)
            
            # Variable typing speed
            typing_delay = self._get_character_delay(char)
            await asyncio.sleep(typing_delay)
            
            i += 1
    
    async def _make_typing_error(self, page: Any, element: Any, char: str, 
                               full_text: str, position: int) -> None:
        """Make a realistic typing error and correct it"""
        error_types = ['wrong_char', 'double_char', 'transpose']
        
        # Skip transpose if at end of text
        if position >= len(full_text) - 1:
            error_types.remove('transpose')
        
        error_type = random.choice(error_types)
        
        if error_type == 'wrong_char':
            # Type wrong character
            wrong_char = self.get_similar_char(char)
            await page.keyboard.type(wrong_char)
            
            # Realize error and correct
            await self.simulate_correction(page, element, 1)
            await page.keyboard.type(char)
            
        elif error_type == 'double_char':
            # Type character twice
            await page.keyboard.type(char + char)
            
            # Realize error and correct
            await self.simulate_correction(page, element, 1)
            
        elif error_type == 'transpose':
            # Type next character first, then current
            next_char = full_text[position + 1]
            await page.keyboard.type(next_char + char)
            
            # Realize error and correct
            await self.simulate_correction(page, element, 2)
            await page.keyboard.type(char)
            # Note: next character will be typed in next iteration
    
    def _get_character_delay(self, char: str) -> float:
        """Get delay for typing specific character"""
        base_delay = 1.0 / self.profile.get_typing_speed()
        
        # Longer delays for punctuation (natural pause)
        if char in '.!?,:;':
            base_delay *= random.uniform(1.5, 2.5)
        
        # Shorter delays for common characters
        elif char in 'etaoinshrdlu':  # Most common English letters
            base_delay *= random.uniform(0.8, 1.0)
        
        # Apply timing engine variance
        return self.timing_engine.get_delay(base_delay, 0.3, 'typing')
    
    async def simulate_form_hesitation(self, page: Any, element: Any) -> None:
        """Simulate hesitation when filling forms"""
        try:
            box = await element.bounding_box()
            if not box:
                return
            
            # Hover over different parts of the form
            hesitation_count = random.randint(1, 3)
            
            for _ in range(hesitation_count):
                hover_x = box['x'] + box['width'] * random.uniform(0.2, 0.8)
                hover_y = box['y'] + box['height'] * random.uniform(0.2, 0.8)
                
                await page.mouse.move(hover_x, hover_y)
                
                # Thinking pause
                hesitation_delay = self.timing_engine.get_delay(0.8, 0.4, 'thinking')
                await asyncio.sleep(hesitation_delay)
            
        except Exception as e:
            log_warning(f"[TYPING] Form hesitation failed: {e}")