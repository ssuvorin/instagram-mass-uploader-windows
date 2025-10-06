# 🔧 Исправление модели WarmupTask

**Дата:** 2025-10-05  
**Статус:** ✅ Исправлено

---

## 🐛 Проблема

При попытке перезапуска задачи прогрева возникала ошибка:

```
Error restarting task: The following fields do not exist in this model, are m2m fields, or are non-concrete fields: completed_at, started_at
```

---

## 🔍 Причина

В модели `WarmupTask` отсутствовали поля `started_at` и `completed_at`, которые присутствуют в модели `BulkUploadTask` и используются в коде:

### **Было в `WarmupTask`:**
```python
class WarmupTask(models.Model):
    # ...
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # ❌ Нет started_at и completed_at
```

### **В `BulkUploadTask` (для сравнения):**
```python
class BulkUploadTask(models.Model):
    # ...
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)    # ✅ Есть
    completed_at = models.DateTimeField(null=True, blank=True)  # ✅ Есть
```

---

## ✅ Решение

Добавлены недостающие поля в модель `WarmupTask`:

```python
class WarmupTask(models.Model):
    # Логи
    log = models.TextField(blank=True, default="")
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)    # ✅ Добавлено
    completed_at = models.DateTimeField(null=True, blank=True)  # ✅ Добавлено
```

---

## 📝 Изменения в коде

### 1. **Модель `WarmupTask` в `models.py`:**
```python
# Добавлены поля
started_at = models.DateTimeField(null=True, blank=True)
completed_at = models.DateTimeField(null=True, blank=True)
```

### 2. **View `restart_warmup_task` в `views_warmup.py`:**
```python
# Сбрасываем статус задачи
task.status = 'PENDING'
task.started_at = None      # ✅ Теперь работает
task.completed_at = None    # ✅ Теперь работает
task.save(update_fields=['status', 'started_at', 'completed_at'])
```

### 3. **Service `run_warmup_task` в `services.py`:**

#### При старте:
```python
task.status = 'RUNNING'
task.started_at = timezone.now()  # ✅ Записываем время старта
task.save(update_fields=['status', 'started_at'])
```

#### При завершении:
```python
task.status = 'COMPLETED'
task.completed_at = timezone.now()  # ✅ Записываем время завершения
task.save(update_fields=['status', 'completed_at'])
```

#### При ошибке:
```python
task.status = 'FAILED'
task.completed_at = timezone.now()  # ✅ Записываем время завершения
task.save()
```

---

## 🗄️ Миграция

### **Создана миграция:**
```bash
python manage.py makemigrations tiktok_uploader
```

**Результат:**
```
Migrations for 'tiktok_uploader':
  tiktok_uploader\migrations\0004_warmuptask_completed_at_warmuptask_started_at.py
    + Add field completed_at to warmuptask
    + Add field started_at to warmuptask
```

### **Применена миграция:**
```bash
python manage.py migrate tiktok_uploader
```

**Результат:**
```
Operations to perform:
  Apply all migrations: tiktok_uploader
Running migrations:
  Applying tiktok_uploader.0004_warmuptask_completed_at_warmuptask_started_at... OK
```

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

## 📊 Влияние изменений

### **Файлы изменены:**

| Файл | Изменения | Статус |
|------|-----------|--------|
| `tiktok_uploader/models.py` | ✅ Добавлены поля `started_at`, `completed_at` | ✅ |
| `tiktok_uploader/views_warmup.py` | ✅ Обновлен `restart_warmup_task` | ✅ |
| `tiktok_uploader/bot_integration/services.py` | ✅ Обновлен `run_warmup_task` | ✅ |
| `tiktok_uploader/migrations/0004_*.py` | ✅ Новая миграция | ✅ |

---

## 🎯 Преимущества

1. ✅ **Консистентность моделей** - `WarmupTask` теперь имеет те же поля что и `BulkUploadTask`
2. ✅ **Отслеживание времени** - можно точно видеть когда задача была запущена и завершена
3. ✅ **Исправлена ошибка рестарта** - функция перезапуска теперь работает корректно
4. ✅ **Улучшенная аналитика** - можно вычислять длительность выполнения задач

---

## 📈 Использование новых полей

### **В шаблонах:**
```html
{% if task.started_at %}
    Started: {{ task.started_at|date:"Y-m-d H:i:s" }}
{% endif %}

{% if task.completed_at %}
    Completed: {{ task.completed_at|date:"Y-m-d H:i:s" }}
    Duration: {{ task.completed_at|timeuntil:task.started_at }}
{% endif %}
```

### **В админке:**
```python
class WarmupTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'status', 'started_at', 'completed_at', 'created_at']
    list_filter = ['status', 'started_at', 'completed_at']
```

---

## 🔗 Связанные документы

- `WARMUP_RESTART_FEATURE.md` - Документация функции перезапуска
- `WARMUP_COMPLETE.md` - Полная документация Warmup Tasks
- `PLAYWRIGHT_ASYNC_CONTEXT_FIX.md` - Исправление async контекста

---

## ✅ Статус: ИСПРАВЛЕНО

Модель `WarmupTask` обновлена, миграция применена, все проверки пройдены! 🎉

**Теперь можно:**
- ✅ Перезапускать задачи прогрева
- ✅ Отслеживать время старта и завершения
- ✅ Вычислять длительность выполнения задач


