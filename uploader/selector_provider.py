from typing import List

from .selectors_config import InstagramSelectors as SelectorConfig


class BaseSelectorProvider:
    """Base interface for selector providers."""

    def get_login_username_selectors(self) -> List[str]:
        return SelectorConfig.LOGIN_FORM.get('username', [])

    def get_login_password_selectors(self) -> List[str]:
        return SelectorConfig.LOGIN_FORM.get('password', [])

    def get_login_submit_selectors(self) -> List[str]:
        base = list(SelectorConfig.LOGIN_FORM.get('submit', []))
        extras = [
            'button:has-text("Iniciar sesión")',
            'div[role="button"]:has-text("Iniciar sesión")',
            'button:has-text("Entrar")',
            'div[role="button"]:has-text("Entrar")',
        ]
        return base + extras

    def get_not_now_selectors(self) -> List[str]:
        return [
            'button:has-text("Не сейчас")',
            'button:has-text("Not now")',
            'button:has-text("Not Now")',
            'button:has-text("Agora não")',
            'button:has-text("Ahora no")',
            'div[role="button"]:has-text("Не сейчас")',
            'div[role="button"]:has-text("Not now")',
            'div[role="button"]:has-text("Agora não")',
            'div[role="button"]:has-text("Ahora no")',
        ]

    def get_save_login_selectors(self) -> List[str]:
        return [
            'button:has-text("Сохранить")',
            'button:has-text("Save")',
            'button:has-text("Guardar")',
            'button:has-text("Salvar")',
            'div[role="button"]:has-text("Сохранить")',
            'div[role="button"]:has-text("Save")',
            'div[role="button"]:has-text("Guardar")',
            'div[role="button"]:has-text("Salvar")',
        ]

    def get_next_button_selectors(self) -> List[str]:
        base = list(SelectorConfig.NEXT_BUTTON)
        extras = [
            'button:has-text("Siguiente")',
            'div[role="button"]:has-text("Siguiente")',
            'button:has-text("Avançar")',
            'div[role="button"]:has-text("Avançar")',
            'button:has-text("Weiter")',      # DE
            'div[role="button"]:has-text("Weiter")',      # DE
            'button:has-text("Fortfahren")',  # DE
            'div[role="button"]:has-text("Fortfahren")',  # DE
            'button:has-text("Επόμενο")',     # EL
            'div[role="button"]:has-text("Επόμενο")',     # EL
            'button:has-text("Συνέχεια")',    # EL
            'div[role="button"]:has-text("Συνέχεια")',    # EL
        ]
        return base + extras

    def get_share_button_selectors(self) -> List[str]:
        base = list(SelectorConfig.SHARE_BUTTON)
        extras = [
            'button:has-text("Compartir")',
            'div[role="button"]:has-text("Compartir")',
            'button:has-text("Compartilhar")',
            'div[role="button"]:has-text("Compartilhar")',
            'button:has-text("Teilen")',        # DE
            'div[role="button"]:has-text("Teilen")',        # DE
            'button:has-text("Veröffentlichen")', # DE
            'div[role="button"]:has-text("Veröffentlichen")', # DE
            'button:has-text("Κοινοποίηση")',   # EL
            'div[role="button"]:has-text("Κοινοποίηση")',   # EL
            'button:has-text("Δημοσίευση")',    # EL
            'div[role="button"]:has-text("Δημοσίευση")',    # EL
        ]
        return base + extras

    def get_caption_textarea_selectors(self) -> List[str]:
        base = list(SelectorConfig.CAPTION_TEXTAREA)
        extras = [
            'textarea[aria-label*="Escribe un pie de foto"]',
            'textarea[placeholder*="Escribe un pie de foto"]',
            'textarea[aria-label*="Escreva uma legenda"]',
            'textarea[placeholder*="Escreva uma legenda"]',
        ]
        return base + extras


class InstagramSelectorProvider(BaseSelectorProvider):
    pass


