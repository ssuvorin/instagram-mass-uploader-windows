"""
Windows-specific fixes for the Instagram uploader
Addresses common issues that occur on Windows platform
"""

import platform
import asyncio
import time
from typing import Optional, Any


def is_windows() -> bool:
    """Check if running on Windows"""
    return platform.system().lower() == 'windows'


class WindowsAsyncFixes:
    """Windows-specific fixes for async operations"""
    
    @staticmethod
    async def safe_browser_close(browser_obj: Any, delay: float = 1.0) -> bool:
        """Safely close browser on Windows with proper delays"""
        if not is_windows():
            return True
            
        try:
            if hasattr(browser_obj, 'close'):
                await asyncio.sleep(delay)
                await browser_obj.close()
            return True
        except Exception as e:
            print(f"[WINDOWS_FIX] Browser close error: {str(e)}")
            return False
    
    @staticmethod
    async def safe_playwright_stop(playwright_obj: Any, delay: float = 0.5) -> bool:
        """Safely stop Playwright on Windows with proper delays"""
        if not is_windows():
            return True
            
        try:
            if hasattr(playwright_obj, 'stop'):
                await asyncio.sleep(delay)
                await playwright_obj.stop()
            return True
        except Exception as e:
            print(f"[WINDOWS_FIX] Playwright stop error: {str(e)}")
            return False
    
    @staticmethod
    async def safe_page_close(page_obj: Any, delay: float = 0.5) -> bool:
        """Safely close page on Windows with proper delays"""
        if not is_windows():
            return True
            
        try:
            if hasattr(page_obj, 'close'):
                await asyncio.sleep(delay)
                await page_obj.close()
            return True
        except Exception as e:
            print(f"[WINDOWS_FIX] Page close error: {str(e)}")
            return False


class WindowsSyncFixes:
    """Windows-specific fixes for sync operations"""
    
    @staticmethod
    def safe_process_cleanup(delay: float = 0.5) -> None:
        """Add delay for process cleanup on Windows"""
        if is_windows():
            time.sleep(delay)
    
    @staticmethod
    def safe_db_close(delay: float = 0.1) -> None:
        """Add delay for database connection close on Windows"""
        if is_windows():
            time.sleep(delay)


def apply_windows_async_context_fix():
    """
    Apply fix for 'You cannot call this from an async context' error on Windows
    This error often occurs when Django ORM is called from async functions
    """
    if not is_windows():
        return
        
    try:
        import nest_asyncio
        nest_asyncio.apply()
        print("[WINDOWS_FIX] Applied nest_asyncio fix for Windows async context")
    except ImportError:
        print("[WINDOWS_FIX] nest_asyncio not available, async context fix not applied")


def get_windows_safe_timeouts():
    """Get Windows-safe timeouts for various operations"""
    if not is_windows():
        return {
            'browser_close': 5.0,
            'page_close': 3.0,
            'playwright_stop': 3.0,
            'process_cleanup': 1.0,
            'db_close': 0.1
        }
    
    # Windows needs longer timeouts
    return {
        'browser_close': 10.0,
        'page_close': 5.0,
        'playwright_stop': 5.0,
        'process_cleanup': 2.0,
        'db_close': 0.5
    }


def log_windows_environment():
    """Log Windows environment information for debugging"""
    if not is_windows():
        return
        
    try:
        import sys
        print(f"[WINDOWS_INFO] Python version: {sys.version}")
        print(f"[WINDOWS_INFO] Platform: {platform.platform()}")
        print(f"[WINDOWS_INFO] Architecture: {platform.architecture()}")
        
        # Check for common Windows-specific issues
        try:
            import asyncio
            policy = asyncio.get_event_loop_policy()
            print(f"[WINDOWS_INFO] Event loop policy: {type(policy).__name__}")
        except Exception as e:
            print(f"[WINDOWS_INFO] Could not get event loop policy: {str(e)}")
            
    except Exception as e:
        print(f"[WINDOWS_INFO] Error getting Windows environment info: {str(e)}") 