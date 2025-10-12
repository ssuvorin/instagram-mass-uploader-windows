from __future__ import annotations
from typing import Optional, Protocol, Any


class SessionStore(Protocol):
    def load(self, username: str) -> Optional[dict]:
        ...

    def save(self, username: str, settings: dict) -> None:
        ...


class NoopSessionStore:
    def load(self, username: str) -> Optional[dict]:
        return None

    def save(self, username: str, settings: dict) -> None:
        return None


class DjangoDeviceSessionStore(NoopSessionStore):
    """
    Stores session settings into Django model InstagramDevice if accessible.
    Safe to import lazily to avoid circular imports.
    """
    def __init__(self) -> None:
        self._models = None

    def _get_models(self):
        if not self._models:
            from uploader.models import InstagramAccount, InstagramDevice  # type: ignore
            self._models = (InstagramAccount, InstagramDevice)
        return self._models

    def load(self, username: str) -> Optional[dict]:
        try:
            InstagramAccount, InstagramDevice = self._get_models()
            acc = InstagramAccount.objects.filter(username=username).first()
            if not acc:
                print(f"[DEBUG] Account {username} not found in database")
                return None
            dev = getattr(acc, 'device', None)
            if not dev:
                print(f"[DEBUG] Device not found for account {username}")
                return None
            session_settings = getattr(dev, 'session_settings', None)
            print(f"[DEBUG] Loaded session_settings for {username}: {type(session_settings)}, keys: {list(session_settings.keys()) if session_settings else 'None'}")
            return session_settings
        except Exception as e:
            print(f"[DEBUG] Error loading session for {username}: {e}")
            return None

    def save(self, username: str, settings: dict) -> None:
        try:
            InstagramAccount, InstagramDevice = self._get_models()
            acc = InstagramAccount.objects.filter(username=username).first()
            if not acc:
                print(f"[DEBUG] Account {username} not found for saving session")
                return
            dev = getattr(acc, 'device', None)
            if not dev:
                dev = InstagramDevice.objects.create(account=acc, device_settings={}, user_agent="")
                print(f"[DEBUG] Created new device for account {username}")
            
            print(f"[DEBUG] Saving session_settings for {username}: keys: {list(settings.keys())}")
            if 'authorization_data' in settings:
                sessionid = settings['authorization_data'].get('sessionid')
                print(f"[DEBUG] sessionid to save: {str(sessionid)[:50] if sessionid else 'None'}...")
            
            dev.session_settings = settings
            dev.save(update_fields=['session_settings'])
            print(f"[DEBUG] Session saved successfully for {username}")
        except Exception as e:
            print(f"[DEBUG] Error saving session for {username}: {e}")
            return 