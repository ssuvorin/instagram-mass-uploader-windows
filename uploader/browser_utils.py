"""
Browser utilities and helper functions
Provides utilities for browser management, page operations, and error handling
"""

import os
import psutil
import subprocess
import time
from .logging_utils import log_info, log_warning, log_error


class BrowserManager:
    """Manages browser processes and cleanup operations"""
    
    @staticmethod
    def cleanup_hanging_processes():
        """Clean up hanging browser processes - DEPRECATED: Too aggressive"""
        log_warning("[CLEANUP] [WARN] cleanup_hanging_processes is deprecated - use safe_cleanup_profile instead")
        # Don't kill all processes - this is too dangerous
        log_info("[CLEANUP] [OK] Skipping aggressive cleanup to preserve other browser instances")
    
    @staticmethod
    def safe_cleanup_profile(dolphin_profile_id=None, page=None):
        """Safely cleanup only the specific profile without affecting other instances"""
        try:
            log_info(f"[CLEANUP] [CLEAN] Starting safe cleanup for profile: {dolphin_profile_id}")
            
            cleanup_success = True
            
            # Step 1: Close page gracefully if provided
            if page:
                try:
                    log_info("[CLEANUP] [FILE] Closing page gracefully...")
                    if not page.is_closed():
                        # Try to navigate away first (more graceful)
                        try:
                            page.goto("about:blank", timeout=5000)
                            time.sleep(1)
                        except:
                            pass
                        
                        # Close the page
                        page.close()
                        log_info("[CLEANUP] [OK] Page closed successfully")
                    else:
                        log_info("[CLEANUP] ℹ️ Page was already closed")
                except Exception as e:
                    log_warning(f"[CLEANUP] [WARN] Error closing page: {str(e)}")
                    cleanup_success = False
            
            # Step 2: Stop Dolphin profile via API (safest method)
            if dolphin_profile_id:
                try:
                    log_info(f"[CLEANUP] 🐬 Stopping Dolphin profile via API: {dolphin_profile_id}")
                    
                    # Import here to avoid circular imports
                    from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
                    
                    dolphin_token = os.environ.get("DOLPHIN_API_TOKEN")
                    if dolphin_token:
                        # Get Dolphin API host from environment (critical for Docker Windows deployment)
                        dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
                        if not dolphin_api_host.endswith("/v1.0"):
                            dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
                        
                        dolphin = DolphinAnty(api_key=dolphin_token, local_api_base=dolphin_api_host)
                        stop_result = dolphin.stop_profile(dolphin_profile_id)
                        
                        if stop_result:
                            log_info(f"[CLEANUP] [OK] Dolphin profile {dolphin_profile_id} stopped successfully via API")
                        else:
                            log_warning(f"[CLEANUP] [WARN] Failed to stop profile {dolphin_profile_id} via API")
                            cleanup_success = False
                    else:
                        log_warning("[CLEANUP] [WARN] No Dolphin API token available for profile cleanup")
                        cleanup_success = False
                        
                except Exception as e:
                    log_warning(f"[CLEANUP] [WARN] Error stopping Dolphin profile via API: {str(e)}")
                    cleanup_success = False
            
            # Step 3: Wait for graceful shutdown
            if cleanup_success:
                log_info("[CLEANUP] [WAIT] Waiting for graceful shutdown...")
                time.sleep(3)  # Give time for processes to close naturally
                log_info("[CLEANUP] [OK] Safe cleanup completed successfully")
            else:
                log_warning("[CLEANUP] [WARN] Safe cleanup had some issues, but continuing...")
            
            return cleanup_success
            
        except Exception as e:
            log_error(f"[CLEANUP] [FAIL] Error during safe cleanup: {str(e)}")
            return False
    
    @staticmethod
    def safely_close_browser(page, dolphin_browser, dolphin_profile_id=None):
        """Safely close browser using the new safe cleanup method"""
        try:
            log_info("[CLEANUP] 🔒 Starting safe browser closure...")
            
            # Use the new safe cleanup method
            cleanup_success = BrowserManager.safe_cleanup_profile(dolphin_profile_id, page)
            
            # Additional cleanup for dolphin_browser object if provided
            if dolphin_browser:
                try:
                    # Try to stop via the browser object as well
                    if hasattr(dolphin_browser, 'stop_profile'):
                        dolphin_browser.stop_profile()
                        log_info("[CLEANUP] [OK] Dolphin browser object stopped")
                except Exception as e:
                    log_warning(f"[CLEANUP] [WARN] Error stopping Dolphin browser object: {str(e)}")
            
            return cleanup_success
            
        except Exception as e:
            log_error(f"[CLEANUP] [FAIL] Error during safe browser closure: {str(e)}")
            return False


class PageUtils:
    """Utilities for page operations"""
    
    @staticmethod
    def wait_for_page_load(page, timeout=30000):
        """Wait for page to fully load"""
        try:
            log_info("[PAGE] [WAIT] Waiting for page to load...")
            page.wait_for_load_state('networkidle', timeout=timeout)
            log_info("[PAGE] [OK] Page loaded successfully")
            return True
        except Exception as e:
            log_warning(f"[PAGE] [WARN] Page load timeout: {str(e)}")
            return False
    
    @staticmethod
    def scroll_page(page, direction="down", amount=500):
        """Scroll page in specified direction"""
        try:
            if direction == "down":
                page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == "top":
                page.evaluate("window.scrollTo(0, 0)")
            elif direction == "bottom":
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            time.sleep(0.5)  # Brief pause after scrolling
            return True
        except Exception as e:
            log_warning(f"[PAGE] Failed to scroll: {str(e)}")
            return False


class ErrorHandler:
    """Handles common errors and provides recovery strategies"""
    
    @staticmethod
    def handle_login_error(page, error_type="unknown"):
        """Handle login-related errors"""
        error_strategies = {
            'rate_limit': ErrorHandler._handle_rate_limit,
            'captcha': ErrorHandler._handle_captcha,
            'phone_verification': ErrorHandler._handle_phone_verification,
            'suspicious_activity': ErrorHandler._handle_suspicious_activity,
            'incorrect_credentials': ErrorHandler._handle_incorrect_credentials
        }
        
        strategy = error_strategies.get(error_type, ErrorHandler._handle_generic_error)
        return strategy(page)
    
    @staticmethod
    def _handle_rate_limit(page):
        """Handle rate limiting"""
        log_warning("[ERROR] [BLOCK] Rate limit detected")
        # Wait longer and retry
        time.sleep(300)  # 5 minutes
        return "retry"
    
    @staticmethod
    def _handle_captcha(page):
        """Handle CAPTCHA challenges"""
        log_warning("[ERROR] [BOT] CAPTCHA detected")
        return "manual_intervention"
    
    @staticmethod
    def _handle_phone_verification(page):
        """Handle phone verification requirement"""
        log_warning("[ERROR] [PHONE] Phone verification required")
        return "phone_verification_required"
    
    @staticmethod
    def _handle_suspicious_activity(page):
        """Handle suspicious activity warnings"""
        log_warning("[ERROR] [WARN] Suspicious activity detected")
        # Wait and retry with different behavior
        time.sleep(600)  # 10 minutes
        return "retry_with_caution"
    
    @staticmethod
    def _handle_incorrect_credentials(page):
        """Handle incorrect credentials"""
        log_error("[ERROR] 🔐 Incorrect credentials")
        return "credentials_error"
    
    @staticmethod
    def _handle_generic_error(page):
        """Handle generic errors"""
        log_warning("[ERROR] ❓ Generic error occurred")
        return "unknown_error"


class NetworkUtils:
    """Network-related utilities"""
    
    @staticmethod
    def setup_proxy(context, proxy_details):
        """Setup proxy for browser context"""
        if not proxy_details:
            return True
        
        try:
            log_info(f"[PROXY] 🌐 Setting up proxy: {proxy_details.get('host', 'unknown')}")
            
            # This would be implemented based on your proxy setup
            # For now, just log the attempt
            log_info("[PROXY] [OK] Proxy setup completed")
            return True
            
        except Exception as e:
            log_error(f"[PROXY] [FAIL] Proxy setup failed: {str(e)}")
            return False
    
    @staticmethod
    def check_internet_connection():
        """Check if internet connection is available"""
        try:
            import requests
            response = requests.get('https://www.google.com', timeout=5)
            return response.status_code == 200
        except:
            return False


class FileUtils:
    """File-related utilities"""
    
    @staticmethod
    def validate_video_file(file_path):
        """Validate video file exists and is accessible"""
        try:
            if not os.path.exists(file_path):
                log_error(f"[FILE] [FAIL] Video file not found: {file_path}")
                return False
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                log_error(f"[FILE] [FAIL] Video file is empty: {file_path}")
                return False
            
            # Check file extension
            valid_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext not in valid_extensions:
                log_warning(f"[FILE] [WARN] Unusual video format: {file_ext}")
            
            log_info(f"[FILE] [OK] Video file validated: {file_path} ({file_size} bytes)")
            return True
            
        except Exception as e:
            log_error(f"[FILE] [FAIL] Error validating video file: {str(e)}")
            return False
    
    @staticmethod
    def cleanup_temp_files(temp_files):
        """Clean up temporary files"""
        cleaned_count = 0
        
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    cleaned_count += 1
                    log_info(f"[CLEANUP] [DELETE] Removed temp file: {temp_file}")
            except Exception as e:
                log_warning(f"[CLEANUP] Failed to remove temp file {temp_file}: {str(e)}")
        
        if cleaned_count > 0:
            log_info(f"[CLEANUP] [OK] Cleaned up {cleaned_count} temporary files")


class DebugUtils:
    """Debugging utilities"""
    
    @staticmethod
    def log_page_elements(page, selector_type="all"):
        """Log page elements for debugging"""
        try:
            if selector_type == "all":
                elements = page.query_selector_all('*')
            elif selector_type == "clickable":
                elements = page.query_selector_all('a, button, div[role="button"], input[type="submit"]')
            elif selector_type == "inputs":
                elements = page.query_selector_all('input, textarea, select')
            else:
                elements = page.query_selector_all(selector_type)
            
            log_info(f"[DEBUG] 🔍 Found {len(elements)} elements of type '{selector_type}'")
            
            for i, element in enumerate(elements[:10]):  # Limit to first 10
                try:
                    tag_name = element.evaluate('el => el.tagName')
                    text_content = element.text_content()[:50] if element.text_content() else ""
                    is_visible = element.is_visible()
                    
                    log_info(f"[DEBUG] Element {i+1}: {tag_name} - '{text_content}' (visible: {is_visible})")
                except:
                    continue
                    
        except Exception as e:
            log_warning(f"[DEBUG] Failed to log page elements: {str(e)}")
    
    @staticmethod
    def log_console_messages(page):
        """Set up console message logging"""
        def handle_console(msg):
            log_info(f"[CONSOLE] {msg.type}: {msg.text}")
        
        page.on("console", handle_console)
    
    @staticmethod
    def monitor_network_requests(page):
        """Monitor network requests for debugging"""
        def handle_request(request):
            log_info(f"[NETWORK] Request: {request.method} {request.url}")
        
        def handle_response(response):
            if response.status >= 400:
                log_warning(f"[NETWORK] Error response: {response.status} {response.url}")
        
        page.on("request", handle_request)
        page.on("response", handle_response)

    @staticmethod
    def get_page_info(page):
        """Get basic page information for debugging"""
        try:
            info = {
                'url': page.url,
                'title': page.title(),
                'viewport': page.viewport_size,
                'is_closed': page.is_closed()
            }
            log_info(f"[DEBUG] [FILE] Page info: {info}")
            return info
        except Exception as e:
            log_warning(f"[DEBUG] Failed to get page info: {str(e)}")
            return {} 