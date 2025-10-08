from django.db import models
from django.utils import timezone
import uuid
import random
import json


class Tag(models.Model):
    """Tags for categorizing Instagram accounts"""
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#6c757d', help_text="Hex color code for UI display")
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['name']
    
    def __str__(self):
        return self.name


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
    
    host = models.CharField(max_length=255, help_text="Proxy host (IP address or domain name)")
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
    # Link for IP change functionality
    ip_change_url = models.URLField(max_length=500, null=True, blank=True, help_text="URL for changing proxy IP address")
    # External IP address (resolved from proxy)
    external_ip = models.GenericIPAddressField(null=True, blank=True, help_text="External IP address when using this proxy")
    
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
            "pass": self.password,
            "country": self.country,
            "city": self.city,
        }


class InstagramAccount(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('BLOCKED', 'Blocked'),
        ('LIMITED', 'Limited'),
        ('INACTIVE', 'Inactive'),
        ('PHONE_VERIFICATION_REQUIRED', 'Phone Verification Required'),
        ('HUMAN_VERIFICATION_REQUIRED', 'Human Verification Required'),
        ('SUSPENDED', 'Suspended'),
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
    # New: phone number used for mobile device profile and account verification
    phone_number = models.CharField(max_length=32, null=True, blank=True)
    # Link to client from integrated cabinet
    client = models.ForeignKey('cabinet.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='accounts')
    # Tag for categorizing account (only one tag per account)
    tag = models.ForeignKey(Tag, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounts', help_text="Tag for categorizing this account")
    # Locale in Dolphin-style, e.g. ru_BY, en_IN, es_CL, es_MX, pt_BR
    locale = models.CharField(max_length=5, default='ru_BY', help_text="Dolphin-style locale, e.g. ru_BY en_IN es_CL es_MX pt_BR")

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
            
        # Add proxy if exists - use current_proxy as the primary proxy
        if self.current_proxy:
            data["proxy"] = self.current_proxy.to_dict()
        elif self.proxy:
            # Fallback to proxy field if current_proxy is not set
            data["proxy"] = self.proxy.to_dict()
            
        # Add Dolphin profile if exists
        if self.dolphin_profile_id:
            data["dolphin_profile_id"] = self.dolphin_profile_id
            
        # Add phone if exists
        if self.phone_number:
            data["phone"] = self.phone_number
        
        # Add locale and language mapping
        try:
            acc_locale = (self.locale or 'ru_BY')
        except Exception:
            acc_locale = 'ru_BY'
        data["locale"] = acc_locale
        # Map to language code: en, ru, es, pt
        try:
            lang = acc_locale.split('_', 1)[0].lower()
            if lang not in ("en", "ru", "es", "pt"):
                lang = "ru"
        except Exception:
            lang = "ru"
        data["language"] = lang
            
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
        # Use current_proxy as the primary proxy
        if self.current_proxy and self.current_proxy.is_active:
            return self.current_proxy
        elif self.proxy and self.proxy.is_active:
            # Fallback to proxy field if current_proxy is not set
            return self.proxy
            
        active_proxies = Proxy.objects.filter(is_active=True)
        if active_proxies.exists():
            return random.choice(active_proxies)
        return None
    
    def save(self, *args, **kwargs):
        """Override save method to synchronize proxy and current_proxy fields"""
        # If proxy is set but current_proxy is different, sync them
        if self.proxy and self.proxy != self.current_proxy:
            self.current_proxy = self.proxy
        # If proxy is None but current_proxy is set, sync them
        elif self.proxy is None and self.current_proxy is not None:
            self.current_proxy = None
        
        super().save(*args, **kwargs)


# New: Persistent mobile device/session profile tied to account
class InstagramDevice(models.Model):
    account = models.OneToOneField(InstagramAccount, on_delete=models.CASCADE, related_name='device')
    device_settings = models.JSONField(default=dict, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    session_settings = models.JSONField(null=True, blank=True)
    session_file = models.CharField(max_length=255, null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_avatar_change_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Instagram device"
        verbose_name_plural = "Instagram devices"
    
    def __str__(self):
        return f"Device for {self.account.username}"


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


class UploadTask(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PARTIALLY_COMPLETED', 'Partially Completed'),
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
    default_location = models.CharField(max_length=200, blank=True, default="", help_text="Location template to copy to videos (not applied automatically)")
    default_mentions = models.TextField(blank=True, default="", help_text="Mentions template to copy to videos (not applied automatically)")
    
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
        ('SUSPENDED', 'Suspended'),
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
    # Per-account upload counters
    uploaded_success_count = models.IntegerField(default=0)
    uploaded_failed_count = models.IntegerField(default=0)
    
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
    location = models.CharField(max_length=200, blank=True, default="", help_text="Location for this video (overrides default)")
    mentions = models.TextField(blank=True, default="", help_text="Mentions for this video, one per line (overrides default)")
    
    def __str__(self):
        return f"Video {self.id} for {self.bulk_task.name}"
    
    class Meta:
        ordering = ['order']
    
    def get_effective_location(self):
        """Get the effective location (individual or default from task)"""
        if self.location:
            return self.location
        elif self.bulk_task.default_location:
            return self.bulk_task.default_location
        return None
    
    def get_effective_mentions_list(self):
        """Get the effective mentions as a list (individual or default from task)"""
        if self.mentions:
            return [mention.strip() for mention in self.mentions.split('\n') if mention.strip()]
        elif self.bulk_task.default_mentions:
            return [mention.strip() for mention in self.bulk_task.default_mentions.split('\n') if mention.strip()]
        return []


# New: Title model for bulk uploads
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
        return f"Title {self.id} for {self.bulk_task.name}"


# New: Avatar change task models
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
    account = models.ForeignKey(InstagramAccount, on_delete=models.CASCADE, related_name='avatar_tasks')
    proxy = models.ForeignKey(Proxy, on_delete=models.SET_NULL, null=True, blank=True, related_name='avatar_used_in')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    log = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.account.username} in Avatar Task {self.task.id}"


class AvatarImage(models.Model):
    task = models.ForeignKey(AvatarChangeTask, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='bot/avatars/')
    order = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"AvatarImage {self.id} for Task {self.task.id}"


class FollowCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Follow category"
        verbose_name_plural = "Follow categories"

    def __str__(self):
        return self.name


class FollowTarget(models.Model):
    """A target to follow: stores username and resolved user_id (pk)."""
    category = models.ForeignKey(FollowCategory, on_delete=models.CASCADE, related_name='targets')
    username = models.CharField(max_length=150)
    user_id = models.BigIntegerField(null=True, blank=True)
    full_name = models.CharField(max_length=255, blank=True, default="")
    is_private = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    profile_pic_url = models.URLField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('category', 'username')
        verbose_name = "Follow target"
        verbose_name_plural = "Follow targets"

    def __str__(self):
        return f"{self.username} ({self.user_id or 'unresolved'})"


class FollowTask(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    name = models.CharField(max_length=120, default="Follow Task")
    category = models.ForeignKey(FollowCategory, on_delete=models.CASCADE, related_name='tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    delay_min_sec = models.IntegerField(default=10)
    delay_max_sec = models.IntegerField(default=25)
    concurrency = models.IntegerField(default=1)
    # New: random range of follows per account
    follow_min_count = models.IntegerField(default=3)
    follow_max_count = models.IntegerField(default=10)
    log = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Follow Task {self.id} - {self.status}"


class FollowTaskAccount(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    task = models.ForeignKey(FollowTask, on_delete=models.CASCADE, related_name='accounts')
    account = models.ForeignKey(InstagramAccount, on_delete=models.CASCADE, related_name='follow_tasks')
    proxy = models.ForeignKey(Proxy, on_delete=models.SET_NULL, null=True, blank=True, related_name='follow_used_in')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    log = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    # Progress: last processed target id
    last_target_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.account.username} in Follow Task {self.task.id}"


# ===== Bulk Login Task Models =====
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


# ===== Hashtag Analytics =====
class HashtagAnalytics(models.Model):
    SOCIAL_NETWORK_CHOICES = [
        ('INSTAGRAM', 'Instagram'),
        ('YOUTUBE', 'YouTube'),
        ('TIKTOK', 'TikTok'),
    ]
    
    hashtag = models.CharField(max_length=150, db_index=True)
    total_medias_reported = models.IntegerField(default=0)
    fetched_medias = models.IntegerField(default=0)
    analyzed_medias = models.IntegerField(default=0)
    pages_loaded = models.IntegerField(default=0)
    total_views = models.BigIntegerField(default=0, blank=True)
    average_views = models.FloatField(default=0.0)
    # New metrics for engagement tracking
    total_likes = models.BigIntegerField(default=0, blank=True)
    total_comments = models.BigIntegerField(default=0, blank=True)
    engagement_rate = models.FloatField(default=0.0, help_text="(likes+comments)/views, 0 if views == 0")
    info_json = models.JSONField(null=True, blank=True)
    
    # Manual analytics fields
    client = models.ForeignKey(
        'cabinet.Client',
        on_delete=models.CASCADE,
        related_name='hashtag_analytics',
        null=True,
        blank=True,
        help_text="Client for manual analytics (null for automatic hashtag analysis)"
    )
    social_network = models.CharField(
        max_length=20,
        choices=SOCIAL_NETWORK_CHOICES,
        default='INSTAGRAM',
        help_text="Social network platform"
    )
    is_manual = models.BooleanField(
        default=False,
        help_text="True if this is manually entered analytics, False if automatic hashtag analysis"
    )
    
    # Additional manual analytics fields
    total_shares = models.BigIntegerField(default=0, blank=True, help_text="Total shares/reposts")
    total_followers = models.BigIntegerField(default=0, blank=True, help_text="Current follower count")
    growth_rate = models.FloatField(default=0.0, blank=True, help_text="Follower growth rate (%)")
    
    # Platform-specific metrics
    instagram_stories_views = models.BigIntegerField(default=0, blank=True, help_text="Instagram stories views")
    instagram_reels_views = models.BigIntegerField(default=0, blank=True, help_text="Instagram reels views")
    youtube_subscribers = models.BigIntegerField(default=0, blank=True, help_text="YouTube subscribers")
    youtube_watch_time = models.BigIntegerField(default=0, blank=True, help_text="YouTube watch time (minutes)")
    tiktok_video_views = models.BigIntegerField(default=0, blank=True, help_text="TikTok video views")
    tiktok_profile_views = models.BigIntegerField(default=0, blank=True, help_text="TikTok profile views")
    
    # Period for manual analytics
    period_start = models.DateField(null=True, blank=True, help_text="Start date of analytics period")
    period_end = models.DateField(null=True, blank=True, help_text="End date of analytics period")
    notes = models.TextField(blank=True, default="", help_text="Additional notes about the analytics")
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_hashtag_analytics',
        help_text="Admin user who created this manual analytics entry"
    )
    
    # Advanced metrics for account-level statistics
    total_accounts = models.IntegerField(default=0, blank=True, help_text="Total number of accounts analyzed")
    avg_videos_per_account = models.FloatField(default=0.0, blank=True, help_text="Average videos per account")
    max_videos_per_account = models.IntegerField(default=0, blank=True, help_text="Maximum videos per account")
    avg_views_per_video = models.FloatField(default=0.0, blank=True, help_text="Average views per video")
    max_views_per_video = models.BigIntegerField(default=0, blank=True, help_text="Maximum views per video")
    avg_views_per_account = models.FloatField(default=0.0, blank=True, help_text="Average views per account")
    max_views_per_account = models.BigIntegerField(default=0, blank=True, help_text="Maximum views per account")
    avg_likes_per_video = models.FloatField(default=0.0, blank=True, help_text="Average likes per video")
    max_likes_per_video = models.BigIntegerField(default=0, blank=True, help_text="Maximum likes per video")
    avg_likes_per_account = models.FloatField(default=0.0, blank=True, help_text="Average likes per account")
    max_likes_per_account = models.BigIntegerField(default=0, blank=True, help_text="Maximum likes per account")
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now, help_text="Date and time when analytics data was collected")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['hashtag', 'created_at']),
            models.Index(fields=['client', 'social_network', 'created_at']),
            models.Index(fields=['is_manual', 'created_at']),
        ]
        verbose_name = 'Hashtag analytics'
        verbose_name_plural = 'Hashtag analytics'
        # Note: unique_together with date fields is complex, we'll handle duplicates in form validation

    def __str__(self):
        if self.is_manual and self.client:
            return f"{self.client.name} - {self.get_social_network_display()} - #{self.hashtag} ({self.created_at:%Y-%m-%d})"
        return f"#{self.hashtag} at {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def total_videos(self) -> int:
        """Alias for analyzed_medias to match personal_cab wording."""
        try:
            return int(self.analyzed_medias or 0)
        except Exception:
            return 0
    
    def get_platform_specific_metrics(self):
        """Get platform-specific metrics as a dictionary"""
        metrics = {}
        
        if self.social_network == 'INSTAGRAM':
            metrics.update({
                'stories_views': self.instagram_stories_views,
                'reels_views': self.instagram_reels_views,
            })
        elif self.social_network == 'YOUTUBE':
            metrics.update({
                'subscribers': self.youtube_subscribers,
                'watch_time': self.youtube_watch_time,
            })
        elif self.social_network == 'TIKTOK':
            metrics.update({
                'video_views': self.tiktok_video_views,
                'profile_views': self.tiktok_profile_views,
            })
        
        return metrics
    
    def save(self, *args, **kwargs):
        # Ensure growth_rate is never None
        if self.growth_rate is None:
            self.growth_rate = 0.0
        
        # Calculate derived metrics for manual analytics
        if self.is_manual and self.analyzed_medias and self.analyzed_medias > 0:
            self.average_views = (self.total_views or 0) / self.analyzed_medias
        elif not self.is_manual and self.analyzed_medias and self.analyzed_medias > 0:
            # For automatic hashtag analysis
            self.average_views = (self.total_views or 0) / self.analyzed_medias
        
        if self.total_views and self.total_views > 0:
            total_engagement = (self.total_likes or 0) + (self.total_comments or 0) + (self.total_shares or 0)
            self.engagement_rate = total_engagement / self.total_views
        
        # Auto-calculate advanced metrics if not manually set
        if self.analyzed_medias and self.analyzed_medias > 0:
            # Avg Views per Video (if not already set or is 0)
            if not self.avg_views_per_video:
                self.avg_views_per_video = (self.total_views or 0) / self.analyzed_medias
            
            # Avg Likes per Video (if not already set or is 0)
            if not self.avg_likes_per_video:
                self.avg_likes_per_video = (self.total_likes or 0) / self.analyzed_medias
        
        if self.total_accounts and self.total_accounts > 0:
            # Avg Videos per Account (if not already set or is 0)
            if not self.avg_videos_per_account:
                self.avg_videos_per_account = (self.analyzed_medias or 0) / self.total_accounts
            
            # Avg Views per Account (if not already set or is 0)
            if not self.avg_views_per_account:
                self.avg_views_per_account = (self.total_views or 0) / self.total_accounts
            
            # Avg Likes per Account (if not already set or is 0)
            if not self.avg_likes_per_account:
                self.avg_likes_per_account = (self.total_likes or 0) / self.total_accounts
        
        super().save(*args, **kwargs)


# Per-account aggregated analytics snapshots
class AccountAnalytics(models.Model):
    account = models.ForeignKey(InstagramAccount, on_delete=models.CASCADE, related_name='analytics')
    total_videos = models.IntegerField(default=0)
    total_views = models.BigIntegerField(default=0)
    total_likes = models.BigIntegerField(default=0)
    total_comments = models.BigIntegerField(default=0)
    average_views = models.FloatField(default=0.0)
    engagement_rate = models.FloatField(default=0.0, help_text="(likes+comments)/views, 0 if views == 0")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['account', 'created_at']),
        ]
        verbose_name = 'Account analytics'
        verbose_name_plural = 'Account analytics'

    def __str__(self):
        return f"{self.account.username} analytics @ {self.created_at:%Y-%m-%d %H:%M}"

class BulkLoginAccount(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PHONE_VERIFICATION_REQUIRED', 'Phone Verification Required'),
        ('HUMAN_VERIFICATION_REQUIRED', 'Human Verification Required'),
        ('SUSPENDED', 'Suspended'),
    ]

    bulk_task = models.ForeignKey(BulkLoginTask, on_delete=models.CASCADE, related_name='accounts')
    account = models.ForeignKey(InstagramAccount, on_delete=models.CASCADE, related_name='bulk_logins')
    proxy = models.ForeignKey(Proxy, on_delete=models.SET_NULL, null=True, blank=True, related_name='bulk_login_used_in')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    log = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.account.username} in {self.bulk_task.name}"


# New: Bio link change task models
class BioLinkChangeTask(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    name = models.CharField(max_length=120, default="Bio Link Change")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    link_url = models.URLField(max_length=500)
    delay_min_sec = models.IntegerField(default=15)
    delay_max_sec = models.IntegerField(default=45)
    concurrency = models.IntegerField(default=1)
    log = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bio Task {self.id} - {self.status}"


class BioLinkChangeTaskAccount(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    task = models.ForeignKey(BioLinkChangeTask, on_delete=models.CASCADE, related_name='accounts')
    account = models.ForeignKey(InstagramAccount, on_delete=models.CASCADE, related_name='bio_tasks')
    proxy = models.ForeignKey(Proxy, on_delete=models.SET_NULL, null=True, blank=True, related_name='bio_used_in')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    log = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.account.username} in Bio Task {self.task.id}"


# New: Warmup task models
class WarmupTask(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    name = models.CharField(max_length=120, default="Warmup Task")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # Human-like delays between accounts
    delay_min_sec = models.IntegerField(default=15)
    delay_max_sec = models.IntegerField(default=45)

    # Concurrency cap will be enforced at 4 in forms and workers
    concurrency = models.IntegerField(default=1)

    # Optional: use follow category for small follow actions during warmup
    follow_category = models.ForeignKey('FollowCategory', on_delete=models.SET_NULL, null=True, blank=True, related_name='warmup_tasks')

    # Action ranges
    feed_scroll_min_count = models.IntegerField(default=1)
    feed_scroll_max_count = models.IntegerField(default=3)

    like_min_count = models.IntegerField(default=0)
    like_max_count = models.IntegerField(default=3)

    view_stories_min_count = models.IntegerField(default=0)
    view_stories_max_count = models.IntegerField(default=5)

    follow_min_count = models.IntegerField(default=0)
    follow_max_count = models.IntegerField(default=2)

    log = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Warmup Task {self.id} - {self.status}"


class WarmupTaskAccount(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    task = models.ForeignKey(WarmupTask, on_delete=models.CASCADE, related_name='accounts')
    account = models.ForeignKey(InstagramAccount, on_delete=models.CASCADE, related_name='warmup_tasks')
    proxy = models.ForeignKey(Proxy, on_delete=models.SET_NULL, null=True, blank=True, related_name='warmup_used_in')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    log = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.account.username} in Warmup Task {self.task.id}"


# ===== YouTube Shorts Models =====
class YouTubeAccount(models.Model):
    """YouTube account for Shorts uploading"""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('BLOCKED', 'Blocked'),
        ('LIMITED', 'Limited'),
        ('INACTIVE', 'Inactive'),
        ('PHONE_VERIFICATION_REQUIRED', 'Phone Verification Required'),
        ('HUMAN_VERIFICATION_REQUIRED', 'Human Verification Required'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    email = models.EmailField(unique=True, help_text="YouTube/Google account email")
    password = models.CharField(max_length=200)
    channel_name = models.CharField(max_length=200, blank=True, default="")
    channel_id = models.CharField(max_length=200, blank=True, default="", help_text="YouTube channel ID")
    recovery_email = models.EmailField(blank=True, default="")
    phone_number = models.CharField(max_length=32, null=True, blank=True)
    tfa_secret = models.CharField(max_length=100, null=True, blank=True, help_text="2FA secret for TOTP")
    
    proxy = models.ForeignKey(
        Proxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='youtube_accounts'
    )
    current_proxy = models.ForeignKey(
        Proxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_youtube_accounts'
    )
    dolphin_profile_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Dolphin Anty browser profile ID"
    )
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='ACTIVE')
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, default="")
    
    # Link to client from integrated cabinet
    client = models.ForeignKey(
        'cabinet.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='youtube_accounts'
    )
    
    # Locale for browser profile
    locale = models.CharField(
        max_length=5,
        default='en_US',
        help_text="Browser locale, e.g. en_US, ru_RU, es_ES"
    )
    
    class Meta:
        verbose_name = "YouTube Account"
        verbose_name_plural = "YouTube Accounts"
    
    def __str__(self):
        return self.email
    
    def to_dict(self):
        """Converts YouTube account to a dictionary for use in the bot"""
        data = {
            "email": self.email,
            "password": self.password,
        }
        
        # Add recovery email if exists
        if self.recovery_email:
            data["recovery_email"] = self.recovery_email
        
        # Add channel info if exists
        if self.channel_name:
            data["channel_name"] = self.channel_name
        if self.channel_id:
            data["channel_id"] = self.channel_id
        
        # Add 2FA secret if exists
        if self.tfa_secret:
            data["tfa_secret"] = self.tfa_secret
            
        # Add proxy if exists - use current_proxy as the primary proxy
        if self.current_proxy:
            data["proxy"] = self.current_proxy.to_dict()
        elif self.proxy:
            # Fallback to proxy field if current_proxy is not set
            data["proxy"] = self.proxy.to_dict()
            
        # Add Dolphin profile if exists
        if self.dolphin_profile_id:
            data["dolphin_profile_id"] = self.dolphin_profile_id
            
        # Add phone if exists
        if self.phone_number:
            data["phone"] = self.phone_number
        
        # Add locale and language mapping
        try:
            acc_locale = (self.locale or 'en_US')
        except Exception:
            acc_locale = 'en_US'
        data["locale"] = acc_locale
        # Map to language code: en, ru, es, pt
        try:
            lang = acc_locale.split('_', 1)[0].lower()
            if lang not in ("en", "ru", "es", "pt"):
                lang = "en"
        except Exception:
            lang = "en"
        data["language"] = lang
        
        # Add client info if exists
        if self.client:
            data["client"] = {
                "id": self.client.id,
                "name": self.client.name,
            }
        
        # Add status and metadata
        data["status"] = self.status
        data["notes"] = self.notes
        data["created_at"] = self.created_at.isoformat() if self.created_at else None
        data["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        data["last_used"] = self.last_used.isoformat() if self.last_used else None
        
        # Add browser/device data if exists
        try:
            if hasattr(self, 'device') and self.device:
                device_data = {}
                if self.device.user_agent:
                    device_data["user_agent"] = self.device.user_agent
                if self.device.device_settings:
                    device_data["device_settings"] = self.device.device_settings
                if self.device.session_settings:
                    device_data["session_settings"] = self.device.session_settings
                if device_data:
                    data["device"] = device_data
        except Exception:
            pass
        
        # Add cookies if exists
        try:
            if hasattr(self, 'cookies') and self.cookies and self.cookies.is_valid:
                data["cookies"] = self.cookies.cookies_data
        except Exception:
            pass
        
        # Add Dolphin profile snapshot if exists
        try:
            if hasattr(self, 'dolphin_snapshot') and self.dolphin_snapshot:
                snapshot_data = {
                    "profile_id": self.dolphin_snapshot.profile_id,
                    "payload_json": self.dolphin_snapshot.payload_json,
                    "response_json": self.dolphin_snapshot.response_json,
                    "meta_json": self.dolphin_snapshot.meta_json,
                    "created_at": self.dolphin_snapshot.created_at.isoformat() if self.dolphin_snapshot.created_at else None,
                    "updated_at": self.dolphin_snapshot.updated_at.isoformat() if self.dolphin_snapshot.updated_at else None,
                }
                data["dolphin_snapshot"] = snapshot_data
        except Exception:
            pass
            
        return data
    
    def mark_as_used(self):
        """Mark account as used"""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])


class DolphinProfileSnapshot(models.Model):
    """Full snapshot of Dolphin profile payload/response to be able to recreate 1:1."""
    # Support both Instagram and YouTube accounts
    instagram_account = models.OneToOneField(
        InstagramAccount, 
        on_delete=models.CASCADE, 
        related_name='dolphin_snapshot',
        null=True,
        blank=True
    )
    youtube_account = models.OneToOneField(
        YouTubeAccount,
        on_delete=models.CASCADE,
        related_name='dolphin_snapshot', 
        null=True,
        blank=True
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
        account_name = ""
        if self.instagram_account:
            account_name = self.instagram_account.username
        elif self.youtube_account:
            account_name = self.youtube_account.email
        return f"Snapshot for {account_name} ({self.profile_id})"
    
    @property
    def account(self):
        """Get the associated account (Instagram or YouTube)"""
        return self.instagram_account or self.youtube_account


class YouTubeDevice(models.Model):
    """YouTube device and browser data for account"""
    account = models.OneToOneField(YouTubeAccount, on_delete=models.CASCADE, related_name='device')
    device_settings = models.JSONField(default=dict, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, default="")
    session_settings = models.JSONField(null=True, blank=True)
    session_file = models.CharField(max_length=255, null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "YouTube device"
        verbose_name_plural = "YouTube devices"
    
    def __str__(self):
        return f"Device for {self.account.email}"


class YouTubeCookies(models.Model):
    """YouTube cookies storage"""
    account = models.OneToOneField(YouTubeAccount, on_delete=models.CASCADE, related_name='cookies')
    cookies_data = models.JSONField()  # Store cookies in JSON format
    last_updated = models.DateTimeField(auto_now=True)
    is_valid = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "YouTube cookies"
        verbose_name_plural = "YouTube cookies"
    
    def __str__(self):
        return f"Cookies for {self.account.email}"


class DolphinCookieRobotTask(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    # Support both Instagram and YouTube accounts
    instagram_account = models.ForeignKey(
        InstagramAccount, 
        on_delete=models.CASCADE, 
        related_name='cookie_robot_tasks',
        null=True,
        blank=True
    )
    youtube_account = models.ForeignKey(
        YouTubeAccount,
        on_delete=models.CASCADE,
        related_name='cookie_robot_tasks',
        null=True,
        blank=True
    )
    
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
        account_name = ""
        if self.instagram_account:
            account_name = self.instagram_account.username
        elif self.youtube_account:
            account_name = self.youtube_account.email
        return f"Cookie Robot Task {self.id} - {account_name} - {self.status}"
    
    @property
    def account(self):
        """Get the associated account (Instagram or YouTube)"""
        return self.instagram_account or self.youtube_account


class YouTubeShortsBulkUploadTask(models.Model):
    """Bulk upload task for YouTube Shorts"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PARTIALLY_COMPLETED', 'Partially Completed'),
    ]
    
    name = models.CharField(max_length=200, default="YouTube Shorts Bulk Upload")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    log = models.TextField(blank=True, default="")
    
    # Random identifier for the upload group
    upload_id = models.UUIDField(default=uuid.uuid4, editable=False)
    
    # Default settings for videos (optional)
    default_visibility = models.CharField(
        max_length=20,
        choices=[
            ('PUBLIC', 'Public'),
            ('UNLISTED', 'Unlisted'),
            ('PRIVATE', 'Private'),
        ],
        default='PUBLIC',
        help_text="Default visibility for uploaded shorts"
    )
    default_category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Default YouTube category"
    )
    default_tags = models.TextField(
        blank=True,
        default="",
        help_text="Default tags, one per line"
    )
    
    def __str__(self):
        return f"YouTube Shorts Upload {self.id} - {self.status}"
    
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


class YouTubeShortsBulkUploadAccount(models.Model):
    """Link between YouTube account and bulk upload task"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PHONE_VERIFICATION_REQUIRED', 'Phone Verification Required'),
        ('HUMAN_VERIFICATION_REQUIRED', 'Human Verification Required'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    bulk_task = models.ForeignKey(
        YouTubeShortsBulkUploadTask,
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    account = models.ForeignKey(
        YouTubeAccount,
        on_delete=models.CASCADE,
        related_name='bulk_uploads'
    )
    proxy = models.ForeignKey(
        Proxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='youtube_bulk_used_in'
    )
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    log = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Per-account upload counters
    uploaded_success_count = models.IntegerField(default=0)
    uploaded_failed_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.account.email} in {self.bulk_task.name}"


class YouTubeShortsVideo(models.Model):
    """Video file for YouTube Shorts bulk upload"""
    bulk_task = models.ForeignKey(
        YouTubeShortsBulkUploadTask,
        on_delete=models.CASCADE,
        related_name='videos'
    )
    video_file = models.FileField(upload_to='youtube/shorts_videos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(
        YouTubeShortsBulkUploadAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_videos'
    )
    order = models.IntegerField(default=0)
    
    # Individual video settings (override defaults if set)
    visibility = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Visibility for this video (overrides default)"
    )
    category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Category for this video (overrides default)"
    )
    tags = models.TextField(
        blank=True,
        default="",
        help_text="Tags for this video, one per line (overrides default)"
    )
    
    def __str__(self):
        return f"YouTube Short {self.id} for {self.bulk_task.name}"
    
    class Meta:
        ordering = ['order']
    
    def get_effective_visibility(self):
        """Get the effective visibility (individual or default from task)"""
        if self.visibility:
            return self.visibility
        elif self.bulk_task.default_visibility:
            return self.bulk_task.default_visibility
        return 'PUBLIC'
    
    def get_effective_category(self):
        """Get the effective category (individual or default from task)"""
        if self.category:
            return self.category
        elif self.bulk_task.default_category:
            return self.bulk_task.default_category
        return None
    
    def get_effective_tags_list(self):
        """Get the effective tags as a list (individual or default from task)"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split('\n') if tag.strip()]
        elif self.bulk_task.default_tags:
            return [tag.strip() for tag in self.bulk_task.default_tags.split('\n') if tag.strip()]
        return []


class YouTubeShortsVideoTitle(models.Model):
    """Title/description for YouTube Shorts videos"""
    bulk_task = models.ForeignKey(
        YouTubeShortsBulkUploadTask,
        on_delete=models.CASCADE,
        related_name='titles'
    )
    title = models.CharField(max_length=100, help_text="Video title (max 100 chars for Shorts)")
    description = models.TextField(blank=True, default="", help_text="Video description")
    used = models.BooleanField(default=False)
    assigned_to = models.OneToOneField(
        YouTubeShortsVideo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='title_data'
    )
    
    def __str__(self):
        return f"Title {self.id} for {self.bulk_task.name}"


# ===== Analytics Models =====
class ClientAnalytics(models.Model):
    """Manual analytics data for clients, accessible only from admin panel"""
    SOCIAL_NETWORK_CHOICES = [
        ('INSTAGRAM', 'Instagram'),
        ('YOUTUBE', 'YouTube'),
        ('TIKTOK', 'TikTok'),
    ]
    
    client = models.ForeignKey(
        'cabinet.Client',
        on_delete=models.CASCADE,
        related_name='analytics',
        help_text="Client for whom analytics are recorded"
    )
    social_network = models.CharField(
        max_length=20,
        choices=SOCIAL_NETWORK_CHOICES,
        help_text="Social network platform"
    )
    
    # Basic metrics
    total_posts = models.IntegerField(default=0, help_text="Total number of posts/videos")
    total_views = models.BigIntegerField(default=0, help_text="Total views across all posts")
    total_likes = models.BigIntegerField(default=0, help_text="Total likes across all posts")
    total_comments = models.BigIntegerField(default=0, help_text="Total comments across all posts")
    total_shares = models.BigIntegerField(default=0, help_text="Total shares/reposts")
    total_followers = models.BigIntegerField(default=0, help_text="Current follower count")
    
    # Calculated metrics
    average_views = models.FloatField(default=0.0, help_text="Average views per post")
    engagement_rate = models.FloatField(default=0.0, help_text="Engagement rate (likes+comments+shares)/views")
    growth_rate = models.FloatField(default=0.0, help_text="Follower growth rate (%)")
    
    # Additional metrics specific to platforms
    instagram_stories_views = models.BigIntegerField(default=0, blank=True, help_text="Instagram stories views")
    instagram_reels_views = models.BigIntegerField(default=0, blank=True, help_text="Instagram reels views")
    youtube_subscribers = models.BigIntegerField(default=0, blank=True, help_text="YouTube subscribers")
    youtube_watch_time = models.BigIntegerField(default=0, blank=True, help_text="YouTube watch time (minutes)")
    tiktok_video_views = models.BigIntegerField(default=0, blank=True, help_text="TikTok video views")
    tiktok_profile_views = models.BigIntegerField(default=0, blank=True, help_text="TikTok profile views")
    
    # Metadata
    period_start = models.DateField(help_text="Start date of analytics period")
    period_end = models.DateField(help_text="End date of analytics period")
    hashtag = models.CharField(max_length=100, blank=True, default="", help_text="Specific hashtag for this analytics (optional)")
    notes = models.TextField(blank=True, default="", help_text="Additional notes about the analytics")
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now, help_text="Date and time when analytics data was collected")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_analytics',
        help_text="Admin user who created this analytics entry"
    )
    
    class Meta:
        verbose_name = "Client Analytics"
        verbose_name_plural = "Client Analytics"
        indexes = [
            models.Index(fields=['client', 'social_network', 'period_start']),
            models.Index(fields=['social_network', 'period_start']),
        ]
        unique_together = ['client', 'social_network', 'period_start', 'period_end', 'hashtag']
    
    def __str__(self):
        return f"{self.client.name} - {self.get_social_network_display()} ({self.period_start} to {self.period_end})"
    
    def save(self, *args, **kwargs):
        # Set created_at to current time if not provided
        if not self.created_at:
            from django.utils import timezone
            self.created_at = timezone.now()
        
        # Calculate derived metrics
        if self.total_posts > 0:
            self.average_views = self.total_views / self.total_posts
        
        if self.total_views > 0:
            self.engagement_rate = (self.total_likes + self.total_comments + self.total_shares) / self.total_views
        
        super().save(*args, **kwargs)
    
    def get_platform_specific_metrics(self):
        """Get platform-specific metrics as a dictionary"""
        metrics = {}
        
        if self.social_network == 'INSTAGRAM':
            metrics.update({
                'stories_views': self.instagram_stories_views,
                'reels_views': self.instagram_reels_views,
            })
        elif self.social_network == 'YOUTUBE':
            metrics.update({
                'subscribers': self.youtube_subscribers,
                'watch_time': self.youtube_watch_time,
            })
        elif self.social_network == 'TIKTOK':
            metrics.update({
                'video_views': self.tiktok_video_views,
                'profile_views': self.tiktok_profile_views,
            })
        
        return metrics
