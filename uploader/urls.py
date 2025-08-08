from django.urls import path
from . import views
from . import views_avatar
from . import views_follow

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
    path('accounts/<int:account_id>/warm/', views.warm_account, name='warm_account'),
    path('accounts/<int:account_id>/edit/', views.edit_account, name='edit_account'),
    path('accounts/<int:account_id>/change-proxy/', views.change_account_proxy, name='change_account_proxy'),
    path('accounts/<int:account_id>/create-profile/', views.create_dolphin_profile, name='create_dolphin_profile'),
    path('accounts/<int:account_id>/delete/', views.delete_account, name='delete_account'),
    path('accounts/bulk-change-proxy/', views.bulk_change_proxy, name='bulk_change_proxy'),
    path('accounts/refresh-dolphin-proxies/', views.refresh_dolphin_proxies, name='refresh_dolphin_proxies'),
    
    # Proxies
    path('proxies/', views.proxy_list, name='proxy_list'),
    path('proxies/create/', views.create_proxy, name='create_proxy'),
    path('proxies/<int:proxy_id>/edit/', views.edit_proxy, name='edit_proxy'),
    path('proxies/<int:proxy_id>/test/', views.test_proxy, name='test_proxy'),
    path('proxies/<int:proxy_id>/delete/', views.delete_proxy, name='delete_proxy'),
    path('proxies/import/', views.import_proxies, name='import_proxies'),
    path('proxies/validate-all/', views.validate_all_proxies, name='validate_all_proxies'),
    path('proxies/cleanup-inactive/', views.cleanup_inactive_proxies, name='cleanup_inactive_proxies'),
    
    # Bulk Upload
    path('bulk-upload/', views.bulk_upload_list, name='bulk_upload_list'),
    path('bulk-upload/create/', views.create_bulk_upload, name='create_bulk_upload'),
    path('bulk-upload/<int:task_id>/', views.bulk_upload_detail, name='bulk_upload_detail'),
    path('bulk-upload/<int:task_id>/add-videos/', views.add_bulk_videos, name='add_bulk_videos'),
    path('bulk-upload/<int:task_id>/add-titles/', views.add_bulk_titles, name='add_bulk_titles'),
    path('bulk-upload/<int:task_id>/start/', views.start_bulk_upload, name='start_bulk_upload'),
    path('bulk-upload/<int:task_id>/delete/', views.delete_bulk_upload, name='delete_bulk_upload'),
    path('bulk-upload/<int:task_id>/logs/', views.get_bulk_task_logs, name='bulk_task_logs'),
    path('bulk-upload/<int:task_id>/bulk-edit-location-mentions/', views.bulk_edit_location_mentions, name='bulk_edit_location_mentions'),
    path('bulk-upload/video/<int:video_id>/edit-location-mentions/', views.edit_video_location_mentions, name='edit_video_location_mentions'),
    
    # Cookies Dashboard
    path('cookies/', views.cookie_dashboard, name='cookie_dashboard'),
    path('cookies/tasks/', views.cookie_task_list, name='cookie_task_list'),
    path('cookies/tasks/create/', views.create_cookie_robot_task, name='create_cookie_robot_task'),
    path('cookies/tasks/<int:task_id>/', views.cookie_task_detail, name='cookie_task_detail'),
    path('cookies/tasks/<int:task_id>/start/', views.start_cookie_task, name='start_cookie_task'),
    path('cookies/tasks/<int:task_id>/stop/', views.stop_cookie_task, name='stop_cookie_task'),
    path('cookies/tasks/<int:task_id>/delete/', views.delete_cookie_task, name='delete_cookie_task'),
    path('cookies/tasks/<int:task_id>/logs/', views.get_cookie_task_logs, name='cookie_task_logs'),
    path('cookies/accounts/<int:account_id>/', views.account_cookies, name='account_cookies'),
    path('cookies/bulk/', views.bulk_cookie_robot, name='bulk_cookie_robot'),

    # Avatars
    path('avatars/', views_avatar.avatar_task_list, name='avatar_task_list'),
    path('avatars/create/', views_avatar.create_avatar_task, name='create_avatar_task'),
    path('avatars/<int:task_id>/', views_avatar.avatar_task_detail, name='avatar_task_detail'),
    path('avatars/<int:task_id>/start/', views_avatar.start_avatar_task, name='start_avatar_task'),
    path('avatars/<int:task_id>/logs/', views_avatar.get_avatar_task_logs, name='avatar_task_logs'),
    
    # Captcha API
    path('api/captcha-notification/', views.captcha_notification, name='captcha_notification'),
    path('api/captcha-status/<int:task_id>/', views.get_captcha_status, name='get_captcha_status'),
    path('api/captcha-clear/<int:task_id>/', views.clear_captcha_notification, name='clear_captcha_notification'),
] 

urlpatterns += [
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
] 