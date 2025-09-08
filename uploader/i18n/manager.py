import json
import os
from typing import Dict


class LanguageManager:
    """Lightweight i18n manager with strict fallback: account language -> en -> raw key"""

    def __init__(self, base_path: str | None = None):
        self.base_path = base_path or os.path.join(os.path.dirname(__file__), 'resources')
        self._cache: Dict[str, Dict[str, str]] = {}

    def _load_lang(self, lang: str) -> Dict[str, str]:
        lang = (lang or 'en').lower()
        if lang in self._cache:
            return self._cache[lang]
        file_path = os.path.join(self.base_path, f'{lang}.json')
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._cache[lang] = {str(k): str(v) for k, v in data.items()}
                else:
                    self._cache[lang] = {}
        except Exception:
            self._cache[lang] = {}
        return self._cache[lang]

    def t(self, key: str, lang: str) -> str:
        """Translate a key using fallback chain: lang -> en -> raw key"""
        key = str(key)
        lang_map = self._load_lang(lang)
        if key in lang_map:
            return lang_map[key]
        en_map = self._load_lang('en')
        if key in en_map:
            return en_map[key]
        return key

    @staticmethod
    def resolve_language_from_locale(locale_str: str) -> str:
        """Map Dolphin-style locale ru_BY, es_CL, pt_BR to language code ru, es, pt, en"""
        try:
            lang = (locale_str or 'ru_BY').split('_', 1)[0].lower()
            if lang in ('ru', 'en', 'es', 'pt'):
                return lang
            return 'ru'
        except Exception:
            return 'ru'

    @staticmethod
    def accept_language_for_locale(locale_str: str) -> str:
        s = (locale_str or '').strip().replace('_', '-')
        if not s:
            return 'ru-BY,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        lang = s.split('-')[0].lower()
        if lang == 'ru':
            return 'ru-BY,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        if lang == 'en':
            return f'{s},en;q=0.9'
        if lang == 'es':
            return f'{s},es;q=0.9,en;q=0.8,ru;q=0.7'
        if lang == 'pt':
            return f'{s},pt;q=0.9,en;q=0.8,ru;q=0.7'
        return 'ru-BY,ru;q=0.9,en-US;q=0.8,en;q=0.7'


