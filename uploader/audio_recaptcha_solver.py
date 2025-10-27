import os
import urllib.request
import random
import pydub
import speech_recognition
import asyncio
import time
import logging
import tempfile
import aiohttp
import aiofiles
from typing import Optional, List
from playwright.async_api import Page

# Import centralized constants
from .recaptcha_constants import (
    AUDIO_CHALLENGE_SELECTORS,
    IMAGE_CHALLENGE_SELECTORS,
    BOT_DETECTION_SELECTORS,
    LOGIN_PAGE_SELECTORS,
    CAPTCHA_SOLUTION_SELECTORS,
    SUPPORTED_LANGUAGES,
    TIMEOUTS,
    AUDIO_SETTINGS,
    RETRY_SETTINGS
)

# Use centralized logging - all logs go to django.log
logger = logging.getLogger('uploader.audio_recaptcha_solver')


class PlaywrightRecaptchaSolver:
    """Enhanced reCAPTCHA audio challenge solver with improved reliability"""

    # Use centralized constants
    TEMP_DIR = AUDIO_SETTINGS['temp_dir'] or (os.getenv("TEMP") if os.name == "nt" else "/tmp")
    TIMEOUT_STANDARD = TIMEOUTS['standard']
    TIMEOUT_SHORT = TIMEOUTS['short']
    TIMEOUT_DETECTION = TIMEOUTS['detection']
    MAX_RETRIES = RETRY_SETTINGS['max_retries']

    def __init__(self, page: Page, task_id: int = None, log_callback: callable = None) -> None:
        """Initialize the enhanced solver with a Playwright Page.

        Args:
            page: Playwright Page instance for browser interaction
            task_id: Task ID for web logging (optional)
            log_callback: Callback function for web logging (optional)
        """
        self.page = page
        self.temp_files = []  # Track temp files for cleanup
        self.task_id = task_id
        self.log_callback = log_callback

    async def _web_log(self, message: str) -> None:
        """Log message to web interface if callback provided"""
        try:
            if self.log_callback:
                await self.log_callback(message)
            elif self.task_id:
                # Fallback: try to update task log directly
                from django.utils import timezone
                from .models import YouTubeShortsBulkUploadTask

                try:
                    task = await YouTubeShortsBulkUploadTask.objects.aget(id=self.task_id)
                    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                    await task.aupdate(log=f"{task.log}[{timestamp}] {message}\n")
                except Exception as e:
                    logger.debug(f"Could not log to web: {e}")
        except Exception as e:
            logger.debug(f"Web logging error: {e}")
    
    async def solve_captcha(self) -> bool:
        """Enhanced reCAPTCHA challenge solving with retry logic and better error handling.

        Returns:
            bool: True if captcha solved successfully, False otherwise
        """
        logger.info("[RECAPTCHA_SOLVER] Starting enhanced reCAPTCHA challenge solving...")
        
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"[RECAPTCHA_SOLVER] Attempt {attempt + 1}/{self.MAX_RETRIES}")
                
                # Handle main reCAPTCHA iframe
                logger.info("[RECAPTCHA_SOLVER] Looking for main reCAPTCHA iframe...")
                await asyncio.sleep(2)  # Allow page to load
                
                # Try multiple iframe selectors
                iframe_selectors = [
                    'iframe[title="reCAPTCHA"]',
                    'iframe[src*="recaptcha"]',
                    'iframe[name*="recaptcha"]'
                ]
                
                recaptcha_frame = None
                for selector in iframe_selectors:
                    try:
                        recaptcha_frame = self.page.frame_locator(selector).first
                        # Test if frame is accessible
                        await recaptcha_frame.locator('.rc-anchor-content').wait_for(timeout=3000)
                        logger.info(f"[RECAPTCHA_SOLVER] Main reCAPTCHA iframe found with selector: {selector}")
                        break
                    except Exception:
                        continue
                
                if not recaptcha_frame:
                    logger.error("[RECAPTCHA_SOLVER] ❌ Main reCAPTCHA iframe not found")
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(5)
                        continue
                    return False

                # Click the checkbox
                logger.info("[RECAPTCHA_SOLVER] Looking for checkbox to click...")
                checkbox_selectors = ['.rc-anchor-content', '.recaptcha-checkbox-border', '.rc-anchor-center-item']
                
                checkbox_clicked = False
                for checkbox_selector in checkbox_selectors:
                    try:
                        # Try to find the checkbox element
                        checkbox = recaptcha_frame.locator(checkbox_selector)

                        # For problematic selectors that have overlapping elements,
                        # try to click on a more specific child element or use evaluate
                        try:
                            await checkbox.wait_for(timeout=self.TIMEOUT_STANDARD * 1000)
                            logger.info(f"[RECAPTCHA_SOLVER] Checkbox found with selector: {checkbox_selector}")

                            # Add pre-click delay to simulate human hesitation
                            await asyncio.sleep(random.uniform(1.0, 2.5))

                            # Try normal click first
                            try:
                                await checkbox.click(timeout=10000)
                                logger.info("[RECAPTCHA_SOLVER] Checkbox clicked successfully (normal)")
                            except Exception as click_error:
                                # If normal click fails due to overlapping elements, try evaluate
                                logger.warning(f"[RECAPTCHA_SOLVER] Normal click failed, trying evaluate: {click_error}")
                                await recaptcha_frame.evaluate("""
                                    (selector) => {
                                        const element = document.querySelector(selector);
                                        if (element) {
                                            element.click();
                                            return true;
                                        }
                                        return false;
                                    }
                                """, checkbox_selector)
                                logger.info("[RECAPTCHA_SOLVER] Checkbox clicked successfully (evaluate)")

                            # Add longer human-like delay after clicking checkbox
                            await asyncio.sleep(random.uniform(3.0, 6.0))
                            checkbox_clicked = True
                            break

                        except Exception as wait_error:
                            logger.warning(f"[RECAPTCHA_SOLVER] Checkbox wait failed: {wait_error}")
                            continue

                    except Exception as e:
                        logger.warning(f"[RECAPTCHA_SOLVER] Checkbox selector {checkbox_selector} failed: {e}")
                        continue
                
                if not checkbox_clicked:
                    logger.error("[RECAPTCHA_SOLVER] ❌ Failed to click checkbox")
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(5)
                        continue
                    return False

                # Check if solved by just clicking
                logger.info("[RECAPTCHA_SOLVER] Checking if captcha solved by simple click...")
                if await self.is_solved():
                    logger.info("[RECAPTCHA_SOLVER] ✅ Captcha solved by simple click!")
                    return True
                logger.info("[RECAPTCHA_SOLVER] Simple click didn't solve, proceeding to audio challenge...")

                # Handle audio challenge
                success = await self._handle_audio_challenge()
                if success:
                    logger.info("[RECAPTCHA_SOLVER] ✅ Audio challenge solved successfully!")
                    return True
                else:
                    logger.warning(f"[RECAPTCHA_SOLVER] ❌ Audio challenge failed on attempt {attempt + 1}")
                    if attempt < self.MAX_RETRIES - 1:
                        logger.info("[RECAPTCHA_SOLVER] Retrying after delay...")
                        await asyncio.sleep(5)
                        continue
                    
            except Exception as e:
                logger.error(f"[RECAPTCHA_SOLVER] ❌ Attempt {attempt + 1} failed with error: {str(e)}")
                if attempt < self.MAX_RETRIES - 1:
                    logger.info("[RECAPTCHA_SOLVER] Retrying after error...")
                    await asyncio.sleep(5)
                    continue
        
        logger.error(f"[RECAPTCHA_SOLVER] ❌ All {self.MAX_RETRIES} attempts failed")
        return False
    
    async def _handle_audio_challenge(self) -> bool:
        """Handle the audio challenge portion of reCAPTCHA"""
        try:
            logger.info("[RECAPTCHA_SOLVER] Looking for audio challenge iframe...")
            await asyncio.sleep(2)  # Wait for challenge iframe to appear

            # First, check if we have an image challenge that we need to switch to audio
            await self._handle_image_to_audio_transition()
            
            # Find challenge iframe - more comprehensive search
            challenge_frame_selectors = AUDIO_CHALLENGE_SELECTORS['iframe_selectors']

            challenge_frame = None
            for selector in challenge_frame_selectors:
                try:
                    frames = await self.page.query_selector_all(selector)
                    if frames:
                        # Get the frame content
                        for frame_element in frames:
                            frame = await frame_element.content_frame()
                            if frame:
                                # Check if this frame has audio challenge elements
                                try:
                                    # Look for audio challenge specific elements using multiple selectors
                                    audio_selectors = AUDIO_CHALLENGE_SELECTORS['play_button_selectors']

                                    for audio_selector in audio_selectors:
                                        try:
                                            audio_play_button = frame.locator(audio_selector)
                                            await audio_play_button.wait_for(timeout=TIMEOUTS['element_wait'] * 1000)
                                            challenge_frame = frame
                                            logger.info(f"[RECAPTCHA_SOLVER] Audio challenge iframe found with selector: {selector}, button: {audio_selector}")
                                            break
                                        except:
                                            continue

                                    if challenge_frame:
                                        break

                                except:
                                    continue
                        if challenge_frame:
                            break
                except Exception:
                    continue

            if not challenge_frame:
                logger.error("[RECAPTCHA_SOLVER] ❌ Audio challenge iframe not found")
                return False

            # Click play button with multiple fallback selectors
            logger.info("[RECAPTCHA_SOLVER] Clicking play button...")
            play_button_selectors = AUDIO_CHALLENGE_SELECTORS['play_button_selectors']

            play_clicked = False
            for play_selector in play_button_selectors:
                try:
                    play_button = challenge_frame.locator(play_selector)
                    # Simulate human hesitation before clicking play button
                    await asyncio.sleep(random.uniform(1.5, 3.0))

                    # Simulate mouse movement to play button
                    try:
                        box = await play_button.bounding_box()
                        if box:
                            await self.page.mouse.move(
                                box['x'] + box['width'] / 2 + random.uniform(-8, 8),
                                box['y'] + box['height'] / 2 + random.uniform(-4, 4)
                            )
                            await asyncio.sleep(random.uniform(0.2, 0.6))
                    except Exception:
                        pass  # Ignore mouse movement errors

                    await play_button.click(timeout=TIMEOUTS['click_timeout'] * 1000)
                    logger.info(f"[RECAPTCHA_SOLVER] Play button clicked with selector: {play_selector}")

                    # Longer delay after clicking play button
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    play_clicked = True
                    break
                except Exception as e:
                    logger.debug(f"[RECAPTCHA_SOLVER] Play button selector {play_selector} failed: {e}")
                    continue

            if not play_clicked:
                logger.error("[RECAPTCHA_SOLVER] ❌ Failed to click play button with any selector")
                return False

            await asyncio.sleep(3)  # Wait for audio to load

            # Check for bot detection
            logger.info("[RECAPTCHA_SOLVER] Checking for bot detection...")
            if await self._is_detected_in_frame(challenge_frame):
                logger.error("[RECAPTCHA_SOLVER] ❌ Bot detected by reCAPTCHA!")
                return False
            logger.info("[RECAPTCHA_SOLVER] ✅ No bot detection, proceeding...")

            # Get audio source and process
            logger.info("[RECAPTCHA_SOLVER] Waiting for audio source...")
            await asyncio.sleep(random.uniform(1.5, 3.0))  # Longer random wait

            # First try the simple approach like in GitHub code - direct #audio-source lookup
            try:
                logger.info("[RECAPTCHA_SOLVER] Trying direct #audio-source lookup...")
                audio_element = challenge_frame.locator("#audio-source")

                # Audio elements are always hidden, so don't wait for visibility
                # Just check if element exists and has src attribute
                count = await audio_element.count()
                if count > 0:
                    audio_src = await audio_element.get_attribute('src')
                    logger.info(f"[RECAPTCHA_SOLVER] Direct lookup found audio src: {audio_src}")

                    if audio_src and audio_src.strip():
                        logger.info(f"[RECAPTCHA_SOLVER] ✅ Audio source found via direct lookup: {audio_src[:100]}...")
                        # Process audio
                        logger.info("[RECAPTCHA_SOLVER] Starting enhanced audio processing...")
                        text_response = await self._process_audio_challenge(audio_src)
                        return await self._submit_audio_response(challenge_frame, text_response)

            except Exception as e:
                logger.warning(f"[RECAPTCHA_SOLVER] Direct #audio-source lookup failed: {e}")

            # Fallback: Try multiple selectors for audio element
            audio_selectors = AUDIO_CHALLENGE_SELECTORS['audio_element_selectors']
            logger.info(f"[RECAPTCHA_SOLVER] Trying fallback selectors ({len(audio_selectors)} total)...")

            audio_src = None
            for audio_selector in audio_selectors:
                try:
                    audio_source = challenge_frame.locator(audio_selector)
                    logger.info(f"[RECAPTCHA_SOLVER] Trying fallback selector: {audio_selector}")

                    # Audio elements are always hidden, just check if they exist
                    count = await audio_source.count()
                    if count > 0:
                        # Check if it has src attribute
                        audio_src = await audio_source.get_attribute('src')
                        audio_id = await audio_source.get_attribute('id')

                        logger.info(f"[RECAPTCHA_SOLVER] Fallback found: selector='{audio_selector}', id='{audio_id}', src='{audio_src}'")

                        # Accept any non-empty src
                        if audio_src and audio_src.strip():
                            logger.info(f"[RECAPTCHA_SOLVER] ✅ Audio source found via fallback: {audio_src[:100]}...")
                            # Process audio
                            logger.info("[RECAPTCHA_SOLVER] Starting enhanced audio processing...")
                            text_response = await self._process_audio_challenge(audio_src)
                            return await self._submit_audio_response(challenge_frame, text_response)

                except Exception as e:
                    logger.debug(f"[RECAPTCHA_SOLVER] Fallback selector {audio_selector} failed: {e}")
                    continue

            logger.error("[RECAPTCHA_SOLVER] ❌ Audio source not found with any method")
            return False

        except Exception as e:
            logger.error(f"[RECAPTCHA_SOLVER] ❌ Audio challenge error: {str(e)}")
            return False

    async def _submit_audio_response(self, challenge_frame, text_response: str) -> bool:
        """Submit the audio response and verify the solution."""
        try:
            # Input the response
            input_selectors = AUDIO_CHALLENGE_SELECTORS['input_field_selectors']
            input_found = False

            for input_selector in input_selectors:
                try:
                    input_field = challenge_frame.locator(input_selector)
                    await input_field.wait_for(timeout=2000)
                    # Simulate mouse movement to input field
                    try:
                        box = await input_field.bounding_box()
                        if box:
                            await challenge_frame.page.mouse.move(
                                box['x'] + random.uniform(10, box['width'] - 10),
                                box['y'] + box['height'] / 2 + random.uniform(-3, 3)
                            )
                            await asyncio.sleep(random.uniform(0.3, 0.7))
                    except Exception:
                        pass

                    # Clear field first and type like a human
                    await input_field.clear()
                    await asyncio.sleep(random.uniform(0.2, 0.5))

                    # Type the response character by character with small delays
                    for char in text_response.lower():
                        await input_field.type(char, delay=random.uniform(50, 150))  # Human typing speed

                    # Log what we entered
                    entered_text = text_response.lower()
                    log_message = f"🎯 ENTERED TEXT INTO FIELD: '{entered_text}'"
                    logger.info(f"[RECAPTCHA_SOLVER] {log_message}")
                    await self._web_log(log_message)
                    logger.info(f"[RECAPTCHA_SOLVER] Response entered using selector: {input_selector}")

                    # Human-like delay after typing (simulate thinking)
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                    input_found = True
                    break
                except Exception as e:
                    logger.debug(f"[RECAPTCHA_SOLVER] Input selector {input_selector} failed: {e}")
                    continue

            if not input_found:
                logger.error("[RECAPTCHA_SOLVER] ❌ Could not find input field")
                return False

            # Click verify button
            verify_selectors = AUDIO_CHALLENGE_SELECTORS['verify_button_selectors']
            verify_found = False

            for verify_selector in verify_selectors:
                try:
                    verify_button = challenge_frame.locator(verify_selector)
                    await verify_button.wait_for(timeout=2000)
                    # Simulate mouse movement to verify button
                    try:
                        box = await verify_button.bounding_box()
                        if box:
                            await challenge_frame.page.mouse.move(
                                box['x'] + box['width'] / 2 + random.uniform(-8, 8),
                                box['y'] + box['height'] / 2 + random.uniform(-4, 4)
                            )
                            await asyncio.sleep(random.uniform(0.4, 0.9))
                    except Exception:
                        pass

                    await verify_button.click(timeout=TIMEOUTS['click_timeout'] * 1000)
                    logger.info(f"[RECAPTCHA_SOLVER] Verify button clicked using selector: {verify_selector}")

                    # Human-like delay before checking result
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    verify_found = True
                    break
                except Exception as e:
                    logger.debug(f"[RECAPTCHA_SOLVER] Verify selector {verify_selector} failed: {e}")
                    continue

            if not verify_found:
                logger.error("[RECAPTCHA_SOLVER] ❌ Could not find verify button")
                return False

            # Wait for verification result (2-4 seconds) then always click Next
            logger.info("[RECAPTCHA_SOLVER] ⏳ Waiting 2-4 seconds for verification, then clicking Next...")
            await asyncio.sleep(random.uniform(2.0, 4.0))  # Random wait for verification

            # Always click Next button - let the next step determine if captcha was solved
            try:
                log_message = "🎯 Clicking 'Siguiente' button to proceed to next step..."
                logger.info(f"[RECAPTCHA_SOLVER] {log_message}")
                await self._web_log(log_message)

                # Try multiple selectors for the "Siguiente" button
                next_button_selectors = LOGIN_PAGE_SELECTORS['next_button_selectors']

                next_clicked = False
                for next_selector in next_button_selectors:
                    try:
                        next_button = self.page.locator(next_selector)
                        if await next_button.is_visible():
                            # Simulate mouse movement
                            try:
                                box = await next_button.bounding_box()
                                if box:
                                    await self.page.mouse.move(
                                        box['x'] + box['width'] / 2 + random.uniform(-5, 5),
                                        box['y'] + box['height'] / 2 + random.uniform(-3, 3)
                                    )
                                    await asyncio.sleep(random.uniform(0.3, 0.7))
                            except Exception:
                                pass

                            await next_button.click(timeout=10000)
                            success_message = "✅ 'Siguiente' button clicked - proceeding to password field check"
                            logger.info(f"[RECAPTCHA_SOLVER] {success_message}")
                            await self._web_log(success_message)
                            next_clicked = True
                            break
                    except Exception as e:
                        logger.debug(f"[RECAPTCHA_SOLVER] Next button selector {next_selector} failed: {e}")
                        continue

                if next_clicked:
                    return True
                else:
                    error_message = "❌ Could not find or click 'Siguiente' button"
                    logger.error(f"[RECAPTCHA_SOLVER] {error_message}")
                    await self._web_log(error_message)
                    return False

            except Exception as e:
                error_message = f"❌ Error during Next button interaction: {e}"
                logger.error(f"[RECAPTCHA_SOLVER] {error_message}")
                await self._web_log(error_message)
                return False

        except Exception as e:
            logger.error(f"[RECAPTCHA_SOLVER] ❌ Error submitting audio response: {e}")
            return False
    
    async def _handle_image_to_audio_transition(self) -> None:
        """Handle transition from image challenge to audio challenge"""
        try:
            logger.info("[RECAPTCHA_SOLVER] Checking for image challenge to switch to audio...")

            # Wait for image challenge to fully load (it may take time to appear after checkbox click)
            await asyncio.sleep(random.uniform(4.0, 7.0))  # Longer random delay

            # First, find the challenge iframe (same as in _handle_audio_challenge)
            challenge_frame_selectors = AUDIO_CHALLENGE_SELECTORS['iframe_selectors']
            logger.info(f"[RECAPTCHA_SOLVER] Looking for challenge iframes with {len(challenge_frame_selectors)} selectors")

            for selector in challenge_frame_selectors:
                try:
                    frames = await self.page.query_selector_all(selector)
                    logger.info(f"[RECAPTCHA_SOLVER] Selector '{selector}' found {len(frames)} iframes")
                    if frames:
                        for frame_element in frames:
                            frame = await frame_element.content_frame()
                            if frame:
                                # Check if this frame has image challenge elements
                                try:
                                    image_challenge_selectors = IMAGE_CHALLENGE_SELECTORS['container_selectors']

                                    for img_selector in image_challenge_selectors:
                                        try:
                                            image_container = frame.locator(img_selector)
                                            if await image_container.is_visible():
                                                logger.info(f"[RECAPTCHA_SOLVER] ✅ Image challenge found in iframe with selector: {selector}")

                                                # Look for audio button in the image challenge within the frame
                                                audio_button_selectors = IMAGE_CHALLENGE_SELECTORS['audio_button_selectors']

                                                for audio_selector in audio_button_selectors:
                                                    try:
                                                        audio_button = frame.locator(audio_selector)
                                                        if await audio_button.is_visible():
                                                            # Simulate human hesitation before clicking audio button
                                                            await asyncio.sleep(random.uniform(2.0, 4.0))

                                                            # Simulate mouse movement to button
                                                            try:
                                                                box = await audio_button.bounding_box()
                                                                if box:
                                                                    # Move mouse to random point near the button
                                                                    await self.page.mouse.move(
                                                                        box['x'] + box['width'] / 2 + random.uniform(-10, 10),
                                                                        box['y'] + box['height'] / 2 + random.uniform(-5, 5)
                                                                    )
                                                                    await asyncio.sleep(random.uniform(0.3, 0.8))
                                                            except Exception:
                                                                pass  # Ignore mouse movement errors

                                                            await audio_button.click(timeout=TIMEOUTS['click_timeout'] * 1000)
                                                            logger.info(f"[RECAPTCHA_SOLVER] ✅ Clicked audio button in image challenge: {audio_selector}")

                                                            # Longer delay after clicking audio button
                                                            await asyncio.sleep(random.uniform(3.0, 5.0))

                                                            # Check for bot detection after clicking audio button
                                                            if await self._is_detected_in_frame(frame):
                                                                logger.warning("[RECAPTCHA_SOLVER] ❌ Bot detected after clicking audio button, reloading page...")

                                                                # Reload page to reset captcha state
                                                                try:
                                                                    await self.page.reload(wait_until="domcontentloaded")
                                                                    logger.info("[RECAPTCHA_SOLVER] Page reloaded after bot detection, waiting before retry...")

                                                                    # Much longer delay before retrying (simulate human giving up and trying later)
                                                                    await asyncio.sleep(random.uniform(15.0, 25.0))

                                                                    # Reset attempt counter and retry the entire login process
                                                                    logger.info("[RECAPTCHA_SOLVER] 🔄 Retrying captcha solving after page reload...")
                                                                    return await self.solve_captcha()  # Recursive retry

                                                                except Exception as e:
                                                                    logger.error(f"[RECAPTCHA_SOLVER] Page reload failed: {e}")
                                                                    return False

                                                            return
                                                    except Exception as e:
                                                        logger.debug(f"[RECAPTCHA_SOLVER] Audio button selector {audio_selector} failed: {e}")
                                                        continue

                                        except Exception as e:
                                            logger.debug(f"[RECAPTCHA_SOLVER] Image challenge selector {img_selector} failed: {e}")
                                            continue

                                except Exception as e:
                                    logger.debug(f"[RECAPTCHA_SOLVER] Frame check failed: {e}")
                                    continue

                except Exception as e:
                    logger.debug(f"[RECAPTCHA_SOLVER] Frame selector {selector} failed: {e}")
                    continue

            logger.info("[RECAPTCHA_SOLVER] No image challenge found or already in audio mode")

        except Exception as e:
            logger.warning(f"[RECAPTCHA_SOLVER] Error handling image to audio transition: {e}")

    async def _is_detected_in_frame(self, frame) -> bool:
        """Check if bot detection occurred in the challenge frame"""
        try:
            detection_selectors = BOT_DETECTION_SELECTORS
            
            for selector in detection_selectors:
                try:
                    element = frame.locator(selector)
                    if await element.is_visible():
                        return True
                except:
                    continue
            return False
        except Exception:
            return False
    
    async def _process_audio_challenge(self, audio_url: str) -> Optional[str]:
        """Enhanced audio processing with multiple recognition attempts and audio enhancement.

        Args:
            audio_url: URL of the audio file to process

        Returns:
            str: Recognized text from the audio file
        """
        # Create unique temporary file names
        timestamp = int(time.time() * 1000)
        mp3_path = os.path.join(self.TEMP_DIR, f"recaptcha_audio_{timestamp}.mp3")
        wav_path = os.path.join(self.TEMP_DIR, f"recaptcha_audio_{timestamp}.wav")
        enhanced_wav_path = os.path.join(self.TEMP_DIR, f"recaptcha_enhanced_{timestamp}.wav")
        
        # Track temp files for cleanup
        self.temp_files.extend([mp3_path, wav_path, enhanced_wav_path])
        
        logger.info(f"[RECAPTCHA_SOLVER] Enhanced audio processing started")
        logger.info(f"[RECAPTCHA_SOLVER] Audio URL: {audio_url[:50]}...")

        try:
            # Download audio file asynchronously
            logger.info("[RECAPTCHA_SOLVER] Downloading audio file...")
            success = await self._download_audio_async(audio_url, mp3_path)
            if not success:
                logger.error("[RECAPTCHA_SOLVER] ❌ Failed to download audio file")
                return None
                
            mp3_size = os.path.getsize(mp3_path)
            logger.info(f"[RECAPTCHA_SOLVER] ✅ Audio downloaded: {mp3_size} bytes")
            
            # Convert and enhance audio
            logger.info("[RECAPTCHA_SOLVER] Converting and enhancing audio...")
            enhanced_audio = await self._convert_and_enhance_audio(mp3_path, wav_path, enhanced_wav_path)
            if not enhanced_audio:
                logger.error("[RECAPTCHA_SOLVER] ❌ Failed to process audio")
                return None

                # Try speech recognition with multiple methods
            logger.info("[RECAPTCHA_SOLVER] Starting enhanced speech recognition...")
            recognized_text = await self._recognize_speech_enhanced(enhanced_audio)

            # If we got here, speech recognition worked, so we can clean up audio files immediately
            # This prevents issues with retries trying to re-download the same URL
            try:
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
                if os.path.exists(wav_path):
                    os.remove(wav_path)
                if os.path.exists(enhanced_wav_path):
                    os.remove(enhanced_wav_path)
                logger.info("[RECAPTCHA_SOLVER] ✅ Cleaned up audio files after successful recognition")
            except Exception as e:
                logger.debug(f"[RECAPTCHA_SOLVER] Could not clean up audio files: {e}")
            
            if recognized_text:
                logger.info(f"[RECAPTCHA_SOLVER] ✅ Speech recognition successful: '{recognized_text}'")
                return recognized_text
            else:
                logger.error("[RECAPTCHA_SOLVER] ❌ All speech recognition attempts failed")
                return None

        except Exception as e:
            logger.error(f"[RECAPTCHA_SOLVER] ❌ Audio processing error: {str(e)}")
            return None
        finally:
            # Cleanup temp files
            await self._cleanup_temp_files()
    
    async def _download_audio_async(self, audio_url: str, output_path: str) -> bool:
        """Download audio file asynchronously with proper error handling"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url) as response:
                    if response.status == 200:
                        async with aiofiles.open(output_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        return True
                    else:
                        logger.error(f"[RECAPTCHA_SOLVER] HTTP error downloading audio: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"[RECAPTCHA_SOLVER] Error downloading audio: {e}")
            # Fallback to synchronous download
            try:
                urllib.request.urlretrieve(audio_url, output_path)
                return True
            except Exception as fallback_e:
                logger.error(f"[RECAPTCHA_SOLVER] Fallback download also failed: {fallback_e}")
                return False
    
    async def _convert_and_enhance_audio(self, mp3_path: str, wav_path: str, enhanced_path: str) -> Optional[str]:
        """Convert MP3 to WAV and enhance audio quality"""
        try:
            # Convert MP3 to WAV
            sound = pydub.AudioSegment.from_mp3(mp3_path)
            logger.info(f"[RECAPTCHA_SOLVER] Original audio: {len(sound)/1000:.2f}s, {sound.frame_rate}Hz")
            
            # Basic audio enhancement
            enhanced_sound = sound
            
            # Normalize volume
            if sound.max_possible_amplitude > 0:
                enhanced_sound = sound.normalize()
                logger.info("[RECAPTCHA_SOLVER] Audio normalized")
            
            # Apply noise reduction (simple high-pass filter)
            try:
                # Remove low frequency noise (below 300Hz)
                enhanced_sound = enhanced_sound.high_pass_filter(300)
                logger.info("[RECAPTCHA_SOLVER] High-pass filter applied")
            except Exception as filter_e:
                logger.warning(f"[RECAPTCHA_SOLVER] Filter failed: {filter_e}, using original")
                enhanced_sound = sound
            
            # Ensure proper sample rate for speech recognition
            if enhanced_sound.frame_rate != AUDIO_SETTINGS['sample_rate']:
                enhanced_sound = enhanced_sound.set_frame_rate(AUDIO_SETTINGS['sample_rate'])
                logger.info(f"[RECAPTCHA_SOLVER] Sample rate set to {AUDIO_SETTINGS['sample_rate']}Hz")

            # Convert to mono if stereo
            if enhanced_sound.channels > AUDIO_SETTINGS['channels']:
                enhanced_sound = enhanced_sound.set_channels(AUDIO_SETTINGS['channels'])
                logger.info("[RECAPTCHA_SOLVER] Converted to mono")
            
            # Export enhanced audio
            enhanced_sound.export(enhanced_path, format="wav")
            enhanced_size = os.path.getsize(enhanced_path)
            logger.info(f"[RECAPTCHA_SOLVER] ✅ Enhanced audio created: {enhanced_size} bytes")
            
            # Also export basic WAV as fallback
            sound.export(wav_path, format="wav")
            
            return enhanced_path
            
        except Exception as e:
            logger.error(f"[RECAPTCHA_SOLVER] Audio enhancement failed: {e}")
            # Try basic conversion as fallback
            try:
                sound = pydub.AudioSegment.from_mp3(mp3_path)
                sound.export(wav_path, format="wav")
                logger.info("[RECAPTCHA_SOLVER] Basic WAV conversion successful")
                return wav_path
            except Exception as basic_e:
                logger.error(f"[RECAPTCHA_SOLVER] Basic conversion also failed: {basic_e}")
                return None
    
    async def _recognize_speech_enhanced(self, audio_path: str) -> Optional[str]:
        """Enhanced speech recognition with multiple attempts and languages"""
        recognizer = speech_recognition.Recognizer()
        
        # Adjust recognizer settings for better accuracy
        recognizer.energy_threshold = AUDIO_SETTINGS['energy_threshold']
        recognizer.dynamic_energy_threshold = AUDIO_SETTINGS['dynamic_energy']
        recognizer.pause_threshold = AUDIO_SETTINGS['pause_threshold']
        recognizer.operation_timeout = AUDIO_SETTINGS['operation_timeout']
        
        # Try recognition with different languages
        for language in SUPPORTED_LANGUAGES:
            try:
                logger.info(f"[RECAPTCHA_SOLVER] Trying speech recognition with language: {language}")
                
                with speech_recognition.AudioFile(audio_path) as source:
                    # Adjust for ambient noise
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.record(source)
                
                # Try Google Speech Recognition
                try:
                    text = recognizer.recognize_google(audio, language=language)
                    if text and len(text.strip()) > 0:
                        logger.info(f"[RECAPTCHA_SOLVER] ✅ Recognition successful with {language}: '{text}'")
                        return text.strip()
                except speech_recognition.UnknownValueError:
                    logger.info(f"[RECAPTCHA_SOLVER] No speech detected with {language}")
                except speech_recognition.RequestError as e:
                    logger.warning(f"[RECAPTCHA_SOLVER] Google API error with {language}: {e}")
                
                # Try with different audio settings if first attempt fails
                if language == 'en-US':  # Only try variations for primary language
                    try:
                        with speech_recognition.AudioFile(audio_path) as source:
                            # Try with different duration
                            recognizer.adjust_for_ambient_noise(source, duration=1.0)
                            audio = recognizer.record(source)
                        
                        text = recognizer.recognize_google(audio, language=language)
                        if text and len(text.strip()) > 0:
                            logger.info(f"[RECAPTCHA_SOLVER] ✅ Recognition successful with adjusted settings: '{text}'")
                            return text.strip()
                    except Exception:
                        pass
                
            except Exception as e:
                logger.warning(f"[RECAPTCHA_SOLVER] Recognition failed for {language}: {e}")
                continue
        
        logger.error("[RECAPTCHA_SOLVER] ❌ All speech recognition attempts failed")
        return None
    
    async def _cleanup_temp_files(self):
        """Clean up all temporary files"""
        logger.info("[RECAPTCHA_SOLVER] Cleaning up temporary files...")
        for file_path in self.temp_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"[RECAPTCHA_SOLVER] ✅ Cleaned up: {os.path.basename(file_path)}")
                except OSError as e:
                    logger.warning(f"[RECAPTCHA_SOLVER] ⚠️ Could not remove {file_path}: {e}")
        self.temp_files.clear()
    
    async def is_solved(self) -> bool:
        """Check if the captcha has been solved successfully."""
        try:
            # Check solved indicators (checkbox states)
            for indicator in CAPTCHA_SOLUTION_SELECTORS['solved_indicators']:
                try:
                    element = self.page.locator(indicator)
                    if await element.count() > 0:
                        # For checkmark, check if it's visible
                        if 'checkmark' in indicator:
                            style = await element.get_attribute('style')
                            if style and 'display' not in style:
                                logger.info(f"[RECAPTCHA_SOLVER] ✅ Captcha solved: {indicator} visible")
                                return True
                        else:
                            # For other indicators, just presence is enough
                            logger.info(f"[RECAPTCHA_SOLVER] ✅ Captcha solved: {indicator} detected")
                            return True
                except Exception:
                    continue

            # Check success messages in multiple languages
            for message_selector in CAPTCHA_SOLUTION_SELECTORS['success_messages']:
                try:
                    message_element = self.page.locator(message_selector)
                    if await message_element.is_visible():
                        logger.info(f"[RECAPTCHA_SOLVER] ✅ Captcha solved: success message '{message_selector}' visible")
                        return True
                except Exception:
                    continue

            return False
        except Exception as e:
            logger.debug(f"[RECAPTCHA_SOLVER] Error checking if solved: {e}")
            return False

    async def is_detected(self) -> bool:
        """Check if the bot has been detected."""
        try:
            error_msg = self.page.locator('text="Try again later"')
            return await error_msg.is_visible()
        except Exception:
            return False

    async def get_token(self) -> Optional[str]:
        """Get the reCAPTCHA token if available."""
        try:
            token_element = self.page.locator('#recaptcha-token')
            if await token_element.count() > 0:
                return await token_element.get_attribute('value')
            return None
        except Exception:
            return None


async def solve_recaptcha_with_audio(page: Page, task_id: int = None, log_callback: callable = None) -> bool:
    """Solve reCAPTCHA through audio challenge with full logging"""
    logger.info("[AUDIO_CAPTCHA] Starting audio challenge solve...")
    solver = PlaywrightRecaptchaSolver(page, task_id=task_id, log_callback=log_callback)
    result = await solver.solve_captcha()

    if result:
        logger.info("[AUDIO_CAPTCHA] ✅ Audio challenge completed successfully!")
    else:
        logger.error("[AUDIO_CAPTCHA] ❌ Audio challenge failed!")

    return result
