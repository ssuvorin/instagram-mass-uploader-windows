from django.contrib import admin
from .models import Proxy, InstagramAccount, InstagramCookies, UploadTask, VideoFile, FollowCategory, FollowTarget, FollowTask, FollowTaskAccount


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
