#!/usr/bin/env python
import os
import logging
import time
import random
from typing import Dict, Optional, Any, Tuple

# Suppress verbose Playwright logging before importing Playwright
os.environ['PLAYWRIGHT_QUIET'] = '1'
os.environ['PLAYWRIGHT_DISABLE_COLORS'] = '1'
os.environ['DEBUG'] = ''

# Configure logging to suppress verbose Playwright logs
logging.getLogger('playwright').setLevel(logging.CRITICAL)
logging.getLogger('playwright._impl').setLevel(logging.CRITICAL)
logging.getLogger('playwright.sync_api').setLevel(logging.CRITICAL)

from playwright.sync_api import sync_playwright, Browser, Page

from bot.src.instagram_uploader.dolphin_anty import DolphinAnty

logger = logging.getLogger('bot.instagram_uploader.browser_dolphin')

class DolphinBrowser:
    """
    Class to handle browser automation using Dolphin Anty with Playwright
    """
    def __init__(self, dolphin_api_token: str = None):
        # Initialize Dolphin Anty API client
        if dolphin_api_token:
            print(f"[OK] Initializing Dolphin Anty with API token")
            
            # Get Dolphin API host from environment (critical for Docker Windows deployment)
            dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
            if not dolphin_api_host.endswith("/v1.0"):
                dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
            
            print(f"🐬 Using Dolphin API host: {dolphin_api_host}")
            self.dolphin = DolphinAnty(api_key=dolphin_api_token, local_api_base=dolphin_api_host)
        else:
            print(f"[FAIL] No Dolphin API token provided - cannot initialize DolphinAnty")
            raise ValueError("Dolphin API token is required")
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.dolphin_profile_id = None
        self.automation_data = None
        
    def connect_to_profile(self, profile_id: str, headless: bool = False) -> Optional[Page]:
        """
        Connect to an existing Dolphin Anty profile using Playwright
        Returns the Page object if successful
        """
        try:
            self.dolphin_profile_id = profile_id
            
            # Start the Dolphin profile
            logger.info(f"[RETRY] [Step 1/5] Starting Dolphin Anty profile: {profile_id} (headless: {headless})")
            success, automation_data = self.dolphin.start_profile(profile_id, headless=headless)
            
            if not success or not automation_data:
                logger.error(f"[FAIL] Failed to start Dolphin profile: {profile_id}")
                return None
                
            self.automation_data = automation_data
            port = automation_data.get("port")
            ws_endpoint = automation_data.get("wsEndpoint")
            
            # Validate automation data
            if not port or not ws_endpoint:
                logger.error(f"[FAIL] Invalid automation data from Dolphin API:")
                logger.error(f"   Port: {port}")
                logger.error(f"   WS Endpoint: {ws_endpoint}")
                logger.error(f"   Full data: {automation_data}")
                return None
            
            # Construct WebSocket URL
            # В Docker контейнере используем host.docker.internal, иначе localhost
            docker_container = os.environ.get("DOCKER_CONTAINER", "0") == "1"
            host = "host.docker.internal" if docker_container else "127.0.0.1"
            ws_url = f"ws://{host}:{port}{ws_endpoint}"
            logger.info(f"🔗 WebSocket URL: {ws_url}")
            
            # Initialize Playwright
            logger.info(f"[RETRY] [Step 2/5] Initializing Playwright...")
            self.playwright = sync_playwright().start()
            
            # Connect to browser
            logger.info(f"[RETRY] [Step 3/5] Connecting to Dolphin browser via WebSocket...")
            try:
                self.browser = self.playwright.chromium.connect_over_cdp(ws_url)
                logger.info(f"[OK] Successfully connected to browser using CDP")
            except Exception as connect_error:
                logger.error(f"[FAIL] Failed to connect via CDP: {connect_error}")
                logger.error(f"   Make sure Dolphin profile {profile_id} is running")
                logger.error(f"   WebSocket URL: {ws_url}")
                return None
            
            # Use the default context (using contexts property like in working code)
            logger.info(f"[RETRY] [Step 4/5] Getting browser context...")
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                logger.info(f"[OK] Using existing browser context")
            else:
                # If no contexts exist, create a new one
                self.context = self.browser.new_context()
                logger.info(f"[OK] Created new browser context")
            
            # Create a new page
            logger.info(f"[RETRY] [Step 5/5] Creating new browser page...")
            self.page = self.context.new_page()
            logger.info("[OK] Successfully connected to Dolphin browser")
            
            # Add event handlers for dialog windows
            logger.info("[TOOL] Setting up browser event handlers...")
            self._add_event_handlers()
            
            return self.page
            
        except Exception as e:
            logger.error(f"[FAIL] Error connecting to Dolphin profile: {str(e)}")
            self.close()
            return None
            
    def create_profile_for_account(self, 
                                 account_data: Dict[str, Any], 
                                 proxy_data: Optional[Dict[str, Any]] = None,
                                 headless: bool = False) -> Optional[Page]:
        """
        Create a new Dolphin profile for an Instagram account and connect to it
        Returns the Page object if successful
        """
        try:
            username = account_data.get('username', 'unknown')
            logger.info(f"[TOOL] [Step 1/2] Creating Dolphin Anty profile for Instagram account: {username}")
            
            if proxy_data:
                logger.info(f"🌐 Using proxy: {proxy_data.get('host')}:{proxy_data.get('port')}")
            else:
                logger.info(f"[WARN] No proxy specified for account {username}")
            
            # Create profile
            profile_id, response = self.dolphin.create_profile_for_account(account_data, proxy_data)
            
            if not profile_id:
                logger.error(f"[FAIL] Failed to create Dolphin profile for account: {username}")
                return None
                
            # Store profile ID and response for snapshot
            logger.info(f"[OK] Successfully created Dolphin profile ID: {profile_id}")
            self.dolphin_profile_id = profile_id
            self.dolphin_profile_response = response  # Store for potential snapshot saving
                
            # Connect to the profile
            logger.info(f"[RETRY] [Step 2/2] Connecting to newly created Dolphin profile {profile_id}...")
            return self.connect_to_profile(profile_id, headless=headless)
            
        except Exception as e:
            logger.error(f"[FAIL] Error creating and connecting to Dolphin profile: {str(e)}")
            return None
            
    def _add_event_handlers(self):
        """Add event handlers to the page"""
        if not self.page:
            logger.warning("[WARN] Cannot add event handlers - no page available")
            return
            
        # Handle dialog events
        logger.info("[TOOL] Adding dialog event handler to browser page")
        self.page.on("dialog", lambda dialog: self._handle_dialog(dialog))
        
    def _handle_dialog(self, dialog):
        """Handle JavaScript dialogs (alert, confirm, prompt)"""
        dialog_type = dialog.type
        dialog_message = dialog.message
        
        logger.info(f"[BELL] Dialog appeared: {dialog_type} - {dialog_message}")
        
        # Default behavior: accept alerts and confirms, dismiss prompts
        if dialog_type == "alert":
            logger.info("[BELL] Automatically accepting alert dialog")
            dialog.accept()
        elif dialog_type == "confirm":
            # Randomly accept or dismiss confirms to mimic human behavior
            if random.random() > 0.3:  # 70% chance to accept
                logger.info("[BELL] Automatically accepting confirm dialog (70% chance)")
                dialog.accept()
            else:
                logger.info("[BELL] Automatically dismissing confirm dialog (30% chance)")
                dialog.dismiss()
        elif dialog_type == "prompt":
            # Dismiss prompts by default
            logger.info("[BELL] Automatically dismissing prompt dialog")
            dialog.dismiss()
        elif dialog_type == "beforeunload":
            # For page unload confirmations, usually accept
            logger.info("[BELL] Automatically accepting beforeunload dialog")
            dialog.accept()
            
    def close(self):
        """Close the browser and stop the Dolphin profile"""
        try:
            # Close Playwright resources
            if self.browser:
                logger.info("[RETRY] [Step 1/3] Closing Playwright browser...")
                self.browser.close()
                self.browser = None
                
            if self.playwright:
                logger.info("[RETRY] [Step 2/3] Stopping Playwright...")
                self.playwright.stop()
                self.playwright = None
                
            # Stop Dolphin profile
            if self.dolphin_profile_id:
                logger.info(f"[RETRY] [Step 3/3] Stopping Dolphin profile: {self.dolphin_profile_id}")
                self.dolphin.stop_profile(self.dolphin_profile_id)
                self.dolphin_profile_id = None
                
            logger.info("[OK] Browser and profile successfully closed")
            
        except Exception as e:
            logger.error(f"[FAIL] Error closing browser and profile: {str(e)}")

# Utility functions for backward compatibility

def get_browser(headless=False, proxy=None, api_token=None, profile_id=None, account_data=None):
    """
    Get a browser instance using Dolphin Anty
    
    Args:
        headless: Whether to run in headless mode
        proxy: Proxy configuration (for creating new profiles only)
        api_token: Dolphin Anty API token
        profile_id: Existing Dolphin profile ID to use
        account_data: Account data for creating a new profile
    
    Returns:
        DolphinBrowser instance
    """
    logger.info("[RETRY] Initializing Dolphin Browser...")
    
    if proxy:
        logger.info(f"🌐 Using proxy configuration: {proxy.get('host')}:{proxy.get('port')}")
    
    if headless:
        logger.info("💻 Browser will run in headless mode")
    else:
        logger.info("💻 Browser will run in visible mode")
    
    browser = DolphinBrowser(dolphin_api_token=api_token)
    
    try:
        if profile_id:
            # Connect to existing profile
            logger.info(f"[RETRY] Connecting to existing Dolphin profile: {profile_id}")
            browser.connect_to_profile(profile_id, headless=headless)
        elif account_data:
            # Create new profile
            username = account_data.get('username', 'unknown')
            logger.info(f"[RETRY] Creating new Dolphin profile for account: {username}")
            browser.create_profile_for_account(account_data, proxy_data=proxy, headless=headless)
        else:
            logger.error("[FAIL] Either profile_id or account_data must be provided")
            return None
            
        return browser
    except Exception as e:
        logger.error(f"[FAIL] Error getting browser: {str(e)}")
        browser.close()
        return None

def get_page(browser):
    """Get the page from a browser instance"""
    if not browser or not isinstance(browser, DolphinBrowser):
        logger.error("[FAIL] Invalid browser instance")
        return None
        
    return browser.page

def close_browser(browser):
    """Close a browser instance"""
    if browser and isinstance(browser, DolphinBrowser):
        browser.close() 