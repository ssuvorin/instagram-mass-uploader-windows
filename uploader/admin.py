from django.contrib import admin
from .models import (
    Proxy, InstagramAccount, InstagramCookies, UploadTask, VideoFile,
    FollowCategory, FollowTarget, FollowTask, FollowTaskAccount,
    YouTubeAccount, YouTubeShortsBulkUploadTask, YouTubeShortsBulkUploadAccount,
    YouTubeShortsVideo, YouTubeShortsVideoTitle, ClientAnalytics
)


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = ('host', 'port', 'proxy_type', 'status', 'username', 'is_active', 'last_checked', 'assigned_account')
    list_filter = ('is_active', 'status', 'proxy_type')
    search_fields = ('host', 'port', 'username', 'assigned_account__username')


@admin.register(InstagramAccount)
class InstagramAccountAdmin(admin.ModelAdmin):
    list_display = ('username', 'status', 'proxy', 'dolphin_profile_id', 'last_used', 'last_warmed')
    list_filter = ('status',)
    search_fields = ('username', 'email_username', 'notes', 'dolphin_profile_id')
    readonly_fields = ('created_at', 'updated_at', 'last_used', 'last_warmed')


@admin.register(InstagramCookies)
class InstagramCookiesAdmin(admin.ModelAdmin):
    list_display = ('account', 'last_updated', 'is_valid')
    list_filter = ('is_valid',)
    readonly_fields = ('last_updated',)


class VideoFileInline(admin.TabularInline):
    model = VideoFile
    extra = 1


@admin.register(UploadTask)
class UploadTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('account__username', 'log')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [VideoFileInline]


@admin.register(VideoFile)
class VideoFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('task__account__username', 'caption')
    readonly_fields = ('uploaded_at',)


@admin.register(FollowCategory)
class FollowCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')


@admin.register(FollowTarget)
class FollowTargetAdmin(admin.ModelAdmin):
    list_display = ('username', 'user_id', 'category', 'is_private', 'is_verified', 'created_at')
    list_filter = ('category', 'is_private', 'is_verified')
    search_fields = ('username', 'user_id')


@admin.register(FollowTask)
class FollowTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'status', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('name', 'log')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FollowTaskAccount)
class FollowTaskAccountAdmin(admin.ModelAdmin):
    list_display = ('task', 'account', 'status', 'started_at', 'completed_at')
    list_filter = ('status',)
    search_fields = ('task__name', 'account__username')
    readonly_fields = ('started_at', 'completed_at')


# ===== YouTube Shorts Admin =====
@admin.register(YouTubeAccount)
class YouTubeAccountAdmin(admin.ModelAdmin):
    list_display = ('email', 'channel_name', 'status', 'proxy', 'dolphin_profile_id', 'last_used')
    list_filter = ('status', 'client')
    search_fields = ('email', 'channel_name', 'channel_id', 'notes', 'dolphin_profile_id')
    readonly_fields = ('created_at', 'updated_at', 'last_used')


@admin.register(YouTubeShortsBulkUploadTask)
class YouTubeShortsBulkUploadTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'status', 'get_total_count', 'get_completed_count', 'created_at')
    list_filter = ('status', 'default_visibility')
    search_fields = ('name', 'log')
    readonly_fields = ('created_at', 'updated_at', 'upload_id', 'get_completion_percentage')


@admin.register(YouTubeShortsBulkUploadAccount)
class YouTubeShortsBulkUploadAccountAdmin(admin.ModelAdmin):
    list_display = ('bulk_task', 'account', 'status', 'uploaded_success_count', 'uploaded_failed_count', 'started_at')
    list_filter = ('status',)
    search_fields = ('bulk_task__name', 'account__email')
    readonly_fields = ('started_at', 'completed_at')


@admin.register(YouTubeShortsVideo)
class YouTubeShortsVideoAdmin(admin.ModelAdmin):
    list_display = ('id', 'bulk_task', 'video_file', 'assigned_to', 'order', 'visibility')
    list_filter = ('bulk_task', 'visibility')
    search_fields = ('video_file',)
    readonly_fields = ('uploaded_at',)
    ordering = ['order']


@admin.register(YouTubeShortsVideoTitle)
class YouTubeShortsVideoTitleAdmin(admin.ModelAdmin):
    list_display = ('id', 'bulk_task', 'title', 'used', 'assigned_to')
    list_filter = ('bulk_task', 'used')
    search_fields = ('title', 'description')


# ===== Analytics Admin =====
@admin.register(ClientAnalytics)
class ClientAnalyticsAdmin(admin.ModelAdmin):
    list_display = (
        'client', 'social_network', 'period_start', 'period_end', 
        'total_posts', 'total_views', 'total_followers', 'engagement_rate',
        'created_at', 'created_by'
    )
    list_filter = ('social_network', 'client', 'period_start', 'created_at')
    search_fields = ('client__name', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'average_views', 'engagement_rate')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('client', 'social_network', 'period_start', 'period_end', 'notes')
        }),
        ('Core Metrics', {
            'fields': (
                'total_posts', 'total_views', 'total_likes', 'total_comments', 
                'total_shares', 'total_followers'
            )
        }),
        ('Calculated Metrics', {
            'fields': ('average_views', 'engagement_rate', 'growth_rate'),
            'classes': ('collapse',)
        }),
        ('Instagram Specific', {
            'fields': ('instagram_stories_views', 'instagram_reels_views'),
            'classes': ('collapse',)
        }),
        ('YouTube Specific', {
            'fields': ('youtube_subscribers', 'youtube_watch_time'),
            'classes': ('collapse',)
        }),
        ('TikTok Specific', {
            'fields': ('tiktok_video_views', 'tiktok_profile_views'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Automatically set created_by to current user"""
        if not change:  # Only for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Only show analytics to superusers"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.none()
    
    def has_add_permission(self, request):
        """Only superusers can add analytics"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Only superusers can change analytics"""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete analytics"""
        return request.user.is_superuser
