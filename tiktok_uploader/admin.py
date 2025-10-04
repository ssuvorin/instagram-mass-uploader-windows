"""
Django Admin Configuration for TikTok Uploader
================================================

Регистрация моделей в Django Admin для управления через админ-панель.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    TikTokProxy, TikTokAccount, DolphinProfileSnapshot,
    BulkUploadTask, BulkUploadAccount, BulkVideo, VideoCaption,
    WarmupTask, WarmupTaskAccount,
    FollowCategory, FollowTarget, FollowTask, FollowTaskAccount,
    CookieRobotTask, CookieRobotTaskAccount
)


# ============================================================================
# ПРОКСИ
# ============================================================================

@admin.register(TikTokProxy)
class TikTokProxyAdmin(admin.ModelAdmin):
    """
    Админ для TikTok прокси.
    """
    list_display = [
        'id', 'proxy_display', 'proxy_type', 'status_badge', 
        'country', 'external_ip', 'accounts_count', 'last_checked'
    ]
    list_filter = ['status', 'proxy_type', 'country', 'is_active']
    search_fields = ['host', 'external_ip', 'country', 'city']
    readonly_fields = ['external_ip', 'last_checked', 'last_used', 'last_verified']
    
    fieldsets = (
        ('Proxy Settings', {
            'fields': ('host', 'port', 'username', 'password', 'proxy_type')
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'last_checked', 'last_used', 'last_verified')
        }),
        ('Location', {
            'fields': ('external_ip', 'country', 'city')
        }),
        ('Advanced', {
            'fields': ('ip_change_url', 'notes'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['test_proxies', 'mark_as_active', 'mark_as_inactive']
    
    def proxy_display(self, obj):
        """Отображение прокси в формате host:port."""
        return f"{obj.host}:{obj.port}"
    proxy_display.short_description = 'Proxy'
    
    def status_badge(self, obj):
        """Цветной badge для статуса."""
        colors = {
            'active': 'success',
            'inactive': 'secondary',
            'banned': 'danger',
            'checking': 'warning'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def accounts_count(self, obj):
        """Количество привязанных аккаунтов."""
        count = obj.accounts.count()
        if count > 0:
            url = reverse('admin:tiktok_uploader_tiktokaccount_changelist')
            return format_html('<a href="{}?proxy__id__exact={}">{}</a>', url, obj.id, count)
        return count
    accounts_count.short_description = 'Accounts'
    
    def test_proxies(self, request, queryset):
        """Action: тестировать выбранные прокси."""
        # TODO: Implement proxy testing
        self.message_user(request, f"{queryset.count()} proxies will be tested in background.")
    test_proxies.short_description = "Test selected proxies"
    
    def mark_as_active(self, request, queryset):
        """Action: пометить как активные."""
        updated = queryset.update(status='active', is_active=True)
        self.message_user(request, f"{updated} proxies marked as active.")
    mark_as_active.short_description = "Mark as active"
    
    def mark_as_inactive(self, request, queryset):
        """Action: пометить как неактивные."""
        updated = queryset.update(status='inactive', is_active=False)
        self.message_user(request, f"{updated} proxies marked as inactive.")
    mark_as_inactive.short_description = "Mark as inactive"


# ============================================================================
# АККАУНТЫ
# ============================================================================

@admin.register(TikTokAccount)
class TikTokAccountAdmin(admin.ModelAdmin):
    """
    Админ для TikTok аккаунтов.
    """
    list_display = [
        'id', 'username', 'status_badge', 'proxy_link', 
        'dolphin_profile_id', 'client', 'last_used', 'created_at'
    ]
    list_filter = ['status', 'locale', 'client', 'created_at']
    search_fields = ['username', 'email', 'phone_number', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'last_used', 'last_warmed']
    
    fieldsets = (
        ('Account Info', {
            'fields': ('username', 'password', 'status')
        }),
        ('Contact Info', {
            'fields': ('email', 'email_password', 'phone_number')
        }),
        ('Configuration', {
            'fields': ('proxy', 'current_proxy', 'dolphin_profile_id', 'locale', 'client')
        }),
        ('Timestamps', {
            'fields': ('last_used', 'last_warmed', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['create_dolphin_profiles', 'refresh_cookies', 'mark_as_active']
    
    def status_badge(self, obj):
        """Цветной badge для статуса."""
        colors = {
            'ACTIVE': 'success',
            'BLOCKED': 'danger',
            'LIMITED': 'warning',
            'INACTIVE': 'secondary',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def proxy_link(self, obj):
        """Ссылка на прокси."""
        proxy = obj.current_proxy or obj.proxy
        if proxy:
            url = reverse('admin:tiktok_uploader_tiktokproxy_change', args=[proxy.id])
            return format_html('<a href="{}">{}</a>', url, str(proxy))
        return '-'
    proxy_link.short_description = 'Proxy'
    
    def create_dolphin_profiles(self, request, queryset):
        """Action: создать Dolphin профили."""
        # TODO: Implement
        self.message_user(request, f"Dolphin profiles will be created for {queryset.count()} accounts.")
    create_dolphin_profiles.short_description = "Create Dolphin profiles"
    
    def refresh_cookies(self, request, queryset):
        """Action: обновить cookies."""
        # TODO: Implement
        self.message_user(request, f"Cookies will be refreshed for {queryset.count()} accounts.")
    refresh_cookies.short_description = "Refresh cookies"
    
    def mark_as_active(self, request, queryset):
        """Action: пометить как активные."""
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f"{updated} accounts marked as active.")
    mark_as_active.short_description = "Mark as ACTIVE"


@admin.register(DolphinProfileSnapshot)
class DolphinProfileSnapshotAdmin(admin.ModelAdmin):
    """
    Админ для снимков Dolphin профилей.
    """
    list_display = ['id', 'account', 'profile_id', 'created_at', 'updated_at']
    search_fields = ['account__username', 'profile_id']
    readonly_fields = ['created_at', 'updated_at']


# ============================================================================
# МАССОВАЯ ЗАГРУЗКА
# ============================================================================

class BulkUploadAccountInline(admin.TabularInline):
    """Inline для аккаунтов в задаче."""
    model = BulkUploadAccount
    extra = 0
    readonly_fields = ['status', 'uploaded_success_count', 'uploaded_failed_count']
    fields = ['account', 'status', 'uploaded_success_count', 'uploaded_failed_count']


class BulkVideoInline(admin.TabularInline):
    """Inline для видео в задаче."""
    model = BulkVideo
    extra = 0
    readonly_fields = ['video_file', 'uploaded', 'order']
    fields = ['video_file', 'caption', 'uploaded', 'order', 'assigned_to']


@admin.register(BulkUploadTask)
class BulkUploadTaskAdmin(admin.ModelAdmin):
    """
    Админ для задач массовой загрузки.
    """
    list_display = [
        'id', 'name', 'status_badge', 'accounts_count', 
        'videos_count', 'progress', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'default_privacy']
    search_fields = ['name', 'default_caption']
    readonly_fields = ['created_at', 'updated_at', 'started_at', 'completed_at']
    
    inlines = [BulkUploadAccountInline, BulkVideoInline]
    
    fieldsets = (
        ('Task Info', {
            'fields': ('name', 'status')
        }),
        ('Upload Settings', {
            'fields': ('delay_min_sec', 'delay_max_sec', 'concurrency')
        }),
        ('Video Defaults', {
            'fields': ('default_caption', 'default_hashtags', 'default_privacy', 
                      'allow_comments', 'allow_duet', 'allow_stitch')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('Logs', {
            'fields': ('log',),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Цветной badge для статуса."""
        colors = {
            'PENDING': 'secondary',
            'RUNNING': 'primary',
            'COMPLETED': 'success',
            'FAILED': 'danger',
            'PAUSED': 'warning',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def accounts_count(self, obj):
        """Количество аккаунтов."""
        return obj.accounts.count()
    accounts_count.short_description = 'Accounts'
    
    def videos_count(self, obj):
        """Количество видео."""
        return obj.videos.count()
    videos_count.short_description = 'Videos'
    
    def progress(self, obj):
        """Прогресс загрузки."""
        uploaded = obj.videos.filter(uploaded=True).count()
        total = obj.videos.count()
        if total > 0:
            percent = (uploaded / total) * 100
            return format_html(
                '<div class="progress"><div class="progress-bar" style="width: {}%">{}/{}</div></div>',
                percent, uploaded, total
            )
        return '-'
    progress.short_description = 'Progress'


@admin.register(BulkVideo)
class BulkVideoAdmin(admin.ModelAdmin):
    """
    Админ для видео.
    """
    list_display = ['id', 'bulk_task', 'video_file', 'assigned_to', 'uploaded', 'order', 'uploaded_at']
    list_filter = ['uploaded', 'bulk_task', 'uploaded_at']
    search_fields = ['caption', 'hashtags']


@admin.register(VideoCaption)
class VideoCaptionAdmin(admin.ModelAdmin):
    """
    Админ для описаний видео.
    """
    list_display = ['id', 'bulk_task', 'text_preview', 'assigned_to', 'order']
    list_filter = ['bulk_task']
    search_fields = ['text']
    
    def text_preview(self, obj):
        """Preview текста."""
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Caption'


# ============================================================================
# ПРОГРЕВ
# ============================================================================

@admin.register(WarmupTask)
class WarmupTaskAdmin(admin.ModelAdmin):
    """
    Админ для задач прогрева.
    """
    list_display = ['id', 'name', 'status_badge', 'accounts_count', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name']
    
    def status_badge(self, obj):
        colors = {'PENDING': 'secondary', 'RUNNING': 'primary', 'COMPLETED': 'success', 'FAILED': 'danger'}
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.status)
    status_badge.short_description = 'Status'
    
    def accounts_count(self, obj):
        return obj.accounts.count()
    accounts_count.short_description = 'Accounts'


# ============================================================================
# ПОДПИСКИ
# ============================================================================

@admin.register(FollowCategory)
class FollowCategoryAdmin(admin.ModelAdmin):
    """
    Админ для категорий подписок.
    """
    list_display = ['id', 'name', 'targets_count', 'created_at']
    search_fields = ['name', 'description']
    
    def targets_count(self, obj):
        return obj.targets.count()
    targets_count.short_description = 'Targets'


@admin.register(FollowTarget)
class FollowTargetAdmin(admin.ModelAdmin):
    """
    Админ для целевых аккаунтов.
    """
    list_display = ['id', 'username', 'category', 'added_at']
    list_filter = ['category', 'added_at']
    search_fields = ['username']


@admin.register(FollowTask)
class FollowTaskAdmin(admin.ModelAdmin):
    """
    Админ для задач подписок.
    """
    list_display = ['id', 'name', 'action', 'status_badge', 'category', 'accounts_count', 'created_at']
    list_filter = ['status', 'action', 'created_at']
    search_fields = ['name']
    
    def status_badge(self, obj):
        colors = {'PENDING': 'secondary', 'RUNNING': 'primary', 'COMPLETED': 'success', 'FAILED': 'danger'}
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.status)
    status_badge.short_description = 'Status'
    
    def accounts_count(self, obj):
        return obj.accounts.count()
    accounts_count.short_description = 'Accounts'


# ============================================================================
# COOKIES
# ============================================================================

@admin.register(CookieRobotTask)
class CookieRobotTaskAdmin(admin.ModelAdmin):
    """
    Админ для задач обновления cookies.
    """
    list_display = ['id', 'name', 'status_badge', 'accounts_count', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name']
    
    def status_badge(self, obj):
        colors = {'PENDING': 'secondary', 'RUNNING': 'primary', 'COMPLETED': 'success', 'FAILED': 'danger'}
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.status)
    status_badge.short_description = 'Status'
    
    def accounts_count(self, obj):
        return obj.accounts.count()
    accounts_count.short_description = 'Accounts'


# Регистрация остальных моделей без кастомизации
admin.site.register(BulkUploadAccount)
admin.site.register(WarmupTaskAccount)
admin.site.register(FollowTaskAccount)
admin.site.register(CookieRobotTaskAccount)


