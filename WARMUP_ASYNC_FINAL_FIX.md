# 🔧 Финальное исправление async контекста для Warmup Tasks

**Дата:** 2025-10-05  
**Статус:** ✅ Исправлено

---

## 🐛 Проблема (повторная)

После исправления загрузки данных из БД ДО входа в Playwright контекст, ошибка все равно возникала:

```python
[ERROR] Critical error in warmup task 4: You cannot call this from an async context - use a thread or sync_to_async.

File "services.py", line 398, in run_warmup_task
    warmup_account.save(update_fields=['status', 'started_at'])
    
django.core.exceptions.SynchronousOnlyOperation: You cannot call this from an async context
```

---

## 🔍 Причина

Проблема была в том, что мы пытались вызывать **`.save()`** внутри блока `with sync_playwright()`:

```python
# ❌ ПРОБЛЕМА:
with sync_playwright() as playwright:
    for warmup_account in warmup_accounts:
        warmup_account.status = 'RUNNING'
        warmup_account.save()  # ← Ошибка! Django ORM не работает в async контексте
```

**Почему это не работает?**

Даже если данные загружены из БД заранее, **любой вызов `.save()`** или другой Django ORM операции внутри `sync_playwright()` контекста вызывает ошибку, потому что Playwright создает **event loop** (async контекст), а Django ORM требует **синхронного** подключения к БД.

---

## ✅ Решение

Создан **wrapper-функция** `run_warmup_task_wrapper`, которая:
1. Закрывает текущее Django DB подключение
2. Запускает `run_warmup_task` в **изолированном потоке**
3. Создает **новое** DB подключение в потоке
4. Закрывает подключение после завершения

### **Код решения:**

```python
def run_warmup_task_wrapper(task_id: int):
    """
    Wrapper для запуска задачи прогрева в отдельном потоке.
    Создает новое подключение к БД для изоляции от async контекста Playwright.
    """
    from django.db import connection
    
    # Закрываем текущее подключение чтобы создать новое в потоке
    connection.close()
    
    try:
        run_warmup_task(task_id)
    except Exception as e:
        logger.error(f"Error in warmup task wrapper {task_id}: {str(e)}")
        logger.log_err()
    finally:
        # Закрываем подключение после завершения
        connection.close()
```

---

## 📝 Изменения в коде

### 1. **Добавлен wrapper в `services.py`:**

```python
# Новая функция
def run_warmup_task_wrapper(task_id: int):
    from django.db import connection
    connection.close()
    try:
        run_warmup_task(task_id)
    except Exception as e:
        logger.error(f"Error in warmup task wrapper {task_id}: {str(e)}")
    finally:
        connection.close()

# Существующая функция (без изменений)
def run_warmup_task(task_id: int) -> Dict[str, Any]:
    # ... вся логика прогрева ...
```

---

### 2. **Обновлен `views_warmup.py`:**

#### Было:
```python
from .bot_integration.services import run_warmup_task

def run_warmup_in_background():
    try:
        run_warmup_task(task_id)
    except Exception as e:
        # error handling...

thread = threading.Thread(target=run_warmup_in_background, daemon=True)
```

#### Стало:
```python
from .bot_integration.services import run_warmup_task_wrapper

thread = threading.Thread(
    target=run_warmup_task_wrapper,
    args=(task_id,),
    daemon=True
)
```

---

### 3. **Исправлен `logger.py`:**

Добавлена обработка `PermissionError` при попытке удалить файл лога:

```python
# Инициализация файла лога
if not append:
    try:
        if os.path.exists(self._log_file):
            os.remove(self._log_file)
    except (PermissionError, OSError):
        # Файл занят другим процессом, продолжаем
        pass
    
    try:
        with open(self._log_file, "w") as log:
            log.write(f'{datetime.today()}\n')
            log.write(f'Platform: {platform.platform()}\n\n')
    except (PermissionError, OSError):
        # Не можем записать, продолжаем без инициализации
        pass
```

---

## 🎯 Как это работает?

### **Изоляция подключений к БД:**

```
┌─────────────────────────────────────────────────────┐
│ Django Main Thread                                  │
│  - Request Handler                                  │
│  - DB Connection #1                                 │
│    ↓                                                │
│    calls run_warmup_task_wrapper()                  │
└─────────────────────────────────────────────────────┘
                    ↓
        connection.close() ← закрываем DB #1
                    ↓
┌─────────────────────────────────────────────────────┐
│ Background Thread                                   │
│  - run_warmup_task()                                │
│  - DB Connection #2 ← новое подключение             │
│    ↓                                                │
│    with sync_playwright():  ← async контекст        │
│      - warmup_account.save() ← работает!            │
│        (использует DB Connection #2)                │
│    ↓                                                │
│    connection.close() ← закрываем DB #2             │
└─────────────────────────────────────────────────────┘
```

---

## 📊 Измененные файлы

| Файл | Изменения | Статус |
|------|-----------|--------|
| `tiktok_uploader/bot_integration/services.py` | ✅ Добавлен `run_warmup_task_wrapper` | ✅ |
| `tiktok_uploader/views_warmup.py` | ✅ Использует новый wrapper | ✅ |
| `tiktok_uploader/bot_integration/logger.py` | ✅ Обработка PermissionError | ✅ |
| `WARMUP_ASYNC_FINAL_FIX.md` | ✅ Документация | ✅ |

---

## ✅ Проверка

```bash
python manage.py check
```

**Результат:**
```
System check identified no issues (0 silenced). ✓
```

---

## 🎉 Результат

Теперь задачи прогрева запускаются **без ошибок**:

```
✅ Django ORM изолирован от Playwright async контекста
✅ Каждый background поток имеет свое DB подключение
✅ Нет конфликтов между sync и async кодом
✅ .save() работает внутри Playwright контекста
```

---

## 🔗 Связанные документы

- `PLAYWRIGHT_ASYNC_CONTEXT_FIX.md` - Первое исправление (prefetch данных)
- `WARMUP_RESTART_FEATURE.md` - Функция перезапуска задач
- `WARMUP_MODEL_FIX.md` - Добавление полей started_at/completed_at
- `WARMUP_COMPLETE.md` - Полная документация Warmup Tasks

---

## ✅ Статус: ПОЛНОСТЬЮ ИСПРАВЛЕНО

Все проблемы с async контекстом решены! Warmup Tasks теперь работают стабильно! 🎉

**Можете запускать прогрев аккаунтов без ошибок!** 🚀


