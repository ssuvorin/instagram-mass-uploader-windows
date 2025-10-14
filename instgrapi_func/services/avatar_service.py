from __future__ import annotations
from typing import Dict, Optional, Tuple, Callable
from pathlib import Path
import os
from .client_factory import IGClientFactory
from .proxy import build_proxy_url
from .auth_service import IGAuthService
from .session_store import DjangoDeviceSessionStore
from .device_service import ensure_persistent_device
import logging
from instagrapi.exceptions import ChallengeRequired, PleaseWaitFewMinutes, LoginRequired, PhotoNotUpload  # type: ignore

log = logging.getLogger('insta.avatar')


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
        # Optional identifiers
        "uuid": device_settings.get("uuid"),
        "android_device_id": device_settings.get("android_device_id"),
        "phone_id": device_settings.get("phone_id"),
        "client_session_id": device_settings.get("client_session_id"),
    }


class AvatarService:
    def __init__(self, auth_service: IGAuthService) -> None:
        self.auth = auth_service

    def change_avatar(
        self,
        account: Dict,
        image_path: str,
        device_settings: Dict,
        session_settings: Optional[Dict] = None,
        proxy: Optional[Dict] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, Optional[Dict]]:
        username = account.get("username", "")
        password = account.get("password", "")
        if not username or not password:
            log.debug("Missing credentials for avatar change")
            if on_log:
                on_log("avatar: missing credentials")
            return False, None

        # Validate image file
        if not image_path or not os.path.exists(image_path):
            log.debug("Image file not found: %s", image_path)
            if on_log:
                on_log(f"image file not found: {image_path}")
            return False, None
        
        # Convert to Path object as expected by instagrapi
        image_path_obj = Path(image_path)
        
        # Validate image format
        valid_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        if image_path_obj.suffix.lower() not in valid_extensions:
            log.debug("Invalid image format: %s (supported: %s)", image_path_obj.suffix, valid_extensions)
            if on_log:
                on_log(f"invalid image format: {image_path_obj.suffix} (supported: {', '.join(valid_extensions)})")
            return False, None
        
        if on_log:
            on_log(f"validated image: {image_path_obj.name} ({image_path_obj.stat().st_size} bytes)")

        # Ensure persistent device based on DB/session
        store = DjangoDeviceSessionStore()
        persisted_settings = session_settings or store.load(username) or None
        resolved_device, ua_hint = ensure_persistent_device(username, persisted_settings)
        # Prefer passed-in user agent if present, else resolved
        ua_final = (device_settings or {}).get("user_agent") or ua_hint
        # Merge passed-in device overrides on top of resolved
        merged_device = dict(resolved_device or {})
        merged_device.update(device_settings or {})
        device_cfg = build_device_config(merged_device)
        proxy_url = build_proxy_url(proxy or {})
        user_agent = ua_final
        country = (merged_device or {}).get("country")
        locale = (merged_device or {}).get("locale")

        log.debug("Build client for %s | proxy=%s", username, proxy_url)
        if on_log:
            on_log(f"build client (proxy={'yes' if proxy_url else 'no'})")
        cl = IGClientFactory.create_client(
            device_config=device_cfg,
            proxy_url=proxy_url,
            session_settings=persisted_settings,
            user_agent=user_agent,
            country=country,
            locale=locale,
            proxy_dict=proxy or {},
        )

        if not self.auth.ensure_logged_in(cl, username, password, on_log=on_log):
            log.debug("Auth failed for %s", username)
            if on_log:
                on_log("auth failed")
            return False, None

        try:
            log.debug("Change profile picture for %s: %s", username, image_path)
            if on_log:
                on_log("changing profile picture")
            result = cl.account_change_picture(image_path_obj)
            log.debug("Profile picture changed for %s, result: %s", username, result)
            if on_log:
                on_log(f"picture changed (user: {getattr(result, 'username', 'unknown')})")
        except ChallengeRequired as e:
            log.debug("ChallengeRequired on change picture for %s: %s", username, e)
            if on_log:
                on_log("challenge required (email)")
            try:
                if on_log:
                    on_log("avatar: requesting email challenge code")
                code = self.auth.provider.get_challenge_code(username, method="email") or ""
                if not code:
                    log.debug("No challenge code available for %s", username)
                    if on_log:
                        on_log("no email code available")
                    return False, None
                if on_log:
                    on_log(f"avatar: resolving challenge with code: {code[:2]}***")
                cl.challenge_resolve(code)
                log.debug("Challenge resolved during avatar change for %s, retrying", username)
                if on_log:
                    on_log("challenge ok, retry")
                result = cl.account_change_picture(image_path_obj)
                log.debug("Profile picture changed after challenge for %s, result: %s", username, result)
                if on_log:
                    on_log(f"picture changed after challenge (user: {getattr(result, 'username', 'unknown')})")
            except Exception as e2:
                log.debug("Challenge resolving/retry failed for %s: %s", username, e2)
                if on_log:
                    on_log(f"challenge failed: {e2}")
                return False, None
        except PleaseWaitFewMinutes as e:
            log.debug("PleaseWaitFewMinutes on change picture for %s: %s", username, e)
            if on_log:
                on_log(f"rate limited: {e}")
            return False, None
        except LoginRequired as e:
            log.debug("LoginRequired on change picture for %s: %s", username, e)
            if on_log:
                on_log(f"session expired, attempting to restore...")
            log.info(f"LoginRequired on change picture for {username}, attempting session restoration")
            
            # Use existing authentication logic from bulk upload
            if not self._restore_session_and_login(cl, username, password, on_log):
                log.error(f"Session restoration failed for {username}")
                return False, None
            
            # Retry avatar change after session restoration
            try:
                result = cl.account_change_picture(image_path_obj)
                log.debug("Profile picture changed after session restore for %s, result: %s", username, result)
                if on_log:
                    on_log(f"picture changed after session restore (user: {getattr(result, 'username', 'unknown')})")
                log.info(f"picture changed after session restore for {username} (user: {getattr(result, 'username', 'unknown')})")
            except Exception as retry_e:
                log.error(f"Avatar change retry failed for {username}: {retry_e}")
                if on_log:
                    on_log(f"avatar change retry failed: {retry_e}")
                return False, None
        except PhotoNotUpload as e:
            # Check if PhotoNotUpload contains login_required
            error_str = str(e)
            if "login_required" in error_str.lower():
                log.debug("PhotoNotUpload with login_required for %s: %s", username, e)
                if on_log:
                    on_log(f"session expired (PhotoNotUpload), attempting to restore...")
                log.info(f"PhotoNotUpload with login_required for {username}, attempting session restoration")
                
                # Use existing authentication logic from bulk upload
                if not self._restore_session_and_login(cl, username, password, on_log):
                    log.error(f"Session restoration failed for {username}")
                    return False, None
                
                # Retry avatar change after session restoration
                try:
                    result = cl.account_change_picture(image_path_obj)
                    log.debug("Profile picture changed after session restore for %s, result: %s", username, result)
                    if on_log:
                        on_log(f"picture changed after session restore (user: {getattr(result, 'username', 'unknown')})")
                    log.info(f"picture changed after session restore for {username} (user: {getattr(result, 'username', 'unknown')})")
                except Exception as retry_e:
                    log.error(f"Avatar change retry failed for {username}: {retry_e}")
                    if on_log:
                        on_log(f"avatar change retry failed: {retry_e}")
                    return False, None
            else:
                log.debug("PhotoNotUpload without login_required for %s: %s", username, e)
                if on_log:
                    on_log(f"photo upload failed: {e}")
                return False, None
        except Exception as e:
            # Check if this is a challenge disguised as another exception
            error_str = str(e)
            if "challenge_required" in error_str.lower() or "400" in error_str or "challenge" in error_str.lower():
                log.debug("Challenge detected in generic exception for %s: %s", username, e)
                if on_log:
                    on_log("challenge detected (email)")
                try:
                    if on_log:
                        on_log("avatar: requesting email challenge code")
                    code = self.auth.provider.get_challenge_code(username, method="email") or ""
                    if not code:
                        log.debug("No challenge code available for %s", username)
                        if on_log:
                            on_log("no email code available")
                        return False, None
                    if on_log:
                        on_log(f"avatar: resolving challenge with code: {code[:2]}***")
                    cl.challenge_resolve(code)
                    log.debug("Challenge resolved during avatar change for %s, retrying", username)
                    if on_log:
                        on_log("challenge ok, retry")
                    result = cl.account_change_picture(image_path_obj)
                    log.debug("Profile picture changed after challenge for %s, result: %s", username, result)
                    if on_log:
                        on_log(f"picture changed after challenge (user: {getattr(result, 'username', 'unknown')})")
                    # If we get here, the challenge was resolved successfully
                except Exception as e3:
                    log.debug("Challenge resolving/retry failed for %s: %s", username, e3)
                    if on_log:
                        on_log(f"challenge failed: {e3}")
                    return False, None
            else:
                # Check if this is a 400 error that might be a challenge
                if "400" in error_str:
                    log.debug("400 error detected for %s: %s", username, e)
                    if on_log:
                        on_log("400 error detected, checking for challenge")
                    try:
                        # Check if this is actually a challenge by looking at the response
                        lr = getattr(getattr(cl, 'private', None), 'last_response', None)
                        if lr is not None and ("challenge" in lr.text.lower() or "checkpoint" in lr.text.lower()):
                            log.debug("400 error contains challenge for %s", username)
                            if on_log:
                                on_log("400 error contains challenge, attempting resolution")
                            try:
                                if on_log:
                                    on_log("avatar: requesting email challenge code")
                                code = self.auth.provider.get_challenge_code(username, method="email") or ""
                                if not code:
                                    log.debug("No challenge code available for %s", username)
                                    if on_log:
                                        on_log("no email code available")
                                    return False, None
                                if on_log:
                                    on_log(f"avatar: resolving challenge with code: {code[:2]}***")
                                cl.challenge_resolve(code)
                                log.debug("Challenge resolved during avatar change for %s, retrying", username)
                                if on_log:
                                    on_log("challenge ok, retry")
                                result = cl.account_change_picture(image_path_obj)
                                log.debug("Profile picture changed after challenge for %s, result: %s", username, result)
                                if on_log:
                                    on_log(f"picture changed after challenge (user: {getattr(result, 'username', 'unknown')})")
                            except Exception as e4:
                                log.debug("Challenge resolution failed for %s: %s", username, e4)
                                if on_log:
                                    on_log(f"challenge failed: {e4}")
                                return False, None
                    except Exception:
                        pass
                
                log.debug("Change picture failed for %s: %s (type: %s)", username, e, type(e).__name__)
                if on_log:
                    on_log(f"change failed: {e} (type: {type(e).__name__})")
                return False, None

        try:
            settings = cl.get_settings()
            # Persist updated session and fill missing device/user_agent if needed
            try:
                store.save(username, settings)
                if on_log:
                    on_log("session saved")
                from uploader.models import InstagramAccount
                acc = InstagramAccount.objects.filter(username=username).first()
                if acc and getattr(acc, 'device', None):
                    dev = acc.device
                    updates = []
                    if not dev.user_agent and settings.get('user_agent'):
                        dev.user_agent = settings.get('user_agent')
                        updates.append('user_agent')
                    if not dev.device_settings:
                        dev.device_settings = merged_device
                        updates.append('device_settings')
                    if updates:
                        dev.save(update_fields=updates)
            except Exception:
                pass
            log.debug("Fetched updated settings for %s", username)
            if on_log:
                on_log("fetched updated settings")
            return True, settings
        except Exception as e:
            log.debug("Fetching settings failed for %s: %s", username, e)
            if on_log:
                on_log(f"fetch settings failed: {e}")
            return True, None

    def _restore_session_and_login(self, cl: Client, username: str, password: str, on_log: Optional[Callable[[str], None]] = None) -> bool:
        """Restore session and login using existing logic from bulk upload"""
        from instgrapi_func.services.session_store import SessionStore
        from instgrapi_func.services.auth_service import CompositeProvider, TOTPProvider, AutoIMAPEmailProvider
        
        # Get session settings from database
        session_store = SessionStore()
        persisted_settings = session_store.load(username)
        
        # Try to restore session from bundle
        session_restored = False
        
        if persisted_settings and persisted_settings.get('authorization_data', {}).get('sessionid'):
            sessionid = persisted_settings['authorization_data']['sessionid']
            # Decode URL-encoded sessionid
            import urllib.parse
            sessionid = urllib.parse.unquote(sessionid)
            if isinstance(sessionid, str) and len(sessionid) > 30:
                try:
                    log.info(f"[SESSION] Attempting to restore session for {username}")
                    if on_log:
                        on_log(f"Restoring session from bundle...")
                    
                    result = cl.login_by_sessionid(sessionid)
                    if result:
                        log.info(f"[SESSION] Successfully restored session for {username}")
                        if on_log:
                            on_log("Session restored successfully")
                        session_restored = True
                    else:
                        log.warning(f"[SESSION] Failed to restore session for {username}")
                        if on_log:
                            on_log("Session restoration failed")
                except Exception as e:
                    log.warning(f"[SESSION] Session restoration error for {username}: {e}")
                    if on_log:
                        on_log(f"Session restoration error: {e}")
        
        # Auth: use restored session or fallback to login with TOTP/email
        if not session_restored:
            provider = CompositeProvider([
                TOTPProvider(None),  # Will be set by auth service
                AutoIMAPEmailProvider(None, None, on_log=on_log),  # Will be set by auth service
            ])
            auth = IGAuthService(provider)
            if not auth.ensure_logged_in(cl, username, password, on_log=on_log):
                if on_log:
                    on_log("Authentication failed")
                return False
        else:
            # Verify restored session is valid
            try:
                user_info = cl.user_info_v1(cl.user_id)
                if user_info and user_info.username == username:
                    log.info(f"[SESSION] Session verified for {username}")
                    if on_log:
                        on_log("Session verified")
                else:
                    log.warning(f"[SESSION] Session verification failed for {username}")
                    if on_log:
                        on_log("Session verification failed, falling back to login")
                    # Fallback to login
                    provider = CompositeProvider([
                        TOTPProvider(None),
                        AutoIMAPEmailProvider(None, None, on_log=on_log),
                    ])
                    auth = IGAuthService(provider)
                    if not auth.ensure_logged_in(cl, username, password, on_log=on_log):
                        if on_log:
                            on_log("Authentication failed")
                        return False
            except Exception as e:
                log.warning(f"[SESSION] Session verification error for {username}: {e}")
                if on_log:
                    on_log(f"Session verification error: {e}")
                # Fallback to login
                provider = CompositeProvider([
                    TOTPProvider(None),
                    AutoIMAPEmailProvider(None, None, on_log=on_log),
                ])
                auth = IGAuthService(provider)
                if not auth.ensure_logged_in(cl, username, password, on_log=on_log):
                    if on_log:
                        on_log("Authentication failed")
                    return False
        
        return True 