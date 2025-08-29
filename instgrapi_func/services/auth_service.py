from __future__ import annotations
from typing import Optional, Callable
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ChallengeRequired  # type: ignore
from .code_providers import TwoFactorProvider, NullTwoFactorProvider
import logging

log = logging.getLogger('insta.auth')


class IGAuthService:
    def __init__(self, provider: Optional[TwoFactorProvider] = None) -> None:
        self.provider = provider or NullTwoFactorProvider()

    def ensure_logged_in(self, cl: Client, username: str, password: str, on_log: Optional[Callable[[str], None]] = None) -> bool:
        log.debug("Ensure logged in for %s", username)
        if on_log:
            on_log(f"auth: ensure session for {username}")
        # Set challenge handler early so library can prompt our provider instead of input()
        try:
            def _prelogin_handler(_username, _choice):
                return self.provider.get_challenge_code(username, method="email") or ""
            cl.challenge_code_handler = _prelogin_handler
        except Exception:
            pass
        try:
            cl.user_id_from_username(username)
            log.debug("Already authenticated as %s", username)
            if on_log:
                on_log("auth: already authenticated")
            return True
        except Exception as e:
            log.debug("Auth check failed for %s: %s", username, e)
            if on_log:
                on_log(f"auth: precheck failed: {e}")

        try:
            log.debug("Login attempt for %s", username)
            if on_log:
                on_log("auth: login")
            cl.login(username, password)
            log.debug("Login success for %s", username)
            if on_log:
                on_log("auth: login ok")
            return True
        except TwoFactorRequired:
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
                cl.login(username, password, verification_code=totp)
                log.debug("2FA login success for %s", username)
                if on_log:
                    on_log("auth: 2fa ok")
                return True
            except Exception as e:
                log.debug("2FA login failed for %s: %s", username, e)
                if on_log:
                    on_log(f"auth: 2fa failed: {e}")
                return False
        except ChallengeRequired:
            log.debug("ChallengeRequired for %s", username)
            if on_log:
                on_log("auth: challenge required (email)")
            try:
                # Provide code handler; let library resolver drive the flow
                def _handler(_username, _choice):
                    return self.provider.get_challenge_code(username, method="email") or ""
                try:
                    cl.challenge_code_handler = _handler
                except Exception:
                    pass

                # Resolve strictly via library's native resolver using the current last_json
                resolver = getattr(cl, 'challenge_resolve', None)
                if callable(resolver):
                    ok = resolver(getattr(cl, 'last_json', {}) or {})
                    if ok:
                        if on_log:
                            on_log("auth: challenge ok (native)")
                        try:
                            cl.login(username, password, relogin=True)
                            if on_log:
                                on_log("auth: login ok (post-challenge)")
                            return True
                        except Exception as relog_err:
                            log.debug("Post-challenge login failed for %s: %s", username, relog_err)
                            if on_log:
                                on_log(f"auth: post-challenge login failed: {relog_err}")
                            return False

                # If native resolver not available or failed early: try simple resolver using api_path
                cur = getattr(cl, 'last_json', {}) or {}
                api_path = (cur.get('challenge') or {}).get('api_path') or cur.get('challenge_url') or ''
                if isinstance(api_path, str) and api_path.startswith('/challenge/'):
                    simple = getattr(cl, 'challenge_resolve_simple', None)
                    if callable(simple):
                        simple(api_path)
                        if on_log:
                            on_log("auth: challenge ok (simple)")
                        try:
                            cl.login(username, password, relogin=True)
                            if on_log:
                                on_log("auth: login ok (post-challenge)")
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
        except Exception as e:
            log.debug("Login failed for %s: %s", username, e)
            if on_log:
                on_log(f"auth: login failed: {e}")
            return False 