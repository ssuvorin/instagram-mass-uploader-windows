# 👨‍💻 Документация для разработчиков

## 🏗 Архитектура проекта

### Основные модули

```
uploader/
├── models.py                   # Django модели данных
├── views.py                    # Веб-интерфейс и API
├── bulk_tasks_playwright.py    # 🎯 Основная логика загрузки
├── instagram_automation.py     # Базовые классы автоматизации
├── human_behavior.py          # Симуляция человеческого поведения
├── captcha_solver.py          # Решение reCAPTCHA
├── login_optimized.py         # Оптимизированный вход
├── crop_handler.py            # Обработка обрезки видео
├── constants.py               # 📋 Централизованные константы
└── async_bulk_tasks.py        # Асинхронная обработка
```

### Принципы архитектуры

- **SOLID** - принципы объектно-ориентированного дизайна
- **DRY** - избежание дублирования кода
- **Модульность** - четкое разделение ответственности
- **Централизация конфигурации** - все константы в `constants.py`

## 🔧 Ключевые классы

### InstagramAutomationBase
```python
# Базовый класс для всех операций Instagram
class InstagramAutomationBase:
    def __init__(self, page, human_behavior=None):
        self.page = page
        self.human_behavior = human_behavior
```

### InstagramUploader
```python
# Основной класс загрузки
uploader = InstagramUploader(page, human_behavior)
result = uploader.upload_video(video_file, video_obj)
```

### CropHandler  
```python
# Обработка crop и aspect ratio
crop_handler = CropHandler(page, human_behavior)
crop_handler.handle_crop_settings()
```

### RuCaptchaSolver
```python
# Решение reCAPTCHA
solver = RuCaptchaSolver()
solution = solver.solve_recaptcha_v2(site_key, page_url)
```

## 🔍 Важные функции

### Основной workflow
```python
def run_bulk_upload_task(task_id):
    """Главная функция запуска bulk upload"""
    # 1. Инициализация веб-логгера
    init_web_logger(task_id)
    
    # 2. Получение задачи с аккаунтами
    task = get_task_with_accounts(task_id)
    
    # 3. Обработка каждого аккаунта
    for account_task in account_tasks:
        run_dolphin_browser(account_details, videos, video_files)
```

### Человекоподобное поведение
```python
def init_human_behavior(page):
    """Инициализация симуляции человеческого поведения"""
    global human_behavior
    human_behavior = AdvancedHumanBehavior(page)
    return human_behavior
```

### Строгая проверка успеха
```python
def _verify_video_posted(self):
    """Строгая проверка успешности загрузки видео"""
    # Ищем явные индикаторы успеха
    # Двойная проверка через 3-5 секунд
    # Обнаружение ошибок
```

## 📋 Константы и конфигурация

### Временные интервалы
```python
class TimeConstants:
    HUMAN_DELAY_MIN = 0.5       # Минимальная задержка между действиями
    HUMAN_DELAY_MAX = 2.0       # Максимальная задержка
    ACCOUNT_DELAY_MIN = 30      # Задержка между аккаунтами
    VIDEO_DELAY_MIN = 180       # 3 минуты между видео
    CAPTCHA_SOLVE_TIMEOUT = 180 # Таймаут решения капчи
```

### Селекторы Instagram
```python
class InstagramSelectors:
    SUCCESS_INDICATORS = [
        'div:has-text("Ваша публикация опубликована")',
        'div:has-text("Your post has been shared")',
        # ... 60+ вариантов
    ]
    
    ERROR_INDICATORS = [
        'div:has-text("Что-то пошло не так")',
        'div:has-text("Something went wrong")',
        # ... 80+ вариантов
    ]
```

## 🚀 Добавление новых функций

### 1. Новый Instagram селектор
```python
# В constants.py
class InstagramSelectors:
    NEW_FEATURE_SELECTORS = [
        'button[aria-label="New Feature"]',
        'div[data-testid="new-feature"]'
    ]
```

### 2. Новый метод автоматизации
```python
# В instagram_automation.py
class InstagramNavigator(InstagramAutomationBase):
    def new_feature_method(self):
        """Новая функция автоматизации"""
        selectors = InstagramSelectors.NEW_FEATURE_SELECTORS
        # Реализация логики
```

### 3. Новое человекоподобное поведение
```python
# В human_behavior.py  
class AdvancedHumanBehavior:
    def new_behavior_pattern(self):
        """Новый паттерн поведения"""
        # Реализация нового поведения
```

## 🔄 Асинхронная архитектура

### Семафоры для контроля нагрузки
```python
async def run_async_bulk_upload_task(task_id, max_concurrent=3):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_account(account_task):
        async with semaphore:
            # Обработка аккаунта
            pass
```

### Parallel execution
```python
# Запуск нескольких аккаунтов параллельно
tasks = [process_account(account) for account in accounts]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

## 🐛 Отладка и логирование

### Web Logger
```python
def log_info(message):
    """Логирование для веб-интерфейса"""
    web_logger.info(message)
    print(f"[INFO] {message}")
```

### Скриншоты при ошибках
```python
def capture_debug_screenshot(page, context):
    """Сохранение скриншота для отладки"""
    screenshot_path = f"debug_{int(time.time())}.png"
    page.screenshot(path=screenshot_path)
```

### Verbose режим
```python
# Детальное логирование селекторов
if verbose_logging:
    log_info(f"Trying selector: {selector}")
    log_info(f"Element found: {element is not None}")
```

## 🔧 Полезные утилиты

### Работа с элементами
```python
def wait_for_element(page, selector, timeout=30000):
    """Ожидание появления элемента"""
    try:
        return page.wait_for_selector(selector, timeout=timeout)
    except Exception as e:
        log_error(f"Element not found: {selector}")
        return None
```

### Очистка браузеров
```python
def cleanup_browser_processes():
    """Очистка зависших процессов браузера"""
    # Поиск и завершение Dolphin процессов
    # Очистка временных файлов
```

### Обработка ошибок
```python
def handle_instagram_error(page, error_context):
    """Централизованная обработка ошибок Instagram"""
    # Анализ типа ошибки
    # Логирование с контекстом
    # Принятие решения о продолжении
```

## 🧪 Тестирование

### Тестирование селекторов
```python
def test_selectors_availability(page):
    """Проверка доступности селекторов на странице"""
    for selector in InstagramSelectors.SUCCESS_INDICATORS:
        element = page.query_selector(selector)
        print(f"{selector}: {'✅' if element else '❌'}")
```

### Тестирование человекоподобного поведения
```python
def test_human_behavior(page):
    """Тестирование реалистичности поведения"""
    behavior = AdvancedHumanBehavior(page)
    # Измерение времени выполнения
    # Анализ паттернов движения мыши
```

## 📦 Развертывание

### Docker конфигурация
```dockerfile
# Dockerfile
FROM python:3.8-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install chromium
```

### Environment variables
```bash
# .env.production
SECRET_KEY=production-secret-key
DEBUG=False
DOLPHIN_API_TOKEN=prod-token
RUCAPTCHA_API_KEY=prod-captcha-key
```

## 🔮 Планы развития

### Ближайшие улучшения
- [ ] **TypeScript интеграция** для лучшей типизации
- [ ] **Unit тесты** для критических функций  
- [ ] **CI/CD pipeline** для автоматического тестирования
- [ ] **Metrics collection** для мониторинга производительности

### Архитектурные улучшения
- [ ] **Plugin система** для расширения функциональности
- [ ] **Event-driven architecture** для лучшей декомпозиции
- [ ] **Microservices** для масштабирования отдельных компонентов

---

**Принцип**: *Код должен быть самодокументируемым, модульным и легко тестируемым.* 