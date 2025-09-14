"""
Unified Human Behavior System
Provides backward compatibility while using the new refactored core
Follows Liskov Substitution Principle - can replace existing implementations
"""

import asyncio
import random
from typing import Any, Optional
from datetime import datetime

# Import new refactored system
from human_behavior_core import (
    HumanBehavior,
    TimingEngine,
    MouseBehavior,
    TypingBehavior,
    BehaviorProfile
)

try:
    from logging_utils import log_info, log_warning, log_error
except ImportError:
    # Fallback logging
    def log_info(msg): print(f"INFO: {msg}")
    def log_warning(msg): print(f"WARNING: {msg}")
    def log_error(msg): print(f"ERROR: {msg}")


class UnifiedHumanBehavior:
    """
    Unified human behavior that maintains compatibility with existing code
    Consolidates AdvancedHumanBehavior from both sync and async implementations
    """
    
    def __init__(self, page: Any):
        self.page = page
        
        # Initialize new refactored system
        self.profile = BehaviorProfile()
        self.timing_engine = TimingEngine()
        self.mouse_behavior = MouseBehavior(self.timing_engine, self.profile)
        self.typing_behavior = TypingBehavior(self.timing_engine, self.profile)
        self.human_behavior = HumanBehavior(
            self.timing_engine,
            self.mouse_behavior,
            self.typing_behavior,
            self.profile
        )
        
        # Maintain compatibility properties
        self.session_start = datetime.now()
        self.action_count = 0
        self.fatigue_level = 0.0
        
        log_info(f"[UNIFIED_HUMAN] Initialized with {self.profile.get_description()}")
    
    # === Backward Compatibility Methods ===
    
    async def human_click(self, element: Any, context: str = "general") -> bool:
        """Backward compatible click method"""
        return await self.human_behavior.click_with_behavior(self.page, element, context)
    
    async def human_type(self, element: Any, text: str, context: str = "general") -> bool:
        """Backward compatible typing method"""
        return await self.human_behavior.type_with_behavior(self.page, element, text, context)
    
    async def natural_page_scan(self) -> None:
        """Backward compatible page scanning"""
        await self.human_behavior.scan_page(self.page)
    
    def _calculate_fatigue(self) -> float:
        """Backward compatible fatigue calculation"""
        return self.timing_engine.get_fatigue_multiplier()
    
    def _get_time_of_day_multiplier(self) -> float:
        """Backward compatible time multiplier"""
        return self.timing_engine.get_time_multiplier()
    
    def _should_make_error(self) -> bool:
        """Backward compatible error check"""
        return self.typing_behavior.should_make_error()
    
    def _should_pause_to_think(self) -> bool:
        """Backward compatible thinking pause check"""
        return random.random() < self.profile.get_pause_frequency()
    
    async def _thinking_pause(self, context: str = "general") -> None:
        """Backward compatible thinking pause"""
        thinking_delay = self.timing_engine.get_delay(1.5, 0.5, 'thinking')
        await asyncio.sleep(thinking_delay)
    
    async def _natural_mouse_movement(self, element: Any) -> None:
        """Backward compatible mouse movement"""
        await self.mouse_behavior.move_to_element(self.page, element)
    
    async def _curved_mouse_movement(self, start_x: float, start_y: float, 
                                   end_x: float, end_y: float) -> None:
        """Backward compatible curved movement"""
        await self.mouse_behavior._curved_mouse_movement(self.page, start_x, start_y, end_x, end_y)
    
    def _get_similar_char(self, char: str) -> str:
        """Backward compatible similar character"""
        return self.typing_behavior.get_similar_char(char)
    
    async def human_scroll(self, direction: str = "down", amount: int = 3) -> None:
        """Backward compatible scrolling"""
        try:
            for _ in range(amount):
                if direction == "down":
                    await self.page.mouse.wheel(0, random.randint(100, 300))
                else:
                    await self.page.mouse.wheel(0, -random.randint(100, 300))
                
                scroll_delay = self.timing_engine.get_delay(0.5, 0.3, 'general')
                await asyncio.sleep(scroll_delay)
                
        except Exception as e:
            log_warning(f"[UNIFIED_HUMAN] Scroll failed: {e}")
    
    async def simulate_reading(self, element: Any, estimated_words: int = 10) -> None:
        """Backward compatible reading simulation"""
        await self.human_behavior.simulate_reading_delay(estimated_words * 5)  # Convert words to chars
    
    # === Enhanced Methods Using New System ===
    
    async def simulate_workflow_delays(self, context: str = "general") -> None:
        """Enhanced workflow delays using new timing engine"""
        await self.human_behavior.simulate_workflow_delay(context)
    
    async def simulate_attention_patterns(self) -> None:
        """Enhanced attention patterns using new system"""
        await self.human_behavior.simulate_attention_patterns(self.page)
    
    def get_session_stats(self) -> dict:
        """Get comprehensive session statistics"""
        return self.human_behavior.get_session_stats()
    
    def reset_session(self) -> None:
        """Reset session for new upload"""
        self.human_behavior.reset_session()
        self.session_start = datetime.now()
        self.action_count = 0
        self.fatigue_level = 0.0


# === Global Instance Management ===

_global_unified_behavior: Optional[UnifiedHumanBehavior] = None


def init_unified_human_behavior(page: Any, profile_type: str = None) -> UnifiedHumanBehavior:
    """
    Initialize unified human behavior system
    Replaces both init_advanced_human_behavior and init_human_behavior_async
    """
    global _global_unified_behavior
    
    _global_unified_behavior = UnifiedHumanBehavior(page)
    if profile_type:
        _global_unified_behavior.profile = BehaviorProfile(profile_type)
    
    log_info("[UNIFIED_HUMAN] Global instance initialized")
    return _global_unified_behavior


def get_unified_human_behavior() -> Optional[UnifiedHumanBehavior]:
    """
    Get unified human behavior instance
    Replaces both get_advanced_human_behavior and get_human_behavior
    """
    return _global_unified_behavior


# === Compatibility Functions for Existing Code ===

async def click_element_with_behavior_unified(page: Any, element: Any, element_name: str) -> bool:
    """
    Unified click function that replaces click_element_with_behavior_async
    Maintains same interface but uses new refactored system
    """
    behavior = get_unified_human_behavior()
    if behavior:
        return await behavior.human_click(element, element_name)
    else:
        # Fallback to simple click
        try:
            await element.click()
            return True
        except Exception as e:
            log_error(f"[UNIFIED_HUMAN] Fallback click failed: {e}")
            return False


async def type_like_human_unified(page: Any, element: Any, text: str, context: str = "typing") -> bool:
    """
    Unified typing function that replaces _type_like_human_async
    Maintains same interface but uses new refactored system
    """
    behavior = get_unified_human_behavior()
    if behavior:
        return await behavior.human_type(element, text, context)
    else:
        # Fallback to simple typing
        try:
            await element.fill(text)
            return True
        except Exception as e:
            log_error(f"[UNIFIED_HUMAN] Fallback typing failed: {e}")
            return False


async def simulate_page_scan_unified(page: Any) -> None:
    """
    Unified page scanning that replaces simulate_page_scan_async
    """
    behavior = get_unified_human_behavior()
    if behavior:
        await behavior.natural_page_scan()
    else:
        # Simple fallback
        try:
            await page.evaluate("""
                window.scrollBy({
                    top: Math.random() * 200 - 100,
                    left: 0,
                    behavior: 'smooth'
                });
            """)
            await asyncio.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            log_warning(f"[UNIFIED_HUMAN] Fallback page scan failed: {e}")


# === Import compatibility ===
# Allow existing code to import the old names but get the new implementations

# For backward compatibility with existing imports
AdvancedHumanBehavior = UnifiedHumanBehavior
init_advanced_human_behavior = init_unified_human_behavior
get_advanced_human_behavior = get_unified_human_behavior