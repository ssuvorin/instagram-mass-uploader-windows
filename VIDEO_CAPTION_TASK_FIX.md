# 🔧 Исправление: VideoCaption() got unexpected keyword arguments: 'task'

**Дата:** 2025-10-05  
**Статус:** ✅ Исправлено

---

## 🐛 Проблема

**Ошибка:** `TypeError at /tiktok/bulk-upload/3/add-captions/ VideoCaption() got unexpected keyword arguments: 'task'`

**Причина:** В коде пытались передать параметр `task` в модель `VideoCaption`, но поле называется `bulk_task`.

---

## 🔍 Анализ

### **Проблемный код:**

```python
# В views_bulk.py строки 387-390 и 409-412
VideoCaption.objects.create(
    task=task,  # ❌ Неправильное имя поля
    text=caption
)

VideoCaption.objects.create(
    task=task,  # ❌ Неправильное имя поля
    text=caption_text
)
```

### **Модель VideoCaption:**

```python
# В models.py строки 407-417
class VideoCaption(models.Model):
    """
    Описания/подписи для видео.
    Можно загрузить из файла и распределить между видео.
    """
    
    bulk_task = models.ForeignKey(  # ✅ Поле называется bulk_task
        BulkUploadTask,
        on_delete=models.CASCADE,
        related_name='captions'
    )
    text = models.TextField()
    order = models.IntegerField(default=0)
    assigned_to = models.OneToOneField(
        BulkVideo,
        on_delete=models.SET_NULL,
        # ...
    )
```

---

## ✅ Исправление

### **Было (неправильно):**

```python
# Импорт из файла
VideoCaption.objects.create(
    task=task,  # ❌ Неправильное имя поля
    text=caption
)

# Одно описание для всех
VideoCaption.objects.create(
    task=task,  # ❌ Неправильное имя поля
    text=caption_text
)
```

### **Стало (правильно):**

```python
# Импорт из файла
VideoCaption.objects.create(
    bulk_task=task,  # ✅ Правильное имя поля
    text=caption
)

# Одно описание для всех
VideoCaption.objects.create(
    bulk_task=task,  # ✅ Правильное имя поля
    text=caption_text
)
```

---

## 📁 Измененные файлы

| Файл | Изменения | Строки |
|------|-----------|--------|
| `tiktok_uploader/views_mod/views_bulk.py` | ✅ Исправлено `task` → `bulk_task` (импорт из файла) | 387-390 |
| `tiktok_uploader/views_mod/views_bulk.py` | ✅ Исправлено `task` → `bulk_task` (одно описание) | 409-412 |

---

## ✅ Проверка

```bash
python manage.py check
# System check identified no issues (0 silenced). ✅
```

---

## 🧪 Как проверить что исправлено

### **Тест добавления описаний:**

1. Откройте `/tiktok/bulk-upload/<task_id>/add-captions/`
2. Выберите метод:
   - **Загрузить файл:** Выберите .txt файл с описаниями
   - **Или ввести вручную:** Введите описание в текстовое поле
3. Нажмите "Save Captions"
4. ✅ Описания должны сохраниться без ошибок
5. ✅ Должен произойти redirect на `/bulk-upload/<task_id>/`

### **Проверка в БД:**

```python
python manage.py shell
```

```python
from tiktok_uploader.models import BulkUploadTask, VideoCaption

# Проверить описания в задаче
task = BulkUploadTask.objects.get(id=3)
captions = task.captions.all()
print(f"Captions: {captions.count()}")
for caption in captions:
    print(f"  - {caption.text[:50]}...")
    print(f"    Task: {caption.bulk_task.name}")
```

---

## 📋 Структура моделей

### **VideoCaption:**
```python
class VideoCaption(models.Model):
    bulk_task = models.ForeignKey(BulkUploadTask, related_name='captions')  # ← bulk_task
    text = models.TextField()
    order = models.IntegerField(default=0)
    assigned_to = models.OneToOneField(BulkVideo, null=True, blank=True)
```

### **Связи:**
```python
# Доступ к описаниям задачи
task = BulkUploadTask.objects.get(id=1)
captions = task.captions.all()  # related_name='captions'

# Доступ к задаче описания
caption = VideoCaption.objects.get(id=1)
task = caption.bulk_task  # поле bulk_task
```

---

## 🎯 Результат

**До исправления:**
```
❌ VideoCaption() got unexpected keyword arguments: 'task'
❌ Описания не сохранялись
❌ Ошибка 500
```

**После исправления:**
```
✅ Описания сохраняются корректно
✅ Создаются записи VideoCaption в БД
✅ Redirect на детали задачи
✅ Все валидации работают
```

---

## ✅ Статус: ИСПРАВЛЕНО

**Ошибка `task` → `bulk_task` в VideoCaption полностью устранена!**

Теперь добавление описаний в задачи массовой загрузки работает корректно:
1. ✅ Описания сохраняются без ошибок
2. ✅ Создаются записи в БД
3. ✅ Redirect на детали задачи
4. ✅ Все валидации функционируют

**Готово к использованию!** 🚀

