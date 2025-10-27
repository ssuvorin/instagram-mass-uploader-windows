"""
reCAPTCHA Constants and Selectors
Centralized constants for reCAPTCHA solving across different components
"""

# Audio Challenge Selectors
AUDIO_CHALLENGE_SELECTORS = {
    'iframe_selectors': [
        'iframe[title*="recaptcha challenge"]',
        'iframe[title*="desafío de recaptcha"]',
        'iframe[title*="el desafío de recaptcha"]',  # Spanish full title
        'iframe[title*="desafío de recaptcha caduca"]',  # Spanish with timeout
        'iframe[src*="recaptcha"][src*="bframe"]',
        'iframe[name*="c-"]',
        'iframe[title*="reCAPTCHA"]',
        'iframe[title*="recaptcha"]'
    ],

    'play_button_selectors': [
        'xpath=//button[@id=":2"]',  # ID-based selector
        'xpath=//button[contains(text(), "REPRODUCIR")]',  # Spanish "Play"
        'xpath=//button[contains(text(), "PLAY")]',  # English "Play"
        'xpath=//button[contains(text(), "再生")]',  # Japanese "Play"
        'xpath=//button[contains(text(), "LECTURE")]',  # French "Play"
        'xpath=//button[contains(text(), "RIproduci")]',  # Italian "Play"
        'xpath=//button[@class="rc-button-default goog-inline-block"]',  # Class-based
        'xpath=//button[@aria-labelledby="audio-instructions rc-response-label"]'  # Aria label
    ],

    'audio_element_selectors': [
        'xpath=//audio[@id="audio-source"]',
        'xpath=//audio[contains(@src, "recaptcha/api2/payload")]',
        'xpath=//audio[@style="display: none"]',  # Usually hidden
        'audio#audio-source',  # Fallback to CSS selector
        'audio'  # Last resort - any audio element
    ],

    'input_field_selectors': [
        'xpath=//input[@id="audio-response"]',
        'xpath=//input[@class="rc-response-input-field label-input-label"]',
        'xpath=//input[@autocomplete="off"][@autocorrect="off"]',
        'xpath=//input[contains(@class, "rc-response-input")]',
        'input#audio-response',  # CSS fallback
        'input[type="text"]'  # Generic text input
    ],

    'verify_button_selectors': [
        'xpath=//button[@id="recaptcha-verify-button"]',
        'xpath=//button[contains(text(), "Verificar")]',  # Spanish
        'xpath=//button[contains(text(), "Verify")]',  # English
        'xpath=//button[contains(text(), "検証")]',  # Japanese
        'xpath=//button[contains(text(), "Vérifier")]',  # French
        'xpath=//button[contains(text(), "Verifica")]',  # Italian
        'xpath=//button[contains(text(), "Überprüfen")]',  # German
        'xpath=//button[@class="rc-button-default goog-inline-block"]',  # Class-based
        'button#recaptcha-verify-button'  # CSS fallback
    ]
}

# Image Challenge Selectors
IMAGE_CHALLENGE_SELECTORS = {
    'container_selectors': [
        '#rc-imageselect',
        '.rc-imageselect',
        '[aria-modal="true"][role="dialog"]'  # Generic modal dialog
    ],

    'audio_button_selectors': [
        '#recaptcha-audio-button',
        'xpath=//button[@id="recaptcha-audio-button"]',
        'xpath=//button[contains(@title, "audio")]',  # Contains "audio" in title
        'xpath=//button[contains(@title, "de audio")]',  # Spanish "de audio"
        'xpath=//button[contains(@title, "音频")]',  # Chinese "audio"
        'xpath=//button[@class="rc-button goog-inline-block rc-button-audio"]'  # Class-based
    ]
}

# Detection Selectors
BOT_DETECTION_SELECTORS = [
    'text="Try again later"',
    'text="Vuelve a intentarlo más tarde"',  # Spanish "Try again later"
    'text="Your computer or network may be sending automated queries"',
    'xpath=//*[@class="rc-doscaptcha-body-text"]',
    'xpath=//*[@class="rc-doscaptcha-header-text"]',
    '.rc-doscaptcha-body-text',
    '.rc-doscaptcha-header-text',
    '[class*="rc-doscaptcha"]'  # Generic doscaptcha elements
]

# Supported Languages for Audio Recognition
SUPPORTED_LANGUAGES = ['en-US', 'en', 'es', 'fr', 'de', 'it', 'ja', 'zh-CN']

# Timeouts
TIMEOUTS = {
    'standard': 20,  # seconds
    'short': 5,      # seconds
    'detection': 2,  # seconds
    'element_wait': 5,  # seconds for element waits
    'click_timeout': 5   # seconds for clicks
}

# Audio Processing Settings
AUDIO_SETTINGS = {
    'temp_dir': None,  # Will be set to system temp dir
    'sample_rate': 16000,
    'channels': 1,  # Mono
    'energy_threshold': 300,
    'dynamic_energy': True,
    'pause_threshold': 0.8,
    'operation_timeout': 10
}

# Login Page Selectors (for continuing after captcha)
LOGIN_PAGE_SELECTORS = {
    'next_button_selectors': [
        'button[data-primary-action-label="Siguiente"]',  # Spanish "Next"
        'button[data-primary-action-label="Next"]',      # English "Next"
        'button[data-primary-action-label="Suivant"]',    # French "Next"
        'button[data-primary-action-label="Weiter"]',     # German "Next"
        'button:has-text("Siguiente")',                  # Spanish text
        'button:has-text("Next")',                       # English text
        'button:has-text("Suivant")',                    # French text
        'button:has-text("Weiter")',                     # German text
        '[data-primary-action-label="Siguiente"]',       # Generic attribute
        '[data-primary-action-label="Next"]',            # Generic attribute
        '[data-primary-action-label="Suivant"]',          # Generic attribute
        '[data-primary-action-label="Weiter"]',           # Generic attribute
        '.VfPpkd-LgbsSe:has-text("Siguiente")',          # Material Design class
        '.VfPpkd-LgbsSe:has-text("Next")',               # Material Design class
        '.VfPpkd-LgbsSe:has-text("Suivant")',            # Material Design class
        '.VfPpkd-LgbsSe:has-text("Weiter")',             # Material Design class
        'xpath=//button[contains(text(), "Siguiente")]', # XPath Spanish
        'xpath=//button[contains(text(), "Next")]',      # XPath English
        'xpath=//button[contains(text(), "Suivant")]',   # XPath French
        'xpath=//button[contains(text(), "Weiter")]',    # XPath German
        'xpath=//button[contains(@data-primary-action-label, "Siguiente")]', # XPath attribute
        'xpath=//button[contains(@data-primary-action-label, "Next")]'       # XPath attribute
    ]
}

# Captcha Solution Detection Selectors
CAPTCHA_SOLUTION_SELECTORS = {
    'solved_indicators': [
        '.recaptcha-checkbox-checked',           # Checkbox has checked class
        '[aria-checked="true"]',                 # ARIA checked attribute
        '.recaptcha-checkbox-checkmark',          # Checkmark element (legacy)
    ],
    'success_messages': [
        'text="Tu verificación se ha completado"',  # Spanish
        'text="Your verification has been completed"', # English
        'text="Votre vérification est terminée"',     # French
        'text="Ihre Überprüfung wurde abgeschlossen"', # German
        'text="Verificația dvs. a fost finalizată"',   # Romanian
        'text="Ваша перевірка завершена"',           # Ukrainian
        'text="تم التحقق من هويتك"',                # Arabic
        'text="您的驗證已完成"',                      # Chinese Traditional
        'text="验证已完成"',                         # Chinese Simplified
        'text="인증이 완료되었습니다"',              # Korean
        'text="検証が完了しました"',                 # Japanese
        'text="Verificação concluída"',              # Portuguese
        'text="Verificarea s-a încheiat"',           # Romanian alt
        'text="Doğrulama tamamlandı"',               # Turkish
        'text="Weryfikacja zakończona"',             # Polish
        'text="Ověření dokončeno"',                  # Czech
        'text="Ellenőrzés befejezve"',               # Hungarian
        'text="Verificarea a fost finalizată"',      # Romanian
        'text="Verifikacija završena"',             # Croatian
        'text="Verifikacija je završena"',          # Serbian
        'text="Verifikacija je končana"',           # Slovenian
        'text="Verificering voltooid"',             # Dutch
        'text="Verifisering fullført"',             # Norwegian
        'text="Verifikation slutförd"',             # Swedish
        'text="Verificarea s-a încheiat"',          # Romanian
        'text="Vahvistus valmis"',                  # Finnish
        'text="Verifikācija pabeigta"',             # Latvian
        'text="Patvirtinimas baigtas"',             # Lithuanian
        'text="Verificarea a fost finalizată"',      # Romanian
        'text="Verifikacija je završena"',          # Bosnian
        'text="Verificarea s-a încheiat"',          # Moldavian
        # Generic patterns
        'text="verification"',                      # Generic
        'text="completed"',                         # Generic
        'text="verified"',                          # Generic
        'text="success"',                           # Generic
    ]
}

# Retry Settings
RETRY_SETTINGS = {
    'max_retries': 3,
    'retry_delay': 5  # seconds
}
