"""
Human Behavior Interfaces
Following Interface Segregation Principle - separate concerns into focused interfaces
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from datetime import datetime


class ITimingEngine(ABC):
    """Interface for timing and delay calculations - Single Responsibility"""
    
    @abstractmethod
    def get_delay(self, base_delay: float, variance: float = 0.5, context: str = 'general') -> float:
        """Calculate human-like delay with variance"""
        pass
    
    @abstractmethod
    def get_time_multiplier(self) -> float:
        """Get time-of-day based multiplier"""
        pass
    
    @abstractmethod
    def get_fatigue_multiplier(self) -> float:
        """Get fatigue-based multiplier"""
        pass
    
    @abstractmethod
    def should_take_break(self) -> bool:
        """Determine if a break should be taken"""
        pass


class IMouseBehavior(ABC):
    """Interface for mouse movement and clicking behavior - Single Responsibility"""
    
    @abstractmethod
    async def move_to_element(self, page: Any, element: Any) -> bool:
        """Move mouse to element with human-like trajectory"""
        pass
    
    @abstractmethod
    async def click_element(self, page: Any, element: Any, context: str = 'general') -> bool:
        """Click element with human-like behavior"""
        pass
    
    @abstractmethod
    async def hover_element(self, page: Any, element: Any) -> bool:
        """Hover over element naturally"""
        pass
    
    @abstractmethod
    async def simulate_scanning(self, page: Any) -> None:
        """Simulate page scanning with mouse movements"""
        pass


class ITypingBehavior(ABC):
    """Interface for typing behavior - Single Responsibility"""
    
    @abstractmethod
    async def type_text(self, page: Any, element: Any, text: str, context: str = 'general') -> bool:
        """Type text with human-like behavior including errors"""
        pass
    
    @abstractmethod
    def should_make_error(self) -> bool:
        """Determine if typing error should be made"""
        pass
    
    @abstractmethod
    def get_similar_char(self, char: str) -> str:
        """Get similar character for typing errors"""
        pass
    
    @abstractmethod
    async def simulate_correction(self, page: Any, element: Any, error_length: int) -> None:
        """Simulate error correction behavior"""
        pass


class IHumanBehavior(ABC):
    """Main interface for human behavior coordination - Dependency Inversion"""
    
    @abstractmethod
    async def click_with_behavior(self, page: Any, element: Any, context: str = 'general') -> bool:
        """Click element with full human behavior simulation"""
        pass
    
    @abstractmethod
    async def type_with_behavior(self, page: Any, element: Any, text: str, context: str = 'general') -> bool:
        """Type text with full human behavior simulation"""
        pass
    
    @abstractmethod
    async def scan_page(self, page: Any) -> None:
        """Perform natural page scanning"""
        pass
    
    @abstractmethod
    async def simulate_workflow_delay(self, context: str = 'general') -> None:
        """Add workflow delays between actions"""
        pass
    
    @abstractmethod
    def update_session_state(self) -> None:
        """Update internal session state (fatigue, action count, etc.)"""
        pass


class IBehaviorProfile(ABC):
    """Interface for behavior profile configuration - Open/Closed Principle"""
    
    @abstractmethod
    def get_typing_speed(self) -> float:
        """Get typing speed for this profile"""
        pass
    
    @abstractmethod
    def get_error_rate(self) -> float:
        """Get error rate for this profile"""
        pass
    
    @abstractmethod
    def get_pause_frequency(self) -> float:
        """Get pause frequency for this profile"""
        pass
    
    @abstractmethod
    def get_mouse_precision(self) -> float:
        """Get mouse precision for this profile"""
        pass
    
    @abstractmethod
    def get_profile_type(self) -> str:
        """Get profile type identifier"""
        pass