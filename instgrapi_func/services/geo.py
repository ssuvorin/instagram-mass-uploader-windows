from __future__ import annotations
from typing import Dict, Optional, Tuple
import re
import time
import random

try:
	import requests  # type: ignore
except Exception:  # pragma: no cover
	requests = None  # type: ignore

# Minimal mapping. Extend as needed.
_COUNTRY_TO_LOCALE = {
    'RU': 'ru_RU',
    'US': 'en_US',
    'UA': 'uk_UA',
    'BY': 'be_BY',
    'KZ': 'kk_KZ',
    'TR': 'tr_TR',
    'IN': 'en_IN',
}

_COUNTRY_TO_CODE = {
    'RU': 7,
    'US': 1,
    'UA': 380,
    'BY': 375,
    'KZ': 7,
    'TR': 90,
    'IN': 91,
}

# Offsets in seconds (MSK +3:00 = 10800)
_COUNTRY_TO_TZ = {
    'RU': 10800,
    'US': -14400,  # default to EDT for simplicity
    'UA': 10800,
    'BY': 10800,
    'KZ': 18000,
    'TR': 10800,
    'IN': 19800,
}


def _normalize_country(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip().upper()
    if len(v) == 2:
        return v
    # try map common names to codes
    names = {
        'RUSSIA': 'RU', 'RUSSIAN FEDERATION': 'RU', 'РОССИЯ': 'RU',
        'UNITED STATES': 'US', 'USA': 'US',
        'UKRAINE': 'UA', 'УКРАИНА': 'UA',
        'BELARUS': 'BY', 'БЕЛАРУСЬ': 'BY', 'БЕЛАРУСЬ (БЕЛАРУСЬ)': 'BY',
        'KAZAKHSTAN': 'KZ', 'ҚАЗАҚСТАН': 'KZ',
        'TURKEY': 'TR', 'TÜRKİYE': 'TR',
        'INDIA': 'IN', 'ИНДИЯ': 'IN',
    }
    return names.get(v) or None


def resolve_geo(proxy: Optional[Dict]) -> Dict:
    """
    Build geo settings from proxy data. Defaults to RU/MSK if unknown.
    Returns dict with: country, country_code, locale, timezone_offset
    """
    default_country = 'RU'
    country = None
    if proxy:
        country = _normalize_country(proxy.get('country'))
    country = country or default_country
    return {
        'country': country,
        'country_code': _COUNTRY_TO_CODE.get(country, 7),
        'locale': _COUNTRY_TO_LOCALE.get(country, 'ru_RU'),
        'timezone_offset': _COUNTRY_TO_TZ.get(country, 10800),
    }


# Known popular city name → (display_name, lat, lng)
_KNOWN_LOCATIONS: Dict[str, Tuple[str, float, float]] = {
	# Russia
	'москва, россия': ('Москва, Россия', 55.7558, 37.6173),
	'москва': ('Москва, Россия', 55.7558, 37.6173),
	'moscow, russia': ('Moscow, Russia', 55.7558, 37.6173),
	'moscow': ('Moscow, Russia', 55.7558, 37.6173),
	'санкт-петербург': ('Санкт-Петербург, Россия', 59.9343, 30.3351),
	'питер': ('Санкт-Петербург, Россия', 59.9343, 30.3351),
	'saint petersburg': ('Saint Petersburg, Russia', 59.9343, 30.3351),
	'st petersburg': ('Saint Petersburg, Russia', 59.9343, 30.3351),
	'казань': ('Казань, Россия', 55.7963, 49.1088),
	'sochi': ('Sochi, Russia', 43.5855, 39.7231),
	'сочи': ('Сочи, Россия', 43.5855, 39.7231),
	# Belarus
	'минск, беларусь': ('Минск, Беларусь', 53.9006, 27.5590),
	'минск': ('Минск, Беларусь', 53.9006, 27.5590),
	'minsk, belarus': ('Minsk, Belarus', 53.9006, 27.5590),
	# Ukraine
	'киев': ('Киев, Украина', 50.4501, 30.5234),
	'київ': ('Київ, Україна', 50.4501, 30.5234),
	'kyiv': ('Kyiv, Ukraine', 50.4501, 30.5234),
	# Kazakhstan
	'алматы': ('Алматы, Казахстан', 43.2383, 76.9450),
	'almaty': ('Almaty, Kazakhstan', 43.2383, 76.9450),
	'астана': ('Астана, Казахстан', 51.1694, 71.4491),
	'nur-sultan': ('Nur-Sultan, Kazakhstan', 51.1694, 71.4491),
	# Turkey
	'istanbul': ('Istanbul, Türkiye', 41.0082, 28.9784),
	'стамбул': ('Стамбул, Турция', 41.0082, 28.9784),
	# USA
	'new york': ('New York, USA', 40.7128, -74.0060),
	'нью-йорк': ('Нью-Йорк, США', 40.7128, -74.0060),
}


def _normalize_text(value: Optional[str]) -> str:
    if not value:
        return ''
    v = value.strip().lower()
    v = re.sub(r'\s+', ' ', v)
    return v


def _cache_get(key: str) -> Optional[Tuple[str, float, float]]:
    try:
        from django.core.cache import cache  # type: ignore
        return cache.get(key)
    except Exception:
        return None


def _cache_set(key: str, value: Tuple[str, float, float], ttl_sec: int = 86400) -> None:
    try:
        from django.core.cache import cache  # type: ignore
        cache.set(key, value, ttl_sec)
    except Exception:
        pass


def resolve_location_coordinates(text: Optional[str], proxy: Optional[Dict] = None, accept_language: Optional[str] = None) -> Optional[Tuple[str, float, float]]:
    """Resolve free-text like 'Москва, Россия' to (display_name, lat, lng).
    Strategy:
      1) Quick dictionary of known places
      2) Cache lookup
      3) Nominatim (OpenStreetMap) geocoding
    Returns None if not resolvable.
    """
    if not text:
        return None
    q = _normalize_text(text)

    # 1) Known dictionary
    if q in _KNOWN_LOCATIONS:
        return _KNOWN_LOCATIONS[q]

    # 2) Cache
    cache_key = f"loc:{q}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    # 3) Nominatim
    if requests is None:
        return None

    # Deduce language
    try:
        lang = accept_language or resolve_geo(proxy).get('locale', 'ru_RU').split('_')[0]
    except Exception:
        lang = 'ru'

    # Respectful tiny random delay
    time.sleep(random.uniform(0.2, 0.6))

    try:
        params = {
            'q': text,
            'format': 'json',
            'limit': 1,
            'accept-language': lang,
        }
        headers = {
            'User-Agent': 'insta-uploader/1.0 (+https://github.com)'
        }
        proxies = None
        if proxy:
            try:
                # Build requests proxies dict from our proxy fields
                scheme = proxy.get('scheme') or 'http'
                auth = ''
                if proxy.get('username') and proxy.get('password'):
                    auth = f"{proxy['username']}:{proxy['password']}@"
                host = proxy.get('host') or proxy.get('ip') or ''
                port = proxy.get('port') or ''
                netloc = f"{auth}{host}:{port}" if port else f"{auth}{host}"
                proxy_url = f"{scheme}://{netloc}"
                proxies = {'http': proxy_url, 'https': proxy_url}
            except Exception:
                proxies = None

        resp = requests.get('https://nominatim.openstreetmap.org/search', params=params, headers=headers, proxies=proxies, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                d = data[0]
                name = d.get('display_name') or text
                lat = float(d.get('lat'))
                lon = float(d.get('lon'))
                result = (name, lat, lon)
                _cache_set(cache_key, result)
                return result
    except Exception:
        return None

    return None 