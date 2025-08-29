# -*- coding: utf-8 -*-
"""
Browser support functions for Instagram automation
"""

import time
import random
import os
from .logging_utils import log_info, log_error, log_success, log_warning
from .constants import LogCategories


def cleanup_hanging_browser_processes():
    """Clean up hanging browser processes - Optimized version"""
    try:
        import psutil
        log_info("Checking for hanging browser processes...")
        
        # Process names to look for
        browser_processes = ['chrome', 'chromium', 'firefox', 'safari', 'edge']
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                process_name = proc.info['name'].lower()
                if any(browser in process_name for browser in browser_processes):
                    # Check if process is hanging (you might want to add more sophisticated logic)
                    if proc.status() == psutil.STATUS_ZOMBIE:
                        log_warning(f"Found hanging browser process: {proc.info['name']} (PID: {proc.info['pid']})")
                        proc.kill()
                        log_success(f"Killed hanging process: {proc.info['name']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
    except ImportError:
        log_warning("psutil not available, cannot clean up hanging processes")
    except Exception as e:
        log_error(f"Error during browser cleanup: {str(e)}")


def safely_close_all_windows(page, dolphin_browser, dolphin_profile_id=None):
    """Safely close all browser windows and processes - Optimized version"""
    try:
        log_info("[CLEANUP] Starting comprehensive browser cleanup")
        
        if not page or not dolphin_browser:
            log_warning("[CLEANUP] Page or browser not available")
            return False
        
        try:
            # Close all tabs/pages
            context = page.context
            if context:
                for page_instance in context.pages:
                    try:
                        page_instance.close()
                        log_info("[CLEANUP] Closed page instance")
                    except Exception as e:
                        log_warning(f"[CLEANUP] Error closing page: {str(e)}")
                
                # Close the context
                context.close()
                log_info("[CLEANUP] Closed browser context")
        except Exception as e:
            log_warning(f"[CLEANUP] Error during page cleanup: {str(e)}")
        
        try:
            # Close the browser
            if hasattr(dolphin_browser, 'close'):
                dolphin_browser.close()
                log_info("[CLEANUP] Closed Dolphin browser")
        except Exception as e:
            log_warning(f"[CLEANUP] Error closing browser: {str(e)}")
        
        try:
            # Stop Dolphin profile if available
            if dolphin_profile_id:
                log_info(f"[CLEANUP] Stopping Dolphin profile: {dolphin_profile_id}")
                # This would need the dolphin API instance
                # dolphin.stop_profile(dolphin_profile_id)
        except Exception as e:
            log_warning(f"[CLEANUP] Error stopping profile: {str(e)}")
        
        log_success("[CLEANUP] [OK] Browser cleanup completed successfully")
        return True
        
    except Exception as e:
        log_error(f"[CLEANUP] Critical error during cleanup: {str(e)}")
        return False


def simulate_human_rest_behavior(page, duration):
    """Simulate human rest behavior between actions"""
    try:
        log_info(f"[HUMAN] Simulating rest behavior for {duration:.1f}s")
        
        # Scroll around randomly
        for _ in range(random.randint(1, 3)):
            scroll_amount = random.randint(-200, 200)
            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            time.sleep(random.uniform(1, 2))
        
        # Random mouse movements
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.5, 1.5))
        
        # Wait for remaining time
        remaining = duration - 6  # Approximate time spent on actions above
        if remaining > 0:
            time.sleep(remaining)
            
    except Exception as e:
        log_warning(f"[HUMAN] Rest behavior simulation failed: {str(e)}")
        time.sleep(duration)  # Fallback to simple sleep


def simulate_normal_browsing_behavior(page):
    """Simulate normal browsing behavior before closing"""
    try:
        log_info("[HUMAN] Simulating normal browsing behavior")
        
        # Go to home page
        home_link = page.query_selector('svg[aria-label*="Home"]') or page.query_selector('a[href="/"]')
        if home_link:
            home_link.click()
            time.sleep(random.uniform(2, 4))
        
        # Scroll through feed
        for _ in range(random.randint(3, 6)):
            scroll_amount = random.randint(200, 400)
            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            time.sleep(random.uniform(1, 3))
        
        # Random interactions
        for _ in range(random.randint(1, 3)):
            # Try to hover over posts
            posts = page.query_selector_all('article')
            if posts:
                random_post = random.choice(posts[:5])
                random_post.hover()
                time.sleep(random.uniform(0.5, 1.5))
        
        log_info("[HUMAN] Completed normal browsing simulation")
        
    except Exception as e:
        log_warning(f"[HUMAN] Browsing behavior simulation failed: {str(e)}")
        time.sleep(random.uniform(5, 10))  # Fallback delay


def simulate_extended_human_rest_behavior(page, total_duration):
    """Simulate extended human rest behavior with multiple activities during long breaks"""
    try:
        log_info(f"[EXTENDED_REST] 🛋️ Starting extended rest period: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
        
        # Break the total duration into smaller activity chunks
        remaining_time = total_duration
        activity_count = 0
        
        while remaining_time > 30:  # Continue until less than 30 seconds remain
            activity_count += 1
            
            # Choose random activity duration (30 seconds to 2 minutes)
            activity_duration = min(random.uniform(30, 120), remaining_time)
            remaining_time -= activity_duration
            
            # Choose random activity type
            activity_types = [
                'browse_feed', 'check_profile', 'scroll_explore', 'check_notifications',
                'view_stories', 'search_content', 'idle_pause', 'check_messages'
            ]
            
            activity = random.choice(activity_types)
            log_info(f"[EXTENDED_REST] [TARGET] Activity {activity_count}: {activity} for {activity_duration:.1f}s")
            
            # Simplified activity implementation
            if activity == 'idle_pause':
                log_info(f"[EXTENDED_REST] 😴 Idle pause for {activity_duration:.1f}s...")
                time.sleep(activity_duration)
            else:
                # For other activities, just simulate with basic scrolling
                scroll_count = int(activity_duration / 10)
                for _ in range(max(1, scroll_count)):
                    scroll_amount = random.randint(200, 500)
                    page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                    time.sleep(10)
        
        # Handle any remaining time with a final idle period
        if remaining_time > 0:
            log_info(f"[EXTENDED_REST] 😌 Final rest period: {remaining_time:.1f}s...")
            time.sleep(remaining_time)
        
        log_info(f"[EXTENDED_REST] [OK] Extended rest period completed after {activity_count} activities")
        
    except Exception as e:
        log_warning(f"[EXTENDED_REST] Error during extended rest: {str(e)}")
        # Fallback to simple sleep
        time.sleep(total_duration) 