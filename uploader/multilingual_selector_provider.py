"""
Multilingual Selector Provider for Instagram automation
Provides locale-aware selectors with fallback support for bulk upload async pipeline
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import time

from .i18n.manager import LanguageManager
from .selectors_config import InstagramSelectors as SelectorConfig


@dataclass
class SelectorResult:
    """Result of selector attempt with metadata"""
    success: bool
    selector_used: str
    language_used: str
    fallback_level: int  # 0=primary, 1=english, 2=semantic
    element_found: bool
    execution_time_ms: float
    error_message: Optional[str] = None


class LocaleResolver:
    """Resolves account locale to language codes"""
    
    @staticmethod
    def resolve_account_locale(account) -> str:
        """Resolve account locale from various sources"""
        if hasattr(account, 'locale') and account.locale:
            return LanguageManager.resolve_language_from_locale(account.locale)
        
        # Fallback to default based on account region or other indicators
        if hasattr(account, 'username') and account.username:
            # Simple heuristic based on username patterns (can be enhanced)
            username = account.username.lower()
            if any(indicator in username for indicator in ['es', 'mx', 'ar', 'co', 'cl']):
                return 'es'
            elif any(indicator in username for indicator in ['br', 'pt']):
                return 'pt'
        
        return 'ru'  # Default fallback
    
    @staticmethod
    def get_language_priority(locale: str) -> List[str]:
        """Get language priority list for fallback chain"""
        if locale == 'es':
            return ['es', 'en', 'ru']
        elif locale == 'pt':
            return ['pt', 'en', 'ru']
        elif locale == 'en':
            return ['en', 'ru']
        else:
            return ['ru', 'en']


class MultilingualSelectorProvider:
    """Provides locale-aware selectors with fallback support"""
    
    def __init__(self, i18n_manager: Optional[LanguageManager] = None):
        self.i18n = i18n_manager or LanguageManager()
        self.selector_cache: Dict[str, List[str]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Text-based selector templates using i18n keys
        self.text_selector_templates = {
            'upload_button': [
                'button:has-text("{upload.button}")',
                'div[role="button"]:has-text("{upload.button}")',
                'a:has(span:has-text("{upload.button}"))',
                'span:has-text("{upload.button}")',
                'a[role="link"]:has(span:has-text("{upload.button}"))'
            ],
            'next_button': [
                'button:has-text("{button.next}")',
                'div[role="button"]:has-text("{button.next}")',
                'button:has-text("{button.continue}")',
                'div[role="button"]:has-text("{button.continue}")'
            ],
            'share_button': [
                'button:has-text("{button.share}")',
                'div[role="button"]:has-text("{button.share}")'
            ],
            'login_submit': [
                'button:has-text("{login.submit}")',
                'div[role="button"]:has-text("{login.submit}")',
                'button[type="submit"]:has-text("{login.submit}")'
            ],
            'not_now_button': [
                'button:has-text("{button.not_now}")',
                'div[role="button"]:has-text("{button.not_now}")'
            ],
            'ok_button': [
                'button:has-text("{button.ok}")',
                'div[role="button"]:has-text("{button.ok}")'
            ],
            'accept_button': [
                'button:has-text("{dialog.ok}")',
                'div[role="button"]:has-text("{dialog.ok}")'
            ],
            'done_button': [
                'button:has-text("{button.done}")',
                'div[role="button"]:has-text("{button.done}")'
            ],
            'file_select_button': [
                'button:has-text("{upload.select_from_computer}")',
                'div[role="button"]:has-text("{upload.select_from_computer}")',
                'button:has-text("{upload.select_files}")',
                'div[role="button"]:has-text("{upload.select_files}")'
            ],
            'caption_textarea': [
                'div[contenteditable="true"][aria-label*="{caption.write}"]',
                'div[contenteditable="true"][aria-label*="{caption.description}"]',
                'div[contenteditable="true"][aria-placeholder*="{caption.aria_placeholder}"]',
                'textarea[aria-label*="{caption.write}"]',
                'div[contenteditable="true"][aria-placeholder*="{caption.write}"]',
                'div[contenteditable="true"][aria-placeholder*="{caption.description}"]',
                'textarea[placeholder*="{caption.placeholder}"]',
                'div[contenteditable="true"][placeholder*="{caption.placeholder}"]',
                'div[role="textbox"][contenteditable="true"]',
                'div[contenteditable="true"][data-lexical-editor="true"]'
            ],
            'post_option': [
                'a:has(span:has-text("{upload.post}"))',
                'div[role="menuitem"]:has(span:has-text("{upload.post}"))',
                'span:has-text("{upload.post}")'
            ],
            'crop_original': [
                'span:has-text("{crop.original}")',
                'button:has-text("{crop.original}")',
                'div[role="button"]:has-text("{crop.original}")',
                'div:has(span:has-text("{crop.original}"))',
                '[role="button"]:has(span:has-text("{crop.original}"))'
            ]
        }
        
        # Semantic selectors (language-independent) - highest priority
        # Эти селекторы берутся из SelectorConfig для централизации
        self.semantic_selectors = {
            'upload_button': [
                'svg[aria-label*="New post"]',
                'svg[aria-label*="Nueva publicación"]',
                'svg[aria-label*="Nova publicação"]',
                'svg[aria-label*="Новая публикация"]',
                'svg[aria-label*="Create"]',
                'svg[aria-label*="Crear"]',
                'svg[aria-label*="Criar"]',
                'svg[aria-label*="Создать"]',
                'a[href="/create/select/"]',
                'button[data-testid="new-post-button"]'
            ],
            'next_button': [
                'button[type="submit"]',
                'button[data-testid="next-button"]',
                '[role="button"][tabindex="0"]'
            ],
            'share_button': [
                'button[type="submit"]',
                'button[data-testid="share-button"]'
            ],
            'file_input': [
                'input[type="file"]',
                'input[accept*="image"]',
                'input[accept*="video"]'
            ],
            'reels_dialog_accept': []  # Используем только текстовые селекторы для кнопок
        }
    
    def get_selectors(self, selector_type: str, locale: str = 'ru') -> List[str]:
        """Generate selectors for given type and locale with fallback chain"""
        cache_key = f"{selector_type}_{locale}"
        
        if cache_key in self.selector_cache:
            return self.selector_cache[cache_key]
        
        all_selectors = []
        
        # 1. Add semantic selectors first (highest priority)
        if selector_type in self.semantic_selectors:
            all_selectors.extend(self.semantic_selectors[selector_type])
        
        # 2. Add text-based selectors for language chain
        language_chain = LocaleResolver.get_language_priority(locale)
        
        if selector_type in self.text_selector_templates:
            templates = self.text_selector_templates[selector_type]
            
            for lang in language_chain:
                text_selectors = self._generate_text_selectors(templates, lang)
                all_selectors.extend(text_selectors)
        
        # 3. Add legacy static selectors as fallback
        legacy_selectors = self._get_legacy_selectors(selector_type)
        all_selectors.extend(legacy_selectors)
        
        # Remove duplicates while preserving order
        unique_selectors = []
        seen = set()
        for selector in all_selectors:
            if selector not in seen:
                unique_selectors.append(selector)
                seen.add(selector)
        
        self.selector_cache[cache_key] = unique_selectors
        return unique_selectors
    
    def _generate_text_selectors(self, templates: List[str], locale: str) -> List[str]:
        """Generate text-based selectors using i18n translations"""
        selectors = []
        
        for template in templates:
            try:
                # Find all i18n keys in template
                import re
                keys = re.findall(r'\{([^}]+)\}', template)
                
                # Replace each key with translated text
                selector = template
                for key in keys:
                    translated_text = self.i18n.t(key, locale)
                    selector = selector.replace(f'{{{key}}}', translated_text)
                
                selectors.append(selector)
                
            except Exception as e:
                self.logger.warning(f"Failed to generate selector from template {template}: {e}")
                continue
        
        return selectors
    
    def _get_legacy_selectors(self, selector_type: str) -> List[str]:
        """Get legacy static selectors as final fallback"""
        legacy_mapping = {
            'upload_button': getattr(SelectorConfig, 'UPLOAD_BUTTON', []),
            'next_button': getattr(SelectorConfig, 'NEXT_BUTTON', []),
            'share_button': getattr(SelectorConfig, 'SHARE_BUTTON', []),
            'file_input': getattr(SelectorConfig, 'FILE_INPUT', []),
            'caption_textarea': getattr(SelectorConfig, 'CAPTION_TEXTAREA', []),
            'post_option': getattr(SelectorConfig, 'POST_OPTION', []),
            'login_submit': getattr(SelectorConfig, 'LOGIN_FORM', {}).get('submit', []),
            'not_now_button': [],
            'ok_button': getattr(SelectorConfig, 'OK_BUTTON', []),
            'done_button': getattr(SelectorConfig, 'DONE_BUTTON', []),
            'crop_original': getattr(SelectorConfig, 'CROP_ORIGINAL_SELECTORS', []),
            'accept_button': getattr(SelectorConfig, 'OK_ACCEPT_BUTTONS', []),
            'reels_dialog_accept': getattr(SelectorConfig, 'REELS_DIALOG_ACCEPT_BUTTONS', [])
        }
        
        return legacy_mapping.get(selector_type, [])
    
    def get_upload_button_selectors(self, locale: str = 'ru') -> List[str]:
        """Get upload button selectors for bulk upload async"""
        return self.get_selectors('upload_button', locale)
    
    def get_next_button_selectors(self, locale: str = 'ru') -> List[str]:
        """Get next button selectors for bulk upload async"""
        return self.get_selectors('next_button', locale)
    
    def get_share_button_selectors(self, locale: str = 'ru') -> List[str]:
        """Get share button selectors for bulk upload async"""
        return self.get_selectors('share_button', locale)
    
    def get_file_input_selectors(self, locale: str = 'ru') -> List[str]:
        """Get file input selectors for bulk upload async"""
        return self.get_selectors('file_input', locale)
    
    def get_caption_textarea_selectors(self, locale: str = 'ru') -> List[str]:
        """Get caption textarea selectors for bulk upload async"""
        return self.get_selectors('caption_textarea', locale)
    
    def get_post_option_selectors(self, locale: str = 'ru') -> List[str]:
        """Get post option selectors for bulk upload async"""
        return self.get_selectors('post_option', locale)
    
    def get_login_submit_selectors(self, locale: str = 'ru') -> List[str]:
        """Get login submit selectors for bulk upload async"""
        return self.get_selectors('login_submit', locale)
    
    def get_not_now_selectors(self, locale: str = 'ru') -> List[str]:
        """Get not now button selectors for bulk upload async"""
        return self.get_selectors('not_now_button', locale)
    
    def get_ok_button_selectors(self, locale: str = 'ru') -> List[str]:
        """Get OK button selectors for bulk upload async"""
        return self.get_selectors('ok_button', locale)
    
    def get_done_button_selectors(self, locale: str = 'ru') -> List[str]:
        """Get done button selectors for bulk upload async"""
        return self.get_selectors('done_button', locale)
    
    def get_crop_original_selectors(self, locale: str = 'ru') -> List[str]:
        """Get crop original selectors for bulk upload async"""
        return self.get_selectors('crop_original', locale)
    
    def get_reels_dialog_accept_selectors(self, locale: str = 'ru') -> List[str]:
        """Get Reels dialog accept button selectors for bulk upload async"""
        return self.get_selectors('accept_button', locale)
    
    def clear_cache(self):
        """Clear selector cache"""
        self.selector_cache.clear()


# Global instance for easy access in bulk upload async
_global_provider = None

def get_multilingual_selector_provider() -> MultilingualSelectorProvider:
    """Get global multilingual selector provider instance"""
    global _global_provider
    if _global_provider is None:
        _global_provider = MultilingualSelectorProvider()
    return _global_provider