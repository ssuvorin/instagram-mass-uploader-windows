"""
UI Core Views - API-based views for distributed architecture.

These views replace direct ORM access with API calls to backend services.
"""

import logging
from typing import Dict, Any, List
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.core.paginator import Paginator

from .api_client import management_api, worker_api, monitoring_api

logger = logging.getLogger(__name__)


def dashboard(request):
    """Main dashboard view."""
    try:
        # Get summary data from management API
        accounts_response = management_api.get_accounts()
        tasks_response = management_api.get_bulk_tasks()
        
        context = {
            'accounts_count': len(accounts_response.get('results', [])) if accounts_response.get('success') else 0,
            'active_tasks': 0,  # TODO: Calculate from tasks
            'recent_tasks': tasks_response.get('results', [])[:5] if tasks_response.get('success') else [],
        }
        
        return render(request, 'uploader/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        messages.error(request, f"Dashboard load failed: {str(e)}")
        return render(request, 'uploader/dashboard.html', {'error': str(e)})


# Account Management Views
def account_list(request):
    """Instagram accounts list."""
    try:
        # Get accounts from management API
        response = management_api.get_accounts()
        
        if not response.get('success'):
            messages.error(request, f"Failed to load accounts: {response.get('error', 'Unknown error')}")
            accounts = []
        else:
            accounts = response.get('results', [])
        
        # Pagination
        paginator = Paginator(accounts, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'accounts': page_obj,
            'active_tab': 'accounts'
        }
        
        return render(request, 'uploader/account_list.html', context)
        
    except Exception as e:
        logger.error(f"Account list error: {e}")
        messages.error(request, f"Failed to load accounts: {str(e)}")
        return render(request, 'uploader/account_list.html', {'accounts': [], 'active_tab': 'accounts'})


def account_detail(request, account_id: int):
    """Account details view."""
    try:
        response = management_api.get_account(account_id)
        
        if not response.get('success'):
            messages.error(request, f"Account not found: {response.get('error', 'Unknown error')}")
            return redirect('account_list')
        
        account = response.get('data', {})
        
        context = {
            'account': account,
            'active_tab': 'accounts'
        }
        
        return render(request, 'uploader/account_detail.html', context)
        
    except Exception as e:
        logger.error(f"Account detail error: {e}")
        messages.error(request, f"Failed to load account: {str(e)}")
        return redirect('account_list')


def create_account(request):
    """Create new Instagram account."""
    if request.method == 'POST':
        try:
            account_data = {
                'username': request.POST.get('username'),
                'password': request.POST.get('password'),
                'email': request.POST.get('email', ''),
                'status': 'ACTIVE'
            }
            
            response = management_api.create_account(account_data)
            
            if response.get('success'):
                messages.success(request, f"Account {account_data['username']} created successfully")
                return redirect('account_list')
            else:
                messages.error(request, f"Failed to create account: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Create account error: {e}")
            messages.error(request, f"Failed to create account: {str(e)}")
    
    return render(request, 'uploader/create_account.html', {'active_tab': 'accounts'})


# Task Management Views
def bulk_upload_list(request):
    """Bulk upload tasks list."""
    try:
        response = management_api.get_bulk_tasks()
        
        if not response.get('success'):
            messages.error(request, f"Failed to load tasks: {response.get('error', 'Unknown error')}")
            tasks = []
        else:
            tasks = response.get('results', [])
        
        # Pagination
        paginator = Paginator(tasks, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'tasks': page_obj,
            'active_tab': 'bulk_upload'
        }
        
        return render(request, 'uploader/bulk_upload/list.html', context)
        
    except Exception as e:
        logger.error(f"Bulk upload list error: {e}")
        messages.error(request, f"Failed to load tasks: {str(e)}")
        return render(request, 'uploader/bulk_upload/list.html', {'tasks': [], 'active_tab': 'bulk_upload'})


def bulk_upload_detail(request, task_id: int):
    """Bulk upload task details."""
    try:
        response = management_api.get_bulk_task(task_id)
        
        if not response.get('success'):
            messages.error(request, f"Task not found: {response.get('error', 'Unknown error')}")
            return redirect('bulk_upload_list')
        
        task = response.get('data', {})
        
        # Get task status from worker API
        status_response = worker_api.get_task_status(task_id, 'bulk')
        if status_response.get('success'):
            task.update(status_response.get('data', {}))
        
        context = {
            'task': task,
            'active_tab': 'bulk_upload'
        }
        
        return render(request, 'uploader/bulk_upload/detail.html', context)
        
    except Exception as e:
        logger.error(f"Bulk upload detail error: {e}")
        messages.error(request, f"Failed to load task: {str(e)}")
        return redirect('bulk_upload_list')


def create_bulk_upload(request):
    """Create new bulk upload task."""
    if request.method == 'POST':
        try:
            task_data = {
                'name': request.POST.get('name'),
                'description': request.POST.get('description', ''),
                'strategy': request.POST.get('strategy', 'ROUND_ROBIN'),
                'concurrency': int(request.POST.get('concurrency', 1)),
                'delay_min_sec': int(request.POST.get('delay_min_sec', 5)),
                'delay_max_sec': int(request.POST.get('delay_max_sec', 15))
            }
            
            response = management_api.create_bulk_task(task_data)
            
            if response.get('success'):
                task_id = response.get('data', {}).get('id')
                messages.success(request, f"Bulk upload task created successfully")
                return redirect('bulk_upload_detail', task_id=task_id)
            else:
                messages.error(request, f"Failed to create task: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Create bulk upload error: {e}")
            messages.error(request, f"Failed to create task: {str(e)}")
    
    # Get accounts for task creation
    try:
        accounts_response = management_api.get_accounts()
        accounts = accounts_response.get('results', []) if accounts_response.get('success') else []
    except Exception:
        accounts = []
    
    context = {
        'accounts': accounts,
        'active_tab': 'bulk_upload'
    }
    
    return render(request, 'uploader/bulk_upload/create.html', context)


@require_POST
def start_bulk_upload_via_worker(request, task_id: int):
    """Start bulk upload task via worker API."""
    try:
        response = worker_api.start_bulk_task(task_id)
        
        if response.get('success'):
            messages.success(request, "Bulk upload task started successfully")
        else:
            messages.error(request, f"Failed to start task: {response.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Start bulk upload error: {e}")
        messages.error(request, f"Failed to start task: {str(e)}")
    
    return redirect('bulk_upload_detail', task_id=task_id)


# API Views for AJAX
@require_GET
def task_status_api(request, task_id: int):
    """Get task status via API (for AJAX updates)."""
    try:
        response = worker_api.get_task_status(task_id)
        return JsonResponse(response)
        
    except Exception as e:
        logger.error(f"Task status API error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Health and monitoring
def health_check(request):
    """Health check endpoint."""
    try:
        # Check API connectivity
        management_health = management_api.client.get('/health/')
        worker_health = worker_api.get_health()
        
        healthy = (
            management_health.get('success', False) and
            worker_health.get('success', False)
        )
        
        return JsonResponse({
            'healthy': healthy,
            'services': {
                'management': management_health.get('success', False),
                'worker': worker_health.get('success', False)
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'healthy': False,
            'error': str(e)
        }, status=500)