from __future__ import annotations
from typing import Dict, Optional, Tuple

# Minimal mapping. Extend as needed.
_COUNTRY_TO_LOCALE = {
    'RU': 'ru_RU',
    'US': 'en_US',
    'UA': 'uk_UA',
    'BY': 'be_BY',
    'KZ': 'kk_KZ',
    'TR': 'tr_TR',
}

_COUNTRY_TO_CODE = {
    'RU': 7,
    'US': 1,
    'UA': 380,
    'BY': 375,
    'KZ': 7,
    'TR': 90,
}

# Offsets in seconds (MSK +3:00 = 10800)
_COUNTRY_TO_TZ = {
    'RU': 10800,
    'US': -14400,  # default to EDT for simplicity
    'UA': 10800,
    'BY': 10800,
    'KZ': 18000,
    'TR': 10800,
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