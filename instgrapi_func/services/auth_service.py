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
import secrets
import string

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
        # Ensure auth operations for a given client are serialized
        try:
            import threading
            self._client_lock = threading.RLock()
        except Exception:
            self._client_lock = None

    def _generate_strong_password(self, length: int = 16) -> str:
        """Generate strong password with upper/lower/digits/symbols."""
        alphabet_lower = string.ascii_lowercase
        alphabet_upper = string.ascii_uppercase
        digits = string.digits
        symbols = "!@#$%^&*()-_=+[]{};:,.?"  # safe set
        # Ensure at least one of each class
        base = [
            secrets.choice(alphabet_lower),
            secrets.choice(alphabet_upper),
            secrets.choice(digits),
            secrets.choice(symbols),
        ]
        pool = alphabet_lower + alphabet_upper + digits + symbols
        base += [secrets.choice(pool) for _ in range(max(8, length) - len(base))]
        secrets.SystemRandom().shuffle(base)
        return "".join(base)[:max(8, length)]

    def _get_user_info_v1(self, cl: Client):
        """Fetch user info via private v1 endpoint only (no GQL/public fallbacks)."""
        try:
            uid = getattr(cl, 'user_id', None)
        except Exception:
            uid = None
        if not uid:
            return None
        # Prefer direct private_request to avoid library fallbacks
        try:
            result = cl.private_request(f"users/{uid}/info/")  # type: ignore[attr-defined]
            return result.get('user') if isinstance(result, dict) else result
        except Exception:
            return None

    def _get_username(self, info) -> Optional[str]:
        try:
            if info is None:
                return None
            uname = getattr(info, 'username', None)
            if uname:
                return str(uname)
            if isinstance(info, dict):
                return str(info.get('username') or '') or None
        except Exception:
            return None
        return None

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

        # Serialize precheck/login/verify for this client to avoid concurrent calls using a simple flag on client
        # Busy-wait briefly if another auth is in progress for this client
        wait_start = time.time()
        while getattr(cl, '_auth_in_progress', False) and time.time() - wait_start < 30:
            time.sleep(0.1)
        setattr(cl, '_auth_in_progress', True)

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
        
        # Install password change handler: generate new password and persist to DB
        try:
            from uploader.models import InstagramAccount  # local import to avoid circulars
            def _change_password_handler(_username: str) -> Optional[str]:
                try:
                    new_pwd = self._generate_strong_password()
                    # Persist in DB
                    acc = InstagramAccount.objects.filter(username=username).first()
                    if acc:
                        acc.password = new_pwd
                        acc.save(update_fields=['password', 'updated_at'])
                    # store on client for subsequent relogin
                    try:
                        setattr(cl, '_new_password', new_pwd)
                    except Exception:
                        pass
                    return new_pwd
                except Exception:
                    return None
            cl.change_password_handler = _change_password_handler  # type: ignore[attr-defined]
        except Exception:
            pass
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Record attempt
                self._record_auth_attempt(username)
                
                # Strict authentication check with timeout protection
                try:
                    # Add delay before session check
                    delay = self._get_human_delay('session_check')
                    time.sleep(delay)
                    
                    # Use threading.Timer for timeout in worker threads
                    import threading
                    import queue
                    
                    result_queue = queue.Queue()
                    timeout_occurred = threading.Event()
                    
                    def call_account_info():
                        try:
                            # Prefer stable private v1 endpoint to avoid flaky 403 from accounts/current_user
                            v1_info = self._get_user_info_v1(cl)
                            if not timeout_occurred.is_set():
                                result_queue.put(('success', v1_info))
                        except Exception as e:
                            if not timeout_occurred.is_set():
                                result_queue.put(('error', e))
                    
                    # Start the account_info call in a separate thread
                    thread = threading.Thread(target=call_account_info)
                    thread.daemon = True
                    thread.start()
                    
                    # Wait for result with timeout
                    try:
                        result_type, result_data = result_queue.get(timeout=15)  # 15 second timeout
                        
                        if result_type == 'success':
                            account_info = result_data
                            # Accept dict with user or object with username
                            uname = self._get_username(account_info)
                            if uname:
                                log.debug("Session validated via users/{uid}/info for %s", uname)
                                if on_log:
                                    on_log("auth: session validated")
                                self._record_auth_attempt(username, success=True)
                                return True
                            else:
                                raise LoginRequired("v1 user info returned invalid response")
                        else:
                            # Re-raise the exception from account_info
                            raise result_data
                            
                    except queue.Empty:
                        # Timeout occurred
                        timeout_occurred.set()
                        log.warning("account_info() timed out after 15s for %s", username)
                        if on_log:
                            on_log("auth: session check timeout, proceeding to login")
                        raise LoginRequired("Session check timeout - proceeding to login")
                        
                except Exception as e:
                    # Any failure in account_info() means we need to login
                    log.debug("Session validation failed via account_info: %s", e)
                    if on_log:
                        on_log(f"auth: session check failed: {e}")
                    
                    # Check if this is already a LoginRequired exception
                    if isinstance(e, LoginRequired):
                        log.debug("LoginRequired for %s: %s", username, e)
                        if on_log:
                            on_log(f"auth: precheck failed: {e}")
                        # Diagnostics: log only status codes, not full JSON responses
                        try:
                            lr = getattr(getattr(cl, 'private', None), 'last_response', None)
                            if lr is not None:
                                try:
                                    status = getattr(lr, 'status_code', None)
                                    log.debug("[AUTH] last_response.status: %s", status)
                                    # Skip logging full response text to avoid huge JSON dumps
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        # Break out of the loop to proceed to login
                        break
                    else:
                        # Convert other exceptions to LoginRequired and break to login
                        log.debug("Converting exception to LoginRequired: %s", e)
                        if on_log:
                            on_log(f"auth: session validation failed, proceeding to login")
                        break
                    
                except (ClientForbiddenError, ClientUnauthorizedError) as e:
                    log.debug("Authentication error for %s: %s", username, e)
                    if on_log:
                        on_log(f"auth: authentication error: {e}")
                    
                    # These errors usually mean we need to re-login - break to login block
                    log.debug("Auth error detected, proceeding to login")
                    if on_log:
                        on_log(f"auth: proceeding to login due to auth error")
                    break
                        
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
                        break  # даём коду дойти до логина
                        
                except Exception as e:
                    error_str = str(e).lower()
                    log.debug("Auth check failed for %s: %s", username, e)
                    
                    # Handle 429 errors specifically - treat as signal to proceed to login
                    if "429" in error_str or "too many" in error_str or "rate limit" in error_str:
                        log.warning(f"Rate limit (429) during precheck for {username}, proceeding to login")
                        if on_log:
                            on_log(f"auth: rate limit during precheck, proceeding to login")
                        # Don't retry precheck, proceed directly to login attempt
                        break
                    
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
                        break  # переходим к логину
                
                # Login block moved outside the loop - will be executed after breaking from the loop
                    
            except Exception as e:
                log.error(f"Unexpected error during auth for {username}: {e}")
                if on_log:
                    on_log(f"auth: unexpected error: {e}")
                
                if attempt < max_retries - 1:
                    delay = self._get_human_delay('error_recovery')
                    time.sleep(delay)
                    continue
                
                return False
        
        # If we reach here, it means we broke out of the loop due to LoginRequired or auth errors
        # Now attempt login
        try:
            delay = self._get_human_delay('auth')
            time.sleep(delay)
            
            log.debug("Login attempt for %s after session check failure", username)
            if on_log:
                on_log("auth: login")
            
            cl.login(username, password)
            # Validate session info immediately before logging completion
            info = None
            try:
                # Verify via private v1 users/{uid}/info/ only (avoid accounts/current_user)
                info = self._get_user_info_v1(cl)
                uname = self._get_username(info)
                if uname:
                    log.debug("Login account info for %s: %s", username, uname)
                    if on_log:
                        on_log(f"auth: account_info: {uname}")
                else:
                    pass
            except Exception:
                info = None
            log.debug("Login completed for %s", username)
            if on_log:
                on_log("auth: login completed")
            
            # CRITICAL: Verify login was actually successful with strict check and timeout
            try:
                delay = self._get_human_delay('session_check')
                time.sleep(delay)
                
                # Use threading.Timer for timeout in worker threads
                import threading
                import queue
                
                result_queue = queue.Queue()
                timeout_occurred = threading.Event()
                
                def call_account_info():
                    try:
                        # Verify login success via private v1 only
                        account_info = self._get_user_info_v1(cl)
                        if not timeout_occurred.is_set():
                            result_queue.put(('success', account_info))
                    except Exception as e:
                        if not timeout_occurred.is_set():
                            result_queue.put(('error', e))
                
                # Start the account_info call in a separate thread
                thread = threading.Thread(target=call_account_info)
                thread.daemon = True
                thread.start()
                
                # Wait for result with timeout
                try:
                    result_type, result_data = result_queue.get(timeout=15)  # 15 second timeout
                    
                    if result_type == 'success':
                        account_info = result_data
                        uname2 = self._get_username(account_info)
                        if uname2:
                            log.debug("Login verified for %s", uname2)
                            if on_log:
                                on_log("auth: login verified")
                            # Record successful auth
                            self._record_auth_attempt(username, success=True)
                            return True
                        else:
                            # Log detailed info about the failed verification
                            log.warning(f"Login verification failed for {username}: v1 user info returned invalid response")
                            log.warning(f"Account info received: {account_info}")
                            if on_log:
                                on_log("auth: login verification failed: v1 user info returned invalid response")
                            
                            # Try to save session even if verification failed
                            try:
                                from instgrapi_func.services.session_store import DjangoDeviceSessionStore
                                session_store = DjangoDeviceSessionStore()
                                settings = cl.get_settings()
                                session_store.save(username, settings)
                                log.info(f"Session saved for {username} despite verification failure")
                            except Exception as save_err:
                                log.warning(f"Failed to save session for {username}: {save_err}")
                            
                            # Continue anyway - login might have succeeded even if verification failed
                            log.warning(f"Continuing with login for {username} despite verification failure")
                            if on_log:
                                on_log("auth: continuing despite verification failure")
                            self._record_auth_attempt(username, success=True)
                            return True
                    else:
                        # Re-raise the exception from account_info
                        raise result_data
                        
                except queue.Empty:
                    # Timeout occurred
                    timeout_occurred.set()
                    log.warning("Login verification timed out after 15s for %s", username)
                    if on_log:
                        on_log("auth: login verification timeout")
                    raise Exception("Login verification timeout")
                    
            except Exception as verify_e:
                log.warning("Login verification failed for %s: %s", username, verify_e)
                if on_log:
                    on_log(f"auth: login verification failed: {verify_e}")
                # Don't return True if verification failed
                raise Exception(f"Login verification failed: {verify_e}")
            
        except TwoFactorRequired:
            return self._handle_two_factor_auth(cl, username, password, on_log)
            
        except ChallengeRequired:
            return self._handle_challenge_auth(cl, username, password, on_log)
            
        except RateLimitError as e:
            log.debug("RateLimitError during login for %s: %s", username, e)
            if on_log:
                on_log(f"auth: rate limited during login: {e}")
            
            # For 429 errors, wait longer and try login again
            delay = random.uniform(60, 120)  # 60-120 seconds as requested
            log.warning(f"Rate limited during login for {username}, waiting {delay:.1f}s before retry")
            if on_log:
                on_log(f"auth: rate limited, waiting {delay:.1f}s before retry")
            time.sleep(delay)
            
            # Try login one more time after rate limit delay
            try:
                cl.login(username, password)
                log.debug("Login completed after rate limit delay for %s", username)
                if on_log:
                    on_log("auth: login completed after rate limit delay")
                
                # Verify login success
                delay = self._get_human_delay('session_check')
                time.sleep(delay)
                account_info = self._get_user_info_v1(cl)
                uname_rl = self._get_username(account_info)
                if uname_rl:
                    log.debug("Login verified after rate limit delay for %s", uname_rl)
                    if on_log:
                        on_log("auth: login verified after rate limit delay")
                    self._record_auth_attempt(username, success=True)
                    return True
                else:
                    raise Exception("v1 info failed after rate limit delay login")
            except Exception as retry_e:
                log.warning("Login retry after rate limit failed for %s: %s", username, retry_e)
                if on_log:
                    on_log(f"auth: login retry failed: {retry_e}")
                return False
                
        except Exception as e:
            error_str = str(e).lower()
            log.debug("Login failed for %s: %s", username, e)
            
            if on_log:
                on_log(f"auth: login failed: {e}")
            
            # Handle 429 errors during login
            if "429" in error_str or "too many" in error_str or "rate limit" in error_str:
                log.warning(f"Rate limit (429) during login for {username}")
                if on_log:
                    on_log(f"auth: rate limit during login")
                return False
            
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
            log.debug("2FA login completed for %s", username)
            if on_log:
                on_log("auth: 2fa completed")
            
            # Verify 2FA login success with timeout
            try:
                delay = self._get_human_delay('session_check')
                time.sleep(delay)
                
                # Use threading.Timer for timeout in worker threads
                import threading
                import queue
                
                result_queue = queue.Queue()
                timeout_occurred = threading.Event()
                
                def call_account_info():
                    try:
                        account_info = cl.account_info()  # type: ignore[attr-defined]
                        if not timeout_occurred.is_set():
                            result_queue.put(('success', account_info))
                    except Exception as e:
                        if not timeout_occurred.is_set():
                            result_queue.put(('error', e))
                
                # Start the account_info call in a separate thread
                thread = threading.Thread(target=call_account_info)
                thread.daemon = True
                thread.start()
                
                # Wait for result with timeout
                try:
                    result_type, result_data = result_queue.get(timeout=15)  # 15 second timeout
                    
                    if result_type == 'success':
                        account_info = result_data
                        if account_info and hasattr(account_info, 'username'):
                            log.debug("2FA login verified for %s", account_info.username)
                            if on_log:
                                on_log("auth: 2fa verified")
                            
                            self._record_auth_attempt(username, success=True)
                            return True
                        else:
                            raise Exception("account_info() failed after 2FA login")
                    else:
                        # Re-raise the exception from account_info
                        raise result_data
                        
                except queue.Empty:
                    # Timeout occurred
                    timeout_occurred.set()
                    log.warning("2FA verification timed out after 15s for %s", username)
                    if on_log:
                        on_log("auth: 2fa verification timeout")
                    raise Exception("2FA verification timeout")
                    
            except Exception as verify_e:
                log.warning("2FA login verification failed for %s: %s", username, verify_e)
                if on_log:
                    on_log(f"auth: 2fa verification failed: {verify_e}")
                raise Exception(f"2FA login verification failed: {verify_e}")
            
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
            # Ensure we will NOT change password inside resolver
            try:
                cl.change_password_handler = lambda _username: None  # type: ignore[attr-defined]
            except Exception:
                pass

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
                        # Use new password if it was generated by change_password_handler
                        try:
                            new_pwd = getattr(cl, '_new_password', None)
                            if new_pwd:
                                password = new_pwd  # type: ignore[assignment]
                        except Exception:
                            pass
                        cl.login(username, password, relogin=True)
                        if on_log:
                            on_log("auth: login completed (post-challenge)")
                        
                        # Verify post-challenge login success with timeout
                        try:
                            delay = self._get_human_delay('session_check')
                            time.sleep(delay)
                            
                            # Use threading.Timer for timeout in worker threads
                            import threading
                            import queue
                            
                            result_queue = queue.Queue()
                            timeout_occurred = threading.Event()
                            
                            def call_account_info():
                                try:
                                    account_info = cl.account_info()  # type: ignore[attr-defined]
                                    if not timeout_occurred.is_set():
                                        result_queue.put(('success', account_info))
                                except Exception as e:
                                    if not timeout_occurred.is_set():
                                        result_queue.put(('error', e))
                            
                            # Start the account_info call in a separate thread
                            thread = threading.Thread(target=call_account_info)
                            thread.daemon = True
                            thread.start()
                            
                            # Wait for result with timeout
                            try:
                                result_type, result_data = result_queue.get(timeout=15)  # 15 second timeout
                                
                                if result_type == 'success':
                                    account_info = result_data
                                    if account_info and hasattr(account_info, 'username'):
                                        log.debug("Post-challenge login verified for %s", account_info.username)
                                        if on_log:
                                            on_log("auth: post-challenge login verified")
                                        
                                        self._record_auth_attempt(username, success=True)
                                        return True
                                    else:
                                        raise Exception("account_info() failed after post-challenge login")
                                else:
                                    # Re-raise the exception from account_info
                                    raise result_data
                                    
                            except queue.Empty:
                                # Timeout occurred
                                timeout_occurred.set()
                                log.warning("Post-challenge verification timed out after 15s for %s", username)
                                if on_log:
                                    on_log("auth: post-challenge verification timeout")
                                return False
                                
                        except Exception as verify_e:
                            log.warning("Post-challenge login verification failed for %s: %s", username, verify_e)
                            if on_log:
                                on_log(f"auth: post-challenge verification failed: {verify_e}")
                            return False
                        
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
                        # Use new password if it was generated by change_password_handler
                        try:
                            new_pwd = getattr(cl, '_new_password', None)
                            if new_pwd:
                                password = new_pwd  # type: ignore[assignment]
                        except Exception:
                            pass
                        cl.login(username, password, relogin=True)
                        if on_log:
                            on_log("auth: login completed (post-challenge-simple)")
                        
                        # Verify post-challenge-simple login success with timeout
                        try:
                            delay = self._get_human_delay('session_check')
                            time.sleep(delay)
                            
                            # Use threading.Timer for timeout in worker threads
                            import threading
                            import queue
                            
                            result_queue = queue.Queue()
                            timeout_occurred = threading.Event()
                            
                            def call_account_info():
                                try:
                                    account_info = cl.account_info()  # type: ignore[attr-defined]
                                    if not timeout_occurred.is_set():
                                        result_queue.put(('success', account_info))
                                except Exception as e:
                                    if not timeout_occurred.is_set():
                                        result_queue.put(('error', e))
                            
                            # Start the account_info call in a separate thread
                            thread = threading.Thread(target=call_account_info)
                            thread.daemon = True
                            thread.start()
                            
                            # Wait for result with timeout
                            try:
                                result_type, result_data = result_queue.get(timeout=15)  # 15 second timeout
                                
                                if result_type == 'success':
                                    account_info = result_data
                                    if account_info and hasattr(account_info, 'username'):
                                        log.debug("Post-challenge-simple login verified for %s", account_info.username)
                                        if on_log:
                                            on_log("auth: post-challenge-simple login verified")
                                        
                                        self._record_auth_attempt(username, success=True)
                                        return True
                                    else:
                                        raise Exception("account_info() failed after post-challenge-simple login")
                                else:
                                    # Re-raise the exception from account_info
                                    raise result_data
                                    
                            except queue.Empty:
                                # Timeout occurred
                                timeout_occurred.set()
                                log.warning("Post-challenge-simple verification timed out after 15s for %s", username)
                                if on_log:
                                    on_log("auth: post-challenge-simple verification timeout")
                                return False
                                
                        except Exception as verify_e:
                            log.warning("Post-challenge-simple login verification failed for %s: %s", username, verify_e)
                            if on_log:
                                on_log(f"auth: post-challenge-simple verification failed: {verify_e}")
                            return False
                        
                    except Exception as relog2_err:
                        log.debug("Post-challenge-simple login failed for %s: %s", username, relog2_err)
                        if on_log:
                            on_log(f"auth: post-challenge-simple login failed: {relog2_err}")
                        return False

            if on_log:
                on_log("auth: challenge not resolved")
            return False
            
        except Exception as e:
            log.debug("Challenge resolve failed for %s: %s", username, e)
            if on_log:
                on_log(f"auth: challenge failed: {e}")
            return False 