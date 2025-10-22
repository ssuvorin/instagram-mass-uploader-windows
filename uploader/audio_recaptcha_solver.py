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

# Use centralized logging - all logs go to django.log
logger = logging.getLogger('uploader.audio_recaptcha_solver')


class PlaywrightRecaptchaSolver:
    """Enhanced reCAPTCHA audio challenge solver with improved reliability"""

    # Constants
    TEMP_DIR = os.getenv("TEMP") if os.name == "nt" else "/tmp"
    TIMEOUT_STANDARD = 20  # Increased for better reliability
    TIMEOUT_SHORT = 5      # Increased for stability
    TIMEOUT_DETECTION = 2  # Increased for detection
    MAX_RETRIES = 3        # Maximum retry attempts
    SUPPORTED_LANGUAGES = ['en-US', 'en', 'es', 'fr', 'de', 'it']  # Language fallbacks

    def __init__(self, page: Page) -> None:
        """Initialize the enhanced solver with a Playwright Page.

        Args:
            page: Playwright Page instance for browser interaction
        """
        self.page = page
        self.temp_files = []  # Track temp files for cleanup
    
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
                        checkbox = recaptcha_frame.locator(checkbox_selector)
                        await checkbox.wait_for(timeout=self.TIMEOUT_STANDARD * 1000)
                        logger.info(f"[RECAPTCHA_SOLVER] Checkbox found with selector: {checkbox_selector}")
                        await checkbox.click()
                        logger.info("[RECAPTCHA_SOLVER] Checkbox clicked successfully")
                        checkbox_clicked = True
                        break
                    except Exception as e:
                        logger.warning(f"[RECAPTCHA_SOLVER] Checkbox selector {checkbox_selector} failed: {e}")
                        continue
                
                if not checkbox_clicked:
                    logger.error("[RECAPTCHA_SOLVER] ❌ Failed to click checkbox")
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(5)
                        continue
                    return False

                await asyncio.sleep(2)  # Wait for processing

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
            
            # Find challenge iframe
            challenge_frame_selectors = [
                'iframe[title*="recaptcha challenge"]',
                'iframe[src*="recaptcha"][src*="bframe"]',
                'iframe[name*="c-"]'
            ]
            
            challenge_frame = None
            for selector in challenge_frame_selectors:
                try:
                    frames = await self.page.query_selector_all(selector)
                    if frames:
                        # Get the frame content
                        for frame_element in frames:
                            frame = await frame_element.content_frame()
                            if frame:
                                # Check if this frame has audio button
                                audio_button = frame.locator('#recaptcha-audio-button')
                                try:
                                    await audio_button.wait_for(timeout=3000)
                                    challenge_frame = frame
                                    logger.info(f"[RECAPTCHA_SOLVER] Challenge iframe found with selector: {selector}")
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
            
            # Click audio button
            logger.info("[RECAPTCHA_SOLVER] Clicking audio button...")
            audio_button = challenge_frame.locator('#recaptcha-audio-button')
            await audio_button.click()
            logger.info("[RECAPTCHA_SOLVER] Audio button clicked")
            await asyncio.sleep(3)  # Wait for audio to load

            # Check for bot detection
            logger.info("[RECAPTCHA_SOLVER] Checking for bot detection...")
            if await self._is_detected_in_frame(challenge_frame):
                logger.error("[RECAPTCHA_SOLVER] ❌ Bot detected by reCAPTCHA!")
                return False
            logger.info("[RECAPTCHA_SOLVER] ✅ No bot detection, proceeding...")

            # Get audio source and process
            logger.info("[RECAPTCHA_SOLVER] Waiting for audio source...")
            await asyncio.sleep(2)  # Wait for audio source to appear
            
            audio_source = challenge_frame.locator('#audio-source')
            await audio_source.wait_for(timeout=self.TIMEOUT_STANDARD * 1000)
            audio_src = await audio_source.get_attribute('src')
            logger.info(f"[RECAPTCHA_SOLVER] Audio source URL: {audio_src[:50]}...")

            # Process audio
            logger.info("[RECAPTCHA_SOLVER] Starting enhanced audio processing...")
            text_response = await self._process_audio_challenge(audio_src)
            
            if not text_response:
                logger.error("[RECAPTCHA_SOLVER] ❌ Audio processing failed")
                return False
                
            logger.info(f"[RECAPTCHA_SOLVER] Audio recognized as: '{text_response}'")
            
            # Enter response
            logger.info("[RECAPTCHA_SOLVER] Entering recognized text...")
            audio_response_input = challenge_frame.locator('#audio-response')
            await audio_response_input.fill(text_response.lower())
            logger.info("[RECAPTCHA_SOLVER] Text entered successfully")
            
            # Click verify button
            logger.info("[RECAPTCHA_SOLVER] Clicking verify button...")
            verify_button = challenge_frame.locator('#recaptcha-verify-button')
            await verify_button.click()
            logger.info("[RECAPTCHA_SOLVER] Verify button clicked")
            await asyncio.sleep(4)  # Wait for processing

            # Check final result
            logger.info("[RECAPTCHA_SOLVER] Checking final result...")
            if await self.is_solved():
                logger.info("[RECAPTCHA_SOLVER] ✅ Audio challenge completed successfully!")
                return True
            else:
                logger.error("[RECAPTCHA_SOLVER] ❌ Audio challenge failed - captcha not solved")
                return False

        except Exception as e:
            logger.error(f"[RECAPTCHA_SOLVER] ❌ Audio challenge error: {str(e)}")
            return False
    
    async def _is_detected_in_frame(self, frame) -> bool:
        """Check if bot detection occurred in the challenge frame"""
        try:
            detection_selectors = [
                'text="Try again later"',
                'text="Your computer or network may be sending automated queries"',
                '.rc-doscaptcha-body-text'
            ]
            
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
            if enhanced_sound.frame_rate != 16000:
                enhanced_sound = enhanced_sound.set_frame_rate(16000)
                logger.info("[RECAPTCHA_SOLVER] Sample rate set to 16kHz")
            
            # Convert to mono if stereo
            if enhanced_sound.channels > 1:
                enhanced_sound = enhanced_sound.set_channels(1)
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
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8
        recognizer.operation_timeout = 10
        
        # Try recognition with different languages
        for language in self.SUPPORTED_LANGUAGES:
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
            checkmark = self.page.locator('.recaptcha-checkbox-checkmark')
            if await checkmark.count() > 0:
                style = await checkmark.get_attribute('style')
                return style and 'display' not in style
            return False
        except Exception:
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


async def solve_recaptcha_with_audio(page: Page) -> bool:
    """Solve reCAPTCHA through audio challenge with full logging"""
    logger.info("[AUDIO_CAPTCHA] Starting audio challenge solve...")
    solver = PlaywrightRecaptchaSolver(page)
    result = await solver.solve_captcha()
    
    if result:
        logger.info("[AUDIO_CAPTCHA] ✅ Audio challenge completed successfully!")
    else:
        logger.error("[AUDIO_CAPTCHA] ❌ Audio challenge failed!")
    
    return result
