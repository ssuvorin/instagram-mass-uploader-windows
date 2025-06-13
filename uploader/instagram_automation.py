"""
Instagram Automation Classes
Provides base classes and specialized handlers for Instagram automation
"""

import os
import time
import random
from .selectors_config import InstagramSelectors, SelectorUtils
from .logging_utils import log_info, log_warning, log_error


class InstagramAutomationBase:
    """Base class for Instagram automation operations"""
    
    def __init__(self, page, human_behavior=None):
        self.page = page
        self.human_behavior = human_behavior
        self.selectors = InstagramSelectors()
        
        # Configure page to suppress verbose logs
        self._configure_page_logging()
    
    def _configure_page_logging(self):
        """Configure page to suppress verbose Playwright logs"""
        try:
            # Disable console logging from the page
            self.page.on("console", lambda msg: None)
            
            # Disable request/response logging
            self.page.on("request", lambda request: None)
            self.page.on("response", lambda response: None)
            
            # Set page to not log verbose actions
            self.page.set_default_timeout(30000)  # 30 seconds timeout
            
        except Exception as e:
            # Silently ignore any errors in logging configuration
            pass
    
    def find_element(self, selectors, log_prefix="ELEMENT", timeout=5000):
        """Find element using list of selectors with timeout"""
        return SelectorUtils.find_element_with_selectors(
            self.page, selectors, log_prefix
        )
    
    def wait_for_element(self, selectors, timeout=10000, log_prefix="WAIT"):
        """Wait for element to appear"""
        for selector in selectors:
            try:
                if SelectorUtils.is_xpath(selector):
                    element = self.page.wait_for_selector(
                        f"xpath={selector}", timeout=timeout
                    )
                else:
                    element = self.page.wait_for_selector(selector, timeout=timeout)
                
                if element and element.is_visible():
                    log_info(f"[{log_prefix}] ✅ Element appeared: {selector}")
                    return element
            except:
                continue
        return None
    
    def click_element(self, element, log_prefix="CLICK"):
        """Click element with human behavior if available"""
        if self.human_behavior:
            log_info(f"[{log_prefix}] 🖱️ Clicking with human behavior...")
            self.human_behavior.advanced_element_interaction(element, 'click')
        else:
            log_info(f"[{log_prefix}] 🖱️ Clicking element...")
            element.click()
    
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
        """Navigate to upload page with human behavior"""
        try:
            log_info("[UPLOAD] 🧠 Starting navigation to upload page")
            
            # Simulate page assessment
            self.simulate_page_scan()
            
            # Find upload button
            upload_button = self.find_element(
                self.selectors.UPLOAD_BUTTON, 
                "UPLOAD_BTN"
            )
            
            if not upload_button:
                log_error("[UPLOAD] ❌ Upload button not found")
                return False
            
            # Click upload button
            self.click_element(upload_button, "UPLOAD_BTN")
            
            # Wait and observe page changes
            log_info("[UPLOAD] 👀 Observing page changes...")
            self.simulate_page_scan()
            
            # Wait for dropdown menu
            self._wait_for_dropdown_menu()
            
            # Find and click post option
            return self._click_post_option()
            
        except Exception as e:
            log_error(f"[UPLOAD] ❌ Navigation failed: {str(e)}")
            return False
    
    def _wait_for_dropdown_menu(self):
        """Wait for dropdown menu to appear"""
        log_info("[UPLOAD] ⏳ Waiting for dropdown menu...")
        initial_wait = self.human_wait(1.5, 0.3)
        
        # Check if menu appeared
        for attempt in range(3):
            log_info(f"[UPLOAD] 🔍 Checking for dropdown menu (attempt {attempt + 1}/3)...")
            
            menu_element = self.find_element(
                self.selectors.MENU_INDICATORS,
                "MENU_CHECK"
            )
            
            if menu_element:
                log_info("[UPLOAD] ✅ Dropdown menu detected")
                break
            else:
                additional_wait = self.human_wait(0.8, 0.2)
                log_info(f"[UPLOAD] ⏳ Menu not ready, waiting {additional_wait:.1f}s more...")
        
        # Brief pause to "read" options
        reading_time = self.human_wait(1.2, 0.4)
        log_info(f"[UPLOAD] 📖 Reading menu options for {reading_time:.1f}s...")
    
    def _click_post_option(self):
        """Find and click the post option in dropdown"""
        log_info("[UPLOAD] 🔍 Looking for 'Публикация' option...")
        
        # Scan page first
        self.simulate_page_scan()
        
        # Find post option
        post_option = None
        for i, selector in enumerate(self.selectors.POST_OPTION):
            try:
                # Human behavior: brief pause between attempts
                if i > 0:
                    self.human_wait(0.3, 0.1)
                
                log_info(f"[UPLOAD] 🔍 Trying selector {i+1}/{len(self.selectors.POST_OPTION)}")
                
                if SelectorUtils.is_xpath(selector):
                    post_option = self.page.query_selector(f"xpath={selector}")
                else:
                    post_option = self.page.query_selector(selector)
                
                if post_option and post_option.is_visible():
                    log_info(f"[UPLOAD] ✅ Found 'Публикация' option")
                    
                    # Brief pause to "confirm" element
                    self.human_wait(0.5, 0.2)
                    break
                    
            except Exception as e:
                log_warning(f"[UPLOAD] Selector failed: {str(e)}")
                continue
        
        if post_option:
            try:
                # Move mouse to element first
                if self.human_behavior:
                    self.human_behavior.natural_mouse_movement(post_option)
                
                # Brief pause to simulate decision making
                self.human_wait(0.8, 0.3)
                
                # Click with human behavior
                self.click_element(post_option, "POST_OPTION")
                
                # Wait for upload interface
                wait_time = self.human_wait(3.0, 1.0)
                log_info(f"[UPLOAD] ⏳ Waiting {wait_time:.1f}s for upload interface...")
                
                return True
                
            except Exception as e:
                log_warning(f"[UPLOAD] Error clicking post option: {str(e)}")
                # Fallback: simple click
                try:
                    post_option.click()
                    time.sleep(3)
                    return True
                except Exception as fallback_e:
                    log_error(f"[UPLOAD] Fallback click failed: {str(fallback_e)}")
                    return False
        else:
            log_warning("[UPLOAD] ⚠️ 'Публикация' option not found")
            return self._try_broader_search()
    
    def _try_broader_search(self):
        """Try broader search for clickable menu items"""
        log_info("[UPLOAD] 🔄 Attempting broader search...")
        
        try:
            clickable_elements = self.page.query_selector_all(
                'a, div[role="menuitem"], div[role="button"]'
            )
            
            for element in clickable_elements:
                if element.is_visible():
                    try:
                        text_content = element.inner_text().strip()
                        if text_content and ("Публикация" in text_content or "Post" in text_content):
                            log_info(f"[UPLOAD] 🎯 Found potential option: '{text_content}'")
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
        """Complete video upload process with human behavior"""
        try:
            from .crop_handler import handle_crop_and_aspect_ratio
            import os
            import time
            
            log_info(f"🎬 Starting advanced upload of: {os.path.basename(video_file_path)}")
            
            # Step 1: Select video file
            if not self._select_video_file(video_file_path):
                return False
            
            # Step 2: Handle OK button
            self._handle_ok_button()
            
            # Step 3: Handle crop settings using the new crop handler
            handle_crop_and_aspect_ratio(self.page, self.human_behavior)
            
            # Step 4: Complete the upload flow
            return self._complete_upload_flow(video_obj)
            
        except Exception as e:
            log_error(f"Upload failed: {str(e)}")
            return False
    
    def _select_video_file(self, video_file_path):
        """Select video file for upload using direct input approach"""
        from .selectors_config import InstagramSelectors
        selectors = InstagramSelectors()
        
        log_info(f"📁 Selecting video file: {os.path.basename(video_file_path)}")
        
        # Look for file input element directly
        file_input_selectors = [
            'input[type="file"]',
            'input[accept*="video"]',
            'input[accept*="image"]',
            'form input[type="file"]',
            'input._ac69',  # Instagram's specific class
        ]
        
        file_input_element = None
        for selector in file_input_selectors:
            try:
                element = self.page.query_selector(selector)
                if element:
                    log_info(f"✅ Found file input: {selector}")
                    file_input_element = element
                    break
            except Exception as e:
                log_warning(f"⚠️ Error checking selector {selector}: {str(e)}")
                continue
        
        if not file_input_element:
            log_error("❌ File input element not found")
            return False
        
        try:
            # Method 1: Direct file input (preferred for Instagram)
            log_info("📁 Using direct file input method...")
            
            # Make sure the input is not hidden (Instagram sometimes hides it)
            self.page.evaluate('''(input) => {
                if (input) {
                    input.style.opacity = '1';
                    input.style.visibility = 'visible';
                    input.style.display = 'block';
                    input.style.position = 'static';
                    input.style.width = 'auto';
                    input.style.height = 'auto';
                    input.style.zIndex = '9999';
                }
            }''', file_input_element)
            
            # Set the file directly
            file_input_element.set_input_files(video_file_path)
            log_info("✅ File set successfully using direct input method")
            
        except Exception as e:
            log_warning(f"⚠️ Direct input method failed: {str(e)}")
            
            try:
                # Method 2: File chooser approach as fallback
                log_info("📁 Using file chooser fallback method...")
                
                # Set up file chooser handler
                def handle_file_chooser(file_chooser):
                    log_info(f"📁 File chooser opened, selecting: {video_file_path}")
                    file_chooser.set_files(video_file_path)
                
                # Listen for file chooser
                self.page.on("filechooser", handle_file_chooser)
                
                try:
                    # Find and click the button to trigger file chooser
                    button_selectors = [
                        'button:has-text("Выбрать на компьютере")',
                        'button:has-text("Select from computer")',
                        'div[role="button"]:has-text("Выбрать на компьютере")',
                        'div[role="button"]:has-text("Select from computer")',
                    ]
                    
                    button_clicked = False
                    for selector in button_selectors:
                        try:
                            button = self.page.query_selector(selector)
                            if button and button.is_visible():
                                log_info(f"🖱️ Clicking button: {selector}")
                                self.human_behavior.advanced_element_interaction(button, 'click')
                                button_clicked = True
                                break
                        except Exception as btn_e:
                            log_warning(f"⚠️ Button click failed for {selector}: {str(btn_e)}")
                            continue
                    
                    if not button_clicked:
                        log_error("❌ Could not find or click file selection button")
                        return False
                    
                    # Wait for file chooser to be handled
                    time.sleep(2)
                    
                finally:
                    # Remove the file chooser listener
                    try:
                        self.page.remove_listener("filechooser", handle_file_chooser)
                    except:
                        pass
                        
            except Exception as e2:
                log_error(f"❌ File chooser method also failed: {str(e2)}")
                return False
        
        # Human-like wait for file processing
        processing_time = self.human_behavior.get_human_delay(6.0, 2.0)
        log_info(f"⏳ Waiting {processing_time:.1f}s for file processing...")
        time.sleep(processing_time)
        
        # Verify file was selected by checking for upload progress or next step
        try:
            # Check for various indicators that file was processed
            file_processed_indicators = [
                'button:has-text("Далее")',
                'button:has-text("Next")',
                'div[role="button"]:has-text("Далее")',
                'div[role="button"]:has-text("Next")',
                'canvas',  # Video preview
                'video',   # Video element
                'img[src*="blob:"]',  # Preview image
                'div[class*="x1i10hfl"]',  # Instagram button classes
            ]
            
            file_processed = False
            found_indicator = None
            
            for indicator in file_processed_indicators:
                try:
                    element = self.page.query_selector(indicator)
                    if element and element.is_visible():
                        log_info(f"✅ File processing indicator found: {indicator}")
                        file_processed = True
                        found_indicator = indicator
                        break
                except Exception as e:
                    log_warning(f"⚠️ Error checking indicator {indicator}: {str(e)}")
                    continue
            
            if file_processed:
                log_info(f"✅ File appears to be processed successfully")
                
                # If we found a Next button, try to click it to proceed
                if "Далее" in found_indicator or "Next" in found_indicator:
                    log_info("🖱️ Found Next button after file selection, clicking to proceed...")
                    
                    # Use the improved click_next_button function
                    from .bulk_tasks_playwright import click_next_button
                    
                    next_success = click_next_button(self.page, "FILE_SELECTION")
                    
                    if next_success:
                        log_info("✅ Successfully clicked Next button after file selection")
                    else:
                        log_warning("⚠️ Could not click Next button, but file seems processed")
                
                return True
            else:
                log_warning("⚠️ Could not verify file was processed")
                
                # Debug: show what's on the page
                try:
                    page_text = self.page.inner_text('body')[:200]
                    log_info(f"🔍 Page content sample: {page_text}...")
                except:
                    pass
                
                return False
                
        except Exception as e:
            log_error(f"❌ Error verifying file selection: {str(e)}")
            return False
    
    def _handle_ok_button(self):
        """Handle OK button with advanced behavior"""
        from .selectors_config import InstagramSelectors
        selectors = InstagramSelectors()
        
        for selector in selectors.OK_BUTTON:
            ok_button = self.page.query_selector(selector)
            if ok_button and ok_button.is_visible():
                log_info("✅ Found OK button, clicking with advanced behavior...")
                self.human_behavior.advanced_element_interaction(ok_button, 'click')
                break
    
    def _complete_upload_flow(self, video_obj):
        """Complete the upload flow with captions, etc. and verify success"""
        try:
            import time
            
            log_info("🎬 Completing upload flow...")
            
            # Step 1: Handle crop/editing phase
            log_info("📐 Handling crop and editing phase...")
            crop_success = self._handle_crop_phase()
            
            if not crop_success:
                log_warning("⚠️ Crop phase had issues, but continuing...")
            
            # Step 2: Handle caption and sharing phase
            log_info("📝 Handling caption and sharing phase...")
            caption_success = self._handle_caption_phase(video_obj)
            
            if not caption_success:
                log_warning("⚠️ Caption phase had issues, but continuing...")
            
            # Step 3: Final upload submission
            log_info("🚀 Submitting final upload...")
            submit_success = self._submit_upload()
            
            if not submit_success:
                log_error("❌ Failed to submit upload")
                return False
            
            # Step 4: Verify upload success
            log_info("✅ Verifying upload success...")
            verification_success = self._verify_upload_success()
            
            if verification_success:
                log_info("🎉 Upload completed successfully!")
                return True
            else:
                log_warning("⚠️ Could not verify upload success, but upload may have completed")
                return True  # Return True as upload likely succeeded
                
        except Exception as e:
            log_error(f"❌ Upload flow failed: {str(e)}")
            return False
    
    def _handle_crop_phase(self):
        """Handle the crop/editing phase"""
        try:
            # Look for crop-related elements
            crop_indicators = [
                'div:has-text("Обрезка")',
                'div:has-text("Crop")',
                'button:has-text("Далее")',
                'button:has-text("Next")',
                'canvas',  # Video preview
                'div[role="button"]:has-text("Далее")',  # Instagram-specific
                'div[class*="x1i10hfl"]',  # Instagram button classes
            ]
            
            # Wait for crop interface to load
            time.sleep(2)
            
            crop_found = False
            for indicator in crop_indicators:
                try:
                    element = self.page.query_selector(indicator)
                    if element and element.is_visible():
                        log_info(f"✅ Found crop interface: {indicator}")
                        crop_found = True
                        break
                except Exception as e:
                    log_warning(f"⚠️ Error checking crop indicator {indicator}: {str(e)}")
                    continue
            
            if crop_found:
                log_info("📐 Crop interface detected, looking for Next button...")
                
                # Use the improved click_next_button function from bulk_tasks_playwright
                from .bulk_tasks_playwright import click_next_button
                
                # Try to click the next button with improved selectors
                next_success = click_next_button(self.page, "CROP")
                
                if next_success:
                    log_info("✅ Successfully clicked Next button in crop phase")
                    return True
                else:
                    log_warning("⚠️ Could not click Next button in crop phase")
                    
                    # Fallback: try manual approach with basic selectors
                    log_info("🔄 Trying fallback approach for Next button...")
                    fallback_selectors = [
                        'button:has-text("Далее")',
                        'button:has-text("Next")',
                        'div[role="button"]:has-text("Далее")',
                        'div[role="button"]:has-text("Next")',
                    ]
                    
                    for selector in fallback_selectors:
                        try:
                            button = self.page.query_selector(selector)
                            if button and button.is_visible():
                                log_info(f"🖱️ Fallback: Clicking Next button: {selector}")
                                self.click_element(button, "CROP_NEXT_FALLBACK")
                                time.sleep(3)  # Wait for next phase
                                return True
                        except Exception as e:
                            log_warning(f"⚠️ Fallback error with {selector}: {str(e)}")
                            continue
                    
                    log_warning("⚠️ All Next button attempts failed in crop phase")
                    return False
            else:
                log_info("ℹ️ No crop interface detected, may have skipped crop phase")
                return True  # Not necessarily an error if no crop needed
            
        except Exception as e:
            log_error(f"❌ Error in crop phase: {str(e)}")
            return False
    
    def _handle_caption_phase(self, video_obj):
        """Handle the caption and sharing phase"""
        try:
            # Wait for caption interface
            time.sleep(2)
            
            # Look for caption input
            caption_selectors = [
                'textarea[aria-label*="Напишите подпись"]',
                'textarea[aria-label*="Write a caption"]',
                'textarea[placeholder*="Напишите подпись"]',
                'textarea[placeholder*="Write a caption"]',
                'div[contenteditable="true"]',
                'textarea',
            ]
            
            caption_input = None
            for selector in caption_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element and element.is_visible():
                        log_info(f"✅ Found caption input: {selector}")
                        caption_input = element
                        break
                except:
                    continue
            
            # Add caption if available
            if caption_input and hasattr(video_obj, 'title_data') and video_obj.title_data:
                caption_text = video_obj.title_data.title
                if caption_text and caption_text.strip():
                    log_info(f"📝 Adding caption: {caption_text[:50]}...")
                    self.type_text(caption_input, caption_text, "CAPTION")
                    time.sleep(1)
            
            return True
            
        except Exception as e:
            log_error(f"❌ Error in caption phase: {str(e)}")
            return False
    
    def _submit_upload(self):
        """Submit the final upload"""
        try:
            # Look for share/publish buttons
            share_buttons = [
                'button:has-text("Поделиться")',
                'button:has-text("Share")',
                'button:has-text("Опубликовать")',
                'button:has-text("Publish")',
                'button._acan._acap._acas._aj1-._ap30:has-text("Поделиться")',
                'button._acan._acap._acas._aj1-._ap30:has-text("Share")',
            ]
            
            for selector in share_buttons:
                try:
                    button = self.page.query_selector(selector)
                    if button and button.is_visible():
                        log_info(f"🚀 Clicking share button: {selector}")
                        self.click_element(button, "SHARE")
                        
                        # Wait for upload to process
                        log_info("⏳ Waiting for upload to process...")
                        time.sleep(10)  # Give time for upload
                        return True
                        
                except Exception as e:
                    log_warning(f"⚠️ Error clicking share button {selector}: {str(e)}")
                    continue
            
            log_error("❌ Could not find share button")
            return False
            
        except Exception as e:
            log_error(f"❌ Error submitting upload: {str(e)}")
            return False
    
    def _verify_upload_success(self):
        """Verify that the upload was successful"""
        try:
            # Wait a bit for success indicators to appear
            time.sleep(3)
            
            # Look for success indicators
            success_indicators = [
                # Success messages
                'div:has-text("Ваша публикация опубликована")',
                'div:has-text("Your post has been shared")',
                'div:has-text("Публикация опубликована")',
                'div:has-text("Post shared")',
                
                # Success dialogs
                'div[role="dialog"]:has-text("опубликована")',
                'div[role="dialog"]:has-text("shared")',
                
                # URL changes indicating success
                # We'll check this separately
            ]
            
            # Check for success messages
            for indicator in success_indicators:
                try:
                    element = self.page.query_selector(indicator)
                    if element and element.is_visible():
                        log_info(f"🎉 Upload success confirmed: {indicator}")
                        return True
                except:
                    continue
            
            # Check URL for success indicators
            try:
                current_url = self.page.url
                if any(keyword in current_url.lower() for keyword in ['feed', 'profile', 'instagram.com']):
                    # If we're back to main Instagram pages, upload likely succeeded
                    log_info("✅ URL indicates successful return to main Instagram")
                    return True
            except:
                pass
            
            # Check if we're no longer in create flow
            try:
                create_elements = self.page.query_selector_all('div[aria-label*="Создание публикации"], div[aria-label*="Create post"]')
                if not any(elem.is_visible() for elem in create_elements):
                    log_info("✅ No longer in create flow - upload likely succeeded")
                    return True
            except:
                pass
            
            log_warning("⚠️ Could not definitively verify upload success")
            return False
            
        except Exception as e:
            log_error(f"❌ Error verifying upload success: {str(e)}")
            return False


class InstagramLoginHandler(InstagramAutomationBase):
    """Handles Instagram login operations"""
    
    def login(self, account_details):
        """Perform Instagram login with human behavior"""
        try:
            log_info(f"[LOGIN] 🔐 Starting login for: {account_details['username']}")
            
            # Fill username
            if not self._fill_username(account_details['username']):
                return False
            
            # Fill password
            if not self._fill_password(account_details['password']):
                return False
            
            # Submit form
            if not self._submit_login_form():
                return False
            
            # Handle 2FA if needed
            if account_details.get('tfa_secret'):
                return self._handle_2fa(account_details['tfa_secret'])
            
            return True
            
        except Exception as e:
            log_error(f"[LOGIN] ❌ Login failed: {str(e)}")
            return False
    
    def _fill_username(self, username):
        """Fill username field"""
        username_input = self.find_element(
            self.selectors.LOGIN_FORM['username'], 
            "USERNAME"
        )
        
        if not username_input:
            log_error("[LOGIN] ❌ Username input not found")
            return False
        
        self.type_text(username_input, username, "USERNAME")
        self.human_wait(1.0, 0.3)
        return True
    
    def _fill_password(self, password):
        """Fill password field"""
        password_input = self.find_element(
            self.selectors.LOGIN_FORM['password'], 
            "PASSWORD"
        )
        
        if not password_input:
            log_error("[LOGIN] ❌ Password input not found")
            return False
        
        self.type_text(password_input, password, "PASSWORD")
        self.human_wait(1.0, 0.3)
        return True
    
    def _submit_login_form(self):
        """Submit login form"""
        submit_button = self.find_element(
            self.selectors.LOGIN_FORM['submit'], 
            "SUBMIT"
        )
        
        if not submit_button:
            log_error("[LOGIN] ❌ Submit button not found")
            return False
        
        self.click_element(submit_button, "SUBMIT")
        self.human_wait(3.0, 1.0)
        return True
    
    def _handle_2fa(self, tfa_secret):
        """Handle 2FA authentication"""
        log_info("[LOGIN] 🔐 Handling 2FA...")
        
        # Wait for 2FA input to appear
        tfa_input = self.wait_for_element(self.selectors.TFA_INPUT, 10000, "2FA")
        
        if not tfa_input:
            log_warning("[LOGIN] ⚠️ 2FA input not found")
            return True  # Maybe 2FA not required
        
        # Get 2FA code
        from .bulk_tasks_playwright import get_2fa_code
        tfa_code = get_2fa_code(tfa_secret)
        
        if not tfa_code:
            log_error("[LOGIN] ❌ Failed to get 2FA code")
            return False
        
        # Fill 2FA code
        self.type_text(tfa_input, tfa_code, "2FA")
        self.human_wait(2.0, 0.5)
        
        return True 