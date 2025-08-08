import random
import time
from typing import Dict, Optional, Tuple, Callable

from instagrapi import Client

from .services.avatar_service import AvatarService
from .services.auth_service import IGAuthService
from .services.code_providers import (
    TOTPProvider,
    NullTwoFactorProvider,
    AutoIMAPEmailProvider,
    External2FAApiProvider,
    CompositeProvider,
)
import os


def _default_delay(min_s: float = 0.8, max_s: float = 2.2) -> None:
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


def build_proxy_url(proxy: Dict) -> Optional[str]:
    if not proxy:
        return None
    proto = (proxy.get('type') or 'http').lower()
    host = proxy.get('host')
    port = proxy.get('port')
    user = proxy.get('user')
    pwd = proxy.get('pass')
    if not (host and port):
        return None
    if user and pwd:
        return f"{proto}://{user}:{pwd}@{host}:{port}"
    return f"{proto}://{host}:{port}"


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


def ensure_logged_in(client: Client, username: str, password: str) -> bool:
    """Try lightweight auth check, fallback to login if needed."""
    try:
        _default_delay(0.2, 0.6)
        # instagrapi: simple call to check current user
        client.user_id_from_username(username)
        return True
    except Exception:
        pass

    try:
        _default_delay(1.0, 2.5)
        client.login(username, password)
        return True
    except Exception:
        return False


def change_avatar_for_account(
    account: Dict,
    image_path: str,
    device_settings: Dict,
    session_settings: Optional[Dict] = None,
    proxy: Optional[Dict] = None,
    on_log: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, Optional[Dict]]:
    """
    Change avatar using instagrapi for a single account.

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
        providers.append(AutoIMAPEmailProvider(email_login, email_password))

    provider = CompositeProvider(providers) if providers else NullTwoFactorProvider()
    auth = IGAuthService(provider=provider)
    service = AvatarService(auth_service=auth)

    # Human-like small delay before action
    _default_delay(0.6, 1.4)

    return service.change_avatar(
        account=account,
        image_path=image_path,
        device_settings=device_settings,
        session_settings=session_settings,
        proxy=proxy,
        on_log=on_log,
    ) 