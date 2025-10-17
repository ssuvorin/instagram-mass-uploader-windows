import os
import urllib.request
import random
import pydub
import speech_recognition
import asyncio
import time
import logging
from typing import Optional
from playwright.async_api import Page

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PlaywrightRecaptchaSolver:
    """A class to solve reCAPTCHA challenges using audio recognition for Playwright"""

    # Constants
    TEMP_DIR = os.getenv("TEMP") if os.name == "nt" else "/tmp"
    TIMEOUT_STANDARD = 15  # Увеличено для медленной загрузки
    TIMEOUT_SHORT = 3      # Увеличено для стабильности
    TIMEOUT_DETECTION = 1  # Увеличено для проверки

    def __init__(self, page: Page) -> None:
        """Initialize the solver with a Playwright Page.

        Args:
            page: Playwright Page instance for browser interaction
        """
        self.page = page
    
    async def solve_captcha(self) -> bool:
        """Attempt to solve the reCAPTCHA challenge with full logging.

        Returns:
            bool: True if captcha solved successfully, False otherwise
        """
        logger.info("[RECAPTCHA_SOLVER] Starting reCAPTCHA challenge solving...")
        
        try:
            # Handle main reCAPTCHA iframe
            logger.info("[RECAPTCHA_SOLVER] Looking for main reCAPTCHA iframe...")
            await asyncio.sleep(2)  # Даем время странице загрузиться
            
            recaptcha_frame = self.page.frame_locator('iframe[title="reCAPTCHA"]').first
            logger.info("[RECAPTCHA_SOLVER] Main reCAPTCHA iframe found")
            await asyncio.sleep(1)

            # Click the checkbox
            logger.info("[RECAPTCHA_SOLVER] Looking for checkbox to click...")
            checkbox = recaptcha_frame.locator('.rc-anchor-content')
            await checkbox.wait_for(timeout=self.TIMEOUT_STANDARD * 1000)
            logger.info("[RECAPTCHA_SOLVER] Checkbox found, clicking...")
            await checkbox.click()
            logger.info("[RECAPTCHA_SOLVER] Checkbox clicked successfully")
            await asyncio.sleep(1)  # Даем время на обработку клика

            # Check if solved by just clicking
            logger.info("[RECAPTCHA_SOLVER] Checking if captcha solved by simple click...")
            if await self.is_solved():
                logger.info("[RECAPTCHA_SOLVER] ✅ Captcha solved by simple click!")
                return True
            logger.info("[RECAPTCHA_SOLVER] Simple click didn't solve, proceeding to audio challenge...")

            # Handle audio challenge
            logger.info("[RECAPTCHA_SOLVER] Looking for audio challenge iframe...")
            await asyncio.sleep(2)  # Даем время на появление challenge iframe
            
            challenge_frame = self.page.frame_locator('iframe[title*="recaptcha"]').nth(1)
            audio_button = challenge_frame.locator('#recaptcha-audio-button')
            await audio_button.wait_for(timeout=self.TIMEOUT_STANDARD * 1000)
            logger.info("[RECAPTCHA_SOLVER] Audio challenge iframe found")
            
            logger.info("[RECAPTCHA_SOLVER] Clicking audio button...")
            await audio_button.click()
            logger.info("[RECAPTCHA_SOLVER] Audio button clicked")
            await asyncio.sleep(2)  # Даем время на загрузку аудио

            logger.info("[RECAPTCHA_SOLVER] Checking for bot detection...")
            if await self.is_detected():
                logger.error("[RECAPTCHA_SOLVER] ❌ Bot detected by reCAPTCHA!")
                return False
            logger.info("[RECAPTCHA_SOLVER] ✅ No bot detection, proceeding...")

            # Download and process audio
            logger.info("[RECAPTCHA_SOLVER] Waiting for audio source...")
            await asyncio.sleep(1)  # Даем время на появление audio source
            
            audio_source = challenge_frame.locator('#audio-source')
            await audio_source.wait_for(timeout=self.TIMEOUT_STANDARD * 1000)
            audio_src = await audio_source.get_attribute('src')
            logger.info(f"[RECAPTCHA_SOLVER] Audio source URL: {audio_src[:50]}...")

            try:
                logger.info("[RECAPTCHA_SOLVER] Starting audio processing...")
                text_response = await self._process_audio_challenge(audio_src)
                logger.info(f"[RECAPTCHA_SOLVER] Audio recognized as: '{text_response}'")
                
                logger.info("[RECAPTCHA_SOLVER] Entering recognized text...")
                await challenge_frame.locator('#audio-response').fill(text_response.lower())
                logger.info("[RECAPTCHA_SOLVER] Text entered successfully")
                
                logger.info("[RECAPTCHA_SOLVER] Clicking verify button...")
                await challenge_frame.locator('#recaptcha-verify-button').click()
                logger.info("[RECAPTCHA_SOLVER] Verify button clicked")
                await asyncio.sleep(3)  # Даем время на обработку ответа

                logger.info("[RECAPTCHA_SOLVER] Checking final result...")
                if not await self.is_solved():
                    logger.error("[RECAPTCHA_SOLVER] ❌ Audio challenge failed to solve captcha")
                    return False
                
                logger.info("[RECAPTCHA_SOLVER] ✅ Audio challenge solved successfully!")
                return True

            except Exception as e:
                logger.error(f"[RECAPTCHA_SOLVER] ❌ Audio challenge failed: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"[RECAPTCHA_SOLVER] ❌ Overall captcha solving failed: {str(e)}")
            return False
    
    async def _process_audio_challenge(self, audio_url: str) -> Optional[str]:
        """Process the audio challenge and return the recognized text with full logging.

        Args:
            audio_url: URL of the audio file to process

        Returns:
            str: Recognized text from the audio file
        """
        mp3_path = os.path.join(self.TEMP_DIR, f"{random.randrange(1,1000)}.mp3")
        wav_path = os.path.join(self.TEMP_DIR, f"{random.randrange(1,1000)}.wav")
        
        logger.info(f"[RECAPTCHA_SOLVER] Audio processing started")
        logger.info(f"[RECAPTCHA_SOLVER] Audio URL: {audio_url[:50]}...")
        logger.info(f"[RECAPTCHA_SOLVER] Temp MP3 path: {mp3_path}")
        logger.info(f"[RECAPTCHA_SOLVER] Temp WAV path: {wav_path}")

        try:
            # Download audio file
            logger.info("[RECAPTCHA_SOLVER] Downloading audio file...")
            urllib.request.urlretrieve(audio_url, mp3_path)
            mp3_size = os.path.getsize(mp3_path)
            logger.info(f"[RECAPTCHA_SOLVER] ✅ Audio downloaded: {mp3_size} bytes")
            
            # Convert MP3 to WAV
            logger.info("[RECAPTCHA_SOLVER] Converting MP3 to WAV...")
            sound = pydub.AudioSegment.from_mp3(mp3_path)
            logger.info(f"[RECAPTCHA_SOLVER] Audio duration: {len(sound)/1000:.2f} seconds")
            
            sound.export(wav_path, format="wav")
            wav_size = os.path.getsize(wav_path)
            logger.info(f"[RECAPTCHA_SOLVER] ✅ WAV conversion complete: {wav_size} bytes")

            # Speech recognition
            logger.info("[RECAPTCHA_SOLVER] Starting speech recognition...")
            recognizer = speech_recognition.Recognizer()
            
            with speech_recognition.AudioFile(wav_path) as source:
                logger.info("[RECAPTCHA_SOLVER] Recording audio for recognition...")
                audio = recognizer.record(source)
                logger.info("[RECAPTCHA_SOLVER] Audio recorded, starting Google recognition...")
                
                recognized_text = recognizer.recognize_google(audio)
                logger.info(f"[RECAPTCHA_SOLVER] ✅ Speech recognition successful: '{recognized_text}'")
                
                return recognized_text

        except speech_recognition.UnknownValueError:
            logger.error("[RECAPTCHA_SOLVER] ❌ Speech recognition failed: Could not understand audio")
            return None
        except speech_recognition.RequestError as e:
            logger.error(f"[RECAPTCHA_SOLVER] ❌ Speech recognition API error: {e}")
            return None
        except Exception as e:
            logger.error(f"[RECAPTCHA_SOLVER] ❌ Audio processing error: {str(e)}")
            return None
        finally:
            # Cleanup temp files
            logger.info("[RECAPTCHA_SOLVER] Cleaning up temporary files...")
            for path in (mp3_path, wav_path):
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        logger.info(f"[RECAPTCHA_SOLVER] ✅ Cleaned up: {os.path.basename(path)}")
                    except OSError as e:
                        logger.warning(f"[RECAPTCHA_SOLVER] ⚠️ Could not remove {path}: {e}")
    
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
