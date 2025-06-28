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
    
    # Новые улучшенные задержки
    BATCH_PROCESSING_DELAY_MIN = 300   # 5 минут между батчами
    BATCH_PROCESSING_DELAY_MAX = 900   # 15 минут между батчами
    
    # Адаптивные задержки по времени суток
    NIGHT_DELAY_MULTIPLIER = 2.0      # Ночью медленнее
    MORNING_DELAY_MULTIPLIER = 1.5    # Утром медленнее
    EVENING_DELAY_MULTIPLIER = 0.8    # Вечером быстрее
    
    # Задержки при ошибках
    ERROR_RECOVERY_DELAY_MIN = 30     # Минимальная задержка после ошибки
    ERROR_RECOVERY_DELAY_MAX = 180    # Максимальная задержка после ошибки
    
    # Задержки для симуляции перерывов
    BREAK_PROBABILITY = 0.15          # 15% вероятность перерыва
    MICRO_BREAK_MIN = 5               # Микроперерыв 5-15 сек
    MICRO_BREAK_MAX = 15
    SHORT_BREAK_MIN = 60              # Короткий перерыв 1-3 мин
    SHORT_BREAK_MAX = 180
    LONG_BREAK_MIN = 300              # Длинный перерыв 5-15 мин
    LONG_BREAK_MAX = 900
    
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
    
    # Email верификация - УЛУЧШЕННЫЕ ключевые слова
    EMAIL_VERIFICATION_KEYWORDS = [
        # Специфичные для Instagram фразы
        'we sent you a login code',
        'мы отправили вам код для входа',
        'login code was sent',
        'код для входа отправлен',
        'enter the login code',
        'введите код для входа',
        'check your email for a code',
        'проверьте почту на наличие кода',
        'verification code sent to',
        'код подтверждения отправлен на',
        
        # Общие фразы email верификации (более специфичные)
        'sent you a code',
        'отправили вам код',
        'code was sent to your email',
        'код отправлен на вашу почту',
        'check your email',
        'проверьте почту',
        'sent to your email',
        'отправлен на вашу почту',
        'email address',
        'адрес электронной почты',
        'we sent',
        'мы отправили',
        'sent you',
        'отправили вам',
        
        # Ключевые слова верификации
        'verification',
        'верификация',
        'confirmation',
        'подтверждение',
        'verify your',
        'подтвердите ваш',
        'confirm your',
        'подтвердите свой',
        
        # Более общие (используются как fallback)
        'enter your email',
        'введите ваш email',
        'provide email',
        'укажите email',
        'email required',
        'email обязателен',
    ]
    
    # Код входа - УЛУЧШЕННЫЕ ключевые слова
    CODE_ENTRY_KEYWORDS = [
        # Специфичные для Instagram
        'enter the 6-digit code',
        'введите 6-значный код',
        'enter the code we sent',
        'введите код который мы отправили',
        'enter your login code',
        'введите ваш код для входа',
        'login code',
        'код для входа',
        
        # Общие фразы ввода кода
        'enter the code',
        'введите код',
        'enter code',
        'введите код',
        'confirmation code',
        'код подтверждения',
        'security code',
        'код безопасности',
        'verification code',
        'код верификации',
        'we sent you',
        'мы отправили вам',
        'sent you a',
        'отправили вам',
        'code from',
        'код из',
    ]
    
    # Ключевые слова NON-email верификации (для исключения ложных срабатываний)
    NON_EMAIL_VERIFICATION_KEYWORDS = [
        'google authenticator',
        'authentication app',
        'приложение аутентификации',
        'authenticator app',
        'приложение authenticator',
        'two-factor app',
        'приложение двухфакторной',
        'backup code',
        'резервный код',
        'recovery code',
        'код восстановления',
        'sms code',
        'смс код',
        'text message',
        'текстовое сообщение',
        'phone number',
        'номер телефона',
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
    SUSPENDED = 'SUSPENDED'  # Account suspended by Instagram

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
    
    # Упоминания/соавторы - ОБНОВЛЕННЫЕ СЕЛЕКТОРЫ для индивидуального ввода
    MENTION_FIELDS = [
        # Основные селекторы из HTML
        'input[name="creation-collaborator-input"]',
        'input[placeholder="Добавить соавторов"]',
        
        # Расширенные селекторы
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
        
        # English selectors
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
        
        # XPath селекторы
        '//input[@placeholder="Добавить соавторов"]',
        '//input[@name="creation-collaborator-input"]',
        '//input[contains(@placeholder, "Добавить соавторов")]',
        '//input[contains(@placeholder, "добавить соавторов")]',
        '//input[contains(@aria-label, "Добавить соавторов")]',
        '//input[contains(@aria-label, "соавторы")]',
        '//input[contains(@placeholder, "Отметить людей")]',
        '//input[contains(@placeholder, "отметить людей")]',
        '//input[contains(@aria-label, "Отметить людей")]',
        '//input[contains(@aria-label, "отметить")]',
        '//input[contains(@placeholder, "Add collaborators")]',
        '//input[contains(@placeholder, "Tag people")]',
        '//input[contains(@aria-label, "Add collaborators")]',
        '//input[contains(@aria-label, "collaborators")]',
        '//input[contains(@aria-label, "Tag people")]',
        '//input[contains(@aria-label, "tag")]'
    ]
    
    # Упоминания - предложения (для индивидуального выбора)
    MENTION_SUGGESTIONS = [
        # Селекторы для конкретного пользователя (будут форматироваться)
        "//div[text()='{username}']/../../div/label/div/input",
        "//div[contains(text(), '{username}')]/../../div/label/div/input",
        
        # Диалоговые селекторы
        "//div[@role='dialog']/div/div/div/div/div/div/button",
        "//div[@role='dialog']//button[1]",
        "//div[@role='dialog']//div[@role='button'][1]",
        
        # Общие селекторы для первого предложения
        'div[role="button"]:has-text("{username}")',
        'button:has-text("{username}")',
        'div[role="button"]:first-child',
        'li[role="button"]:first-child',
        'button:first-child',
        
        # XPath для первого предложения
        '(//div[@role="button"])[1]',
        '(//li[@role="button"])[1]',
        '(//button)[1]',
        
        # Дополнительные селекторы
        'div[data-testid*="mention"]:first-child',
        'div[class*="mention"]:first-child',
        'li[data-testid*="mention"]:first-child',
        'li[class*="mention"]:first-child'
    ]
    
    # Кнопка "Готово" для упоминаний (обновленные селекторы)
    DONE_BUTTONS = [
        # Основные селекторы
        "//div[text()='Done']",
        "//div[text()='Готово']",
        "//button[text()='Done']",
        "//button[text()='Готово']",
        
        # CSS селекторы
        'button:has-text("Готово")',
        'button:has-text("Done")',
        'button:has-text("Продолжить")',
        'button:has-text("Continue")',
        'div[role="button"]:has-text("Готово")',
        'div[role="button"]:has-text("Done")',
        
        # Расширенные XPath
        "//div[@role='button' and text()='Done']",
        "//div[@role='button' and text()='Готово']",
        "//button[contains(text(), 'Done')]",
        "//button[contains(text(), 'Готово')]",
        "//div[@role='button' and contains(text(), 'Done')]",
        "//div[@role='button' and contains(text(), 'Готово')]",
        
        # Aria-label селекторы
        'button[aria-label*="Done"]',
        'button[aria-label*="Готово"]',
        'div[role="button"][aria-label*="Done"]',
        'div[role="button"][aria-label*="Готово"]',
        
        # Fallback селекторы
        'button:has-text("OK")',
        'button:has-text("ОК")',
        '[aria-label*="OK"]',
        '[aria-label*="ОК"]'
    ]
    
    # Кнопка "Далее" - SEMANTIC VERSION (без динамических CSS-классов)
    NEXT_BUTTONS = [
        # 🎯 ПРИОРИТЕТ 1: Текстовые селекторы (самые надежные)
        'button:has-text("Далее")',
        'button:has-text("Next")',
        'button:has-text("Продолжить")',
        'button:has-text("Continue")',
        'div[role="button"]:has-text("Далее")',
        'div[role="button"]:has-text("Next")',
        'div[role="button"]:has-text("Продолжить")',
        'div[role="button"]:has-text("Continue")',
        
        # 🎯 ПРИОРИТЕТ 2: Роли и табиндексы (семантические)
        '[role="button"]:has-text("Далее")',
        '[role="button"][tabindex="0"]:has-text("Далее")',
        '[role="button"]:has-text("Next")',
        '[role="button"][tabindex="0"]:has-text("Next")',
        '[role="button"]:has-text("Продолжить")',
        '[role="button"]:has-text("Continue")',
        
        # 🎯 ПРИОРИТЕТ 3: Aria-label атрибуты
        'button[aria-label*="Далее"]',
        'button[aria-label*="Next"]',
        'button[aria-label*="Продолжить"]',
        'button[aria-label*="Continue"]',
        '[role="button"][aria-label*="Далее"]',
        '[role="button"][aria-label*="Next"]',
        
        # 🎯 ПРИОРИТЕТ 4: XPath текстовые (очень точные)
        '//button[contains(text(), "Далее")]',
        '//button[contains(text(), "Next")]',
        '//button[contains(text(), "Продолжить")]',
        '//button[contains(text(), "Continue")]',
        '//div[@role="button" and contains(text(), "Далее")]',
        '//div[@role="button" and contains(text(), "Next")]',
        '//div[@role="button" and contains(text(), "Продолжить")]',
        '//div[@role="button" and contains(text(), "Continue")]',
        
        # 🎯 ПРИОРИТЕТ 5: XPath с span (для сложной структуры)
        '//button[.//span[contains(text(), "Далее")]]',
        '//div[@role="button" and .//span[contains(text(), "Далее")]]',
        '//button[.//span[contains(text(), "Next")]]',
        '//div[@role="button" and .//span[contains(text(), "Next")]]',
        '//button[.//span[contains(text(), "Продолжить")]]',
        '//div[@role="button" and .//span[contains(text(), "Продолжить")]]',
        
        # 🎯 ПРИОРИТЕТ 6: Универсальные семантические селекторы
        'div[role="button"][tabindex="0"]',  # Любая кнопка с табиндексом
        'button[type="button"]',  # Любая кнопка
    ]
    
    # Email поля - УЛУЧШЕННЫЕ селекторы
    EMAIL_FIELDS = [
        # Основные селекторы для email полей
        'input[name="emailOrPhone"]',
        'input[name="email_or_phone"]',
        'input[name="email"]',
        'input[type="email"]',
        'input[type="text"][autocomplete="email"]',
        'input[inputmode="email"]',
        
        # Селекторы с aria-label (исключая поля кода)
        'input[aria-label*="email" i]:not([aria-label*="code" i]):not([aria-label*="код" i]):not([aria-label*="verification" i])',
        'input[aria-label*="Email" i]:not([aria-label*="code" i]):not([aria-label*="код" i]):not([aria-label*="verification" i])',
        'input[aria-label*="почт" i]:not([aria-label*="код" i]):not([aria-label*="verification" i])',
        'input[aria-label*="Почт" i]:not([aria-label*="код" i]):not([aria-label*="verification" i])',
        'input[aria-label*="электронная почта" i]:not([aria-label*="код" i])',
        'input[aria-label*="адрес" i]:not([aria-label*="код" i])',
        
        # Селекторы с placeholder (исключая поля кода)
        'input[placeholder*="email" i]:not([placeholder*="code" i]):not([placeholder*="код" i]):not([placeholder*="verification" i])',
        'input[placeholder*="Email" i]:not([placeholder*="code" i]):not([placeholder*="код" i]):not([placeholder*="verification" i])',
        'input[placeholder*="почт" i]:not([placeholder*="код" i]):not([placeholder*="verification" i])',
        'input[placeholder*="Почт" i]:not([placeholder*="код" i]):not([placeholder*="verification" i])',
        'input[placeholder*="электронная почта" i]:not([placeholder*="код" i])',
        'input[placeholder*="укажите email" i]',
        'input[placeholder*="введите email" i]',
        
        # ID селекторы (исключая поля кода и верификации)
        'input[id*="email"]:not([id*="code"]):not([id*="verification"]):not([id*="confirm"])',
        'input[id*="Email"]:not([id*="code"]):not([id*="verification"]):not([id*="confirm"])',
        
        # XPath селекторы для более точного поиска
        '//input[contains(@placeholder, "email") and not(contains(@placeholder, "code")) and not(contains(@placeholder, "verification"))]',
        '//input[contains(@aria-label, "email") and not(contains(@aria-label, "code")) and not(contains(@aria-label, "verification"))]',
        '//input[@type="email"]',
        '//input[@inputmode="email"]',
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
        '//button[.//span[contains(text(), "Next")]',
        '//button[.//span[contains(text(), "Продолжить")]',
        '//button[.//span[contains(text(), "Подтвердить")]',
        'form button',
        'form input[type="button"]',
        'button:not([style*="display: none"]):not([style*="visibility: hidden"])'
    ]
    
    # Поля кода верификации - УЛУЧШЕННЫЕ селекторы
    VERIFICATION_CODE_FIELDS = [
        # Специфичные селекторы для Instagram кодов
        'input[name="verificationCode"]',
        'input[name="confirmationCode"]',
        'input[name="securityCode"]',
        'input[name="loginCode"]',
        'input[name="code"]',
        'input[autocomplete="one-time-code"]',
        'input[inputmode="numeric"]',
        
        # Селекторы по типу поля
        'input[type="tel"]',
        'input[type="number"]',
        'input[type="text"][maxlength="6"]',
        'input[type="text"][pattern="[0-9]*"]',
        
        # Селекторы с aria-label для кодов
        'input[aria-label*="код" i]:not([aria-label*="email" i]):not([aria-label*="почт" i])',
        'input[aria-label*="code" i]:not([aria-label*="email" i]):not([aria-label*="phone" i])',
        'input[aria-label*="verification" i]',
        'input[aria-label*="верификация" i]',
        'input[aria-label*="confirmation" i]',
        'input[aria-label*="подтверждение" i]',
        'input[aria-label*="security" i]',
        'input[aria-label*="безопасность" i]',
        'input[aria-label*="login code" i]',
        'input[aria-label*="код входа" i]',
        
        # Селекторы с placeholder для кодов
        'input[placeholder*="код" i]:not([placeholder*="email" i]):not([placeholder*="почт" i])',
        'input[placeholder*="code" i]:not([placeholder*="email" i]):not([placeholder*="phone" i])',
        'input[placeholder*="verification" i]',
        'input[placeholder*="верификация" i]',
        'input[placeholder*="confirmation" i]',
        'input[placeholder*="подтверждение" i]',
        'input[placeholder*="security" i]',
        'input[placeholder*="6-digit" i]',
        'input[placeholder*="6 цифр" i]',
        'input[placeholder*="enter code" i]',
        'input[placeholder*="введите код" i]',
        
        # Универсальные селекторы (используются как fallback)
        'input[type="text"]',
        'input[id*="code"]',
        'input[id*="verification"]',
        'input[id*="confirm"]',
        'input[autocomplete="off"]',
    ]
    
    # Ограниченные селекторы для кода верификации (более строгие)
    VERIFICATION_CODE_FIELDS_RESTRICTIVE = [
        'input[name="verificationCode"]',
        'input[name="confirmationCode"]',
        'input[name="securityCode"]',
        'input[name="loginCode"]',
        'input[name="code"]',
        'input[autocomplete="one-time-code"]',
        'input[inputmode="numeric"]',
        'input[type="tel"]',
        'input[type="number"]',
        'input[maxlength="6"]',
        'input[aria-label*="код" i]:not([aria-label*="пользователя"]):not([aria-label*="email"]):not([aria-label*="почт"])',
        'input[aria-label*="code" i]:not([aria-label*="username"]):not([aria-label*="email"]):not([aria-label*="phone"])',
        'input[placeholder*="код" i]:not([placeholder*="email"]):not([placeholder*="почт"])',
        'input[placeholder*="code" i]:not([placeholder*="email"]):not([placeholder*="phone"])',
    ]
    
    # Кнопки сохранения данных входа - SEMANTIC VERSION
    SAVE_LOGIN_BUTTONS = [
        # 🎯 ПРИОРИТЕТ 1: Текстовые селекторы (самые надежные)
        'button:has-text("Сохранить данные")',
        'button:has-text("Save Info")',
        'button:has-text("Save")',
        'button:has-text("Сохранить")',
        'button:has-text("Сохранить информацию")',
        'button:has-text("Save Information")',
        
        # 🎯 ПРИОРИТЕТ 2: Тип кнопки с текстом
        'button[type="button"]:has-text("Сохранить")',
        'button[type="button"]:has-text("Save")',
        
        # 🎯 ПРИОРИТЕТ 3: XPath текстовые
        '//button[contains(text(), "Сохранить данные")]',
        '//button[contains(text(), "Save Info")]',
        '//button[contains(text(), "Save")]',
        '//button[contains(text(), "Сохранить")]',
        
        # 🎯 ПРИОРИТЕТ 4: Aria-label атрибуты
        'button[aria-label*="Save"]',
        'button[aria-label*="Сохранить"]',
        '[role="button"][aria-label*="Save"]',
        '[role="button"][aria-label*="Сохранить"]',
        
        # 🎯 ПРИОРИТЕТ 5: Контекстные селекторы
        'main button[type="button"]',
        'section button[type="button"]',
        'form button[type="button"]',
        
        # 🎯 ПРИОРИТЕТ 6: Широкие селекторы (fallback)
        'button[type="button"]',
        'div[role="button"]',
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
        # Русские индикаторы успеха - текстовые
        'div:has-text("Ваша публикация опубликована")',
        'div:has-text("Публикация опубликована")',
        'div:has-text("Опубликовано")',
        'div:has-text("Публикация размещена")',
        'div:has-text("Пост опубликован")',
        'div:has-text("Видео опубликовано")',
        'div:has-text("Публикация размещена в ленте")',
        'div:has-text("Ваше видео опубликовано")',
        'span:has-text("Опубликовано")',
        'span:has-text("Публикация опубликована")',
        
        # Английские индикаторы успеха - текстовые
        'div:has-text("Your post has been shared")',
        'div:has-text("Post shared")',
        'div:has-text("Posted")',
        'div:has-text("Video posted")',
        'div:has-text("Successfully posted")',
        'div:has-text("Your video has been posted")',
        'div:has-text("Post published")',
        'div:has-text("Video published")',
        'div:has-text("Shared to feed")',
        'span:has-text("Posted")',
        'span:has-text("Post shared")',
        
        # XPath селекторы для более точного поиска (русские)
        '//div[contains(text(), "Ваша публикация опубликована")]',
        '//div[contains(text(), "Публикация опубликована")]',
        '//div[contains(text(), "Опубликовано")]',
        '//div[contains(text(), "Публикация размещена")]',
        '//div[contains(text(), "Пост опубликован")]',
        '//div[contains(text(), "Видео опубликовано")]',
        '//div[contains(text(), "Ваше видео опубликовано")]',
        '//span[contains(text(), "Опубликовано")]',
        '//span[contains(text(), "Публикация опубликована")]',
        
        # XPath селекторы для более точного поиска (английские)
        '//div[contains(text(), "Your post has been shared")]',
        '//div[contains(text(), "Post shared")]',
        '//div[contains(text(), "Posted")]',
        '//div[contains(text(), "Video posted")]',
        '//div[contains(text(), "Successfully posted")]',
        '//div[contains(text(), "Your video has been posted")]',
        '//div[contains(text(), "Post published")]',
        '//div[contains(text(), "Video published")]',
        '//span[contains(text(), "Posted")]',
        '//span[contains(text(), "Post shared")]',
        
        # Иконки и aria-label индикаторы
        'svg[aria-label*="Готово" i]',
        'svg[aria-label*="Done" i]',
        'svg[aria-label*="Success" i]',
        'svg[aria-label*="Успешно" i]',
        'svg[aria-label*="Checkmark" i]',
        'svg[aria-label*="Галочка" i]',
        '[aria-label*="Готово" i]',
        '[aria-label*="Done" i]',
        '[aria-label*="Success" i]',
        '[aria-label*="Успешно" i]',
        
        # Диалоги успеха
        'div[role="dialog"]:has-text("Ваша публикация опубликована")',
        'div[role="dialog"]:has-text("Your post has been shared")',
        'div[role="dialog"]:has-text("Опубликовано")',
        'div[role="dialog"]:has-text("Posted")',
        'div[role="dialog"]:has-text("Shared")',
        '[data-testid="success-dialog"]',
        '[data-testid="post-success"]',
        
        # Индикаторы возврата к главной странице после успешной публикации
        'a[href="/"][aria-label*="Главная" i]',
        'a[href="/"][aria-label*="Home" i]',
        'svg[aria-label*="Главная" i]',
        'svg[aria-label*="Home" i]',
        '[aria-label*="Главная" i]',
        '[aria-label*="Home" i]',
        
        # Дополнительные селекторы успеха
        'div[class*="success"]',
        'div[class*="posted"]',
        'div[class*="shared"]',
        '[data-testid*="success"]',
        '[data-testid*="posted"]',
        '[data-testid*="shared"]',
    ]
    
    # Индикаторы ошибок
    ERROR_INDICATORS = [
        # Русские сообщения об ошибках
        'div:has-text("Что-то пошло не так")',
        'div:has-text("Произошла ошибка")',
        'div:has-text("Ошибка")',
        'div:has-text("Не удалось")',
        'div:has-text("Попробуйте еще раз")',
        'div:has-text("Попробуйте позже")',
        'div:has-text("Не удалось опубликовать")',
        'div:has-text("Не удалось загрузить")',
        'div:has-text("Ошибка при загрузке")',
        'div:has-text("Ошибка публикации")',
        'div:has-text("Публикация не удалась")',
        'div:has-text("Видео не загружено")',
        'div:has-text("Загрузка не удалась")',
        'span:has-text("Ошибка")',
        'span:has-text("Не удалось")',
        
        # Английские сообщения об ошибках
        'div:has-text("Something went wrong")',
        'div:has-text("An error occurred")',
        'div:has-text("Error")',
        'div:has-text("Failed")',
        'div:has-text("Try again")',
        'div:has-text("Please try again")',
        'div:has-text("Upload failed")',
        'div:has-text("Post failed")',
        'div:has-text("Could not upload")',
        'div:has-text("Could not post")',
        'div:has-text("Unable to upload")',
        'div:has-text("Unable to post")',
        'div:has-text("Video not uploaded")',
        'div:has-text("Post not shared")',
        'span:has-text("Error")',
        'span:has-text("Failed")',
        
        # XPath селекторы для ошибок (русские)
        '//div[contains(text(), "Что-то пошло не так")]',
        '//div[contains(text(), "Произошла ошибка")]',
        '//div[contains(text(), "Ошибка")]',
        '//div[contains(text(), "Не удалось")]',
        '//div[contains(text(), "Попробуйте еще раз")]',
        '//div[contains(text(), "Не удалось опубликовать")]',
        '//div[contains(text(), "Не удалось загрузить")]',
        '//div[contains(text(), "Ошибка при загрузке")]',
        '//div[contains(text(), "Публикация не удалась")]',
        '//span[contains(text(), "Ошибка")]',
        '//span[contains(text(), "Не удалось")]',
        
        # XPath селекторы для ошибок (английские)
        '//div[contains(text(), "Something went wrong")]',
        '//div[contains(text(), "An error occurred")]',
        '//div[contains(text(), "Error")]',
        '//div[contains(text(), "Failed")]',
        '//div[contains(text(), "Try again")]',
        '//div[contains(text(), "Upload failed")]',
        '//div[contains(text(), "Post failed")]',
        '//div[contains(text(), "Could not upload")]',
        '//div[contains(text(), "Unable to upload")]',
        '//span[contains(text(), "Error")]',
        '//span[contains(text(), "Failed")]',
        
        # Иконки ошибок и aria-label
        'svg[aria-label*="Ошибка" i]',
        'svg[aria-label*="Error" i]',
        'svg[aria-label*="Warning" i]',
        'svg[aria-label*="Предупреждение" i]',
        'svg[aria-label*="Alert" i]',
        'svg[aria-label*="Внимание" i]',
        '[aria-label*="Ошибка" i]',
        '[aria-label*="Error" i]',
        '[aria-label*="Warning" i]',
        '[aria-label*="Предупреждение" i]',
        '[aria-label*="Alert" i]',
        '[aria-label*="Внимание" i]',
        
        # Диалоги ошибок
        'div[role="dialog"]:has-text("Что-то пошло не так")',
        'div[role="dialog"]:has-text("Something went wrong")',
        'div[role="dialog"]:has-text("Ошибка")',
        'div[role="dialog"]:has-text("Error")',
        'div[role="dialog"]:has-text("Не удалось")',
        'div[role="dialog"]:has-text("Failed")',
        '[data-testid="error-dialog"]',
        '[data-testid="error-message"]',
        
        # CSS классы ошибок
        'div[class*="error"]',
        'div[class*="failed"]',
        'div[class*="warning"]',
        '[data-testid*="error"]',
        '[data-testid*="failed"]',
        '[data-testid*="warning"]',
        
        # Кнопки повторной попытки (косвенный индикатор ошибки)
        'button:has-text("Попробовать снова")',
        'button:has-text("Try Again")',
        'button:has-text("Retry")',
        'button:has-text("Повторить")',
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

# Селекторы для обработки кропа видео
class CropSelectors:
    # ПОЛНОСТЬЮ АДАПТИВНЫЕ селекторы (независимы от CSS-классов Instagram)
    CROP_BUTTON_SELECTORS = [
        # 🎯 ПРИОРИТЕТ 1: Семантические SVG селекторы (самые устойчивые)
        'svg[aria-label="Выбрать размер и обрезать"]',
        'svg[aria-label*="Выбрать размер"]',
        'svg[aria-label*="обрезать"]',
        'svg[aria-label*="размер"]',
        'svg[aria-label*="Select crop"]',
        'svg[aria-label*="Crop"]',
        'svg[aria-label*="Select size"]',
        
        # 🎯 ПРИОРИТЕТ 2: Родительские элементы с семантическими SVG
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
        
        # 🎯 ПРИОРИТЕТ 3: Универсальные aria-label
        '[aria-label*="Выбрать размер и обрезать"]',
        '[aria-label*="Выбрать размер"]',
        '[aria-label*="обрезать"]',
        '[aria-label*="Select crop"]',
        '[aria-label*="Crop"]',
        'button[aria-label*="Выбрать размер"]',
        'button[aria-label*="обрезать"]',
        'button[aria-label*="Select crop"]',
        'button[aria-label*="Crop"]',
        
        # 🎯 ПРИОРИТЕТ 4: XPath семантические селекторы
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
        
        # 🎯 ПРИОРИТЕТ 5: Текстовые селекторы
        'button:has-text("Обрезка")',
        'button:has-text("Crop")',
        'div[role="button"]:has-text("Обрезка")',
        'div[role="button"]:has-text("Crop")',
        
        # 🎯 ПРИОРИТЕТ 6: Универсальные паттерны
        'button[type="button"]:has(svg[aria-label*="размер"])',
        'button[type="button"]:has(svg[aria-label*="crop"])',
        'div[role="button"]:has(button:has(svg[aria-label*="размер"]))',
        'div[role="button"]:has(button:has(svg[aria-label*="crop"]))',
        
        # 🎯 ПРИОРИТЕТ 7: Широкие селекторы (последний resort)
        'button:has(svg)',  # Любая кнопка с SVG
        'div[role="button"]:has(svg)',  # Любой div-кнопка с SVG
    ]
    
    # Селекторы для опции "Оригинал" - ПОЛНОСТЬЮ АДАПТИВНЫЕ
    ORIGINAL_CROP_SELECTORS = [
        # 🎯 ПРИОРИТЕТ 1: Семантические текстовые селекторы (самые надежные)
        'span:has-text("Оригинал")',
        'span:has-text("Original")',
        'div[role="button"]:has(span:has-text("Оригинал"))',
        'button:has(span:has-text("Оригинал"))',
        'div[role="button"]:has(span:has-text("Original"))',
        'button:has(span:has-text("Original"))',
        
        # 🎯 ПРИОРИТЕТ 2: Прямые текстовые селекторы
        'button:has-text("Оригинал")',
        'div[role="button"]:has-text("Оригинал")',
        'button:has-text("Original")',
        'div[role="button"]:has-text("Original")',
        
        # 🎯 ПРИОРИТЕТ 3: SVG с семантическими атрибутами
        'svg[aria-label="Значок контура фото"]',
        'svg[aria-label*="контур"]',
        'svg[aria-label*="фото"]',
        'svg[aria-label*="photo"]',
        'svg[aria-label*="outline"]',
        'div[role="button"]:has(svg[aria-label="Значок контура фото"])',
        'button:has(svg[aria-label="Значок контура фото"])',
        
        # 🎯 ПРИОРИТЕТ 4: XPath семантические (самые точные)
        '//span[text()="Оригинал"]',
        '//span[text()="Original"]',
        '//div[@role="button" and .//span[text()="Оригинал"]]',
        '//button[.//span[text()="Оригинал"]]',
        '//div[@role="button" and .//span[text()="Original"]]',
        '//button[.//span[text()="Original"]]',
        '//button[contains(text(), "Оригинал")]',
        '//div[@role="button" and contains(text(), "Оригинал")]',
        '//button[contains(text(), "Original")]',
        '//div[@role="button" and contains(text(), "Original")]',
        
        # 🎯 ПРИОРИТЕТ 5: SVG XPath
        '//svg[@aria-label="Значок контура фото"]',
        '//svg[contains(@aria-label, "контур")]',
        '//svg[contains(@aria-label, "фото")]',
        '//svg[contains(@aria-label, "photo")]',
        '//svg[contains(@aria-label, "outline")]',
        '//button[.//svg[@aria-label="Значок контура фото"]]',
        '//div[@role="button" and .//svg[@aria-label="Значок контура фото"]]',
        
        # 🎯 ПРИОРИТЕТ 6: Универсальные aria-label
        '[aria-label*="Оригинал"]',
        '[aria-label*="Original"]',
        'button[aria-label*="Оригинал"]',
        'button[aria-label*="Original"]',
        '[title*="Оригинал"]',
        '[title*="Original"]',
        
        # 🎯 ПРИОРИТЕТ 7: Позиционные селекторы (обычно "Оригинал" первый)
        '(//div[@role="button" and @tabindex="0"])[1]',
        '(//button[@tabindex="0"])[1]',
        'div[role="button"][tabindex="0"]:first-child',
        'button[tabindex="0"]:first-child',
    ]
    
    # Индикаторы страницы кропа - SEMANTIC VERSION
    CROP_PAGE_INDICATORS = [
        # Семантические индикаторы
        'svg[aria-label="Выбрать размер и обрезать"]',
        'svg[aria-label*="Выбрать размер"]',
        'svg[aria-label*="обрезать"]',
        'svg[aria-label*="Select crop"]',
        'svg[aria-label*="Crop"]',
        'button:has(svg[aria-label*="размер"])',
        'button:has(svg[aria-label*="crop"])',
        '[aria-label*="Выбрать размер"]',
        '[aria-label*="Select size"]',
        'button:has-text("Оригинал")',
        'button:has-text("Original")',
        'span:has-text("9:16")',
        'span:has-text("1:1")',
        'span:has-text("4:5")',
        'div:has-text("Обрезка")',
        'div:has-text("Crop")',
    ]
    
    # 🤖 АДАПТИВНЫЕ МЕТОДЫ ПОИСКА (независимо от CSS-классов)
    
    @staticmethod
    def find_adaptive_crop_elements(page):
        """Адаптивный поиск элементов кропа на странице"""
        crop_candidates = []
        
        try:
            # 1. Поиск по семантическим атрибутам
            semantic_elements = page.locator('[aria-label*="размер"], [aria-label*="обрез"], [aria-label*="crop"], [aria-label*="Crop"]').all()
            for element in semantic_elements:
                if element.is_visible():
                    crop_candidates.append({
                        'element': element,
                        'method': 'semantic',
                        'confidence': 0.9,
                        'aria_label': element.get_attribute('aria-label')
                    })
            
            # 2. Поиск SVG с анализом содержимого
            svg_elements = page.locator('svg').all()
            for svg in svg_elements:
                if svg.is_visible():
                    aria_label = svg.get_attribute('aria-label') or ""
                    paths = svg.locator('path').all()
                    
                    # Анализ path-ов для характерных паттернов кропа
                    for path in paths:
                        path_data = path.get_attribute('d') or ""
                        if any(pattern in path_data for pattern in ['M10 20H4v-6', 'M20.999 2H14', 'H4v-6', 'V']):
                            crop_candidates.append({
                                'element': svg,
                                'method': 'svg_analysis', 
                                'confidence': 0.7,
                                'aria_label': aria_label,
                                'path_data': path_data[:50]
                            })
                            break
            
            # 3. Контекстный анализ
            button_elements = page.locator('button:has(svg), div[role="button"]:has(svg)').all()
            for button in button_elements:
                if button.is_visible():
                    bbox = button.bounding_box()
                    if bbox and 10 <= bbox['width'] <= 60 and 10 <= bbox['height'] <= 60:
                        svg_inside = button.locator('svg').first
                        if svg_inside.is_visible():
                            crop_candidates.append({
                                'element': button,
                                'method': 'context_analysis',
                                'confidence': 0.5,
                                'size': f"{bbox['width']}x{bbox['height']}",
                                'has_svg': True
                            })
            
            # Сортировка по уверенности
            crop_candidates.sort(key=lambda x: x['confidence'], reverse=True)
            
            return crop_candidates
            
        except Exception as e:
            return []
    
    @staticmethod
    def analyze_page_structure(page):
        """Анализ структуры страницы для понимания текущего состояния"""
        analysis = {
            'page_type': 'unknown',
            'crop_available': False,
            'interactive_elements': 0,
            'svg_count': 0,
            'buttons_with_svg': 0
        }
        
        try:
            # Анализ URL
            url = page.url.lower()
            if 'create' in url:
                analysis['page_type'] = 'create'
            elif 'stories' in url:
                analysis['page_type'] = 'stories'
            elif 'reel' in url:
                analysis['page_type'] = 'reel'
            
            # Подсчет элементов
            analysis['svg_count'] = len(page.locator('svg').all())
            analysis['buttons_with_svg'] = len(page.locator('button:has(svg), div[role="button"]:has(svg)').all())
            analysis['interactive_elements'] = len(page.locator('button, [role="button"], input, textarea').all())
            
            # Проверка доступности кропа
            crop_indicators = [
                '[aria-label*="размер"]',
                '[aria-label*="обрез"]', 
                '[aria-label*="crop"]',
                '[aria-label*="Crop"]'
            ]
            
            for indicator in crop_indicators:
                if page.locator(indicator).first.is_visible(timeout=1000):
                    analysis['crop_available'] = True
                    break
                    
        except Exception as e:
            pass
            
        return analysis
    
    @staticmethod
    def smart_element_detection(page, element_type='crop'):
        """Умное обнаружение элементов с использованием ML-подобных алгоритмов"""
        candidates = []
        
        try:
            if element_type == 'crop':
                # Многоуровневая стратегия поиска элементов кропа
                strategies = [
                    # Стратегия 1: Точные семантические совпадения
                    {
                        'selectors': [
                            'svg[aria-label="Выбрать размер и обрезать"]',
                            'svg[aria-label*="Select crop"]',
                            '[aria-label="Выбрать размер и обрезать"]'
                        ],
                        'weight': 1.0
                    },
                    # Стратегия 2: Частичные семантические совпадения
                    {
                        'selectors': [
                            'svg[aria-label*="размер"]',
                            'svg[aria-label*="обрез"]',
                            '[aria-label*="crop"]'
                        ],
                        'weight': 0.8
                    },
                    # Стратегия 3: Контекстный анализ
                    {
                        'selectors': [
                            'button:has(svg[aria-label*="размер"])',
                            'div[role="button"]:has(svg[aria-label*="crop"])'
                        ],
                        'weight': 0.6
                    },
                    # Стратегия 4: Структурный анализ
                    {
                        'selectors': [
                            'button[type="button"]:has(svg)',
                            'div[role="button"]:has(svg)'
                        ],
                        'weight': 0.3
                    }
                ]
                
                for strategy in strategies:
                    for selector in strategy['selectors']:
                        try:
                            elements = page.locator(selector).all()
                            for element in elements:
                                if element.is_visible(timeout=500):
                                    candidates.append({
                                        'element': element,
                                        'selector': selector,
                                        'weight': strategy['weight'],
                                        'strategy': strategy
                                    })
                        except:
                            continue
            
            # Сортировка по весу
            candidates.sort(key=lambda x: x['weight'], reverse=True)
            return candidates
            
        except Exception as e:
            return []

# Профили пользователей для различного поведения
class UserProfiles:
    PROFILES = {
        'conservative': {
            'speed_multiplier': 1.5,
            'error_rate': 0.02,
            'break_probability': 0.20,
            'retry_patience': 3,
            'description': 'Консервативный пользователь'
        },
        'normal': {
            'speed_multiplier': 1.0,
            'error_rate': 0.05,
            'break_probability': 0.15,
            'retry_patience': 2,
            'description': 'Обычный пользователь'
        },
        'aggressive': {
            'speed_multiplier': 0.7,
            'error_rate': 0.08,
            'break_probability': 0.10,
            'retry_patience': 1,
            'description': 'Агрессивный пользователь'
        },
        'casual': {
            'speed_multiplier': 1.8,
            'error_rate': 0.12,
            'break_probability': 0.25,
            'retry_patience': 4,
            'description': 'Случайный пользователь'
        }
    }

# Login form selectors
LOGIN_FORM = {
    'username': [
        'input[name="email"]',              # CURRENT Instagram selector
        'input[name="username"]',           # Legacy selector
        'input[name="emailOrPhone"]',       # Alternative selector
        'input[type="text"]:not([name="pass"])',  # Any text input that's not password
        'input[aria-label*="Имя пользователя"]',
        'input[aria-label*="Телефон"]',
        'input[aria-label*="Phone number"]',
        'input[aria-label*="номер мобильного телефона"]',
        'input[aria-label*="электронный адрес"]',
        'input[placeholder*="Имя пользователя"]',
        'input[placeholder*="Телефон"]',
        'input[placeholder*="Phone number"]',
        'input[placeholder*="номер мобильного телефона"]',
        'input[placeholder*="электронный адрес"]',
    ],
    'password': [
        'input[name="pass"]',               # CURRENT Instagram selector
        'input[name="password"]',           # Legacy selector
        'input[type="password"]',           # Any password input
        'input[aria-label*="Пароль"]',
        'input[aria-label*="Password"]',
        'input[placeholder*="Пароль"]',
        'input[placeholder*="Password"]',
    ],
    'submit': [
        # Enabled buttons first
        'button:not([aria-disabled="true"]):has-text("Войти")',
        'button:not([aria-disabled="true"]):has-text("Log in")',
        'div[role="button"]:not([aria-disabled="true"]):has-text("Войти")',
        'div[role="button"]:not([aria-disabled="true"]):has-text("Log in")',
        
        # Fallback to any submit button
        'button[type="submit"]',
        'button:has-text("Войти")',
        'button:has-text("Log in")',
        'div[role="button"]:has-text("Войти")',
        'div[role="button"]:has-text("Log in")',
        
        # Even disabled ones as last resort
        'button[aria-disabled="true"]:has-text("Войти")',
        'button[aria-disabled="true"]:has-text("Log in")',
        'div[role="button"][aria-disabled="true"]:has-text("Войти")',
        'div[role="button"][aria-disabled="true"]:has-text("Log in")',
    ]
} 