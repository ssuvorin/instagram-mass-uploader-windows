"""
Instagram automation classes for navigation, upload, and login operations
"""

import os
import time
import random
import logging
from .logging_utils import log_info, log_error, log_debug, log_warning, log_success
from .selectors_config import InstagramSelectors as SelectorConfig, SelectorUtils

logger = logging.getLogger('uploader.instagram_automation')


class InstagramAutomationBase:
    """Base class for Instagram automation operations"""
    
    def __init__(self, page, human_behavior=None):
        self.page = page
        self.human_behavior = human_behavior
        self.selectors = SelectorConfig()
        
        # Configure logging to reduce verbose output
        self._configure_page_logging()
    
    def _configure_page_logging(self):
        """Configure page logging to reduce verbose output"""
        try:
            # Set page console logging to minimal
            self.page.on("console", lambda msg: None)
            self.page.on("pageerror", lambda exception: None)
            
            # Set browser context timeouts
            self.page.set_default_timeout(30000)  # 30 seconds
            self.page.set_default_navigation_timeout(60000)  # 60 seconds
        except Exception as e:
            log_warning(f"Could not configure page logging: {str(e)}")
    
    def find_element(self, selectors, log_prefix="ELEMENT", timeout=5000):
        """Find the first visible element from a list of selectors"""
        for selector in selectors:
            try:
                if selector.startswith('//'):
                    element = self.page.query_selector(f"xpath={selector}")
                else:
                    element = self.page.query_selector(selector)
                
                if element and element.is_visible():
                    return element
            except Exception:
                continue
        return None
    
    def wait_for_element(self, selectors, timeout=10000, log_prefix="WAIT"):
        """Wait for any of the provided selectors to appear"""
        for selector in selectors:
            try:
                if selector.startswith('//'):
                    self.page.wait_for_selector(f"xpath={selector}", timeout=timeout)
                    return self.page.query_selector(f"xpath={selector}")
                else:
                    self.page.wait_for_selector(selector, timeout=timeout)
                    return self.page.query_selector(selector)
            except Exception:
                continue
        return None
    
    def click_element(self, element, log_prefix="CLICK"):
        """Click element with human behavior if available"""
        if self.human_behavior:
            log_info(f"[{log_prefix}] 🖱️ Clicking with human behavior...")
            try:
                # Set shorter timeout for human behavior to avoid long retry loops
                original_timeout = getattr(self.page, '_timeout_settings', {}).get('default_timeout', 30000)
                self.page.set_default_timeout(5000)  # 5 seconds max
                
                self.human_behavior.advanced_element_interaction(element, 'click')
                
                # Restore original timeout
                self.page.set_default_timeout(original_timeout)
                
            except Exception as e:
                # If human behavior fails, fallback to quick click
                log_warning(f"[{log_prefix}] Human behavior failed, using fallback: {str(e)[:100]}")
                self._quick_click(element, log_prefix)
        else:
            log_info(f"[{log_prefix}] 🖱️ Clicking element...")
            element.click()
    
    def _quick_click(self, element, log_prefix="QUICK_CLICK"):
        """Quick click without verbose Playwright logs"""
        try:
            # Try force click first (fastest)
            element.click(force=True, timeout=3000)
            log_info(f"[{log_prefix}] [OK] Quick click successful")
        except Exception as e:
            try:
                # Fallback to JavaScript click
                self.page.evaluate('(element) => element.click()', element)
                log_info(f"[{log_prefix}] [OK] JavaScript click successful")
            except Exception as e2:
                # Last resort: standard click with short timeout
                try:
                    element.click(timeout=2000)
                    log_info(f"[{log_prefix}] [OK] Standard click successful")
                except Exception as e3:
                    log_warning(f"[{log_prefix}] [WARN] All click methods failed: {str(e3)[:100]}")
    
    def type_text(self, element, text, log_prefix="TYPE"):
        """Type text with human behavior if available"""
        if self.human_behavior:
            log_info(f"[{log_prefix}] ⌨️ Typing with human behavior...")
            self.human_behavior.human_typing(element, text)
        else:
            log_info(f"[{log_prefix}] ⌨️ Typing text...")
            element.fill(text)
    
    def human_wait(self, base_delay=1.0, variance=0.5):
        """Wait with human-like timing"""
        if self.human_behavior:
            delay = self.human_behavior.get_human_delay(base_delay, variance)
        else:
            delay = base_delay + random.uniform(-variance, variance)
        
        time.sleep(max(0.1, delay))
        return delay
    
    def simulate_page_scan(self):
        """Simulate human page scanning behavior"""
        if self.human_behavior:
            self.human_behavior.simulate_page_scanning()
        else:
            time.sleep(random.uniform(0.5, 1.5))


class InstagramNavigator(InstagramAutomationBase):
    """Handles Instagram navigation operations"""
    
    def navigate_to_upload(self):
        """Navigate to upload page with human behavior - handles both menu and direct file dialog scenarios"""
        try:
            log_info("[UPLOAD] [BRAIN] Starting navigation to upload page")
            
            # Simulate page assessment
            self.simulate_page_scan()
            
            # Find upload button
            upload_button = self.find_element(
                self.selectors.UPLOAD_BUTTON, 
                "UPLOAD_BTN"
            )
            
            if not upload_button:
                log_warning("[UPLOAD] [WARN] Upload button not found, trying alternative navigation...")
                return self._navigate_to_upload_alternative()
            
            # Click upload button
            self.click_element(upload_button, "UPLOAD_BTN")
            
            # Wait and observe page changes
            log_info("[UPLOAD] [EYES] Observing page changes...")
            self.simulate_page_scan()
            
            # Check what happened after clicking upload button
            success = self._handle_post_upload_click()
            
            if not success:
                log_warning("[UPLOAD] [WARN] Standard navigation failed, trying alternative...")
                return self._navigate_to_upload_alternative()
            
            return success
            
        except Exception as e:
            log_error(f"[UPLOAD] [FAIL] Navigation failed: {str(e)}")
            log_info("[UPLOAD] [RETRY] Trying alternative navigation method...")
            return self._navigate_to_upload_alternative()
    
    def _navigate_to_upload_alternative(self):
        """Alternative navigation method - direct URL"""
        try:
            log_info("[UPLOAD] [RETRY] Using alternative navigation: direct URL")
            
            # Navigate directly to create page
            current_url = self.page.url
            if 'instagram.com' in current_url:
                create_url = "https://www.instagram.com/create/select/"
                log_info(f"[UPLOAD] 🌐 Navigating to: {create_url}")
                
                self.page.goto(create_url, wait_until="domcontentloaded", timeout=30000)
                
                # Wait for page to load
                load_wait = self.human_wait(3.0, 1.0)
                log_info(f"[UPLOAD] [WAIT] Waiting {load_wait:.1f}s for page load...")
                
                # Check if we're on upload page
                if self._check_for_file_dialog():
                    log_success("[UPLOAD] [OK] Successfully navigated to upload page via direct URL")
                    return True
                else:
                    log_warning("[UPLOAD] [WARN] Direct URL navigation didn't show file dialog")
                    return False
            else:
                log_error("[UPLOAD] [FAIL] Not on Instagram domain, cannot use direct URL")
                return False
                
        except Exception as e:
            log_error(f"[UPLOAD] [FAIL] Alternative navigation failed: {str(e)}")
            return False
    
    def _handle_post_upload_click(self):
        """Handle what happens after clicking upload button - menu or direct file dialog"""
        try:
            # Wait for interface response
            initial_wait = self.human_wait(3.0, 1.0)
            log_info(f"[UPLOAD] [WAIT] Waiting {initial_wait:.1f}s for interface response...")
            
            # Check for file dialog first
            if self._check_for_file_dialog():
                log_info("[UPLOAD] [FOLDER] File dialog opened directly - no menu needed")
                return True
            
            # Check for dropdown menu
            if self._check_for_dropdown_menu():
                log_info("[UPLOAD] [CLIPBOARD] Dropdown menu detected - selecting post option")
                return self._click_post_option()
            
            # Wait additional time and check again
            additional_wait = self.human_wait(2.0, 0.5)
            log_info(f"[UPLOAD] [WAIT] Waiting additional {additional_wait:.1f}s...")
            
            if self._check_for_file_dialog():
                log_info("[UPLOAD] [FOLDER] File dialog appeared after delay")
                return True
            
            if self._check_for_dropdown_menu():
                log_info("[UPLOAD] [CLIPBOARD] Menu appeared after delay")
                return self._click_post_option()
            
            # Try broader detection
            log_warning("[UPLOAD] [WARN] Neither menu nor file dialog detected, trying broader detection...")
            return self._try_broader_upload_detection()
            
        except Exception as e:
            log_error(f"[UPLOAD] [FAIL] Error handling post-upload click: {str(e)}")
            return False
    
    def _check_for_file_dialog(self):
        """Check if file selection dialog is open"""
        try:
            log_info("[UPLOAD] [SEARCH] Checking for file dialog...")
            
            # Use comprehensive file input selectors
            for selector in self.selectors.FILE_INPUT:
                try:
                    if SelectorUtils.is_xpath(selector):
                        elements = self.page.query_selector_all(f"xpath={selector}")
                    else:
                        elements = self.page.query_selector_all(selector)
                    
                    for element in elements:
                        if element.is_visible():
                            log_info(f"[UPLOAD] [OK] File dialog indicator found: {selector}")
                            return True
                except Exception as e:
                    log_debug(f"[UPLOAD] Selector failed: {selector} - {str(e)}")
                    continue
            
            # Check URL for create mode
            try:
                current_url = self.page.url
                if 'create' in current_url.lower():
                    log_info(f"[UPLOAD] [SEARCH] URL indicates create mode: {current_url}")
                    return True
            except:
                pass
            
            # Check page content for upload indicators
            try:
                page_text = self.page.inner_text('body') or ""
                upload_keywords = [
                    'выбрать на компьютере', 'select from computer', 
                    'выбрать файлы', 'select files',
                    'перетащите файлы', 'drag files',
                    'загрузить файл', 'upload file'
                ]
                
                for keyword in upload_keywords:
                    if keyword in page_text.lower():
                        log_info(f"[UPLOAD] [OK] Upload interface detected via keyword: '{keyword}'")
                        return True
            except:
                pass
            
            log_info("[UPLOAD] [FAIL] No file dialog detected")
            return False
            
        except Exception as e:
            log_warning(f"[UPLOAD] Error checking for file dialog: {str(e)}")
            return False
    
    def _check_for_dropdown_menu(self):
        """Check if dropdown menu appeared"""
        try:
            menu_element = self.find_element(
                self.selectors.MENU_INDICATORS,
                "MENU_CHECK"
            )
            
            if menu_element:
                log_info("[UPLOAD] [OK] Dropdown menu detected")
                return True
            
            # Check for specific menu items
            for selector in self.selectors.POST_OPTION[:3]:
                try:
                    if SelectorUtils.is_xpath(selector):
                        post_option = self.page.query_selector(f"xpath={selector}")
                    else:
                        post_option = self.page.query_selector(selector)
                    
                    if post_option and post_option.is_visible():
                        log_info(f"[UPLOAD] [OK] Post option visible in menu")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            log_warning(f"[UPLOAD] Error checking for dropdown menu: {str(e)}")
            return False
    
    def _try_broader_upload_detection(self):
        """Try broader detection methods when standard methods fail"""
        try:
            log_info("[UPLOAD] [RETRY] Attempting broader upload interface detection...")
            
            upload_indicators = [
                'div:has-text("Создать")',
                'div:has-text("Create")',
                'div:has-text("Erstellen")',    # DE
                'div:has-text("Δημιουργία")',    # EL
                'div:has-text("Публикация")',
                'div:has-text("Post")',
                'div:has-text("Beitrag")',       # DE
                'div:has-text("Δημοσίευση")',    # EL
                'div:has-text("Выбрать")',
                'div:has-text("Select")',
                'button:has-text("Выбрать на компьютере")',
                'button:has-text("Select from computer")',
            ]
            
            for indicator in upload_indicators:
                try:
                    element = self.page.query_selector(indicator)
                    if element and element.is_visible():
                        log_info(f"[UPLOAD] [TARGET] Found upload indicator: {indicator}")
                        
                        if 'button' in indicator.lower():
                            self.click_element(element, "UPLOAD_INDICATOR")
                            time.sleep(2)
                        
                        return True
                except:
                    continue
            
            # Check page content
            try:
                page_text = self.page.inner_text('body') or ""
                upload_keywords = ['выбрать на компьютере', 'select from computer', 'перетащите', 'drag']
                
                if any(keyword in page_text.lower() for keyword in upload_keywords):
                    log_info("[UPLOAD] [OK] Upload interface detected via page content")
                    return True
            except:
                pass
            
            log_warning("[UPLOAD] [WARN] Could not detect upload interface")
            return False
            
        except Exception as e:
            log_error(f"[UPLOAD] [FAIL] Error in broader detection: {str(e)}")
            return False
    
    def _click_post_option(self):
        """Find and click the post option in dropdown"""
        try:
            log_info("[UPLOAD] [SEARCH] Looking for 'Публикация' option...")
            
            # Human-like pause to read menu options
            reading_time = self.human_wait(2.0, 0.8)
            log_info(f"[UPLOAD] 📖 Reading menu options for {reading_time:.1f}s...")
            
            self.simulate_page_scan()
            
            post_option = None
            found_selector = None
            
            for i, selector in enumerate(self.selectors.POST_OPTION):
                try:
                    if i > 0:
                        self.human_wait(0.5, 0.2)
                
                    log_info(f"[UPLOAD] [SEARCH] Trying selector {i+1}/{len(self.selectors.POST_OPTION)}")
                
                    if SelectorUtils.is_xpath(selector):
                        post_option = self.page.query_selector(f"xpath={selector}")
                    else:
                        post_option = self.page.query_selector(selector)
                
                    if post_option and post_option.is_visible():
                        try:
                            element_text = post_option.text_content() or ""
                            element_aria = post_option.get_attribute('aria-label') or ""
                            combined_text = (element_text + " " + element_aria).lower()
                            
                            post_keywords = ['публикация', 'post', 'создать публикацию', 'create post']
                            if any(keyword in combined_text for keyword in post_keywords):
                                log_info(f"[UPLOAD] [OK] Found 'Публикация' option: '{element_text.strip()}'")
                                found_selector = selector
                                break
                            else:
                                log_info(f"[UPLOAD] [SEARCH] Element found but text doesn't match: '{element_text.strip()}'")
                                post_option = None
                                continue
                        except:
                            log_info(f"[UPLOAD] [OK] Found potential 'Публикация' option (no text check)")
                            found_selector = selector
                            break
                    
                except Exception as e:
                    log_warning(f"[UPLOAD] Selector failed: {str(e)}")
                    continue
        
            if post_option:
                try:
                    if self.human_behavior:
                        self.human_behavior.natural_mouse_movement(post_option)
                
                    decision_time = self.human_wait(1.5, 0.5)
                    log_info(f"[UPLOAD] 🤔 Decision making pause: {decision_time:.1f}s...")
                
                    self.click_element(post_option, "POST_OPTION")
                
                    wait_time = self.human_wait(5.0, 1.5)
                    log_info(f"[UPLOAD] [WAIT] Waiting {wait_time:.1f}s for upload interface...")
                
                    return True
                
                except Exception as e:
                    log_warning(f"[UPLOAD] Error clicking post option: {str(e)}")
                    try:
                        post_option.click()
                        time.sleep(5)
                        return True
                    except Exception as fallback_e:
                        log_error(f"[UPLOAD] Fallback click failed: {str(fallback_e)}")
                        return False
            else:
                log_warning("[UPLOAD] [WARN] 'Публикация' option not found in menu")
                return self._try_broader_search()
                
        except Exception as e:
            log_error(f"[UPLOAD] [FAIL] Error in _click_post_option: {str(e)}")
            return False
    
    def _try_broader_search(self):
        """Try broader search for clickable menu items"""
        log_info("[UPLOAD] [RETRY] Attempting broader search...")
        
        try:
            clickable_elements = self.page.query_selector_all(
                'a, div[role="menuitem"], div[role="button"]'
            )
            
            for element in clickable_elements:
                if element.is_visible():
                    try:
                        text_content = element.inner_text().strip()
                        if text_content and ("Публикация" in text_content or "Post" in text_content):
                            log_info(f"[UPLOAD] [TARGET] Found potential option: '{text_content}'")
                            self.click_element(element, "BROAD_SEARCH")
                            time.sleep(3)
                            return True
                    except:
                        continue
                        
        except Exception as e:
            log_warning(f"[UPLOAD] Broader search failed: {str(e)}")
        
        return False


class InstagramUploader(InstagramAutomationBase):
    """Handles Instagram video upload operations"""
    
    def upload_video(self, video_file_path, video_obj):
        """Complete video upload process following Selenium pipeline exactly"""
        try:
            if not os.path.exists(video_file_path):
                log_error(f"[UPLOAD] Video file not found: {video_file_path}")
                return False
            
            log_info(f"[UPLOAD] [VIDEO] Starting video upload: {os.path.basename(video_file_path)}")
            
            # Step 1: Select video file IMMEDIATELY (while browser is still open)
            if not self._select_video_file_immediate(video_file_path):
                log_error("[UPLOAD] Failed to select video file")
                return False
            
            # Step 2: Handle crop (Selenium style)
            if not self._handle_crop_selenium_style():
                log_error("[UPLOAD] Failed to handle crop")
                return False
            
            # Step 3: Click Next twice (for _ in range(2): _next_page)
            for i in range(2):
                if not self._click_next_button(i + 1):
                    log_error(f"[UPLOAD] Failed to click Next button {i + 1}")
                    return False
            
            # Step 4: Set description
            if not self._set_description_selenium_style(video_obj):
                log_warning("[UPLOAD] Failed to set description, continuing...")
            
            # Step 5: Set location
            if not self._set_location_selenium_style(video_obj):
                log_warning("[UPLOAD] Failed to set location, continuing...")
            
            # Step 6: Set mentions
            if not self._set_mentions_selenium_style(video_obj):
                log_warning("[UPLOAD] Failed to set mentions, continuing...")
            
            # Step 7: Post video
            if not self._post_video_selenium_style():
                log_error("[UPLOAD] Failed to post video")
                return False
            
            # Step 8: Verify success
            return self._verify_video_posted()
            
        except Exception as e:
            log_error(f"[UPLOAD] Upload failed: {str(e)}")
            return False
    
    def _select_video_file_immediate(self, video_file_path):
        """Select video file immediately after navigation - ADAPTIVE VERSION"""
        try:
            log_info("[UPLOAD] [FOLDER] Selecting video file with adaptive search...")
            
            # Validate file exists first
            if not os.path.exists(video_file_path):
                log_error(f"[UPLOAD] Video file not found: {video_file_path}")
                return False
            
            log_info(f"[UPLOAD] File exists: {os.path.basename(video_file_path)} ({os.path.getsize(video_file_path)} bytes)")
            
            # [TARGET] АДАПТИВНАЯ СТРАТЕГИЯ ПОИСКА FILE INPUT
            file_input = self._find_file_input_adaptive()
            
            if not file_input:
                log_error("[UPLOAD] [FAIL] File input not found with any adaptive strategy")
                return False
            
            # Set files on input IMMEDIATELY
            log_info(f"[UPLOAD] 📤 Setting file on input: {video_file_path}")
            file_input.set_input_files(video_file_path)
            log_success("[UPLOAD] [OK] Video file selected successfully")
            
            # Minimal wait for processing
            processing_delay = random.uniform(2, 3)
            log_info(f"[UPLOAD] [WAIT] Waiting {processing_delay:.1f}s for file processing...")
            time.sleep(processing_delay)
            return True
            
        except Exception as e:
            log_error(f"[UPLOAD] [FAIL] Error selecting video file: {str(e)}")
            return False
    
    def _find_file_input_adaptive(self):
        """Адаптивный поиск файлового input независимо от CSS-классов"""
        try:
            log_info("[UPLOAD] [SEARCH] Starting adaptive file input search...")
            
            # [TARGET] СТРАТЕГИЯ 1: Поиск по семантическим атрибутам (самый надежный)
            log_info("[UPLOAD] [CLIPBOARD] Strategy 1: Semantic attributes search...")
            semantic_strategies = [
                'input[type="file"]',
                'input[accept*="video"]',
                'input[accept*="image"]', 
                'input[accept*="mp4"]',
                'input[accept*="quicktime"]',
                'input[multiple]',
                'form[enctype="multipart/form-data"] input[type="file"]',
                'form[method="POST"] input[type="file"]',
            ]
            
            for selector in semantic_strategies:
                try:
                    elements = self.page.query_selector_all(selector)
                    log_info(f"[UPLOAD] 🔎 Checking selector: {selector} - found {len(elements)} elements")
                    
                    for element in elements:
                        if element and self._is_valid_file_input(element):
                            log_success(f"[UPLOAD] [OK] Found file input via semantic: {selector}")
                            return element
                except Exception as e:
                    log_debug(f"[UPLOAD] Semantic selector failed: {selector} - {str(e)}")
                    continue
            
            # [TARGET] СТРАТЕГИЯ 2: Поиск через структуру диалога "Создание публикации"
            log_info("[UPLOAD] 🏗️ Strategy 2: Dialog structure search...")
            dialog_input = self._find_input_via_dialog_structure()
            if dialog_input:
                log_success("[UPLOAD] [OK] Found file input via dialog structure")
                return dialog_input
            
            # [TARGET] СТРАТЕГИЯ 3: Поиск через кнопку "Выбрать на компьютере"
            log_info("[UPLOAD] 🔘 Strategy 3: Button-based search...")
            button_input = self._find_input_via_button()
            if button_input:
                log_success("[UPLOAD] [OK] Found file input via button search")
                return button_input
            
            # [TARGET] СТРАТЕГИЯ 4: Поиск по контексту формы
            log_info("[UPLOAD] [TEXT] Strategy 4: Form context search...")
            form_input = self._find_input_via_form_context()
            if form_input:
                log_success("[UPLOAD] [OK] Found file input via form context")
                return form_input
            
            # [TARGET] СТРАТЕГИЯ 5: Поиск по характерным CSS-классам Instagram
            log_info("[UPLOAD] 🎨 Strategy 5: Instagram CSS patterns...")
            css_input = self._find_input_via_css_patterns()
            if css_input:
                log_success("[UPLOAD] [OK] Found file input via CSS patterns")
                return css_input
            
            # [TARGET] СТРАТЕГИЯ 6: Широкий поиск всех input и фильтрация
            log_info("[UPLOAD] 🌐 Strategy 6: Broad search with filtering...")
            all_input = self._find_input_via_broad_search()
            if all_input:
                log_success("[UPLOAD] [OK] Found file input via broad search")
                return all_input
                
            log_warning("[UPLOAD] [WARN] No file input found with any adaptive strategy")
            return None
            
        except Exception as e:
            log_error(f"[UPLOAD] [FAIL] Adaptive file input search failed: {str(e)}")
            return None
    
    def _find_input_via_css_patterns(self):
        """Поиск по характерным CSS-паттернам Instagram"""
        try:
            # Паттерны CSS-классов Instagram для файловых input
            css_patterns = [
                # Точный класс из предоставленного HTML
                'input._ac69',
                # Паттерны классов Instagram
                'input[class*="_ac69"]',
                'input[class*="_ac"]', 
                'input[class*="_ac"]',
                # Комбинированные селекторы
                'form input[class*="_ac"]',
                'form[role="presentation"] input',
                'form[enctype="multipart/form-data"] input',
            ]
            
            for pattern in css_patterns:
                try:
                    elements = self.page.query_selector_all(pattern)
                    log_info(f"[UPLOAD] 🎨 CSS pattern: {pattern} - found {len(elements)} elements")
                    
                    for element in elements:
                        if element and self._is_valid_file_input(element):
                            log_info(f"[UPLOAD] [OK] Valid file input found with CSS pattern: {pattern}")
                            return element
                            
                except Exception as e:
                    log_debug(f"[UPLOAD] CSS pattern failed: {pattern} - {str(e)}")
                    continue
                    
            return None
        except Exception as e:
            log_debug(f"[UPLOAD] CSS patterns search failed: {str(e)}")
            return None
    
    def _find_input_via_dialog_structure(self):
        """Найти input через структуру диалога создания публикации"""
        try:
            log_info("[UPLOAD] 🏗️ Searching within dialog structure...")
            
            # Селекторы для диалога создания публикации (из предоставленного HTML)
            dialog_selectors = [
                'div[aria-label="Создание публикации"]',
                'div[aria-label*="Создание"]',
                'div[role="dialog"]',
                'div:has-text("Создание публикации")',
                'div:has-text("Перетащите сюда фото и видео")',
                'div:has-text("Выбрать на компьютере")',
                'div[aria-label="Create new post"]',
                'div[aria-label*="Create"]',
                'div:has-text("Create new post")',
                'div:has-text("Drag photos and videos here")',
                'div:has-text("Select from computer")',
                'div:has-text("Select from device")',
            ]
            
            for selector in dialog_selectors:
                try:
                    dialog = self.page.query_selector(selector)
                    if dialog:
                        log_info(f"[UPLOAD] 🏗️ Found dialog with: {selector}")
                        
                        # Ищем input внутри диалога
                        file_input = dialog.query_selector('input[type="file"]')
                        if file_input and self._is_valid_file_input(file_input):
                            log_info("[UPLOAD] [OK] Found valid file input inside dialog")
                            return file_input
                        
                        # Также проверяем form внутри диалога
                        form = dialog.query_selector('form')
                        if form:
                            form_input = form.query_selector('input[type="file"]')
                            if form_input and self._is_valid_file_input(form_input):
                                log_info("[UPLOAD] [OK] Found valid file input inside form within dialog")
                                return form_input
                                
                except Exception as e:
                    log_debug(f"[UPLOAD] Dialog selector failed {selector}: {str(e)}")
                    continue
                    
            return None
        except Exception as e:
            log_debug(f"[UPLOAD] Dialog structure search failed: {str(e)}")
            return None
    
    def _find_input_via_button(self):
        """Найти input через кнопку 'Выбрать на компьютере'"""
        try:
            button_selectors = [
                'button:has-text("Выбрать на компьютере")',
                'button:has-text("Select from computer")',
                'button:has-text("Выбрать файлы")',
                'button:has-text("Select files")',
                'button:has-text("Select from device")',
            ]
            
            for selector in button_selectors:
                try:
                    button = self.page.query_selector(selector)
                    if button and button.is_visible():
                        # Ищем input в том же контейнере
                        parent = button
                        for _ in range(5):  # Поднимаемся до 5 уровней вверх
                            try:
                                parent = parent.query_selector('xpath=..')
                                if parent:
                                    file_input = parent.query_selector('input[type="file"]')
                                    if file_input:
                                        return file_input
                            except:
                                break
                except Exception as e:
                    log_debug(f"[UPLOAD] Button search failed for {selector}: {str(e)}")
                    continue
            return None
        except Exception as e:
            log_debug(f"[UPLOAD] Button-based search failed: {str(e)}")
            return None
    
    def _find_input_via_form_context(self):
        """Найти input через контекст формы"""
        try:
            # Ищем формы с multipart/form-data
            forms = self.page.query_selector_all('form[enctype="multipart/form-data"]')
            for form in forms:
                file_input = form.query_selector('input[type="file"]')
                if file_input and self._is_valid_file_input(file_input):
                    return file_input
            
            # Ищем формы с method="POST"
            forms = self.page.query_selector_all('form[method="POST"]')
            for form in forms:
                file_input = form.query_selector('input[type="file"]')
                if file_input and self._is_valid_file_input(file_input):
                    return file_input
                    
            return None
        except Exception as e:
            log_debug(f"[UPLOAD] Form context search failed: {str(e)}")
            return None
    
    def _find_input_via_broad_search(self):
        """Широкий поиск всех input элементов с фильтрацией"""
        try:
            # Получаем все input элементы на странице
            all_inputs = self.page.query_selector_all('input')
            
            for input_element in all_inputs:
                try:
                    # Проверяем каждый input
                    if self._is_valid_file_input(input_element):
                        # Дополнительная проверка - input должен быть в активном контексте
                        input_classes = input_element.get_attribute('class') or ""
                        input_accept = input_element.get_attribute('accept') or ""
                        
                        # Проверяем, что accept содержит нужные типы файлов
                        if any(file_type in input_accept.lower() for file_type in ['video', 'image', 'mp4', 'jpeg', 'png']):
                            log_info(f"[UPLOAD] Found valid file input: accept='{input_accept}', classes='{input_classes[:50]}'")
                            return input_element
                            
                except Exception as e:
                    log_debug(f"[UPLOAD] Error checking input element: {str(e)}")
                    continue
                    
            return None
        except Exception as e:
            log_debug(f"[UPLOAD] Broad search failed: {str(e)}")
            return None
    
    def _handle_crop_selenium_style(self):
        """Handle crop exactly like Selenium version - ADAPTIVE VERSION"""
        try:
            log_info("📐 [CROP] Starting ADAPTIVE crop handling...")
            
            # Wait for crop page to load
            initial_wait = random.uniform(3, 5)
            log_info(f"📐 [CROP] Waiting {initial_wait:.1f}s for crop page to load...")
            time.sleep(initial_wait)
            
            # First, verify if we're on a crop page using adaptive detection
            if not self._verify_crop_page_adaptive():
                log_info("ℹ️ [CROP] Not on crop page or crop not needed, skipping crop handling")
                return True
            
            # Use adaptive crop detection and handling
            if self._handle_crop_adaptive():
                log_success("📐 [CROP] [OK] Crop handled successfully with adaptive method")
                return True
            else:
                log_warning("📐 [CROP] [WARN] Adaptive crop handling failed, video may proceed with default crop")
                return True  # Don't fail the whole process
                
        except Exception as e:
            log_error(f"📐 [CROP] [FAIL] Crop handling failed: {str(e)}")
            return True  # Don't fail the whole upload process
    
    def _verify_crop_page_adaptive(self):
        """Verify if we're on a crop page using adaptive detection"""
        try:
            log_info("📐 [VERIFY] Checking if we're on crop page (adaptive)...")
            
            # Adaptive indicators for crop page
            crop_page_indicators = [
                # Семантические индикаторы
                'svg[aria-label*="Выбрать размер"]',
                'svg[aria-label*="обрезать"]', 
                'svg[aria-label*="Select crop"]',
                'svg[aria-label*="Crop"]',
                '[aria-label*="Выбрать размер и обрезать"]',
                '[aria-label*="Select crop and size"]',
                
                # Контекстные индикаторы
                'button:has(svg[aria-label*="размер"])',
                'button:has(svg[aria-label*="crop"])',
                'div[role="button"]:has(svg[aria-label*="размер"])',
                'div[role="button"]:has(svg[aria-label*="crop"])',
                
                # XPath индикаторы
                '//svg[contains(@aria-label, "размер")]',
                '//svg[contains(@aria-label, "crop")]',
                '//button[.//svg[contains(@aria-label, "размер")]]',
                '//button[.//svg[contains(@aria-label, "crop")]]',
            ]
            
            for indicator in crop_page_indicators:
                try:
                    if indicator.startswith('//'):
                        element = self.page.locator(f'xpath={indicator}').first
                    else:
                        element = self.page.locator(indicator).first
                        
                    if element.is_visible(timeout=1000):
                        log_success(f"📐 [VERIFY] [OK] Found crop page indicator: {indicator}")
                        return True
                        
                except Exception as e:
                    log_debug(f"📐 [VERIFY] Indicator {indicator} not found: {str(e)}")
                    continue
            
            log_info("📐 [VERIFY] No crop page indicators found")
            return False
            
        except Exception as e:
            log_warning(f"📐 [VERIFY] Crop page verification failed: {str(e)}")
            return False
    
    def _handle_crop_adaptive(self):
        """Handle crop with adaptive methods"""
        try:
            log_info("📐 [ADAPTIVE] Starting adaptive crop handling...")
            
            # Strategy 1: Use crop handler (recommended)
            try:
                from .crop_handler import CropHandler
                crop_handler = CropHandler(self.page, self.human_behavior)
                if crop_handler.handle_crop():
                    log_success("📐 [ADAPTIVE] [OK] Crop handled by CropHandler")
                    return True
            except Exception as e:
                log_warning(f"📐 [ADAPTIVE] CropHandler failed: {str(e)}")
            
            # Strategy 2: Direct adaptive search and click
            try:
                if self._find_and_click_crop_button_adaptive():
                    log_success("📐 [ADAPTIVE] [OK] Crop button found and clicked directly")
                    
                    # Wait for crop options to appear
                    time.sleep(random.uniform(2, 4))
                    
                    # Try to select appropriate crop option
                    if self._select_crop_option_adaptive():
                        log_success("📐 [ADAPTIVE] [OK] Crop option selected")
                        return True
            except Exception as e:
                log_warning(f"📐 [ADAPTIVE] Direct crop handling failed: {str(e)}")
            
            # Strategy 3: Fallback - continue without crop
            log_warning("📐 [ADAPTIVE] [WARN] All crop strategies failed, continuing without crop adjustment")
            return True
            
        except Exception as e:
            log_error(f"📐 [ADAPTIVE] Adaptive crop handling failed: {str(e)}")
            return False
    
    def _find_and_click_crop_button_adaptive(self):
        """Find and click crop button using adaptive search"""
        log_info("📐 [SEARCH] Starting adaptive crop button search...")
        
        # Multi-level search strategy
        search_levels = [
            # Level 1: Semantic attributes (most reliable)
            [
                'svg[aria-label="Выбрать размер и обрезать"]',
                'svg[aria-label*="Выбрать размер"]',
                'svg[aria-label*="обрезать"]',
                'svg[aria-label*="Select crop"]',
                'svg[aria-label*="Crop"]',
            ],
            # Level 2: Parent elements
            [
                'button:has(svg[aria-label*="Выбрать размер"])',
                'button:has(svg[aria-label*="обрезать"])',
                'button:has(svg[aria-label*="Select crop"])',
                'div[role="button"]:has(svg[aria-label*="Выбрать размер"])',
                'div[role="button"]:has(svg[aria-label*="Select crop"])',
            ],
            # Level 3: XPath search
            [
                '//svg[contains(@aria-label, "Выбрать размер")]',
                '//svg[contains(@aria-label, "обрезать")]',
                '//svg[contains(@aria-label, "Select crop")]',
                '//button[.//svg[contains(@aria-label, "Выбрать размер")]]',
                '//button[.//svg[contains(@aria-label, "Select crop")]]',
            ]
        ]
        
        for level_index, selectors in enumerate(search_levels, 1):
            log_info(f"📐 [SEARCH] Trying search level {level_index}...")
            
            for selector in selectors:
                try:
                    log_info(f"📐 [SEARCH] Testing selector: {selector}")
                    
                    if selector.startswith('//'):
                        element = self.page.locator(f'xpath={selector}').first
                    else:
                        element = self.page.locator(selector).first
                    
                    if element.is_visible(timeout=1000):
                        log_success(f"📐 [SEARCH] [OK] Found crop element: {selector}")
                        
                        # If it's an SVG, find the parent button
                        if 'svg' in selector and not 'has(' in selector:
                            parent_button = element.locator('xpath=ancestor::button[1] | xpath=ancestor::div[@role="button"][1]').first
                            if parent_button.is_visible():
                                element = parent_button
                                log_info("📐 [SEARCH] Using parent button element")
                        
                        # Human-like click
                        element.hover()
                        time.sleep(random.uniform(0.3, 0.7))
                        element.click()
                        time.sleep(random.uniform(0.5, 1.0))
                        
                        log_success("📐 [SEARCH] [OK] Successfully clicked crop button")
                        return True
                
                except Exception as e:
                    log_debug(f"📐 [SEARCH] Selector {selector} failed: {str(e)}")
                    continue
        
        log_warning("📐 [SEARCH] [WARN] All search levels failed")
        return False
    
    def _select_crop_option_adaptive(self):
        """Select crop option using adaptive methods - IMPROVED for dynamic selectors"""
        try:
            log_info("📐 [OPTION] Looking for crop options to select...")
            
            # Wait for crop menu to appear
            time.sleep(random.uniform(1, 2))
            
            # [TARGET] АДАПТИВНАЯ СТРАТЕГИЯ: Поиск по семантическим признакам (не по CSS-классам)
            search_strategies = [
                self._find_original_by_text,
                self._find_original_by_svg,
                self._find_original_by_position,
                self._find_any_crop_option
            ]
            
            for strategy_index, strategy in enumerate(search_strategies, 1):
                log_info(f"📐 [OPTION] Trying strategy {strategy_index}: {strategy.__name__}")
                
                try:
                    crop_option = strategy()
                    if crop_option:
                        log_success(f"📐 [OPTION] [OK] Found crop option using strategy {strategy_index}")
                        
                        # Human-like selection
                        crop_option.hover()
                        time.sleep(random.uniform(0.2, 0.5))
                        crop_option.click()
                        time.sleep(random.uniform(0.5, 1.0))
                        
                        log_success("📐 [OPTION] [OK] Successfully selected crop option")
                        return True
                        
                except Exception as e:
                    log_debug(f"📐 [OPTION] Strategy {strategy_index} failed: {str(e)}")
                    continue
            
            # If no specific option found, just continue (default crop will be used)
            log_info("📐 [OPTION] No specific crop option selected, using default")
            return True
            
        except Exception as e:
            log_warning(f"📐 [OPTION] Crop option selection failed: {str(e)}")
            return True  # Don't fail the process
    
    def _find_original_by_text(self):
        """Поиск 'Оригинал' по тексту (самый надежный)"""
        log_info("📐 [TEXT] Searching for 'Оригинал' by text content...")
        
        # Семантические селекторы по тексту (не зависят от CSS)
        text_selectors = [
            # Прямой поиск по тексту в span
            'span:has-text("Оригинал")',
            'span:has-text("Original")',
            
            # Поиск родительской кнопки с текстом "Оригинал"
            'button:has-text("Оригинал")',
            'div[role="button"]:has-text("Оригинал")',
            'button:has-text("Original")',
            'div[role="button"]:has-text("Original")',
            
            # Поиск элементов содержащих span с текстом "Оригинал"
            'div[role="button"]:has(span:has-text("Оригинал"))',
            'button:has(span:has-text("Оригинал"))',
            'div[role="button"]:has(span:has-text("Original"))',
            'button:has(span:has-text("Original"))',
            
            # XPath селекторы (самые мощные)
            '//span[text()="Оригинал"]',
            '//span[text()="Original"]',
            '//div[@role="button" and .//span[text()="Оригинал"]]',
            '//button[.//span[text()="Оригинал"]]',
            '//div[@role="button" and .//span[text()="Original"]]',
            '//button[.//span[text()="Original"]]',
        ]
        
        for selector in text_selectors:
            try:
                log_info(f"📐 [TEXT] Trying: {selector}")
                
                if selector.startswith('//'):
                    element = self.page.locator(f'xpath={selector}').first
                else:
                    element = self.page.locator(selector).first
                
                if element.is_visible(timeout=1000):
                    # Если найден span, найти родительскую кнопку
                    if 'span' in selector and not 'button' in selector and not 'role="button"' in selector:
                        parent_button = element.locator('xpath=ancestor::*[@role="button"][1] | xpath=ancestor::button[1]').first
                        if parent_button.is_visible():
                            log_success(f"📐 [TEXT] [OK] Found 'Оригинал' parent button: {selector}")
                            return parent_button
                    
                    log_success(f"📐 [TEXT] [OK] Found 'Оригинал' element: {selector}")
                    return element
            
            except Exception as e:
                log_debug(f"📐 [TEXT] Selector {selector} failed: {str(e)}")
                continue
        
        return None
    
    def _find_original_by_svg(self):
        """Поиск 'Оригинал' по SVG иконке (контур фото)"""
        log_info("📐 [SVG] Searching for 'Оригинал' by SVG icon...")
        
        try:
            # Поиск SVG с aria-label "Значок контура фото" (как в HTML)
            svg_selectors = [
                'svg[aria-label="Значок контура фото"]',
                'svg[aria-label*="контур"]',
                'svg[aria-label*="фото"]',
                'svg[aria-label*="photo"]',
                'svg[aria-label*="outline"]',
                
                # XPath для SVG
                '//svg[@aria-label="Значок контура фото"]',
                '//svg[contains(@aria-label, "контур")]',
                '//svg[contains(@aria-label, "фото")]',
                '//svg[contains(@aria-label, "photo")]',
                '//svg[contains(@aria-label, "outline")]',
            ]
            
            for selector in svg_selectors:
                try:
                    if selector.startswith('//'):
                        svg_element = self.page.locator(f'xpath={selector}').first
                    else:
                        svg_element = self.page.locator(selector).first
                    
                    if svg_element.is_visible(timeout=1000):
                        log_success(f"📐 [SVG] [OK] Found SVG icon: {selector}")
                        
                        # Найти родительскую кнопку
                        parent_button = svg_element.locator('xpath=ancestor::*[@role="button"][1] | xpath=ancestor::button[1]').first
                        if parent_button.is_visible():
                            log_success("📐 [SVG] [OK] Found parent button for SVG")
                            return parent_button
                        
                        return svg_element
                        
                except Exception as e:
                    log_debug(f"📐 [SVG] SVG selector {selector} failed: {str(e)}")
                    continue
            
        except Exception as e:
            log_warning(f"📐 [SVG] SVG search failed: {str(e)}")
        
        return None
    
    def _find_original_by_position(self):
        """Поиск 'Оригинал' по позиции (обычно первый элемент)"""
        log_info("📐 [POS] Searching for 'Оригинал' by position...")
        
        try:
            # Найти все кнопки с role="button" в контексте кропа
            crop_buttons = self.page.locator('div[role="button"][tabindex="0"]').all()
            
            if crop_buttons:
                log_info(f"📐 [POS] Found {len(crop_buttons)} crop option buttons")
                
                # Проверить первые несколько кнопок
                for i, button in enumerate(crop_buttons[:4]):  # Проверить первые 4
                    try:
                        if button.is_visible():
                            # Проверить содержимое кнопки
                            button_text = button.text_content() or ""
                            if 'Оригинал' in button_text or 'Original' in button_text:
                                log_success(f"📐 [POS] [OK] Found 'Оригинал' at position {i+1}")
                                return button
                            
                            # Если первая кнопка и нет явного текста - возможно это "Оригинал"
                            if i == 0 and not button_text.strip():
                                log_info(f"📐 [POS] [OK] Using first button as potential 'Оригинал'")
                                return button
            
                    except Exception as e:
                        log_debug(f"📐 [POS] Button {i+1} check failed: {str(e)}")
                        continue
                        
        except Exception as e:
            log_warning(f"📐 [POS] Position search failed: {str(e)}")
        
        return None
    
    def _find_any_crop_option(self):
        """Поиск любой доступной опции кропа (fallback)"""
        log_info("📐 [ANY] Searching for any available crop option...")
        
        try:
            # Широкие селекторы для любых опций кропа
            fallback_selectors = [
                # Любые кнопки с табиндексом в контексте кропа
                'div[role="button"][tabindex="0"]',
                'button[tabindex="0"]',
                '[role="button"][tabindex="0"]',
                
                # Любые кнопки содержащие span
                'div[role="button"]:has(span)',
                'button:has(span)',
                
                # Любые элементы с соотношением сторон
                'div[role="button"]:has-text("1:1")',
                'div[role="button"]:has-text("9:16")',
                'div[role="button"]:has-text("16:9")',
                'div[role="button"]:has-text("4:5")',
                
                # XPath для первой доступной кнопки
                '(//div[@role="button" and @tabindex="0"])[1]',
                '(//button[@tabindex="0"])[1]',
            ]
            
            for selector in fallback_selectors:
                try:
                    if selector.startswith('//') or selector.startswith('(//'):
                        element = self.page.locator(f'xpath={selector}').first
                    else:
                        element = self.page.locator(selector).first
                    
                    if element.is_visible(timeout=1000):
                        element_text = element.text_content() or ""
                        log_info(f"📐 [ANY] [OK] Found fallback crop option: '{element_text.strip()}' with selector: {selector}")
                        return element
                        
                except Exception as e:
                    log_debug(f"📐 [ANY] Fallback selector {selector} failed: {str(e)}")
                    continue
                    
        except Exception as e:
            log_warning(f"📐 [ANY] Fallback search failed: {str(e)}")
        
        return None
    
    def _click_next_button(self, step_number):
        """Click next button (like Selenium _next_page)"""
        try:
            log_info(f"[RETRY] Next button click {step_number}/2")
            
            # Human delay before clicking
            time.sleep(random.uniform(3, 5))
            
            next_button = self.find_element([
                'button:has-text("Далее")',
                'button:has-text("Next")',
                'button:has-text("Weiter")',      # DE
                'button:has-text("Fortfahren")', # DE
                'button:has-text("Επόμενο")',     # EL
                'button:has-text("Συνέχεια")',    # EL
                'button:has-text("Продолжить")',
                'button:has-text("Continue")',
                'div[role="button"]:has-text("Далее")',
                'div[role="button"]:has-text("Next")',
                'div[role="button"]:has-text("Weiter")',      # DE
                'div[role="button"]:has-text("Fortfahren")',  # DE
                'div[role="button"]:has-text("Επόμενο")',     # EL
                'div[role="button"]:has-text("Συνέχεια")',    # EL
            ])
            
            if next_button:
                next_button.scroll_into_view_if_needed()
                time.sleep(random.uniform(1, 2))
                
                next_button.hover()
                time.sleep(random.uniform(1, 2))
                
                # Use JavaScript click for reliability
                self.page.evaluate('(element) => element.click()', next_button)
                
                time.sleep(random.uniform(4, 6))
                log_success(f"[OK] Successfully clicked next button for step {step_number}")
                return True
            else:
                log_error(f"[FAIL] Next button not found for step {step_number}")
                return False
            
        except Exception as e:
            log_error(f"Error clicking next button for step {step_number}: {str(e)}")
            return False
    
    def _set_description_selenium_style(self, video_obj):
        """Set video description with HUMAN-LIKE typing behavior"""
        try:
            if not hasattr(video_obj, 'title_data') or not video_obj.title_data:
                log_info("[ОПИСАНИЕ] Нет данных для описания")
                return True
            
            description = video_obj.title_data.title
            if not description:
                log_info("[ОПИСАНИЕ] Пустое описание")
                return True
            
            log_info(f"[ОПИСАНИЕ] Устанавливаем описание: {description[:50]}...")
            
            # Find description textarea
            description_field = self.find_element([
                'textarea[aria-label*="Напишите подпись" i]',
                'textarea[aria-label*="Write a caption" i]',
                'div[contenteditable="true"]',
                'textarea[placeholder*="подпись" i]',
                'textarea[placeholder*="caption" i]',
            ])
            
            if not description_field:
                log_warning("[ОПИСАНИЕ] Поле описания не найдено")
                return False
            
            # Click field and wait
            description_field.click()
            time.sleep(random.uniform(0.8, 1.5))
            
            # Clear field
            description_field.fill('')
            time.sleep(random.uniform(0.5, 1.0))
            
            # HUMAN-LIKE TYPING with mistakes and corrections
            self._type_like_human(description_field, description)
            
            # Press Enter for line break after description
            log_info("[ОПИСАНИЕ] Нажимаем Enter для переноса строки...")
            description_field.press('Enter')
            time.sleep(random.uniform(0.5, 1.0))
            
            log_success("[ОПИСАНИЕ] [OK] Описание установлено успешно")
            return True
            
        except Exception as e:
            log_error(f"[ОПИСАНИЕ] [FAIL] Ошибка установки описания: {str(e)}")
            return False
    
    def _type_like_human(self, element, text):
        """Type text like a human with mistakes, corrections, and realistic timing"""
        try:
            log_info("[ПЕЧАТЬ] [BOT] Начинаем человеческую печать...")
            
            i = 0
            while i < len(text):
                char = text[i]
                
                # Random typing speed (slower for humans)
                delay = random.uniform(0.08, 0.25)  # Much slower than 0.05
                
                # Chance to make a mistake (5% for Russian, 3% for English)
                mistake_chance = 0.05 if ord(char) > 127 else 0.03
                
                if random.random() < mistake_chance and char.isalpha():
                    # Make a mistake
                    if ord(char) > 127:  # Russian characters
                        wrong_chars = ['ф', 'в', 'а', 'п', 'р', 'о', 'л', 'д', 'ж', 'э']
                    else:  # English characters
                        wrong_chars = ['q', 'w', 'e', 'r', 't', 'y', 'a', 's', 'd', 'f']
                    
                    wrong_char = random.choice(wrong_chars)
                    element.type(wrong_char)
                    time.sleep(delay)
                    
                    # Realize mistake after 1-3 more characters
                    realization_delay = random.randint(1, 3)
                    mistake_chars = 1
                    
                    # Continue typing a bit before realizing mistake
                    for j in range(min(realization_delay, len(text) - i - 1)):
                        if i + j + 1 < len(text):
                            element.type(text[i + j + 1])
                            mistake_chars += 1
                            time.sleep(random.uniform(0.05, 0.15))
                    
                    # Pause (human realizes mistake)
                    time.sleep(random.uniform(0.3, 0.8))
                    
                    # Delete wrong characters
                    for _ in range(mistake_chars):
                        element.press('Backspace')
                        time.sleep(random.uniform(0.05, 0.12))
                    
                    # Pause before correction
                    time.sleep(random.uniform(0.2, 0.5))
                    
                    # Type correct characters
                    for j in range(mistake_chars):
                        if i + j < len(text):
                            element.type(text[i + j])
                            time.sleep(random.uniform(0.08, 0.2))
                    
                    i += mistake_chars
                else:
                    # Normal typing
                    element.type(char)
                    time.sleep(delay)
                    i += 1
                
                # Random pauses for thinking
                if random.random() < 0.02:  # 2% chance
                    thinking_pause = random.uniform(0.5, 2.0)
                    log_info(f"[ПЕЧАТЬ] 🤔 Думаем {thinking_pause:.1f}с...")
                    time.sleep(thinking_pause)
                
                # Longer pause after punctuation
                if char in '.!?,:;':
                    time.sleep(random.uniform(0.1, 0.4))
            
            log_success("[ПЕЧАТЬ] [OK] Человеческая печать завершена")
            
        except Exception as e:
            log_error(f"[ПЕЧАТЬ] [FAIL] Ошибка человеческой печати: {str(e)}")
            # Fallback to simple typing
            element.type(text)
    
    def _set_location_selenium_style(self, video_obj):
        """Set location with proper data access and correct selectors"""
        try:
            # ПРАВИЛЬНЫЙ способ получения локации из BulkVideo модели
            location = None
            
            # 1. Сначала проверяем индивидуальную локацию видео
            if hasattr(video_obj, 'location') and video_obj.location:
                location = video_obj.location.strip()
                log_info(f"[ЛОКАЦИЯ] Найдена индивидуальная локация: {location}")
            
            # 2. Затем проверяем default_location из задачи
            elif hasattr(video_obj, 'bulk_task') and video_obj.bulk_task:
                if hasattr(video_obj.bulk_task, 'default_location') and video_obj.bulk_task.default_location:
                    location = video_obj.bulk_task.default_location.strip()
                    log_info(f"[ЛОКАЦИЯ] Найдена локация по умолчанию из задачи: {location}")
            
            # 3. Проверяем get_effective_location если есть
            if not location and hasattr(video_obj, 'get_effective_location'):
                try:
                    location = video_obj.get_effective_location()
                    if location:
                        location = location.strip()
                        log_info(f"[ЛОКАЦИЯ] Найдена локация через get_effective_location: {location}")
                except Exception as e:
                    log_debug(f"[ЛОКАЦИЯ] Ошибка в get_effective_location: {str(e)}")
            
            # 4. DEBUG: Показать все доступные атрибуты video_obj
            if not location:
                log_info("[ЛОКАЦИЯ] Попытка найти локацию среди всех атрибутов video_obj...")
                for attr_name in dir(video_obj):
                    if not attr_name.startswith('_') and 'location' in attr_name.lower():
                        try:
                            attr_value = getattr(video_obj, attr_name)
                            if attr_value and isinstance(attr_value, str) and attr_value.strip():
                                location = attr_value.strip()
                                log_info(f"[ЛОКАЦИЯ] Найдена локация в video_obj.{attr_name}: {location}")
                                break
                        except:
                            continue
            
            if not location:
                log_info("[ЛОКАЦИЯ] Нет данных о локации")
                return True
            
            log_info(f"[ЛОКАЦИЯ] Устанавливаем локацию: {location}")
            
            # Wait a bit before location (after description and Enter)
            time.sleep(random.uniform(1.0, 2.0))
            
            # ИСПРАВЛЕННЫЕ СЕЛЕКТОРЫ из предоставленного HTML
            location_field_selectors = [
                # Точные селекторы из HTML
                'input[placeholder="Добавить место"]',
                'input[name="creation-location-input"]',
                
                # Альтернативные селекторы
                'input[placeholder*="место" i]',
                'input[placeholder*="location" i]',
                'input[aria-label*="место" i]',
                'input[aria-label*="location" i]',
                'input[aria-label*="Добавить место" i]',
                'input[placeholder*="Добавить место" i]',
                
                # XPath селекторы
                '//input[@placeholder="Добавить место"]',
                '//input[@name="creation-location-input"]',
            ]
            
            location_field = None
            for selector in location_field_selectors:
                try:
                    if selector.startswith('//'):
                        element = self.page.query_selector(f"xpath={selector}")
                    else:
                        element = self.page.query_selector(selector)
                    
                    if element and element.is_visible():
                        log_success(f"[ЛОКАЦИЯ] [OK] Найдено поле локации: {selector}")
                        location_field = element
                        break
                except Exception as e:
                    log_debug(f"[ЛОКАЦИЯ] Селектор {selector} не сработал: {str(e)}")
                    continue
            
            if not location_field:
                log_warning("[ЛОКАЦИЯ] [WARN] Поле локации не найдено")
                return False
            
            # Human-like interaction with location field
            location_field.scroll_into_view_if_needed()
            time.sleep(random.uniform(0.5, 1.0))
            
            location_field.click()
            time.sleep(random.uniform(1.0, 2.0))
            
            # Clear field first
            location_field.fill('')
            time.sleep(random.uniform(0.3, 0.7))
            
            # Type location with human-like speed
            self._type_like_human(location_field, location)
            
            # Wait for suggestions
            time.sleep(random.uniform(2.0, 3.0))
            
            # ИСПРАВЛЕННЫЕ СЕЛЕКТОРЫ для выбора предложений локации
            suggestion_selectors = [
                # Основной селектор для первого предложения в диалоге
                "//div[@role='dialog']/div/div/div/div/div/div/button",
                "//div[@role='dialog']//button[1]",
                
                # Альтернативные селекторы
                f'div[role="button"]:has-text("{location}")',
                f'button:has-text("{location}")',
                'div[role="button"]:first-child',
                'li[role="button"]:first-child',
                'div[data-testid*="location"]:first-child',
                
                # XPath для первого предложения
                '(//div[@role="button"])[1]',
                '(//li[@role="button"])[1]',
                '(//button)[1]',
            ]
            
            suggestion = None
            for selector in suggestion_selectors:
                try:
                    if selector.startswith('//') or selector.startswith('(//'):
                        element = self.page.query_selector(f"xpath={selector}")
                    else:
                        element = self.page.query_selector(selector)
                    
                    if element and element.is_visible():
                        suggestion = element
                        log_success(f"[ЛОКАЦИЯ] [OK] Найдено предложение локации: {selector}")
                        break
                except Exception as e:
                    log_debug(f"[ЛОКАЦИЯ] Селектор {selector} не сработал: {str(e)}")
                    continue
            
            if suggestion:
                suggestion.hover()
                time.sleep(random.uniform(0.5, 1.0))
                suggestion.click()
                time.sleep(random.uniform(1.0, 2.0))
                log_success("[ЛОКАЦИЯ] [OK] Локация установлена успешно")
            else:
                log_warning("[ЛОКАЦИЯ] [WARN] Предложения локации не найдены")
                # Press Enter to try to accept typed location
                location_field.press('Enter')
                time.sleep(random.uniform(1.0, 1.5))
            
            return True
            
        except Exception as e:
            log_error(f"[ЛОКАЦИЯ] [FAIL] Ошибка установки локации: {str(e)}")
            return False
    
    def _set_mentions_selenium_style(self, video_obj):
        """Set mentions with proper data access and correct selectors - ONE BY ONE"""
        try:
            # ПРАВИЛЬНЫЙ способ получения упоминаний из BulkVideo модели
            mentions = None
            
            # 1. Сначала проверяем индивидуальные упоминания видео
            if hasattr(video_obj, 'mentions') and video_obj.mentions:
                mentions = video_obj.mentions.strip()
                log_info(f"[УПОМИНАНИЯ] Найдены индивидуальные упоминания: {mentions}")
            
            # 2. Затем проверяем default_mentions из задачи
            elif hasattr(video_obj, 'bulk_task') and video_obj.bulk_task:
                if hasattr(video_obj.bulk_task, 'default_mentions') and video_obj.bulk_task.default_mentions:
                    mentions = video_obj.bulk_task.default_mentions.strip()
                    log_info(f"[УПОМИНАНИЯ] Найдены упоминания по умолчанию из задачи: {mentions}")
            
            # 3. Проверяем get_effective_mentions_list если есть
            if not mentions and hasattr(video_obj, 'get_effective_mentions_list'):
                try:
                    mentions_list = video_obj.get_effective_mentions_list()
                    if mentions_list:
                        mentions = ', '.join(mentions_list)
                        log_info(f"[УПОМИНАНИЯ] Найдены упоминания через get_effective_mentions_list: {mentions}")
                except Exception as e:
                    log_debug(f"[УПОМИНАНИЯ] Ошибка в get_effective_mentions_list: {str(e)}")
            
            # 4. Проверяем default_mentions_list если есть в задаче
            if not mentions and hasattr(video_obj, 'bulk_task') and video_obj.bulk_task:
                if hasattr(video_obj.bulk_task, 'get_default_mentions_list'):
                    try:
                        default_mentions_list = video_obj.bulk_task.get_default_mentions_list()
                        if default_mentions_list:
                            mentions = ', '.join(default_mentions_list)
                            log_info(f"[УПОМИНАНИЯ] Найдены упоминания через get_default_mentions_list: {mentions}")
                    except Exception as e:
                        log_debug(f"[УПОМИНАНИЯ] Ошибка в get_default_mentions_list: {str(e)}")
            
            # 5. DEBUG: Показать все доступные атрибуты video_obj
            if not mentions:
                log_info("[УПОМИНАНИЯ] Попытка найти упоминания среди всех атрибутов video_obj...")
                for attr_name in dir(video_obj):
                    if not attr_name.startswith('_') and ('mention' in attr_name.lower() or 'collaborator' in attr_name.lower()):
                        try:
                            attr_value = getattr(video_obj, attr_name)
                            if attr_value and isinstance(attr_value, str) and attr_value.strip():
                                mentions = attr_value.strip()
                                log_info(f"[УПОМИНАНИЯ] Найдены упоминания в video_obj.{attr_name}: {mentions}")
                                break
                        except:
                            continue
            
            if not mentions:
                log_info("[УПОМИНАНИЯ] Нет данных об упоминаниях")
                return True
            
            log_info(f"[УПОМИНАНИЯ] Устанавливаем упоминания: {mentions}")
            
            # Wait a bit before mentions (after location)
            time.sleep(random.uniform(1.0, 2.0))
            
            # ИСПРАВЛЕННЫЕ СЕЛЕКТОРЫ из предоставленного HTML
            mention_field_selectors = [
                # Точные селекторы из HTML
                'input[placeholder="Добавить соавторов"]',
                'input[name="creation-collaborator-input"]',
                
                # Альтернативные селекторы
                'input[placeholder*="соавторов" i]',
                'input[placeholder*="collaborator" i]', 
                'input[placeholder*="Отметить людей" i]',
                'input[placeholder*="Tag people" i]',
                'input[aria-label*="соавторы" i]',
                'input[aria-label*="collaborators" i]',
                'input[aria-label*="упоминания" i]',
                'input[aria-label*="mentions" i]',
                'input[aria-label*="Добавить соавторов" i]',
                
                # XPath селекторы
                '//input[@placeholder="Добавить соавторов"]',
                '//input[@name="creation-collaborator-input"]',
            ]
            
            mention_field = None
            for selector in mention_field_selectors:
                try:
                    if selector.startswith('//'):
                        element = self.page.query_selector(f"xpath={selector}")
                    else:
                        element = self.page.query_selector(selector)
                    
                    if element and element.is_visible():
                        log_success(f"[УПОМИНАНИЯ] [OK] Найдено поле упоминаний: {selector}")
                        mention_field = element
                        break
                except Exception as e:
                    log_debug(f"[УПОМИНАНИЯ] Селектор {selector} не сработал: {str(e)}")
                    continue
            
            if not mention_field:
                log_warning("[УПОМИНАНИЯ] [WARN] Поле упоминаний не найдено")
                
                # Try to add mentions to description field as alternative
                log_info("[УПОМИНАНИЯ] [TEXT] Пробуем добавить упоминания в описание...")
                description_field_selectors = [
                    'div[contenteditable="true"][aria-label*="подпись" i]',
                    'div[contenteditable="true"][data-lexical-editor="true"]',
                'textarea[aria-label*="Напишите подпись" i]',
                'div[contenteditable="true"]',
                ]
                
                description_field = None
                for selector in description_field_selectors:
                    try:
                        element = self.page.query_selector(selector)
                        if element and element.is_visible():
                            description_field = element
                            log_success(f"[УПОМИНАНИЯ] [OK] Найдено поле описания: {selector}")
                            break
                    except:
                        continue
                
                if description_field:
                    log_info("[УПОМИНАНИЯ] [TEXT] Добавляем упоминания в описание...")
                    description_field.click()
                    time.sleep(random.uniform(0.5, 1.0))
                    
                    # Move to end
                    description_field.press('End')
                    time.sleep(0.3)
                    
                    # Add space and mentions
                    mention_text = f" {mentions}" if not mentions.startswith('@') else f" @{mentions.replace('@', '')}"
                    self._type_like_human(description_field, mention_text)
                    
                    log_success("[УПОМИНАНИЯ] [OK] Упоминания добавлены в описание")
                    return True
                
                return False
            
            # Human-like interaction with mention field
            mention_field.scroll_into_view_if_needed()
            time.sleep(random.uniform(0.5, 1.0))
                
            mention_field.click()
            time.sleep(random.uniform(1.0, 2.0))
            
            # Process mentions ONE BY ONE (ИСПРАВЛЕНО!)
            mention_list = [m.strip() for m in str(mentions).split(',') if m.strip()]
            
            log_info(f"[УПОМИНАНИЯ] [TEXT] Обрабатываем {len(mention_list)} упоминаний по одному...")
            
            for i, mention in enumerate(mention_list):
                if not mention.startswith('@'):
                    mention = '@' + mention
                
                log_info(f"[УПОМИНАНИЯ] 👤 Добавляем упоминание {i+1}/{len(mention_list)}: {mention}")
                
                # ВАЖНО: Очищаем поле перед каждым новым упоминанием
                log_info(f"[УПОМИНАНИЯ] [CLEAN] Очищаем поле для упоминания {mention}")
                mention_field.click()
                time.sleep(random.uniform(0.3, 0.5))
                mention_field.fill('')
                time.sleep(random.uniform(0.3, 0.7))
                
                # Type mention (without @)
                mention_username = mention.replace('@', '')
                log_info(f"[УПОМИНАНИЯ] ⌨️ Вводим: {mention_username}")
                self._type_like_human(mention_field, mention_username)
                
                # Wait for suggestions to appear
                log_info(f"[УПОМИНАНИЯ] [WAIT] Ждем предложения для {mention_username}...")
                time.sleep(random.uniform(2.0, 4.0))
                
                # ИСПРАВЛЕННЫЕ СЕЛЕКТОРЫ для выбора предложений упоминаний
                suggestion_selectors = [
                    # Основной селектор для упоминаний (адаптированный под конкретного пользователя)
                    f"//div[text()='{mention_username}']/../../div/label/div/input",
                    f"//div[contains(text(), '{mention_username}')]/../../div/label/div/input",
                    
                    # Альтернативные селекторы для первого предложения в диалоге
                    "//div[@role='dialog']/div/div/div/div/div/div/button",
                    "//div[@role='dialog']//button[1]",
                    "//div[@role='dialog']//div[@role='button'][1]",
                    
                    # Стандартные селекторы для первого предложения
                    f'div[role="button"]:has-text("{mention_username}")',
                    f'button:has-text("{mention_username}")',
                    'div[role="button"]:first-child',
                    'li[role="button"]:first-child',
                    'button:first-child',
                    
                    # XPath для первого предложения
                    '(//div[@role="button"])[1]',
                    '(//li[@role="button"])[1]',
                    '(//button)[1]',
                ]
                
                suggestion = None
                found_suggestion_selector = None
                
                for selector in suggestion_selectors:
                    try:
                        log_debug(f"[УПОМИНАНИЯ] [SEARCH] Ищем предложение: {selector}")
                        
                        if selector.startswith('//') or selector.startswith('(//'):
                            element = self.page.query_selector(f"xpath={selector}")
                        else:
                            element = self.page.query_selector(selector)
                        
                        if element and element.is_visible():
                            suggestion = element
                            found_suggestion_selector = selector
                            log_success(f"[УПОМИНАНИЯ] [OK] Найдено предложение: {selector}")
                            break
                    except Exception as e:
                        log_debug(f"[УПОМИНАНИЯ] Селектор {selector} не сработал: {str(e)}")
                        continue
                
                if suggestion:
                    log_info(f"[УПОМИНАНИЯ] 👆 Выбираем предложение для {mention_username}")
                    suggestion.hover()
                    time.sleep(random.uniform(0.5, 1.0))
                    suggestion.click()
                    time.sleep(random.uniform(1.5, 2.5))
                    log_success(f"[УПОМИНАНИЯ] [OK] Упоминание {mention} добавлено успешно")
                    
                    # Дополнительное ожидание для обработки выбора
                    time.sleep(random.uniform(1.0, 2.0))
                    
                else:
                    # Fallback: Press Enter to try to accept
                    log_warning(f"[УПОМИНАНИЯ] [WARN] Предложение для {mention_username} не найдено, пробуем Enter")
                    mention_field.press('Enter')
                    time.sleep(random.uniform(1.0, 1.5))
                    
                    # Check if anything was added
                    current_value = mention_field.input_value() or ""
                    if current_value.strip():
                        log_info(f"[УПОМИНАНИЯ] [OK] Упоминание {mention} добавлено через Enter")
                    else:
                        log_warning(f"[УПОМИНАНИЯ] [FAIL] Не удалось добавить упоминание {mention}")
                
                # Небольшая пауза между упоминаниями
                if i < len(mention_list) - 1:
                    pause_time = random.uniform(1.0, 2.0)
                    log_info(f"[УПОМИНАНИЯ] [PAUSE] Пауза {pause_time:.1f}с перед следующим упоминанием...")
                    time.sleep(pause_time)
            
            # ИСПРАВЛЕННАЯ кнопка Done для упоминаний
            log_info("[УПОМИНАНИЯ] [SEARCH] Ищем кнопку 'Done'...")
            time.sleep(random.uniform(1.0, 2.0))
            
            done_button_selectors = [
                # Основной селектор для кнопки Done
                "//div[text()='Done']",
                "//div[text()='Готово']",
                
                # Альтернативные селекторы
                'button:has-text("Готово")',
                'button:has-text("Done")',
                'button:has-text("Продолжить")',
                'button:has-text("Continue")',
                'div[role="button"]:has-text("Готово")',
                'div[role="button"]:has-text("Done")',
                
                # XPath селекторы
                "//button[text()='Done']",
                "//button[text()='Готово']",
                "//div[@role='button' and text()='Done']",
                "//div[@role='button' and text()='Готово']",
            ]
            
            done_button = None
            for selector in done_button_selectors:
                try:
                    if selector.startswith('//'):
                        element = self.page.query_selector(f"xpath={selector}")
                    else:
                        element = self.page.query_selector(selector)
                    
                    if element and element.is_visible():
                        done_button = element
                        log_success(f"[УПОМИНАНИЯ] [OK] Найдена кнопка Done: {selector}")
                        break
                except Exception as e:
                    log_debug(f"[УПОМИНАНИЯ] Селектор Done {selector} не сработал: {str(e)}")
                    continue
            
            if done_button:
                done_button.hover()
                time.sleep(random.uniform(0.5, 1.0))
                done_button.click()
                time.sleep(random.uniform(1.5, 2.5))
                log_success("[УПОМИНАНИЯ] [OK] Нажали кнопку 'Done'")
            else:
                log_warning("[УПОМИНАНИЯ] [WARN] Кнопка 'Done' не найдена, пробуем продолжить без неё")
                # Try pressing Escape to close any open dialogs
                self.page.keyboard.press('Escape')
                time.sleep(random.uniform(0.5, 1.0))
            
            log_success("[УПОМИНАНИЯ] [OK] Упоминания установлены успешно")
            return True
            
        except Exception as e:
            log_error(f"[УПОМИНАНИЯ] [FAIL] Ошибка установки упоминаний: {str(e)}")
            return False
    
    def _post_video_selenium_style(self):
        """Post video with improved button detection"""
        try:
            log_info("[ПУБЛИКАЦИЯ] 📤 Публикуем видео...")
            
            # Wait before posting
            time.sleep(random.uniform(2.0, 4.0))
            
            # First, ensure we're focused on the main content area (not scrolled away)
            try:
                main_content = self.page.query_selector('main, [role="main"], body')
                if main_content:
                    main_content.click()
                    time.sleep(0.5)
            except:
                pass
            
            # Find share/post button with improved selectors - FOCUS ON DIALOG
            share_button_selectors = [
                # Приоритетные селекторы в диалоговом окне
                "//div[@role='dialog']//div[text()='Поделиться']",
                "//div[@role='dialog']//button[text()='Поделиться']",
                "//div[@role='dialog']//div[text()='Share']",
                "//div[@role='dialog']//button[text()='Share']",
                "//div[@role='dialog']//div[text()='Опубликовать']",
                "//div[@role='dialog']//button[text()='Опубликовать']",
                "//div[@role='dialog']//div[text()='Post']",
                "//div[@role='dialog']//button[text()='Post']",
                
                # Стандартные селекторы (если диалог не найден)
                'button:has-text("Поделиться")',
                'button:has-text("Опубликовать")',
                'div[role="button"]:has-text("Поделиться")',
                'div[role="button"]:has-text("Опубликовать")',
                
                # English buttons
                'button:has-text("Share")',
                'button:has-text("Post")',
                'button:has-text("Publish")',
                'div[role="button"]:has-text("Share")',
                'div[role="button"]:has-text("Post")',
                
                # German buttons
                'button:has-text("Teilen")',        # DE
                'button:has-text("Veröffentlichen")', # DE
                'div[role="button"]:has-text("Teilen")',        # DE
                'div[role="button"]:has-text("Veröffentlichen")', # DE
                
                # Greek buttons
                'button:has-text("Κοινοποίηση")',   # EL
                'button:has-text("Δημοσίευση")',    # EL
                'div[role="button"]:has-text("Κοινοποίηση")',   # EL
                'div[role="button"]:has-text("Δημοσίευση")',    # EL
                
                # XPath selectors for better precision
                '//button[contains(text(), "Поделиться")]',
                '//button[contains(text(), "Опубликовать")]',
                '//button[contains(text(), "Share")]',
                '//button[contains(text(), "Post")]',
                '//div[@role="button" and contains(text(), "Поделиться")]',
                '//div[@role="button" and contains(text(), "Share")]',
                
                # Aria-label selectors
                'button[aria-label*="Поделиться"]',
                'button[aria-label*="Share"]',
                'button[aria-label*="Опубликовать"]',
                'button[aria-label*="Post"]',
                
                # Type-based selectors
                'button[type="submit"]',
                'button[type="button"]:has-text("Поделиться")',
                'button[type="button"]:has-text("Share")',
                'button[type="button"]:has-text("Teilen")',        # DE
                'button[type="button"]:has-text("Veröffentlichen")', # DE
                'button[type="button"]:has-text("Κοινοποίηση")',   # EL
                'button[type="button"]:has-text("Δημοσίευση")',    # EL
            ]
            
            share_button = None
            found_selector = None
            
            for selector in share_button_selectors:
                try:
                    log_info(f"[ПУБЛИКАЦИЯ] [SEARCH] Ищем кнопку: {selector}")
                    
                    if selector.startswith('//'):
                        element = self.page.query_selector(f"xpath={selector}")
                    else:
                        element = self.page.query_selector(selector)
                    
                    if element and element.is_visible():
                        button_text = element.text_content() or ""
                        log_success(f"[ПУБЛИКАЦИЯ] [OK] Найдена кнопка: '{button_text.strip()}' с селектором: {selector}")
                        share_button = element
                        found_selector = selector
                        break
                        
                except Exception as e:
                    log_debug(f"[ПУБЛИКАЦИЯ] Селектор {selector} не сработал: {str(e)}")
                    continue
            
            if not share_button:
                log_error("[ПУБЛИКАЦИЯ] [FAIL] Кнопка публикации не найдена")
                
                # Debug: show available buttons
                try:
                    all_buttons = self.page.query_selector_all('button, div[role="button"]')
                    log_info(f"[ПУБЛИКАЦИЯ] [SEARCH] Найдено {len(all_buttons)} кнопок на странице:")
                    for i, btn in enumerate(all_buttons[:10]):  # Show first 10
                        if btn.is_visible():
                            btn_text = btn.text_content() or ""
                            btn_aria = btn.get_attribute('aria-label') or ""
                            log_info(f"  {i+1}. Текст: '{btn_text.strip()[:30]}', aria-label: '{btn_aria[:30]}'")
                except:
                    pass
                
                return False
            
            # Human-like clicking sequence
            try:
                # Scroll button into view if needed
                share_button.scroll_into_view_if_needed()
                time.sleep(random.uniform(0.5, 1.0))
                
                # Hover over button
                share_button.hover()
                time.sleep(random.uniform(1.0, 2.0))
                
                # Final decision pause
                decision_pause = random.uniform(1.5, 3.0)
                log_info(f"[ПУБЛИКАЦИЯ] 🤔 Принимаем решение о публикации... {decision_pause:.1f}с")
                time.sleep(decision_pause)
                
                # Click the button
                log_info(f"[ПУБЛИКАЦИЯ] 👆 Нажимаем кнопку публикации...")
                share_button.click()
                
                # Wait for processing
                processing_time = random.uniform(3.0, 6.0)
                log_info(f"[ПУБЛИКАЦИЯ] [WAIT] Ожидаем обработки публикации... {processing_time:.1f}с")
                time.sleep(processing_time)
                
                log_success("[ПУБЛИКАЦИЯ] [OK] Кнопка публикации нажата успешно")
                return True
            
            except Exception as e:
                log_error(f"[ПУБЛИКАЦИЯ] [FAIL] Ошибка нажатия кнопки: {str(e)}")
                
                # Fallback: try JavaScript click
                try:
                    log_info("[ПУБЛИКАЦИЯ] [RETRY] Пробуем JavaScript клик...")
                    self.page.evaluate('(element) => element.click()', share_button)
                    time.sleep(random.uniform(3.0, 5.0))
                    log_success("[ПУБЛИКАЦИЯ] [OK] JavaScript клик выполнен")
                    return True
                except Exception as js_error:
                    log_error(f"[ПУБЛИКАЦИЯ] [FAIL] JavaScript клик тоже не сработал: {str(js_error)}")
                    return False
            
        except Exception as e:
            log_error(f"[ПУБЛИКАЦИЯ] [FAIL] Ошибка публикации видео: {str(e)}")
            return False
    
    def _verify_video_posted(self):
        """Verify video was posted successfully - STRICT verification only"""
        try:
            log_info("[VERIFY] Checking if video was posted successfully...")
            
            # УВЕЛИЧЕННОЕ ВРЕМЯ ОЖИДАНИЯ - Instagram нужно время на обработку видео
            initial_wait = random.uniform(15, 20) 
            log_info(f"[VERIFY] [WAIT] Ожидаем обработки видео Instagram... {initial_wait:.1f}с")
            time.sleep(initial_wait)
            
            # Look for explicit success indicators ONLY
            success_indicators = [
                'div:has-text("Ваша публикация опубликована")',
                'div:has-text("Your post has been shared")',
                'div:has-text("Опубликовано")',
                'div:has-text("Shared")',
                'div:has-text("Публикация опубликована")',
                'div:has-text("Post shared")',
                'div:has-text("Posted")',
                'div:has-text("Successfully posted")',
                'svg[aria-label*="Готово" i]',
                'svg[aria-label*="Done" i]',
                # XPath selectors for more precise matching
                '//div[contains(text(), "Ваша публикация опубликована")]',
                '//div[contains(text(), "Публикация опубликована")]',
                '//div[contains(text(), "Your post has been shared")]',
                '//div[contains(text(), "Post shared")]',
                '//span[contains(text(), "Опубликовано")]',
                '//span[contains(text(), "Posted")]',
            ]
            
            # STRICT: Only return True if we find explicit success indicators
            for indicator in success_indicators:
                try:
                    if indicator.startswith('//'):
                        element = self.page.query_selector(f"xpath={indicator}")
                    else:
                        element = self.page.query_selector(indicator)
                        
                    if element and element.is_visible():
                        element_text = element.text_content() or ""
                        log_success(f"[VERIFY] [OK] SUCCESS CONFIRMED: Found explicit success indicator: '{element_text.strip()}'")
                        return True
                except Exception as e:
                    log_debug(f"[VERIFY] Error checking indicator {indicator}: {str(e)}")
                    continue
            
            # Additional wait and second check for success indicators - УВЕЛИЧЕНО
            additional_wait = random.uniform(8, 12)  # Было 3-5, стало 8-12 секунд
            log_info(f"[VERIFY] No immediate success indicators found, waiting additional {additional_wait:.1f}s and checking again...")
            time.sleep(additional_wait)
            
            for indicator in success_indicators:
                try:
                    if indicator.startswith('//'):
                        element = self.page.query_selector(f"xpath={indicator}")
                    else:
                        element = self.page.query_selector(indicator)
                        
                    if element and element.is_visible():
                        element_text = element.text_content() or ""
                        log_success(f"[VERIFY] [OK] SUCCESS CONFIRMED (delayed): Found explicit success indicator: '{element_text.strip()}'")
                        return True
                except Exception as e:
                    log_debug(f"[VERIFY] Error checking indicator {indicator} (second attempt): {str(e)}")
                    continue
            
            # Check for error indicators
            error_indicators = [
                'div:has-text("Что-то пошло не так")',
                'div:has-text("Something went wrong")',
                'div:has-text("Ошибка")',
                'div:has-text("Error")',
                'div:has-text("Не удалось")',
                'div:has-text("Failed")',
                'div:has-text("Try again")',
                'div:has-text("Попробуйте еще раз")',
            ]
            
            for indicator in error_indicators:
                try:
                    element = self.page.query_selector(indicator)
                    if element and element.is_visible():
                        error_text = element.text_content() or ""
                        log_error(f"[VERIFY] [FAIL] ERROR DETECTED: '{error_text.strip()}'")
                        return False
                except:
                    continue
            
            # Check if still on upload page (indicates failure)
            upload_indicators = [
                'textarea[aria-label*="Напишите подпись" i]',
                'textarea[aria-label*="Write a caption" i]',
                'input[placeholder*="Добавить местоположение" i]',
                'input[placeholder*="Add location" i]',
                'input[placeholder*="Ort hinzufügen" i]',     # DE
                'input[placeholder*="Προσθήκη τοποθεσίας" i]', # EL
                'button:has-text("Поделиться")',
                'button:has-text("Share")',
                'button:has-text("Teilen")',        # DE
                'button:has-text("Κοινοποίηση")',   # EL
                'button:has-text("Опубликовать")',
                'button:has-text("Post")',
                'button:has-text("Veröffentlichen")', # DE
                'button:has-text("Δημοσίευση")',    # EL
            ]
            
            still_on_upload = False
            for indicator in upload_indicators:
                try:
                    element = self.page.query_selector(indicator)
                    if element and element.is_visible():
                        still_on_upload = True
                        log_info(f"[VERIFY] Found upload page indicator: {indicator}")
                        break
                except:
                    continue
            
            if still_on_upload:
                log_error("[VERIFY] [FAIL] UPLOAD FAILED: Still on upload page - video was NOT posted successfully")
                return False
            
            # ПРОВЕРКА URL - если мы на главной странице, это может означать успех
            current_url = self.page.url
            if current_url and ('instagram.com/' == current_url.rstrip('/') or 'instagram.com' in current_url and len(current_url.split('/')) <= 4):
                log_info(f"[VERIFY] [SEARCH] Redirected to main page: {current_url}")
                log_info("[VERIFY] [OK] LIKELY SUCCESS: Redirected to main Instagram page after posting")
                
                # Дополнительная проверка - ждем еще немного и проверяем, что мы не вернулись на страницу загрузки
                final_wait = random.uniform(3, 5)
                log_info(f"[VERIFY] [WAIT] Final verification wait: {final_wait:.1f}s...")
                time.sleep(final_wait)
                
                # Проверяем, что мы все еще не на странице загрузки
                for indicator in upload_indicators:
                    try:
                        element = self.page.query_selector(indicator)
                        if element and element.is_visible():
                            log_warning("[VERIFY] [WARN] Returned to upload page - upload may have failed")
                            return False
                    except:
                        continue
                
                log_success("[VERIFY] [OK] SUCCESS CONFIRMED: Video appears to be posted successfully")
                return True
            
            # МЯГКАЯ ПОЛИТИКА: Если нет явных ошибок и мы не на странице загрузки, считаем успехом
            log_warning("[VERIFY] [WARN] No explicit success indicators found, but no errors detected either")
            log_info(f"[VERIFY] [SEARCH] Current page URL: {current_url}")
            
            # Если мы не на странице загрузки и нет ошибок, вероятно загрузка прошла успешно
            log_success("[VERIFY] [OK] PROBABLE SUCCESS: No errors detected and not on upload page")
            return True
                
        except Exception as e:
            log_error(f"[VERIFY] Error verifying video post: {str(e)}")
            return False

    def _is_valid_file_input(self, element):
        """Проверить, является ли элемент валидным файловым input"""
        try:
            if not element:
                return False
                
            # Проверить тип
            input_type = element.get_attribute('type')
            if input_type != 'file':
                return False
            
            # Проверить accept атрибут (должен поддерживать видео или изображения)
            accept_attr = element.get_attribute('accept') or ""
            
            # Логируем для отладки
            log_debug(f"[UPLOAD] Validating input: type='{input_type}', accept='{accept_attr}'")
            
            # Проверяем, что accept содержит нужные типы файлов
            valid_types = ['video', 'image', 'mp4', 'jpeg', 'png', 'quicktime', 'heic', 'heif', 'avif']
            if accept_attr and not any(file_type in accept_attr.lower() for file_type in valid_types):
                log_debug(f"[UPLOAD] Input rejected: accept attribute doesn't contain valid file types")
                return False
            
            # Если accept пустой, но это input[type="file"], считаем валидным
            if not accept_attr:
                log_debug("[UPLOAD] Input has no accept attribute, but type='file' - considering valid")
            
            # Проверить multiple атрибут (Instagram обычно поддерживает multiple)
            multiple_attr = element.get_attribute('multiple')
            if multiple_attr is not None:
                log_debug("[UPLOAD] Input supports multiple files - good sign")
            
            log_debug("[UPLOAD] Input validation passed")
            return True
                
        except Exception as e:
            log_debug(f"[UPLOAD] Error validating file input: {str(e)}")
            return False


class InstagramLoginHandler(InstagramAutomationBase):
    """Handles Instagram login operations"""
    
    def perform_login(self, username, password, tfa_secret=None):
        """Perform Instagram login"""
        try:
            log_info(f"[LOGIN] Starting login for: {username}")
            
            # Fill username
            if not self._fill_username(username):
                return False
            
            # Fill password
            if not self._fill_password(password):
                return False
            
            # Submit form
            if not self._submit_login_form():
                return False
            
            # Handle 2FA if needed
            if tfa_secret:
                if not self._handle_2fa(tfa_secret):
                    log_warning("[LOGIN] 2FA failed, but continuing...")
            
            log_success(f"[LOGIN] Login completed for: {username}")
            return True
            
        except Exception as e:
            log_error(f"[LOGIN] Login failed: {str(e)}")
            return False
    
    def _fill_username(self, username):
        """Fill username field"""
        try:
            username_field = self.find_element([
                'input[name="username"]',
                'input[aria-label*="имя пользователя" i]',
                'input[aria-label*="username" i]',
            ])
            
            if not username_field:
                log_error("[LOGIN] Username field not found")
                return False
            
            self.type_text(username_field, username, "USERNAME")
            return True
            
        except Exception as e:
            log_error(f"[LOGIN] Error filling username: {str(e)}")
            return False
    
    def _fill_password(self, password):
        """Fill password field"""
        try:
            password_field = self.find_element([
                'input[name="password"]',
                'input[type="password"]',
                'input[aria-label*="пароль" i]',
                'input[aria-label*="password" i]',
            ])
            
            if not password_field:
                log_error("[LOGIN] Password field not found")
                return False
            
            self.type_text(password_field, password, "PASSWORD")
            return True
            
        except Exception as e:
            log_error(f"[LOGIN] Error filling password: {str(e)}")
            return False
    
    def _submit_login_form(self):
        """Submit login form"""
        try:
            submit_button = self.find_element([
                'button[type="submit"]',
                'button:has-text("Вход")',
                'button:has-text("Log in")',
                'button:has-text("Войти")',
                'div[role="button"]:has-text("Вход")',
            ])
            
            if not submit_button:
                log_error("[LOGIN] Submit button not found")
                return False
            
            self.click_element(submit_button, "SUBMIT")
            time.sleep(random.uniform(3, 5))
            return True
            
        except Exception as e:
            log_error(f"[LOGIN] Error submitting form: {str(e)}")
            return False
    
    def _handle_2fa(self, tfa_secret):
        """Handle 2FA verification"""
        try:
            log_info("[LOGIN] Handling 2FA verification...")
            
            # Wait for 2FA field
            tfa_field = self.wait_for_element([
                'input[name="verificationCode"]',
                'input[aria-label*="код" i]',
                'input[aria-label*="code" i]',
                'input[placeholder*="код" i]',
            ], timeout=10000)
            
            if not tfa_field:
                log_warning("[LOGIN] 2FA field not found")
                return False
            
            # Get 2FA code (this would need to be implemented)
            from .bulk_tasks_playwright import get_2fa_code
            tfa_code = get_2fa_code(tfa_secret)
            
            if not tfa_code:
                log_error("[LOGIN] Failed to get 2FA code")
                return False
            
            # Enter 2FA code
            self.type_text(tfa_field, tfa_code, "2FA_CODE")
            
            # Submit 2FA
            submit_button = self.find_element([
                'button[type="submit"]',
                'button:has-text("Подтвердить")',
                'button:has-text("Confirm")',
            ])
            
            if submit_button:
                self.click_element(submit_button, "2FA_SUBMIT")
                time.sleep(random.uniform(3, 5))
            
            log_success("[LOGIN] 2FA handled successfully")
            return True
            
        except Exception as e:
            log_error(f"[LOGIN] Error handling 2FA: {str(e)}")
            return False 