from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from ..analytics_forms import ClientAnalyticsForm, ClientAnalyticsFilterForm
from ..models import HashtagAnalytics
from cabinet.models import Client


@login_required
def analytics_dashboard(request):
    """Dashboard for managing client analytics - only for superusers"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Only administrators can manage analytics.')
        return redirect('dashboard')
    
    # Get filter form
    filter_form = ClientAnalyticsFilterForm(request.GET)
    
    # Build queryset with filters
    analytics = HashtagAnalytics.objects.filter(is_manual=True).select_related('client', 'created_by').order_by('-created_at')
    
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('client'):
            analytics = analytics.filter(client=filter_form.cleaned_data['client'])
        if filter_form.cleaned_data.get('social_network'):
            analytics = analytics.filter(social_network=filter_form.cleaned_data['social_network'])
        if filter_form.cleaned_data.get('period_start'):
            analytics = analytics.filter(period_start__gte=filter_form.cleaned_data['period_start'])
        if filter_form.cleaned_data.get('period_end'):
            analytics = analytics.filter(period_end__lte=filter_form.cleaned_data['period_end'])
    
    # Pagination
    paginator = Paginator(analytics, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'active_tab': 'analytics',
        'total_count': analytics.count(),
    }
    
    return render(request, 'uploader/analytics/dashboard.html', context)


@login_required
def analytics_add(request):
    """Add new analytics data - only for superusers"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Only administrators can add analytics.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ClientAnalyticsForm(request.POST)
        if form.is_valid():
            analytics = form.save(commit=False)
            analytics.created_by = request.user
            analytics.save()
            messages.success(request, f'Analytics data added successfully for {analytics.client.name} - {analytics.get_social_network_display()}')
            return redirect('analytics_dashboard')
    else:
        form = ClientAnalyticsForm()
    
    context = {
        'form': form,
        'active_tab': 'analytics',
        'title': 'Add Analytics Data'
    }
    
    return render(request, 'uploader/analytics/form.html', context)


@login_required
def analytics_edit(request, pk):
    """Edit analytics data - only for superusers"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Only administrators can edit analytics.')
        return redirect('dashboard')
    
    analytics = get_object_or_404(HashtagAnalytics, pk=pk, is_manual=True)
    
    if request.method == 'POST':
        form = ClientAnalyticsForm(request.POST, instance=analytics)
        if form.is_valid():
            form.save()
            messages.success(request, f'Analytics data updated successfully for {analytics.client.name} - {analytics.get_social_network_display()}')
            return redirect('analytics_dashboard')
    else:
        form = ClientAnalyticsForm(instance=analytics)
    
    context = {
        'form': form,
        'analytics': analytics,
        'active_tab': 'analytics',
        'title': f'Edit Analytics - {analytics.client.name}'
    }
    
    return render(request, 'uploader/analytics/form.html', context)


@login_required
def analytics_delete(request, pk):
    """Delete analytics data - only for superusers"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Only administrators can delete analytics.')
        return redirect('dashboard')
    
    analytics = get_object_or_404(HashtagAnalytics, pk=pk, is_manual=True)
    
    if request.method == 'POST':
        client_name = analytics.client.name
        social_network = analytics.get_social_network_display()
        analytics.delete()
        messages.success(request, f'Analytics data deleted successfully for {client_name} - {social_network}')
        return redirect('analytics_dashboard')
    
    context = {
        'analytics': analytics,
        'active_tab': 'analytics',
    }
    
    return render(request, 'uploader/analytics/delete_confirm.html', context)


@login_required
def analytics_detail(request, pk):
    """View analytics details - only for superusers"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Only administrators can view analytics.')
        return redirect('dashboard')
    
    analytics = get_object_or_404(HashtagAnalytics, pk=pk, is_manual=True)
    
    context = {
        'analytics': analytics,
        'active_tab': 'analytics',
    }
    
    return render(request, 'uploader/analytics/detail.html', context)


@login_required
def analytics_api_summary(request):
    """API endpoint for analytics summary - only for superusers"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Get summary statistics
    total_analytics = ClientAnalytics.objects.count()
    clients_count = ClientAnalytics.objects.values('client').distinct().count()
    
    # Group by social network
    by_network = {}
    for choice in ClientAnalytics.SOCIAL_NETWORK_CHOICES:
        count = ClientAnalytics.objects.filter(social_network=choice[0]).count()
        by_network[choice[1]] = count
    
    # Recent analytics (last 30 days)
    from django.utils import timezone
    from datetime import timedelta
    recent_date = timezone.now().date() - timedelta(days=30)
    recent_count = ClientAnalytics.objects.filter(created_at__date__gte=recent_date).count()
    
    return JsonResponse({
        'total_analytics': total_analytics,
        'clients_count': clients_count,
        'by_network': by_network,
        'recent_count': recent_count,
    })
