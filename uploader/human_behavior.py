"""
Human Behavior Simulation for Instagram Automation
Provides realistic human-like behavior patterns
"""

import time
import random
import math
from .logging_utils import log_info, log_warning, log_error


class AdvancedHumanBehavior:
    """Advanced human behavior simulation for Instagram automation"""
    
    def __init__(self, page):
        self.page = page
        self.typing_speed_base = 0.1  # Base typing speed
        self.typing_speed_variance = 0.05  # Variance in typing speed
        self.mouse_movement_speed = 1.0  # Mouse movement speed multiplier
        
    def get_human_delay(self, base_delay=1.0, variance=0.5):
        """
        Generate human-like delay with natural variance
        
        Args:
            base_delay: Base delay in seconds
            variance: Maximum variance as fraction of base_delay
        
        Returns:
            float: Randomized delay time
        """
        min_delay = base_delay * (1 - variance)
        max_delay = base_delay * (1 + variance)
        
        # Use normal distribution for more realistic timing
        delay = random.normalvariate(base_delay, variance * base_delay / 3)
        
        # Clamp to reasonable bounds
        delay = max(min_delay, min(max_delay, delay))
        
        return delay
    
    def simulate_reading_time(self, text_length):
        """
        Simulate time needed to read text (average reading speed: 200-250 WPM)
        
        Args:
            text_length: Length of text to read
            
        Returns:
            float: Reading time in seconds
        """
        words_per_minute = random.uniform(200, 250)
        estimated_words = text_length / 5  # Average word length
        reading_time = (estimated_words / words_per_minute) * 60
        
        # Add some variance and minimum time
        reading_time = max(1.0, reading_time * random.uniform(0.8, 1.2))
        
        return reading_time
    
    def natural_mouse_movement(self, target_element):
        """
        Simulate natural mouse movement to element
        
        Args:
            target_element: Element to move mouse to
        """
        try:
            # Get element position
            box = target_element.bounding_box()
            if not box:
                return
            
            # Calculate target position (slightly randomized within element)
            target_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            target_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
            
            # Move mouse in natural arc
            self.page.mouse.move(target_x, target_y)
            
            # Small pause after movement
            time.sleep(self.get_human_delay(0.1, 0.05))
            
        except Exception as e:
            log_warning(f"Mouse movement simulation failed: {str(e)}")
    
    def human_typing(self, element, text, simulate_mistakes=True):
        """
        Type text with human-like behavior including mistakes and corrections
        
        Args:
            element: Element to type into
            text: Text to type
            simulate_mistakes: Whether to simulate typing mistakes
        """
        try:
            # Click on element first
            element.click()
            time.sleep(self.get_human_delay(0.3, 0.1))
            
            # Clear existing content
            element.fill('')
            time.sleep(self.get_human_delay(0.2, 0.1))
            
            typed_text = ""
            i = 0
            
            while i < len(text):
                char = text[i]
                
                # Simulate typing mistake (5% chance)
                if simulate_mistakes and random.random() < 0.05 and i > 0:
                    # Type wrong character
                    wrong_chars = 'abcdefghijklmnopqrstuvwxyz'
                    wrong_char = random.choice(wrong_chars)
                    element.type(wrong_char)
                    typed_text += wrong_char
                    
                    # Pause to "notice" mistake
                    time.sleep(self.get_human_delay(0.3, 0.1))
                    
                    # Backspace to correct
                    element.press('Backspace')
                    typed_text = typed_text[:-1]
                    time.sleep(self.get_human_delay(0.1, 0.05))
                
                # Type correct character
                element.type(char)
                typed_text += char
                
                # Variable typing speed
                typing_delay = self.get_human_delay(self.typing_speed_base, self.typing_speed_variance)
                time.sleep(typing_delay)
                
                i += 1
            
            # Small pause after typing
            time.sleep(self.get_human_delay(0.5, 0.2))
            
        except Exception as e:
            log_warning(f"Human typing simulation failed: {str(e)}")
            # Fallback to simple fill
            element.fill(text)
    
    def simulate_decision_making(self, options_count=1):
        """
        Simulate time needed for decision making
        
        Args:
            options_count: Number of options to consider
        """
        base_time = 0.5 + (options_count * 0.3)
        decision_time = self.get_human_delay(base_time, 0.3)
        time.sleep(decision_time)
    
    def simulate_page_scanning(self):
        """Simulate time spent scanning/reading page content"""
        scan_time = self.get_human_delay(2.0, 1.0)
        time.sleep(scan_time)
    
    def simulate_distraction(self):
        """
        Simulate brief distraction/pause in activity
        """
        if random.random() < 0.1:  # 10% chance of distraction
            distraction_time = self.get_human_delay(2.0, 1.0)
            log_info(f"Simulating brief distraction for {distraction_time:.1f}s")
            time.sleep(distraction_time)
    
    def advanced_element_interaction(self, element, action='click'):
        """
        Perform advanced interaction with element including natural movement
        
        Args:
            element: Element to interact with
            action: Type of interaction ('click', 'hover', etc.)
        """
        try:
            # Ensure element is in viewport
            element.scroll_into_view_if_needed()
            time.sleep(self.get_human_delay(0.2, 0.1))
            
            # Natural mouse movement to element
            self.natural_mouse_movement(element)
            
            # Brief pause before action
            time.sleep(self.get_human_delay(0.1, 0.05))
            
            # Perform action
            if action == 'click':
                element.click()
            elif action == 'hover':
                element.hover()
            
            # Brief pause after action
            time.sleep(self.get_human_delay(0.2, 0.1))
            
        except Exception as e:
            log_warning(f"Advanced element interaction failed: {str(e)}")
            # Fallback to simple action
            if action == 'click':
                element.click()
            elif action == 'hover':
                element.hover()


# Global variable to store human behavior instance
human_behavior = None


def init_human_behavior(page):
    """Initialize human behavior for the given page"""
    global human_behavior
    if not human_behavior:
        human_behavior = AdvancedHumanBehavior(page)
        log_info("Human behavior initialized")
    return human_behavior


def get_human_behavior():
    """Get the current human behavior instance"""
    return human_behavior 