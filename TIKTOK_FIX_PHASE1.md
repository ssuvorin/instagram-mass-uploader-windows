# 🔧 TikTok Модуль - Фаза 1: Критичные исправления

## 🎯 Цель
Привести TikTok модуль к базовой совместимости с Instagram модулем.

---

## 📋 Изменения моделей

### 1. Добавить proxy в BulkUploadAccount

**Файл:** `tiktok_uploader/models.py`

**Найти:**
```python
class BulkUploadAccount(models.Model):
    """
    Связь между задачей загрузки и аккаунтом.
    Отслеживает прогресс для каждого аккаунта.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    bulk_task = models.ForeignKey(
        BulkUploadTask, 
        on_delete=models.CASCADE, 
        related_name='accounts'
    )
    account = models.ForeignKey(
        TikTokAccount, 
        on_delete=models.CASCADE, 
        related_name='bulk_uploads'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
```

**Заменить на:**
```python
class BulkUploadAccount(models.Model):
    """
    Связь между задачей загрузки и аккаунтом.
    Отслеживает прогресс для каждого аккаунта.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    bulk_task = models.ForeignKey(
        BulkUploadTask, 
        on_delete=models.CASCADE, 
        related_name='accounts'
    )
    account = models.ForeignKey(
        TikTokAccount, 
        on_delete=models.CASCADE, 
        related_name='bulk_uploads'
    )
    proxy = models.ForeignKey(  # ← ДОБАВЛЕНО
        TikTokProxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bulk_used_in',
        help_text="Прокси, используемый для этой задачи"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
```

---

### 2. Добавить proxy в WarmupTaskAccount

**Найти:**
```python
class WarmupTaskAccount(models.Model):
    """
    Связь между задачей прогрева и аккаунтом.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    task = models.ForeignKey(
        WarmupTask,
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    account = models.ForeignKey(
        TikTokAccount,
        on_delete=models.CASCADE,
        related_name='warmup_tasks'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
```

**Заменить на:**
```python
class WarmupTaskAccount(models.Model):
    """
    Связь между задачей прогрева и аккаунтом.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    task = models.ForeignKey(
        WarmupTask,
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    account = models.ForeignKey(
        TikTokAccount,
        on_delete=models.CASCADE,
        related_name='warmup_tasks'
    )
    proxy = models.ForeignKey(  # ← ДОБАВЛЕНО
        TikTokProxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='warmup_used_in',
        help_text="Прокси, используемый для прогрева"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
```

---

### 3. Добавить proxy в FollowTaskAccount

**Найти:**
```python
class FollowTaskAccount(models.Model):
    """
    Связь между задачей подписок и аккаунтом.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    task = models.ForeignKey(
        FollowTask,
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    account = models.ForeignKey(
        TikTokAccount,
        on_delete=models.CASCADE,
        related_name='follow_tasks'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    follow_count = models.IntegerField(default=0)
```

**Заменить на:**
```python
class FollowTaskAccount(models.Model):
    """
    Связь между задачей подписок и аккаунтом.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    task = models.ForeignKey(
        FollowTask,
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    account = models.ForeignKey(
        TikTokAccount,
        on_delete=models.CASCADE,
        related_name='follow_tasks'
    )
    proxy = models.ForeignKey(  # ← ДОБАВЛЕНО
        TikTokProxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='follow_used_in',
        help_text="Прокси, используемый для подписок"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    follow_count = models.IntegerField(default=0)
    last_target_id = models.IntegerField(null=True, blank=True)  # ← ДОБАВЛЕНО
```

---

### 4. Добавить proxy в CookieRobotTaskAccount

**Найти:**
```python
class CookieRobotTaskAccount(models.Model):
    """
    Связь между задачей обновления cookies и аккаунтом.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    task = models.ForeignKey(
        CookieRobotTask,
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    account = models.ForeignKey(
        TikTokAccount,
        on_delete=models.CASCADE,
        related_name='cookie_tasks'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
```

**Заменить на:**
```python
class CookieRobotTaskAccount(models.Model):
    """
    Связь между задачей обновления cookies и аккаунтом.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    task = models.ForeignKey(
        CookieRobotTask,
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    account = models.ForeignKey(
        TikTokAccount,
        on_delete=models.CASCADE,
        related_name='cookie_tasks'
    )
    proxy = models.ForeignKey(  # ← ДОБАВЛЕНО
        TikTokProxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cookie_used_in',
        help_text="Прокси, используемый для обновления cookies"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
```

---

### 5. Добавить tfa_secret в TikTokAccount

**Найти:**
```python
    # Основные данные аккаунта
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    email = models.CharField(max_length=100, null=True, blank=True)
    email_password = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=32, null=True, blank=True)
```

**Заменить на:**
```python
    # Основные данные аккаунта
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    email = models.CharField(max_length=100, null=True, blank=True)
    email_password = models.CharField(max_length=100, null=True, blank=True)
    tfa_secret = models.CharField(  # ← ДОБАВЛЕНО
        max_length=100, 
        null=True, 
        blank=True,
        help_text="2FA secret key for TOTP authentication"
    )
    phone_number = models.CharField(max_length=32, null=True, blank=True)
```

**И обновить метод to_dict():**

**Найти:**
```python
    def to_dict(self):
        """Преобразует аккаунт в словарь для использования в боте"""
        data = {
            "username": self.username,
            "password": self.password,
        }
        
        if self.email:
            data["email"] = self.email
        
        if self.email_password:
            data["email_password"] = self.email_password
        
        if self.phone_number:
            data["phone"] = self.phone_number
```

**Заменить на:**
```python
    def to_dict(self):
        """Преобразует аккаунт в словарь для использования в боте"""
        data = {
            "username": self.username,
            "password": self.password,
        }
        
        if self.email:
            data["email"] = self.email
        
        if self.email_password:
            data["email_password"] = self.email_password
        
        if self.tfa_secret:  # ← ДОБАВЛЕНО
            data["tfa_secret"] = self.tfa_secret
        
        if self.phone_number:
            data["phone"] = self.phone_number
```

---

### 6. Улучшить FollowTarget

**Найти:**
```python
class FollowTarget(models.Model):
    """
    Целевой TikTok аккаунт для подписок.
    """
    
    category = models.ForeignKey(
        FollowCategory,
        on_delete=models.CASCADE,
        related_name='targets'
    )
    username = models.CharField(max_length=100, help_text="TikTok username (без @)")
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Follow Target"
        verbose_name_plural = "Follow Targets"
        unique_together = ['category', 'username']
    
    def __str__(self):
        return f"@{self.username} ({self.category.name})"
```

**Заменить на:**
```python
class FollowTarget(models.Model):
    """
    Целевой TikTok аккаунт для подписок.
    """
    
    category = models.ForeignKey(
        FollowCategory,
        on_delete=models.CASCADE,
        related_name='targets'
    )
    username = models.CharField(max_length=100, help_text="TikTok username (без @)")
    user_id = models.CharField(max_length=100, null=True, blank=True)  # ← ДОБАВЛЕНО (TikTok user ID может быть строкой)
    full_name = models.CharField(max_length=255, blank=True, default="")  # ← ДОБАВЛЕНО
    is_private = models.BooleanField(default=False)  # ← ДОБАВЛЕНО
    is_verified = models.BooleanField(default=False)  # ← ДОБАВЛЕНО
    profile_pic_url = models.URLField(blank=True, default="")  # ← ДОБАВЛЕНО
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # ← ДОБАВЛЕНО
    
    class Meta:
        verbose_name = "Follow Target"
        verbose_name_plural = "Follow Targets"
        unique_together = ['category', 'username']
    
    def __str__(self):
        return f"@{self.username} ({self.category.name})"
```

---

## 🔄 Команды для применения

```bash
# 1. Создать резервную копию базы данных
cp db.sqlite3 db.sqlite3.backup_phase1

# 2. Создать миграции
python manage.py makemigrations tiktok_uploader

# 3. Просмотреть SQL миграции (опционально)
python manage.py sqlmigrate tiktok_uploader <номер_миграции>

# 4. Применить миграции
python manage.py migrate tiktok_uploader

# 5. Проверить что все ОК
python manage.py check
```

---

## 📝 Обновление форм

**Файл:** `tiktok_uploader/forms.py`

### Добавить tfa_secret в TikTokAccountForm

**Найти:**
```python
    class Meta:
        model = TikTokAccount
        fields = [
            'username', 'password', 'email', 'email_password',
            'proxy', 'locale', 'client', 'notes'
        ]
```

**Заменить на:**
```python
    class Meta:
        model = TikTokAccount
        fields = [
            'username', 'password', 'email', 'email_password', 'tfa_secret',
            'proxy', 'locale', 'client', 'notes'
        ]
```

**И добавить виджет:**

**Найти:**
```python
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'email_password': forms.PasswordInput(attrs={'class': 'form-control'}),
```

**Заменить на:**
```python
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'email_password': forms.PasswordInput(attrs={'class': 'form-control'}),
            'tfa_secret': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2FA Secret Key'}),  # ← ДОБАВЛЕНО
```

---

## 🎨 Обновление шаблонов

**Файл:** `tiktok_uploader/templates/tiktok_uploader/accounts/create_account.html`

**Найти секцию с email_password (после строки 74):**

**Добавить после:**
```html
                        <div class="mb-3">
                            <label for="{{ form.email_password.id_for_label }}" class="form-label">Email Password</label>
                            {{ form.email_password }}
                            {% if form.email_password.errors %}
                                <div class="invalid-feedback d-block">{{ form.email_password.errors.0 }}</div>
                            {% endif %}
                            <small class="form-text text-muted">Password for email account (needed to get verification codes)</small>
                        </div>

                        <!-- ДОБАВИТЬ ЭТОТ БЛОК -->
                        <div class="mb-3">
                            <label for="{{ form.tfa_secret.id_for_label }}" class="form-label">2FA Secret (Optional)</label>
                            {{ form.tfa_secret }}
                            {% if form.tfa_secret.errors %}
                                <div class="invalid-feedback d-block">{{ form.tfa_secret.errors.0 }}</div>
                            {% endif %}
                            <small class="form-text text-muted">Two-factor authentication secret key (TOTP)</small>
                        </div>
```

---

## ✅ Чеклист Фазы 1

### Модели
- [ ] Добавить `proxy` в `BulkUploadAccount`
- [ ] Добавить `proxy` в `WarmupTaskAccount`
- [ ] Добавить `proxy` в `FollowTaskAccount`
- [ ] Добавить `proxy` в `CookieRobotTaskAccount`
- [ ] Добавить `tfa_secret` в `TikTokAccount`
- [ ] Обновить `to_dict()` в `TikTokAccount`
- [ ] Улучшить `FollowTarget` (добавить дополнительные поля)
- [ ] Добавить `last_target_id` в `FollowTaskAccount`

### Миграции
- [ ] Создать резервную копию БД
- [ ] Создать миграции (`makemigrations`)
- [ ] Применить миграции (`migrate`)
- [ ] Проверить работоспособность (`check`)

### Формы
- [ ] Добавить `tfa_secret` в `TikTokAccountForm.Meta.fields`
- [ ] Добавить виджет для `tfa_secret`
- [ ] Добавить валидацию (если нужно)

### Шаблоны
- [ ] Добавить поле 2FA в `create_account.html`
- [ ] Добавить поле 2FA в `edit_account.html` (если есть)

### Views (обновление логики)
- [ ] Обновить `create_bulk_upload` - сохранять proxy в BulkUploadAccount
- [ ] Обновить `warmup_task_create` - сохранять proxy в WarmupTaskAccount
- [ ] Обновить `follow_task_create` - сохранять proxy в FollowTaskAccount
- [ ] Обновить `bulk_cookie_robot` - сохранять proxy в CookieRobotTaskAccount

### Тестирование
- [ ] Создать тестовый аккаунт с 2FA
- [ ] Создать bulk upload task и проверить что proxy сохраняется
- [ ] Создать warmup task и проверить что proxy сохраняется
- [ ] Создать follow task и проверить что proxy сохраняется
- [ ] Создать cookie robot task и проверить что proxy сохраняется

---

## 🚨 Потенциальные проблемы

### 1. Existing Data Migration

При добавлении новых полей `proxy` со значением `null=True, blank=True` существующие записи получат `NULL` значения. Это нормально.

### 2. Backward Compatibility

Если бот уже использует модели, убедитесь что:
- Код бота проверяет наличие `proxy` перед использованием
- Fallback на `account.current_proxy` или `account.proxy`

### 3. Admin Interface

Новые поля автоматически появятся в Django Admin. Возможно потребуется настроить отображение.

---

## 🎯 Ожидаемый результат

После Фазы 1:
- ✅ TikTok модель имеет те же базовые поля что Instagram
- ✅ Все task accounts отслеживают используемый proxy
- ✅ Поддержка 2FA для аккаунтов
- ✅ Расширенная информация о Follow Targets
- ✅ Готовность к Фазе 2 (Bulk Login)

**Время выполнения:** ~1-2 часа  
**Сложность:** Низкая  
**Риск:** Минимальный (только добавление полей)

---

**Следующий шаг:** После завершения Фазы 1 → [TIKTOK_FIX_PHASE2.md](./TIKTOK_FIX_PHASE2.md) (Bulk Login)




