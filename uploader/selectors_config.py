# Instagram Selectors Configuration
# This file contains all CSS and XPath selectors used for Instagram automation

class InstagramSelectors:
    """Centralized Instagram selectors configuration - ADAPTIVE VERSION"""
    
    # Upload button selectors - SEMANTIC APPROACH
    UPLOAD_BUTTON = [
        # [TARGET] ПРИОРИТЕТ 0: Родительские элементы (самые устойчивые, RU/EN)
        'a[role="link"]:has(svg[aria-label*="Новая публикация"])',
        'a[role="link"]:has(span:has-text("Создать"))',
        'a[role="link"]:has(svg[aria-label*="New post"])',
        'a[role="link"]:has(span:has-text("Create"))',
        'button:has(svg[aria-label*="Новая публикация"])',
        'button:has(svg[aria-label*="New post"])',
        'div[role="button"]:has(svg[aria-label*="Новая публикация"])',
        'div[role="button"]:has(svg[aria-label*="New post"])',
        'svg:has(title:has-text("Новая публикация"))',
        'svg:has(title:has-text("New post"))',
        
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
        'button:has-text("Select from device")',
        'div[role="button"]:has-text("Select from device")',
        
        # [TARGET] ПРИОРИТЕТ 4b: Испанские/Португальские тексты
        'button:has-text("Seleccionar desde el ordenador")',
        'div[role="button"]:has-text("Seleccionar desde el ordenador")',
        'button:has-text("Seleccionar desde la computadora")',
        'div[role="button"]:has-text("Seleccionar desde la computadora")',
        'button:has-text("Seleccionar desde el dispositivo")',
        'div[role="button"]:has-text("Seleccionar desde el dispositivo")',
        'button:has-text("Seleccionar archivos")',
        'div[role="button"]:has-text("Seleccionar archivos")',
        'button:has-text("Selecionar do computador")',
        'div[role="button"]:has-text("Selecionar do computador")',
        'button:has-text("Selecionar do dispositivo")',
        'div[role="button"]:has-text("Selecionar do dispositivo")',
        'button:has-text("Selecionar arquivos")',
        'div[role="button"]:has-text("Selecionar arquivos")',
        
        # [TARGET] ПРИОРИТЕТ 5: XPath тексты
        '//button[contains(text(), "Выбрать на компьютере")]',
        '//div[@role="button" and contains(text(), "Выбрать на компьютере")]',
        '//button[contains(text(), "Выбрать файлы")]',
        '//div[@role="button" and contains(text(), "Выбрать файлы")]',
        '//button[contains(text(), "Select from computer")]',
        '//div[@role="button" and contains(text(), "Select from computer")]',
        '//button[contains(text(), "Select files")]',
        '//div[@role="button" and contains(text(), "Select files")]',
        '//button[contains(text(), "Select from device")]',
        '//div[@role="button" and contains(text(), "Select from device")]',
        '//button[contains(text(), "Seleccionar desde el ordenador")]',
        '//div[@role="button" and contains(text(), "Seleccionar desde el ordenador")]',
        '//button[contains(text(), "Seleccionar desde la computadora")]',
        '//div[@role="button" and contains(text(), "Seleccionar desde la computadora")]',
        '//button[contains(text(), "Seleccionar archivos")]',
        '//div[@role="button" and contains(text(), "Seleccionar archivos")]',
        '//button[contains(text(), "Seleccionar desde el dispositivo")]',
        '//div[@role="button" and contains(text(), "Seleccionar desde el dispositivo")]',
        '//button[contains(text(), "Selecionar do computador")]',
        '//div[@role="button" and contains(text(), "Selecionar do computador")]',
        '//button[contains(text(), "Selecionar arquivos")]',
        '//div[@role="button" and contains(text(), "Selecionar arquivos")]',
        '//button[contains(text(), "Selecionar do dispositivo")]',
        '//div[@role="button" and contains(text(), "Selecionar do dispositivo")]',
        
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
    
    # OK/Accept variants for dialogs (RU/EN/ES/PT)
    OK_ACCEPT_BUTTONS = [
        'button:has-text("OK")',
        'button:has-text("ОК")',
        'div[role="button"]:has-text("OK")',
        'div[role="button"]:has-text("ОК")',
        'button:has-text("Aceptar")',
        'div[role="button"]:has-text("Aceptar")',
        'button:has-text("Aceitar")',
        'div[role="button"]:has-text("Aceitar")',
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
        # Spanish/Portuguese fallbacks
        'button:has-text("Siguiente")',
        'div[role="button"]:has-text("Siguiente")',
        'button:has-text("Avançar")',
        'div[role="button"]:has-text("Avançar")',
        
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

    # Keywords to validate Next/Continue buttons by text content (lowercase)
    NEXT_BUTTON_KEYWORDS = [
        'далее', 'продолжить',
        'next', 'continue',
        'siguiente', 'continuar',
        'avançar'
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
        # Spanish/Portuguese fallbacks
        'button:has-text("Compartir")',
        'div[role="button"]:has-text("Compartir")',
        'button:has-text("Compartilhar")',
        'div[role="button"]:has-text("Compartilhar")',
        
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
    
    # Done button in mentions/location dialogs (RU/EN/ES/PT)
    DONE_BUTTON = [
        '//div[text()="Done"]',
        '//div[text()="Готово"]',
        '//div[text()="Listo"]',
        '//div[text()="Concluído"]',
        'div[role="button"]:has-text("Done")',
        'button:has-text("Done")',
        'div[role="button"]:has-text("Готово")',
        'button:has-text("Готово")',
        'div[role="button"]:has-text("Listo")',
        'button:has-text("Listo")',
        'div[role="button"]:has-text("Concluído")',
        'button:has-text("Concluído")',
        'div[aria-label*="Done"]',
        'button[aria-label*="Done"]',
        'div[aria-label*="Готово"]',
        'button[aria-label*="Готово"]',
        'div[aria-label*="Listo"]',
        'button[aria-label*="Listo"]',
        'div[aria-label*="Concluído"]',
        'button[aria-label*="Concluído"]',
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
        # Spanish/Portuguese fallbacks
        'textarea[aria-label*="Escribe un pie de foto"]',
        'textarea[placeholder*="Escribe un pie de foto"]',
        'textarea[aria-label*="Escreva uma legenda"]',
        'textarea[placeholder*="Escreva uma legenda"]',
        
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
            # Spanish/Portuguese fallbacks
            'button:has-text("Iniciar sesión")',
            'div[role="button"]:has-text("Iniciar sesión")',
            'button:has-text("Entrar")',
            'div[role="button"]:has-text("Entrar")',
        ]
    }
    
    # 2FA code input selectors
    TFA_INPUT = [
        'input[name="verificationCode"]',
        'input[aria-label*="код"]',
        'input[aria-label*="code"]',
        'input[aria-label*="código" i]',
        'input[aria-label*="código de segurança" i]',
        'input[placeholder*="код"]',
        'input[placeholder*="code"]',
        'input[placeholder*="código" i]',
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
        # Spanish/Portuguese success messages
        'div:has-text("Se compartió tu publicación")',
        'div:has-text("Publicado")',
        'div:has-text("Reel compartido")',
        'div:has-text("Sua publicação foi compartilhada")',
        'div:has-text("Reel compartilhado")',
        
        # XPath selectors for success messages
        '//div[contains(text(), "Ваша публикация опубликована")]',
        '//div[contains(text(), "Публикация опубликована")]',
        '//div[contains(text(), "Видео опубликовано")]',
        '//div[contains(text(), "Your post has been shared")]',
        '//div[contains(text(), "Post shared")]',
    ]
    
    # Error dialog selectors
    ERROR_DIALOG = [
        'div:has-text("Error")',
        'div:has-text("Ошибка")',
        'div:has-text("Failed")',
        'div:has-text("Не удалось")',
        'div:has-text("Something went wrong")',
        'div:has-text("Что-то пошло не так")',
        'div:has-text("Algo salió mal")',
        'div:has-text("Algo deu errado")',
    ]

    # Reels dialog detection selectors (RU/EN/ES/PT)
    REELS_DIALOG_SELECTORS = [
        'div:has(h2:has-text("Теперь видеопубликациями можно делиться как видео Reels"))',
        'div:has(h2:has-text("Now video publications can be shared as Reels videos"))',
        'div:has(h2:has-text("Ahora las publicaciones de video se pueden compartir como Reels"))',
        'div:has(h2:has-text("Agora as publicações de vídeo podem ser compartilhadas como Reels"))',
        'div:has(h2:has-text("видео Reels"))',
        'div:has(h2:has-text("Reels videos"))',
        'div:has(h2:has-text("videos de Reels"))',
        'div:has(h2:has-text("vídeos do Reels"))',
        'div:has(h2:has-text("Reels"))',
        'div:has(span:has-text("видео Reels"))',
        'div:has(span:has-text("Reels videos"))',
        'div:has(span:has-text("videos de Reels"))',
        'div:has(span:has-text("vídeos do Reels"))',
        'div:has(span:has-text("Reels"))',
        'div:has(span:has-text("Теперь видеопубликациями"))',
        'div:has(span:has-text("Now video publications"))',
        'div:has(span:has-text("Ahora las publicaciones de video"))',
        'div:has(span:has-text("Agora as publicações de vídeo"))',
        'div:has(span:has-text("общедоступный аккаунт"))',
        'div:has(span:has-text("public account"))',
        'div:has(span:has-text("cuenta pública"))',
        'div:has(span:has-text("conta pública"))',
        'div:has(span:has-text("создать видео Reels"))',
        'div:has(span:has-text("create Reels videos"))',
        'div:has(span:has-text("crear videos de Reels"))',
        'div:has(span:has-text("criar vídeos do Reels"))',
        'div:has(span:has-text("аудиодорожкой"))',
        'div:has(span:has-text("audio track"))',
        'div:has(span:has-text("pista de audio"))',
        'div:has(span:has-text("faixa de áudio"))',
        'div:has(span:has-text("сделать ремикс"))',
        'div:has(span:has-text("make remix"))',
        'div:has(span:has-text("hacer remix"))',
        'div:has(span:has-text("fazer remix"))',
        'div[role="dialog"]:has-text("Reels")',
        # Icon-based hints
        'div:has(img[src*="reels_nux_icon.png"])',
        'div:has(img[alt*="reels"])',
        'div:has(img[src*="reels"])',
        'div[role="dialog"]',
    ]

    # Upload context indicators used to validate we're in the upload modal/page
    UPLOAD_CONTEXT_INDICATORS = [
        'div[role="dialog"]',
        'div[aria-label*="Создать"]',
        'div[aria-label*="Create"]',
        'div[aria-label*="Publicar"]',
        'div[aria-label*="Publicação"]',
        'textarea[aria-label*="подпись"]',
        'textarea[aria-label*="caption"]',
        'textarea[aria-label*="Escribe un pie de foto"]',
        'textarea[aria-label*="Escreva uma legenda"]',
    ]

    # Location input selectors (RU/EN/ES/PT)
    LOCATION_INPUT = [
        'input[name="creation-location-input"]',
        'input[placeholder="Добавить место"]',
        'input[placeholder*="место" i]',
        'input[placeholder*="location" i]',
        'input[aria-label*="место" i]',
        'input[aria-label*="location" i]',
        'input[aria-label*="Добавить место" i]',
        '//input[@placeholder="Добавить место"]',
        '//input[@name="creation-location-input"]',
        # Spanish
        'input[placeholder*="Agregar ubicación" i]',
        'input[placeholder*="Añadir ubicación" i]',
        'input[aria-label*="ubicación" i]',
        # Portuguese
        'input[placeholder*="Adicionar localização" i]',
        'input[aria-label*="localização" i]',
    ]

    # Mentions input selectors (RU/EN/ES/PT)
    MENTIONS_INPUT = [
        'input[placeholder="Добавить соавторов"]',
        'input[placeholder*="соавтор" i]',
        'input[placeholder*="collaborator" i]',
        'input[aria-label*="соавтор" i]',
        'input[aria-label*="collaborator" i]',
        'input[aria-label*="Добавить соавторов" i]',
        'input[placeholder*="Добавить соавторов" i]',
        '//input[@placeholder="Добавить соавторов"]',
        # Spanish
        'input[placeholder*="Agregar colaboradores" i]',
        'input[placeholder*="Añadir colaboradores" i]',
        'input[aria-label*="colaboradores" i]',
        # Portuguese
        'input[placeholder*="Adicionar colaboradores" i]',
        'input[aria-label*="colaboradores" i]',
    ]

    # Phone verification indicators (RU/EN/ES/PT)
    PHONE_VERIFICATION_INDICATORS = [
        'div:has-text("Подтвердите свой номер телефона")',
        'div:has-text("Введите код подтверждения")',
        'div:has-text("Confirm your phone number")',
        'div:has-text("Enter confirmation code")',
        'input[placeholder*="код" i]',
        'input[placeholder*="code" i]',
        # Spanish
        'div:has-text("Confirma tu número de teléfono")',
        'div:has-text("Introduce el código de confirmación")',
        'input[placeholder*="código" i]',
        # Portuguese
        'div:has-text("Confirme seu número de telefone")',
        'div:has-text("Insira o código de confirmação")',
        'input[placeholder*="código" i]',
    ]

    # Account suspension indicators (RU/EN/ES/PT)
    SUSPENSION_INDICATORS = [
        'div:has-text("Ваш аккаунт заблокирован")',
        'div:has-text("аккаунт приостановлен")',
        'div:has-text("временно заблокирован")',
        'div:has-text("Your account has been disabled")',
        'div:has-text("Account suspended")',
        'div:has-text("temporarily locked")',
        # Spanish
        'div:has-text("Tu cuenta ha sido inhabilitada")',
        'div:has-text("Cuenta suspendida")',
        'div:has-text("bloqueada temporalmente")',
        # Portuguese
        'div:has-text("Sua conta foi desativada")',
        'div:has-text("Conta suspensa")',
        'div:has-text("bloqueada temporariamente")',
    ]

    # Suspension text keywords (used when scanning body text)
    SUSPENSION_TEXT_KEYWORDS = [
        'мы приостановили ваш аккаунт',
        'приостановили ваш аккаунт',
        'аккаунт приостановлен',
        'ваш аккаунт приостановлен',
        'account suspended',
        'account has been suspended',
        'we suspended your account',
        'your account is suspended',
        'your account has been disabled',
        'account disabled',
        'аккаунт заблокирован',
        'ваш аккаунт заблокирован',
        'временно приостановлен',
        'temporarily suspended',
        'осталось',
        'days left'
    ]

    # Email submit buttons (RU/EN/ES/PT)
    EMAIL_SUBMIT_BUTTONS = [
        'button[type="submit"]',
        'button:has-text("Confirm")',
        'button:has-text("Подтвердить")',
        'button:has-text("Confirmar")',
        'div[role="button"]:has-text("Confirm")',
        'div[role="button"]:has-text("Подтвердить")',
        'div[role="button"]:has-text("Confirmar")'
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

    # Broader upload detection indicators (RU/EN/ES/PT)
    UPLOAD_BROAD_INDICATORS = [
        'a[role="link"]:has(svg[aria-label*="Новая публикация"])',
        'a[role="link"]:has(svg[aria-label*="New post"])',
        'a[role="link"]:has(svg[aria-label*="Nueva publicación"])',
        'a[role="link"]:has(svg[aria-label*="Nova publicação"])',
        'a[role="link"]:has(span:has-text("Создать"))',
        'a[role="link"]:has(span:has-text("Create"))',
        'a[role="link"]:has(span:has-text("Crear"))',
        'a[role="link"]:has(span:has-text("Criar"))',
        'button:has(svg[aria-label*="Новая публикация"])',
        'button:has(svg[aria-label*="New post"])',
        'button:has(svg[aria-label*="Nueva publicación"])',
        'button:has(svg[aria-label*="Nova publicação"])',
        'div[role="button"]:has(svg[aria-label*="Новая публикация"])',
        'div[role="button"]:has(svg[aria-label*="New post"])',
        'div[role="button"]:has(svg[aria-label*="Nueva publicación"])',
        'div[role="button"]:has(svg[aria-label*="Nova publicação"])',
        'svg[aria-label*="Новая публикация"]',
        'svg[aria-label*="New post"]',
        'svg[aria-label*="Nueva publicación"]',
        'svg[aria-label*="Nova publicação"]',
        'svg:has(title:has-text("Новая публикация"))',
        'svg:has(title:has-text("New post"))',
        'svg:has(title:has-text("Nueva publicación"))',
        'svg:has(title:has-text("Nova publicação"))',
        'div:has-text("Создать")',
        'div:has-text("Create")',
        'div:has-text("Crear")',
        'div:has-text("Criar")',
        'div:has-text("Публикация")',
        'div:has-text("Post")',
        'div:has-text("Publicación")',
        'div:has-text("Publicação")',
        'div:has-text("Выбрать")',
        'div:has-text("Select")',
        'div:has-text("Seleccionar")',
        'div:has-text("Selecionar")',
        'button:has-text("Выбрать на компьютере")',
        'button:has-text("Select from computer")',
        'button:has-text("Seleccionar desde el ordenador")',
        'button:has-text("Seleccionar desde la computadora")',
        'button:has-text("Selecionar do computador")',
        'button:has-text("Выбрать файлы")',
        'button:has-text("Select files")',
        'button:has-text("Selecionar arquivos")',
        'button:has-text("Seleccionar archivos")',
        'div[role="button"]:has-text("Создать")',
        'div[role="button"]:has-text("Create")',
        'div[role="button"]:has-text("Публикация")',
        'div[role="button"]:has-text("Post")',
        'div[role="button"]:has-text("Publicación")',
        'div[role="button"]:has-text("Publicação")',
        'input[type="file"]',
        'input[accept*="video"]',
        'input[accept*="image"]',
        'input[accept*="mp4"]',
        'input[accept*="quicktime"]',
        'input[multiple]',
        'form[enctype="multipart/form-data"] input[type="file"]',
        'form[method="POST"] input[type="file"]',
    ]

    # Broader upload keyword heuristics for page text scanning
    UPLOAD_KEYWORDS = [
        'выбрать на компьютере', 'select from computer',
        'перетащите', 'drag',
        'выбрать файлы', 'select files',
        'загрузить файл', 'upload file',
        'создать публикацию', 'create post',
        'добавить публикацию', 'add post',
        'добавить фото', 'add photo',
        'добавить видео', 'add video',
        'перетащите сюда', 'drag here',
        'нажмите для выбора', 'click to select',
        'seleccionar desde el ordenador', 'seleccionar desde la computadora',
        'seleccionar desde el dispositivo',
        'arrastra', 'arrastre', 'arrastrar',
        'seleccionar archivos', 'subir archivo', 'subir archivos',
        'crear publicación', 'añadir publicación',
        'añadir фото', 'añadir video', 'agregar foto', 'agregar video',
        'arrastra aquí', 'haz clic para seleccionar',
        'selecionar do computador', 'selecionar do dispositivo',
        'arrastar', 'arraste',
        'selecionar arquivos', 'enviar arquivo', 'enviar arquivos',
        'criar publicação', 'adicionar publicação',
        'adicionar фото', 'adicionar vídeo',
        'arraste aqui', 'clique para selecionar'
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
        
        # Spanish/Portuguese accept variants
        'button:has-text("Aceptar todas")',
        'button:has-text("Aceptar todas las cookies")',
        'button:has-text("Aceptar")',
        'div[role="button"]:has-text("Aceptar todas")',
        'div[role="button"]:has-text("Aceptar")',
        'button:has-text("Aceitar todas")',
        'button:has-text("Aceitar todos os cookies")',
        'button:has-text("Aceitar")',
        'div[role="button"]:has-text("Aceitar todas")',
        'div[role="button"]:has-text("Aceitar")',
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
        # Spanish/Portuguese decline variants
        'button:has-text("Rechazar")',
        'button:has-text("Rechazar cookies opcionales")',
        'button:has-text("Rechazar opcionales")',
        'button:has-text("Recusar")',
        'button:has-text("Recusar cookies opcionais")',
        'button:has-text("Recusar opcionais")',
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
        from .logging_utils import log_info, log_warning
        
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