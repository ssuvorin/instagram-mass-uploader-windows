# -*- coding: utf-8 -*-
"""
Константы для Instagram uploader
"""

# Временные интервалы (в секундах)
class TimeConstants:
    # Задержки между действиями
    HUMAN_DELAY_MIN = 0.5
    HUMAN_DELAY_MAX = 2.0
    
    # Задержки между аккаунтами
    ACCOUNT_DELAY_MIN = 30
    ACCOUNT_DELAY_MAX = 120
    
    # Задержки между видео
    VIDEO_DELAY_MIN = 180  # 3 минуты
    VIDEO_DELAY_MAX = 420  # 7 минут
    
    # Таймауты
    PAGE_LOAD_TIMEOUT = 30000  # 30 сек
    ELEMENT_TIMEOUT = 10000    # 10 сек
    BROWSER_TIMEOUT = 300      # 5 минут
    
    # Капча
    CAPTCHA_SOLVE_TIMEOUT = 180  # 3 минуты
    CAPTCHA_RETRY_DELAY = 5      # 5 сек между попытками

# Тексты для поиска
class InstagramTexts:
    # Верификация
    VERIFICATION_KEYWORDS = [
        'подтвердите, что это вы',
        'подтвердите что это вы',
        'подтвердите, что вы человек',
        'confirm that you are human',
        'prove you are human',
        'целостности аккаунта',
        'account integrity'
    ]
    
    # Успешная загрузка
    SUCCESS_KEYWORDS = [
        'Ваша публикация опубликована',
        'Публикация опубликована',
        'Опубликовано',
        'Your post has been shared',
        'Post shared',
        'Posted'
    ]
    
    # Ошибки
    ERROR_KEYWORDS = [
        'Ошибка',
        'Не удалось',
        'Попробуйте еще раз',
        'Error',
        'Failed',
        'Try again',
        'Something went wrong'
    ]
    
    # Email верификация
    EMAIL_VERIFICATION_KEYWORDS = [
        'email', 'sent you', 'check your email', 'confirmation code', 
        'we sent', 'email address', 'код отправлен', 'проверьте почту',
        'verify', 'verification', 'confirm', 'подтверждение', 'верификация',
        'enter your email', 'provide email', 'email required',
        'проверьте свою почту', 'введите код', 'отправили код', 'код подтверждения',
        'электронный адрес', 'на электронный адрес', 'мы отправили'
    ]
    
    # Код входа
    CODE_ENTRY_KEYWORDS = [
        'enter the code', 'введите код', 'confirmation code', 'код подтверждения',
        'security code', 'verification code', 'we sent you', 'мы отправили'
    ]
    
    # Сохранение данных входа
    SAVE_LOGIN_KEYWORDS = [
        'сохранить данные для входа', 'save login info', 'save your login info',
        'сохранить данные', 'save info', 'remember login', 'запомнить вход',
        'сохранить информацию', 'save information'
    ]
    
    # Ключевые слова для верификационной страницы
    VERIFICATION_PAGE_KEYWORDS = [
        'verification', 'verify', 'confirm', 'security code', 'confirmation code',
        'верификация', 'подтверждение', 'код', 'проверьте почту', 'код отправлен',
        'enter the code', 'check your email', 'we sent', 'sent you'
    ]

# Verbose логи для фильтрации
class VerboseFilters:
    PLAYWRIGHT_VERBOSE_KEYWORDS = [
        'attempting click action',
        'retrying click action',
        'waiting for element to be visible',
        'scrolling into view',
        'done scrolling',
        'subtree intercepts pointer events',
        'element is visible, enabled and stable',
        'waiting 20ms',
        'waiting 100ms',
        'waiting 500ms',
        'Element is not attached to the DOM',
        'locator.click',
        'locator.fill',
        'locator.type',
        'page.goto',
        'page.wait_for_selector',
        'browser.new_page',
        'context.new_page',
        'retrying click action, attempt',
        'waiting for element to be visible, enabled and stable',
        'element is visible, enabled and stable',
        'scrolling into view if needed',
        'done scrolling',
        'from <div',
        'subtree intercepts pointer events',
        'waiting 20ms',
        'waiting 100ms',
        'waiting 500ms',
        'retrying click action, attempt #',
        'click action',
        'element intercepts pointer events'
    ]

# Настройки браузера
class BrowserConfig:
    # Аргументы для запуска
    CHROME_ARGS = [
        '--disable-logging',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-gpu',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        '--disable-features=TranslateUI',
        '--disable-ipc-flooding-protection',
        '--log-level=3',
        '--silent',
        '--quiet'
    ]
    
    # Переменные окружения
    ENV_VARS = {
        'PLAYWRIGHT_BROWSERS_PATH': '0',
        'DEBUG': '',
        'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD': '1',
        'PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS': '1',
        'PLAYWRIGHT_DISABLE_COLORS': '1',
        'PLAYWRIGHT_QUIET': '1',
        'CHROME_LOG_FILE': '/dev/null',
        'CHROME_HEADLESS': '1'
    }

# Ограничения
class Limits:
    MAX_VIDEOS_PER_ACCOUNT = 50
    MAX_RETRY_ATTEMPTS = 3
    MAX_CAPTCHA_ATTEMPTS = 3
    MAX_LOG_ENTRIES = 1000
    MAX_TEMP_FILES = 100

# Статусы
class TaskStatus:
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    PARTIALLY_COMPLETED = 'PARTIALLY_COMPLETED'
    PHONE_VERIFICATION_REQUIRED = 'PHONE_VERIFICATION_REQUIRED'
    HUMAN_VERIFICATION_REQUIRED = 'HUMAN_VERIFICATION_REQUIRED'

# Логирование
class LogCategories:
    TASK_START = 'TASK_START'
    TASK_INFO = 'TASK_INFO'
    DOLPHIN = 'DOLPHIN'
    LOGIN = 'LOGIN'
    UPLOAD = 'UPLOAD'
    CAPTCHA = 'CAPTCHA'
    VERIFICATION = 'VERIFICATION'
    NAVIGATION = 'NAVIGATION'
    HUMAN = 'HUMAN'
    CLEANUP = 'CLEANUP'
    DATABASE = 'DATABASE'
    GENERAL = 'GENERAL'

# Пути файлов
class FilePaths:
    SCREENSHOTS_DIR = 'screenshots'
    TEMP_DIR = 'temp'
    LOGS_DIR = 'logs'

# Селекторы для элементов Instagram
class InstagramSelectors:
    # Локация
    LOCATION_FIELDS = [
        'input[name="creation-location-input"]',
        'input[placeholder="Добавить место"]',
        'input[placeholder*="Добавить местоположение"]',
        'input[placeholder*="добавить местоположение"]',
        'input[placeholder*="Добавить место"]',
        'input[placeholder*="добавить место"]',
        'input[aria-label*="Добавить местоположение"]',
        'input[aria-label*="добавить местоположение"]',
        'input[aria-label*="Добавить место"]',
        'input[aria-label*="добавить место"]',
        'input[aria-label*="Местоположение"]',
        'input[aria-label*="местоположение"]',
        '//input[contains(@placeholder, "Добавить место")]',
        '//input[contains(@placeholder, "добавить место")]',
        '//input[contains(@placeholder, "Добавить местоположение")]',
        '//input[contains(@placeholder, "добавить местоположение")]',
        '//input[contains(@aria-label, "Добавить местоположение")]',
        '//input[contains(@aria-label, "местоположение")]',
        '//input[@name="creation-location-input"]',
        'input[placeholder*="Add location"]',
        'input[placeholder*="add location"]',
        'input[placeholder*="Add place"]',
        'input[placeholder*="add place"]',
        'input[aria-label*="Add location"]',
        'input[aria-label*="Location"]',
        'input[aria-label*="location"]',
        'input[aria-label*="Add place"]',
        'input[aria-label*="Place"]',
        'input[aria-label*="place"]',
        '//input[contains(@placeholder, "Add location")]',
        '//input[contains(@placeholder, "Add place")]',
        '//input[contains(@aria-label, "Add location")]',
        '//input[contains(@aria-label, "location")]',
        '//input[contains(@aria-label, "Add place")]',
        '//input[contains(@aria-label, "place")]'
    ]
    
    # Локация - предложения
    LOCATION_SUGGESTIONS = [
        'div[role="button"]:first-child',
        'li[role="button"]:first-child',
        'div[data-testid*="location"]:first-child',
        'div[class*="location"]:first-child',
        '//div[@role="button"][1]',
        '//li[@role="button"][1]'
    ]
    
    # Упоминания/соавторы
    MENTION_FIELDS = [
        'input[name="creation-collaborator-input"]',
        'input[placeholder="Добавить соавторов"]',
        'input[placeholder*="Добавить соавторов"]',
        'input[placeholder*="добавить соавторов"]',
        'input[aria-label*="Добавить соавторов"]',
        'input[aria-label*="добавить соавторов"]',
        'input[aria-label*="Соавторы"]',
        'input[aria-label*="соавторы"]',
        'input[placeholder*="Отметить людей"]',
        'input[placeholder*="отметить людей"]',
        'input[aria-label*="Отметить людей"]',
        'input[aria-label*="отметить людей"]',
        'input[aria-label*="Отметить"]',
        'input[aria-label*="отметить"]',
        '//input[contains(@placeholder, "Добавить соавторов")]',
        '//input[contains(@placeholder, "добавить соавторов")]',
        '//input[contains(@aria-label, "Добавить соавторов")]',
        '//input[contains(@aria-label, "соавторы")]',
        '//input[contains(@placeholder, "Отметить людей")]',
        '//input[contains(@placeholder, "отметить людей")]',
        '//input[contains(@aria-label, "Отметить людей")]',
        '//input[contains(@aria-label, "отметить")]',
        '//input[@name="creation-collaborator-input"]',
        'input[placeholder*="Add collaborators"]',
        'input[placeholder*="add collaborators"]',
        'input[aria-label*="Add collaborators"]',
        'input[aria-label*="Collaborators"]',
        'input[aria-label*="collaborators"]',
        'input[placeholder*="Tag people"]',
        'input[placeholder*="tag people"]',
        'input[aria-label*="Tag people"]',
        'input[aria-label*="Tag"]',
        'input[aria-label*="tag"]',
        '//input[contains(@placeholder, "Add collaborators")]',
        '//input[contains(@placeholder, "Tag people")]',
        '//input[contains(@aria-label, "Add collaborators")]',
        '//input[contains(@aria-label, "collaborators")]',
        '//input[contains(@aria-label, "Tag people")]',
        '//input[contains(@aria-label, "tag")]'
    ]
    
    # Упоминания - предложения
    MENTION_SUGGESTIONS = [
        'div[role="button"]:first-child',
        'li[role="button"]:first-child',
        'div[data-testid*="mention"]:first-child',
        'div[class*="mention"]:first-child',
        '//div[@role="button"][1]',
        '//li[@role="button"][1]'
    ]
    
    # Кнопка "Готово" для упоминаний
    DONE_BUTTONS = [
        'button:has-text("Готово")',
        'div[role="button"]:has-text("Готово")',
        '[aria-label*="Готово"]',
        '//button[contains(text(), "Готово")]',
        '//div[@role="button" and contains(text(), "Готово")]',
        'button:has-text("Done")',
        'div[role="button"]:has-text("Done")',
        '[aria-label*="Done"]',
        '//button[contains(text(), "Done")]',
        '//div[@role="button" and contains(text(), "Done")]',
        'button:has-text("OK")',
        'button:has-text("ОК")',
        '[aria-label*="OK"]',
        '[aria-label*="ОК"]'
    ]
    
    # Кнопка "Далее"
    NEXT_BUTTONS = [
        'div[role="button"]:has-text("Далее")',
        'div.x1i10hfl:has-text("Далее")',
        'div.xjqpnuy:has-text("Далее")',
        'div[class*="x1i10hfl"][class*="xjqpnuy"]:has-text("Далее")',
        'div[class*="x1i10hfl"][class*="xa49m3k"]:has-text("Далее")',
        'div[class*="x1i10hfl"][role="button"]:has-text("Далее")',
        '//div[@role="button" and contains(text(), "Далее")]',
        '//div[contains(@class, "x1i10hfl") and contains(text(), "Далее")]',
        '//div[contains(@class, "xjqpnuy") and contains(text(), "Далее")]',
        '//div[contains(@class, "x1i10hfl") and contains(@class, "xjqpnuy") and contains(text(), "Далее")]',
        '[role="button"]:has-text("Далее")',
        '[role="button"][tabindex="0"]:has-text("Далее")',
        'button:has-text("Далее")',
        'div[role="button"]:has-text("Далее")',
        '[aria-label*="Далее"]',
        'button:contains("Далее")',
        '//button[contains(text(), "Далее")]',
        '//div[@role="button" and contains(text(), "Далее")]',
        '//button[.//span[contains(text(), "Далее")]]',
        '//div[@role="button" and .//span[contains(text(), "Далее")]]',
        'button:has-text("Next")',
        'div[role="button"]:has-text("Next")',
        '[aria-label*="Next"]',
        'button:contains("Next")',
        '//button[contains(text(), "Next")]',
        '//div[@role="button" and contains(text(), "Next")]',
        '//button[.//span[contains(text(), "Next")]]',
        '//div[@role="button" and .//span[contains(text(), "Next")]]',
        'button:has-text("Продолжить")',
        'button:has-text("Continue")',
        '[aria-label*="Продолжить"]',
        '[aria-label*="Continue"]',
        'div[class*="x1i10hfl"][role="button"]',
        'div[class*="xjqpnuy"][role="button"]',
        'div[tabindex="0"][role="button"]'
    ]
    
    # Email поля
    EMAIL_FIELDS = [
        'input[name="emailOrPhone"]',
        'input[name="email_or_phone"]',
        'input[type="email"]',
        'input[type="text"][autocomplete="email"]',
        'input[aria-label*="email" i]:not([aria-label*="code" i]):not([aria-label*="код" i])',
        'input[aria-label*="Email" i]:not([aria-label*="code" i]):not([aria-label*="код" i])',
        'input[aria-label*="почт" i]:not([aria-label*="код" i])',
        'input[aria-label*="Почт" i]:not([aria-label*="код" i])',
        'input[placeholder*="email" i]:not([placeholder*="code" i]):not([placeholder*="код" i])',
        'input[placeholder*="Email" i]:not([placeholder*="code" i]):not([placeholder*="код" i])',
        'input[placeholder*="почт" i]:not([placeholder*="код" i])',
        'input[placeholder*="Почт" i]:not([placeholder*="код" i])',
        'input[id*="email"]:not([id*="code"]):not([id*="verification"])',
        'input[id*="Email"]:not([id*="code"]):not([id*="verification"])'
    ]
    
    # Кнопки отправки
    SUBMIT_BUTTONS = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Confirm")',
        'button:has-text("Continue")',
        'button:has-text("Submit")',
        'button:has-text("Next")',
        'button:has-text("Продолжить")',
        'button:has-text("Подтвердить")',
        'button:has-text("Отправить")',
        'button[aria-label*="confirm" i]',
        'button[aria-label*="continue" i]',
        'button[aria-label*="submit" i]',
        'button[aria-label*="next" i]',
        'button[aria-label*="подтвердить" i]',
        'button[aria-label*="продолжить" i]',
        '[role="button"][aria-label*="confirm" i]',
        '[role="button"][aria-label*="continue" i]',
        '[role="button"][aria-label*="submit" i]',
        '//button[contains(text(), "Confirm")]',
        '//button[contains(text(), "Continue")]',
        '//button[contains(text(), "Submit")]',
        '//button[contains(text(), "Next")]',
        '//button[contains(text(), "Продолжить")]',
        '//button[contains(text(), "Подтвердить")]',
        '//button[.//span[contains(text(), "Confirm")]]',
        '//button[.//span[contains(text(), "Continue")]]',
        '//button[.//span[contains(text(), "Submit")]]',
        '//button[.//span[contains(text(), "Next")]]',
        '//button[.//span[contains(text(), "Продолжить")]]',
        '//button[.//span[contains(text(), "Подтвердить")]]',
        'form button',
        'form input[type="button"]',
        'button:not([style*="display: none"]):not([style*="visibility: hidden"])'
    ]
    
    # Поля кода верификации
    VERIFICATION_CODE_FIELDS = [
        'input[name="email"]',
        'input[name="verificationCode"]',
        'input[name="confirmationCode"]',
        'input[name="securityCode"]',
        'input[name="code"]',
        'input[type="text"]',
        'input[type="tel"]',
        'input[type="number"]',
        'input[aria-label*="код" i]',
        'input[aria-label*="code" i]',
        'input[aria-label*="security" i]',
        'input[aria-label*="verification" i]',
        'input[aria-label*="confirmation" i]',
        'input[placeholder*="код" i]',
        'input[placeholder*="code" i]',
        'input[placeholder*="security" i]',
        'input[placeholder*="verification" i]',
        'input[placeholder*="confirmation" i]',
        'input[id*="r"]',
        'input[id^="«"]',
        'input[autocomplete="off"]',
        'input[autocomplete="one-time-code"]'
    ]
    
    # Ограниченные селекторы для кода верификации
    VERIFICATION_CODE_FIELDS_RESTRICTIVE = [
        'input[name="verificationCode"]',
        'input[name="confirmationCode"]',
        'input[name="securityCode"]',
        'input[name="code"]',
        'input[autocomplete="one-time-code"]',
        'input[aria-label*="код" i]:not([aria-label*="пользователя"])',
        'input[aria-label*="code" i]:not([aria-label*="username"])'
    ]
    
    # Кнопки сохранения данных входа
    SAVE_LOGIN_BUTTONS = [
        'button:has-text("Сохранить данные")',
        'button:has-text("Save Info")',
        'button:has-text("Save")',
        'button:has-text("Сохранить")',
        'button._acan._acap._acas._aj1-._ap30',
        'button[type="button"]:has-text("Сохранить")',
        '//button[contains(text(), "Сохранить данные")]',
        '//button[contains(text(), "Save Info")]',
        '//button[contains(text(), "Save")]',
        '//button[contains(text(), "Сохранить")]',
        'button[aria-label*="Save"]',
        'button[aria-label*="Сохранить"]',
        'main button[type="button"]',
        'section button[type="button"]'
    ]
    
    # Кнопки "Не сейчас"
    NOT_NOW_BUTTONS = [
        'button:has-text("Не сейчас")',
        'button:has-text("Not now")',
        'button:has-text("Not Now")',
        'div[role="button"]:has-text("Не сейчас")',
        'div[role="button"]:has-text("Not now")',
        '//button[contains(text(), "Не сейчас")]',
        '//button[contains(text(), "Not now")]',
        '//div[@role="button" and contains(text(), "Не сейчас")]',
        '//div[@role="button" and contains(text(), "Not now")]'
    ]
    
    # Индикаторы успешной загрузки
    SUCCESS_INDICATORS = [
        'div:has-text("Ваша публикация опубликована")',
        'div:has-text("Публикация опубликована")',
        'div:has-text("Опубликовано")',
        'div:has-text("Публикация размещена")',
        'div:has-text("Пост опубликован")',
        'div:has-text("Видео опубликовано")',
        '//div[contains(text(), "Ваша публикация опубликована")]',
        '//div[contains(text(), "Публикация опубликована")]',
        '//div[contains(text(), "Опубликовано")]',
        '//div[contains(text(), "Публикация размещена")]',
        '//div[contains(text(), "Пост опубликован")]',
        '//span[contains(text(), "Опубликовано")]',
        'div:has-text("Your post has been shared")',
        'div:has-text("Post shared")',
        'div:has-text("Posted")',
        'div:has-text("Video posted")',
        'div:has-text("Successfully posted")',
        '//div[contains(text(), "Your post has been shared")]',
        '//div[contains(text(), "Post shared")]',
        '//div[contains(text(), "Posted")]',
        '//div[contains(text(), "Video posted")]',
        '//span[contains(text(), "Posted")]',
        'svg[aria-label*="Действия"]',
        'svg[aria-label*="Activity"]',
        '[aria-label*="Действия"]',
        '[aria-label*="Activity"]',
        'svg[aria-label*="Главная"]',
        'svg[aria-label*="Home"]',
        '[aria-label*="Главная"]',
        '[aria-label*="Home"]',
        'a[href="/"]',
        'svg[aria-label*="Профиль"]',
        'svg[aria-label*="Profile"]',
        '[aria-label*="Профиль"]',
        '[aria-label*="Profile"]'
    ]
    
    # Индикаторы ошибок
    ERROR_INDICATORS = [
        'div:has-text("Ошибка")',
        'div:has-text("Не удалось")',
        'div:has-text("Попробуйте еще раз")',
        'div:has-text("Error")',
        'div:has-text("Failed")',
        'div:has-text("Try again")',
        'div:has-text("Something went wrong")'
    ]
    
    # Индикаторы страницы загрузки
    UPLOAD_PAGE_INDICATORS = [
        'input[type="file"]',
        'input[accept*="video"]',
        'input[accept*="image"]',
        'button:has-text("Поделиться")',
        'button:has-text("Опубликовать")',
        'div[role="button"]:has-text("Поделиться")',
        'button:has-text("Share")',
        'button:has-text("Publish")',
        'div[role="button"]:has-text("Share")',
        'textarea[aria-label*="Напишите подпись"]',
        'textarea[placeholder*="Напишите подпись"]',
        'textarea[aria-label*="Write a caption"]',
        'textarea[placeholder*="Write a caption"]',
        'button:has-text("Далее")',
        'button:has-text("Next")',
        '[aria-label*="Обрезка"]',
        '[aria-label*="Crop"]',
        'button:has-text("Обрезка")'
    ]
    
    # Диалоги успешной загрузки
    SUCCESS_DIALOGS = [
        'div:has-text("Ваша публикация опубликована")',
        'div:has-text("Публикация опубликована")',
        'div:has-text("Видео опубликовано")',
        'div:has-text("Пост опубликован")',
        'div:has-text("Опубликовано")',
        'div:has-text("Your post has been shared")',
        'div:has-text("Post shared")',
        'div:has-text("Video posted")',
        'div:has-text("Posted successfully")',
        '//div[contains(text(), "Ваша публикация опубликована")]',
        '//div[contains(text(), "Публикация опубликована")]',
        '//div[contains(text(), "Видео опубликовано")]',
        '//div[contains(text(), "Your post has been shared")]',
        '//div[contains(text(), "Post shared")]'
    ]
    
    # Кнопки закрытия
    CLOSE_BUTTONS = [
        'button[aria-label*="Закрыть"]',
        'button[aria-label*="Close"]',
        'svg[aria-label*="Закрыть"]',
        'svg[aria-label*="Close"]',
        '[aria-label*="Закрыть"]',
        '[aria-label*="Close"]',
        'button:has-text("×")',
        'button:has-text("✕")',
        'div[role="button"]:has-text("×")',
        'div[role="button"]:has-text("✕")',
        '//button[@aria-label="Закрыть"]',
        '//button[@aria-label="Close"]',
        '//svg[@aria-label="Закрыть"]',
        '//svg[@aria-label="Close"]',
        '//button[contains(text(), "×")]',
        '//div[@role="button" and contains(text(), "×")]',
        'button[class*="close"]',
        'div[class*="close"][role="button"]',
        'button[data-testid*="close"]',
        'div[data-testid*="close"][role="button"]'
    ]
    
    # Индикаторы главного интерфейса
    MAIN_INTERFACE_INDICATORS = [
        'svg[aria-label*="Главная"]',
        'svg[aria-label*="Home"]',
        'svg[aria-label*="Создать"]',
        'svg[aria-label*="Create"]',
        '[aria-label*="Главная"]',
        '[aria-label*="Home"]'
    ]
    
    # Селекторы диалогов человеческой верификации
    HUMAN_VERIFICATION_DIALOGS = [
        'span:has-text("подтвердите, что это вы")',
        'span:has-text("подтвердите что это вы")',
        'span:has-text("подтвердите, что вы")',
        'span:has-text("подтвердите что вы")',
        'span:has-text("человек")',
        'div:has-text("целостности аккаунта")',
        'div:has-text("целостность аккаунта")',
        'span:has-text("Почему вы это видите")',
        'span:has-text("Что это означает")',
        'span:has-text("Что можно сделать")',
        'span:has-text("confirm that you are human")',
        'span:has-text("prove you are human")',
        'div:has-text("account integrity")',
        'span:has-text("Why you are seeing this")',
        'span:has-text("What this means")',
        'span:has-text("What you can do")',
        'div[data-bloks-name="bk.components.Flexbox"]',
        'div[role="dialog"]',
        'button:has-text("Продолжить")',
        'button:has-text("Continue")'
    ]

# API константы
class APIConstants:
    TFA_API_URL = "https://2fa.fb.rip/api/otp/"
    DOLPHIN_TIMEOUT = 30
    RECAPTCHA_TIMEOUT = 180 