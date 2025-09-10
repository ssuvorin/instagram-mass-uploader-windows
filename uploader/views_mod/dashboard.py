"""Views module: dashboard (split from monolith)."""
from .common import *
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect


@login_required
@user_passes_test(lambda u: u.is_superuser)
def dashboard(request):
    """Dashboard with recent tasks and accounts"""
    tasks = UploadTask.objects.order_by('-created_at')[:10]
    accounts = InstagramAccount.objects.order_by('-last_used')[:10]
    
    # Get counts for dashboard stats
    tasks_count = UploadTask.objects.count()
    accounts_count = InstagramAccount.objects.count()
    proxies_count = Proxy.objects.count()
    completed_tasks_count = UploadTask.objects.filter(status='COMPLETED').count()
    
    # Get proxy stats
    active_proxies_count = Proxy.objects.filter(is_active=True).count()
    
    # Get proxy stats by status
    proxy_status_counts = {
        'active': Proxy.objects.filter(status='active').count(),
        'inactive': Proxy.objects.filter(status='inactive').count(),
        'banned': Proxy.objects.filter(status='banned').count(),
        'checking': Proxy.objects.filter(status='checking').count()
    }
    
    # Get proxy stats by type
    proxy_type_counts = {
        'http': Proxy.objects.filter(proxy_type='HTTP').count(),
        'socks5': Proxy.objects.filter(proxy_type='SOCKS5').count(),
        'https': Proxy.objects.filter(proxy_type='HTTPS').count()
    }
    
    # Get recently verified proxies
    recently_verified_proxies = Proxy.objects.filter(
        last_verified__isnull=False
    ).order_by('-last_verified')[:5]
    
    # Get inactive proxies statistics for cleanup recommendations
    inactive_proxies_total = Proxy.objects.filter(
        Q(status='inactive') | Q(is_active=False)
    ).count()
    
    inactive_proxies_assigned = Proxy.objects.filter(
        Q(status='inactive') | Q(is_active=False),
        assigned_account__isnull=False
    ).count()
    
    inactive_proxies_unassigned = inactive_proxies_total - inactive_proxies_assigned
    
    context = {
        'tasks': tasks,
        'accounts': accounts,
        'tasks_count': tasks_count,
        'accounts_count': accounts_count,
        'proxies_count': proxies_count,
        'completed_tasks_count': completed_tasks_count,
        'active_proxies_count': active_proxies_count,
        'recently_verified_proxies': recently_verified_proxies,
        'proxy_status_counts': proxy_status_counts,
        'proxy_type_counts': proxy_type_counts,
        'inactive_proxies_total': inactive_proxies_total,
        'inactive_proxies_assigned': inactive_proxies_assigned,
        'inactive_proxies_unassigned': inactive_proxies_unassigned,
        'active_tab': 'dashboard'
    }
    return render(request, 'uploader/dashboard.html', context)
