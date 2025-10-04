"""
URL configuration for instagram_uploader project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from uploader.views_auth import logout_view
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def post_login_redirect(request):
    # Superuser → root dashboard
    if request.user.is_superuser:
        return redirect('dashboard')
    # Client → client dashboard if has client; else agency
    from cabinet.models import Client, Agency
    client = Client.objects.filter(user=request.user).first()
    if client:
        return redirect('cabinet_agency_dashboard')
    agency = Agency.objects.filter(owner=request.user).first()
    if agency:
        return redirect('cabinet_agency_dashboard')
    return redirect('login')
from django.conf import settings
from django.conf.urls.static import static
import os
import sys

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tiktok/', include('tiktok_uploader.urls')),  # TikTok automation routes (MUST be before uploader.urls)
    path('cabinet/', include('cabinet.urls')),
    path('', include('uploader.urls')),  # Instagram routes (includes old tiktok paths, but new app has priority)
    path('login/', auth_views.LoginView.as_view(template_name='uploader/login.html', redirect_authenticated_user=True), name='login'),
    path('post-login/', login_required(post_login_redirect), name='post_login'),
    path('logout/', logout_view, name='logout'),
]

# Always serve static and media files 
# This ensures static files work in all environments including Docker
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
