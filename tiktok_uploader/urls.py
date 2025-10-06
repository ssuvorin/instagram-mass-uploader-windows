"""
URL Configuration for TikTok Uploader
======================================

Маршруты для всех эндпоинтов управления TikTok ботом.
Структура аналогична Instagram Uploader.
"""

from django.urls import path
from . import views
from . import views_warmup
from . import views_follow
from .views_mod import views_bulk
from .views_mod import views_proxies
from .views_mod import views_cookie
from .views_mod import views_import

app_name = 'tiktok_uploader'

urlpatterns = [
    # ========================================================================
    # ГЛАВНАЯ СТРАНИЦА И ДАШБОРД
    # ========================================================================
    path('', views.dashboard, name='dashboard'),
    
    # ========================================================================
    # УПРАВЛЕНИЕ АККАУНТАМИ
    # ========================================================================
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/<int:account_id>/', views.account_detail, name='account_detail'),
    path('accounts/create/', views.create_account, name='create_account'),
    path('accounts/import/', views_import.import_accounts, name='import_accounts'),
    path('accounts/<int:account_id>/edit/', views.edit_account, name='edit_account'),
    path('accounts/<int:account_id>/delete/', views.delete_account, name='delete_account'),
    path('accounts/bulk-delete/', views.bulk_delete_accounts, name='bulk_delete_accounts'),
    path('accounts/<int:account_id>/change-proxy/', views.change_account_proxy, name='change_account_proxy'),
    path('accounts/<int:account_id>/create-profile/', views.create_dolphin_profile, name='create_dolphin_profile'),
    path('accounts/bulk-change-proxy/', views.bulk_change_proxy, name='bulk_change_proxy'),
    path('accounts/refresh-dolphin-proxies/', views.refresh_dolphin_proxies, name='refresh_dolphin_proxies'),
    
    # ========================================================================
    # УПРАВЛЕНИЕ ПРОКСИ
    # ========================================================================
    path('proxies/', views_proxies.proxy_list, name='proxy_list'),
    path('proxies/create/', views_proxies.create_proxy, name='create_proxy'),
    path('proxies/import/', views_proxies.import_proxies, name='import_proxies'),
    path('proxies/validate-all/', views_proxies.validate_all_proxies, name='validate_all_proxies'),
    path('proxies/cleanup-inactive/', views_proxies.cleanup_inactive_proxies, name='cleanup_inactive_proxies'),
    path('proxies/<int:proxy_id>/edit/', views_proxies.edit_proxy, name='edit_proxy'),
    path('proxies/<int:proxy_id>/test/', views_proxies.test_proxy, name='test_proxy'),
    path('proxies/<int:proxy_id>/change-ip/', views_proxies.change_proxy_ip, name='change_proxy_ip'),
    path('proxies/<int:proxy_id>/delete/', views_proxies.delete_proxy, name='delete_proxy'),
    path('proxies/bulk-delete/', views_proxies.bulk_delete_proxies, name='bulk_delete_proxies'),
    
    # ========================================================================
    # МАССОВАЯ ЗАГРУЗКА ВИДЕО
    # ========================================================================
    path('bulk-upload/', views_bulk.bulk_upload_list, name='bulk_upload_list'),
    path('bulk-upload/create/', views_bulk.create_bulk_upload, name='create_bulk_upload'),
    path('bulk-upload/<int:task_id>/', views_bulk.bulk_upload_detail, name='bulk_upload_detail'),
    path('bulk-upload/<int:task_id>/add-videos/', views_bulk.add_bulk_videos, name='add_bulk_videos'),
    path('bulk-upload/<int:task_id>/add-captions/', views_bulk.add_bulk_captions, name='add_bulk_captions'),
    path('bulk-upload/<int:task_id>/start/', views_bulk.start_bulk_upload, name='start_bulk_upload'),
    path('bulk-upload/<int:task_id>/start-api/', views_bulk.start_bulk_upload_api, name='start_bulk_upload_api'),
    path('bulk-upload/<int:task_id>/delete/', views_bulk.delete_bulk_upload, name='delete_bulk_upload'),
    path('bulk-upload/<int:task_id>/force-delete/', views_bulk.force_delete_bulk_upload, name='force_delete_bulk_upload'),
    path('bulk-upload/<int:task_id>/logs/', views_bulk.get_bulk_task_logs, name='bulk_task_logs'),
    path('bulk-upload/<int:task_id>/pause/', views_bulk.pause_bulk_upload, name='pause_bulk_upload'),
    path('bulk-upload/<int:task_id>/resume/', views_bulk.resume_bulk_upload, name='resume_bulk_upload'),
    path('bulk-upload/video/<int:video_id>/edit/', views_bulk.edit_video_metadata, name='edit_video_metadata'),
    
    # ========================================================================
    # УПРАВЛЕНИЕ COOKIES
    # ========================================================================
    path('cookies/', views_cookie.cookie_dashboard, name='cookie_dashboard'),
    path('cookies/tasks/', views_cookie.cookie_task_list, name='cookie_task_list'),
    path('cookies/tasks/<int:task_id>/', views_cookie.cookie_task_detail, name='cookie_task_detail'),
    path('cookies/tasks/<int:task_id>/start/', views_cookie.start_cookie_task, name='start_cookie_task'),
    path('cookies/tasks/<int:task_id>/stop/', views_cookie.stop_cookie_task, name='stop_cookie_task'),
    path('cookies/tasks/<int:task_id>/delete/', views_cookie.delete_cookie_task, name='delete_cookie_task'),
    path('cookies/tasks/<int:task_id>/logs/', views_cookie.get_cookie_task_logs, name='cookie_task_logs'),
    path('cookies/accounts/<int:account_id>/', views_cookie.account_cookies, name='account_cookies'),
    path('cookies/bulk/', views_cookie.bulk_cookie_robot, name='bulk_cookie_robot'),
    path('cookies/bulk/refresh/', views_cookie.refresh_cookies_from_profiles, name='refresh_cookies_from_profiles'),
    
    # ========================================================================
    # ПРОГРЕВ АККАУНТОВ (WARMUP)
    # ========================================================================
    path('warmup/', views_warmup.warmup_task_list, name='warmup_task_list'),
    path('warmup/create/', views_warmup.warmup_task_create, name='warmup_task_create'),
    path('warmup/<int:task_id>/', views_warmup.warmup_task_detail, name='warmup_task_detail'),
    path('warmup/<int:task_id>/start/', views_warmup.warmup_task_start, name='warmup_task_start'),
    path('warmup/<int:task_id>/force-stop/', views_warmup.force_stop_warmup_task, name='force_stop_warmup_task'),
    path('warmup/<int:task_id>/restart/', views_warmup.restart_warmup_task, name='restart_warmup_task'),
    path('warmup/<int:task_id>/logs/', views_warmup.warmup_task_logs, name='warmup_task_logs'),
    path('warmup/<int:task_id>/delete/', views_warmup.delete_warmup_task, name='delete_warmup_task'),
    
    # ========================================================================
    # ПОДПИСКИ И ОТПИСКИ
    # ========================================================================
    # Категории целей
    path('follow/categories/', views_follow.follow_category_list, name='follow_category_list'),
    path('follow/categories/create/', views_follow.follow_category_create, name='follow_category_create'),
    path('follow/categories/<int:category_id>/', views_follow.follow_category_detail, name='follow_category_detail'),
    path('follow/categories/<int:category_id>/targets/add/', views_follow.follow_target_add, name='follow_target_add'),
    path('follow/categories/<int:category_id>/targets/<int:target_id>/delete/', views_follow.follow_target_delete, name='follow_target_delete'),
    
    # Задачи подписок
    path('follow/tasks/', views_follow.follow_task_list, name='follow_task_list'),
    path('follow/tasks/create/', views_follow.follow_task_create, name='follow_task_create'),
    path('follow/tasks/<int:task_id>/', views_follow.follow_task_detail, name='follow_task_detail'),
    path('follow/tasks/<int:task_id>/start/', views_follow.follow_task_start, name='follow_task_start'),
    path('follow/tasks/<int:task_id>/logs/', views_follow.follow_task_logs, name='follow_task_logs'),
    path('follow/tasks/<int:task_id>/delete/', views_follow.delete_follow_task, name='delete_follow_task'),
    
    # ========================================================================
    # API ЭНДПОИНТЫ
    # ========================================================================
    path('api/captcha-notification/', views.captcha_notification, name='captcha_notification'),
    path('api/captcha-status/<int:task_id>/', views.get_captcha_status, name='get_captcha_status'),
    path('api/captcha-clear/<int:task_id>/', views.clear_captcha_notification, name='clear_captcha_notification'),
    
    # Статистика и мониторинг
    path('api/stats/', views.get_stats_api, name='get_stats_api'),
    path('api/account/<int:account_id>/status/', views.get_account_status_api, name='get_account_status_api'),
    path('api/task/<int:task_id>/progress/', views.get_task_progress_api, name='get_task_progress_api'),
]


