"""
Mouse Behavior Implementation
Handles all mouse movement and clicking behavior - Single Responsibility Principle
"""

import asyncio
import random
import math
from typing import Any, Optional, Tuple
from .interfaces import IMouseBehavior, ITimingEngine, IBehaviorProfile
try:
    from logging_utils import log_info, log_warning, log_debug
except ImportError:
    # Fallback logging for testing
    def log_info(msg): print(f"INFO: {msg}")
    def log_warning(msg): print(f"WARNING: {msg}")
    def log_debug(msg): print(f"DEBUG: {msg}")


class MouseBehavior(IMouseBehavior):
    """
    Consolidated mouse behavior implementation
    Eliminates duplication between sync and async mouse movement code
    """
    
    def __init__(self, timing_engine: ITimingEngine, profile: IBehaviorProfile):
        self.timing_engine = timing_engine
        self.profile = profile
        self.last_position = (0, 0)
    
    async def move_to_element(self, page: Any, element: Any) -> bool:
        """
        Move mouse to element with human-like trajectory
        Consolidates _natural_mouse_movement and _curved_mouse_movement logic
        """
        try:
            # Normalize element to handle both Locator and ElementHandle
            if hasattr(element, "first"):
                element = element.first()
            
            # Ensure element is in viewport
            try:
                await element.scroll_into_view_if_needed(timeout=2000)
            except Exception:
                pass
            
            # Get element bounding box
            box = await element.bounding_box()
            if not box:
                log_warning("[MOUSE] Could not get element bounding box")
                return False
            
            # Calculate target position with precision variance
            precision = self.profile.get_mouse_precision()
            target_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            target_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
            
            # Add imprecision based on profile
            offset_range = (1 - precision) * 10
            target_x += random.uniform(-offset_range, offset_range)
            target_y += random.uniform(-offset_range, offset_range)
            
            # Perform curved movement
            await self._curved_mouse_movement(page, self.last_position[0], self.last_position[1], 
                                            target_x, target_y)
            
            self.last_position = (target_x, target_y)
            return True
            
        except Exception as e:
            log_warning(f"[MOUSE] Move to element failed: {e}")
            return False
    
    async def click_element(self, page: Any, element: Any, context: str = 'general') -> bool:
        """
        Click element with human-like behavior
        Consolidates human_click logic from both sync and async implementations
        """
        try:
            # Move to element first
            if not await self.move_to_element(page, element):
                log_warning("[MOUSE] Failed to move to element before click")
                # Continue anyway, element might still be clickable
            
            # Pre-click thinking pause
            if random.random() < self.profile.get_pause_frequency():
                thinking_delay = self.timing_engine.get_delay(0.8, 0.3, 'thinking')
                await asyncio.sleep(thinking_delay)
            
            # Hover before click (natural human behavior)
            hover_delay = self.timing_engine.get_delay(0.1, 0.05, 'clicking')
            await asyncio.sleep(hover_delay)
            
            try:
                await element.hover(timeout=2000)
            except Exception:
                pass
            
            # Brief pause after hover
            await asyncio.sleep(random.uniform(0.05, 0.15))
            
            # Perform click
            await element.click()
            
            # Post-click delay
            post_click_delay = self.timing_engine.get_delay(0.5, 0.3, context)
            await asyncio.sleep(post_click_delay)
            
            log_debug(f"[MOUSE] Successfully clicked element ({context})")
            return True
            
        except Exception as e:
            log_warning(f"[MOUSE] Click element failed: {e}")
            return False
    
    async def hover_element(self, page: Any, element: Any) -> bool:
        """Hover over element naturally"""
        try:
            if not await self.move_to_element(page, element):
                return False
            
            await element.hover()
            
            # Natural hover duration
            hover_duration = self.timing_engine.get_delay(0.3, 0.2, 'general')
            await asyncio.sleep(hover_duration)
            
            return True
            
        except Exception as e:
            log_warning(f"[MOUSE] Hover element failed: {e}")
            return False
    
    async def simulate_scanning(self, page: Any) -> None:
        """
        Simulate page scanning with mouse movements
        Consolidates natural_page_scan and simulate_page_scan_async logic
        """
        try:
            viewport = await page.viewport_size()
            if not viewport:
                return
            
            # Random scanning movements
            scan_count = random.randint(2, 5)
            
            for _ in range(scan_count):
                # Random position within safe bounds
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                
                # Move to position
                await page.mouse.move(x, y)
                self.last_position = (x, y)
                
                # Pause to "read" content at this position
                scan_delay = self.timing_engine.get_delay(0.8, 0.4, 'reading')
                await asyncio.sleep(scan_delay)
            
            log_debug("[MOUSE] Page scanning completed")
            
        except Exception as e:
            log_warning(f"[MOUSE] Page scanning failed: {e}")
    
    async def _curved_mouse_movement(self, page: Any, start_x: float, start_y: float, 
                                   end_x: float, end_y: float) -> None:
        """
        Move mouse in curved trajectory using Bezier curves
        Consolidates curved movement logic from both implementations
        """
        try:
            # Calculate distance for step count
            distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
            steps = max(8, min(20, int(distance / 50)))  # Adaptive step count
            
            # Create control points for Bezier curve
            mid_x = (start_x + end_x) / 2
            mid_y = (start_y + end_y) / 2
            
            # Add curve deviation based on distance
            curve_intensity = min(50, distance / 10)
            control_x = mid_x + random.uniform(-curve_intensity, curve_intensity)
            control_y = mid_y + random.uniform(-curve_intensity/2, curve_intensity/2)
            
            # Execute curved movement
            for i in range(steps + 1):
                t = i / steps
                
                # Quadratic Bezier curve calculation
                x = (1 - t)**2 * start_x + 2 * (1 - t) * t * control_x + t**2 * end_x
                y = (1 - t)**2 * start_y + 2 * (1 - t) * t * control_y + t**2 * end_y
                
                # Add micro-variations for naturalness
                x += random.uniform(-2, 2)
                y += random.uniform(-2, 2)
                
                await page.mouse.move(x, y)
                
                # Variable movement speed
                move_delay = random.uniform(0.01, 0.03)
                await asyncio.sleep(move_delay)
            
        except Exception as e:
            log_warning(f"[MOUSE] Curved movement failed: {e}")
            # Fallback to direct movement
            try:
                await page.mouse.move(end_x, end_y)
            except Exception:
                pass
    
    async def simulate_idle_movement(self, page: Any, duration: float = 2.0) -> None:
        """Simulate random mouse movements during idle time"""
        try:
            viewport = await page.viewport_size()
            if not viewport:
                return
            
            start_time = asyncio.get_event_loop().time()
            movements = random.randint(2, 4)
            
            for i in range(movements):
                if asyncio.get_event_loop().time() - start_time >= duration:
                    break
                
                # Random position
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                
                await page.mouse.move(x, y)
                self.last_position = (x, y)
                
                # Pause between movements
                pause_time = duration / movements
                await asyncio.sleep(pause_time * random.uniform(0.5, 1.5))
            
        except Exception as e:
            log_warning(f"[MOUSE] Idle movement failed: {e}")
    
    def update_position(self, x: float, y: float) -> None:
        """Update last known mouse position"""
        self.last_position = (x, y)