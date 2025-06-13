from django.db import models
from django.utils import timezone
import uuid
import random
import json


class Proxy(models.Model):
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
    
    host = models.GenericIPAddressField()
    port = models.IntegerField()
    username = models.CharField(max_length=200, null=True, blank=True)
    password = models.CharField(max_length=200, null=True, blank=True)
    proxy_type = models.CharField(max_length=10, choices=PROXY_TYPE_CHOICES, default='HTTP')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive')
    last_checked = models.DateTimeField(null=True, blank=True)
    assigned_account = models.ForeignKey('InstagramAccount', null=True, blank=True, on_delete=models.SET_NULL, related_name='proxy_assignment')
    
    # Additional fields from existing model kept for backwards compatibility
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    last_verified = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    country = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        verbose_name = "Proxy"
        verbose_name_plural = "Proxies"
        # Make sure we can have same host+port with different credentials
        unique_together = ['host', 'port', 'username', 'password']
    
    def __str__(self):
        return f"{self.proxy_type}://{self.host}:{self.port}"
    
    def to_dict(self):
        """Converts proxy to a dictionary for use in the bot"""
        return {
            "type": self.proxy_type.lower(),
            "host": self.host,
            "port": self.port,
            "user": self.username,
            "pass": self.password
        }


class InstagramAccount(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('BLOCKED', 'Blocked'),
        ('LIMITED', 'Limited'),
        ('INACTIVE', 'Inactive'),
        ('PHONE_VERIFICATION_REQUIRED', 'Phone Verification Required'),
        ('HUMAN_VERIFICATION_REQUIRED', 'Human Verification Required'),
    ]
    
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    email_username = models.CharField(max_length=100, null=True, blank=True)
    email_password = models.CharField(max_length=100, null=True, blank=True)
    tfa_secret = models.CharField(max_length=100, null=True, blank=True)
    proxy = models.ForeignKey(Proxy, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounts')
    current_proxy = models.ForeignKey(Proxy, on_delete=models.SET_NULL, null=True, blank=True, related_name='active_accounts')
    dolphin_profile_id = models.CharField(max_length=100, null=True, blank=True, help_text="Dolphin Anty browser profile ID")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='ACTIVE')
    last_used = models.DateTimeField(null=True, blank=True)
    last_warmed = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, default="")
    
    class Meta:
        verbose_name = "Instagram account"
        verbose_name_plural = "Instagram accounts"
    
    def __str__(self):
        return self.username
    
    def to_dict(self):
        """Converts account to a dictionary for use in the bot"""
        data = {
            "username": self.username,
            "password": self.password,
        }
        
        # Add 2FA secret if exists
        if self.tfa_secret:
            data["tfa_secret"] = self.tfa_secret
        
        # Add email verification credentials if they exist
        if self.email_username:
            data["email_username"] = self.email_username
        
        if self.email_password:
            data["email_password"] = self.email_password
            
        # Add proxy if exists
        if self.proxy:
            data["proxy"] = self.proxy.to_dict()
            
        # Add Dolphin profile if exists
        if self.dolphin_profile_id:
            data["dolphin_profile_id"] = self.dolphin_profile_id
            
        return data
    
    def mark_as_used(self):
        """Mark account as used"""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])
    
    def mark_as_warmed(self):
        """Mark account as warmed up"""
        self.last_warmed = timezone.now()
        self.save(update_fields=['last_warmed'])
    
    def get_random_proxy(self):
        """Get a random active proxy if none is assigned"""
        if self.proxy and self.proxy.is_active:
            return self.proxy
            
        active_proxies = Proxy.objects.filter(is_active=True)
        if active_proxies.exists():
            return random.choice(active_proxies)
        return None


class InstagramCookies(models.Model):
    account = models.OneToOneField(InstagramAccount, on_delete=models.CASCADE, related_name='cookies')
    cookies_data = models.JSONField()  # Store cookies in JSON format
    last_updated = models.DateTimeField(auto_now=True)
    is_valid = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Instagram cookies"
        verbose_name_plural = "Instagram cookies"
    
    def __str__(self):
        return f"Cookies for {self.account.username}"


class DolphinCookieRobotTask(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    account = models.ForeignKey(InstagramAccount, on_delete=models.CASCADE, related_name='cookie_robot_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    urls = models.JSONField(default=list)  # List of URLs to visit
    headless = models.BooleanField(default=True)
    imageless = models.BooleanField(default=False)
    log = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Dolphin Cookie Robot Task"
        verbose_name_plural = "Dolphin Cookie Robot Tasks"
    
    def __str__(self):
        return f"Cookie Robot Task {self.id} - {self.account.username} - {self.status}"


class UploadTask(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    account = models.ForeignKey(InstagramAccount, on_delete=models.CASCADE, related_name='tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    log = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Task {self.id} - {self.account.username} - {self.status}"


class VideoFile(models.Model):
    task = models.ForeignKey(
        UploadTask,
        on_delete=models.CASCADE,
        related_name='video_files'
    )
    video_file = models.FileField(upload_to='bot/videos/')
    caption = models.TextField(blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Video for task {self.task.id}"


class BulkUploadTask(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PARTIALLY_COMPLETED', 'Partially Completed'),
    ]
    
    name = models.CharField(max_length=100, default="Bulk Upload")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    log = models.TextField(blank=True, default="")
    
    # Random identifier for the upload group
    upload_id = models.UUIDField(default=uuid.uuid4, editable=False)
    
    # Location and mentions for all videos (optional)
    default_location = models.CharField(max_length=200, blank=True, default="", help_text="Шаблон локации для копирования в видео (не применяется автоматически)")
    default_mentions = models.TextField(blank=True, default="", help_text="Шаблон упоминаний для копирования в видео (не применяются автоматически)")
    
    def __str__(self):
        return f"Bulk Upload {self.id} - {self.status}"
    
    def get_completed_count(self):
        """Get count of completed individual tasks"""
        return self.accounts.filter(status='COMPLETED').count()
    
    def get_total_count(self):
        """Get total count of individual tasks"""
        return self.accounts.count()
    
    def get_completion_percentage(self):
        """Calculate completion percentage"""
        total = self.get_total_count()
        if total == 0:
            return 0
        return int(self.get_completed_count() / total * 100)
    
    def get_default_mentions_list(self):
        """Get default mentions as a list"""
        if not self.default_mentions:
            return []
        return [mention.strip() for mention in self.default_mentions.split('\n') if mention.strip()]


class BulkUploadAccount(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PHONE_VERIFICATION_REQUIRED', 'Phone Verification Required'),
        ('HUMAN_VERIFICATION_REQUIRED', 'Human Verification Required'),
    ]
    
    bulk_task = models.ForeignKey(
        BulkUploadTask,
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    account = models.ForeignKey(
        InstagramAccount,
        on_delete=models.CASCADE,
        related_name='bulk_uploads'
    )
    proxy = models.ForeignKey(
        Proxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bulk_used_in'
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    log = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.account.username} in {self.bulk_task.name}"


class BulkVideo(models.Model):
    bulk_task = models.ForeignKey(
        BulkUploadTask,
        on_delete=models.CASCADE,
        related_name='videos'
    )
    video_file = models.FileField(upload_to='bot/bulk_videos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(
        BulkUploadAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_videos'
    )
    order = models.IntegerField(default=0)
    
    # Individual location and mentions (override defaults if set)
    location = models.CharField(max_length=200, blank=True, default="", help_text="Локация для этого видео (переопределяет общую)")
    mentions = models.TextField(blank=True, default="", help_text="Упоминания для этого видео, по одному на строку (переопределяет общие)")
    
    def __str__(self):
        return f"Video {self.id} for {self.bulk_task.name}"
    
    class Meta:
        ordering = ['order']
    
    def get_effective_location(self):
        """Get the effective location (only individual, not default)"""
        return self.location if self.location else None
    
    def get_effective_mentions_list(self):
        """Get the effective mentions as a list (only individual, not default)"""
        if self.mentions:
            return [mention.strip() for mention in self.mentions.split('\n') if mention.strip()]
        return []


class VideoTitle(models.Model):
    bulk_task = models.ForeignKey(
        BulkUploadTask,
        on_delete=models.CASCADE,
        related_name='titles'
    )
    title = models.TextField()
    used = models.BooleanField(default=False)
    assigned_to = models.OneToOneField(
        BulkVideo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='title_data'
    )
    
    def __str__(self):
        return f"Title {self.id} for Bulk Upload {self.bulk_task.id}"
