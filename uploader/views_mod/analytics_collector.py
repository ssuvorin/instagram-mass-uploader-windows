from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from ..analytics_forms import ClientAnalyticsForm
from ..models import HashtagAnalytics
from cabinet.models import Client, ClientHashtag


@login_required
@require_http_methods(["GET", "POST"])
def analytics_collector(request):
    """UI: Collect manual analytics data for clients - similar to hashtag analyzer"""
    # Only superusers can access analytics collector
    if not request.user.is_superuser:
        messages.error(request, 'Доступ запрещен. Только администраторы могут собирать аналитику.')
        return redirect('dashboard')
    
    # Get all clients for dropdown
    clients = Client.objects.all().order_by('name')
    
    # Create empty form for GET request
    form = ClientAnalyticsForm()
    
    context = {
        'clients': clients,
        'active_tab': 'analytics',
        'form': form,
        'form_data': {},  # Empty form data for GET request
    }

    if request.method == 'GET':
        return render(request, 'uploader/analytics/collector.html', context)

    # Handle POST request
    client_id = request.POST.get('client_id')
    social_network = request.POST.get('social_network')
    hashtag = request.POST.get('hashtag', '').strip()
    
    if not client_id or not social_network:
        messages.error(request, 'Выберите клиента и социальную сеть')
        context['form_client_id'] = client_id
        context['form_social_network'] = social_network
        return render(request, 'uploader/analytics/collector.html', context)
    
    if not hashtag:
        messages.error(request, 'Выберите хэштег')
        context['form_client_id'] = client_id
        context['form_social_network'] = social_network
        return render(request, 'uploader/analytics/collector.html', context)

    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        messages.error(request, 'Клиент не найден')
        return render(request, 'uploader/analytics/collector.html', context)

    # Create form with initial data
    form_data = {
        'client': client_id,
        'social_network': social_network,
        'hashtag': hashtag,
        'created_at': request.POST.get('created_at', ''),
        'analyzed_medias': request.POST.get('analyzed_medias', '') or 0,
        'total_views': request.POST.get('total_views', '') or 0,
        'total_likes': request.POST.get('total_likes', '') or 0,
        'total_comments': request.POST.get('total_comments', '') or 0,
        'total_shares': request.POST.get('total_shares', '') or 0,
        'total_followers': request.POST.get('total_followers', '') or 0,
        'growth_rate': request.POST.get('growth_rate', '') or 0.0,
        'notes': request.POST.get('notes', ''),
    }
    
    # Add platform-specific fields
    if social_network == 'INSTAGRAM':
        form_data.update({
            'instagram_stories_views': request.POST.get('instagram_stories_views', '') or 0,
            'instagram_reels_views': request.POST.get('instagram_reels_views', '') or 0,
        })
    elif social_network == 'YOUTUBE':
        form_data.update({
            'youtube_subscribers': request.POST.get('youtube_subscribers', '') or 0,
            'youtube_watch_time': request.POST.get('youtube_watch_time', '') or 0,
        })
    elif social_network == 'TIKTOK':
        form_data.update({
            'tiktok_video_views': request.POST.get('tiktok_video_views', '') or 0,
            'tiktok_profile_views': request.POST.get('tiktok_profile_views', '') or 0,
        })
    
    # Add advanced metrics
    form_data.update({
        'total_accounts': request.POST.get('total_accounts', '') or 0,
        'avg_videos_per_account': request.POST.get('avg_videos_per_account', '') or 0.0,
        'max_videos_per_account': request.POST.get('max_videos_per_account', '') or 0,
        'avg_views_per_video': request.POST.get('avg_views_per_video', '') or 0.0,
        'max_views_per_video': request.POST.get('max_views_per_video', '') or 0,
        'avg_views_per_account': request.POST.get('avg_views_per_account', '') or 0.0,
        'max_views_per_account': request.POST.get('max_views_per_account', '') or 0,
        'avg_likes_per_video': request.POST.get('avg_likes_per_video', '') or 0.0,
        'max_likes_per_video': request.POST.get('max_likes_per_video', '') or 0,
        'avg_likes_per_account': request.POST.get('avg_likes_per_account', '') or 0.0,
        'max_likes_per_account': request.POST.get('max_likes_per_account', '') or 0,
    })

    form = ClientAnalyticsForm(form_data)
    
    if form.is_valid():
        analytics = form.save(commit=False)
        analytics.is_manual = True
        analytics.created_by = request.user
        
        # Handle created_at separately
        created_at_str = request.POST.get('created_at', '')
        print(f"DEBUG: Received created_at_str: '{created_at_str}'")
        if created_at_str:
            try:
                from django.utils.dateparse import parse_datetime
                from django.utils import timezone
                from datetime import datetime
                
                # Try different parsing methods
                parsed_datetime = None
                
                # Method 1: Try parse_datetime (for ISO format)
                try:
                    parsed_datetime = parse_datetime(created_at_str)
                    print(f"DEBUG: parse_datetime result: {parsed_datetime}")
                except Exception as e:
                    print(f"DEBUG: parse_datetime failed: {e}")
                
                # Method 2: Try manual parsing for datetime-local format (YYYY-MM-DDTHH:MM)
                if not parsed_datetime:
                    try:
                        # datetime-local format: 2025-10-07T01:15
                        parsed_datetime = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M')
                        print(f"DEBUG: strptime result: {parsed_datetime}")
                    except Exception as e:
                        print(f"DEBUG: strptime failed: {e}")
                
                if parsed_datetime:
                    # Make timezone aware if it's naive
                    if timezone.is_naive(parsed_datetime):
                        parsed_datetime = timezone.make_aware(parsed_datetime)
                    analytics.created_at = parsed_datetime
                    print(f"DEBUG: Successfully set created_at to: {analytics.created_at}")
                else:
                    print(f"DEBUG: Failed to parse created_at, using current time")
                    
            except Exception as e:
                # If parsing fails, use current time
                print(f"DEBUG: Exception during created_at parsing: {e}")
                pass
        else:
            print(f"DEBUG: No created_at_str provided, using current time")
        
        analytics.save()
        
        messages.success(request, f'Аналитика успешно добавлена для {client.name} - {analytics.get_social_network_display()}')
        return redirect('analytics_collector')
    else:
        # Show form errors
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
        
        context.update({
            'form_client_id': client_id,
            'form_social_network': social_network,
            'form_data': form_data,
        })
        return render(request, 'uploader/analytics/collector.html', context)


@login_required
def analytics_collector_api(request):
    """API endpoint for analytics collector - get client info"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    client_id = request.GET.get('client_id')
    if not client_id:
        return JsonResponse({'error': 'Client ID required'}, status=400)
    
    try:
        client = Client.objects.get(id=client_id)
        
        # Get client hashtags
        hashtags = ClientHashtag.objects.filter(client=client).values_list('hashtag', flat=True)
        
        return JsonResponse({
            'client': {
                'id': client.id,
                'name': client.name,
                'agency': client.agency.name if client.agency else None,
            },
            'hashtags': list(hashtags)
        })
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Client not found'}, status=404)
