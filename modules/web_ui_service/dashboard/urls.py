from django.urls import path
from . import views, api_views

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
] 