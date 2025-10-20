"""
Enhanced Captcha Detection System for YouTube Pipeline
Provides robust detection of various captcha types with multiple fallback methods
"""

import asyncio
import logging
from typing import Optional, Dict, List, Tuple
from enum import Enum
from dataclasses import dataclass
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class CaptchaType(Enum):
    """Supported captcha types"""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    STANDARD_CAPTCHA = "standard_captcha"
    INVISIBLE_RECAPTCHA = "invisible_recaptcha"
    NONE = "none"


@dataclass
class CaptchaParameters:
    """Parameters extracted from detected captcha"""
    captcha_type: CaptchaType
    site_key: Optional[str] = None
    page_url: str = ""
    iframe_src: Optional[str] = None
    callback_function: Optional[str] = None
    invisible: bool = False
    data_sitekey: Optional[str] = None
    data_callback: Optional[str] = None


class EnhancedCaptchaDetector:
    """Enhanced captcha detection with multiple detection methods"""
    
    def __init__(self):
        self.detection_timeout = 30
        self.quick_check_timeout = 5
        
    async def detect_captcha_type(self, page: Page) -> CaptchaParameters:
        """
        Detect captcha type and extract parameters using multiple methods
        
        Args:
            page: Playwright page instance
            
        Returns:
            CaptchaParameters with detected captcha information
        """
        logger.info("[CAPTCHA_DETECT] Starting enhanced captcha detection...")
        
        # Method 1: JavaScript-based detection (most reliable)
        js_result = await self._detect_via_javascript(page)
        if js_result.captcha_type != CaptchaType.NONE:
            logger.info(f"[CAPTCHA_DETECT] JavaScript detection found: {js_result.captcha_type.value}")
            return js_result
            
        # Method 2: DOM-based detection
        dom_result = await self._detect_via_dom(page)
        if dom_result.captcha_type != CaptchaType.NONE:
            logger.info(f"[CAPTCHA_DETECT] DOM detection found: {dom_result.captcha_type.value}")
            return dom_result
            
        # Method 3: Network monitoring (for invisible captchas)
        network_result = await self._detect_via_network(page)
        if network_result.captcha_type != CaptchaType.NONE:
            logger.info(f"[CAPTCHA_DETECT] Network detection found: {network_result.captcha_type.value}")
            return network_result
            
        logger.info("[CAPTCHA_DETECT] No captcha detected")
        return CaptchaParameters(
            captcha_type=CaptchaType.NONE,
            page_url=page.url
        )
    
    async def wait_for_captcha_appearance(self, page: Page, timeout: int = 30) -> bool:
        """
        Wait for captcha to appear on the page
        
        Args:
            page: Playwright page instance
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if captcha appeared, False if timeout
        """
        logger.info(f"[CAPTCHA_DETECT] Waiting for captcha appearance (timeout: {timeout}s)...")
        
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            result = await self.detect_captcha_type(page)
            if result.captcha_type != CaptchaType.NONE:
                logger.info(f"[CAPTCHA_DETECT] Captcha appeared: {result.captcha_type.value}")
                return True
                
            await asyncio.sleep(1)
            
        logger.info("[CAPTCHA_DETECT] Timeout waiting for captcha")
        return False
    
    async def is_captcha_solved(self, page: Page) -> bool:
        """
        Check if captcha has been solved successfully
        
        Args:
            page: Playwright page instance
            
        Returns:
            True if captcha is solved, False otherwise
        """
        try:
            # Check for reCAPTCHA solved state
            recaptcha_solved = await page.evaluate("""
                () => {
                    // Check for visible checkmark
                    const checkmark = document.querySelector('.recaptcha-checkbox-checkmark');
                    if (checkmark) {
                        const style = window.getComputedStyle(checkmark);
                        return style.display !== 'none' && style.visibility !== 'hidden';
                    }
                    
                    // Check for filled response textarea
                    const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (textarea && textarea.value && textarea.value.length > 0) {
                        return true;
                    }
                    
                    return false;
                }
            """)
            
            if recaptcha_solved:
                logger.info("[CAPTCHA_DETECT] reCAPTCHA appears to be solved")
                return True
                
            # Check for hCaptcha solved state
            hcaptcha_solved = await page.evaluate("""
                () => {
                    const textarea = document.querySelector('textarea[name="h-captcha-response"]');
                    return textarea && textarea.value && textarea.value.length > 0;
                }
            """)
            
            if hcaptcha_solved:
                logger.info("[CAPTCHA_DETECT] hCaptcha appears to be solved")
                return True
                
            return False
            
        except Exception as e:
            logger.warning(f"[CAPTCHA_DETECT] Error checking solved state: {e}")
            return False
    
    async def _detect_via_javascript(self, page: Page) -> CaptchaParameters:
        """Detect captcha using JavaScript configuration objects"""
        try:
            js_detection = await page.evaluate("""
                () => {
                    const result = {
                        type: 'none',
                        siteKey: null,
                        invisible: false,
                        callback: null
                    };
                    
                    // Check for reCAPTCHA configuration
                    if (typeof ___grecaptcha_cfg !== 'undefined' && ___grecaptcha_cfg.clients) {
                        const clients = Object.entries(___grecaptcha_cfg.clients);
                        if (clients.length > 0) {
                            result.type = 'recaptcha_v2';
                            
                            // Extract site key and other parameters
                            for (const [id, client] of clients) {
                                const objects = Object.entries(client).filter(([_, value]) => 
                                    value && typeof value === 'object'
                                );
                                
                                for (const [toplevelKey, toplevel] of objects) {
                                    const found = Object.entries(toplevel).find(([_, value]) => (
                                        value && typeof value === 'object' && 'sitekey' in value
                                    ));
                                    
                                    if (found) {
                                        const [_, sublevel] = found;
                                        result.siteKey = sublevel.sitekey;
                                        result.invisible = sublevel.size === 'invisible';
                                        result.callback = sublevel.callback || null;
                                        
                                        if (result.invisible) {
                                            result.type = 'invisible_recaptcha';
                                        }
                                        break;
                                    }
                                }
                                if (result.siteKey) break;
                            }
                        }
                    }
                    
                    // Check for hCaptcha
                    if (typeof hcaptcha !== 'undefined' || document.querySelector('[data-sitekey*="hcaptcha"]')) {
                        result.type = 'hcaptcha';
                        const hcaptchaElement = document.querySelector('[data-sitekey]');
                        if (hcaptchaElement) {
                            result.siteKey = hcaptchaElement.getAttribute('data-sitekey');
                        }
                    }
                    
                    return result;
                }
            """)
            
            if js_detection['type'] != 'none':
                return CaptchaParameters(
                    captcha_type=CaptchaType(js_detection['type']),
                    site_key=js_detection['siteKey'],
                    page_url=page.url,
                    invisible=js_detection['invisible'],
                    callback_function=js_detection['callback']
                )
                
        except Exception as e:
            logger.warning(f"[CAPTCHA_DETECT] JavaScript detection failed: {e}")
            
        return CaptchaParameters(captcha_type=CaptchaType.NONE, page_url=page.url)
    
    async def _detect_via_dom(self, page: Page) -> CaptchaParameters:
        """Detect captcha using DOM element analysis"""
        try:
            # reCAPTCHA indicators
            recaptcha_indicators = [
                'iframe[src*="recaptcha"]',
                'div[data-sitekey]',
                'div[data-site-key]',
                'textarea[name="g-recaptcha-response"]',
                '.g-recaptcha',
                '#g-recaptcha'
            ]
            
            for indicator in recaptcha_indicators:
                elements = await page.locator(indicator).all()
                if elements:
                    logger.info(f"[CAPTCHA_DETECT] Found reCAPTCHA indicator: {indicator}")
                    
                    # Extract site key
                    site_key = await self._extract_site_key_from_dom(page)
                    
                    return CaptchaParameters(
                        captcha_type=CaptchaType.RECAPTCHA_V2,
                        site_key=site_key,
                        page_url=page.url
                    )
            
            # hCaptcha indicators
            hcaptcha_indicators = [
                'iframe[src*="hcaptcha"]',
                'div[data-sitekey*="hcaptcha"]',
                'textarea[name="h-captcha-response"]',
                '.h-captcha'
            ]
            
            for indicator in hcaptcha_indicators:
                elements = await page.locator(indicator).all()
                if elements:
                    logger.info(f"[CAPTCHA_DETECT] Found hCaptcha indicator: {indicator}")
                    
                    return CaptchaParameters(
                        captcha_type=CaptchaType.HCAPTCHA,
                        page_url=page.url
                    )
            
            # Standard captcha indicators
            standard_indicators = [
                'img[src*="captcha"]',
                'input[name*="captcha"]',
                '#captchaimg',
                '.captcha-image'
            ]
            
            for indicator in standard_indicators:
                elements = await page.locator(indicator).all()
                if elements:
                    logger.info(f"[CAPTCHA_DETECT] Found standard captcha indicator: {indicator}")
                    
                    return CaptchaParameters(
                        captcha_type=CaptchaType.STANDARD_CAPTCHA,
                        page_url=page.url
                    )
                    
        except Exception as e:
            logger.warning(f"[CAPTCHA_DETECT] DOM detection failed: {e}")
            
        return CaptchaParameters(captcha_type=CaptchaType.NONE, page_url=page.url)
    
    async def _detect_via_network(self, page: Page) -> CaptchaParameters:
        """Detect captcha by monitoring network requests"""
        try:
            # This would require setting up request/response listeners
            # For now, return none - can be implemented later if needed
            pass
            
        except Exception as e:
            logger.warning(f"[CAPTCHA_DETECT] Network detection failed: {e}")
            
        return CaptchaParameters(captcha_type=CaptchaType.NONE, page_url=page.url)
    
    async def _extract_site_key_from_dom(self, page: Page) -> Optional[str]:
        """Extract site key from DOM elements"""
        try:
            site_key = await page.evaluate("""
                () => {
                    // Try data-sitekey attribute
                    let element = document.querySelector('[data-sitekey]');
                    if (element) {
                        return element.getAttribute('data-sitekey');
                    }
                    
                    // Try data-site-key attribute
                    element = document.querySelector('[data-site-key]');
                    if (element) {
                        return element.getAttribute('data-site-key');
                    }
                    
                    // Try iframe src parameter
                    const iframe = document.querySelector('iframe[src*="recaptcha"]');
                    if (iframe) {
                        const src = iframe.src;
                        const match = src.match(/[?&]k=([^&]+)/);
                        if (match) {
                            return match[1];
                        }
                    }
                    
                    return null;
                }
            """)
            
            return site_key
            
        except Exception as e:
            logger.warning(f"[CAPTCHA_DETECT] Site key extraction failed: {e}")
            return None


# Convenience function for backward compatibility
async def detect_captcha(page: Page) -> Tuple[CaptchaType, Optional[str]]:
    """
    Convenience function for simple captcha detection
    
    Returns:
        Tuple of (CaptchaType, site_key)
    """
    detector = EnhancedCaptchaDetector()
    params = await detector.detect_captcha_type(page)
    return params.captcha_type, params.site_key