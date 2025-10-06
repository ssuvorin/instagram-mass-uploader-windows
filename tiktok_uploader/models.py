"""
TikTok Uploader Models
======================

Модели данных для управления TikTok аккаунтами и автоматизацией.
По аналогии с Instagram Uploader, но адаптированы под специфику TikTok.
"""

from django.db import models
from django.utils import timezone
import uuid
import random
import json


# ============================================================================
# ПРОКСИ И БАЗОВЫЕ МОДЕЛИ
# ============================================================================

class TikTokProxy(models.Model):
    """
    Модель для хранения прокси-серверов для TikTok аккаунтов.
    Поддерживает HTTP, HTTPS, SOCKS5 прокси.
    """
    
    PROXY_TYPE_CHOICES = [
        ('HTTP', 'HTTP'),
        ('SOCKS5', 'SOCKS5'),
        ('HTTPS', 'HTTPS')
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('banned', 'Banned'),
        ('checking', 'Checking')
    ]
    
    host = models.CharField(max_length=255, help_text="Proxy host (IP address or domain name)")
    port = models.IntegerField()
    username = models.CharField(max_length=200, null=True, blank=True)
    password = models.CharField(max_length=200, null=True, blank=True)
    proxy_type = models.CharField(max_length=10, choices=PROXY_TYPE_CHOICES, default='HTTP')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive')
    last_checked = models.DateTimeField(null=True, blank=True)
    
    # Дополнительные поля
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    last_verified = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    country = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    
    # Функционал смены IP
    ip_change_url = models.URLField(
        max_length=500, 
        null=True, 
        blank=True, 
        help_text="URL для смены IP-адреса прокси"
    )
    external_ip = models.GenericIPAddressField(
        null=True, 
        blank=True, 
        help_text="Внешний IP-адрес при использовании прокси"
    )
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        verbose_name = "TikTok Proxy"
        verbose_name_plural = "TikTok Proxies"
        unique_together = ['host', 'port', 'username', 'password']
    
    def __str__(self):
        return f"{self.proxy_type}://{self.host}:{self.port}"
    
    def to_dict(self):
        """Преобразует прокси в словарь для использования в боте"""
        return {
            "type": self.proxy_type.lower(),
            "host": self.host,
            "port": self.port,
            "user": self.username,
            "pass": self.password,
            "country": self.country,
            "city": self.city,
        }


# ============================================================================
# АККАУНТЫ TIKTOK
# ============================================================================

class TikTokAccount(models.Model):
    """
    Модель TikTok аккаунта.
    Хранит учетные данные, статус, привязку к прокси и Dolphin профилю.
    """
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('BLOCKED', 'Blocked'),
        ('LIMITED', 'Limited'),
        ('INACTIVE', 'Inactive'),
        ('PHONE_VERIFICATION_REQUIRED', 'Phone Verification Required'),
        ('CAPTCHA_REQUIRED', 'Captcha Required'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    # Основные данные аккаунта
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    email = models.CharField(max_length=100, null=True, blank=True)
    email_password = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=32, null=True, blank=True)
    
    # Прокси
    proxy = models.ForeignKey(
        TikTokProxy, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='accounts'
    )
    current_proxy = models.ForeignKey(
        TikTokProxy, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='active_accounts'
    )
    
    # Dolphin Anty профиль
    dolphin_profile_id = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        help_text="Dolphin Anty browser profile ID"
    )
    
    # Статус и метаданные
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='ACTIVE')
    last_used = models.DateTimeField(null=True, blank=True)
    last_warmed = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, default="")
    
    # Локализация
    locale = models.CharField(
        max_length=5, 
        default='en_US', 
        help_text="Locale, e.g. en_US, ru_RU, es_ES"
    )
    
    # Привязка к клиенту (интеграция с cabinet)
    client = models.ForeignKey(
        'cabinet.Client', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='tiktok_accounts'
    )
    
    class Meta:
        verbose_name = "TikTok Account"
        verbose_name_plural = "TikTok Accounts"
    
    def __str__(self):
        return self.username
    
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
        
        # Прокси
        if self.current_proxy:
            data["proxy"] = self.current_proxy.to_dict()
        elif self.proxy:
            data["proxy"] = self.proxy.to_dict()
        
        # Dolphin профиль
        if self.dolphin_profile_id:
            data["dolphin_profile_id"] = self.dolphin_profile_id
        
        # Локализация
        data["locale"] = self.locale or 'en_US'
        
        return data
    
    def mark_as_used(self):
        """Отметить аккаунт как использованный"""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])
    
    def mark_as_warmed(self):
        """Отметить аккаунт как прогретый"""
        self.last_warmed = timezone.now()
        self.save(update_fields=['last_warmed'])


class DolphinProfileSnapshot(models.Model):
    """
    Снимок Dolphin профиля для возможности восстановления 1:1.
    """
    account = models.OneToOneField(
        TikTokAccount, 
        on_delete=models.CASCADE, 
        related_name='dolphin_snapshot'
    )
    profile_id = models.CharField(max_length=100, db_index=True)
    payload_json = models.JSONField()
    response_json = models.JSONField()
    meta_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Dolphin Profile Snapshot"
        verbose_name_plural = "Dolphin Profile Snapshots"
    
    def __str__(self):
        return f"Snapshot for {self.account.username} ({self.profile_id})"


# ============================================================================
# МАССОВАЯ ЗАГРУЗКА ВИДЕО
# ============================================================================

class BulkUploadTask(models.Model):
    """
    Задача массовой загрузки видео на TikTok.
    Может содержать множество видео и аккаунтов.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PAUSED', 'Paused'),
    ]
    
    name = models.CharField(max_length=200, help_text="Название задачи")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Настройки загрузки
    delay_min_sec = models.IntegerField(default=30, help_text="Минимальная задержка между загрузками (сек)")
    delay_max_sec = models.IntegerField(default=60, help_text="Максимальная задержка между загрузками (сек)")
    concurrency = models.IntegerField(default=1, help_text="Количество параллельных загрузок")
    
    # Настройки видео по умолчанию
    default_caption = models.TextField(blank=True, default="", help_text="Описание по умолчанию")
    default_hashtags = models.TextField(blank=True, default="", help_text="Хештеги по умолчанию (через запятую)")
    default_privacy = models.CharField(
        max_length=20, 
        choices=[
            ('PUBLIC', 'Public'),
            ('FRIENDS', 'Friends'),
            ('PRIVATE', 'Private'),
        ],
        default='PUBLIC'
    )
    
    # Дополнительные опции TikTok
    allow_comments = models.BooleanField(default=True)
    allow_duet = models.BooleanField(default=True)
    allow_stitch = models.BooleanField(default=True)
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Логи
    log = models.TextField(blank=True, default="")
    
    class Meta:
        verbose_name = "Bulk Upload Task"
        verbose_name_plural = "Bulk Upload Tasks"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.status})"


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
    proxy = models.ForeignKey(
        TikTokProxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bulk_used_in',
        help_text="Прокси, используемый для этой задачи"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    uploaded_success_count = models.IntegerField(default=0)
    uploaded_failed_count = models.IntegerField(default=0)
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    log = models.TextField(blank=True, default="")
    
    class Meta:
        verbose_name = "Bulk Upload Account"
        verbose_name_plural = "Bulk Upload Accounts"
        unique_together = ['bulk_task', 'account']
    
    def __str__(self):
        return f"{self.account.username} in {self.bulk_task.name}"


class BulkVideo(models.Model):
    """
    Видео для массовой загрузки.
    """
    
    bulk_task = models.ForeignKey(
        BulkUploadTask,
        on_delete=models.CASCADE,
        related_name='videos'
    )
    video_file = models.FileField(upload_to='tiktok/bulk_videos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Привязка к аккаунту
    assigned_to = models.ForeignKey(
        BulkUploadAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_videos'
    )
    
    order = models.IntegerField(default=0)
    uploaded = models.BooleanField(default=False)
    
    # Индивидуальные настройки видео
    caption = models.TextField(blank=True, default="", help_text="Описание видео")
    hashtags = models.TextField(blank=True, default="", help_text="Хештеги (через запятую)")
    
    class Meta:
        verbose_name = "Bulk Video"
        verbose_name_plural = "Bulk Videos"
        ordering = ['order']
    
    def __str__(self):
        return f"Video {self.id} for {self.bulk_task.name}"
    
    def get_effective_caption(self):
        """Получить эффективное описание (индивидуальное или по умолчанию)"""
        if self.caption:
            return self.caption
        elif self.bulk_task.default_caption:
            return self.bulk_task.default_caption
        return ""
    
    def get_effective_hashtags(self):
        """Получить эффективные хештеги (индивидуальные или по умолчанию)"""
        if self.hashtags:
            return self.hashtags
        elif self.bulk_task.default_hashtags:
            return self.bulk_task.default_hashtags
        return ""


class VideoCaption(models.Model):
    """
    Описания/подписи для видео.
    Можно загрузить из файла и распределить между видео.
    """
    
    bulk_task = models.ForeignKey(
        BulkUploadTask,
        on_delete=models.CASCADE,
        related_name='captions'
    )
    text = models.TextField()
    order = models.IntegerField(default=0)
    assigned_to = models.OneToOneField(
        BulkVideo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_caption'
    )
    
    class Meta:
        verbose_name = "Video Caption"
        verbose_name_plural = "Video Captions"
        ordering = ['order']
    
    def __str__(self):
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"Caption {self.id}: {preview}"


# ============================================================================
# ПРОГРЕВ АККАУНТОВ (WARMUP)
# ============================================================================

class WarmupTask(models.Model):
    """
    Задача прогрева TikTok аккаунтов.
    Имитирует активность реального пользователя.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    name = models.CharField(max_length=120, default="Warmup Task")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Задержки между действиями
    delay_min_sec = models.IntegerField(default=15)
    delay_max_sec = models.IntegerField(default=45)
    
    # Параллельность
    concurrency = models.IntegerField(default=1, help_text="Максимум 4")
    
    # Диапазоны действий
    feed_scroll_min_count = models.IntegerField(default=5, help_text="Минимум прокруток ленты")
    feed_scroll_max_count = models.IntegerField(default=15, help_text="Максимум прокруток ленты")
    
    like_min_count = models.IntegerField(default=3, help_text="Минимум лайков")
    like_max_count = models.IntegerField(default=10, help_text="Максимум лайков")
    
    watch_video_min_count = models.IntegerField(default=5, help_text="Минимум просмотров видео")
    watch_video_max_count = models.IntegerField(default=20, help_text="Максимум просмотров видео")
    
    follow_min_count = models.IntegerField(default=0, help_text="Минимум подписок")
    follow_max_count = models.IntegerField(default=5, help_text="Максимум подписок")
    
    comment_min_count = models.IntegerField(default=0, help_text="Минимум комментариев")
    comment_max_count = models.IntegerField(default=3, help_text="Максимум комментариев")
    
    # Логи
    log = models.TextField(blank=True, default="")
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Warmup Task"
        verbose_name_plural = "Warmup Tasks"
    
    def __str__(self):
        return f"Warmup Task {self.id} - {self.status}"


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
    proxy = models.ForeignKey(
        TikTokProxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='warmup_used_in',
        help_text="Прокси, используемый для прогрева"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    log = models.TextField(blank=True, default="")
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Warmup Task Account"
        verbose_name_plural = "Warmup Task Accounts"
        unique_together = ['task', 'account']
    
    def __str__(self):
        return f"{self.account.username} in Warmup {self.task.id}"


# ============================================================================
# ПОДПИСКИ И ВЗАИМОДЕЙСТВИЯ
# ============================================================================

class FollowCategory(models.Model):
    """
    Категория целевых аккаунтов для подписок.
    """
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Follow Category"
        verbose_name_plural = "Follow Categories"
    
    def __str__(self):
        return self.name


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
    user_id = models.CharField(max_length=100, null=True, blank=True, help_text="TikTok user ID")
    full_name = models.CharField(max_length=255, blank=True, default="", help_text="Полное имя пользователя")
    is_private = models.BooleanField(default=False, help_text="Приватный ли аккаунт")
    is_verified = models.BooleanField(default=False, help_text="Верифицирован ли аккаунт")
    profile_pic_url = models.URLField(blank=True, default="", help_text="URL аватарки")
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Follow Target"
        verbose_name_plural = "Follow Targets"
        unique_together = ['category', 'username']
    
    def __str__(self):
        return f"@{self.username} ({self.category.name})"


class FollowTask(models.Model):
    """
    Задача массовых подписок/отписок.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    ACTION_CHOICES = [
        ('FOLLOW', 'Follow'),
        ('UNFOLLOW', 'Unfollow'),
    ]
    
    name = models.CharField(max_length=120, default="Follow Task")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='FOLLOW')
    
    # Категория целей
    category = models.ForeignKey(
        FollowCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='follow_tasks'
    )
    
    # Настройки
    delay_min_sec = models.IntegerField(default=30)
    delay_max_sec = models.IntegerField(default=60)
    concurrency = models.IntegerField(default=1)
    
    follow_min_count = models.IntegerField(default=10, help_text="Минимум подписок на аккаунт")
    follow_max_count = models.IntegerField(default=50, help_text="Максимум подписок на аккаунт")
    
    # Логи
    log = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Follow Task"
        verbose_name_plural = "Follow Tasks"
    
    def __str__(self):
        return f"{self.name} - {self.action}"


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
    proxy = models.ForeignKey(
        TikTokProxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='follow_used_in',
        help_text="Прокси, используемый для подписок"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    follow_count = models.IntegerField(default=0)
    last_target_id = models.IntegerField(null=True, blank=True, help_text="ID последнего обработанного таргета")
    log = models.TextField(blank=True, default="")
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Follow Task Account"
        verbose_name_plural = "Follow Task Accounts"
        unique_together = ['task', 'account']
    
    def __str__(self):
        return f"{self.account.username} in Follow Task {self.task.id}"


# ============================================================================
# УПРАВЛЕНИЕ COOKIES
# ============================================================================

class CookieRobotTask(models.Model):
    """
    Задача обновления cookies через Dolphin Anty.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    name = models.CharField(max_length=120, default="Cookie Robot Task")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    delay_min_sec = models.IntegerField(default=10)
    delay_max_sec = models.IntegerField(default=30)
    concurrency = models.IntegerField(default=2)
    
    log = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Cookie Robot Task"
        verbose_name_plural = "Cookie Robot Tasks"
    
    def __str__(self):
        return f"{self.name} - {self.status}"


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
    proxy = models.ForeignKey(
        TikTokProxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cookie_used_in',
        help_text="Прокси, используемый для обновления cookies"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    cookies_json = models.JSONField(null=True, blank=True)
    log = models.TextField(blank=True, default="")
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Cookie Robot Task Account"
        verbose_name_plural = "Cookie Robot Task Accounts"
        unique_together = ['task', 'account']
    
    def __str__(self):
        return f"{self.account.username} in Cookie Task {self.task.id}"


