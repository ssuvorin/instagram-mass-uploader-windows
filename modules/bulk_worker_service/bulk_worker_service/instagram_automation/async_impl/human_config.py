"""
Human behavior config scaffold. Not enforced yet to avoid behavior changes.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class HumanTimings:
    mouse_move_ms: int = 120
    between_steps_ms: int = 200
    page_scan_ms: int = 500
    random_browse_steps: int = 3

DEFAULT_HUMAN_TIMINGS = HumanTimings()

__all__ = ["HumanTimings", "DEFAULT_HUMAN_TIMINGS"]
