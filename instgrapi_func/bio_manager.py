import random
import time
from typing import Dict, Optional, Tuple, Callable
import os

from .services.bio_service import BioService
from .services.auth_service import IGAuthService
from .services.code_providers import (
    TOTPProvider,
    NullTwoFactorProvider,
    AutoIMAPEmailProvider,
    External2FAApiProvider,
    CompositeProvider,
)


def _default_delay(min_s: float = 0.8, max_s: float = 2.2) -> None:
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


def build_device_config(device_settings: Dict) -> Dict:
    return {
        "cpu": device_settings.get("cpu", "exynos9820"),
        "dpi": device_settings.get("dpi", "640dpi"),
        "model": device_settings.get("model", "SM-G973F"),
        "device": device_settings.get("device", "beyond1"),
        "resolution": device_settings.get("resolution", "1440x3040"),
        "app_version": device_settings.get("app_version", "269.0.0.18.75"),
        "manufacturer": device_settings.get("manufacturer", "samsung"),
        "version_code": device_settings.get("version_code", "314665256"),
        "android_release": device_settings.get("android_release", "10"),
        "android_version": device_settings.get("android_version", 29),
    }


def change_bio_link_for_account(
    account: Dict,
    link_url: str,
    device_settings: Dict,
    session_settings: Optional[Dict] = None,
    proxy: Optional[Dict] = None,
    on_log: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, Optional[Dict]]:
    """
    Change external_url (bio link) for a single account using instagrapi client under the hood.

    - Supports optional TOTP via account['tfa_secret'] if provided
    - Supports email challenge via account['email'] + account['email_password']
    - Optional external 2FA API via env TWOFA_API_URL and account['twofa_token']
    - Returns (success, updated_session_settings)
    """
    providers = []
    # External 2FA API (optional, token per account)
    ext_api_url = os.environ.get('TWOFA_API_URL')
    twofa_token = (account.get('twofa_token') or '').strip() or None
    if ext_api_url and twofa_token:
        providers.append(External2FAApiProvider(ext_api_url, twofa_token))
    # TOTP from secret
    tfa_secret = (account.get('tfa_secret') or '').replace(' ', '') or None
    if tfa_secret:
        providers.append(TOTPProvider(tfa_secret))
    # Email challenge via IMAP
    email_login = (account.get('email') or '').strip() or None
    email_password = (account.get('email_password') or '').strip() or None
    if email_login and email_password:
        providers.append(AutoIMAPEmailProvider(email_login, email_password, on_log=on_log))

    provider = CompositeProvider(providers) if providers else NullTwoFactorProvider()
    auth = IGAuthService(provider=provider)
    service = BioService(auth_service=auth)

    # Human-like small delay before action
    _default_delay(0.6, 1.4)

    return service.change_external_url(
        account=account,
        link_url=link_url,
        device_settings=device_settings,
        session_settings=session_settings,
        proxy=proxy,
        on_log=on_log,
    ) 