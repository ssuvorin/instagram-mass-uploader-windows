from django.urls import path
from . import views, api_views
from . import monitoring_views

urlpatterns = [
    # Overrides for start actions to call worker
    path('bulk-upload/<int:task_id>/start/', views.start_bulk_upload_via_worker, name='start_bulk_upload'),
    path('bulk-login/<int:task_id>/start/', views.start_bulk_login_via_worker, name='start_bulk_login'),
    path('warmup/<int:task_id>/start/', views.start_warmup_via_worker, name='warmup_task_start'),
    path('avatars/<int:task_id>/start/', views.start_avatar_via_worker, name='start_avatar_task'),
    path('bio/<int:task_id>/start/', views.start_bio_via_worker, name='start_bio_task'),
    path('follow/tasks/<int:task_id>/start/', views.start_follow_via_worker, name='follow_task_start'),
    path('proxy_diag/<int:task_id>/start/', views.start_proxy_diag_via_worker, name='proxy_diag_task_start'),
    path('media_uniq/<int:task_id>/start/', views.start_media_uniq_via_worker, name='media_uniq_task_start'),

    # Pull-mode APIs for worker (must be protected by token in views)
    path('api/bulk-tasks/<int:task_id>/aggregate', api_views.bulk_task_aggregate, name='api_bulk_task_aggregate'),
    path('api/media/<int:video_id>/download', api_views.media_download, name='api_media_download'),
    path('api/media/images/<int:image_id>/download', api_views.avatar_media_download, name='api_avatar_media_download'),
    path('api/bulk-tasks/<int:task_id>/status', api_views.bulk_task_status, name='api_bulk_task_status'),
    path('api/bulk-accounts/<int:account_task_id>/status', api_views.bulk_account_status, name='api_bulk_account_status'),
    path('api/bulk-accounts/<int:account_task_id>/counters', api_views.bulk_account_counters, name='api_bulk_account_counters'),

    # Aggregates for other tasks
    path('api/bulk_login/<int:task_id>/aggregate', api_views.bulk_login_aggregate, name='api_bulk_login_aggregate'),
    path('api/warmup/<int:task_id>/aggregate', api_views.warmup_aggregate, name='api_warmup_aggregate'),
    path('api/avatar/<int:task_id>/aggregate', api_views.avatar_aggregate, name='api_avatar_aggregate'),
    path('api/bio/<int:task_id>/aggregate', api_views.bio_aggregate, name='api_bio_aggregate'),
    path('api/follow/<int:task_id>/aggregate', api_views.follow_aggregate, name='api_follow_aggregate'),
    path('api/proxy_diag/<int:task_id>/aggregate', api_views.proxy_diag_aggregate, name='api_proxy_diag_aggregate'),
    path('api/media_uniq/<int:task_id>/aggregate', api_views.media_uniq_aggregate, name='api_media_uniq_aggregate'),

    # Generic status endpoints (worker uses these for non-bulk kinds)
    path('api/<str:kind>/<int:task_id>/status', api_views.generic_task_status, name='api_generic_task_status'),
    path('api/<str:kind>/accounts/<int:account_task_id>/status', api_views.generic_account_status, name='api_generic_account_status'),
    path('api/<str:kind>/accounts/<int:account_task_id>/counters', api_views.generic_account_counters, name='api_generic_account_counters'),

    # Worker registry and health
    path('workers/', views.workers_list, name='workers_list'),
    path('workers/health-poll', views.health_poll, name='workers_health_poll'),
    path('api/worker/register', api_views.worker_register, name='api_worker_register'),
    path('api/worker/heartbeat', api_views.worker_heartbeat, name='api_worker_heartbeat'),
    
    # Production monitoring views
    path('monitoring/', monitoring_views.monitoring_dashboard, name='monitoring_dashboard'),
    path('monitoring/errors/', monitoring_views.error_logs_view, name='error_logs_view'),
    path('monitoring/performance/', monitoring_views.performance_metrics, name='performance_metrics'),
    path('monitoring/worker/<int:worker_id>/', monitoring_views.worker_details, name='worker_details'),
    path('api/monitoring/metrics/', monitoring_views.system_metrics_api, name='system_metrics_api'),
    path('api/monitoring/worker/<int:worker_id>/restart/', monitoring_views.restart_worker, name='restart_worker'),
    
    # Account Management APIs
    path('api/accounts/create/', api_views.create_account_api, name='api_create_account'),
    path('api/accounts/import/', api_views.import_accounts_api, name='api_import_accounts'),
    path('api/accounts/<int:account_id>/edit/', api_views.edit_account_api, name='api_edit_account'),
    path('api/accounts/bulk-change-proxy/', api_views.bulk_change_proxy_api, name='api_bulk_change_proxy'),
    path('api/accounts/<int:account_id>/create-dolphin-profile/', api_views.create_dolphin_profile_api, name='api_create_dolphin_profile'),
    
    # Proxy Management APIs
    path('api/proxies/create/', api_views.create_proxy_api, name='api_create_proxy'),
    path('api/proxies/import/', api_views.import_proxies_api, name='api_import_proxies'),
    path('api/proxies/validate-all/', api_views.validate_all_proxies_api, name='api_validate_all_proxies'),
    path('api/proxies/cleanup-inactive/', api_views.cleanup_inactive_proxies_api, name='api_cleanup_inactive_proxies'),
    
    # Media Uniquifier APIs
    path('api/media/uniquify/', api_views.media_uniquify_start_api, name='api_media_uniquify_start'),
    path('api/media/uniquify/<str:task_id>/status/', api_views.media_uniquify_status_api, name='api_media_uniquify_status'),
    
    # Cookie Robot APIs
    path('api/cookie-robot/start/', api_views.cookie_robot_start_api, name='api_cookie_robot_start'),
    
    # Follow Category Management APIs
    path('api/follow/categories/create/', api_views.create_follow_category_api, name='api_create_follow_category'),
    path('api/follow/categories/<int:category_id>/targets/', api_views.add_follow_targets_api, name='api_add_follow_targets'),
    
    # TikTok APIs (Placeholder)
    path('api/tiktok/booster/start/', api_views.tiktok_booster_start_api, name='api_tiktok_booster_start'),
    path('api/tiktok/booster/status/', api_views.tiktok_booster_status_api, name='api_tiktok_booster_status'),
    
    # Enhanced Monitoring APIs
    path('api/monitoring/worker/metrics/', api_views.report_worker_metrics_api, name='api_report_worker_metrics'),
    path('api/monitoring/worker/errors/', api_views.report_worker_error_api, name='api_report_worker_error'),
    path('api/monitoring/worker/<str:worker_id>/status/', api_views.get_worker_status_api, name='api_get_worker_status'),
    path('api/monitoring/system/health/', api_views.get_system_health_api, name='api_get_system_health'),
    path('api/monitoring/worker/<str:worker_id>/restart/', api_views.trigger_worker_restart_api, name='api_trigger_worker_restart'),
    
    # Task Lock Management APIs
    path('api/locks/acquire/', api_views.acquire_task_lock_api, name='api_acquire_task_lock'),
    path('api/locks/release/', api_views.release_task_lock_api, name='api_release_task_lock'),
] 