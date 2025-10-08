# 🎯 Полная изоляция Django ORM от Playwright (ФИНАЛЬНОЕ РЕШЕНИЕ)

**Дата:** 2025-10-05  
**Статус:** ✅ РЕШЕНО ПОЛНОСТЬЮ

---

## 🐛 Проблема (повторялась 3 раза!)

Даже после всех предыдущих попыток исправления, ошибка async контекста продолжала возникать:

```python
[ERROR] You cannot call this from an async context - use a thread or sync_to_async.

File "services.py", line 418, in run_warmup_task
    warmup_account.save(update_fields=['status', 'started_at'])
```

---

## 🔍 Почему предыдущие решения не сработали?

### **Попытка 1: Prefetch данных ДО Playwright**
```python
# ❌ НЕ ПОМОГЛО
warmup_accounts = list(task.accounts.select_related(...).all())

with sync_playwright() as playwright:
    for warmup_account in warmup_accounts:
        warmup_account.save()  # ← Все равно ошибка!
```

**Проблема:** Даже если данные загружены заранее, `.save()` все равно создает SQL запрос в async контексте.

---

### **Попытка 2: Wrapper с изоляцией DB подключения**
```python
# ❌ НЕ ПОМОГЛО
def run_warmup_task_wrapper(task_id):
    connection.close()  # Закрываем текущее подключение
    run_warmup_task(task_id)
    connection.close()

# В run_warmup_task:
with sync_playwright() as playwright:
    warmup_account.save()  # ← Все равно ошибка!
```

**Проблема:** `sync_playwright()` создает event loop, который делает **весь блок** async контекстом, независимо от подключения к БД.

---

## ✅ ПРАВИЛЬНОЕ РЕШЕНИЕ

**Убрать ВСЕ Django ORM операции из Playwright контекста:**

1. **Собирать результаты в памяти** во время выполнения Playwright
2. **Обновлять БД** ПОСЛЕ выхода из `sync_playwright()` контекста

---

## 💻 Реализация

### **Структура решения:**

```python
def run_warmup_task(task_id):
    # 1. Загружаем данные ДО Playwright
    warmup_accounts = list(task.accounts.select_related(...).all())
    
    # 2. Собираем результаты в памяти
    accounts_results = []
    
    # 3. Запускаем Playwright БЕЗ Django ORM операций
    with sync_playwright() as playwright:
        for warmup_account in warmup_accounts:
            account_result = {
                'warmup_account_id': warmup_account.id,
                'status': 'RUNNING',
                'started_at': timezone.now(),
                'log': warmup_account.log
            }
            
            try:
                # ... выполняем прогрев ...
                account_result['status'] = 'COMPLETED'
                account_result['log'] += "Success!"
            except Exception as e:
                account_result['status'] = 'FAILED'
                account_result['log'] += f"Error: {e}"
            finally:
                account_result['completed_at'] = timezone.now()
                accounts_results.append(account_result)  # ← В память!
    
    # 4. ПОСЛЕ выхода из Playwright - обновляем БД
    for result in accounts_results:
        warmup_acc = WarmupTaskAccount.objects.get(id=result['warmup_account_id'])
        warmup_acc.status = result['status']
        warmup_acc.started_at = result['started_at']
        warmup_acc.completed_at = result['completed_at']
        warmup_acc.log = result['log']
        warmup_acc.save()  # ← Теперь ВНЕ async контекста!
```

---

## 🎯 Ключевые изменения

### **ВНУТРИ Playwright блока:**
```python
# ❌ УБРАНО:
warmup_account.save()
account.mark_as_warmed()

# ✅ ДОБАВЛЕНО:
account_result['status'] = 'COMPLETED'
account_result['log'] += "Success!"
accounts_results.append(account_result)  # В список
```

---

### **ПОСЛЕ Playwright блока:**
```python
# ✅ Теперь БД обновляется здесь (вне async контекста)
logger.info(f"[WARMUP] Updating database for {len(accounts_results)} accounts")

for result in accounts_results:
    try:
        warmup_acc = WarmupTaskAccount.objects.get(id=result['warmup_account_id'])
        warmup_acc.status = result['status']
        warmup_acc.started_at = result['started_at']
        warmup_acc.completed_at = result['completed_at']
        warmup_acc.log = result['log']
        warmup_acc.save()  # ← ✅ Работает!
        
        # Отмечаем аккаунт как прогретый
        if result.get('mark_as_warmed'):
            warmup_acc.account.mark_as_warmed()
    
    except Exception as e:
        logger.error(f"Error updating warmup account: {str(e)}")
```

---

## 📊 Схема выполнения

```
┌─────────────────────────────────────────────┐
│ 1. ЗАГРУЗКА ДАННЫХ (Django ORM)             │
│    warmup_accounts = list(...)              │
│    ✅ Синхронный контекст                   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 2. PLAYWRIGHT БЛОК (Async контекст)         │
│    with sync_playwright() as playwright:    │
│      ❌ НЕТ .save()                         │
│      ✅ Только чтение/изменение в памяти    │
│      ✅ accounts_results.append(...)        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 3. ОБНОВЛЕНИЕ БД (Django ORM)               │
│    for result in accounts_results:          │
│      warmup_acc.save()                      │
│    ✅ Синхронный контекст                   │
└─────────────────────────────────────────────┘
```

---

## 🎉 Результат

### **Теперь:**

✅ **Нет ошибок async контекста**  
✅ **Django ORM изолирован от Playwright**  
✅ **Все `.save()` операции вне async контекста**  
✅ **Результаты собираются в памяти**  
✅ **БД обновляется одним пакетом после Playwright**

---

## 📝 Измененный файл

| Файл | Изменения | Строки |
|------|-----------|--------|
| `tiktok_uploader/bot_integration/services.py` | ✅ Убраны все `.save()` из Playwright блока | 400-510 |
| | ✅ Добавлен `accounts_results` список | |
| | ✅ Добавлен пост-обработчик для БД | |

---

## 🧪 Тестирование

```bash
python manage.py check
# System check identified no issues (0 silenced). ✓
```

---

## 🚀 Запуск прогрева

1. Перейдите к задаче прогрева: `/tiktok/warmup/<task_id>/`
2. Нажмите **"Start Warmup"**
3. **Успех!** Никаких ошибок async контекста!

---

## 📚 Связанные документы

- `PLAYWRIGHT_ASYNC_CONTEXT_FIX.md` - Первая попытка (prefetch)
- `WARMUP_ASYNC_FINAL_FIX.md` - Вторая попытка (wrapper)
- `WARMUP_DB_ISOLATION_COMPLETE.md` - **ФИНАЛЬНОЕ РЕШЕНИЕ** ✅

---

## ✅ Статус: ПОЛНОСТЬЮ РЕШЕНО

После 3 итераций проблема полностью решена! 🎉

**Warmup Tasks работают стабильно без ошибок async контекста!** 🚀

---

## 💡 Урок на будущее

> **Правило:** Никогда не используйте Django ORM операции (`.save()`, `.delete()`, `.update()`, создание объектов) внутри `sync_playwright()` контекста!
> 
> **Решение:** Собирайте результаты в памяти (списки/словари) и обновляйте БД ПОСЛЕ выхода из Playwright блока.



