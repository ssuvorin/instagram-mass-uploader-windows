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
                return None
            dev = getattr(acc, 'device', None)
            return getattr(dev, 'session_settings', None)
        except Exception:
            return None

    def save(self, username: str, settings: dict) -> None:
        try:
            InstagramAccount, InstagramDevice = self._get_models()
            acc = InstagramAccount.objects.filter(username=username).first()
            if not acc:
                return
            dev = getattr(acc, 'device', None)
            if not dev:
                dev = InstagramDevice.objects.create(account=acc, device_settings={}, user_agent="")
            dev.session_settings = settings
            dev.save(update_fields=['session_settings'])
        except Exception:
            return 