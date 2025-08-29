"""
Comprehensive monitoring views for production deployment.

Provides web interface for monitoring worker health, metrics, errors,
and system status with server IP tracking for troubleshooting.
"""

import json
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import WorkerNode, TaskLock

logger = logging.getLogger(__name__)


def _worker_headers():
    """Get authentication headers for worker communication."""
    headers = {"Accept": "application/json"}
    token = getattr(settings, 'WORKER_API_TOKEN', None)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _extract_server_info(base_url: str) -> Dict[str, str]:
    """Extract server information from worker URL."""
    try:
        parsed = urlparse(base_url)
        return {
            'host': parsed.hostname or 'unknown',
            'port': str(parsed.port) if parsed.port else '8088',
            'protocol': parsed.scheme or 'http'
        }
    except Exception:
        return {'host': 'unknown', 'port': 'unknown', 'protocol': 'http'}


async def _fetch_worker_metrics(worker_url: str, timeout: int = 10) -> Dict[str, Any]:
    """Fetch comprehensive metrics from a worker."""
    headers = _worker_headers()
    
    try:
        # Get detailed health check
        health_resp = requests.get(
            f"{worker_url}/api/v1/health",
            headers=headers,
            timeout=timeout
        )
        health_data = health_resp.json() if health_resp.status_code == 200 else {}
        
        # Get metrics
        metrics_resp = requests.get(
            f"{worker_url}/api/v1/metrics",
            headers=headers,
            timeout=timeout
        )
        metrics_data = metrics_resp.json() if metrics_resp.status_code == 200 else {}
        
        # Get status
        status_resp = requests.get(
            f"{worker_url}/api/v1/status",
            headers=headers,
            timeout=timeout
        )
        status_data = status_resp.json() if status_resp.status_code == 200 else {}
        
        # Get active locks
        locks_resp = requests.get(
            f"{worker_url}/api/v1/locks",
            headers=headers,
            timeout=timeout
        )
        locks_data = locks_resp.json() if locks_resp.status_code == 200 else {}
        
        # Get active jobs
        jobs_resp = requests.get(
            f"{worker_url}/api/v1/jobs",
            headers=headers,
            timeout=timeout
        )
        jobs_data = jobs_resp.json() if jobs_resp.status_code == 200 else []
        
        server_info = _extract_server_info(worker_url)
        
        return {
            'server_info': server_info,
            'health': health_data,
            'metrics': metrics_data,
            'status': status_data,
            'locks': locks_data,
            'jobs': jobs_data,
            'last_updated': datetime.now().isoformat(),
            'worker_url': worker_url,
            'accessible': True,
            'error': None
        }
        
    except requests.exceptions.Timeout:
        return {
            'server_info': _extract_server_info(worker_url),
            'worker_url': worker_url,
            'accessible': False,
            'error': 'Connection timeout',
            'error_type': 'timeout'
        }
    except requests.exceptions.ConnectionError:
        return {
            'server_info': _extract_server_info(worker_url),
            'worker_url': worker_url,
            'accessible': False,
            'error': 'Connection refused - worker may be down',
            'error_type': 'connection'
        }
    except Exception as e:
        return {
            'server_info': _extract_server_info(worker_url),
            'worker_url': worker_url,
            'accessible': False,
            'error': str(e),
            'error_type': 'unknown'
        }


def monitoring_dashboard(request):
    """Main monitoring dashboard view."""
    try:
        # Get all registered workers
        workers = WorkerNode.objects.all().order_by('-is_active', '-capacity', 'name')
        
        worker_data = []
        total_metrics = {
            'total_workers': 0,
            'healthy_workers': 0,
            'total_tasks': 0,
            'active_tasks': 0,
            'total_memory_mb': 0,
            'total_cpu_percent': 0,
            'errors_last_hour': 0
        }
        
        for worker in workers:
            try:
                metrics = _fetch_worker_metrics(worker.base_url, timeout=10)
                
                # Extract key metrics for summary
                if metrics.get('accessible'):
                    total_metrics['healthy_workers'] += 1
                    
                    status_data = metrics.get('status', {})
                    resource_usage = status_data.get('resource_usage', {})
                    
                    total_metrics['active_tasks'] += status_data.get('active_tasks', 0)
                    total_metrics['total_memory_mb'] += resource_usage.get('memory_mb', 0)
                    total_metrics['total_cpu_percent'] += resource_usage.get('cpu_percent', 0)
                    
                    # Count recent errors from metrics
                    worker_metrics = metrics.get('metrics', {})
                    counters = worker_metrics.get('counters', {})
                    for key, value in counters.items():
                        if 'error' in key.lower() or 'failed' in key.lower():
                            total_metrics['errors_last_hour'] += value
                
                total_metrics['total_workers'] += 1
                
                # Add worker info to metrics
                metrics['worker_name'] = worker.name
                metrics['worker_capacity'] = worker.capacity
                metrics['last_heartbeat'] = worker.last_heartbeat
                metrics['db_last_error'] = worker.last_error
                
                worker_data.append(metrics)
                
            except Exception as e:
                logger.error(f"Error fetching metrics for worker {worker.name}: {e}")
                worker_data.append({
                    'worker_name': worker.name,
                    'worker_url': worker.base_url,
                    'server_info': _extract_server_info(worker.base_url),
                    'accessible': False,
                    'error': f'Metrics fetch error: {str(e)}',
                    'error_type': 'fetch_error'
                })
        
        # Calculate averages
        if total_metrics['healthy_workers'] > 0:
            total_metrics['avg_cpu_percent'] = total_metrics['total_cpu_percent'] / total_metrics['healthy_workers']
            total_metrics['avg_memory_mb'] = total_metrics['total_memory_mb'] / total_metrics['healthy_workers']
        else:
            total_metrics['avg_cpu_percent'] = 0
            total_metrics['avg_memory_mb'] = 0
        
        # Get task locks summary
        task_locks = TaskLock.objects.all()
        lock_summary = {}
        for lock in task_locks:
            lock_type = lock.kind
            if lock_type not in lock_summary:
                lock_summary[lock_type] = {
                    'total': 0,
                    'expired': 0,
                    'by_worker': {}
                }
            
            lock_summary[lock_type]['total'] += 1
            
            # Check if expired (if TTL fields available)
            if hasattr(lock, 'expires_at') and lock.expires_at <= timezone.now():
                lock_summary[lock_type]['expired'] += 1
            
            # Count by worker
            worker_id = getattr(lock, 'worker_id', 'unknown')
            if worker_id not in lock_summary[lock_type]['by_worker']:
                lock_summary[lock_type]['by_worker'][worker_id] = 0
            lock_summary[lock_type]['by_worker'][worker_id] += 1
        
        context = {
            'workers': worker_data,
            'total_metrics': total_metrics,
            'lock_summary': lock_summary,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'refresh_interval': getattr(settings, 'MONITORING_REFRESH_INTERVAL', 30)
        }
        
        return render(request, 'dashboard/monitoring_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in monitoring dashboard: {e}")
        logger.error(traceback.format_exc())
        
        return render(request, 'dashboard/monitoring_dashboard.html', {
            'error': f'Dashboard error: {str(e)}',
            'workers': [],
            'total_metrics': {},
            'lock_summary': {}
        })


@require_GET
def worker_details(request, worker_id: int):
    """Detailed view of a specific worker."""
    try:
        worker = WorkerNode.objects.get(id=worker_id)
        
        # Fetch comprehensive worker data
        worker_metrics = _fetch_worker_metrics(worker.base_url, timeout=15)
        
        # Get historical data if available
        # TODO: Implement historical metrics collection
        
        context = {
            'worker': worker,
            'metrics': worker_metrics,
            'server_info': worker_metrics.get('server_info', {}),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return render(request, 'dashboard/worker_details.html', context)
        
    except WorkerNode.DoesNotExist:
        return render(request, 'dashboard/worker_details.html', {
            'error': f'Worker with ID {worker_id} not found'
        })
    except Exception as e:
        logger.error(f"Error fetching worker details: {e}")
        return render(request, 'dashboard/worker_details.html', {
            'error': f'Error fetching worker details: {str(e)}'
        })


@require_GET 
def system_metrics_api(request):
    """API endpoint for system metrics (for AJAX updates)."""
    try:
        workers = WorkerNode.objects.filter(is_active=True)
        
        system_data = {
            'timestamp': datetime.now().isoformat(),
            'workers': [],
            'summary': {
                'total_workers': 0,
                'healthy_workers': 0,
                'total_active_tasks': 0,
                'total_memory_usage': 0,
                'total_cpu_usage': 0,
                'errors_count': 0
            }
        }
        
        for worker in workers:
            try:
                # Quick health check
                health_url = f"{worker.base_url}/api/v1/health/simple"
                response = requests.get(health_url, headers=_worker_headers(), timeout=5)
                
                worker_info = {
                    'id': worker.id,
                    'name': worker.name,
                    'url': worker.base_url,
                    'server_info': _extract_server_info(worker.base_url),
                    'healthy': response.status_code == 200,
                    'last_heartbeat': worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
                    'capacity': worker.capacity
                }
                
                if worker_info['healthy']:
                    system_data['summary']['healthy_workers'] += 1
                    
                    # Get detailed metrics for healthy workers
                    try:
                        status_resp = requests.get(
                            f"{worker.base_url}/api/v1/status",
                            headers=_worker_headers(),
                            timeout=3
                        )
                        if status_resp.status_code == 200:
                            status_data = status_resp.json()
                            resource_usage = status_data.get('resource_usage', {})
                            
                            worker_info.update({
                                'active_tasks': status_data.get('active_tasks', 0),
                                'memory_mb': resource_usage.get('memory_mb', 0),
                                'cpu_percent': resource_usage.get('cpu_percent', 0)
                            })
                            
                            system_data['summary']['total_active_tasks'] += worker_info['active_tasks']
                            system_data['summary']['total_memory_usage'] += worker_info['memory_mb']
                            system_data['summary']['total_cpu_usage'] += worker_info['cpu_percent']
                    except Exception:
                        pass
                
                system_data['workers'].append(worker_info)
                system_data['summary']['total_workers'] += 1
                
            except Exception as e:
                logger.warning(f"Error checking worker {worker.name}: {e}")
                system_data['workers'].append({
                    'id': worker.id,
                    'name': worker.name,
                    'url': worker.base_url,
                    'server_info': _extract_server_info(worker.base_url),
                    'healthy': False,
                    'error': str(e)
                })
                system_data['summary']['total_workers'] += 1
        
        return JsonResponse(system_data)
        
    except Exception as e:
        logger.error(f"Error in system metrics API: {e}")
        return JsonResponse({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=500)


@require_POST
@csrf_exempt
def restart_worker(request, worker_id: int):
    """Send restart signal to a worker (if supported)."""
    try:
        worker = WorkerNode.objects.get(id=worker_id)
        
        # Try to send graceful restart signal
        restart_url = f"{worker.base_url}/api/v1/admin/restart"
        response = requests.post(restart_url, headers=_worker_headers(), timeout=10)
        
        if response.status_code == 200:
            return JsonResponse({
                'success': True,
                'message': f'Restart signal sent to {worker.name}',
                'server_ip': _extract_server_info(worker.base_url)['host']
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'Failed to restart worker: HTTP {response.status_code}',
                'server_ip': _extract_server_info(worker.base_url)['host']
            })
            
    except WorkerNode.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Worker not found'})
    except requests.exceptions.ConnectionError:
        return JsonResponse({
            'success': False,
            'message': 'Cannot connect to worker - manual restart required',
            'server_ip': _extract_server_info(worker.base_url)['host']
        })
    except Exception as e:
        logger.error(f"Error restarting worker: {e}")
        return JsonResponse({'success': False, 'message': str(e)})


@require_GET
def error_logs_view(request):
    """View for displaying system error logs with server information."""
    try:
        workers = WorkerNode.objects.all()
        error_logs = []
        
        for worker in workers:
            try:
                # Try to get error logs from worker
                logs_url = f"{worker.base_url}/api/v1/admin/logs"
                response = requests.get(logs_url, headers=_worker_headers(), timeout=10)
                
                if response.status_code == 200:
                    worker_logs = response.json().get('error_logs', [])
                    
                    for log_entry in worker_logs:
                        log_entry['worker_name'] = worker.name
                        log_entry['server_ip'] = _extract_server_info(worker.base_url)['host']
                        log_entry['worker_url'] = worker.base_url
                    
                    error_logs.extend(worker_logs)
            except Exception as e:
                # Add connection error as log entry
                error_logs.append({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'ERROR',
                    'message': f'Cannot fetch logs: {str(e)}',
                    'worker_name': worker.name,
                    'server_ip': _extract_server_info(worker.base_url)['host'],
                    'worker_url': worker.base_url,
                    'error_type': 'connection_error'
                })
        
        # Sort by timestamp (newest first)
        error_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        context = {
            'error_logs': error_logs[:100],  # Limit to last 100 errors
            'total_errors': len(error_logs),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return render(request, 'dashboard/error_logs.html', context)
        
    except Exception as e:
        logger.error(f"Error fetching error logs: {e}")
        return render(request, 'dashboard/error_logs.html', {
            'error': f'Error fetching logs: {str(e)}',
            'error_logs': []
        })


@require_GET
def performance_metrics(request):
    """Performance metrics view with charts and graphs."""
    try:
        # This would ideally connect to a metrics database
        # For now, we'll get current metrics from all workers
        
        workers = WorkerNode.objects.filter(is_active=True)
        performance_data = {
            'cpu_usage': [],
            'memory_usage': [],
            'task_throughput': [],
            'response_times': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for worker in workers:
            try:
                metrics_resp = requests.get(
                    f"{worker.base_url}/api/v1/metrics",
                    headers=_worker_headers(),
                    timeout=5
                )
                
                if metrics_resp.status_code == 200:
                    metrics = metrics_resp.json()
                    
                    resource_usage = metrics.get('resource_usage', {})
                    server_ip = _extract_server_info(worker.base_url)['host']
                    
                    performance_data['cpu_usage'].append({
                        'worker': worker.name,
                        'server_ip': server_ip,
                        'value': resource_usage.get('cpu_percent', 0)
                    })
                    
                    performance_data['memory_usage'].append({
                        'worker': worker.name,
                        'server_ip': server_ip,
                        'value': resource_usage.get('memory_mb', 0)
                    })
                    
                    # Extract task completion rates from counters
                    counters = metrics.get('counters', {})
                    completed_tasks = sum(v for k, v in counters.items() if 'completed' in k.lower())
                    
                    performance_data['task_throughput'].append({
                        'worker': worker.name,
                        'server_ip': server_ip,
                        'value': completed_tasks
                    })
                    
            except Exception as e:
                logger.warning(f"Error fetching performance data from {worker.name}: {e}")
        
        context = {
            'performance_data': performance_data,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return render(request, 'dashboard/performance_metrics.html', context)
        
    except Exception as e:
        logger.error(f"Error in performance metrics: {e}")
        return render(request, 'dashboard/performance_metrics.html', {
            'error': str(e),
            'performance_data': {}
        })


# Enhanced health poll with detailed error tracking
def enhanced_health_poll(request):
    """Enhanced health polling with detailed error information."""
    nodes = WorkerNode.objects.all()
    
    for node in nodes:
        try:
            # Get comprehensive health data
            health_data = _fetch_worker_metrics(node.base_url, timeout=10)
            
            if health_data.get('accessible'):
                # Worker is accessible, check detailed health
                health_info = health_data.get('health', {})
                overall_healthy = health_info.get('healthy', False)
                
                if overall_healthy:
                    node.mark_heartbeat(ok=True, error=None)
                else:
                    # Extract specific health issues
                    checks = health_info.get('checks', {})
                    failed_checks = [k for k, v in checks.items() if not v.get('ok', True)]
                    error_msg = f"Health checks failed: {', '.join(failed_checks)}"
                    node.mark_heartbeat(ok=False, error=error_msg)
            else:
                # Worker not accessible
                error_type = health_data.get('error_type', 'unknown')
                error_msg = health_data.get('error', 'Unknown error')
                server_ip = health_data.get('server_info', {}).get('host', 'unknown')
                
                detailed_error = f"[{server_ip}] {error_type}: {error_msg}"
                node.mark_heartbeat(ok=False, error=detailed_error)
                
        except Exception as e:
            server_ip = _extract_server_info(node.base_url)['host']
            error_msg = f"[{server_ip}] Health check exception: {str(e)}"
            node.mark_heartbeat(ok=False, error=error_msg)
    
    return redirect('monitoring_dashboard')