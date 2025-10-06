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
        # Spanish/Portuguese high-priority
        'a[role="link"]:has(svg[aria-label*="Nueva publicación"])',
        'a[role="link"]:has(span:has-text("Crear"))',
        'a[role="link"]:has(svg[aria-label*="Nova publicação"])',
        'a[role="link"]:has(span:has-text("Criar"))',
        # German high-priority
        'a[role="link"]:has(svg[aria-label*="Neuer Beitrag"])',
        'a[role="link"]:has(span:has-text("Erstellen"))',
        # Greek high-priority
        'a[role="link"]:has(svg[aria-label*="Νέα δημοσίευση"])',
        'a[role="link"]:has(span:has-text("Δημιουργία"))',
        'button:has(svg[aria-label*="Новая публикация"])',
        'button:has(svg[aria-label*="New post"])',
        'button:has(svg[aria-label*="Nueva publicación"])',
        'button:has(svg[aria-label*="Nova publicação"])',
        'div[role="button"]:has(svg[aria-label*="Новая публикация"])',
        'div[role="button"]:has(svg[aria-label*="New post"])',
        'div[role="button"]:has(svg[aria-label*="Nueva publicación"])',
        'div[role="button"]:has(svg[aria-label*="Nova publicação"])',
        'svg:has(title:has-text("Новая публикация"))',
        'svg:has(title:has-text("New post"))',
        'svg:has(title:has-text("Nueva publicación"))',
        'svg:has(title:has-text("Nova publicação"))',
        
        # [TARGET] ПРИОРИТЕТ 1: Семантические атрибуты (самые устойчивые)
        'svg[aria-label="Новая публикация"]',
        'svg[aria-label*="Новая публикация"]',
        'svg[aria-label*="New post"]',
        'svg[aria-label*="Create"]',
        'svg[aria-label*="Создать"]',
        'svg[aria-label*="Nueva publicación"]',
        'svg[aria-label*="Nova publicação"]',
        'svg[aria-label*="Crear"]',
        'svg[aria-label*="Criar"]',
        'svg[aria-label*="Neuer Beitrag"]',
        'svg[aria-label*="Erstellen"]',
        'svg[aria-label*="Νέα δημοσίευση"]',
        'svg[aria-label*="Δημιουργία"]',
        
        # [TARGET] ПРИОРИТЕТ 2: Родительские элементы с семантическими SVG
        'a:has(svg[aria-label="Новая публикация"])',
        'button:has(svg[aria-label="Новая публикация"])',
        'div[role="button"]:has(svg[aria-label="Новая публикация"])',
        'a:has(svg[aria-label*="New post"])',
        'button:has(svg[aria-label*="New post"])',
        'div[role="button"]:has(svg[aria-label*="New post"])',
        'a:has(svg[aria-label*="Nueva publicación"])',
        'button:has(svg[aria-label*="Nueva publicación"])',
        'div[role="button"]:has(svg[aria-label*="Nueva publicación"])',
        'a:has(svg[aria-label*="Nova publicação"])',
        'button:has(svg[aria-label*="Nova publicação"])',
        'div[role="button"]:has(svg[aria-label*="Nova publicação"])',
        
        # [TARGET] ПРИОРИТЕТ 3: Текстовые селекторы
        'span:has-text("Создать")',
        'a:has(span:has-text("Создать"))',
        'div[role="button"]:has-text("Создать")',
        'button:has-text("Создать")',
        'span:has-text("Create")',
        'a:has(span:has-text("Create"))',
        'div[role="button"]:has-text("Create")',
        'button:has-text("Create")',
        'span:has-text("Crear")',
        'a:has(span:has-text("Crear"))',
        'div[role="button"]:has-text("Crear")',
        'button:has-text("Crear")',
        'span:has-text("Criar")',
        'a:has(span:has-text("Criar"))',
        'div[role="button"]:has-text("Criar")',
        'button:has-text("Criar")',
        'span:has-text("Erstellen")',
        'a:has(span:has-text("Erstellen"))',
        'div[role="button"]:has-text("Erstellen")',
        'button:has-text("Erstellen")',
        'span:has-text("Δημιουργία")',
        'a:has(span:has-text("Δημιουργία"))',
        'div[role="button"]:has-text("Δημιουργία")',
        'button:has-text("Δημιουργία")',
        
        # [TARGET] ПРИОРИТЕТ 4: XPath семантические
        '//svg[@aria-label="Новая публикация"]',
        '//svg[contains(@aria-label, "Новая публикация")]',
        '//svg[contains(@aria-label, "New post")]',
        '//svg[contains(@aria-label, "Create")]',
        '//svg[contains(@aria-label, "Создать")]',
        '//svg[contains(@aria-label, "Nueva publicación")]',
        '//svg[contains(@aria-label, "Nova publicação")]',
        '//svg[contains(@aria-label, "Crear")]',
        '//svg[contains(@aria-label, "Criar")]',
        '//svg[contains(@aria-label, "Neuer Beitrag")]',
        '//svg[contains(@aria-label, "Erstellen")]',
        '//svg[contains(@aria-label, "Νέα δημοσίευση")]',
        '//svg[contains(@aria-label, "Δημιουργία")]',
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
        '//span[contains(text(), "Crear")]',
        '//a[.//span[contains(text(), "Crear")]]',
        '//div[@role="button" and contains(text(), "Crear")]',
        '//button[contains(text(), "Crear")]',
        '//span[contains(text(), "Criar")]',
        '//a[.//span[contains(text(), "Criar")]]',
        '//div[@role="button" and contains(text(), "Criar")]',
        '//button[contains(text(), "Criar")]',
        '//span[contains(text(), "Erstellen")]',
        '//a[.//span[contains(text(), "Erstellen")]]',
        '//div[@role="button" and contains(text(), "Erstellen")]',
        '//button[contains(text(), "Erstellen")]',
        '//span[contains(text(), "Δημιουργία")]',
        '//a[.//span[contains(text(), "Δημιουργία")]]',
        '//div[@role="button" and contains(text(), "Δημιουργία")]',
        '//button[contains(text(), "Δημιουργία")]',
        
        # [TARGET] ПРИОРИТЕТ 6: Универсальные aria-label
        '[aria-label*="Создать"]',
        '[aria-label*="Новая публикация"]',
        '[aria-label*="Create"]',
        '[aria-label*="New post"]',
        '[aria-label*="Nueva publicación"]',
        '[aria-label*="Nova publicação"]',
        '[aria-label*="Crear"]',
        '[aria-label*="Criar"]',
        '[aria-label*="Neuer Beitrag"]',
        '[aria-label*="Erstellen"]',
        '[aria-label*="Νέα δημοσίευση"]',
        '[aria-label*="Δημιουργία"]',
        'button[aria-label*="Создать"]',
        'button[aria-label*="Create"]',
        'button[aria-label*="Crear"]',
        'button[aria-label*="Criar"]',
        'button[aria-label*="Erstellen"]',
        'button[aria-label*="Δημιουργία"]',
        'a[aria-label*="Создать"]',
        'a[aria-label*="Create"]',
        'a[aria-label*="Crear"]',
        'a[aria-label*="Criar"]',
        'a[aria-label*="Erstellen"]',
        'a[aria-label*="Δημιουργία"]',
    ]
    
    # Post option selectors - SEMANTIC APPROACH
    POST_OPTION = [
        # [TARGET] ПРИОРИТЕТ 1: Семантические SVG селекторы
        'svg[aria-label="Публикация"]',
        'svg[aria-label*="Публикация"]',
        'svg[aria-label*="Post"]',
        'svg[aria-label="Post"]',
        'svg[aria-label*="Beitrag"]',
        'svg[aria-label="Beitrag"]',
        'svg[aria-label*="Δημοσίευση"]',
        'svg[aria-label="Δημοσίευση"]',
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
        'span:has-text("Beitrag")',
        'span:has-text("Δημοσίευση")',
        
        # [TARGET] ПРИОРИТЕТ 3: XPath семантические
        '//svg[@aria-label="Публикация"]',
        '//svg[contains(@aria-label, "Публикация")]',
        '//svg[contains(@aria-label, "Post")]',
        '//svg[@aria-label="Post"]',
        '//svg[contains(@aria-label, "Beitrag")]',
        '//svg[@aria-label="Beitrag"]',
        '//svg[contains(@aria-label, "Δημοσίευση")]',
        '//svg[@aria-label="Δημοσίευση"]',
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
        '//span[text()="Beitrag"]',
        '//span[text()="Δημοσίευση"]',
        
        # [TARGET] ПРИОРИТЕТ 5: Универсальные
        '[aria-label*="Публикация"]',
        '[aria-label*="Post"]',
        '[aria-label*="Beitrag"]',
        '[aria-label*="Δημοσίευση"]',
        'button[aria-label*="Публикация"]',
        'button[aria-label*="Post"]',
        'button[aria-label*="Beitrag"]',
        'button[aria-label*="Δημοσίευση"]',
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
        # German file selection buttons
        'button:has-text("Vom Computer auswählen")',
        'div[role="button"]:has-text("Vom Computer auswählen")',
        'button:has-text("Dateien auswählen")',
        'div[role="button"]:has-text("Dateien auswählen")',
        'button:has-text("Vom Gerät auswählen")',
        'div[role="button"]:has-text("Vom Gerät auswählen")',
        # Greek file selection buttons
        'button:has-text("Επιλογή από τον υπολογιστή")',
        'div[role="button"]:has-text("Επιλογή από τον υπολογιστή")',
        'button:has-text("Επιλογή αρχείων")',
        'div[role="button"]:has-text("Επιλογή αρχείων")',
        'button:has-text("Επιλογή από τη συσκευή")',
        'div[role="button"]:has-text("Επιλογή από τη συσκευή")',
        
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
        # German XPath selectors
        '//button[contains(text(), "Vom Computer auswählen")]',
        '//div[@role="button" and contains(text(), "Vom Computer auswählen")]',
        '//button[contains(text(), "Dateien auswählen")]',
        '//div[@role="button" and contains(text(), "Dateien auswählen")]',
        '//button[contains(text(), "Vom Gerät auswählen")]',
        '//div[@role="button" and contains(text(), "Vom Gerät auswählen")]',
        # Greek XPath selectors
        '//button[contains(text(), "Επιλογή από τον υπολογιστή")]',
        '//div[@role="button" and contains(text(), "Επιλογή από τον υπολογιστή")]',
        '//button[contains(text(), "Επιλογή αρχείων")]',
        '//div[@role="button" and contains(text(), "Επιλογή αρχείων")]',
        '//button[contains(text(), "Επιλογή από τη συσκευή")]',
        '//div[@role="button" and contains(text(), "Επιλογή από τη συσκευή")]',
        
        # [TARGET] ПРИОРИТЕТ 6: Aria-label семантические
        'button[aria-label*="Выбрать"]',
        'button[aria-label*="Select"]',
        'button[aria-label*="Choose"]',
        'button[aria-label*="Auswählen"]',
        'button[aria-label*="Επιλογή"]',
        '[aria-label*="Выбрать файл"]',
        '[aria-label*="Select file"]',
        '[aria-label*="Choose file"]',
        '[aria-label*="Datei auswählen"]',
        '[aria-label*="Επιλογή αρχείου"]',
        
        # [TARGET] ПРИОРИТЕТ 7: Drag and drop области
        'div:has-text("Перетащите фото и видео сюда")',
        'div:has-text("Drag photos and videos here")',
        'div:has-text("Ziehen Sie Fotos und Videos hierher")',
        'div:has-text("Σύρετε φωτογραφίες και βίντεο εδώ")',
        'div[role="button"]:has-text("Перетащите")',
        'div[role="button"]:has-text("Drag")',
        'div[role="button"]:has-text("Ziehen")',
        'div[role="button"]:has-text("Σύρετε")',
        
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
        'button:has-text("Accept")',
        'div[role="button"]:has-text("Accept")',
        'button:has-text("Принять")',
        'div[role="button"]:has-text("Принять")',
        # German accept buttons
        'button:has-text("Akzeptieren")',
        'div[role="button"]:has-text("Akzeptieren")',
        'button:has-text("Alle akzeptieren")',
        'div[role="button"]:has-text("Alle akzeptieren")',
        # Greek accept buttons
        'button:has-text("Αποδοχή")',
        'div[role="button"]:has-text("Αποδοχή")',
        'button:has-text("Αποδοχή όλων")',
        'div[role="button"]:has-text("Αποδοχή όλων")',
    ]
    
    # Reels dialog specific accept buttons (more specific than OK_ACCEPT_BUTTONS)
    REELS_DIALOG_ACCEPT_BUTTONS = [
        # Высокоприоритетные текстовые селекторы
        'button:has-text("Aceptar")',
        'div[role="button"]:has-text("Aceptar")',
        'button:has-text("Aceitar")',
        'div[role="button"]:has-text("Aceitar")',
        'button:has-text("OK")',
        'button:has-text("ОК")',
        'div[role="button"]:has-text("OK")',
        'div[role="button"]:has-text("ОК")',
        # German Reels dialog accept buttons
        'button:has-text("Akzeptieren")',
        'div[role="button"]:has-text("Akzeptieren")',
        # Greek Reels dialog accept buttons
        'button:has-text("Αποδοχή")',
        'div[role="button"]:has-text("Αποδοχή")',
        # Селекторы внутри диалога Reels
        'div[role="dialog"] button:last-child',
        'div[role="dialog"] div[role="button"]:last-child',
        # XPath для более точного поиска
        '//div[@role="dialog"]//button[contains(text(), "Aceptar")]',
        '//div[@role="dialog"]//button[contains(text(), "Aceitar")]',
        '//div[@role="dialog"]//button[contains(text(), "OK")]',
        '//div[@role="dialog"]//button[contains(text(), "ОК")]',
        # German XPath for Reels dialog
        '//div[@role="dialog"]//button[contains(text(), "Akzeptieren")]',
        # Greek XPath for Reels dialog
        '//div[@role="dialog"]//button[contains(text(), "Αποδοχή")]',
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
        # German next buttons
        'button:has-text("Weiter")',
        'div[role="button"]:has-text("Weiter")',
        'button:has-text("Fortfahren")',
        'div[role="button"]:has-text("Fortfahren")',
        # Greek next buttons
        'button:has-text("Επόμενο")',
        'div[role="button"]:has-text("Επόμενο")',
        'button:has-text("Συνέχεια")',
        'div[role="button"]:has-text("Συνέχεια")',
        
        # [TARGET] ПРИОРИТЕТ 2: XPath текстовые
        '//button[contains(text(), "Далее")]',
        '//button[contains(text(), "Next")]',
        '//button[contains(text(), "Продолжить")]',
        '//button[contains(text(), "Continue")]',
        '//div[@role="button" and contains(text(), "Далее")]',
        '//div[@role="button" and contains(text(), "Next")]',
        # German XPath next buttons
        '//button[contains(text(), "Weiter")]',
        '//button[contains(text(), "Fortfahren")]',
        '//div[@role="button" and contains(text(), "Weiter")]',
        '//div[@role="button" and contains(text(), "Fortfahren")]',
        # Greek XPath next buttons
        '//button[contains(text(), "Επόμενο")]',
        '//button[contains(text(), "Συνέχεια")]',
        '//div[@role="button" and contains(text(), "Επόμενο")]',
        '//div[@role="button" and contains(text(), "Συνέχεια")]',
        
        # [TARGET] ПРИОРИТЕТ 3: Aria-label
        'button[aria-label*="Далее"]',
        'button[aria-label*="Next"]',
        'button[aria-label*="Продолжить"]',
        'button[aria-label*="Continue"]',
        'button[aria-label*="Weiter"]',
        'button[aria-label*="Fortfahren"]',
        'button[aria-label*="Επόμενο"]',
        'button[aria-label*="Συνέχεια"]',
        '[role="button"][aria-label*="Далее"]',
        '[role="button"][aria-label*="Next"]',
        '[role="button"][aria-label*="Weiter"]',
        '[role="button"][aria-label*="Επόμενο"]',
        
        # [TARGET] ПРИОРИТЕТ 4: Универсальные роли
        '[role="button"]:has-text("Далее")',
        '[role="button"][tabindex="0"]:has-text("Далее")',
        '[role="button"]:has-text("Next")',
        '[role="button"][tabindex="0"]:has-text("Next")',
        '[role="button"]:has-text("Weiter")',
        '[role="button"][tabindex="0"]:has-text("Weiter")',
        '[role="button"]:has-text("Επόμενο")',
        '[role="button"][tabindex="0"]:has-text("Επόμενο")',
    ]

    # Keywords to validate Next/Continue buttons by text content (lowercase)
    NEXT_BUTTON_KEYWORDS = [
        'далее', 'продолжить',
        'next', 'continue',
        'siguiente', 'continuar',
        'avançar',
        'weiter', 'fortfahren',
        'επόμενο', 'συνέχεια'
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
        # German share buttons
        'button:has-text("Teilen")',
        'div[role="button"]:has-text("Teilen")',
        'button:has-text("Veröffentlichen")',
        'div[role="button"]:has-text("Veröffentlichen")',
        # Greek share buttons
        'button:has-text("Κοινοποίηση")',
        'div[role="button"]:has-text("Κοινοποίηση")',
        'button:has-text("Δημοσίευση")',
        'div[role="button"]:has-text("Δημοσίευση")',
        
        # [TARGET] ПРИОРИТЕТ 2: XPath текстовые
        '//button[contains(text(), "Поделиться")]',
        '//button[contains(text(), "Share")]',
        '//button[contains(text(), "Опубликовать")]',
        '//button[contains(text(), "Post")]',
        '//div[@role="button" and contains(text(), "Поделиться")]',
        '//div[@role="button" and contains(text(), "Share")]',
        # German XPath share buttons
        '//button[contains(text(), "Teilen")]',
        '//button[contains(text(), "Veröffentlichen")]',
        '//div[@role="button" and contains(text(), "Teilen")]',
        '//div[@role="button" and contains(text(), "Veröffentlichen")]',
        # Greek XPath share buttons
        '//button[contains(text(), "Κοινοποίηση")]',
        '//button[contains(text(), "Δημοσίευση")]',
        '//div[@role="button" and contains(text(), "Κοινοποίηση")]',
        '//div[@role="button" and contains(text(), "Δημοσίευση")]',
        
        # [TARGET] ПРИОРИТЕТ 3: Aria-label
        'button[aria-label*="Поделиться"]',
        'button[aria-label*="Share"]',
        'button[aria-label*="Опубликовать"]',
        'button[aria-label*="Post"]',
        'button[aria-label*="Teilen"]',
        'button[aria-label*="Veröffentlichen"]',
        'button[aria-label*="Κοινοποίηση"]',
        'button[aria-label*="Δημοσίευση"]',
        '[role="button"][aria-label*="Поделиться"]',
        '[role="button"][aria-label*="Share"]',
        '[role="button"][aria-label*="Teilen"]',
        '[role="button"][aria-label*="Κοινοποίηση"]',
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
        # German done buttons
        '//div[text()="Fertig"]',
        'div[role="button"]:has-text("Fertig")',
        'button:has-text("Fertig")',
        'div[aria-label*="Fertig"]',
        'button[aria-label*="Fertig"]',
        # Greek done buttons
        '//div[text()="Τέλος"]',
        'div[role="button"]:has-text("Τέλος")',
        'button:has-text("Τέλος")',
        'div[aria-label*="Τέλος"]',
        'button[aria-label*="Τέλος"]',
    ]
    
    # Caption textarea selectors - SEMANTIC APPROACH (multilingual)
    CAPTION_TEXTAREA = [
        # [TARGET] ПРИОРИТЕТ 1: Семантические aria-label (все языки)
        'textarea[aria-label*="Напишите подпись"]',
        'textarea[aria-label*="Write a caption"]',
        'textarea[aria-label*="подпись"]',
        'textarea[aria-label*="caption"]',
        'textarea[aria-label*="Escribe una descripción"]',
        'textarea[aria-label*="descripción"]',
        'textarea[aria-label*="Escreva uma descrição"]',
        'textarea[aria-label*="descrição"]',
        # German caption textarea
        'textarea[aria-label*="Schreibe eine Bildunterschrift"]',
        'textarea[aria-label*="Bildunterschrift"]',
        'textarea[aria-label*="Beschreibung"]',
        # Greek caption textarea
        'textarea[aria-label*="Γράψτε μια λεζάντα"]',
        'textarea[aria-label*="λεζάντα"]',
        'textarea[aria-label*="περιγραφή"]',
        
        # [TARGET] ПРИОРИТЕТ 2: Contenteditable div (все языки)
        'div[contenteditable="true"][aria-label*="подпись"]',
        'div[contenteditable="true"][aria-label*="caption"]',
        'div[contenteditable="true"][aria-label*="Escribe una descripción"]',
        'div[contenteditable="true"][aria-label*="descripción"]',
        'div[contenteditable="true"][aria-label*="Escreva uma descrição"]',
        'div[contenteditable="true"][aria-label*="descrição"]',
        # German contenteditable div
        'div[contenteditable="true"][aria-label*="Schreibe eine Bildunterschrift"]',
        'div[contenteditable="true"][aria-label*="Bildunterschrift"]',
        'div[contenteditable="true"][aria-label*="Beschreibung"]',
        # Greek contenteditable div
        'div[contenteditable="true"][aria-label*="Γράψτε μια λεζάντα"]',
        'div[contenteditable="true"][aria-label*="λεζάντα"]',
        'div[contenteditable="true"][aria-label*="περιγραφή"]',
        
        # [TARGET] ПРИОРИТЕТ 3: Placeholder атрибуты
        'textarea[placeholder*="Напишите подпись"]',
        'textarea[placeholder*="Write a caption"]',
        'textarea[placeholder*="подпись"]',
        'textarea[placeholder*="caption"]',
        'div[contenteditable="true"][placeholder*="подпись"]',
        'div[contenteditable="true"][placeholder*="caption"]',
        'div[contenteditable="true"][placeholder*="descripción"]',
        'div[contenteditable="true"][placeholder*="descrição"]',
        # German placeholder attributes
        'textarea[placeholder*="Schreibe eine Bildunterschrift"]',
        'textarea[placeholder*="Bildunterschrift"]',
        'div[contenteditable="true"][placeholder*="Bildunterschrift"]',
        # Greek placeholder attributes
        'textarea[placeholder*="Γράψτε μια λεζάντα"]',
        'textarea[placeholder*="λεζάντα"]',
        'div[contenteditable="true"][placeholder*="λεζάντα"]',
        
        # [TARGET] ПРИОРИТЕТ 4: Дополнительные испанские/португальские варианты
        'textarea[aria-label*="Escribe un pie de foto"]',
        'textarea[placeholder*="Escribe un pie de foto"]',
        'textarea[aria-label*="Escreva uma legenda"]',
        'textarea[placeholder*="Escreva uma legenda"]',
        # German additional variants
        'textarea[aria-label*="Schreibe eine Legende"]',
        'textarea[placeholder*="Schreibe eine Legende"]',
        # Greek additional variants
        'textarea[aria-label*="Γράψτε μια επιγραφή"]',
        'textarea[placeholder*="Γράψτε μια επιγραφή"]',
        
        # [TARGET] ПРИОРИТЕТ 5: XPath (все языки)
        '//textarea[contains(@aria-label, "подпись")]',
        '//textarea[contains(@aria-label, "caption")]',
        '//textarea[contains(@aria-label, "descripción")]',
        '//textarea[contains(@aria-label, "descrição")]',
        '//div[@contenteditable="true" and contains(@aria-label, "подпись")]',
        '//div[@contenteditable="true" and contains(@aria-label, "caption")]',
        '//div[@contenteditable="true" and contains(@aria-label, "descripción")]',
        '//div[@contenteditable="true" and contains(@aria-label, "descrição")]',
        # German XPath selectors
        '//textarea[contains(@aria-label, "Bildunterschrift")]',
        '//textarea[contains(@aria-label, "Beschreibung")]',
        '//div[@contenteditable="true" and contains(@aria-label, "Bildunterschrift")]',
        '//div[@contenteditable="true" and contains(@aria-label, "Beschreibung")]',
        # Greek XPath selectors
        '//textarea[contains(@aria-label, "λεζάντα")]',
        '//textarea[contains(@aria-label, "περιγραφή")]',
        '//div[@contenteditable="true" and contains(@aria-label, "λεζάντα")]',
        '//div[@contenteditable="true" and contains(@aria-label, "περιγραφή")]',
        
        # [TARGET] ПРИОРИТЕТ 6: Роль textbox (универсальный)
        'div[role="textbox"][contenteditable="true"]',
        '[role="textbox"][contenteditable="true"]',
        
        # [TARGET] ПРИОРИТЕТ 7: Специфичные селекторы для новых интерфейсов
        'div[contenteditable="true"][data-lexical-editor="true"]',
        'div[contenteditable="true"][spellcheck="true"]',
        'div[contenteditable="true"][tabindex="0"]',
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
            # German login buttons
            'button:has-text("Anmelden")',
            'div[role="button"]:has-text("Anmelden")',
            # Greek login buttons
            'button:has-text("Σύνδεση")',
            'div[role="button"]:has-text("Σύνδεση")',
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
        # German 2FA input
        'input[aria-label*="Code" i]',
        'input[placeholder*="Code" i]',
        # Greek 2FA input
        'input[aria-label*="κωδικός" i]',
        'input[placeholder*="κωδικός" i]',
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
        'div:has-text("Seu reel foi compartilhado")',
        'div:has-text("Seu reel foi compartilhado.")',
        'div:has-text("Reels compartilhados")',
        'div[role="dialog"][aria-label*="Post compartilhado" i]',
        '[role="dialog"][aria-label*="Post compartilhado" i]',
        # German success messages
        'div:has-text("Ihr Beitrag wurde geteilt")',
        'div:has-text("Beitrag geteilt")',
        'div:has-text("Video veröffentlicht")',
        'div:has-text("Erfolgreich veröffentlicht")',
        # Greek success messages
        'div:has-text("Η δημοσίευσή σας κοινοποιήθηκε")',
        'div:has-text("Δημοσίευση κοινοποιήθηκε")',
        'div:has-text("Βίντεο δημοσιεύτηκε")',
        'div:has-text("Δημοσιεύτηκε επιτυχώς")',
        
        # XPath selectors for success messages
        '//div[contains(text(), "Ваша публикация опубликована")]',
        '//div[contains(text(), "Публикация опубликована")]',
        '//div[contains(text(), "Видео опубликовано")]',
        '//div[contains(text(), "Your post has been shared")]',
        '//div[contains(text(), "Post shared")]',
        '//div[contains(text(), "Seu reel foi compartilhado")]',
        '//div[contains(text(), "Reels compartilhados")]',
        '//*[@role="dialog" and contains(@aria-label, "Post compartilhado")]',
        # German XPath success messages
        '//div[contains(text(), "Ihr Beitrag wurde geteilt")]',
        '//div[contains(text(), "Beitrag geteilt")]',
        '//div[contains(text(), "Video veröffentlicht")]',
        # Greek XPath success messages
        '//div[contains(text(), "Η δημοσίευσή σας κοινοποιήθηκε")]',
        '//div[contains(text(), "Δημοσίευση κοινοποιήθηκε")]',
        '//div[contains(text(), "Βίντεο δημοσιεύτηκε")]',
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
        # German error messages
        'div:has-text("Fehler")',
        'div:has-text("Fehlgeschlagen")',
        'div:has-text("Etwas ist schiefgelaufen")',
        # Greek error messages
        'div:has-text("Σφάλμα")',
        'div:has-text("Αποτυχία")',
        'div:has-text("Κάτι πήγε στραβά")',
    ]

    # Reels dialog detection selectors (RU/EN/ES/PT)
    REELS_DIALOG_SELECTORS = [
        'div:has(h2:has-text("Теперь видеопубликациями можно делиться как видео Reels"))',
        'div:has(h2:has-text("Now video publications can be shared as Reels videos"))',
        'div:has(h2:has-text("Ahora las publicaciones de video se pueden compartir como Reels"))',
        'div:has(h2:has-text("Las publicaciones con video ahora se comparten como reels"))',
        'div:has(h2:has-text("Agora as publicações de vídeo podem ser compartilhadas como Reels"))',
        # German Reels dialog
        'div:has(h2:has-text("Video-Beiträge können jetzt als Reels-Videos geteilt werden"))',
        'div:has(h2:has-text("Reels-Videos"))',
        # Greek Reels dialog
        'div:has(h2:has-text("Τα βίντεο δημοσιεύσεις μπορούν τώρα να κοινοποιηθούν ως βίντεο Reels"))',
        'div:has(h2:has-text("βίντεο Reels"))',
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
        # German span texts
        'div:has(span:has-text("Video-Beiträge können jetzt"))',
        'div:has(span:has-text("öffentliches Konto"))',
        'div:has(span:has-text("Reels-Videos erstellen"))',
        'div:has(span:has-text("Audiospur"))',
        'div:has(span:has-text("Remix erstellen"))',
        # Greek span texts
        'div:has(span:has-text("Τα βίντεο δημοσιεύσεις μπορούν τώρα"))',
        'div:has(span:has-text("δημόσιος λογαριασμός"))',
        'div:has(span:has-text("δημιουργία βίντεο Reels"))',
        'div:has(span:has-text("ήχος"))',
        'div:has(span:has-text("δημιουργία remix"))',
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
        'div[role="dialog"]:has-text("видео")',
        'div[role="dialog"]:has-text("Теперь")',
        'div[role="dialog"]:has-text("Now")',
        'div[role="dialog"]:has-text("Las publicaciones con video")',
        'div[role="dialog"]:has-text("ahora se comparten como reels")',
        'div[role="dialog"]:has-text("As publicações de vídeo")',
        'div[role="dialog"]:has-text("agora são compartilhadas como reels")',
        # German dialog texts
        'div[role="dialog"]:has-text("Video-Beiträge können jetzt")',
        'div[role="dialog"]:has-text("als Reels-Videos geteilt werden")',
        # Greek dialog texts
        'div[role="dialog"]:has-text("Τα βίντεο δημοσιεύσεις μπορούν τώρα")',
        'div[role="dialog"]:has-text("να κοινοποιηθούν ως βίντεο Reels")',
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
        'div[aria-label*="Crear"]',
        'div[aria-label*="Criar"]',
        'div[aria-label*="Erstellen"]',
        'div[aria-label*="Δημιουργία"]',
        'div[aria-label*="Publicar"]',
        'div[aria-label*="Publicação"]',
        'textarea[aria-label*="подпись"]',
        'textarea[aria-label*="caption"]',
        'textarea[aria-label*="Escribe un pie de foto"]',
        'textarea[aria-label*="Escreva uma legenda"]',
        'textarea[aria-label*="Schreibe eine Bildunterschrift"]',
        'textarea[aria-label*="Γράψτε μια λεζάντα"]',
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
        # German location input
        'input[placeholder*="Ort hinzufügen" i]',
        'input[aria-label*="Ort" i]',
        'input[placeholder*="Standort hinzufügen" i]',
        'input[aria-label*="Standort" i]',
        # Greek location input
        'input[placeholder*="Προσθήκη τοποθεσίας" i]',
        'input[aria-label*="τοποθεσία" i]',
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
        # German mentions input
        'input[placeholder*="Mitwirkende hinzufügen" i]',
        'input[aria-label*="Mitwirkende" i]',
        'input[placeholder*="Kollaborateure hinzufügen" i]',
        'input[aria-label*="Kollaborateure" i]',
        # Greek mentions input
        'input[placeholder*="Προσθήκη συνεργατών" i]',
        'input[aria-label*="συνεργάτες" i]',
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
        # German phone verification
        'div:has-text("Bestätigen Sie Ihre Telefonnummer")',
        'div:has-text("Geben Sie den Bestätigungscode ein")',
        'input[placeholder*="Code" i]',
        # Greek phone verification
        'div:has-text("Επιβεβαιώστε τον αριθμό τηλεφώνου σας")',
        'div:has-text("Εισάγετε τον κωδικό επιβεβαίωσης")',
        'input[placeholder*="κωδικός" i]',
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
        # German suspension indicators
        'div:has-text("Ihr Konto wurde deaktiviert")',
        'div:has-text("Konto gesperrt")',
        'div:has-text("temporär gesperrt")',
        # Greek suspension indicators
        'div:has-text("Ο λογαριασμός σας έχει απενεργοποιηθεί")',
        'div:has-text("Λογαριασμός ανασταλμένος")',
        'div:has-text("προσωρινά κλειδωμένος")',
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
        'days left',
        # German suspension keywords
        'wir haben ihr konto gesperrt',
        'konto gesperrt',
        'konto wurde gesperrt',
        'ihr konto ist gesperrt',
        'konto deaktiviert',
        'temporär gesperrt',
        'verbleibende',
        'tage verbleibend',
        # Greek suspension keywords
        'έχουμε αναστείλει τον λογαριασμό σας',
        'λογαριασμός ανασταλμένος',
        'ο λογαριασμός σας είναι ανασταλμένος',
        'λογαριασμός απενεργοποιημένος',
        'προσωρινά ανασταλμένος',
        'απομένουν',
        'ημέρες απομένουν'
    ]
    
    # Reels dialog detection keywords (multilingual)
    REELS_DIALOG_KEYWORDS = [
        'Reels', 'видео', 'Теперь', 'Now', 'общедоступный', 'public',
        'Las publicaciones con video', 'ahora se comparten como reels',
        'As publicações de vídeo', 'agora são compartilhadas como reels',
        'Tu cuenta es pública', 'Sua conta é pública',
        # German Reels dialog keywords
        'Video-Beiträge', 'Reels-Videos', 'öffentliches Konto', 'Audiospur', 'Remix',
        # Greek Reels dialog keywords
        'βίντεο δημοσιεύσεις', 'βίντεο Reels', 'δημόσιος λογαριασμός', 'ήχος', 'remix'
    ]
    
    # Accept button keywords (multilingual)
    ACCEPT_BUTTON_KEYWORDS = [
        'OK', 'ОК', 'Aceptar', 'Aceitar', 'Accept', 'Принять',
        'Akzeptieren', 'Αποδοχή'
    ]

    # Email submit buttons (RU/EN/ES/PT)
    EMAIL_SUBMIT_BUTTONS = [
        'button[type="submit"]',
        'button:has-text("Confirm")',
        'button:has-text("Подтвердить")',
        'button:has-text("Confirmar")',
        'div[role="button"]:has-text("Confirm")',
        'div[role="button"]:has-text("Подтвердить")',
        'div[role="button"]:has-text("Confirmar")',
        # German email submit buttons
        'button:has-text("Bestätigen")',
        'div[role="button"]:has-text("Bestätigen")',
        # Greek email submit buttons
        'button:has-text("Επιβεβαίωση")',
        'div[role="button"]:has-text("Επιβεβαίωση")'
    ]
    
    # Crop page indicators (multilingual)
    CROP_PAGE_INDICATORS = [
        # Text-based selectors for all languages
        'button:has-text("Оригинал")',
        'button:has-text("Original")',
        'button:has-text("Original")',  # Spanish uses same word
        'button:has-text("Original")',  # Portuguese uses same word
        'div[role="button"]:has-text("Оригинал")',
        'div[role="button"]:has-text("Original")',
        'span:has-text("Original")',
        'span:has-text("Оригинал")',
        # SVG aria-labels for crop (multilingual)
        'svg[aria-label*="Выбрать размер"]',
        'svg[aria-label*="Select crop"]',
        'svg[aria-label*="Seleccionar recorte"]',
        'svg[aria-label*="Selecionar corte"]',
        'svg[aria-label*="Crop"]',
        'svg[aria-label*="обрезать"]',
        'svg[aria-label*="recorte"]',
        'svg[aria-label*="corte"]',
        # German crop SVG aria-labels
        'svg[aria-label*="Zuschnitt auswählen"]',
        'svg[aria-label*="Zuschnitt"]',
        'svg[aria-label*="beschneiden"]',
        # Greek crop SVG aria-labels
        'svg[aria-label*="Επιλογή περικοπής"]',
        'svg[aria-label*="περικοπή"]',
        'svg[aria-label*="κόψιμο"]',
        # Crop option indicators
        'span:has-text("1:1")',
        'span:has-text("9:16")',
        'span:has-text("16:9")',
        # SVG titles for crop icons
        'svg[title*="recorte"]',
        'svg[title*="crop"]',
        'svg[title*="обрезать"]',
        # German SVG titles for crop
        'svg[title*="Zuschnitt"]',
        'svg[title*="beschneiden"]',
        # Greek SVG titles for crop
        'svg[title*="περικοπή"]',
        'svg[title*="κόψιμο"]',
    ]
    
    # Original crop button selectors (multilingual, prioritized)
    CROP_ORIGINAL_SELECTORS = [
        # High priority: direct span text (all languages)
        'span:has-text("Original")',
        'span:has-text("Оригинал")',
        # Medium priority: clickable elements with text
        'button:has-text("Original")',
        'button:has-text("Оригинал")',
        'div[role="button"]:has-text("Original")',
        'div[role="button"]:has-text("Оригинал")',
        # Lower priority: parent elements containing text
        'div:has(span:has-text("Original"))',
        'div:has(span:has-text("Оригинал"))',
        '[role="button"]:has(span:has-text("Original"))',
        '[role="button"]:has(span:has-text("Оригинал"))',
        # XPath for more precise matching
        '//span[text()="Original"]',
        '//span[text()="Оригинал"]',
        '//div[@role="button" and .//span[text()="Original"]]',
        '//div[@role="button" and .//span[text()="Оригинал"]]',
        '//button[.//span[text()="Original"]]',
        '//button[.//span[text()="Оригинал"]]',
    ]
    
    # Close button selectors
    CLOSE_BUTTON = [
        # Common close button selectors
        'button[aria-label*="Закрыть"]',
        'button[aria-label*="Close"]',
        'button[aria-label*="Schließen"]',
        'button[aria-label*="Κλείσιμο"]',
        'svg[aria-label*="Закрыть"]',
        'svg[aria-label*="Close"]',
        'svg[aria-label*="Schließen"]',
        'svg[aria-label*="Κλείσιμο"]',
        '[aria-label*="Закрыть"]',
        '[aria-label*="Close"]',
        '[aria-label*="Schließen"]',
        '[aria-label*="Κλείσιμο"]',
        
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
        '//button[@aria-label="Schließen"]',
        '//svg[@aria-label="Schließen"]',
        '//button[@aria-label="Κλείσιμο"]',
        '//svg[@aria-label="Κλείσιμο"]',
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
        'div:has(span:has-text("Beitrag"))',
        'div:has(span:has-text("Δημοσίευση"))',
    ]
    
    # Main interface selectors (for navigation verification)
    MAIN_INTERFACE = [
        'svg[aria-label*="Главная"]',
        'svg[aria-label*="Home"]',
        'svg[aria-label*="Создать"]',
        'svg[aria-label*="Create"]',
        '[aria-label*="Главная"]',
        '[aria-label*="Home"]',
        # Spanish navigation labels
        'svg[aria-label*="Inicio"]',
        '[aria-label*="Inicio"]',
        'svg[aria-label*="Buscar"]',
        '[aria-label*="Buscar"]',
        'svg[aria-label*="Explorar"]',
        '[aria-label*="Explorar"]',
        'svg[aria-label*="Reels"]',
        '[aria-label*="Reels"]',
        'svg[aria-label*="Mensajes"]',
        '[aria-label*="Mensajes"]',
        'svg[aria-label*="Notificaciones"]',
        '[aria-label*="Notificaciones"]',
        'svg[aria-label*="Crear"]',
        '[aria-label*="Crear"]',
        'svg[aria-label*="Perfil"]',
        '[aria-label*="Perfil"]',
        # Portuguese navigation labels
        'svg[aria-label*="Início"]',
        '[aria-label*="Início"]',
        'svg[aria-label*="Pesquisar"]',
        '[aria-label*="Pesquisar"]',
        'svg[aria-label*="Explorar"]',
        '[aria-label*="Explorar"]',
        'svg[aria-label*="Reels"]',
        '[aria-label*="Reels"]',
        'svg[aria-label*="Mensagens"]',
        '[aria-label*="Mensagens"]',
        'svg[aria-label*="Notificações"]',
        '[aria-label*="Notificações"]',
        'svg[aria-label*="Criar"]',
        '[aria-label*="Criar"]',
        'svg[aria-label*="Perfil"]',
        '[aria-label*="Perfil"]',
        # German navigation labels
        'svg[aria-label*="Startseite"]',
        '[aria-label*="Startseite"]',
        'svg[aria-label*="Suchen"]',
        '[aria-label*="Suchen"]',
        'svg[aria-label*="Entdecken"]',
        '[aria-label*="Entdecken"]',
        'svg[aria-label*="Reels"]',
        '[aria-label*="Reels"]',
        'svg[aria-label*="Nachrichten"]',
        '[aria-label*="Nachrichten"]',
        'svg[aria-label*="Benachrichtigungen"]',
        '[aria-label*="Benachrichtigungen"]',
        'svg[aria-label*="Erstellen"]',
        '[aria-label*="Erstellen"]',
        'svg[aria-label*="Profil"]',
        '[aria-label*="Profil"]',
        # Greek navigation labels
        'svg[aria-label*="Αρχική"]',
        '[aria-label*="Αρχική"]',
        'svg[aria-label*="Αναζήτηση"]',
        '[aria-label*="Αναζήτηση"]',
        'svg[aria-label*="Εξερεύνηση"]',
        '[aria-label*="Εξερεύνηση"]',
        'svg[aria-label*="Reels"]',
        '[aria-label*="Reels"]',
        'svg[aria-label*="Μηνύματα"]',
        '[aria-label*="Μηνύματα"]',
        'svg[aria-label*="Ειδοποιήσεις"]',
        '[aria-label*="Ειδοποιήσεις"]',
        'svg[aria-label*="Δημιουργία"]',
        '[aria-label*="Δημιουργία"]',
        'svg[aria-label*="Προφίλ"]',
        '[aria-label*="Προφίλ"]',
    ]
    
    # Upload indicators (to check if still on upload page)
    UPLOAD_INDICATORS = [
        'input[type="file"]',
        'div:has-text("Drag photos and videos here")',
        'div:has-text("Select from computer")',
        'div:has-text("Ziehen Sie Fotos und Videos hierher")',
        'div:has-text("Vom Computer auswählen")',
        'div:has-text("Σύρετε φωτογραφίες και βίντεο εδώ")',
        'div:has-text("Επιλογή από τον υπολογιστή")',
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
        
        # Spanish indicators
        'svg[aria-label*="Inicio"]',
        '[aria-label*="Inicio"]',
        'a[aria-label*="Inicio"]',
        'svg[aria-label*="Buscar"]',
        '[aria-label*="Buscar"]',
        'input[placeholder*="Buscar"]',
        'svg[aria-label*="Explorar"]',
        '[aria-label*="Explorar"]',
        'svg[aria-label*="Reels"]',
        '[aria-label*="Reels"]',
        'svg[aria-label*="Mensajes"]',
        '[aria-label*="Mensajes"]',
        'a[href*="/direct/"]',
        'svg[aria-label*="Notificaciones"]',
        '[aria-label*="Notificaciones"]',
        'svg[aria-label*="Crear"]',
        '[aria-label*="Crear"]',
        'svg[aria-label*="Nueva publicación"]',
        '[aria-label*="Nueva publicación"]',
        'svg[aria-label*="Perfil"]',
        '[aria-label*="Perfil"]',
        'img[alt*="foto del perfil"]',

        # Portuguese indicators
        'svg[aria-label*="Início"]',
        '[aria-label*="Início"]',
        'a[aria-label*="Início"]',
        'svg[aria-label*="Pesquisar"]',
        '[aria-label*="Pesquisar"]',
        'input[placeholder*="Pesquisar"]',
        'svg[aria-label*="Explorar"]',
        '[aria-label*="Explorar"]',
        'svg[aria-label*="Reels"]',
        '[aria-label*="Reels"]',
        'svg[aria-label*="Mensagens"]',
        '[aria-label*="Mensagens"]',
        'svg[aria-label*="Notificações"]',
        '[aria-label*="Notificações"]',
        'svg[aria-label*="Criar"]',
        '[aria-label*="Criar"]',
        'svg[aria-label*="Nova publicação"]',
        '[aria-label*="Nova publicação"]',
        'svg[aria-label*="Perfil"]',
        '[aria-label*="Perfil"]',
        'img[alt*="foto do perfil"]',
        
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