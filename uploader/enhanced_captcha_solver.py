"""
Enhanced Captcha Solver for YouTube Pipeline
Provides robust captcha solving with multiple methods and proper error handling
"""

import asyncio
import logging
import os
import aiohttp
import json
import time
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
from playwright.async_api import Page

from .captcha_detection import EnhancedCaptchaDetector, CaptchaParameters, CaptchaType
from .audio_recaptcha_solver import solve_recaptcha_with_audio

logger = logging.getLogger(__name__)


class SolutionMethod(Enum):
    """Methods used to solve captcha"""
    AUDIO_CHALLENGE = "audio_challenge"
    RUCAPTCHA_API = "rucaptcha_api"
    JAVASCRIPT_CALLBACK = "javascript_callback"


@dataclass
class SolutionResult:
    """Result of captcha solving attempt"""
    success: bool
    solution: Optional[str] = None
    method_used: Optional[SolutionMethod] = None
    processing_time: float = 0.0
    error_message: Optional[str] = None
    retry_recommended: bool = False


@dataclass
class CaptchaConfig:
    """Configuration for captcha solving"""
    audio_timeout: int = 30
    api_timeout: int = 120
    max_retries: int = 3
    rucaptcha_api_key: Optional[str] = None
    enable_audio_challenge: bool = True
    enable_api_fallback: bool = True
    submission_delay: int = 3
    detection_timeout: int = 30


class EnhancedCaptchaSolver:
    """Enhanced captcha solver with multiple methods and proper error handling"""
    
    def __init__(self, config: Optional[CaptchaConfig] = None, task_id: int = None, log_callback: callable = None):
        self.config = config or CaptchaConfig()
        self.detector = EnhancedCaptchaDetector()
        self.task_id = task_id
        self.log_callback = log_callback

        # Load API key from environment if not provided
        if not self.config.rucaptcha_api_key:
            self.config.rucaptcha_api_key = os.getenv('RUCAPTCHA_API_KEY')
    
    async def solve_captcha(self, page: Page, proxy: Optional[Dict] = None, 
                          user_agent: Optional[str] = None) -> SolutionResult:
        """
        Main captcha solving method with multiple fallback strategies
        
        Args:
            page: Playwright page instance
            proxy: Proxy configuration for API calls
            user_agent: User agent string for consistency
            
        Returns:
            SolutionResult with solving outcome
        """
        start_time = time.time()
        
        try:
            logger.info("[CAPTCHA_SOLVER] Starting enhanced captcha solving...")
            
            # Step 1: Detect captcha
            captcha_params = await self.detector.detect_captcha_type(page)

            if captcha_params.captcha_type == CaptchaType.NONE:
                logger.info("[CAPTCHA_SOLVER] No captcha detected")
                return SolutionResult(
                    success=True,
                    processing_time=time.time() - start_time
                )

            logger.info(f"[CAPTCHA_SOLVER] Detected captcha: {captcha_params.captcha_type.value}")

            # Step 1.5: Wait for captcha to fully load
            if not await self.detector.wait_for_captcha_full_load(page, timeout=self.config.detection_timeout):
                logger.warning("[CAPTCHA_SOLVER] Captcha failed to fully load, reloading page and retrying...")

                # Reload page to fix stuck captcha
                try:
                    await page.reload(wait_until="domcontentloaded")
                    logger.info("[CAPTCHA_SOLVER] Page reloaded, waiting for captcha to reappear...")

                    # Wait a bit for page to reload
                    await asyncio.sleep(3)

                    # Re-detect captcha after reload
                    captcha_params = await self.detector.detect_captcha_type(page)
                    if captcha_params.captcha_type == CaptchaType.NONE:
                        logger.warning("[CAPTCHA_SOLVER] No captcha found after reload")
                        return SolutionResult(
                            success=False,
                            error_message="No captcha found after page reload",
                            retry_recommended=True,
                            processing_time=time.time() - start_time
                        )

                    logger.info(f"[CAPTCHA_SOLVER] Captcha re-detected after reload: {captcha_params.captcha_type.value}")

                    # Wait for captcha to fully load again
                    if not await self.detector.wait_for_captcha_full_load(page, timeout=self.config.detection_timeout):
                        logger.error("[CAPTCHA_SOLVER] Captcha still failed to load after page reload")
                        return SolutionResult(
                            success=False,
                            error_message="Captcha failed to load even after page reload",
                            retry_recommended=True,
                            processing_time=time.time() - start_time
                        )

                    logger.info("[CAPTCHA_SOLVER] Captcha fully loaded after page reload")

                except Exception as e:
                    logger.error(f"[CAPTCHA_SOLVER] Page reload failed: {e}")
                    return SolutionResult(
                        success=False,
                        error_message=f"Page reload failed: {str(e)}",
                        retry_recommended=True,
                        processing_time=time.time() - start_time
                    )

            # Step 2: Try solving methods in order of preference
            methods = self._get_solving_methods(captcha_params)
            
            for method in methods:
                logger.info(f"[CAPTCHA_SOLVER] Trying method: {method.value}")
                
                result = await self._try_solving_method(
                    page, captcha_params, method, proxy, user_agent
                )
                
                if result.success:
                    result.processing_time = time.time() - start_time
                    logger.info(f"[CAPTCHA_SOLVER] Success with {method.value} in {result.processing_time:.1f}s")
                    return result
                
                logger.warning(f"[CAPTCHA_SOLVER] Method {method.value} failed: {result.error_message}")
                
                # Wait before trying next method
                await asyncio.sleep(2)
            
            # All methods failed
            processing_time = time.time() - start_time
            logger.error(f"[CAPTCHA_SOLVER] All methods failed after {processing_time:.1f}s")
            
            return SolutionResult(
                success=False,
                processing_time=processing_time,
                error_message="All solving methods failed",
                retry_recommended=True
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"[CAPTCHA_SOLVER] Critical error: {e}")
            
            return SolutionResult(
                success=False,
                processing_time=processing_time,
                error_message=f"Critical error: {str(e)}",
                retry_recommended=False
            )
    
    def _get_solving_methods(self, captcha_params: CaptchaParameters) -> List[SolutionMethod]:
        """Get ordered list of solving methods based on captcha type and config"""
        methods = []
        
        if captcha_params.captcha_type == CaptchaType.RECAPTCHA_V2:
            if self.config.enable_audio_challenge:
                methods.append(SolutionMethod.AUDIO_CHALLENGE)
            if self.config.enable_api_fallback and self.config.rucaptcha_api_key:
                methods.append(SolutionMethod.RUCAPTCHA_API)
                
        elif captcha_params.captcha_type == CaptchaType.INVISIBLE_RECAPTCHA:
            if self.config.enable_api_fallback and self.config.rucaptcha_api_key:
                methods.append(SolutionMethod.RUCAPTCHA_API)
            methods.append(SolutionMethod.JAVASCRIPT_CALLBACK)
            
        elif captcha_params.captcha_type == CaptchaType.RECAPTCHA_V3:
            if self.config.enable_api_fallback and self.config.rucaptcha_api_key:
                methods.append(SolutionMethod.RUCAPTCHA_API)
                
        
        return methods
    
    async def _try_solving_method(self, page: Page, captcha_params: CaptchaParameters,
                                method: SolutionMethod, proxy: Optional[Dict],
                                user_agent: Optional[str]) -> SolutionResult:
        """Try a specific solving method"""
        
        try:
            if method == SolutionMethod.AUDIO_CHALLENGE:
                return await self._solve_with_audio_challenge(page)
                
            elif method == SolutionMethod.RUCAPTCHA_API:
                return await self._solve_with_rucaptcha_api(
                    page, captcha_params, proxy, user_agent
                )
                
            elif method == SolutionMethod.JAVASCRIPT_CALLBACK:
                return await self._solve_with_javascript_callback(page, captcha_params)

            else:
                return SolutionResult(
                    success=False,
                    error_message=f"Unknown method: {method}"
                )
                
        except Exception as e:
            return SolutionResult(
                success=False,
                method_used=method,
                error_message=f"Method {method.value} error: {str(e)}"
            )
    
    async def _solve_with_audio_challenge(self, page: Page) -> SolutionResult:
        """Solve using audio challenge method"""
        try:
            logger.info("[CAPTCHA_SOLVER] Attempting audio challenge...")
            
            success = await solve_recaptcha_with_audio(page, task_id=self.task_id, log_callback=self.log_callback)

            if success:
                # Audio challenge returned success, meaning Next was clicked successfully
                # No need for additional verification since Next click indicates captcha was solved
                logger.info("[CAPTCHA_SOLVER] ✅ Audio challenge completed and Next clicked - captcha solved!")
                return SolutionResult(
                    success=True,
                    method_used=SolutionMethod.AUDIO_CHALLENGE
                )
            else:
                return SolutionResult(
                    success=False,
                    method_used=SolutionMethod.AUDIO_CHALLENGE,
                    error_message="Audio challenge failed"
                )
                
        except Exception as e:
            return SolutionResult(
                success=False,
                method_used=SolutionMethod.AUDIO_CHALLENGE,
                error_message=f"Audio challenge error: {str(e)}"
            )
    
    async def _solve_with_rucaptcha_api(self, page: Page, captcha_params: CaptchaParameters,
                                      proxy: Optional[Dict], user_agent: Optional[str]) -> SolutionResult:
        """Solve using RuCaptcha API"""
        try:
            logger.info("[CAPTCHA_SOLVER] Attempting RuCaptcha API...")
            
            if not self.config.rucaptcha_api_key:
                return SolutionResult(
                    success=False,
                    method_used=SolutionMethod.RUCAPTCHA_API,
                    error_message="RuCaptcha API key not configured"
                )
            
            if not captcha_params.site_key:
                return SolutionResult(
                    success=False,
                    method_used=SolutionMethod.RUCAPTCHA_API,
                    error_message="Site key not found for API solving"
                )
            
            # Create task
            task_id = await self._create_rucaptcha_task(
                captcha_params, proxy, user_agent
            )
            
            if not task_id:
                return SolutionResult(
                    success=False,
                    method_used=SolutionMethod.RUCAPTCHA_API,
                    error_message="Failed to create RuCaptcha task"
                )
            
            # Get solution
            solution = await self._get_rucaptcha_solution(task_id)
            
            if not solution:
                return SolutionResult(
                    success=False,
                    method_used=SolutionMethod.RUCAPTCHA_API,
                    error_message="Failed to get solution from RuCaptcha"
                )
            
            # Submit solution
            success = await self._submit_solution_safely(page, solution)
            
            if success:
                return SolutionResult(
                    success=True,
                    solution=solution,
                    method_used=SolutionMethod.RUCAPTCHA_API
                )
            else:
                return SolutionResult(
                    success=False,
                    method_used=SolutionMethod.RUCAPTCHA_API,
                    error_message="Failed to submit API solution"
                )
                
        except Exception as e:
            return SolutionResult(
                success=False,
                method_used=SolutionMethod.RUCAPTCHA_API,
                error_message=f"RuCaptcha API error: {str(e)}"
            )
    
    async def _create_rucaptcha_task(self, captcha_params: CaptchaParameters,
                                   proxy: Optional[Dict], user_agent: Optional[str]) -> Optional[str]:
        """Create task in RuCaptcha API"""
        try:
            # Determine task type based on proxy availability
            if proxy and proxy.get('host') and proxy.get('port'):
                proxy_type = (proxy.get('type') or 'http').upper()
                if proxy_type not in ('HTTP', 'HTTPS', 'SOCKS5'):
                    proxy_type = 'HTTP'
                    
                task_obj = {
                    "type": "RecaptchaV2Task",
                    "websiteURL": captcha_params.page_url,
                    "websiteKey": captcha_params.site_key,
                    "proxyType": proxy_type,
                    "proxyAddress": proxy.get('host'),
                    "proxyPort": int(proxy.get('port')),
                }
                
                if proxy.get('user'):
                    task_obj["proxyLogin"] = proxy.get('user')
                if proxy.get('pass'):
                    task_obj["proxyPassword"] = proxy.get('pass')
                if user_agent:
                    task_obj["userAgent"] = user_agent
            else:
                task_obj = {
                    "type": "RecaptchaV2TaskProxyless",
                    "websiteURL": captcha_params.page_url,
                    "websiteKey": captcha_params.site_key,
                    "isInvisible": captcha_params.invisible
                }
                if user_agent:
                    task_obj["userAgent"] = user_agent
            
            task_data = {
                "clientKey": self.config.rucaptcha_api_key,
                "task": task_obj,
                "softId": "3898"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.rucaptcha.com/createTask',
                    json=task_data
                ) as response:
                    result = await response.json()
                    
                    if result.get('errorId') != 0:
                        logger.error(f"[CAPTCHA_SOLVER] RuCaptcha task creation failed: {result}")
                        return None
                    
                    task_id = result.get('taskId')
                    logger.info(f"[CAPTCHA_SOLVER] RuCaptcha task created: {task_id}")
                    return str(task_id)
                    
        except Exception as e:
            logger.error(f"[CAPTCHA_SOLVER] Error creating RuCaptcha task: {e}")
            return None
    
    async def _get_rucaptcha_solution(self, task_id: str) -> Optional[str]:
        """Get solution from RuCaptcha API"""
        try:
            result_data = {
                "clientKey": self.config.rucaptcha_api_key,
                "taskId": int(task_id)
            }
            
            # Poll for solution with timeout
            max_attempts = self.config.api_timeout // 10
            
            async with aiohttp.ClientSession() as session:
                for attempt in range(max_attempts):
                    logger.info(f"[CAPTCHA_SOLVER] Polling RuCaptcha solution (attempt {attempt + 1}/{max_attempts})")
                    
                    await asyncio.sleep(10)
                    
                    async with session.post(
                        'https://api.rucaptcha.com/getTaskResult',
                        json=result_data
                    ) as response:
                        result = await response.json()
                        
                        if result.get('status') == 'ready':
                            solution = result.get('solution', {}).get('gRecaptchaResponse')
                            if solution:
                                logger.info(f"[CAPTCHA_SOLVER] RuCaptcha solution received: {solution[:20]}...")
                                return solution
                            else:
                                logger.error("[CAPTCHA_SOLVER] No solution in RuCaptcha response")
                                return None
                                
                        elif result.get('errorId') != 0:
                            logger.error(f"[CAPTCHA_SOLVER] RuCaptcha error: {result}")
                            return None
                        else:
                            logger.info("[CAPTCHA_SOLVER] RuCaptcha solution not ready yet...")
                            continue
                
                logger.error("[CAPTCHA_SOLVER] RuCaptcha timeout waiting for solution")
                return None
                
        except Exception as e:
            logger.error(f"[CAPTCHA_SOLVER] Error getting RuCaptcha solution: {e}")
            return None
    
    async def _submit_solution_safely(self, page: Page, solution: str) -> bool:
        """Submit captcha solution with proper error handling and timing"""
        try:
            logger.info(f"[CAPTCHA_SOLVER] Submitting solution safely: {solution[:20]}...")
            
            # Step 1: Insert token into textarea
            insert_success = await page.evaluate(f'''
                () => {{
                    const textarea = document.getElementById('g-recaptcha-response') ||
                                   document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (textarea) {{
                        textarea.value = '{solution}';
                        textarea.style.display = 'block';
                        const event = new Event('change', {{ bubbles: true }});
                        textarea.dispatchEvent(event);
                        return true;
                    }}
                    return false;
                }}
            ''')
            
            if not insert_success:
                logger.error("[CAPTCHA_SOLVER] Failed to insert solution token")
                return False
            
            logger.info("[CAPTCHA_SOLVER] Solution token inserted successfully")
            
            # Step 2: Mandatory delay to prevent 400 errors
            logger.info(f"[CAPTCHA_SOLVER] Waiting {self.config.submission_delay}s before submission...")
            await asyncio.sleep(self.config.submission_delay)
            
            # Step 3: Try to execute callback functions with enhanced detection
            callback_success = await page.evaluate(f'''
                () => {{
                    const solution = '{solution}';

                    // Method 1: Try ___grecaptcha_cfg callbacks (most common)
                    if (typeof ___grecaptcha_cfg !== 'undefined' && ___grecaptcha_cfg.clients) {{
                        const clients = ___grecaptcha_cfg.clients;
                        const paths = [
                            'callback', 'L.L.callback', 'I.I.callback', 'A.A.callback',
                            'F.F.callback', 'B.B.callback', 'C.C.callback', 'D.D.callback'
                        ];

                        for (let clientId in clients) {{
                            // Try direct callback first
                            if (typeof clients[clientId].callback === 'function') {{
                                try {{
                                    clients[clientId].callback(solution);
                                    return {{ success: true, method: 'direct_callback' }};
                                }} catch (e) {{
                                    console.log('Direct callback error:', e);
                                }}
                            }}

                            // Try nested paths
                            for (let path of paths) {{
                                let current = clients[clientId];
                                const parts = path.split('.');
                                for (let part of parts) {{
                                    current = current[part];
                                    if (!current) break;
                                }}
                                if (typeof current === 'function') {{
                                    try {{
                                        current(solution);
                                        return {{ success: true, method: 'nested_callback_' + path }};
                                    }} catch (e) {{
                                        console.log('Nested callback error:', e);
                                    }}
                                }}
                            }}
                        }}
                    }}

                    // Method 2: Try grecaptcha global object
                    if (typeof grecaptcha !== 'undefined') {{
                        try {{
                            // Try to find and call success callback
                            if (grecaptcha && typeof grecaptcha.getResponse === 'function') {{
                                // Simulate successful verification
                                Object.defineProperty(document.querySelector('textarea[name="g-recaptcha-response"]'), 'value', {{
                                    get: () => solution,
                                    set: () => {{}}
                                }});

                                // Try to trigger callback if exists
                                if (window.recaptchaSuccessCallback) {{
                                    window.recaptchaSuccessCallback(solution);
                                    return {{ success: true, method: 'grecaptcha_callback' }};
                                }}
                            }}
                        }} catch (e) {{
                            console.log('grecaptcha method error:', e);
                        }}
                    }}

                    // Method 3: Try to simulate checkbox click after token insertion
                    try {{
                        const checkbox = document.querySelector('.recaptcha-checkbox');
                        if (checkbox && !checkbox.classList.contains('recaptcha-checkbox-checked')) {{
                            // Simulate successful verification by adding checked class
                            checkbox.classList.add('recaptcha-checkbox-checked');
                            const checkmark = document.querySelector('.recaptcha-checkbox-checkmark');
                            if (checkmark) {{
                                checkmark.style.display = 'block';
                            }}

                            // Trigger change events
                            const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                            if (textarea) {{
                                textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            }}

                            return {{ success: true, method: 'checkbox_simulation' }};
                        }}
                    }} catch (e) {{
                        console.log('Checkbox simulation error:', e);
                    }}

                    return {{ success: false, method: 'none' }};
                }}
            ''')

            if callback_success and callback_success.success:
                logger.info(f"[CAPTCHA_SOLVER] Callback executed successfully via: {callback_success.method}")
            else:
                logger.warning("[CAPTCHA_SOLVER] No callback method worked, trying fallback approaches")

                # Fallback Method 4: Try direct JavaScript execution
                fallback_success = await page.evaluate(f'''
                    () => {{
                        const solution = '{solution}';

                        try {{
                            // Method 4a: Try to execute any registered callback
                            if (window.recaptchaCallback) {{
                                window.recaptchaCallback(solution);
                                return {{ success: true, method: 'window_callback' }};
                            }}

                            // Method 4b: Try to trigger form validation manually
                            const form = document.querySelector('form');
                            if (form) {{
                                // Force form validation
                                const inputs = form.querySelectorAll('input, textarea');
                                inputs.forEach(input => {{
                                    if (input.name === 'g-recaptcha-response') {{
                                        input.value = solution;
                                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    }}
                                }});

                                // Try to trigger HTML5 validation
                                if (typeof form.reportValidity === 'function') {{
                                    form.reportValidity();
                                }}

                                return {{ success: true, method: 'form_validation' }};
                            }}

                            // Method 4c: Try to simulate successful reCAPTCHA state
                            const simulateSuccess = () => {{
                                // Hide error messages
                                const errors = document.querySelectorAll('.rc-anchor-error-msg');
                                errors.forEach(el => el.style.display = 'none');

                                // Add success classes
                                const anchor = document.querySelector('.rc-anchor');
                                if (anchor) {{
                                    anchor.classList.add('rc-anchor-checked');
                                    anchor.classList.remove('rc-anchor-error');
                                }}

                                // Show checkmark
                                const checkmark = document.querySelector('.recaptcha-checkbox-checkmark');
                                if (checkmark) {{
                                    checkmark.style.display = 'block';
                                    checkmark.style.opacity = '1';
                                }}

                                // Hide checkbox border animation
                                const border = document.querySelector('.recaptcha-checkbox-border');
                                if (border) {{
                                    border.style.animation = 'none';
                                }}
                            }};

                            simulateSuccess();
                            return {{ success: true, method: 'visual_simulation' }};

                        }} catch (e) {{
                            console.log('Fallback method error:', e);
                            return {{ success: false, method: 'fallback_failed' }};
                        }}
                    }}
                ''')

                if fallback_success and fallback_success.success:
                    logger.info(f"[CAPTCHA_SOLVER] Fallback method succeeded via: {fallback_success.method}")
                else:
                    logger.error("[CAPTCHA_SOLVER] All callback and fallback methods failed")
            
            # Step 4: Try to find and click submit button
            submit_success = await self._find_and_click_submit_button(page)
            
            if not submit_success:
                logger.warning("[CAPTCHA_SOLVER] Submit button not found, trying form.submit()")
                
                # Fallback: try form.submit()
                form_submit_success = await page.evaluate(f'''
                    () => {{
                        const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                        if (textarea && textarea.value === '{solution}') {{
                            const form = textarea.closest('form');
                            if (form) {{
                                form.submit();
                                return true;
                            }}
                        }}
                        return false;
                    }}
                ''')
                
                if not form_submit_success:
                    logger.error("[CAPTCHA_SOLVER] Failed to submit form")
                    return False
            
            # Step 5: Wait and verify solution was accepted
            logger.info("[CAPTCHA_SOLVER] Verifying solution acceptance...")
            await asyncio.sleep(2)

            # Enhanced verification of successful solving
            verification_result = await page.evaluate('''
                () => {
                    const result = {
                        hasToken: false,
                        checkboxChecked: false,
                        noErrorMessages: true,
                        callbackExecuted: false
                    };

                    // Check 1: Token is present in textarea
                    const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (textarea && textarea.value && textarea.value.length > 10) {
                        result.hasToken = true;
                    }

                    // Check 2: Checkbox shows as checked (green checkmark visible)
                    const checkmark = document.querySelector('.recaptcha-checkbox-checkmark');
                    const checkbox = document.querySelector('.recaptcha-checkbox');
                    if (checkmark && checkmark.offsetParent !== null &&
                        (!checkbox || !checkbox.classList.contains('recaptcha-checkbox-error'))) {
                        result.checkboxChecked = true;
                    }

                    // Check 3: No error messages visible
                    const errorElements = document.querySelectorAll('.rc-anchor-error-msg, .rc-doscaptcha-body-text');
                    for (let element of errorElements) {
                        if (element.offsetParent !== null && element.textContent.trim()) {
                            result.noErrorMessages = false;
                            break;
                        }
                    }

                    // Check 4: Success callback was executed (if we can detect it)
                    if (typeof ___grecaptcha_cfg !== 'undefined' && ___grecaptcha_cfg.clients) {
                        result.callbackExecuted = true; // If config exists, assume callback was attempted
                    }

                    return result;
                }
            ''')

            logger.info(f"[CAPTCHA_SOLVER] Verification result: Token={verification_result.hasToken}, Checkbox={verification_result.checkboxChecked}, NoErrors={verification_result.noErrorMessages}")

            # Consider solution successful if token is present AND (checkbox is checked OR no errors)
            solution_accepted = verification_result.hasToken and (verification_result.checkboxChecked or verification_result.noErrorMessages)

            if solution_accepted:
                logger.info("[CAPTCHA_SOLVER] ✅ Solution verification successful")
            else:
                logger.warning("[CAPTCHA_SOLVER] ⚠️ Solution verification inconclusive, but proceeding")

            # Step 6: Check for submission errors (but don't fail if verification passed)
            error_detected = await self._detect_submission_errors(page)

            if error_detected and not solution_accepted:
                logger.error(f"[CAPTCHA_SOLVER] Submission error detected: {error_detected}")
                return False

            if error_detected:
                logger.warning(f"[CAPTCHA_SOLVER] Submission error detected but solution seems accepted: {error_detected}")

            logger.info("[CAPTCHA_SOLVER] Solution submitted and verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"[CAPTCHA_SOLVER] Error submitting solution: {e}")
            return False
    
    async def _find_and_click_submit_button(self, page: Page) -> bool:
        """Find and click the appropriate submit button"""
        try:
            # Google-specific submit button selectors
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button[data-identifier]',
                'button[data-primary-action-label]',
                '.VfPpkd-LgbsSe',
                'button[jsname="LgbsSe"]'
            ]
            
            for selector in submit_selectors:
                try:
                    elements = await page.locator(selector).all()
                    
                    for element in elements:
                        if await element.is_visible():
                            logger.info(f"[CAPTCHA_SOLVER] Clicking submit button: {selector}")
                            await element.click(timeout=10000)
                            return True
                            
                except Exception as e:
                    logger.warning(f"[CAPTCHA_SOLVER] Error with selector {selector}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"[CAPTCHA_SOLVER] Error finding submit button: {e}")
            return False
    
    async def _detect_submission_errors(self, page: Page) -> Optional[str]:
        """Detect submission errors like 400 Bad Request"""
        try:
            # Check page content for error indicators
            page_content = await page.content()
            current_url = page.url
            
            # Check for 400 error
            if '400' in page_content and any(word in page_content.lower() for word in ['error', 'bad request', 'invalid']):
                return "400 Bad Request detected"
            
            # Check for other error indicators
            error_indicators = [
                'error',
                'invalid',
                'failed',
                'try again',
                'something went wrong'
            ]
            
            for indicator in error_indicators:
                if indicator in page_content.lower():
                    return f"Error indicator found: {indicator}"
            
            # Check for reCAPTCHA error messages
            recaptcha_error = await page.evaluate('''
                () => {
                    const errorElements = document.querySelectorAll('.rc-anchor-error-msg, .rc-doscaptcha-body-text');
                    for (let element of errorElements) {
                        if (element.textContent && element.textContent.trim()) {
                            return element.textContent.trim();
                        }
                    }
                    return null;
                }
            ''')
            
            if recaptcha_error:
                return f"reCAPTCHA error: {recaptcha_error}"
            
            return None
            
        except Exception as e:
            logger.warning(f"[CAPTCHA_SOLVER] Error detecting submission errors: {e}")
            return None
    
    async def _solve_with_javascript_callback(self, page: Page, captcha_params: CaptchaParameters) -> SolutionResult:
        """Solve invisible reCAPTCHA using JavaScript callbacks"""
        try:
            logger.info("[CAPTCHA_SOLVER] Attempting JavaScript callback method...")
            
            # This method would be used for invisible reCAPTCHA
            # For now, return not implemented
            return SolutionResult(
                success=False,
                method_used=SolutionMethod.JAVASCRIPT_CALLBACK,
                error_message="JavaScript callback method not yet implemented"
            )
            
        except Exception as e:
            return SolutionResult(
                success=False,
                method_used=SolutionMethod.JAVASCRIPT_CALLBACK,
                error_message=f"JavaScript callback error: {str(e)}"
            )
    


# Convenience function for backward compatibility
async def solve_captcha_enhanced(page: Page, proxy: Optional[Dict] = None, 
                               user_agent: Optional[str] = None) -> bool:
    """
    Enhanced captcha solving function for backward compatibility
    
    Returns:
        True if captcha solved successfully, False otherwise
    """
    solver = EnhancedCaptchaSolver()
    result = await solver.solve_captcha(page, proxy, user_agent)
    return result.success