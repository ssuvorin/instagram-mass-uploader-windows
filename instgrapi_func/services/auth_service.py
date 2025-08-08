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
                code = self.provider.get_challenge_code(username, method="email") or ""
                log.debug("Challenge code obtained: %s", "yes" if code else "no")
                if not code:
                    if on_log:
                        on_log("auth: no email code available")
                    return False
                cl.challenge_resolve(code)
                log.debug("Challenge resolved for %s", username)
                if on_log:
                    on_log("auth: challenge ok")
                return True
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