# Instagram Selectors Configuration
# This file contains all CSS and XPath selectors used for Instagram automation

class InstagramSelectors:
    """Centralized Instagram selectors configuration"""
    
    # Upload button selectors
    UPLOAD_BUTTON = [
        # Russian selectors
        'svg[aria-label="Новая публикация"]',
        'a:has(svg[aria-label="Новая публикация"])',
        'span:has-text("Создать")',
        'a:has(span:has-text("Создать"))',
        'div[role="button"]:has-text("Создать")',
        'button:has-text("Создать")',
        
        # XPath selectors for Russian text
        '//span[contains(text(), "Создать")]',
        '//a[.//span[contains(text(), "Создать")]]',
        '//div[@role="button" and contains(text(), "Создать")]',
        '//button[contains(text(), "Создать")]',
        '//svg[@aria-label="Новая публикация"]',
        '//a[.//svg[@aria-label="Новая публикация"]]',
        
        # Aria-label based selectors
        '[aria-label*="Создать"]',
        '[aria-label*="Новая публикация"]',
        '[aria-label*="Create"]',
        '[aria-label*="New post"]',
        
        # English fallback selectors
        'svg[aria-label*="New post"]',
        'a:has(svg[aria-label*="New post"])',
        'span:has-text("Create")',
        'a:has(span:has-text("Create"))',
        'div[role="button"]:has-text("Create")',
        'button:has-text("Create")',
        
        # XPath selectors for English text
        '//span[contains(text(), "Create")]',
        '//a[.//span[contains(text(), "Create")]]',
        '//div[@role="button" and contains(text(), "Create")]',
        '//button[contains(text(), "Create")]',
        '//svg[@aria-label="New post"]',
        '//a[.//svg[@aria-label="New post"]]',
    ]
    
    # Post option selectors (for dropdown menu)
    POST_OPTION = [
        # Most likely selectors for Instagram's dropdown
        'a:has(span:has-text("Публикация"))',
        'div[role="menuitem"]:has(span:has-text("Публикация"))',
        'div[role="button"]:has(span:has-text("Публикация"))',
        
        # SVG-based selectors (Instagram often uses SVG icons)
        'svg[aria-label="Публикация"]',
        'a:has(svg[aria-label="Публикация"])',
        
        # Text-based selectors
        'span:has-text("Публикация")',
        
        # XPath selectors for more precise matching
        '//a[.//span[text()="Публикация"]]',
        '//div[@role="menuitem" and .//span[text()="Публикация"]]',
        '//span[text()="Публикация"]',
        
        # English fallbacks
        'a:has(span:has-text("Post"))',
        'div[role="menuitem"]:has(span:has-text("Post"))',
        'span:has-text("Post")',
        '//a[.//span[text()="Post"]]',
        '//span[text()="Post"]',
    ]
    
    # File input selectors
    FILE_INPUT = [
        # Traditional file input selectors (most stable)
        'input[type="file"]',
        'input[accept*="video"]',
        'input[accept*="image"]',
        'input[accept*="mp4"]',
        'input[accept*="quicktime"]',
        'input[accept*="jpeg"]',
        'input[accept*="png"]',
        'input[accept*="heic"]',
        'input[accept*="heif"]',
        'input[accept*="avif"]',
        'input[multiple]',
        
        # Form-based selectors (more stable than classes)
        'form[enctype="multipart/form-data"] input[type="file"]',
        'form[method="POST"] input[type="file"]',
        'form[role="presentation"] input[type="file"]',
        
        # Modern Instagram file selection buttons (Russian)
        'button:has-text("Выбрать на компьютере")',
        'div[role="button"]:has-text("Выбрать на компьютере")',
        'button:has-text("Выбрать файлы")',
        'div[role="button"]:has-text("Выбрать файлы")',
        'button:has-text("Выбрать с компьютера")',
        'div[role="button"]:has-text("Выбрать с компьютера")',
        
        # XPath selectors for Russian text
        '//button[contains(text(), "Выбрать на компьютере")]',
        '//div[@role="button" and contains(text(), "Выбрать на компьютере")]',
        '//button[contains(text(), "Выбрать файлы")]',
        '//div[@role="button" and contains(text(), "Выбрать файлы")]',
        '//button[contains(text(), "Выбрать с компьютера")]',
        '//div[@role="button" and contains(text(), "Выбрать с компьютера")]',
        
        # English fallback selectors
        'button:has-text("Select from computer")',
        'div[role="button"]:has-text("Select from computer")',
        'button:has-text("Select files")',
        'div[role="button"]:has-text("Select files")',
        'button:has-text("Choose files")',
        'div[role="button"]:has-text("Choose files")',
        
        # XPath selectors for English text
        '//button[contains(text(), "Select from computer")]',
        '//div[@role="button" and contains(text(), "Select from computer")]',
        '//button[contains(text(), "Select files")]',
        '//div[@role="button" and contains(text(), "Select files")]',
        '//button[contains(text(), "Choose files")]',
        '//div[@role="button" and contains(text(), "Choose files")]',
        
        # Aria-label based selectors (more stable)
        'button[aria-label*="Выбрать"]',
        'button[aria-label*="Select"]',
        'button[aria-label*="Choose"]',
        '[aria-label*="Выбрать файл"]',
        '[aria-label*="Select file"]',
        '[aria-label*="Choose file"]',
        
        # Generic upload area selectors
        'div[data-testid="file-upload"]',
        'button[data-testid="upload-button"]',
        
        # Drag and drop area selectors
        'div:has-text("Перетащите фото и видео сюда")',
        'div:has-text("Drag photos and videos here")',
        'div[role="button"]:has-text("Перетащите")',
        'div[role="button"]:has-text("Drag")',
        
        # Fallback: any file input in the page
        'input[type="file"]:not([style*="display: none"]):not([hidden])',
        'input[type="file"][style*="display: block"]',
        'input[type="file"][style*="visibility: visible"]',
    ]
    
    # OK button selectors
    OK_BUTTON = [
        'button:has-text("OK")',
        'button:has-text("ОК")',
    ]
    
    # Next button selectors
    NEXT_BUTTON = [
        'button:has-text("Далее")',
        'button:has-text("Next")',
        'div[role="button"]:has-text("Далее")',
        'div[role="button"]:has-text("Next")',
        '//button[contains(text(), "Далее")]',
        '//button[contains(text(), "Next")]',
        '//div[@role="button" and contains(text(), "Далее")]',
        '//div[@role="button" and contains(text(), "Next")]',
    ]
    
    # Share button selectors
    SHARE_BUTTON = [
        'button:has-text("Поделиться")',
        'button:has-text("Share")',
        'div[role="button"]:has-text("Поделиться")',
        'div[role="button"]:has-text("Share")',
        '//button[contains(text(), "Поделиться")]',
        '//button[contains(text(), "Share")]',
    ]
    
    # Caption textarea selectors
    CAPTION_TEXTAREA = [
        'textarea[aria-label*="Напишите подпись"]',
        'textarea[aria-label*="Write a caption"]',
        'textarea[placeholder*="Напишите подпись"]',
        'textarea[placeholder*="Write a caption"]',
        'div[contenteditable="true"][aria-label*="подпись"]',
        'div[contenteditable="true"][aria-label*="caption"]',
    ]
    
    # Login form selectors
    LOGIN_FORM = {
        'username': [
            'input[name="username"]',
            'input[aria-label*="Телефон"]',
            'input[aria-label*="Phone number"]',
            'input[placeholder*="Телефон"]',
            'input[placeholder*="Phone number"]',
        ],
        'password': [
            'input[name="password"]',
            'input[type="password"]',
            'input[aria-label*="Пароль"]',
            'input[aria-label*="Password"]',
        ],
        'submit': [
            'button[type="submit"]',
            'button:has-text("Войти")',
            'button:has-text("Log in")',
            'div[role="button"]:has-text("Войти")',
            'div[role="button"]:has-text("Log in")',
        ]
    }
    
    # 2FA code input selectors
    TFA_INPUT = [
        'input[name="verificationCode"]',
        'input[aria-label*="код"]',
        'input[aria-label*="code"]',
        'input[placeholder*="код"]',
        'input[placeholder*="code"]',
        'input[maxlength="6"]',
        'input[pattern="[0-9]*"]',
    ]
    
    # Success dialog selectors
    SUCCESS_DIALOG = [
        # Russian success messages
        'div:has-text("Ваша публикация опубликована")',
        'div:has-text("Публикация опубликована")',
        'div:has-text("Видео опубликовано")',
        'div:has-text("Пост опубликован")',
        'div:has-text("Опубликовано")',
        
        # English success messages
        'div:has-text("Your post has been shared")',
        'div:has-text("Post shared")',
        'div:has-text("Video posted")',
        'div:has-text("Posted successfully")',
        
        # XPath selectors for success messages
        '//div[contains(text(), "Ваша публикация опубликована")]',
        '//div[contains(text(), "Публикация опубликована")]',
        '//div[contains(text(), "Видео опубликовано")]',
        '//div[contains(text(), "Your post has been shared")]',
        '//div[contains(text(), "Post shared")]',
    ]
    
    # Close button selectors
    CLOSE_BUTTON = [
        # Common close button selectors
        'button[aria-label*="Закрыть"]',
        'button[aria-label*="Close"]',
        'svg[aria-label*="Закрыть"]',
        'svg[aria-label*="Close"]',
        '[aria-label*="Закрыть"]',
        '[aria-label*="Close"]',
        
        # X button patterns
        'button:has-text("×")',
        'button:has-text("✕")',
        'div[role="button"]:has-text("×")',
        'div[role="button"]:has-text("✕")',
        
        # XPath for close buttons
        '//button[@aria-label="Закрыть"]',
        '//button[@aria-label="Close"]',
        '//svg[@aria-label="Закрыть"]',
        '//svg[@aria-label="Close"]',
        '//button[contains(text(), "×")]',
        '//div[@role="button" and contains(text(), "×")]',
        
        # Generic close patterns
        'button[class*="close"]',
        'div[class*="close"][role="button"]',
        'button[data-testid*="close"]',
        'div[data-testid*="close"][role="button"]',
    ]
    
    # Menu indicators (for dropdown detection)
    MENU_INDICATORS = [
        'div[aria-hidden="false"]',
        'div[style*="width: 200px"]',
        'div:has(span:has-text("Публикация"))',
        'div:has(span:has-text("Post"))',
    ]
    
    # Main interface selectors (for navigation verification)
    MAIN_INTERFACE = [
        'svg[aria-label*="Главная"]',
        'svg[aria-label*="Home"]',
        'svg[aria-label*="Создать"]',
        'svg[aria-label*="Create"]',
        '[aria-label*="Главная"]',
        '[aria-label*="Home"]',
    ]
    
    # Upload indicators (to check if still on upload page)
    UPLOAD_INDICATORS = [
        'input[type="file"]',
        'div:has-text("Drag photos and videos here")',
        'div:has-text("Select from computer")',
    ]

    # Crop/Size selection selectors
    CROP_SIZE_BUTTON = [
        # Based on provided HTML structure - button with crop icon
        'div[role="button"] svg[aria-label*="Выбрать размер и обрезать"]',
        'button svg[aria-label*="Выбрать размер и обрезать"]',
        'div[role="button"] svg[aria-label*="Select crop"]',
        'button svg[aria-label*="Select crop"]',
        
        # Parent elements of the crop icon
        'div[role="button"]:has(svg[aria-label*="Выбрать размер и обрезать"])',
        'button:has(svg[aria-label*="Выбрать размер и обрезать"])',
        'div[role="button"]:has(svg[aria-label*="Select crop"])',
        'button:has(svg[aria-label*="Select crop"])',
        
        # Generic crop selectors
        '[aria-label*="Обрезка"]',
        '[aria-label*="Crop"]',
        'button:has-text("Обрезка")',
        'button:has-text("Crop")',
    ]
    
    # Original aspect ratio selectors
    ORIGINAL_ASPECT_RATIO = [
        # Based on provided HTML structure - look for "Оригинал" text
        'div[role="button"]:has-text("Оригинал")',
        'button:has-text("Оригинал")',
        'span:has-text("Оригинал")',
        
        # More specific selectors based on the HTML structure
        'div.x1i10hfl:has(span:has-text("Оригинал"))',
        'div[role="button"] span:has-text("Оригинал")',
        
        # XPath selectors for "Оригинал"
        '//div[@role="button" and contains(., "Оригинал")]',
        '//button[contains(., "Оригинал")]',
        '//span[text()="Оригинал"]',
        '//div[contains(@class, "x1i10hfl") and .//span[text()="Оригинал"]]',
        
        # English fallback for "Original"
        'div[role="button"]:has-text("Original")',
        'button:has-text("Original")',
        'span:has-text("Original")',
        'div.x1i10hfl:has(span:has-text("Original"))',
        '//div[@role="button" and contains(., "Original")]',
        '//button[contains(., "Original")]',
        '//span[text()="Original"]',
        
        # Alternative selectors
        '[aria-label*="Оригинал"]',
        '[aria-label*="Original"]',
        '[data-testid*="original"]',
        '[title*="Оригинал"]',
        '[title*="Original"]',
    ]
    
    # Fallback aspect ratio selectors
    FALLBACK_ASPECT_RATIOS = [
        # Try 9:16 as fallback
        'div[role="button"]:has-text("9:16")',
        'span:has-text("9:16")',
        '//div[@role="button" and contains(., "9:16")]',
        '//span[text()="9:16"]',
        
        # Try 1:1 as another fallback
        'div[role="button"]:has-text("1:1")',
        'span:has-text("1:1")',
        '//div[@role="button" and contains(., "1:1")]',
        '//span[text()="1:1"]',
    ]
    
    # Logged in indicators
    LOGGED_IN_INDICATORS = [
        # Russian navigation indicators (most likely for Russian Instagram)
        'svg[aria-label*="Главная"]',
        'svg[aria-label*="главная"]',
        '[aria-label*="Главная"]',
        '[aria-label*="главная"]',
        'a[aria-label*="Главная"]',
        'a[aria-label*="главная"]',
        
        # Russian Create/New post indicators
        'svg[aria-label*="Создать"]',
        'svg[aria-label*="создать"]',
        'svg[aria-label*="Новая публикация"]',
        'svg[aria-label*="новая публикация"]',
        '[aria-label*="Создать"]',
        '[aria-label*="создать"]',
        '[aria-label*="Новая публикация"]',
        '[aria-label*="новая публикация"]',
        
        # Russian Profile indicators
        'svg[aria-label*="Профиль"]',
        'svg[aria-label*="профиль"]',
        '[aria-label*="Профиль"]',
        '[aria-label*="профиль"]',
        'img[alt*="фото профиля"]',
        'img[alt*="Фото профиля"]',
        
        # Russian Search indicators
        'svg[aria-label*="Поиск"]',
        'svg[aria-label*="поиск"]',
        '[aria-label*="Поиск"]',
        '[aria-label*="поиск"]',
        'input[placeholder*="Поиск"]',
        'input[placeholder*="поиск"]',
        
        # Russian Messages/Direct indicators
        'svg[aria-label*="Сообщения"]',
        'svg[aria-label*="сообщения"]',
        'svg[aria-label*="Messenger"]',
        '[aria-label*="Сообщения"]',
        '[aria-label*="сообщения"]',
        '[aria-label*="Messenger"]',
        
        # Russian Activity indicators
        'svg[aria-label*="Действия"]',
        'svg[aria-label*="действия"]',
        'svg[aria-label*="Уведомления"]',
        'svg[aria-label*="уведомления"]',
        '[aria-label*="Действия"]',
        '[aria-label*="действия"]',
        '[aria-label*="Уведомления"]',
        '[aria-label*="уведомления"]',
        
        # English fallback indicators
        'svg[aria-label*="Home"]',
        '[aria-label*="Home"]',
        'a[href="/"]',
        '[data-testid="home-icon"]',
        
        # Profile/user menu indicators
        'svg[aria-label*="Profile"]',
        '[aria-label*="Profile"]',
        'img[alt*="profile picture"]',
        '[data-testid="user-avatar"]',
        
        # Navigation indicators
        'nav[role="navigation"]',
        '[role="navigation"]',
        
        # Create post indicators
        'svg[aria-label*="New post"]',
        '[aria-label*="New post"]',
        'a[href*="/create/"]',
        
        # Search indicators
        'svg[aria-label*="Search"]',
        '[aria-label*="Search"]',
        'input[placeholder*="Search"]',
        
        # Messages indicators
        'svg[aria-label*="Direct"]',
        '[aria-label*="Direct"]',
        'a[href*="/direct/"]',
        
        # Activity indicators
        'svg[aria-label*="Activity"]',
        '[aria-label*="Activity"]',
        
        # Instagram main navigation
        'div[role="main"]',
        'main[role="main"]',
        
        # More specific logged-in indicators
        'div[data-testid="ig-nav-bar"]',
        'nav[aria-label*="Primary navigation"]',
        'div[class*="nav"]',
        
        # User avatar/profile picture indicators
        'img[data-testid="user-avatar"]',
        'button[aria-label*="Профиль"]',
        'button[aria-label*="Profile"]',
        
        # Story creation indicators (only available when logged in)
        'button[aria-label*="Добавить в историю"]',
        'button[aria-label*="Add to story"]',
        
        # Settings/menu indicators
        'svg[aria-label*="Настройки"]',
        'svg[aria-label*="Settings"]',
        'button[aria-label*="Настройки"]',
        'button[aria-label*="Settings"]',
    ]
    
    # Login form indicators
    LOGIN_FORM_INDICATORS = [
        'input[name="username"]',
        'input[name="password"]',
        'button[type="submit"]:has-text("Log in")',
        'button:has-text("Log in")',
        'form[id*="loginForm"]',
        'div:has-text("Log in")',
        'a[href*="/accounts/login/"]',
    ]

class SelectorUtils:
    """Utility functions for working with selectors"""
    
    @staticmethod
    def is_xpath(selector):
        """Check if selector is XPath"""
        return selector.startswith('//')
    
    @staticmethod
    def format_xpath(selector):
        """Format XPath selector for Playwright"""
        return f"xpath={selector}" if SelectorUtils.is_xpath(selector) else selector
    
    @staticmethod
    def find_element_with_selectors(page, selectors, log_prefix="ELEMENT"):
        """Find element using list of selectors with logging"""
        from .bulk_tasks_playwright import log_info, log_warning
        
        for i, selector in enumerate(selectors):
            try:
                log_info(f"[{log_prefix}] 🔍 Trying selector {i+1}/{len(selectors)}: {selector[:50]}...")
                
                if SelectorUtils.is_xpath(selector):
                    element = page.query_selector(f"xpath={selector}")
                else:
                    element = page.query_selector(selector)
                
                if element and element.is_visible():
                    log_info(f"[{log_prefix}] ✅ Found element with selector: {selector}")
                    return element
                    
            except Exception as e:
                log_warning(f"[{log_prefix}] Selector failed: {str(e)}")
                continue
        
        return None 