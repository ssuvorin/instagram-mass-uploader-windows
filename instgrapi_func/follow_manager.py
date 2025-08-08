import random
import time
from typing import Dict, Optional, Tuple, Callable
import os

from instgrapi_func.services.follow_service import FollowService
from instgrapi_func.services.auth_service import IGAuthService
from instgrapi_func.services.code_providers import (
    TOTPProvider,
    NullTwoFactorProvider,
    AutoIMAPEmailProvider,
    External2FAApiProvider,
    CompositeProvider,
)


def _default_delay(min_s: float = 0.8, max_s: float = 2.2) -> None:
    time.sleep(random.uniform(min_s, max_s))


def follow_single_target(
    account: Dict,
    target_username: str,
    target_user_id: Optional[int],
    device_settings: Dict,
    session_settings: Optional[Dict] = None,
    proxy: Optional[Dict] = None,
    on_log: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, Optional[int], Optional[Dict]]:
    providers = []
    ext_api_url = os.environ.get('TWOFA_API_URL')
    twofa_token = (account.get('twofa_token') or '').strip() or None
    if ext_api_url and twofa_token:
        providers.append(External2FAApiProvider(ext_api_url, twofa_token))
    tfa_secret = (account.get('tfa_secret') or '').replace(' ', '') or None
    if tfa_secret:
        providers.append(TOTPProvider(tfa_secret))
    email_login = (account.get('email') or '').strip() or None
    email_password = (account.get('email_password') or '').strip() or None
    if email_login and email_password:
        providers.append(AutoIMAPEmailProvider(email_login, email_password))

    provider = CompositeProvider(providers) if providers else NullTwoFactorProvider()
    auth = IGAuthService(provider=provider)
    service = FollowService(auth_service=auth)

    _default_delay(0.6, 1.4)

    return service.follow_target(
        account=account,
        target_username=target_username,
        target_user_id=target_user_id,
        device_settings=device_settings,
        session_settings=session_settings,
        proxy=proxy,
        on_log=on_log,
    )
