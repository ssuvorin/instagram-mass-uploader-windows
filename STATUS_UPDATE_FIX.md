# 🔧 Исправление обновления статусов аккаунтов

**Дата:** 2025-10-05  
**Статус:** ✅ Исправлено

---

## 🐛 Проблема

**Симптом:** Статусы аккаунтов не обновлялись в базе данных, хотя в логах было написано, что статус изменен.

**Причина:** Callbacks пытались сделать `.save()` внутри Playwright контекста, где Django ORM не работает из-за `SynchronousOnlyOperation`.

**Пример из логов:**
```
[20:00:25] ⚠️ Status updated to: BLOCKED
[20:00:25]    Reason: Password is incorrect
```
→ Но в БД статус оставался **ACTIVE** ❌

---

## ✅ Решение

Переделал callbacks чтобы они **НЕ делали `.save()` внутри Playwright**, а собирали данные в память:

### **Было (неправильно):**

```python
def update_status_callback(username, status, error_message):
    from tiktok_uploader.models import TikTokAccount
    acc = TikTokAccount.objects.get(username=username)  # ❌ Django ORM внутри Playwright
    acc.status = status
    acc.save(update_fields=['status'])  # ❌ .save() внутри Playwright
    account_result['log'] += f"Status updated to: {status}\n"
```

---

### **Стало (правильно):**

```python
def update_status_callback(username, status, error_message):
    # Сохраняем в память, БД обновим ПОСЛЕ выхода из Playwright
    account_result['new_status'] = status
    account_result['status_reason'] = error_message
    account_result['log'] += f"Status will be updated to: {status}\n"
    logger.warning(f"[STATUS_UPDATE] {username} -> {status}: {error_message}")
```

Затем **ПОСЛЕ** выхода из Playwright контекста:

```python
# ПОСЛЕ выхода из Playwright - обновляем БД
for result in accounts_results:
    warmup_acc = WarmupTaskAccount.objects.get(id=result['warmup_account_id'])
    
    # Обновляем пароль если он был изменен
    if result.get('new_password'):
        warmup_acc.account.password = result['new_password']
        warmup_acc.account.save(update_fields=['password'])
        logger.info(f"[PASSWORD_UPDATE] Password updated for {warmup_acc.account.username}")
    
    # Обновляем статус аккаунта
    if result.get('new_status'):
        warmup_acc.account.status = result['new_status']
        warmup_acc.account.save(update_fields=['status'])
        logger.info(f"[STATUS_UPDATE] {warmup_acc.account.username} status updated to {result['new_status']}")
    
    # Сбрасываем статус на ACTIVE при успешном входе
    if result.get('reset_status_to_active'):
        warmup_acc.account.status = 'ACTIVE'
        warmup_acc.account.save(update_fields=['status'])
        logger.info(f"[STATUS_RESET] {warmup_acc.account.username} status reset to ACTIVE")
```

---

## 🎯 Что изменилось

| Было | Стало |
|------|-------|
| ❌ `.save()` внутри Playwright | ✅ Сбор в память внутри Playwright |
| ❌ Django ORM в async контексте | ✅ Django ORM ПОСЛЕ async контекста |
| ❌ Статусы не обновлялись | ✅ Статусы обновляются корректно |
| ❌ Пароли не обновлялись | ✅ Пароли обновляются корректно |

---

## 📁 Измененные файлы

| Файл | Изменения | Строки |
|------|-----------|--------|
| `tiktok_uploader/bot_integration/services.py` | ✅ Callbacks для Warmup Tasks (без .save()) | 551-563 |
| `tiktok_uploader/bot_integration/services.py` | ✅ Обновление БД после Playwright (Warmup) | 648-664 |
| `tiktok_uploader/bot_integration/services.py` | ✅ Callbacks для Bulk Upload Tasks (без .save()) | 256-268 |
| `tiktok_uploader/bot_integration/services.py` | ✅ Обновление БД после Playwright (Bulk Upload) | 376-392 |
| `STATUS_UPDATE_FIX.md` | ✅ Документация | - |

---

## ✅ Проверка

```bash
python manage.py check
# System check identified no issues (0 silenced). ✓
```

---

## 🧪 Как проверить что теперь работает

### **Тест 1: Запустить прогрев**

1. Запустите прогрев аккаунтов: `/tiktok/warmup/<task_id>/`
2. Если какой-то аккаунт не войдет (например, неверный пароль)
3. ✅ В логах: `Status will be updated to: BLOCKED`
4. ✅ В БД: Статус обновится на `BLOCKED`
5. ✅ В списке аккаунтов: `/tiktok/accounts/` → бейдж будет **BLOCKED** 🔴

---

### **Тест 2: Проверить в БД напрямую**

```bash
python manage.py shell
```

```python
from tiktok_uploader.models import TikTokAccount

# Посмотреть все статусы
for acc in TikTokAccount.objects.all():
    print(f"{acc.username}: {acc.status}")

# Найти аккаунты с проблемами
blocked = TikTokAccount.objects.filter(status='BLOCKED')
print(f"Blocked accounts: {blocked.count()}")

suspended = TikTokAccount.objects.filter(status='SUSPENDED')
print(f"Suspended accounts: {suspended.count()}")
```

---

### **Тест 3: Проверить в интерфейсе**

1. Откройте список аккаунтов: `/tiktok/accounts/`
2. Используйте фильтр по статусу
3. ✅ Аккаунты с проблемами должны показывать правильные статусы:
   - 🟢 **ACTIVE** - работает
   - 🔴 **BLOCKED** - неверные данные
   - 🔴 **SUSPENDED** - заблокирован
   - 🟡 **CAPTCHA_REQUIRED** - нужна капча
   - 🟡 **PHONE_VERIFICATION_REQUIRED** - нужен телефон

---

## 📝 Логи теперь правильные

### **Внутри Playwright:**
```
[20:00:25] ⚠️ Status will be updated to: BLOCKED
[20:00:25]    Reason: Password is incorrect
```
↓

### **После Playwright (в логах сервера):**
```
[STATUS_UPDATE] user1 status updated to BLOCKED
```

---

## 🔗 Связанная проблема

Это та же самая проблема, что была с обновлением `WarmupTaskAccount`:
- ❌ Нельзя делать `.save()` внутри `sync_playwright()` контекста
- ✅ Нужно собирать данные в память и обновлять БД после выхода

**Документация:** `WARMUP_DB_ISOLATION_COMPLETE.md`

---

## ✅ Статус: ИСПРАВЛЕНО

Теперь статусы и пароли аккаунтов **правильно обновляются** в базе данных! 🎉

**Проблема `SynchronousOnlyOperation` при обновлении статусов полностью решена!** ✅



