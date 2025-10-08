# 🔧 Исправление: Invalid field name(s) given in select_related: 'assigned_account'

**Дата:** 2025-10-05  
**Статус:** ✅ Исправлено

---

## 🐛 Проблема

**Ошибка:** `FieldError at /tiktok/bulk-upload/3/add-videos/ Invalid field name(s) given in select_related: 'assigned_account'. Choices are: bulk_task, assigned_to, assigned_caption`

**Причина:** В коде использовалось неправильное имя поля `assigned_account` в `select_related`, но в модели `BulkVideo` поле называется `assigned_to`.

---

## 🔍 Анализ

### **Проблемный код:**

```python
# В views_bulk.py строка 295
videos = task.videos.all().select_related('assigned_account__account')  # ❌ Неправильное имя поля
```

### **Модель BulkVideo:**

```python
# В models.py строки 353-373
class BulkVideo(models.Model):
    bulk_task = models.ForeignKey(
        BulkUploadTask,
        on_delete=models.CASCADE,
        related_name='videos'
    )
    video_file = models.FileField(upload_to='tiktok/bulk_videos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Привязка к аккаунту
    assigned_to = models.ForeignKey(  # ✅ Поле называется assigned_to
        BulkUploadAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_videos'
    )
```

**Доступные поля в BulkVideo:**
- `bulk_task` ✅
- `assigned_to` ✅ (не `assigned_account`)
- `assigned_caption` ✅

---

## ✅ Исправление

### **Было (неправильно):**

```python
videos = task.videos.all().select_related('assigned_account__account')  # ❌ Неправильное имя поля
```

### **Стало (правильно):**

```python
videos = task.videos.all().select_related('assigned_to__account')  # ✅ Правильное имя поля
```

---

## 📁 Измененные файлы

| Файл | Изменения | Строки |
|------|-----------|--------|
| `tiktok_uploader/views_mod/views_bulk.py` | ✅ Исправлено `assigned_account` → `assigned_to` | 295 |

---

## ✅ Проверка

```bash
python manage.py check
# System check identified no issues (0 silenced). ✅
```

---

## 🧪 Как проверить что исправлено

### **Тест добавления видео:**

1. Откройте `/tiktok/bulk-upload/<task_id>/add-videos/`
2. ✅ Страница должна загрузиться без ошибок
3. ✅ Должны отображаться уже загруженные видео (если есть)
4. ✅ Форма загрузки должна работать

### **Проверка в БД:**

```python
python manage.py shell
```

```python
from tiktok_uploader.models import BulkUploadTask, BulkVideo

# Проверить видео в задаче
task = BulkUploadTask.objects.get(id=3)
videos = task.videos.all().select_related('assigned_to__account')
print(f"Videos: {videos.count()}")
for video in videos:
    print(f"  - {video.video_file.name}")
    if video.assigned_to:
        print(f"    Assigned to: {video.assigned_to.account.username}")
    else:
        print(f"    Not assigned yet")
```

---

## 📋 Структура моделей

### **BulkVideo:**
```python
class BulkVideo(models.Model):
    bulk_task = models.ForeignKey(BulkUploadTask, related_name='videos')
    video_file = models.FileField(upload_to='tiktok/bulk_videos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(BulkUploadAccount, related_name='assigned_videos')  # ← assigned_to
    assigned_caption = models.OneToOneField(VideoCaption, null=True, blank=True)
```

### **BulkUploadAccount:**
```python
class BulkUploadAccount(models.Model):
    bulk_task = models.ForeignKey(BulkUploadTask, related_name='accounts')
    account = models.ForeignKey(TikTokAccount)
    proxy = models.ForeignKey(TikTokProxy, null=True, blank=True)
    # ... другие поля
```

### **Связи:**
```python
# Доступ к видео задачи
task = BulkUploadTask.objects.get(id=1)
videos = task.videos.all()  # related_name='videos'

# Доступ к назначенным видео аккаунта
bulk_account = BulkUploadAccount.objects.get(id=1)
assigned_videos = bulk_account.assigned_videos.all()  # related_name='assigned_videos'

# Доступ к аккаунту видео
video = BulkVideo.objects.get(id=1)
if video.assigned_to:
    account = video.assigned_to.account  # assigned_to → account
```

---

## 🎯 Результат

**До исправления:**
```
❌ FieldError: Invalid field name(s) given in select_related: 'assigned_account'
❌ Страница add-videos не загружалась
❌ Ошибка 500
```

**После исправления:**
```
✅ Страница add-videos загружается корректно
✅ Отображаются уже загруженные видео
✅ Форма загрузки работает
✅ select_related оптимизирует запросы
```

---

## ✅ Статус: ИСПРАВЛЕНО

**Ошибка `assigned_account` → `assigned_to` полностью устранена!**

Теперь страница добавления видео работает корректно:
1. ✅ Страница загружается без ошибок
2. ✅ Отображаются уже загруженные видео
3. ✅ Форма загрузки функционирует
4. ✅ select_related оптимизирует запросы к БД

**Готово к использованию!** 🚀


