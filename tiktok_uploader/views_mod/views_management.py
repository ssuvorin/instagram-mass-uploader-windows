"""
Client and Tag Management Views
================================

Представления для управления клиентами и тегами аккаунтов.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count

from cabinet.models import Client
from tiktok_uploader.models import AccountTag, TikTokAccount

logger = logging.getLogger('tiktok_uploader')


# ============================================================================
# CLIENT MANAGEMENT
# ============================================================================

@login_required
def client_management(request):
    """
    Страница управления клиентами.
    Показывает список всех клиентов с количеством аккаунтов.
    """
    clients = Client.objects.annotate(
        tiktok_accounts_count=Count('tiktok_accounts')
    ).order_by('name')
    
    context = {
        'clients': clients,
    }
    
    return render(request, 'tiktok_uploader/management/clients.html', context)


@login_required
def client_create(request):
    """
    Создание нового клиента.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        
        if not name:
            messages.error(request, 'Client name is required')
            return redirect('tiktok_uploader:client_create')
        
        # Проверка на существование
        if Client.objects.filter(name=name).exists():
            messages.error(request, f'Client "{name}" already exists')
            return redirect('tiktok_uploader:client_create')
        
        try:
            client = Client.objects.create(
                name=name,
                user=request.user
            )
            
            messages.success(request, f'Client "{name}" created successfully')
            logger.info(f"Client created: {name} by {request.user.username}")
            
            return redirect('tiktok_uploader:client_management')
            
        except Exception as e:
            logger.error(f"Error creating client: {str(e)}")
            messages.error(request, f'Error creating client: {str(e)}')
            return redirect('tiktok_uploader:client_create')
    
    return render(request, 'tiktok_uploader/management/client_form.html', {
        'action': 'Create'
    })


@login_required
def client_edit(request, client_id):
    """
    Редактирование клиента.
    """
    client = get_object_or_404(Client, id=client_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        
        if not name:
            messages.error(request, 'Client name is required')
            return redirect('tiktok_uploader:client_edit', client_id=client_id)
        
        # Проверка на существование (кроме текущего)
        if Client.objects.filter(name=name).exclude(id=client_id).exists():
            messages.error(request, f'Client "{name}" already exists')
            return redirect('tiktok_uploader:client_edit', client_id=client_id)
        
        try:
            client.name = name
            client.save()
            
            messages.success(request, f'Client "{name}" updated successfully')
            logger.info(f"Client updated: {name} by {request.user.username}")
            
            return redirect('tiktok_uploader:client_management')
            
        except Exception as e:
            logger.error(f"Error updating client: {str(e)}")
            messages.error(request, f'Error updating client: {str(e)}')
            return redirect('tiktok_uploader:client_edit', client_id=client_id)
    
    context = {
        'client': client,
        'action': 'Edit'
    }
    
    return render(request, 'tiktok_uploader/management/client_form.html', context)


@login_required
@require_http_methods(["POST"])
def client_delete(request, client_id):
    """
    Удаление клиента.
    """
    client = get_object_or_404(Client, id=client_id)
    
    # Проверяем есть ли привязанные аккаунты
    accounts_count = client.tiktok_accounts.count()
    
    if accounts_count > 0:
        messages.error(
            request,
            f'Cannot delete client "{client.name}": {accounts_count} TikTok account(s) are linked to this client. '
            f'Please reassign or delete these accounts first.'
        )
        return redirect('tiktok_uploader:client_management')
    
    client_name = client.name
    client.delete()
    
    messages.success(request, f'Client "{client_name}" deleted successfully')
    logger.info(f"Client deleted: {client_name} by {request.user.username}")
    
    return redirect('tiktok_uploader:client_management')


# ============================================================================
# TAG MANAGEMENT
# ============================================================================

@login_required
def tag_management(request):
    """
    Страница управления тегами.
    Показывает список всех тегов с количеством аккаунтов.
    """
    tags = AccountTag.objects.all().order_by('name')
    
    # Добавляем количество аккаунтов для каждого тега
    tags_with_counts = []
    for tag in tags:
        accounts_count = TikTokAccount.objects.filter(tag=tag.name).count()
        tags_with_counts.append({
            'tag': tag,
            'accounts_count': accounts_count
        })
    
    context = {
        'tags_with_counts': tags_with_counts,
    }
    
    return render(request, 'tiktok_uploader/management/tags.html', context)


@login_required
def tag_create(request):
    """
    Создание нового тега.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip().lower()
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, 'Tag name is required')
            return redirect('tiktok_uploader:tag_create')
        
        # Проверка на существование
        if AccountTag.objects.filter(name=name).exists():
            messages.error(request, f'Tag "{name}" already exists')
            return redirect('tiktok_uploader:tag_create')
        
        try:
            tag = AccountTag.objects.create(
                name=name,
                description=description
            )
            
            messages.success(request, f'Tag "{name}" created successfully')
            logger.info(f"Tag created: {name} by {request.user.username}")
            
            return redirect('tiktok_uploader:tag_management')
            
        except Exception as e:
            logger.error(f"Error creating tag: {str(e)}")
            messages.error(request, f'Error creating tag: {str(e)}')
            return redirect('tiktok_uploader:tag_create')
    
    return render(request, 'tiktok_uploader/management/tag_form.html', {
        'action': 'Create'
    })


@login_required
def tag_edit(request, tag_id):
    """
    Редактирование тега.
    """
    tag = get_object_or_404(AccountTag, id=tag_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip().lower()
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, 'Tag name is required')
            return redirect('tiktok_uploader:tag_edit', tag_id=tag_id)
        
        # Проверка на существование (кроме текущего)
        if AccountTag.objects.filter(name=name).exclude(id=tag_id).exists():
            messages.error(request, f'Tag "{name}" already exists')
            return redirect('tiktok_uploader:tag_edit', tag_id=tag_id)
        
        try:
            old_name = tag.name
            tag.name = name
            tag.description = description
            tag.save()
            
            # Обновляем все аккаунты с старым тегом
            if old_name != name:
                TikTokAccount.objects.filter(tag=old_name).update(tag=name)
                messages.info(request, f'Updated {TikTokAccount.objects.filter(tag=name).count()} account(s) with new tag name')
            
            messages.success(request, f'Tag "{name}" updated successfully')
            logger.info(f"Tag updated: {old_name} -> {name} by {request.user.username}")
            
            return redirect('tiktok_uploader:tag_management')
            
        except Exception as e:
            logger.error(f"Error updating tag: {str(e)}")
            messages.error(request, f'Error updating tag: {str(e)}')
            return redirect('tiktok_uploader:tag_edit', tag_id=tag_id)
    
    context = {
        'tag': tag,
        'action': 'Edit'
    }
    
    return render(request, 'tiktok_uploader/management/tag_form.html', context)


@login_required
@require_http_methods(["POST"])
def tag_delete(request, tag_id):
    """
    Удаление тега.
    """
    tag = get_object_or_404(AccountTag, id=tag_id)
    
    # Проверяем есть ли аккаунты с этим тегом
    accounts_count = TikTokAccount.objects.filter(tag=tag.name).count()
    
    if accounts_count > 0:
        messages.error(
            request,
            f'Cannot delete tag "{tag.name}": {accounts_count} account(s) are using this tag. '
            f'Please reassign or remove the tag from these accounts first.'
        )
        return redirect('tiktok_uploader:tag_management')
    
    tag_name = tag.name
    tag.delete()
    
    messages.success(request, f'Tag "{tag_name}" deleted successfully')
    logger.info(f"Tag deleted: {tag_name} by {request.user.username}")
    
    return redirect('tiktok_uploader:tag_management')


# ============================================================================
# API ENDPOINTS для получения списков (для форм)
# ============================================================================

@login_required
def api_get_tags(request):
    """
    API endpoint для получения списка тегов (для dropdown).
    """
    tags = AccountTag.objects.all().order_by('name').values('id', 'name')
    return JsonResponse({
        'success': True,
        'tags': list(tags)
    })


@login_required
def api_get_clients(request):
    """
    API endpoint для получения списка клиентов (для dropdown).
    """
    clients = Client.objects.all().order_by('name').values('id', 'name')
    return JsonResponse({
        'success': True,
        'clients': list(clients)
    })

