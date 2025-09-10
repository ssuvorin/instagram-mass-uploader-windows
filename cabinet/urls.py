from django.urls import path
from . import views


urlpatterns = [
    path('', views.dashboard, name='cabinet_dashboard'),
    path('admin/', views.admin_dashboard, name='cabinet_admin_dashboard'),
    path('agency/', views.agency_dashboard, name='cabinet_agency_dashboard'),
    path('agency/calculator/', views.agency_calculator, name='cabinet_agency_calculator'),
    path('manage/agencies/', views.manage_agencies, name='cabinet_manage_agencies'),
    path('manage/clients/', views.manage_clients, name='cabinet_manage_clients'),
    path('manage/hashtags/', views.manage_hashtags, name='cabinet_manage_hashtags'),
    path('manage/agencies/<int:agency_id>/delete/', views.delete_agency, name='cabinet_delete_agency'),
    path('manage/clients/<int:client_id>/delete/', views.delete_client, name='cabinet_delete_client'),
    path('manage/hashtags/<int:item_id>/delete/', views.delete_client_hashtag, name='cabinet_delete_client_hashtag'),
    path('manage/clients/<int:client_id>/reset-password/', views.reset_client_user_password, name='cabinet_reset_client_password'),
    path('export/excel/', views.export_excel, name='cabinet_export_excel'),
    # Details
    path('hashtag/<str:hashtag>/', views.hashtag_detail, name='cabinet_hashtag_detail'),
    path('account/<int:account_id>/', views.account_detail_analytics, name='cabinet_account_detail'),
    # API endpoints compatible with personal_cab
    path('api/search/', views.search_view, name='cabinet_search'),
    path('api/client-data/', views.client_data_view, name='cabinet_client_data'),
    path('api/agency-clients/', views.agency_clients_view, name='cabinet_agency_clients'),
    path('api/dashboard-data/', views.dashboard_data_view, name='cabinet_dashboard_data'),
    path('api/agency-calc-quote', views.agency_calc_quote, name='cabinet_agency_calc_quote'),
    path('api/admin/agency/<int:agency_id>/reset-owner/', views.api_admin_reset_agency_owner, name='cabinet_api_admin_reset_agency_owner'),
    path('export/calculations/csv/', views.export_calculations_csv, name='cabinet_export_calculations_csv'),
    path('download/calculation/<int:calculation_id>/excel/', views.download_calculation_excel, name='cabinet_download_calculation_excel'),
    path('api/calculation/<int:calculation_id>/', views.calculation_details_api, name='cabinet_calculation_details_api'),
    path('api/calculations/', views.calculations_list_api, name='cabinet_calculations_list_api'),
]


