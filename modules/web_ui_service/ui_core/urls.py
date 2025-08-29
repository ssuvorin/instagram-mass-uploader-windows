"""
URL patterns for UI Core app - API-based distributed architecture.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Account Management
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/<int:account_id>/', views.account_detail, name='account_detail'),
    path('accounts/create/', views.create_account, name='create_account'),
    
    # Bulk Upload Tasks  
    path('bulk-upload/', views.bulk_upload_list, name='bulk_upload_list'),
    path('bulk-upload/create/', views.create_bulk_upload, name='create_bulk_upload'),
    path('bulk-upload/<int:task_id>/', views.bulk_upload_detail, name='bulk_upload_detail'),
    path('bulk-upload/<int:task_id>/start/', views.start_bulk_upload_via_worker, name='start_bulk_upload'),
    
    # API endpoints for AJAX
    path('api/tasks/<int:task_id>/status/', views.task_status_api, name='task_status_api'),
    path('health/', views.health_check, name='health_check'),
]