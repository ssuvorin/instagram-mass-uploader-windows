from __future__ import annotations
from typing import Optional, Callable
from instagrapi import Client
from instagrapi.exceptions import (
    TwoFactorRequired, 
    ChallengeRequired, 
    LoginRequired, 
    ClientForbiddenError,
    ClientUnauthorizedError,
    RateLimitError,
    ClientConnectionError,
    ClientRequestTimeout,
    ChallengeError,
    ProxyAddressIsBlocked
)  # type: ignore
from .code_providers import TwoFactorProvider, NullTwoFactorProvider
import logging
import time
import random
from datetime import datetime

# Import proxy manager
try:
    from uploader.proxy_manager import proxy_manager
    PROXY_MANAGER_AVAILABLE = True
except ImportError:
    PROXY_MANAGER_AVAILABLE = False

log = logging.getLogger('insta.auth')


class IGAuthService:
    def __init__(self, provider: Optional[TwoFactorProvider] = None) -> None:
        self.provider = provider or NullTwoFactorProvider()
        self.auth_attempts = {}  # Track auth attempts per username
        self.last_auth_time = {}  # Track last successful auth per username

    def _get_human_delay(self, context: str = 'auth', base_delay: float = 1.0) -> float:
        """Generate human-like delays based on context and time"""
        # Context-based delays
        context_delays = {
            'auth': (2.0, 5.0),      # 2-5 seconds for auth operations
            'retry': (5.0, 15.0),    # 5-15 seconds for retries
            'challenge': (3.0, 8.0), # 3-8 seconds for challenges
            'session_check': (1.0, 3.0), # 1-3 seconds for session checks
            'error_recovery': (10.0, 30.0) # 10-30 seconds for error recovery
        }
        
        min_delay, max_delay = context_delays.get(context, (1.0, 3.0))
        
        # Time-based adjustments
        current_hour = datetime.now().hour
        if 2 <= current_hour <= 6:  # Night time - slower
            min_delay *= 1.5
            max_delay *= 2.0
        elif 7 <= current_hour <= 10:  # Morning - moderate
            min_delay *= 1.2
            max_delay *= 1.5
        
        # Add randomness
        delay = random.uniform(min_delay, max_delay)
        return round(delay, 2)

    def _is_rate_limited(self, username: str) -> bool:
        """Check if we're being rate limited for this username"""
        if username not in self.auth_attempts:
            return False
        
        attempts = self.auth_attempts[username]
        current_time = time.time()
        
        # Check if we've made too many attempts recently
        recent_attempts = [t for t in attempts if current_time - t < 300]  # Last 5 minutes
        return len(recent_attempts) >= 5

    def _record_auth_attempt(self, username: str, success: bool = False):
        """Record authentication attempt"""
        current_time = time.time()
        
        if username not in self.auth_attempts:
            self.auth_attempts[username] = []
        
        self.auth_attempts[username].append(current_time)
        
        if success:
            self.last_auth_time[username] = current_time
        
        # Clean old attempts (older than 1 hour)
        self.auth_attempts[username] = [
            t for t in self.auth_attempts[username] 
            if current_time - t < 3600
        ]

    def ensure_logged_in(self, cl: Client, username: str, password: str, on_log: Optional[Callable[[str], None]] = None) -> bool:
        """Enhanced authentication with retry logic, human delays, and better error handling"""
        log.debug("Ensure logged in for %s", username)
        if on_log:
            on_log(f"auth: ensure session for {username}")
        
        # Check for rate limiting
        if self._is_rate_limited(username):
            delay = self._get_human_delay('error_recovery')
            log.warning(f"Rate limited for {username}, waiting {delay}s")
            if on_log:
                on_log(f"auth: rate limited, waiting {delay}s")
            time.sleep(delay)
            return False
        
        # Set challenge handler early
        try:
            def _prelogin_handler(_username, _choice):
                return self.provider.get_challenge_code(username, method="email") or ""
            cl.challenge_code_handler = _prelogin_handler
        except Exception:
            pass
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Record attempt
                self._record_auth_attempt(username)
                
                # First, try to check if already authenticated
                try:
                    # Add delay before session check
                    delay = self._get_human_delay('session_check')
                    time.sleep(delay)
                    
                    cl.user_id_from_username(username)
                    log.debug("Already authenticated as %s", username)
                    if on_log:
                        on_log("auth: already authenticated")
                    
                    # Record successful auth
                    self._record_auth_attempt(username, success=True)
                    return True
                    
                except LoginRequired as e:
                    log.debug("LoginRequired for %s: %s", username, e)
                    if on_log:
                        on_log(f"auth: precheck failed: {e}")
                    # Diagnostics: dump last_json and raw last_response if available
                    try:
                        lj = getattr(cl, 'last_json', None)
                        if lj:
                            log.debug("[AUTH] last_json on precheck: %s", lj)
                        lr = getattr(getattr(cl, 'private', None), 'last_response', None)
                        if lr is not None:
                            try:
                                status = getattr(lr, 'status_code', None)
                                text = getattr(lr, 'text', '')
                                log.debug("[AUTH] last_response.status: %s", status)
                                log.debug("[AUTH] last_response.text: %s", text[:2000])
                            except Exception:
                                pass
                    except Exception:
                        pass
                    
                    # Proceed to login attempt in the same iteration (no break)
                    # Small human-like pause before immediate relogin
                    try:
                        delay = self._get_human_delay('auth')
                        if on_log:
                            on_log(f"auth: session expired, trying relogin after {delay}s")
                        time.sleep(delay)
                    except Exception:
                        pass
                    
                except (ClientForbiddenError, ClientUnauthorizedError) as e:
                    log.debug("Authentication error for %s: %s", username, e)
                    if on_log:
                        on_log(f"auth: authentication error: {e}")
                    
                    # These errors usually mean we need to re-login
                    delay = self._get_human_delay('retry')
                    if attempt < max_retries - 1:
                        log.info(f"Auth error for {username}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        if on_log:
                            on_log(f"auth: retrying in {delay}s")
                        time.sleep(delay)
                        continue
                    else:
                        return False
                        
                except (ClientConnectionError, ClientRequestTimeout) as e:
                    log.debug("Network error for %s: %s", username, e)
                    if on_log:
                        on_log(f"auth: network error: {e}")
                    
                    # Network errors - retry with longer delay
                    delay = self._get_human_delay('error_recovery')
                    if attempt < max_retries - 1:
                        log.warning(f"Network error for {username}, retrying in {delay}s")
                        if on_log:
                            on_log(f"auth: network error, retrying in {delay}s")
                        time.sleep(delay)
                        continue
                    else:
                        return False
                        
                except Exception as e:
                    error_str = str(e).lower()
                    log.debug("Auth check failed for %s: %s", username, e)
                    
                    # Handle generic errors
                    if attempt < max_retries - 1:
                        delay = self._get_human_delay('retry')
                        log.warning(f"Unexpected auth error for {username}: {e}, retrying in {delay}s")
                        if on_log:
                            on_log(f"auth: unexpected error, retrying in {delay}s")
                        time.sleep(delay)
                        continue
                    else:
                        if on_log:
                            on_log(f"auth: precheck failed: {e}")
                        return False
                
                # Attempt login
                try:
                    delay = self._get_human_delay('auth')
                    time.sleep(delay)
                    
                    log.debug("Login attempt for %s (attempt %d/%d)", username, attempt + 1, max_retries)
                    if on_log:
                        on_log("auth: login")
                    
                    cl.login(username, password)
                    log.debug("Login success for %s", username)
                    if on_log:
                        on_log("auth: login ok")
                    
                    # Record successful auth
                    self._record_auth_attempt(username, success=True)
                    return True
                    
                except TwoFactorRequired:
                    return self._handle_two_factor_auth(cl, username, password, on_log)
                    
                except ChallengeRequired:
                    return self._handle_challenge_auth(cl, username, password, on_log)
                    
                except RateLimitError as e:
                    log.debug("RateLimitError during login for %s: %s", username, e)
                    if on_log:
                        on_log(f"auth: rate limited during login: {e}")
                    
                    delay = self._get_human_delay('error_recovery')
                    log.warning(f"Rate limited during login for {username}, waiting {delay}s")
                    if on_log:
                        on_log(f"auth: rate limited during login, waiting {delay}s")
                    time.sleep(delay)
                    
                    if attempt < max_retries - 1:
                        continue
                    return False
                    
                except ChallengeError as e:
                    log.debug("ChallengeError during login for %s: %s", username, e)
                    if on_log:
                        on_log(f"auth: challenge during login: {e}")
                    
                    # Try challenge resolution
                    return self._handle_challenge_auth(cl, username, password, on_log)
                    
                except ProxyAddressIsBlocked as e:
                    log.error("ProxyAddressIsBlocked for %s: %s", username, e)
                    if on_log:
                        on_log(f"auth: proxy blocked: {e}")
                    
                    # Don't retry - proxy is blocked
                    return False
                    
                except (ClientConnectionError, ClientRequestTimeout) as e:
                    log.debug("Network error during login for %s: %s", username, e)
                    if on_log:
                        on_log(f"auth: network error during login: {e}")
                    
                    delay = self._get_human_delay('error_recovery')
                    if attempt < max_retries - 1:
                        log.warning(f"Network error during login for {username}, retrying in {delay}s")
                        if on_log:
                            on_log(f"auth: network error, retrying in {delay}s")
                        time.sleep(delay)
                        continue
                    return False
                    
                except Exception as e:
                    error_str = str(e).lower()
                    log.debug("Login failed for %s: %s", username, e)
                    
                    if on_log:
                        on_log(f"auth: login failed: {e}")
                    # Diagnostics on login failure
                    try:
                        lj = getattr(cl, 'last_json', None)
                        if lj:
                            log.debug("[AUTH] last_json on login failure: %s", lj)
                        lr = getattr(getattr(cl, 'private', None), 'last_response', None)
                        if lr is not None:
                            try:
                                status = getattr(lr, 'status_code', None)
                                text = getattr(lr, 'text', '')
                                log.debug("[AUTH] last_response.status: %s", status)
                                log.debug("[AUTH] last_response.text: %s", text[:2000])
                            except Exception:
                                pass
                    except Exception:
                        pass
                    
                    # Handle generic errors with exponential backoff
                    if attempt < max_retries - 1:
                        delay = self._get_human_delay('retry') * (2 ** attempt)
                        log.info(f"Login failed for {username}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        if on_log:
                            on_log(f"auth: retrying in {delay}s")
                        time.sleep(delay)
                        continue
                    
                    return False
                    
            except Exception as e:
                log.error(f"Unexpected error during auth for {username}: {e}")
                if on_log:
                    on_log(f"auth: unexpected error: {e}")
                
                if attempt < max_retries - 1:
                    delay = self._get_human_delay('error_recovery')
                    time.sleep(delay)
                    continue
                
                return False
        
        return False

    def _handle_two_factor_auth(self, cl: Client, username: str, password: str, on_log: Optional[Callable[[str], None]] = None) -> bool:
        """Handle two-factor authentication"""
        log.debug("TwoFactorRequired for %s", username)
        if on_log:
            on_log("auth: 2fa required (TOTP)")
        
        totp = self.provider.get_totp(username) or ""
        log.debug("TOTP obtained: %s", "yes" if totp else "no")
        if on_log:
            on_log(f"auth: totp {'ok' if totp else 'missing'}")
        
        if not totp:
            return False
        
        try:
            delay = self._get_human_delay('auth')
            time.sleep(delay)
            
            cl.login(username, password, verification_code=totp)
            log.debug("2FA login success for %s", username)
            if on_log:
                on_log("auth: 2fa ok")
            
            self._record_auth_attempt(username, success=True)
            return True
            
        except Exception as e:
            log.debug("2FA login failed for %s: %s", username, e)
            if on_log:
                on_log(f"auth: 2fa failed: {e}")
            return False

    def _handle_challenge_auth(self, cl: Client, username: str, password: str, on_log: Optional[Callable[[str], None]] = None) -> bool:
        """Handle challenge authentication (email verification, etc.)"""
        log.debug("ChallengeRequired for %s", username)
        if on_log:
            on_log("auth: challenge required (email)")
        
        try:
            # Provide code handler
            def _handler(_username, _choice):
                return self.provider.get_challenge_code(username, method="email") or ""
            
            try:
                cl.challenge_code_handler = _handler
            except Exception:
                pass

            # Try native resolver first
            resolver = getattr(cl, 'challenge_resolve', None)
            if callable(resolver):
                delay = self._get_human_delay('challenge')
                time.sleep(delay)
                
                ok = resolver(getattr(cl, 'last_json', {}) or {})
                if ok:
                    if on_log:
                        on_log("auth: challenge ok (native)")
                    
                    delay = self._get_human_delay('auth')
                    time.sleep(delay)
                    
                    try:
                        cl.login(username, password, relogin=True)
                        if on_log:
                            on_log("auth: login ok (post-challenge)")
                        
                        self._record_auth_attempt(username, success=True)
                        return True
                        
                    except Exception as relog_err:
                        log.debug("Post-challenge login failed for %s: %s", username, relog_err)
                        if on_log:
                            on_log(f"auth: post-challenge login failed: {relog_err}")
                        return False

            # Try simple resolver
            cur = getattr(cl, 'last_json', {}) or {}
            api_path = (cur.get('challenge') or {}).get('api_path') or cur.get('challenge_url') or ''
            if isinstance(api_path, str) and api_path.startswith('/challenge/'):
                simple = getattr(cl, 'challenge_resolve_simple', None)
                if callable(simple):
                    delay = self._get_human_delay('challenge')
                    time.sleep(delay)
                    
                    simple(api_path)
                    if on_log:
                        on_log("auth: challenge ok (simple)")
                    
                    delay = self._get_human_delay('auth')
                    time.sleep(delay)
                    
                    try:
                        cl.login(username, password, relogin=True)
                        if on_log:
                            on_log("auth: login ok (post-challenge)")
                        
                        self._record_auth_attempt(username, success=True)
                        return True
                        
                    except Exception as relog2_err:
                        log.debug("Post-challenge login failed for %s: %s", username, relog2_err)
                        if on_log:
                            on_log(f"auth: post-challenge login failed: {relog2_err}")
                        return False

            if on_log:
                on_log("auth: challenge not resolved")
            return False
            
        except Exception as e:
            log.debug("Challenge resolve failed for %s: %s", username, e)
            if on_log:
                on_log(f"auth: challenge failed: {e}")
            return False 