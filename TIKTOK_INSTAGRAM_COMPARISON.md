# 📊 Сравнительный анализ модулей TikTok и Instagram

## 🎯 Цель
Привести модуль TikTok к такому же поведению и функциональности, как модуль Instagram (кроме самого бота).

---

## 📋 Текущее состояние

### ✅ Что уже реализовано в TikTok (аналогично Instagram)

| Функционал | Instagram | TikTok | Статус |
|------------|-----------|--------|--------|
| **Управление аккаунтами** | ✅ | ✅ | ✅ Идентично |
| **Управление прокси** | ✅ | ✅ | ✅ Идентично |
| **Bulk Upload** | ✅ | ✅ | ⚠️ Есть различия |
| **Warmup** | ✅ | ✅ | ⚠️ Есть различия |
| **Follow/Unfollow** | ✅ | ✅ | ⚠️ Есть различия |
| **Cookie Robot** | ✅ | ✅ | ✅ Идентично |
| **Dolphin Integration** | ✅ | ✅ | ✅ Идентично |
| **Dashboard** | ✅ | ✅ | ✅ Идентично |

### ❌ Что отсутствует в TikTok

| Функционал | Instagram | TikTok | Приоритет |
|------------|-----------|--------|-----------|
| **Bulk Login** | ✅ | ❌ | 🔴 Высокий |
| **Avatar Change** | ✅ | ❌ | 🟡 Средний |
| **Bio Link Change** | ✅ | ❌ | 🟡 Средний |
| **Photo Upload** | ✅ | ❌ | 🟢 Низкий |
| **Hashtag Analytics** | ✅ | ❌ | 🟢 Низкий |
| **Account Analytics** | ✅ | ❌ | 🟢 Низкий |

---

## 🔍 Детальное сравнение моделей

### 1. Модели прокси ✅

**Instagram: `Proxy`**
```python
- host, port, username, password
- proxy_type, status
- is_active, last_used, last_verified
- country, city
- ip_change_url, external_ip
- assigned_account (ForeignKey)
```

**TikTok: `TikTokProxy`**
```python
- host, port, username, password
- proxy_type, status
- is_active, last_used, last_verified
- country, city
- ip_change_url, external_ip
- created_at, updated_at ✨ (новое)
```

**Статус:** ✅ Идентично (TikTok даже лучше с timestamps)

---

### 2. Модели аккаунтов ⚠️

**Instagram: `InstagramAccount`**
```python
- username, password
- email_username, email_password
- tfa_secret
- phone_number
- proxy, current_proxy
- dolphin_profile_id
- status, last_used, last_warmed
- created_at, updated_at
- notes, locale, client
```

**TikTok: `TikTokAccount`**
```python
- username, password
- email, email_password  ⚠️ (email вместо email_username)
- phone_number
- proxy, current_proxy
- dolphin_profile_id
- status, last_used, last_warmed
- created_at, updated_at
- notes, locale, client
```

**Отличия:**
- ❌ TikTok: нет `tfa_secret` (2FA)
- ⚠️ TikTok: `email` вместо `email_username`

**Рекомендации:**
```python
# Добавить в TikTokAccount:
tfa_secret = models.CharField(max_length=100, null=True, blank=True)

# Переименовать:
email_username = models.CharField(...)  # вместо email
```

---

### 3. Дополнительные модели Instagram

#### 3.1 `InstagramDevice` ❌
**Назначение:** Хранение настроек мобильного устройства для API instagrapi

```python
class InstagramDevice(models.Model):
    account = models.OneToOneField(InstagramAccount)
    device_settings = models.JSONField()
    user_agent = models.CharField()
    session_settings = models.JSONField()
    session_file = models.CharField()
    last_login_at = models.DateTimeField()
    last_avatar_change_at = models.DateTimeField()
```

**Для TikTok:** НЕ НУЖНО (используется только для instagrapi API)

---

#### 3.2 `InstagramCookies` ❌
**Назначение:** Хранение cookies отдельно от аккаунта

```python
class InstagramCookies(models.Model):
    account = models.OneToOneField(InstagramAccount)
    cookies_data = models.JSONField()
    last_updated = models.DateTimeField()
    is_valid = models.BooleanField()
```

**Для TikTok:** 🟡 Опционально
- В TikTok cookies хранятся в `CookieRobotTaskAccount.cookies_json`
- Можно добавить отдельную модель для удобства

---

### 4. Task Account модели - КРИТИЧЕСКАЯ РАЗНИЦА! ⚠️

#### Instagram: Все task accounts имеют поле `proxy`

**`BulkUploadAccount`:**
```python
proxy = models.ForeignKey(Proxy, on_delete=models.SET_NULL, null=True, blank=True)
```

**`WarmupTaskAccount`:**
```python
proxy = models.ForeignKey(Proxy, on_delete=models.SET_NULL, null=True, blank=True)
```

**`FollowTaskAccount`:**
```python
proxy = models.ForeignKey(Proxy, on_delete=models.SET_NULL, null=True, blank=True)
```

#### TikTok: Task accounts НЕ ИМЕЮТ поля `proxy`! ❌

**`BulkUploadAccount`:**
```python
# НЕТ ПОЛЯ proxy!
```

**`WarmupTaskAccount`:**
```python
# НЕТ ПОЛЯ proxy!
```

**`FollowTaskAccount`:**
```python
# НЕТ ПОЛЯ proxy!
```

**`CookieRobotTaskAccount`:**
```python
# НЕТ ПОЛЯ proxy!
```

### ⚠️ ПРОБЛЕМА:
Без поля `proxy` в task accounts невозможно отслеживать, какой прокси использовался для конкретного аккаунта в конкретной задаче.

### ✅ РЕШЕНИЕ:
Добавить поле `proxy` во все TikTok task account модели!

---

## 🔨 План действий

### Этап 1: Исправление моделей (🔴 Критично)

#### 1.1 Добавить `proxy` в task accounts

```python
# tiktok_uploader/models.py

class BulkUploadAccount(models.Model):
    bulk_task = models.ForeignKey(BulkUploadTask, ...)
    account = models.ForeignKey(TikTokAccount, ...)
    proxy = models.ForeignKey(  # ← ДОБАВИТЬ
        TikTokProxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bulk_used_in'
    )
    status = models.CharField(...)
    # ... остальные поля

class WarmupTaskAccount(models.Model):
    task = models.ForeignKey(WarmupTask, ...)
    account = models.ForeignKey(TikTokAccount, ...)
    proxy = models.ForeignKey(  # ← ДОБАВИТЬ
        TikTokProxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='warmup_used_in'
    )
    status = models.CharField(...)
    # ... остальные поля

class FollowTaskAccount(models.Model):
    task = models.ForeignKey(FollowTask, ...)
    account = models.ForeignKey(TikTokAccount, ...)
    proxy = models.ForeignKey(  # ← ДОБАВИТЬ
        TikTokProxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='follow_used_in'
    )
    status = models.CharField(...)
    # ... остальные поля

class CookieRobotTaskAccount(models.Model):
    task = models.ForeignKey(CookieRobotTask, ...)
    account = models.ForeignKey(TikTokAccount, ...)
    proxy = models.ForeignKey(  # ← ДОБАВИТЬ
        TikTokProxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cookie_used_in'
    )
    status = models.CharField(...)
    # ... остальные поля
```

#### 1.2 Добавить `tfa_secret` в `TikTokAccount`

```python
class TikTokAccount(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    email = models.CharField(max_length=100, null=True, blank=True)
    email_password = models.CharField(max_length=100, null=True, blank=True)
    tfa_secret = models.CharField(  # ← ДОБАВИТЬ
        max_length=100, 
        null=True, 
        blank=True,
        help_text="2FA secret key for TOTP"
    )
    phone_number = models.CharField(max_length=32, null=True, blank=True)
    # ... остальные поля
```

#### 1.3 Улучшить `FollowTarget` (как в Instagram)

```python
class FollowTarget(models.Model):
    category = models.ForeignKey(FollowCategory, ...)
    username = models.CharField(max_length=100)
    user_id = models.BigIntegerField(null=True, blank=True)  # ← ДОБАВИТЬ
    full_name = models.CharField(max_length=255, blank=True, default="")  # ← ДОБАВИТЬ
    is_private = models.BooleanField(default=False)  # ← ДОБАВИТЬ
    is_verified = models.BooleanField(default=False)  # ← ДОБАВИТЬ
    profile_pic_url = models.URLField(blank=True, default="")  # ← ДОБАВИТЬ
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # ← ДОБАВИТЬ
```

#### 1.4 Добавить `last_target_id` в `FollowTaskAccount`

```python
class FollowTaskAccount(models.Model):
    task = models.ForeignKey(FollowTask, ...)
    account = models.ForeignKey(TikTokAccount, ...)
    proxy = models.ForeignKey(TikTokProxy, ...)  # ← уже добавили выше
    status = models.CharField(...)
    follow_count = models.IntegerField(default=0)
    last_target_id = models.IntegerField(null=True, blank=True)  # ← ДОБАВИТЬ
    log = models.TextField(...)
    started_at = models.DateTimeField(...)
    completed_at = models.DateTimeField(...)
```

---

### Этап 2: Добавление отсутствующих функциональных модулей

#### 2.1 Bulk Login Task (🔴 Высокий приоритет)

**Создать модели:**

```python
# tiktok_uploader/models.py

class BulkLoginTask(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PARTIALLY_COMPLETED', 'Partially Completed'),
    ]
    
    name = models.CharField(max_length=120, default="Bulk Login")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    log = models.TextField(blank=True, default="")
    
    def __str__(self):
        return f"Bulk Login {self.id} - {self.status}"
    
    def get_completed_count(self):
        return self.accounts.filter(status='COMPLETED').count()
    
    def get_total_count(self):
        return self.accounts.count()
    
    def get_completion_percentage(self):
        total = self.get_total_count()
        if total == 0:
            return 0
        return int(self.get_completed_count() / total * 100)


class BulkLoginAccount(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PHONE_VERIFICATION_REQUIRED', 'Phone Verification Required'),
        ('CAPTCHA_REQUIRED', 'Captcha Required'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    bulk_task = models.ForeignKey(
        BulkLoginTask, 
        on_delete=models.CASCADE, 
        related_name='accounts'
    )
    account = models.ForeignKey(
        TikTokAccount, 
        on_delete=models.CASCADE, 
        related_name='bulk_logins'
    )
    proxy = models.ForeignKey(
        TikTokProxy, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='bulk_login_used_in'
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    log = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.account.username} in {self.bulk_task.name}"
```

**Создать views:**
- `bulk_login_list` - список задач
- `create_bulk_login` - создание задачи
- `bulk_login_detail` - детали задачи
- `start_bulk_login` - запуск задачи
- `delete_bulk_login` - удаление задачи
- `get_bulk_login_logs` - получение логов

**Создать шаблоны:**
- `templates/tiktok_uploader/bulk_login/list.html`
- `templates/tiktok_uploader/bulk_login/create.html`
- `templates/tiktok_uploader/bulk_login/detail.html`

**Добавить URL:**
```python
# tiktok_uploader/urls.py

# Bulk Login
path('bulk-login/', views.bulk_login_list, name='bulk_login_list'),
path('bulk-login/create/', views.create_bulk_login, name='create_bulk_login'),
path('bulk-login/<int:task_id>/', views.bulk_login_detail, name='bulk_login_detail'),
path('bulk-login/<int:task_id>/start/', views.start_bulk_login, name='start_bulk_login'),
path('bulk-login/<int:task_id>/delete/', views.delete_bulk_login, name='delete_bulk_login'),
path('bulk-login/<int:task_id>/logs/', views.get_bulk_login_logs, name='bulk_login_logs'),
```

---

#### 2.2 Avatar Change Task (🟡 Средний приоритет)

TikTok также поддерживает смену аватарок. Нужно добавить:

```python
# tiktok_uploader/models.py

class AvatarChangeTask(models.Model):
    STRATEGY_CHOICES = [
        ('random_reuse', 'Random reuse when images < accounts'),
        ('one_to_one', 'One image per account (same order)'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    name = models.CharField(max_length=120, default="Avatar Change")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    strategy = models.CharField(max_length=20, choices=STRATEGY_CHOICES, default='random_reuse')
    delay_min_sec = models.IntegerField(default=15)
    delay_max_sec = models.IntegerField(default=45)
    concurrency = models.IntegerField(default=1)
    log = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Avatar Task {self.id} - {self.status}"


class AvatarChangeTaskAccount(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    task = models.ForeignKey(AvatarChangeTask, on_delete=models.CASCADE, related_name='accounts')
    account = models.ForeignKey(TikTokAccount, on_delete=models.CASCADE, related_name='avatar_tasks')
    proxy = models.ForeignKey(TikTokProxy, on_delete=models.SET_NULL, null=True, blank=True, related_name='avatar_used_in')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    log = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.account.username} in Avatar Task {self.task.id}"


class AvatarImage(models.Model):
    task = models.ForeignKey(AvatarChangeTask, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='tiktok/avatars/')
    order = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"AvatarImage {self.id} for Task {self.task.id}"
```

---

#### 2.3 Bio Change Task (🟡 Средний приоритет)

TikTok поддерживает редактирование профиля (bio, website). Добавить:

```python
# tiktok_uploader/models.py

class BioChangeTask(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    name = models.CharField(max_length=120, default="Bio Change Task")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    bio_text = models.TextField(max_length=80, blank=True, help_text="New bio (max 80 chars)")
    website_url = models.URLField(max_length=500, blank=True, help_text="Website link")
    delay_min_sec = models.IntegerField(default=15)
    delay_max_sec = models.IntegerField(default=45)
    concurrency = models.IntegerField(default=1)
    log = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Bio Task {self.id} - {self.status}"


class BioChangeTaskAccount(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    task = models.ForeignKey(BioChangeTask, on_delete=models.CASCADE, related_name='accounts')
    account = models.ForeignKey(TikTokAccount, on_delete=models.CASCADE, related_name='bio_tasks')
    proxy = models.ForeignKey(TikTokProxy, on_delete=models.SET_NULL, null=True, blank=True, related_name='bio_used_in')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    log = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.account.username} in Bio Task {self.task.id}"
```

---

#### 2.4 Photo Upload (🟢 Низкий приоритет)

TikTok теперь поддерживает загрузку фото/слайдшоу. Можно добавить позже.

---

#### 2.5 Hashtag Analytics (🟢 Низкий приоритет)

Аналитика хештегов. Может быть полезна, но не критична.

```python
class HashtagAnalytics(models.Model):
    hashtag = models.CharField(max_length=150, db_index=True)
    total_videos = models.IntegerField(default=0)
    total_views = models.BigIntegerField(default=0)
    total_likes = models.BigIntegerField(default=0)
    total_comments = models.BigIntegerField(default=0)
    total_shares = models.BigIntegerField(default=0)
    average_views = models.FloatField(default=0.0)
    engagement_rate = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['hashtag', 'created_at']),
        ]
```

---

## 📝 Миграции

После внесения изменений в модели:

```bash
# 1. Создать миграции
python manage.py makemigrations tiktok_uploader

# 2. Применить миграции
python manage.py migrate tiktok_uploader
```

---

## 🎨 Обновление forms.py

Добавить формы для новых моделей по аналогии с Instagram:

```python
# tiktok_uploader/forms.py

class BulkLoginTaskForm(forms.ModelForm):
    class Meta:
        model = BulkLoginTask
        fields = ['name']

class AvatarChangeTaskForm(forms.ModelForm):
    class Meta:
        model = AvatarChangeTask
        fields = ['name', 'strategy', 'delay_min_sec', 'delay_max_sec', 'concurrency']

class BioChangeTaskForm(forms.ModelForm):
    class Meta:
        model = BioChangeTask
        fields = ['name', 'bio_text', 'website_url', 'delay_min_sec', 'delay_max_sec', 'concurrency']
```

---

## 🔗 Обновление Admin

Зарегистрировать новые модели в admin.py:

```python
# tiktok_uploader/admin.py

from django.contrib import admin
from .models import (
    # ... существующие
    BulkLoginTask, BulkLoginAccount,
    AvatarChangeTask, AvatarChangeTaskAccount, AvatarImage,
    BioChangeTask, BioChangeTaskAccount,
)

admin.site.register(BulkLoginTask)
admin.site.register(BulkLoginAccount)
admin.site.register(AvatarChangeTask)
admin.site.register(AvatarChangeTaskAccount)
admin.site.register(AvatarImage)
admin.site.register(BioChangeTask)
admin.site.register(BioChangeTaskAccount)
```

---

## ✅ Чеклист внедрения

### Фаза 1: Критичные исправления (Сейчас)
- [ ] Добавить поле `proxy` в `BulkUploadAccount`
- [ ] Добавить поле `proxy` в `WarmupTaskAccount`
- [ ] Добавить поле `proxy` в `FollowTaskAccount`
- [ ] Добавить поле `proxy` в `CookieRobotTaskAccount`
- [ ] Добавить поле `tfa_secret` в `TikTokAccount`
- [ ] Улучшить модель `FollowTarget` (добавить user_id, full_name, is_private, is_verified, profile_pic_url)
- [ ] Добавить поле `last_target_id` в `FollowTaskAccount`
- [ ] Создать и применить миграции

### Фаза 2: Bulk Login (Высокий приоритет)
- [ ] Создать модели `BulkLoginTask` и `BulkLoginAccount`
- [ ] Создать формы
- [ ] Создать views
- [ ] Создать шаблоны
- [ ] Добавить URL
- [ ] Интегрировать с ботом
- [ ] Тестирование

### Фаза 3: Avatar & Bio (Средний приоритет)
- [ ] Создать модели для Avatar Change
- [ ] Создать модели для Bio Change
- [ ] Создать views и шаблоны
- [ ] Интегрировать с ботом
- [ ] Тестирование

### Фаза 4: Аналитика (Низкий приоритет)
- [ ] Создать модели для аналитики
- [ ] Создать дашборд аналитики
- [ ] Интегрировать сбор данных

---

## 📊 Сводная таблица приоритетов

| Задача | Сложность | Приоритет | Время |
|--------|-----------|-----------|-------|
| Добавить proxy в task accounts | Легко | 🔴 Критично | 30 мин |
| Добавить tfa_secret | Легко | 🔴 Высокий | 15 мин |
| Улучшить FollowTarget | Легко | 🟡 Средний | 20 мин |
| Bulk Login модели | Средне | 🔴 Высокий | 2 часа |
| Bulk Login views | Средне | 🔴 Высокий | 3 часа |
| Bulk Login шаблоны | Легко | 🔴 Высокий | 1 час |
| Avatar Change полный | Сложно | 🟡 Средний | 6 часов |
| Bio Change полный | Средне | 🟡 Средний | 4 часа |
| Hashtag Analytics | Сложно | 🟢 Низкий | 8 часов |

---

## 🚀 Быстрый старт - что делать СЕЙЧАС

1. **Создать бэкап БД:**
   ```bash
   cp db.sqlite3 db.sqlite3.backup
   ```

2. **Обновить models.py** (см. Этап 1 выше)

3. **Создать и применить миграции:**
   ```bash
   python manage.py makemigrations tiktok_uploader
   python manage.py migrate tiktok_uploader
   ```

4. **Обновить views для использования proxy** (в существующих task views)

5. **Тестировать на dev окружении**

6. **Перейти к Фазе 2** (Bulk Login)

---

## 📚 Дополнительные материалы

- `uploader/models.py` - эталонные модели Instagram
- `uploader/views.py` - эталонные views Instagram
- `uploader/forms.py` - эталонные формы Instagram

**Принцип:** Копируем логику Instagram, адаптируем под TikTok API

---

**Статус:** 📋 Готов к внедрению  
**Автор:** AI Assistant  
**Дата:** 2025-10-04




