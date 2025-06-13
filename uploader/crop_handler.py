"""
Crop and Aspect Ratio Handler for Instagram Upload
Handles all crop-related operations during video upload
"""

import time
import random
from .selectors_config import InstagramSelectors, SelectorUtils
from .logging_utils import log_info, log_error, log_warning


class CropHandler:
    """Handles crop and aspect ratio operations for Instagram uploads"""
    
    def __init__(self, page, human_behavior):
        self.page = page
        self.human_behavior = human_behavior
        self.selectors = InstagramSelectors()
    
    def handle_crop_settings(self):
        """Handle crop settings and aspect ratio selection with human behavior"""
        log_info("🖼️ Handling crop settings and aspect ratio selection with human behavior...")
        
        # First, look for the crop/size selection button
        crop_button_found = self._find_and_click_crop_button()
        
        if crop_button_found:
            # Now look for "Оригинал" (Original) aspect ratio option
            aspect_ratio_found = self._select_original_aspect_ratio()
            
            if not aspect_ratio_found:
                log_warning("⚠️ 'Оригинал' aspect ratio option not found, trying fallback options...")
                self._try_fallback_aspect_ratios()
        else:
            log_warning("⚠️ Crop/size selection button not found, trying fallback crop logic")
            self._fallback_crop_logic()
        
        return True
    
    def _find_and_click_crop_button(self):
        """Find and click the crop/size selection button"""
        crop_button_found = False
        
        for selector in self.selectors.CROP_SIZE_BUTTON:
            try:
                crop_button = self.page.query_selector(selector)
                if crop_button and crop_button.is_visible():
                    log_info(f"🎯 Found crop/size button with selector: {selector}")
                    
                    # Human-like interaction with crop button
                    self.human_behavior.advanced_element_interaction(crop_button, 'click')
                    crop_button_found = True
                    
                    # Wait for crop menu to appear
                    crop_menu_wait = self.human_behavior.get_human_delay(2.0, 0.5)
                    log_info(f"⏳ Waiting {crop_menu_wait:.1f}s for crop menu to appear...")
                    time.sleep(crop_menu_wait)
                    break
                    
            except Exception as e:
                log_warning(f"Error with crop selector {selector}: {str(e)}")
                continue
        
        return crop_button_found
    
    def _select_original_aspect_ratio(self):
        """Select the 'Оригинал' (Original) aspect ratio option"""
        log_info("📐 Looking for 'Оригинал' (Original) aspect ratio option...")
        
        aspect_ratio_found = False
        
        for selector in self.selectors.ORIGINAL_ASPECT_RATIO:
            try:
                if selector.startswith('//'):
                    aspect_ratio_button = self.page.query_selector(f"xpath={selector}")
                else:
                    aspect_ratio_button = self.page.query_selector(selector)
                
                if aspect_ratio_button and aspect_ratio_button.is_visible():
                    log_info(f"📐 Found 'Оригинал' aspect ratio option with selector: {selector}")
                    
                    # Human-like interaction with aspect ratio selection
                    self.human_behavior.advanced_element_interaction(aspect_ratio_button, 'click')
                    aspect_ratio_found = True
                    
                    # Wait for aspect ratio to be applied
                    aspect_ratio_wait = self.human_behavior.get_human_delay(2.0, 0.5)
                    log_info(f"⏳ Waiting {aspect_ratio_wait:.1f}s for 'Оригинал' aspect ratio to be applied...")
                    time.sleep(aspect_ratio_wait)
                    break
                    
            except Exception as e:
                log_warning(f"Error with aspect ratio selector {selector}: {str(e)}")
                continue
        
        return aspect_ratio_found
    
    def _try_fallback_aspect_ratios(self):
        """Try fallback aspect ratio options"""
        for selector in self.selectors.FALLBACK_ASPECT_RATIOS:
            try:
                if selector.startswith('//'):
                    fallback_button = self.page.query_selector(f"xpath={selector}")
                else:
                    fallback_button = self.page.query_selector(selector)
                
                if fallback_button and fallback_button.is_visible():
                    button_text = fallback_button.text_content() or ""
                    log_info(f"📐 Found fallback aspect ratio option: '{button_text.strip()}'")
                    self.human_behavior.advanced_element_interaction(fallback_button, 'click')
                    time.sleep(2)
                    break
                    
            except Exception as e:
                continue
    
    def _fallback_crop_logic(self):
        """Fallback to original crop logic"""
        original_selectors = [
            'button:has-text("Оригинал")',
            'button:has-text("Original")',
        ]
        
        for selector in original_selectors:
            try:
                original_button = self.page.query_selector(selector)
                if original_button and original_button.is_visible():
                    log_info(f"📐 Found fallback 'Оригинал' button: {selector}")
                    self.human_behavior.advanced_element_interaction(original_button, 'click')
                    time.sleep(2)
                    break
            except Exception as e:
                continue


def handle_crop_and_aspect_ratio(page, human_behavior):
    """
    Standalone function to handle crop and aspect ratio selection
    Maintains backward compatibility with existing code
    """
    try:
        crop_handler = CropHandler(page, human_behavior)
        return crop_handler.handle_crop_settings()
    except Exception as e:
        log_error(f"Error in crop handling: {str(e)}")
        return False 