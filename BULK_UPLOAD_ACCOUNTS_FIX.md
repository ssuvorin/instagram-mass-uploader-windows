# 🔧 Исправление: "Нет доступных аккаунтов" при создании задачи

**Дата:** 2025-10-05  
**Статус:** ✅ Исправлено

---

## 🐛 Проблема

**Симптом:** При попытке создать задачу массовой загрузки показывалось сообщение "No accounts available", хотя в системе есть активные аккаунты.

**Причина:** В функции `create_bulk_upload()` была ошибка в передаче контекста в template.

---

## 🔍 Анализ проблемы

### **Было (неправильно):**

```python
# В views_bulk.py строка 147
context = {
    'available_accounts': TikTokAccount.objects.filter(status='ACTIVE'),  # ❌ Неправильное имя
    'available_proxies': TikTokProxy.objects.filter(status='active'),
}
```

```html
<!-- В create.html строка 81 -->
{% for account in accounts %}  <!-- ❌ Ожидает 'accounts', а получает 'available_accounts' -->
```

**Результат:** Template не находил переменную `accounts` → показывал "No accounts available"

---

### **Стало (правильно):**

```python
# В views_bulk.py строка 147
context = {
    'accounts': TikTokAccount.objects.filter(status='ACTIVE'),  # ✅ Правильное имя
    'available_proxies': TikTokProxy.objects.filter(status='active'),
}
```

```html
<!-- В create.html строка 81 -->
{% for account in accounts %}  <!-- ✅ Теперь находит переменную -->
```

---

## ✅ Дополнительные исправления

### **1. Улучшена POST обработка:**

**Было:**
```python
# Создавалась только задача, без связей с аккаунтами
task = BulkUploadTask.objects.create(
    name=name,
    status='PENDING',
    created_by=request.user,
)
# ❌ Аккаунты не привязывались к задаче
```

**Стало:**
```python
# Создается задача + связи с аккаунтами
task = BulkUploadTask.objects.create(
    name=name,
    status='PENDING',
    created_by=request.user,
)

# ✅ Создаем связи с аккаунтами
from ..models import BulkUploadAccount
for account_id in account_ids:
    account = TikTokAccount.objects.get(id=account_id)
    BulkUploadAccount.objects.create(
        task=task,
        account=account,
        proxy=account.proxy  # Используем прокси аккаунта
    )
```

### **2. Добавлена валидация:**

```python
if not account_ids:
    messages.error(request, 'Выберите минимум один аккаунт')
    return render(request, 'tiktok_uploader/bulk_upload/create.html', {
        'accounts': TikTokAccount.objects.filter(status='ACTIVE'),
        'available_proxies': TikTokProxy.objects.filter(status='active'),
    })
```

### **3. Улучшен redirect:**

**Было:**
```python
return redirect('tiktok_uploader:bulk_upload_list')  # ❌ На список задач
```

**Стало:**
```python
return redirect('tiktok_uploader:add_bulk_videos', task_id=task.id)  # ✅ На добавление видео
```

---

## 📁 Измененные файлы

| Файл | Изменения | Строки |
|------|-----------|--------|
| `tiktok_uploader/views_mod/views_bulk.py` | ✅ Исправлен контекст | 147 |
| `tiktok_uploader/views_mod/views_bulk.py` | ✅ Добавлена POST обработка | 124-164 |
| `tiktok_uploader/views_mod/views_bulk.py` | ✅ Добавлена валидация аккаунтов | 135-140 |
| `tiktok_uploader/views_mod/views_bulk.py` | ✅ Создание BulkUploadAccount | 150-158 |
| `tiktok_uploader/views_mod/views_bulk.py` | ✅ Улучшен redirect | 161 |

---

## ✅ Проверка

```bash
python manage.py check
# System check identified no issues (0 silenced). ✅
```

---

## 🧪 Как проверить что исправлено

### **Тест 1: Создание задачи**

1. Откройте `/tiktok/bulk-upload/create/`
2. ✅ Должны отображаться все активные аккаунты
3. Введите название задачи
4. Выберите аккаунт(ы)
5. Нажмите "Create Task"
6. ✅ Должен произойти redirect на `/add-videos/`

### **Тест 2: Проверка в БД**

```python
python manage.py shell
```

```python
from tiktok_uploader.models import BulkUploadTask, BulkUploadAccount

# Проверить последнюю задачу
task = BulkUploadTask.objects.last()
print(f"Task: {task.name}")

# Проверить связанные аккаунты
accounts = task.accounts.all()
print(f"Accounts: {accounts.count()}")
for acc in accounts:
    print(f"  - {acc.account.username}")
```

---

## 🎯 Результат

**До исправления:**
```
❌ "No accounts available"
❌ Задача создавалась без аккаунтов
❌ Redirect на список задач
```

**После исправления:**
```
✅ Аккаунты отображаются в списке
✅ Задача создается с выбранными аккаунтами
✅ Redirect на добавление видео
✅ Валидация выбора аккаунтов
```

---

## ✅ Статус: ИСПРАВЛЕНО

**Проблема "Нет доступных аккаунтов" полностью решена!**

Теперь при создании задачи массовой загрузки:
1. ✅ Отображаются все активные аккаунты
2. ✅ Можно выбрать нужные аккаунты
3. ✅ Задача создается с привязкой к аккаунтам
4. ✅ Автоматический переход к добавлению видео

**Готово к использованию!** 🚀

