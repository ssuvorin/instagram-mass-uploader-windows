from __future__ import annotations
from typing import Optional, Protocol, List
import time
import random
import re
import asyncio

try:
    import pyotp  # type: ignore
except Exception:  # pyotp is in requirements
    pyotp = None

try:
    import requests  # type: ignore
except Exception:
    requests = None


class TwoFactorProvider(Protocol):
    def get_totp(self, username: str) -> Optional[str]:
        ...

    def get_challenge_code(self, username: str, method: str) -> Optional[str]:
        ...


class NullTwoFactorProvider:
    def get_totp(self, username: str) -> Optional[str]:
        return None

    def get_challenge_code(self, username: str, method: str) -> Optional[str]:
        return None


class CompositeProvider(NullTwoFactorProvider):
    def __init__(self, providers: List[TwoFactorProvider]):
        self.providers = providers

    def get_totp(self, username: str) -> Optional[str]:
        for p in self.providers:
            code = p.get_totp(username)
            if code:
                return code
        return None

    def get_challenge_code(self, username: str, method: str) -> Optional[str]:
        for p in self.providers:
            code = p.get_challenge_code(username, method)
            if code:
                return code
        return None


class TOTPProvider:
    def __init__(self, secret: Optional[str]):
        self.secret = (secret or '').replace(' ', '') or None

    def get_totp(self, username: str) -> Optional[str]:
        if not self.secret or not pyotp:
            return None
        try:
            totp = pyotp.TOTP(self.secret)
            return totp.now()
        except Exception:
            return None

    def get_challenge_code(self, username: str, method: str) -> Optional[str]:
        # No email/SMS fetching here. Extend with Email/SMS providers if needed.
        return None


class External2FAApiProvider(NullTwoFactorProvider):
    """Fetch TOTP via external HTTP API, similar to OLD TwoFactorAuthHandler."""
    def __init__(self, base_url: str, token: Optional[str]):
        self.base_url = base_url.rstrip('/')
        self.token = (token or '').strip() or None

    def get_totp(self, username: str) -> Optional[str]:
        if not self.token or not requests:
            return None
        try:
            url = f"{self.base_url}?token={self.token}"
            resp = requests.get(url, timeout=8)
            data = resp.json() if resp.ok else {}
            code = str(data.get('otp') or data.get('code') or '').strip()
            return code if code.isdigit() and len(code) in (6, 8) else None
        except Exception:
            return None


class AutoIMAPEmailProvider(NullTwoFactorProvider):
    """
    Reuse existing project email verification logic (bulk async module) to fetch
    latest Instagram verification code from mailbox.
    """
    def __init__(self, email: Optional[str], password: Optional[str], on_log=None):
        self.email = (email or '').strip() or None
        self.password = (password or '').strip() or None
        self.on_log = on_log

    def get_challenge_code(self, username: str, method: str) -> Optional[str]:
        if not self.email or not self.password:
            if self.on_log:
                self.on_log("Email credentials not provided for verification")
            return None

        try:
            from uploader.email_verification_async import get_email_verification_code_async  # type: ignore
        except Exception as e:
            if self.on_log:
                self.on_log(f"Email verification module not available: {e}")
            return None

        try:
            if self.on_log:
                self.on_log(f"Attempting to get email verification code from {self.email}")

            # Create a custom version of get_email_verification_code_async that uses our on_log
            async def get_code_with_logging():
                return await get_email_verification_code_async(self.email, self.password, max_retries=3, on_log=self.on_log)

            code = asyncio.run(get_code_with_logging())

            if code:
                if self.on_log:
                    self.on_log(f"Successfully retrieved verification code: {code}")
                return code
            else:
                if self.on_log:
                    self.on_log("No verification code found in email")
                return None

        except RuntimeError:
            # If there's already a running loop, create a new one in this thread
            try:
                if self.on_log:
                    self.on_log("Creating new event loop for email verification")

                loop = asyncio.new_event_loop()
                try:
                    async def get_code_with_logging():
                        return await get_email_verification_code_async(self.email, self.password, max_retries=3, on_log=self.on_log)

                    code = loop.run_until_complete(get_code_with_logging())

                    if code:
                        if self.on_log:
                            self.on_log(f"Successfully retrieved verification code: {code}")
                        return code
                    else:
                        if self.on_log:
                            self.on_log("No verification code found in email")
                        return None
                finally:
                    loop.close()
            except Exception as e:
                if self.on_log:
                    self.on_log(f"Error getting verification code: {e}")
                return None
        except Exception as e:
            if self.on_log:
                self.on_log(f"Error getting verification code: {e}")
            return None 