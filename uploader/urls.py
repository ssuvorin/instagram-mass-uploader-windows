from django.urls import path
from . import views
from . import views_avatar
from . import views_follow
from .views_mod import views_bio
from .views_mod import views_photo
from .views_mod import misc
from .views_mod import hashtag
from .views_mod import proxies
from .views_mod import yt_shorts_bulk
from .views_mod import analytics
from .views_mod import analytics_collector

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Tasks
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('tasks/create/', views.create_task, name='create_task'),
    path('tasks/<int:task_id>/start/', views.start_task, name='start_task'),
    
    # Accounts
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/<int:account_id>/', views.account_detail, name='account_detail'),
    path('accounts/create/', views.create_account, name='create_account'),
    path('accounts/import/', views.import_accounts, name='import_accounts'),
    path('accounts/import-ua-cookies/', views.import_accounts_ua_cookies, name='import_ua_cookies'),
    path('accounts/import-bundle/', views.import_accounts_bundle, name='import_accounts_bundle'),
    path('accounts/<int:account_id>/warm/', views.warm_account, name='warm_account'),
    path('accounts/<int:account_id>/edit/', views.edit_account, name='edit_account'),
    path('accounts/<int:account_id>/change-proxy/', views.change_account_proxy, name='change_account_proxy'),
    path('accounts/<int:account_id>/create-profile/', views.create_dolphin_profile, name='create_dolphin_profile'),
    path('accounts/<int:account_id>/save-profile-snapshot/', misc.save_dolphin_profile_snapshot, name='save_dolphin_profile_snapshot'),
    path('accounts/<int:account_id>/delete/', views.delete_account, name='delete_account'),
    path('accounts/bulk-change-proxy/', views.bulk_change_proxy, name='bulk_change_proxy'),
    path('accounts/bulk-save-snapshots/', views.bulk_save_snapshots, name='bulk_save_snapshots'),
    path('accounts/bulk-change-status/', views.bulk_change_status, name='bulk_change_status'),
    path('accounts/bulk-delete/', views.bulk_delete_accounts, name='bulk_delete_accounts'),
    path('accounts/refresh-dolphin-proxies/', views.refresh_dolphin_proxies, name='refresh_dolphin_proxies'),
    
    # Proxies
    path('proxies/', proxies.proxy_list, name='proxy_list'),
    path('proxies/create/', proxies.create_proxy, name='create_proxy'),
    path('proxies/<int:proxy_id>/edit/', proxies.edit_proxy, name='edit_proxy'),
    path('proxies/<int:proxy_id>/test/', proxies.test_proxy, name='test_proxy'),
    path('proxies/<int:proxy_id>/change-ip/', proxies.change_proxy_ip, name='change_proxy_ip'),
    path('proxies/<int:proxy_id>/delete/', proxies.delete_proxy, name='delete_proxy'),
    path('proxies/import/', proxies.import_proxies, name='import_proxies'),
    path('proxies/validate-all/', proxies.validate_all_proxies, name='validate_all_proxies'),
    path('proxies/cleanup-inactive/', views.cleanup_inactive_proxies, name='cleanup_inactive_proxies'),
    
    # Bulk Upload
    path('bulk-upload/', views.bulk_upload_list, name='bulk_upload_list'),
    path('bulk-upload/create/', views.create_bulk_upload, name='create_bulk_upload'),
    path('bulk-upload/<int:task_id>/', views.bulk_upload_detail, name='bulk_upload_detail'),
    path('bulk-upload/<int:task_id>/add-videos/', views.add_bulk_videos, name='add_bulk_videos'),
    path('bulk-upload/<int:task_id>/add-titles/', views.add_bulk_titles, name='add_bulk_titles'),
    path('bulk-upload/<int:task_id>/start/', views.start_bulk_upload, name='start_bulk_upload'),
    path('bulk-upload/<int:task_id>/start-api/', views.start_bulk_upload_api, name='start_bulk_upload_api'),
    path('bulk-upload/<int:task_id>/delete/', views.delete_bulk_upload, name='delete_bulk_upload'),
    path('bulk-upload/<int:task_id>/logs/', views.get_bulk_task_logs, name='bulk_task_logs'),
    path('bulk-upload/<int:task_id>/bulk-edit-location-mentions/', views.bulk_edit_location_mentions, name='bulk_edit_location_mentions'),
    path('bulk-upload/video/<int:video_id>/edit-location-mentions/', views.edit_video_location_mentions, name='edit_video_location_mentions'),
    
    # Bulk Login
    path('bulk-login/', views.bulk_login_list, name='bulk_login_list'),
    path('bulk-login/create/', views.create_bulk_login, name='create_bulk_login'),
    path('bulk-login/<int:task_id>/', views.bulk_login_detail, name='bulk_login_detail'),
    path('bulk-login/<int:task_id>/start/', views.start_bulk_login, name='start_bulk_login'),
    path('bulk-login/<int:task_id>/delete/', views.delete_bulk_login, name='delete_bulk_login'),
    path('bulk-login/<int:task_id>/logs/', views.get_bulk_login_logs, name='bulk_login_logs'),
    
    # Cookies Dashboard
    path('cookies/', views.cookie_dashboard, name='cookie_dashboard'),
    path('cookies/tasks/', views.cookie_task_list, name='cookie_task_list'),
    path('cookies/tasks/<int:task_id>/', views.cookie_task_detail, name='cookie_task_detail'),
    path('cookies/tasks/<int:task_id>/start/', views.start_cookie_task, name='start_cookie_task'),
    path('cookies/tasks/<int:task_id>/stop/', views.stop_cookie_task, name='stop_cookie_task'),
    path('cookies/tasks/<int:task_id>/delete/', views.delete_cookie_task, name='delete_cookie_task'),
    path('cookies/tasks/<int:task_id>/logs/', views.get_cookie_task_logs, name='cookie_task_logs'),
    path('cookies/accounts/<int:account_id>/', views.account_cookies, name='account_cookies'),
    path('cookies/bulk/', views.bulk_cookie_robot, name='bulk_cookie_robot'),
    path('cookies/bulk/refresh/', views.refresh_cookies_from_profiles, name='refresh_cookies_from_profiles'),

    # Captcha API
    path('api/captcha-notification/', views.captcha_notification, name='captcha_notification'),
    path('api/captcha-status/<int:task_id>/', views.get_captcha_status, name='get_captcha_status'),
    path('api/captcha-clear/<int:task_id>/', views.clear_captcha_notification, name='clear_captcha_notification'),
    
    # TikTok Dashboard
    path('tiktok/', misc.tiktok_dashboard, name='tiktok_dashboard'),
    
    # TikTok Booster UI
    path('tiktok/booster/', misc.tiktok_booster, name='tiktok_booster'),
    path('tiktok/booster/upload-accounts/', misc.tiktok_booster_upload_accounts, name='tiktok_booster_upload_accounts'),
    path('tiktok/booster/upload-proxies/', misc.tiktok_booster_upload_proxies, name='tiktok_booster_upload_proxies'),
    path('tiktok/booster/prepare/', misc.tiktok_booster_prepare, name='tiktok_booster_prepare'),
    path('tiktok/booster/start/', misc.tiktok_booster_start, name='tiktok_booster_start'),
    path('tiktok/booster/logs/', misc.get_api_server_logs, name='get_api_server_logs'),

    # TikTok Video Management (separate module)
    path('tiktok/videos/', misc.tiktok_videos, name='tiktok_videos'),
    path('tiktok/videos/upload/', misc.tiktok_videos_upload, name='tiktok_videos_upload'),
    path('tiktok/videos/titles/', misc.tiktok_videos_titles, name='tiktok_videos_titles'),
    path('tiktok/videos/prepare/', misc.tiktok_videos_prepare, name='tiktok_videos_prepare'),
    path('tiktok/videos/start/', misc.tiktok_videos_start, name='tiktok_videos_start'),
    # Server-side proxy endpoints
    path('api/tiktok/booster/upload-accounts/', misc.tiktok_booster_proxy_upload_accounts, name='api_tiktok_booster_upload_accounts'),
    path('api/tiktok/booster/upload-proxies/', misc.tiktok_booster_proxy_upload_proxies, name='api_tiktok_booster_upload_proxies'),
    path('api/tiktok/booster/prepare/', misc.tiktok_booster_proxy_prepare_accounts, name='api_tiktok_booster_prepare_accounts'),
    path('api/tiktok/booster/start/', misc.tiktok_booster_proxy_start, name='api_tiktok_booster_start'),
    path('api/tiktok/booster/pipeline/', misc.tiktok_booster_proxy_pipeline, name='api_tiktok_booster_pipeline'),
    path('api/tiktok/set-active-server/', misc.tiktok_set_active_server, name='api_tiktok_set_active_server'),
    path('api/tiktok/ping/', misc.tiktok_api_ping, name='api_tiktok_api_ping'),
    
    # TikTok Video Upload proxy endpoints (separate module)
    path('api/tiktok/videos/upload/', misc.tiktok_videos_proxy_upload, name='api_tiktok_videos_upload'),
    path('api/tiktok/videos/prepare-accounts/', misc.tiktok_videos_proxy_prepare_accounts, name='api_tiktok_videos_prepare_accounts'),
    path('api/tiktok/videos/upload-titles/', misc.tiktok_videos_proxy_upload_titles, name='api_tiktok_videos_upload_titles'),
    path('api/tiktok/videos/prepare-config/', misc.tiktok_videos_proxy_prepare_config, name='api_tiktok_videos_prepare_config'),
    path('api/tiktok/videos/start-upload/', misc.tiktok_videos_proxy_start_upload, name='api_tiktok_videos_start_upload'),
    path('api/tiktok/videos/pipeline/', misc.tiktok_videos_proxy_pipeline, name='api_tiktok_videos_pipeline'),
    path('api/tiktok/videos/release-accounts/', misc.tiktok_videos_proxy_release_accounts, name='api_tiktok_videos_release_accounts'),
    
        # TikTok Proxy Validation endpoints
        path('api/tiktok/proxy/validate/', misc.tiktok_proxy_validate, name='api_tiktok_proxy_validate'),
        path('api/tiktok/proxy/status/<str:client>/', misc.tiktok_proxy_status, name='api_tiktok_proxy_status'),
        path('api/tiktok/proxy/invalid-countries/<str:client>/', misc.tiktok_proxy_invalid_countries, name='api_tiktok_proxy_invalid_countries'),
        path('api/tiktok/proxy/replace-invalid/', misc.tiktok_proxy_replace_invalid, name='api_tiktok_proxy_replace_invalid'),
        path('api/tiktok/proxy/upload-and-validate/', misc.tiktok_proxy_upload_and_validate, name='api_tiktok_proxy_upload_and_validate'),
        path('api/tiktok/proxy/replace-with-uploaded/', misc.tiktok_proxy_replace_with_uploaded, name='api_tiktok_proxy_replace_with_uploaded'),
    path('api/tiktok/booster/release-accounts/', misc.tiktok_booster_proxy_release_accounts, name='api_tiktok_booster_release_accounts'),
    path('api/tiktok/stats/', misc.tiktok_stats_proxy, name='api_tiktok_stats'),
    path('api/tiktok/maintenance/', misc.tiktok_maintenance_proxy, name='api_tiktok_maintenance'),


    # Hashtag Analyzer
    path('tools/hashtag/', hashtag.hashtag_analyzer, name='hashtag_analyzer'),
    
    # Password Reset Tools (temporarily disabled - views module not present)
]

urlpatterns += [
    path('avatars/', views_avatar.avatar_task_list, name='avatar_task_list'),
    path('avatars/create/', views_avatar.create_avatar_task, name='create_avatar_task'),
    path('avatars/<int:task_id>/', views_avatar.avatar_task_detail, name='avatar_task_detail'),
    path('avatars/<int:task_id>/start/', views_avatar.start_avatar_task, name='start_avatar_task'),
    path('avatars/<int:task_id>/logs/', views_avatar.get_avatar_task_logs, name='avatar_task_logs'),
    
    # Photo post
    path('photos/create/', views_photo.create_photo_post, name='create_photo_post'),
    path('photos/status/', views_photo.photo_post_status, name='photo_post_status'),
    
    # Bio link change
    path('bio/', views_bio.bio_task_list, name='bio_task_list'),
    path('bio/create/', views_bio.create_bio_task, name='create_bio_task'),
    path('bio/<int:task_id>/', views_bio.bio_task_detail, name='bio_task_detail'),
    path('bio/<int:task_id>/start/', views_bio.start_bio_task, name='start_bio_task'),
    path('bio/<int:task_id>/logs/', views_bio.get_bio_task_logs, name='bio_task_logs'),
    
    path('follow/categories/', views_follow.follow_category_list, name='follow_category_list'),
    path('follow/categories/create/', views_follow.follow_category_create, name='follow_category_create'),
    path('follow/categories/<int:category_id>/', views_follow.follow_category_detail, name='follow_category_detail'),
    path('follow/categories/<int:category_id>/targets/add/', views_follow.follow_target_add, name='follow_target_add'),
    path('follow/categories/<int:category_id>/targets/<int:target_id>/delete/', views_follow.follow_target_delete, name='follow_target_delete'),

    path('follow/tasks/', views_follow.follow_task_list, name='follow_task_list'),
    path('follow/tasks/create/', views_follow.follow_task_create, name='follow_task_create'),
    path('follow/tasks/<int:task_id>/', views_follow.follow_task_detail, name='follow_task_detail'),
    path('follow/tasks/<int:task_id>/start/', views_follow.follow_task_start, name='follow_task_start'),
    path('follow/tasks/<int:task_id>/logs/', views_follow.follow_task_logs, name='follow_task_logs'),

    # Warmup
    path('warmup/', __import__('uploader.views_warmup', fromlist=['warmup_task_list']).warmup_task_list, name='warmup_task_list'),
    path('warmup/create/', __import__('uploader.views_warmup', fromlist=['warmup_task_create']).warmup_task_create, name='warmup_task_create'),
    path('warmup/<int:task_id>/', __import__('uploader.views_warmup', fromlist=['warmup_task_detail']).warmup_task_detail, name='warmup_task_detail'),
    path('warmup/<int:task_id>/start/', __import__('uploader.views_warmup', fromlist=['warmup_task_start']).warmup_task_start, name='warmup_task_start'),
    path('warmup/<int:task_id>/logs/', __import__('uploader.views_warmup', fromlist=['warmup_task_logs']).warmup_task_logs, name='warmup_task_logs'),
] 

urlpatterns += [
    # External worker API routes temporarily disabled
]

# YouTube Shorts Routes
urlpatterns += [
    # Dashboard
    path('yt-shorts/', yt_shorts_bulk.yt_shorts_dashboard, name='yt_shorts_dashboard'),
    
    # Bulk Upload
    path('yt-shorts/bulk-upload/', yt_shorts_bulk.yt_shorts_bulk_upload_list, name='yt_shorts_bulk_upload_list'),
    path('yt-shorts/bulk-upload/create/', yt_shorts_bulk.create_yt_shorts_bulk_upload, name='create_yt_shorts_bulk_upload'),
    path('yt-shorts/bulk-upload/<int:task_id>/', yt_shorts_bulk.yt_shorts_bulk_upload_detail, name='yt_shorts_bulk_upload_detail'),
    path('yt-shorts/bulk-upload/<int:task_id>/add-videos/', yt_shorts_bulk.add_yt_shorts_bulk_videos, name='yt_shorts_add_bulk_videos'),
    path('yt-shorts/bulk-upload/<int:task_id>/add-titles/', yt_shorts_bulk.add_yt_shorts_bulk_titles, name='yt_shorts_add_bulk_titles'),
    path('yt-shorts/bulk-upload/<int:task_id>/start/', yt_shorts_bulk.start_yt_shorts_bulk_upload, name='start_yt_shorts_bulk_upload'),
    path('yt-shorts/bulk-upload/<int:task_id>/delete/', yt_shorts_bulk.delete_yt_shorts_bulk_upload, name='delete_yt_shorts_bulk_upload'),
    path('yt-shorts/bulk-upload/<int:task_id>/logs/api/', yt_shorts_bulk.get_yt_shorts_bulk_task_logs, name='yt_shorts_bulk_task_logs'),
    path('yt-shorts/bulk-upload/video/<int:video_id>/edit/', yt_shorts_bulk.edit_yt_shorts_video_settings, name='edit_yt_shorts_video_settings'),
    path('yt-shorts/bulk-upload/<int:task_id>/bulk-edit-videos/', yt_shorts_bulk.bulk_edit_yt_shorts_videos, name='bulk_edit_yt_shorts_videos'),
    
    # YouTube Shorts - Account Management
    path('yt-shorts/accounts/', yt_shorts_bulk.yt_accounts_list, name='yt_accounts_list'),
    path('yt-shorts/accounts/import/', yt_shorts_bulk.yt_accounts_import, name='yt_accounts_import'),
    path('yt-shorts/accounts/create/', yt_shorts_bulk.yt_account_create, name='yt_account_create'),
    path('yt-shorts/accounts/<int:account_id>/', yt_shorts_bulk.yt_account_detail, name='yt_account_detail'),
    path('yt-shorts/accounts/<int:account_id>/edit/', yt_shorts_bulk.yt_account_edit, name='yt_account_edit'),
    path('yt-shorts/accounts/<int:account_id>/delete/', yt_shorts_bulk.yt_account_delete, name='yt_account_delete'),
    path('yt-shorts/accounts/<int:account_id>/create-dolphin-profile/', yt_shorts_bulk.create_yt_dolphin_profile, name='create_yt_dolphin_profile'),
    path('yt-shorts/accounts/<int:account_id>/change-proxy/', yt_shorts_bulk.change_yt_account_proxy, name='change_yt_account_proxy'),
    path('yt-shorts/accounts/<int:account_id>/available-proxies/', yt_shorts_bulk.get_available_proxies_for_yt_account, name='get_available_proxies_for_yt_account'),
    path('yt-shorts/accounts/bulk-action/', yt_shorts_bulk.yt_accounts_bulk_action, name='yt_accounts_bulk_action'),
    
    # YouTube Cookie Robot
    path('yt-shorts/cookie-robot/', yt_shorts_bulk.yt_cookie_robot_list, name='yt_cookie_robot_list'),
    path('yt-shorts/cookie-robot/create/', yt_shorts_bulk.yt_cookie_robot_create, name='yt_cookie_robot_create'),
    path('yt-shorts/cookie-robot/<int:task_id>/', yt_shorts_bulk.yt_cookie_robot_detail, name='yt_cookie_robot_detail'),
    path('yt-shorts/cookie-robot/<int:task_id>/delete/', yt_shorts_bulk.yt_cookie_robot_delete, name='yt_cookie_robot_delete'),
    
    # Analytics Management
    path('analytics/', analytics.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/add/', analytics.analytics_add, name='analytics_add'),
    path('analytics/<int:pk>/', analytics.analytics_detail, name='analytics_detail'),
    path('analytics/<int:pk>/edit/', analytics.analytics_edit, name='analytics_edit'),
    path('analytics/<int:pk>/delete/', analytics.analytics_delete, name='analytics_delete'),
    path('analytics/api/summary/', analytics.analytics_api_summary, name='analytics_api_summary'),
    
    # Analytics Collector
    path('analytics/collector/', analytics_collector.analytics_collector, name='analytics_collector'),
    path('analytics/collector/api/', analytics_collector.analytics_collector_api, name='analytics_collector_api'),
] 