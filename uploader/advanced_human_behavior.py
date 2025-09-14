"""
Advanced Human Behavior Simulation for Instagram Automation
REFACTORED: Now uses unified human behavior system following SOLID principles
Максимально человеческое поведение для обхода детекции автоматизации
"""

import asyncio
import random
import math
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from .logging_utils import log_info, log_warning, log_error

# Import the new unified system
from .human_behavior_unified import (
    UnifiedHumanBehavior,
    init_unified_human_behavior,
    get_unified_human_behavior
)


# Legacy profile class - now redirects to new system
class HumanBehaviorProfile:
    """
    DEPRECATED: Legacy profile class for backward compatibility
    Now redirects to the new unified BehaviorProfile system
    """
    
    def __init__(self):
        from .human_behavior_core import BehaviorProfile
        self._new_profile = BehaviorProfile()
        self.profile_type = self._new_profile.get_profile_type()
        self.typing_speed = self._new_profile.get_typing_speed()
        self.error_rate = self._new_profile.get_error_rate()
        self.pause_frequency = self._new_profile.get_pause_frequency()
        self.mouse_precision = self._new_profile.get_mouse_precision()
        
        log_info(f"[LEGACY_PROFILE] Redirected to new system: {self._new_profile.get_description()}")


class AdvancedHumanBehavior:
    """
    REFACTORED: Advanced human behavior now uses unified system
    Maintains backward compatibility while using new SOLID architecture
    """
    
    def __init__(self, page):
        self.page = page
        
        # Initialize new unified system
        self._unified_behavior = UnifiedHumanBehavior(page)
        
        # Maintain backward compatibility properties
        self.profile = self._unified_behavior.profile
        self.session_start = self._unified_behavior.session_start
        self.action_count = self._unified_behavior.action_count
        self.last_action_time = datetime.now()
        self.fatigue_level = self._unified_behavior.fatigue_level
        self.recent_errors = []
        
        log_info(f"[ADVANCED_HUMAN] Initialized with unified system: {self.profile.get_description()}")
    
    def _calculate_fatigue(self) -> float:
        """
        ENHANCED: Improved fatigue calculation using centralized timing engine
        Maintains existing interface while using enhanced calculation system
        """
        # Use centralized timing engine for fatigue calculation
        from .human_behavior_core.timing_engine import get_timing_manager
        timing_manager = get_timing_manager()
        
        # Sync action count
        timing_manager.timing_engine.action_count = self.action_count
        
        # Get enhanced fatigue multiplier
        self.fatigue_level = timing_manager.timing_engine.get_fatigue_multiplier()
        
        return self.fatigue_level
    
    def _get_time_of_day_multiplier(self) -> float:
        """
        ENHANCED: Time-of-day logic using centralized timing engine
        Maintains existing interface while improving internal calculation quality
        """
        # Use centralized timing engine for time-of-day calculation
        from .human_behavior_core.timing_engine import get_timing_manager
        timing_manager = get_timing_manager()
        
        return timing_manager.timing_engine.get_time_multiplier()
    
    def _should_make_error(self) -> bool:
        """REFACTORED: Now uses unified typing behavior"""
        return self._unified_behavior._should_make_error()
    
    def _should_pause_to_think(self) -> bool:
        """REFACTORED: Now uses unified behavior profile"""
        return self._unified_behavior._should_pause_to_think()
    
    async def _thinking_pause(self, context: str = "general") -> None:
        """REFACTORED: Now uses unified timing engine"""
        await self._unified_behavior._thinking_pause(context)
    
    async def _natural_mouse_movement(self, element) -> None:
        """REFACTORED: Now uses unified mouse behavior"""
        await self._unified_behavior._natural_mouse_movement(element)
    
    async def _curved_mouse_movement(self, start_x: float, start_y: float, end_x: float, end_y: float) -> None:
        """REFACTORED: Now uses unified mouse behavior"""
        await self._unified_behavior._curved_mouse_movement(start_x, start_y, end_x, end_y)
    
    async def human_click(self, element, context: str = "general") -> bool:
        """
        ENHANCED: Human click with enhanced fatigue tracking
        Records actions for improved fatigue calculation
        """
        try:
            # Record action for fatigue calculation
            self.action_count += 1
            
            # Use unified behavior system with timeout
            success = await asyncio.wait_for(
                self._unified_behavior.human_click(element, context),
                timeout=5.0
            )
            
            return success
            
        except Exception as e:
            log_warning(f"[ADVANCED_HUMAN] Click failed: {str(e)[:100]}")
            
            # Fallback to simple click
            try:
                await element.click()
                return True
            except Exception:
                return False
    
    async def human_type(self, element, text: str, context: str = "general") -> bool:
        """
        ENHANCED: Human typing with enhanced fatigue tracking
        Records actions for improved fatigue calculation
        """
        try:
            # Record action for fatigue calculation
            self.action_count += 1
            
            # Use unified behavior system with timeout
            success = await asyncio.wait_for(
                self._unified_behavior.human_type(element, text, context),
                timeout=8.0
            )
            
            return success
            
        except Exception as e:
            log_warning(f"[ADVANCED_HUMAN] Typing failed: {str(e)[:100]}")
            
            # Fallback to simple typing
            try:
                await element.fill(text)
                return True
            except Exception:
                return False
    
    def _get_similar_char(self, char: str) -> str:
        """REFACTORED: Now uses unified typing behavior"""
        return self._unified_behavior._get_similar_char(char)
    
    async def human_scroll(self, direction: str = "down", amount: int = 3) -> None:
        """
        ENHANCED: Human scroll with robust error handling
        """
        try:
            await asyncio.wait_for(
                self._unified_behavior.human_scroll(direction, amount),
                timeout=4.0
            )
        except Exception as e:
            log_warning(f"[ADVANCED_HUMAN] Scroll failed: {str(e)[:100]}")
            # Simple fallback scroll
            try:
                delta_y = 300 if direction == "down" else -300
                await self.page.mouse.wheel(0, delta_y * amount)
            except Exception:
                pass
    
    async def simulate_reading(self, element, estimated_words: int = 10) -> None:
        """REFACTORED: Now uses unified human behavior system"""
        await self._unified_behavior.simulate_reading(element, estimated_words)
    
    async def natural_page_scan(self) -> None:
        """
        ENHANCED: Natural page scan with robust error handling
        """
        try:
            await asyncio.wait_for(
                self._unified_behavior.natural_page_scan(),
                timeout=10.0
            )
        except Exception as e:
            log_warning(f"[ADVANCED_HUMAN] Page scan failed: {str(e)[:100]}")
            # Simple fallback scan
            try:
                import random
                await asyncio.sleep(random.uniform(0.5, 1.5))
            except Exception:
                pass
    
    def should_take_break(self) -> bool:
        """
        ENHANCED: Determine if a break should be taken using centralized timing system
        """
        from .human_behavior_core.timing_engine import get_timing_manager
        timing_manager = get_timing_manager()
        return timing_manager.timing_engine.should_take_break()
    
    async def take_enhanced_break(self) -> None:
        """
        ENHANCED: Take a break using centralized timing system
        """
        from .human_behavior_core.timing_engine import get_timing_manager
        timing_manager = get_timing_manager()
        
        log_info("[ADVANCED_HUMAN] Taking break based on fatigue analysis")
        
        # Take the break using timing engine
        await timing_manager.timing_engine.take_break()
        
        log_info("[ADVANCED_HUMAN] Break completed, fatigue level reduced")
    
    def get_enhanced_fatigue_stats(self) -> dict:
        """
        ENHANCED: Get detailed fatigue statistics from centralized system
        """
        from .human_behavior_core.timing_engine import get_timing_manager
        timing_manager = get_timing_manager()
        
        return timing_manager.timing_engine.get_session_stats()


# REFACTORED: Global instance management now uses unified system
_global_human_behavior: Optional[AdvancedHumanBehavior] = None


def init_advanced_human_behavior(page) -> AdvancedHumanBehavior:
    """
    REFACTORED: Инициализация продвинутого человеческого поведения
    Now uses unified system while maintaining backward compatibility
    """
    global _global_human_behavior
    _global_human_behavior = AdvancedHumanBehavior(page)
    
    # Also initialize the unified system globally for other components
    init_unified_human_behavior(page)
    
    log_info("[ADVANCED_HUMAN] Initialized with unified system (backward compatible)")
    return _global_human_behavior


def get_advanced_human_behavior() -> Optional[AdvancedHumanBehavior]:
    """
    REFACTORED: Получить экземпляр продвинутого человеческого поведения
    Now returns wrapper around unified system
    """
    return _global_human_behavior