"""
Human Behavior Core Module
Refactored human behavior system following SOLID principles
"""

from .interfaces import (
    ITimingEngine,
    IMouseBehavior, 
    ITypingBehavior,
    IHumanBehavior,
    IBehaviorProfile
)

from .timing_engine import TimingEngine
from .mouse_behavior import MouseBehavior
from .typing_behavior import TypingBehavior
from .behavior_profile import BehaviorProfile
from .human_behavior import HumanBehavior

__all__ = [
    'ITimingEngine',
    'IMouseBehavior', 
    'ITypingBehavior',
    'IHumanBehavior',
    'IBehaviorProfile',
    'TimingEngine',
    'MouseBehavior',
    'TypingBehavior',
    'BehaviorProfile',
    'HumanBehavior'
]