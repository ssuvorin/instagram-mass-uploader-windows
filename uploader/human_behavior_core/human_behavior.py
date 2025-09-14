"""
Main Human Behavior Implementation
Coordinates all behavior components - Dependency Inversion Principle
"""

import asyncio
import random
from typing import Any, Optional
from .interfaces import IHumanBehavior, ITimingEngine, IMouseBehavior, ITypingBehavior, IBehaviorProfile
from .timing_engine import TimingEngine
from .mouse_behavior import MouseBehavior
from .typing_behavior import TypingBehavior
from .behavior_profile import BehaviorProfile
try:
    from logging_utils import log_info, log_warning, log_error
except ImportError:
    # Fallback logging for testing
    def log_info(msg): print(f"INFO: {msg}")
    def log_warning(msg): print(f"WARNING: {msg}")
    def log_error(msg): print(f"ERROR: {msg}")


class HumanBehavior(IHumanBehavior):
    """
    Main human behavior coordinator
    Follows Dependency Inversion - depends on abstractions, not concretions
    Consolidates AdvancedHumanBehavior functionality from both sync and async implementations
    """
    
    def __init__(self, 
                 timing_engine: Optional[ITimingEngine] = None,
                 mouse_behavior: Optional[IMouseBehavior] = None,
                 typing_behavior: Optional[ITypingBehavior] = None,
                 profile: Optional[IBehaviorProfile] = None):
        """
        Initialize with dependency injection
        Allows easy testing and configuration
        """
        # Create default implementations if not provided
        self.profile = profile or BehaviorProfile()
        self.timing_engine = timing_engine or TimingEngine()
        self.mouse_behavior = mouse_behavior or MouseBehavior(self.timing_engine, self.profile)
        self.typing_behavior = typing_behavior or TypingBehavior(self.timing_engine, self.profile)
        
        log_info(f"[HUMAN_BEHAVIOR] Initialized with {self.profile.get_description()}")
    
    async def click_with_behavior(self, page: Any, element: Any, context: str = 'general') -> bool:
        """
        Click element with full human behavior simulation
        Consolidates human_click from both implementations
        """
        try:
            self.update_session_state()
            
            # Check if break is needed
            if self.timing_engine.should_take_break():
                await self.timing_engine.take_break()
            
            # Perform click with mouse behavior
            success = await self.mouse_behavior.click_element(page, element, context)
            
            if success:
                log_info(f"[HUMAN_BEHAVIOR] Successfully clicked element ({context})")
            else:
                log_warning(f"[HUMAN_BEHAVIOR] Click failed, attempting fallback ({context})")
                # Fallback to simple click
                try:
                    await element.click()
                    success = True
                except Exception as e:
                    log_error(f"[HUMAN_BEHAVIOR] Fallback click failed: {e}")
            
            return success
            
        except Exception as e:
            log_error(f"[HUMAN_BEHAVIOR] Click with behavior failed: {e}")
            return False
    
    async def type_with_behavior(self, page: Any, element: Any, text: str, context: str = 'general') -> bool:
        """
        Type text with full human behavior simulation
        Consolidates human_type from both implementations
        """
        try:
            self.update_session_state()
            
            # Check if break is needed
            if self.timing_engine.should_take_break():
                await self.timing_engine.take_break()
            
            # Perform typing with typing behavior
            success = await self.typing_behavior.type_text(page, element, text, context)
            
            if success:
                log_info(f"[HUMAN_BEHAVIOR] Successfully typed {len(text)} characters ({context})")
            else:
                log_warning(f"[HUMAN_BEHAVIOR] Typing failed, attempting fallback ({context})")
                # Fallback to simple fill
                try:
                    await element.fill(text)
                    success = True
                except Exception as e:
                    log_error(f"[HUMAN_BEHAVIOR] Fallback typing failed: {e}")
            
            return success
            
        except Exception as e:
            log_error(f"[HUMAN_BEHAVIOR] Type with behavior failed: {e}")
            return False
    
    async def scan_page(self, page: Any) -> None:
        """
        Perform natural page scanning
        Consolidates natural_page_scan and simulate_page_scan_async
        """
        try:
            log_info("[HUMAN_BEHAVIOR] Starting page scan")
            
            # Mouse-based scanning
            await self.mouse_behavior.simulate_scanning(page)
            
            # Optional scroll-based scanning
            if random.random() < 0.3:  # 30% chance
                await self._simulate_scroll_scanning(page)
            
            log_info("[HUMAN_BEHAVIOR] Page scan completed")
            
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Page scan failed: {e}")
    
    async def simulate_workflow_delay(self, context: str = 'general') -> None:
        """
        Add workflow delays between actions
        Consolidates workflow delay logic
        """
        try:
            # Base workflow delay
            workflow_delay = self.timing_engine.get_delay(2.0, 1.0, 'workflow')
            
            # Add occasional distractions
            if random.random() < 0.1:  # 10% chance
                distraction_delay = self.timing_engine.get_delay(5.0, 3.0, 'thinking')
                log_info(f"[HUMAN_BEHAVIOR] Simulating distraction for {distraction_delay:.1f}s")
                await asyncio.sleep(distraction_delay)
            
            log_info(f"[HUMAN_BEHAVIOR] Workflow delay: {workflow_delay:.1f}s ({context})")
            await asyncio.sleep(workflow_delay)
            
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Workflow delay failed: {e}")
    
    def update_session_state(self) -> None:
        """Update internal session state (fatigue, action count, etc.)"""
        # Update timing engine state (increments action count, calculates fatigue)
        self.timing_engine.get_fatigue_multiplier()
        
        # Adjust profile based on fatigue if needed
        fatigue_level = self.timing_engine.get_fatigue_multiplier()
        if fatigue_level > 1.3:  # High fatigue
            self.profile.adjust_for_fatigue(fatigue_level)
    
    async def simulate_attention_patterns(self, page: Any) -> None:
        """
        Simulate natural attention patterns
        Consolidates simulate_attention_patterns_async functionality
        """
        try:
            # Look at different elements briefly
            attention_targets = ['h1', 'h2', 'button', '[role="button"]', 'img']
            
            for selector in attention_targets:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        # Pick random visible element
                        for element in elements[:3]:  # Check first 3
                            if await element.is_visible():
                                await self.mouse_behavior.hover_element(page, element)
                                break
                except Exception:
                    continue
            
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Attention patterns failed: {e}")
    
    async def simulate_reading_delay(self, text_length: int) -> None:
        """Simulate time needed to read text"""
        # Average reading speed: 200-250 WPM
        words_per_minute = random.uniform(200, 250)
        estimated_words = text_length / 5  # Average word length
        reading_time = (estimated_words / words_per_minute) * 60
        
        # Apply timing engine for consistency
        reading_delay = self.timing_engine.get_delay(reading_time, 0.3, 'reading')
        
        log_info(f"[HUMAN_BEHAVIOR] Reading delay: {reading_delay:.1f}s for {estimated_words:.0f} words")
        await asyncio.sleep(reading_delay)
    
    async def _simulate_scroll_scanning(self, page: Any) -> None:
        """Simulate scanning with scrolling"""
        try:
            scroll_count = random.randint(1, 3)
            
            for _ in range(scroll_count):
                # Random scroll direction and amount
                direction = random.choice([1, -1])  # down or up
                amount = random.randint(100, 300) * direction
                
                await page.mouse.wheel(0, amount)
                
                # Pause to "read" content
                scan_delay = self.timing_engine.get_delay(1.0, 0.5, 'reading')
                await asyncio.sleep(scan_delay)
                
        except Exception as e:
            log_warning(f"[HUMAN_BEHAVIOR] Scroll scanning failed: {e}")
    
    def get_session_stats(self) -> dict:
        """Get current session statistics"""
        return {
            'profile_type': self.profile.get_profile_type(),
            'profile_description': self.profile.get_description(),
            **self.timing_engine.get_session_stats()
        }
    
    def reset_session(self) -> None:
        """Reset session state for new upload session"""
        self.timing_engine.reset_session()
        self.profile.reset_to_baseline()
        log_info("[HUMAN_BEHAVIOR] Session reset completed")


# Global instance management for backward compatibility
_global_human_behavior: Optional[HumanBehavior] = None


def init_human_behavior_unified(page: Any, profile_type: str = None) -> HumanBehavior:
    """
    Initialize unified human behavior system
    Replaces both init_advanced_human_behavior and init_human_behavior_async
    """
    global _global_human_behavior
    
    profile = BehaviorProfile(profile_type)
    _global_human_behavior = HumanBehavior(profile=profile)
    
    log_info(f"[HUMAN_BEHAVIOR] Unified system initialized with {profile.get_description()}")
    return _global_human_behavior


def get_human_behavior_unified() -> Optional[HumanBehavior]:
    """
    Get unified human behavior instance
    Replaces both get_advanced_human_behavior and get_human_behavior
    """
    return _global_human_behavior