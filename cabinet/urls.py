from django.urls import path
from . import views


urlpatterns = [
    path('', views.dashboard, name='cabinet_dashboard'),
    path('admin/', views.admin_dashboard, name='cabinet_admin_dashboard'),
    path('agency/', views.agency_dashboard, name='cabinet_agency_dashboard'),
    path('manage/agencies/', views.manage_agencies, name='cabinet_manage_agencies'),
    path('manage/clients/', views.manage_clients, name='cabinet_manage_clients'),
    path('manage/hashtags/', views.manage_hashtags, name='cabinet_manage_hashtags'),
    # API endpoints compatible with personal_cab
    path('api/search/', views.search_view, name='cabinet_search'),
    path('api/client-data/', views.client_data_view, name='cabinet_client_data'),
    path('api/agency-clients/', views.agency_clients_view, name='cabinet_agency_clients'),
    path('api/dashboard-data/', views.dashboard_data_view, name='cabinet_dashboard_data'),
]


