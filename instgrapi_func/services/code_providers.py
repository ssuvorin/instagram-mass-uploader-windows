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
        if self.on_log:
            self.on_log(f"📧 [EMAIL_CHALLENGE] Starting challenge code retrieval for {username}")
            self.on_log(f"📧 [EMAIL_CHALLENGE] Method: {method}")
            self.on_log(f"📧 [EMAIL_CHALLENGE] Email: {self.email}")
            
        if not self.email or not self.password:
            if self.on_log:
                self.on_log("📧 [EMAIL_CHALLENGE] ❌ Email credentials not provided for verification")
            return None

        if self.on_log:
            self.on_log(f"📧 [EMAIL_CHALLENGE] ✅ Email credentials available: {self.email} (password: {'yes' if self.password else 'no'})")

        # First try using the synchronous email client which works better in instagrapi context
        if self.on_log:
            self.on_log(f"📧 [EMAIL_CHALLENGE] 🔍 Attempting sync email client approach")
        
        try:
            # Import the synchronous email client
            try:
                from bot.src.instagram_uploader.email_client import Email
            except Exception as e:
                if self.on_log:
                    self.on_log(f"📧 [EMAIL_CHALLENGE] ❌ Email client not available: {e}")
                return None
            
            # Create email client and test connection first
            email_client = Email(self.email, self.password)
            if self.on_log:
                self.on_log(f"📧 [EMAIL_CHALLENGE] 📧 Email client created for {self.email}")
            
            # Test connection
            if not email_client.test_connection():
                if self.on_log:
                    self.on_log(f"📧 [EMAIL_CHALLENGE] ❌ Email connection test failed")
                return None
            
            if self.on_log:
                self.on_log(f"📧 [EMAIL_CHALLENGE] ✅ Email connection test successful")
            
            # Get verification code with retry logic
            code = email_client.get_verification_code(max_retries=3, retry_delay=10)
            
            if code:
                if self.on_log:
                    self.on_log(f"📧 [EMAIL_CHALLENGE] ✅ Successfully retrieved verification code: {code}")
                return code
            else:
                if self.on_log:
                    self.on_log("📧 [EMAIL_CHALLENGE] ❌ No verification code found in email")
                return None
                
        except Exception as e:
            if self.on_log:
                self.on_log(f"📧 [EMAIL_CHALLENGE] ❌ Sync email client failed: {e}")

        # Fallback to async approach if sync fails
        if self.on_log:
            self.on_log(f"📧 [EMAIL_CHALLENGE] 🔄 Falling back to async email approach")
        
        try:
            from uploader.email_verification_async import get_email_verification_code_async  # type: ignore
        except Exception as e:
            if self.on_log:
                self.on_log(f"📧 [EMAIL_CHALLENGE] ❌ Email verification module not available: {e}")
            return None

        try:
            # Try to run async code in current thread
            import asyncio
            
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    # We're in an async context, need to run in thread
                    if self.on_log:
                        self.on_log(f"📧 [EMAIL_CHALLENGE] 🔄 Running in thread due to existing event loop")
                    
                    import concurrent.futures
                    import threading
                    
                    def run_async_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            async def get_code_with_logging():
                                return await get_email_verification_code_async(self.email, self.password, max_retries=3, on_log=self.on_log)
                            
                            return new_loop.run_until_complete(get_code_with_logging())
                        finally:
                            new_loop.close()
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_async_in_thread)
                        code = future.result(timeout=30)  # 30 second timeout
                    
                    if code:
                        if self.on_log:
                            self.on_log(f"📧 [EMAIL_CHALLENGE] ✅ Successfully retrieved verification code: {code}")
                        return code
                    else:
                        if self.on_log:
                            self.on_log("📧 [EMAIL_CHALLENGE] ❌ No verification code found in email")
                        return None
                        
            except RuntimeError:
                # No running loop, we can use asyncio.run
                if self.on_log:
                    self.on_log(f"📧 [EMAIL_CHALLENGE] 🔄 Using asyncio.run (no existing loop)")
                
                async def get_code_with_logging():
                    return await get_email_verification_code_async(self.email, self.password, max_retries=3, on_log=self.on_log)

                code = asyncio.run(get_code_with_logging())

                if code:
                    if self.on_log:
                        self.on_log(f"📧 [EMAIL_CHALLENGE] ✅ Successfully retrieved verification code: {code}")
                    return code
                else:
                    if self.on_log:
                        self.on_log("📧 [EMAIL_CHALLENGE] ❌ No verification code found in email")
                    return None

        except Exception as e:
            if self.on_log:
                self.on_log(f"📧 [EMAIL_CHALLENGE] ❌ Error getting verification code: {e}")
            return None 