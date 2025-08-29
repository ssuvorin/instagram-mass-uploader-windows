"""
Instagram Automation Package for Worker Service

This package contains all the Instagram automation modules copied from the main project
to enable the worker service to execute Instagram tasks independently.
"""

from .instagram_automation import InstagramAutomationBase, InstagramNavigator, InstagramUploader, InstagramLoginHandler
from .login_optimized import perform_instagram_login_optimized
from .human_behavior import AdvancedHumanBehavior, init_human_behavior, get_human_behavior

__all__ = [
    'InstagramAutomationBase',
    'InstagramNavigator', 
    'InstagramUploader',
    'InstagramLoginHandler',
    'perform_instagram_login_optimized',
    'AdvancedHumanBehavior',
    'init_human_behavior',
    'get_human_behavior',
]