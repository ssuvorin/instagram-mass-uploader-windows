# Instagram Selectors Configuration
# This file contains all CSS and XPath selectors used for Instagram automation

class InstagramSelectors:
    """Centralized Instagram selectors configuration - ADAPTIVE VERSION"""
    
    # Upload button selectors - SEMANTIC APPROACH
    UPLOAD_BUTTON = [
        # [TARGET] ПРИОРИТЕТ 1: Семантические атрибуты (самые устойчивые)
        'svg[aria-label="Новая публикация"]',
        'svg[aria-label*="Новая публикация"]',
        'svg[aria-label*="New post"]',
        'svg[aria-label*="Create"]',
        'svg[aria-label*="Создать"]',
        
        # [TARGET] ПРИОРИТЕТ 2: Родительские элементы с семантическими SVG
        'a:has(svg[aria-label="Новая публикация"])',
        'button:has(svg[aria-label="Новая публикация"])',
        'div[role="button"]:has(svg[aria-label="Новая публикация"])',
        'a:has(svg[aria-label*="New post"])',
        'button:has(svg[aria-label*="New post"])',
        'div[role="button"]:has(svg[aria-label*="New post"])',
        
        # [TARGET] ПРИОРИТЕТ 3: Текстовые селекторы
        'span:has-text("Создать")',
        'a:has(span:has-text("Создать"))',
        'div[role="button"]:has-text("Создать")',
        'button:has-text("Создать")',
        'span:has-text("Create")',
        'a:has(span:has-text("Create"))',
        'div[role="button"]:has-text("Create")',
        'button:has-text("Create")',
        
        # [TARGET] ПРИОРИТЕТ 4: XPath семантические
        '//svg[@aria-label="Новая публикация"]',
        '//svg[contains(@aria-label, "Новая публикация")]',
        '//svg[contains(@aria-label, "New post")]',
        '//svg[contains(@aria-label, "Create")]',
        '//svg[contains(@aria-label, "Создать")]',
        '//a[.//svg[@aria-label="Новая публикация"]]',
        '//button[.//svg[@aria-label="Новая публикация"]]',
        '//div[@role="button" and .//svg[@aria-label="Новая публикация"]]',
        
        # [TARGET] ПРИОРИТЕТ 5: XPath текстовые
        '//span[contains(text(), "Создать")]',
        '//a[.//span[contains(text(), "Создать")]]',
        '//div[@role="button" and contains(text(), "Создать")]',
        '//button[contains(text(), "Создать")]',
        '//span[contains(text(), "Create")]',
        '//a[.//span[contains(text(), "Create")]]',
        '//div[@role="button" and contains(text(), "Create")]',
        '//button[contains(text(), "Create")]',
        
        # [TARGET] ПРИОРИТЕТ 6: Универсальные aria-label
        '[aria-label*="Создать"]',
        '[aria-label*="Новая публикация"]',
        '[aria-label*="Create"]',
        '[aria-label*="New post"]',
        'button[aria-label*="Создать"]',
        'button[aria-label*="Create"]',
        'a[aria-label*="Создать"]',
        'a[aria-label*="Create"]',
    ]
    
    # Post option selectors - SEMANTIC APPROACH
    POST_OPTION = [
        # [TARGET] ПРИОРИТЕТ 1: Семантические SVG селекторы
        'svg[aria-label="Публикация"]',
        'svg[aria-label*="Публикация"]',
        'svg[aria-label*="Post"]',
        'svg[aria-label="Post"]',
        'a:has(svg[aria-label="Публикация"])',
        'div[role="menuitem"]:has(svg[aria-label="Публикация"])',
        'div[role="button"]:has(svg[aria-label="Публикация"])',
        'a:has(svg[aria-label="Post"])',
        'div[role="menuitem"]:has(svg[aria-label="Post"])',
        'div[role="button"]:has(svg[aria-label="Post"])',
        
        # [TARGET] ПРИОРИТЕТ 2: Текстовые селекторы
        'a:has(span:has-text("Публикация"))',
        'div[role="menuitem"]:has(span:has-text("Публикация"))',
        'div[role="button"]:has(span:has-text("Публикация"))',
        'span:has-text("Публикация")',
        'a:has(span:has-text("Post"))',
        'div[role="menuitem"]:has(span:has-text("Post"))',
        'div[role="button"]:has(span:has-text("Post"))',
        'span:has-text("Post")',
        
        # [TARGET] ПРИОРИТЕТ 3: XPath семантические
        '//svg[@aria-label="Публикация"]',
        '//svg[contains(@aria-label, "Публикация")]',
        '//svg[contains(@aria-label, "Post")]',
        '//svg[@aria-label="Post"]',
        '//a[.//svg[@aria-label="Публикация"]]',
        '//div[@role="menuitem" and .//svg[@aria-label="Публикация"]]',
        '//a[.//svg[@aria-label="Post"]]',
        '//div[@role="menuitem" and .//svg[@aria-label="Post"]]',
        
        # [TARGET] ПРИОРИТЕТ 4: XPath текстовые
        '//a[.//span[text()="Публикация"]]',
        '//div[@role="menuitem" and .//span[text()="Публикация"]]',
        '//span[text()="Публикация"]',
        '//a[.//span[text()="Post"]]',
        '//div[@role="menuitem" and .//span[text()="Post"]]',
        '//span[text()="Post"]',
        
        # [TARGET] ПРИОРИТЕТ 5: Универсальные
        '[aria-label*="Публикация"]',
        '[aria-label*="Post"]',
        'button[aria-label*="Публикация"]',
        'button[aria-label*="Post"]',
    ]
    
    # File input selectors - SEMANTIC APPROACH
    FILE_INPUT = [
        # [TARGET] ПРИОРИТЕТ 1: Стандартные HTML атрибуты (самые устойчивые)
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
        
        # [TARGET] ПРИОРИТЕТ 2: Семантические формы
        'form[enctype="multipart/form-data"] input[type="file"]',
        'form[method="POST"] input[type="file"]',
        'form[role="presentation"] input[type="file"]',
        
        # [TARGET] ПРИОРИТЕТ 3: Текстовые кнопки (самые надежные)
        'button:has-text("Выбрать на компьютере")',
        'div[role="button"]:has-text("Выбрать на компьютере")',
        'button:has-text("Выбрать файлы")',
        'div[role="button"]:has-text("Выбрать файлы")',
        'button:has-text("Выбрать с компьютера")',
        'div[role="button"]:has-text("Выбрать с компьютера")',
        
        # [TARGET] ПРИОРИТЕТ 4: Английские тексты
        'button:has-text("Select from computer")',
        'div[role="button"]:has-text("Select from computer")',
        'button:has-text("Select files")',
        'div[role="button"]:has-text("Select files")',
        'button:has-text("Choose files")',
        'div[role="button"]:has-text("Choose files")',
        
        # [TARGET] ПРИОРИТЕТ 5: XPath тексты
        '//button[contains(text(), "Выбрать на компьютере")]',
        '//div[@role="button" and contains(text(), "Выбрать на компьютере")]',
        '//button[contains(text(), "Выбрать файлы")]',
        '//div[@role="button" and contains(text(), "Выбрать файлы")]',
        '//button[contains(text(), "Select from computer")]',
        '//div[@role="button" and contains(text(), "Select from computer")]',
        '//button[contains(text(), "Select files")]',
        '//div[@role="button" and contains(text(), "Select files")]',
        
        # [TARGET] ПРИОРИТЕТ 6: Aria-label семантические
        'button[aria-label*="Выбрать"]',
        'button[aria-label*="Select"]',
        'button[aria-label*="Choose"]',
        '[aria-label*="Выбрать файл"]',
        '[aria-label*="Select file"]',
        '[aria-label*="Choose file"]',
        
        # [TARGET] ПРИОРИТЕТ 7: Drag and drop области
        'div:has-text("Перетащите фото и видео сюда")',
        'div:has-text("Drag photos and videos here")',
        'div[role="button"]:has-text("Перетащите")',
        'div[role="button"]:has-text("Drag")',
        
        # [TARGET] ПРИОРИТЕТ 8: Универсальные файловые input
        'input[type="file"]:not([style*="display: none"]):not([hidden])',
        'input[type="file"][style*="display: block"]',
        'input[type="file"][style*="visibility: visible"]',
        
        # [TARGET] ПРИОРИТЕТ 9: Последний resort - современные классы (ТОЛЬКО если ничего не работает)
        'input[class*="_ac69"]',  # Оставляем только как последний вариант
        'form input[class*="_ac"]',  # Широкий паттерн Instagram
    ]
    
    # OK button selectors
    OK_BUTTON = [
        'button:has-text("OK")',
        'button:has-text("ОК")',
        'button[aria-label*="OK"]',
        'button[aria-label*="ОК"]',
        '//button[contains(text(), "OK")]',
        '//button[contains(text(), "ОК")]',
    ]
    
    # Next button selectors - SEMANTIC APPROACH
    NEXT_BUTTON = [
        # [TARGET] ПРИОРИТЕТ 1: Текстовые селекторы (самые надежные)
        'button:has-text("Далее")',
        'button:has-text("Next")',
        'button:has-text("Продолжить")',
        'button:has-text("Continue")',
        'div[role="button"]:has-text("Далее")',
        'div[role="button"]:has-text("Next")',
        'div[role="button"]:has-text("Продолжить")',
        'div[role="button"]:has-text("Continue")',
        
        # [TARGET] ПРИОРИТЕТ 2: XPath текстовые
        '//button[contains(text(), "Далее")]',
        '//button[contains(text(), "Next")]',
        '//button[contains(text(), "Продолжить")]',
        '//button[contains(text(), "Continue")]',
        '//div[@role="button" and contains(text(), "Далее")]',
        '//div[@role="button" and contains(text(), "Next")]',
        
        # [TARGET] ПРИОРИТЕТ 3: Aria-label
        'button[aria-label*="Далее"]',
        'button[aria-label*="Next"]',
        'button[aria-label*="Продолжить"]',
        'button[aria-label*="Continue"]',
        '[role="button"][aria-label*="Далее"]',
        '[role="button"][aria-label*="Next"]',
        
        # [TARGET] ПРИОРИТЕТ 4: Универсальные роли
        '[role="button"]:has-text("Далее")',
        '[role="button"][tabindex="0"]:has-text("Далее")',
        '[role="button"]:has-text("Next")',
        '[role="button"][tabindex="0"]:has-text("Next")',
    ]
    
    # Share button selectors - SEMANTIC APPROACH
    SHARE_BUTTON = [
        # [TARGET] ПРИОРИТЕТ 1: Текстовые селекторы
        'button:has-text("Поделиться")',
        'button:has-text("Share")',
        'button:has-text("Опубликовать")',
        'button:has-text("Post")',
        'button:has-text("Publish")',
        'div[role="button"]:has-text("Поделиться")',
        'div[role="button"]:has-text("Share")',
        'div[role="button"]:has-text("Опубликовать")',
        'div[role="button"]:has-text("Post")',
        
        # [TARGET] ПРИОРИТЕТ 2: XPath текстовые
        '//button[contains(text(), "Поделиться")]',
        '//button[contains(text(), "Share")]',
        '//button[contains(text(), "Опубликовать")]',
        '//button[contains(text(), "Post")]',
        '//div[@role="button" and contains(text(), "Поделиться")]',
        '//div[@role="button" and contains(text(), "Share")]',
        
        # [TARGET] ПРИОРИТЕТ 3: Aria-label
        'button[aria-label*="Поделиться"]',
        'button[aria-label*="Share"]',
        'button[aria-label*="Опубликовать"]',
        'button[aria-label*="Post"]',
        '[role="button"][aria-label*="Поделиться"]',
        '[role="button"][aria-label*="Share"]',
    ]
    
    # Caption textarea selectors - SEMANTIC APPROACH
    CAPTION_TEXTAREA = [
        # [TARGET] ПРИОРИТЕТ 1: Семантические aria-label
        'textarea[aria-label*="Напишите подпись"]',
        'textarea[aria-label*="Write a caption"]',
        'textarea[aria-label*="подпись"]',
        'textarea[aria-label*="caption"]',
        
        # [TARGET] ПРИОРИТЕТ 2: Placeholder атрибуты
        'textarea[placeholder*="Напишите подпись"]',
        'textarea[placeholder*="Write a caption"]',
        'textarea[placeholder*="подпись"]',
        'textarea[placeholder*="caption"]',
        
        # [TARGET] ПРИОРИТЕТ 3: Contenteditable div
        'div[contenteditable="true"][aria-label*="подпись"]',
        'div[contenteditable="true"][aria-label*="caption"]',
        'div[contenteditable="true"][placeholder*="подпись"]',
        'div[contenteditable="true"][placeholder*="caption"]',
        
        # [TARGET] ПРИОРИТЕТ 4: XPath
        '//textarea[contains(@aria-label, "подпись")]',
        '//textarea[contains(@aria-label, "caption")]',
        '//div[@contenteditable="true" and contains(@aria-label, "подпись")]',
        '//div[@contenteditable="true" and contains(@aria-label, "caption")]',
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

    # Crop/Size selection selectors - FULLY ADAPTIVE VERSION (независимо от CSS-классов)
    CROP_SIZE_BUTTON = [
        # [TARGET] ПРИОРИТЕТ 1: Семантические селекторы (самые устойчивые)
        'svg[aria-label="Выбрать размер и обрезать"]',
        'svg[aria-label*="Выбрать размер"]',
        'svg[aria-label*="обрезать"]',
        'svg[aria-label*="размер"]',
        'svg[aria-label*="Select crop"]',
        'svg[aria-label*="Crop"]',
        'svg[aria-label*="Select size"]',
        
        # [TARGET] ПРИОРИТЕТ 2: Родительские элементы SVG (работают всегда)
        'button:has(svg[aria-label="Выбрать размер и обрезать"])',
        'div[role="button"]:has(svg[aria-label="Выбрать размер и обрезать"])',
        'button:has(svg[aria-label*="Выбрать размер"])',
        'div[role="button"]:has(svg[aria-label*="Выбрать размер"])',
        'button:has(svg[aria-label*="обрезать"])',
        'div[role="button"]:has(svg[aria-label*="обрезать"])',
        'button:has(svg[aria-label*="Select crop"])',
        'button:has(svg[aria-label*="Crop"])',
        'div[role="button"]:has(svg[aria-label*="Select crop"])',
        'div[role="button"]:has(svg[aria-label*="Crop"])',
        
        # [TARGET] ПРИОРИТЕТ 3: Универсальные aria-label (без привязки к SVG)
        '[aria-label*="Выбрать размер и обрезать"]',
        '[aria-label*="Выбрать размер"]',
        '[aria-label*="обрезать"]',
        '[aria-label*="Select crop"]',
        '[aria-label*="Crop"]',
        'button[aria-label*="Выбрать размер"]',
        'button[aria-label*="обрезать"]',
        'button[aria-label*="Select crop"]',
        'button[aria-label*="Crop"]',
        
        # [TARGET] ПРИОРИТЕТ 4: XPath семантические (очень устойчивые)
        '//svg[@aria-label="Выбрать размер и обрезать"]',
        '//svg[contains(@aria-label, "Выбрать размер")]',
        '//svg[contains(@aria-label, "обрезать")]',
        '//svg[contains(@aria-label, "размер")]',
        '//button[.//svg[contains(@aria-label, "Выбрать размер")]]',
        '//div[@role="button" and .//svg[contains(@aria-label, "Выбрать размер")]]',
        '//button[.//svg[contains(@aria-label, "обрезать")]]',
        '//div[@role="button" and .//svg[contains(@aria-label, "обрезать")]]',
        '//svg[contains(@aria-label, "Select crop")]',
        '//svg[contains(@aria-label, "Crop")]',
        '//button[.//svg[contains(@aria-label, "Select crop")]]',
        '//button[.//svg[contains(@aria-label, "Crop")]]',
        '//div[@role="button" and .//svg[contains(@aria-label, "Select crop")]]',
        '//div[@role="button" and .//svg[contains(@aria-label, "Crop")]]',
        
        # [TARGET] ПРИОРИТЕТ 5: Текстовые селекторы (fallback)
        'button:has-text("Обрезка")',
        'button:has-text("Crop")',
        'div[role="button"]:has-text("Обрезка")',
        'div[role="button"]:has-text("Crop")',
        
        # [TARGET] ПРИОРИТЕТ 6: Универсальные паттерны
        'button[type="button"]:has(svg[aria-label*="размер"])',
        'button[type="button"]:has(svg[aria-label*="crop"])',
        'div[role="button"]:has(button:has(svg[aria-label*="размер"]))',
        'div[role="button"]:has(button:has(svg[aria-label*="crop"]))',
        
        # [TARGET] ПРИОРИТЕТ 7: Широкие селекторы (если ничего не работает)
        'button:has(svg)',  # Любая кнопка с SVG
        'div[role="button"]:has(svg)',  # Любой div-кнопка с SVG
    ]
    
    # Original aspect ratio selectors - FULLY ADAPTIVE VERSION
    ORIGINAL_ASPECT_RATIO = [
        # [TARGET] ПРИОРИТЕТ 1: Семантические текстовые селекторы (самые надежные)
        'span:has-text("Оригинал")',
        'span:has-text("Original")',
        'div[role="button"]:has(span:has-text("Оригинал"))',
        'button:has(span:has-text("Оригинал"))',
        'div[role="button"]:has(span:has-text("Original"))',
        'button:has(span:has-text("Original"))',
        
        # [TARGET] ПРИОРИТЕТ 2: Прямые текстовые селекторы
        'div[role="button"]:has-text("Оригинал")',
        'button:has-text("Оригинал")',
        'div[role="button"]:has-text("Original")',
        'button:has-text("Original")',
        
        # [TARGET] ПРИОРИТЕТ 3: SVG с семантическими атрибутами
        'svg[aria-label="Значок контура фото"]',
        'svg[aria-label*="контур"]',
        'svg[aria-label*="фото"]',
        'svg[aria-label*="photo"]',
        'svg[aria-label*="outline"]',
        'div[role="button"]:has(svg[aria-label="Значок контура фото"])',
        'button:has(svg[aria-label="Значок контура фото"])',
        
        # [TARGET] ПРИОРИТЕТ 4: XPath семантические (самые точные)
        '//span[text()="Оригинал"]',
        '//span[text()="Original"]',
        '//div[@role="button" and .//span[text()="Оригинал"]]',
        '//button[.//span[text()="Оригинал"]]',
        '//div[@role="button" and .//span[text()="Original"]]',
        '//button[.//span[text()="Original"]]',
        '//div[@role="button" and contains(., "Оригинал")]',
        '//button[contains(., "Оригинал")]',
        '//div[@role="button" and contains(., "Original")]',
        '//button[contains(., "Original")]',
        
        # [TARGET] ПРИОРИТЕТ 5: SVG XPath
        '//svg[@aria-label="Значок контура фото"]',
        '//svg[contains(@aria-label, "контур")]',
        '//svg[contains(@aria-label, "фото")]',
        '//svg[contains(@aria-label, "photo")]',
        '//svg[contains(@aria-label, "outline")]',
        '//button[.//svg[@aria-label="Значок контура фото"]]',
        '//div[@role="button" and .//svg[@aria-label="Значок контура фото"]]',
        
        # [TARGET] ПРИОРИТЕТ 6: Универсальные aria-label
        '[aria-label*="Оригинал"]',
        '[aria-label*="Original"]',
        'button[aria-label*="Оригинал"]',
        'button[aria-label*="Original"]',
        '[title*="Оригинал"]',
        '[title*="Original"]',
        
        # [TARGET] ПРИОРИТЕТ 7: Позиционные селекторы (обычно "Оригинал" первый)
        '(//div[@role="button" and @tabindex="0"])[1]',
        '(//button[@tabindex="0"])[1]',
        'div[role="button"][tabindex="0"]:first-child',
        'button[tabindex="0"]:first-child',
    ]
    
    # Fallback aspect ratio selectors - SEMANTIC VERSION
    FALLBACK_ASPECT_RATIOS = [
        # Семантические селекторы для соотношений сторон
        'div[role="button"]:has-text("9:16")',
        'span:has-text("9:16")',
        'button:has-text("9:16")',
        'div[role="button"]:has-text("1:1")',
        'span:has-text("1:1")',
        'button:has-text("1:1")',
        'div[role="button"]:has-text("4:5")',
        'span:has-text("4:5")',
        'button:has-text("4:5")',
        
        # XPath для соотношений
        '//div[@role="button" and contains(., "9:16")]',
        '//span[text()="9:16"]',
        '//button[contains(., "9:16")]',
        '//div[@role="button" and contains(., "1:1")]',
        '//span[text()="1:1"]',
        '//button[contains(., "1:1")]',
        
        # Универсальные селекторы для любой опции
        'div[role="button"][tabindex="0"]',
        'button[tabindex="0"]',
        '[role="button"][tabindex="0"]',
    ]
    
    # Logged in indicators - ИСПРАВЛЕННЫЕ СЕЛЕКТОРЫ
    LOGGED_IN_INDICATORS = [
        # Russian navigation indicators (most likely for Russian Instagram)
        'svg[aria-label*="Главная"]',
        'svg[aria-label*="главная"]',
        '[aria-label*="Главная"]',
        '[aria-label*="главная"]',
        'a[aria-label*="Главная"]',
        'a[aria-label*="главная"]',
        
        # Russian Create/New post indicators - БОЛЕЕ СПЕЦИФИЧНЫЕ
        'svg[aria-label="Создать"]:not([aria-label*="новый аккаунт"]):not([aria-label*="аккаунт"])',
        'svg[aria-label*="Создать"]:not([aria-label*="новый аккаунт"]):not([aria-label*="аккаунт"])',
        'svg[aria-label*="Новая публикация"]',
        'svg[aria-label*="новая публикация"]',
        'a[aria-label="Создать"]:not([aria-label*="новый аккаунт"]):not([aria-label*="аккаунт"])',
        'a[aria-label*="Создать"]:not([aria-label*="новый аккаунт"]):not([aria-label*="аккаунт"])',
        'a[aria-label*="Новая публикация"]',
        'a[aria-label*="новая публикация"]',
        
        # Более точные селекторы для создания поста
        'nav svg[aria-label*="Создать"]',  # Только в навигации
        'header svg[aria-label*="Создать"]',  # Только в хедере
        '[role="navigation"] svg[aria-label*="Создать"]',  # Только в навигации
        
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
        
        # Navigation indicators - БОЛЕЕ СПЕЦИФИЧНЫЕ
        'nav[role="navigation"]',
        '[role="navigation"]:not(:has(button:has-text("Войти"))):not(:has(button:has-text("Log in")))',
        
        # Create post indicators - ТОЛЬКО ДЛЯ АВТОРИЗОВАННЫХ
        'svg[aria-label="New post"]:not([aria-label*="account"])',
        'svg[aria-label*="New post"]:not([aria-label*="account"])',
        'nav svg[aria-label*="New post"]',
        'header svg[aria-label*="New post"]',
        'a[href*="/create/"]:not(:has-text("account"))',
        
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
        
        # Instagram main navigation - ИСКЛЮЧАЕМ СТРАНИЦЫ ЛОГИНА
        'div[role="main"]:not(:has(form)):not(:has(input[name="password"]))',
        'main[role="main"]:not(:has(form)):not(:has(input[name="password"]))',
        
        # More specific logged-in indicators
        'div[data-testid="ig-nav-bar"]',
        'nav[aria-label*="Primary navigation"]',
        'div[class*="nav"]:not(:has(input[name="password"]))',
        
        # User avatar/profile picture indicators
        'img[data-testid="user-avatar"]',
        'button[aria-label*="Профиль"]:not(:has-text("новый"))',
        'button[aria-label*="Profile"]:not(:has-text("new"))',
        
        # Story creation indicators (only available when logged in)
        'button[aria-label*="Добавить в историю"]',
        'button[aria-label*="Add to story"]',
        
        # Settings/menu indicators
        'svg[aria-label*="Настройки"]',
        'svg[aria-label*="Settings"]',
        'button[aria-label*="Настройки"]',
        'button[aria-label*="Settings"]',
        
        # ДОПОЛНИТЕЛЬНЫЕ СИЛЬНЫЕ ИНДИКАТОРЫ АВТОРИЗАЦИИ
        'svg[aria-label*="Reels"]',
        'svg[aria-label*="Stories"]',
        'svg[aria-label*="Истории"]',
        'svg[aria-label*="Лента"]',
        'svg[aria-label*="Feed"]',
        'a[href="/explore/"]',
        'svg[aria-label*="Интересное"]',
        'svg[aria-label*="Explore"]',
        
        # Пользовательские элементы (есть только когда авторизован)
        'img[alt*="profile"]:not(:has-text("new"))',
        'button:has(img[alt*="profile"])',
        'div:has(img[alt*="Фото профиля"])',
    ]
    
    # Login form indicators - ОБНОВЛЕННЫЕ СЕЛЕКТОРЫ
    LOGIN_FORM_INDICATORS = [
        # АКТУАЛЬНЫЕ селекторы полей Instagram
        'input[name="email"]',                # Текущее поле username Instagram
        'input[name="pass"]',                 # Текущее поле password Instagram
        'input[name="username"]',             # Старое поле username
        'input[name="password"]',             # Старое поле password
        
        # Кнопки входа
        'button[type="submit"]:has-text("Log in")',
        'button:has-text("Log in")',
        'button:has-text("Войти")',
        'div[role="button"]:has-text("Log in")',
        'div[role="button"]:has-text("Войти")',
        
        # Формы логина
        'form[id*="loginForm"]',
        'form[id*="login_form"]',
        'form:has(input[name="email"])',
        'form:has(input[name="pass"])',
        'form:has(input[name="username"])',
        'form:has(input[name="password"])',
        
        # Специфичные элементы страницы логина
        'div:has-text("Log in")',
        'div:has-text("Войти в Instagram")',
        'span:has-text("Войти в Instagram")',
        'a[href*="/accounts/login/"]',
        'a:has-text("Забыли пароль?")',
        'a:has-text("Forgot password?")',
        'a:has-text("Создать новый аккаунт")',
        'a:has-text("Create new account")',
        
        # Контейнеры страницы логина
        'div:has(input[name="email"]):has(input[name="pass"])',
        'div:has(input[name="username"]):has(input[name="password"])',
        'section:has(input[type="password"])',
        'main:has(form:has(input[type="password"]))',
    ]

    # Cookie consent modal selectors - RUSSIAN + ENGLISH SUPPORT
    COOKIE_CONSENT_BUTTONS = [
        # [TARGET] ПРИОРИТЕТ 1: Русские селекторы для кнопки "Разрешить все cookie"
        'button:has-text("Разрешить все cookie")',
        'button:has-text("Разрешить все файлы cookie")', 
        'button[class*="_asz1"]:has-text("Разрешить")',
        'button[class*="_a9--"]:has-text("Разрешить")',
        'button[tabindex="0"]:has-text("Разрешить все")',
        'button[tabindex="0"]:has-text("Разрешить")',
        
        # [TARGET] ПРИОРИТЕТ 2: Английские селекторы
        'button:has-text("Allow all cookies")',
        'button:has-text("Accept all cookies")',
        'button[class*="_asz1"]:has-text("Allow")',
        'button[class*="_a9--"]:has-text("Allow")',
        'button[tabindex="0"]:has-text("Allow all")',
        'button[tabindex="0"]:has-text("Accept")',
        
        # [TARGET] ПРИОРИТЕТ 3: XPath селекторы для русского текста
        '//button[contains(text(), "Разрешить все cookie")]',
        '//button[contains(text(), "Разрешить все файлы cookie")]',
        '//button[contains(@class, "_asz1") and contains(text(), "Разрешить")]',
        '//button[contains(@class, "_a9--") and contains(text(), "Разрешить")]',
        '//button[@tabindex="0" and contains(text(), "Разрешить все")]',
        '//button[@tabindex="0" and contains(text(), "Разрешить")]',
        
        # [TARGET] ПРИОРИТЕТ 4: XPath селекторы для английского текста
        '//button[contains(text(), "Allow all cookies")]',
        '//button[contains(text(), "Accept all cookies")]',
        '//button[contains(@class, "_asz1") and contains(text(), "Allow")]',
        '//button[contains(@class, "_a9--") and contains(text(), "Allow")]',
        '//button[@tabindex="0" and contains(text(), "Allow all")]',
        '//button[@tabindex="0" and contains(text(), "Accept")]',
        
        # [TARGET] ПРИОРИТЕТ 5: Универсальные CSS классы Instagram
        'button[class*="_asz1"]',  # Основной класс кнопки cookies
        'button[class*="_a9--"][class*="_asz1"]',  # Комбинированные классы
        '[class*="_a9--"][class*="_asz1"]',  # Любой элемент с этими классами
        
        # [TARGET] ПРИОРИТЕТ 6: Текст в div с role="button"
        'div[role="button"]:has-text("Разрешить все cookie")',
        'div[role="button"]:has-text("Allow all cookies")',
        'div[tabindex="0"]:has-text("Разрешить все cookie")',
        'div[tabindex="0"]:has-text("Allow all cookies")',
        
        # [TARGET] ПРИОРИТЕТ 7: XPath для div кнопок
        '//div[@role="button" and contains(text(), "Разрешить все cookie")]',
        '//div[@role="button" and contains(text(), "Allow all cookies")]',
        '//div[@tabindex="0" and contains(text(), "Разрешить все cookie")]',
        '//div[@tabindex="0" and contains(text(), "Allow all cookies")]',
        
        # [TARGET] ПРИОРИТЕТ 8: Широкие селекторы (fallback)
        'button:has-text("Разрешить")',
        'button:has-text("Allow")',
        'div[role="button"]:has-text("Разрешить")',
        'div[role="button"]:has-text("Allow")',
        '[tabindex="0"]:has-text("Разрешить")',
        '[tabindex="0"]:has-text("Allow")',
        
        # [TARGET] ПРИОРИТЕТ 9: Универсальные XPath (последний резерв)
        '//button[contains(text(), "Разрешить")]',
        '//button[contains(text(), "Allow")]',
        '//div[@role="button" and contains(text(), "Разрешить")]',
        '//div[@role="button" and contains(text(), "Allow")]',
        '//*[@tabindex="0" and contains(text(), "Разрешить")]',
        '//*[@tabindex="0" and contains(text(), "Allow")]',
    ]
    
    # Alternative cookie consent selectors (for "Отклонить" / "Decline" buttons)
    COOKIE_DECLINE_BUTTONS = [
        # Русские селекторы для кнопки "Отклонить"
        'button:has-text("Отклонить необязательные файлы cookie")',
        'button:has-text("Отклонить необязательные")',
        'button:has-text("Отклонить")',
        'button[class*="_a9_1"]:has-text("Отклонить")',
        
        # Английские селекторы для кнопки "Decline"
        'button:has-text("Decline optional cookies")',
        'button:has-text("Decline optional")',
        'button:has-text("Decline")',
        'button[class*="_a9_1"]:has-text("Decline")',
        
        # XPath селекторы
        '//button[contains(text(), "Отклонить необязательные файлы cookie")]',
        '//button[contains(text(), "Отклонить необязательные")]',
        '//button[contains(text(), "Отклонить")]',
        '//button[contains(text(), "Decline optional cookies")]',
        '//button[contains(text(), "Decline optional")]',
        '//button[contains(text(), "Decline")]',
        
        # CSS класс для decline кнопки
        'button[class*="_a9_1"]',
        'div[role="button"][class*="_a9_1"]',
    ]
    
    # Cookie modal indicators (to detect if modal is open)
    COOKIE_MODAL_INDICATORS = [
        # Заголовок модального окна
        'h2:has-text("Разрешить использование файлов cookie")',
        'h2:has-text("Allow the use of cookies")',
        'h1:has-text("Разрешить использование файлов cookie")',
        'h1:has-text("Allow the use of cookies")',
        
        # Текст в модальном окне
        'div:has-text("Мы используем файлы cookie")',
        'div:has-text("We use cookies")',
        'span:has-text("файлы cookie")',
        'span:has-text("cookies")',
        
        # Контейнеры модального окна
        'div[class*="xs83m0k"]',  # Основной контейнер модала cookies
        'div[class*="x7r02ix"]',  # Внутренний контейнер
        'div[class*="_abdc"]',    # Контейнер с контентом
        
        # XPath для заголовков
        '//h2[contains(text(), "Разрешить использование файлов cookie")]',
        '//h2[contains(text(), "Allow the use of cookies")]',
        '//h1[contains(text(), "Разрешить использование файлов cookie")]',
        '//h1[contains(text(), "Allow the use of cookies")]',
        
        # XPath для текста
        '//div[contains(text(), "Мы используем файлы cookie")]',
        '//div[contains(text(), "We use cookies")]',
        '//*[contains(text(), "файлы cookie")]',
        '//*[contains(text(), "cookies")]',
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
                log_info(f"[{log_prefix}] [SEARCH] Trying selector {i+1}/{len(selectors)}: {selector[:50]}...")
                
                if SelectorUtils.is_xpath(selector):
                    element = page.query_selector(f"xpath={selector}")
                else:
                    element = page.query_selector(selector)
                
                if element and element.is_visible():
                    log_info(f"[{log_prefix}] [OK] Found element with selector: {selector}")
                    return element
                    
            except Exception as e:
                log_warning(f"[{log_prefix}] Selector failed: {str(e)}")
                continue
        
        return None 