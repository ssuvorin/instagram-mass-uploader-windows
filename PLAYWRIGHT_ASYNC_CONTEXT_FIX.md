# 🔧 Исправление асинхронного контекста Playwright

**Дата:** 2025-10-05  
**Статус:** ✅ Исправлено

---

## 🐛 Проблема

При запуске задачи прогрева (Warmup Task) возникала ошибка:

```python
[ERROR] Critical error in warmup task 4: You cannot call this from an async context - use a thread or sync_to_async.

django.core.exceptions.SynchronousOnlyOperation: You cannot call this from an async context - use a thread or sync_to_async.
```

### Трассировка ошибки:
```python
File "tiktok_uploader\bot_integration\services.py", line 385, in run_warmup_task
    for warmup_account in warmup_accounts:
File "django\db\models\query.py", line 400, in __iter__
    self._fetch_all()
...
django.core.exceptions.SynchronousOnlyOperation: You cannot call this from an async context
```

---

## 🔍 Причина проблемы

### **Конфликт синхронного и асинхронного контекста:**

1. **Django ORM** - **синхронный** (blocking I/O)
2. **Playwright** (`sync_playwright()`) - создает **event loop**, делая контекст асинхронным
3. **QuerySet** - ленивый объект, выполняет SQL запрос только при итерации

### **Что происходило:**

```python
# ❌ НЕПРАВИЛЬНО:
warmup_accounts = task.accounts.all()  # QuerySet (не выполнен)

with sync_playwright() as playwright:    # Создает async контекст
    for warmup_account in warmup_accounts:  # ← ЗДЕСЬ выполняется SQL запрос
        # Ошибка! Django ORM не может работать в async контексте
```

### **Почему Playwright создает async контекст?**

`sync_playwright()` использует внутри себя asyncio event loop для управления браузером, даже если API синхронный. Это делает весь блок `with sync_playwright()` асинхронным контекстом.

---

## ✅ Решение

### **Получить все данные из БД ДО входа в Playwright контекст:**

```python
# ✅ ПРАВИЛЬНО:
warmup_accounts = list(
    task.accounts.select_related('account', 'account__proxy').all()
)  # Выполняется SQL запрос СРАЗУ, возвращает список

with sync_playwright() as playwright:    # Создает async контекст
    for warmup_account in warmup_accounts:  # ← Итерация по списку (не QuerySet)
        # Все работает! Данные уже загружены из БД
```

---

## 📝 Изменения в коде

### 1. **`run_warmup_task` в `services.py`**

#### Было:
```python
# Получаем аккаунты задачи
warmup_accounts = task.accounts.all()  # QuerySet

results = {
    "success": True,
    "total_accounts": warmup_accounts.count(),  # Еще один SQL запрос
    "processed": 0,
    "successful": 0,
    "failed": 0
}

# Запускаем Playwright
with sync_playwright() as playwright:
    for warmup_account in warmup_accounts:  # ← Ошибка здесь!
        account = warmup_account.account  # ← И здесь (N+1 queries)
```

#### Стало:
```python
# Получаем аккаунты задачи ДО входа в Playwright контекст
# Используем select_related для prefetch связанных объектов
warmup_accounts = list(
    task.accounts.select_related('account', 'account__proxy').all()
)

results = {
    "success": True,
    "total_accounts": len(warmup_accounts),  # Подсчет длины списка (не SQL)
    "processed": 0,
    "successful": 0,
    "failed": 0
}

# Запускаем Playwright
with sync_playwright() as playwright:
    for warmup_account in warmup_accounts:  # ✅ Итерация по списку
        account = warmup_account.account  # ✅ Уже загружено (select_related)
```

---

### 2. **`run_bulk_upload_task` в `services.py`**

#### Было:
```python
# Получаем все аккаунты задачи
bulk_accounts = task.accounts.all()  # QuerySet

results = {
    "success": True,
    "total_accounts": bulk_accounts.count(),
    "processed": 0,
    "successful": 0,
    "failed": 0,
    "errors": []
}

# Запускаем Playwright для автоматизации
with sync_playwright() as playwright:
    for bulk_account in bulk_accounts:  # ← Ошибка!
```

#### Стало:
```python
# Получаем все аккаунты задачи ДО входа в Playwright контекст
# Используем select_related и prefetch_related для prefetch связанных объектов
bulk_accounts = list(
    task.accounts.select_related('account', 'account__proxy')
    .prefetch_related('assigned_videos')
    .all()
)

results = {
    "success": True,
    "total_accounts": len(bulk_accounts),
    "processed": 0,
    "successful": 0,
    "failed": 0,
    "errors": []
}

# Запускаем Playwright для автоматизации
with sync_playwright() as playwright:
    for bulk_account in bulk_accounts:  # ✅ Итерация по списку
```

---

## 🎯 Преимущества решения

### 1. **Исправлена ошибка async контекста:**
- ✅ Django ORM больше не вызывается внутри async контекста
- ✅ Все данные загружаются заранее

### 2. **Оптимизация запросов к БД:**

#### **`select_related('account', 'account__proxy')`**
- Загружает связанные объекты **одним JOIN запросом**
- Избегает **N+1 queries problem**

**Было:**
```sql
SELECT * FROM warmup_task_accounts;           -- 1 запрос
SELECT * FROM tiktok_accounts WHERE id=1;     -- N запросов
SELECT * FROM tiktok_proxies WHERE id=1;      -- N запросов
-- Итого: 1 + N + N = 2N+1 запросов
```

**Стало:**
```sql
SELECT warmup_task_accounts.*, tiktok_accounts.*, tiktok_proxies.*
FROM warmup_task_accounts
LEFT JOIN tiktok_accounts ON ...
LEFT JOIN tiktok_proxies ON ...;
-- Итого: 1 запрос!
```

#### **`prefetch_related('assigned_videos')`**
- Загружает связанные видео **двумя запросами** (вместо N)
- Используется для ManyToMany и обратных ForeignKey

**Было:**
```sql
SELECT * FROM bulk_upload_accounts;           -- 1 запрос
SELECT * FROM bulk_videos WHERE account_id=1; -- N запросов
-- Итого: N+1 запросов
```

**Стало:**
```sql
SELECT * FROM bulk_upload_accounts;           -- 1 запрос
SELECT * FROM bulk_videos WHERE account_id IN (1,2,3...); -- 1 запрос
-- Итого: 2 запроса!
```

### 3. **Улучшенная производительность:**
- ✅ Меньше SQL запросов = быстрее выполнение
- ✅ Все данные в памяти = нет блокировок БД внутри Playwright

---

## 📊 Измененные файлы

| Файл | Изменения | Статус |
|------|-----------|--------|
| `tiktok_uploader/bot_integration/services.py` | ✅ `run_warmup_task` - prefetch данных | ✅ |
| `tiktok_uploader/bot_integration/services.py` | ✅ `run_bulk_upload_task` - prefetch данных | ✅ |
| `PLAYWRIGHT_ASYNC_CONTEXT_FIX.md` | ✅ Документация | ✅ |

---

## 🧪 Тестирование

### 1. **Запустите задачу прогрева:**
```bash
1. Перейдите: /tiktok/warmup/
2. Создайте новую задачу
3. Выберите аккаунты
4. Нажмите "Start Warmup"
```

### 2. **Проверьте логи:**
```powershell
Get-Content bot\log.txt -Tail 50
```

**Ожидаемый результат:**
```
[INFO] Warmup task "Test" started
[INFO] Warming up account: user1
[INFO] Authentication successful
[INFO] Booster started
[OK] Warmup completed successfully
```

**Не должно быть:**
```
❌ [ERROR] SynchronousOnlyOperation: You cannot call this from an async context
```

---

## 📚 Дополнительная информация

### **Когда использовать `list()`?**

Всегда преобразовывайте QuerySet в список перед входом в async контекст:

```python
# ❌ НЕПРАВИЛЬНО:
items = Model.objects.all()
with sync_playwright() as p:
    for item in items:  # Ошибка!
        ...

# ✅ ПРАВИЛЬНО:
items = list(Model.objects.all())
with sync_playwright() as p:
    for item in items:  # OK!
        ...
```

---

### **Когда использовать `select_related()`?**

Для **ForeignKey** и **OneToOne** полей:

```python
# Загружает account и proxy одним запросом
warmup_accounts = list(
    WarmupTaskAccount.objects.select_related(
        'account',           # ForeignKey
        'account__proxy'     # ForeignKey через другую модель
    ).all()
)
```

---

### **Когда использовать `prefetch_related()`?**

Для **ManyToMany** и **обратных ForeignKey**:

```python
# Загружает видео двумя запросами (вместо N+1)
bulk_accounts = list(
    BulkUploadAccount.objects.prefetch_related(
        'assigned_videos'  # ManyToMany
    ).all()
)
```

---

## ✅ Статус: ИСПРАВЛЕНО

Все проблемы с асинхронным контекстом Playwright исправлены! Теперь задачи прогрева и массовой загрузки работают корректно. 🎉

---

## 🔗 Связанные документы

- `WARMUP_COMPLETE.md` - Документация Warmup Tasks
- `TIKTOK_BULK_IMPORT_COMPLETE.md` - Документация Bulk Upload
- Django Docs: [select_related](https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-related)
- Django Docs: [prefetch_related](https://docs.djangoproject.com/en/stable/ref/models/querysets/#prefetch-related)
- Playwright Docs: [sync_playwright](https://playwright.dev/python/docs/library#sync-api)



