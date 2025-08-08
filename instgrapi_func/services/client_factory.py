from typing import Optional, Dict
from instagrapi import Client
from .geo import resolve_geo


class IGClientFactory:
    @staticmethod
    def create_client(
        device_config: Optional[Dict] = None,
        proxy_url: Optional[str] = None,
        session_settings: Optional[Dict] = None,
        user_agent: Optional[str] = None,
        country: Optional[str] = None,
        locale: Optional[str] = None,
        proxy_dict: Optional[Dict] = None,
    ) -> Client:
        cl = Client()

        # Proxy
        if proxy_url:
            try:
                cl.set_proxy(proxy_url)
            except Exception:
                pass

        # Device
        if device_config:
            try:
                cl.set_device(device_config)
                for key in ("uuid", "android_device_id", "phone_id", "client_session_id"):
                    if device_config.get(key):
                        setattr(cl, key, device_config[key])
            except Exception:
                pass

        # Geo from proxy if not explicitly provided
        geo = resolve_geo(proxy_dict or {})
        country = country or geo.get('country')
        locale = locale or geo.get('locale')
        tz_offset = geo.get('timezone_offset')

        if user_agent:
            try:
                cl.set_user_agent(user_agent)
            except Exception:
                pass

        if country:
            try:
                cl.set_country(country)
            except Exception:
                pass

        if locale:
            try:
                cl.set_locale(locale)
            except Exception:
                pass

        if tz_offset is not None:
            try:
                cl.set_timezone_offset(tz_offset)
            except Exception:
                pass

        # Session
        if session_settings:
            try:
                cl.set_settings(session_settings)
            except Exception:
                pass

        return cl 