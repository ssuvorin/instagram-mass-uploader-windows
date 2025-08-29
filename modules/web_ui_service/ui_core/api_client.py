"""
API Client for distributed architecture communication.

This module provides a unified interface for communicating with backend services
via HTTP APIs instead of direct database access.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class APIClient:
    """Unified API client for backend services communication."""
    
    def __init__(self, service_name: str):
        """Initialize API client for specific service."""
        self.service_name = service_name
        self.config = settings.API_SERVICES.get(service_name, {})
        self.base_url = self.config.get('url', '')
        self.token = self.config.get('token', '')
        
        if not self.base_url:
            logger.warning(f"No URL configured for service: {service_name}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
            
        return headers
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to service API."""
        url = urljoin(self.base_url, endpoint.lstrip('/'))
        headers = self._get_headers()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=30,
                **kwargs
            )
            
            if response.status_code >= 400:
                logger.error(f"API error {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text[:200]}",
                    'status_code': response.status_code
                }
            
            return response.json() if response.content else {'success': True}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'connection_error': True
            }
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request."""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make POST request."""
        json_data = json.dumps(data) if data else None
        return self._make_request('POST', endpoint, data=json_data)
    
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make PUT request.""" 
        json_data = json.dumps(data) if data else None
        return self._make_request('PUT', endpoint, data=json_data)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request."""
        return self._make_request('DELETE', endpoint)


class ManagementAPI:
    """API client for Management Service (CRUD operations)."""
    
    def __init__(self):
        self.client = APIClient('management')
    
    # Account management
    def get_accounts(self, **filters) -> Dict[str, Any]:
        """Get Instagram accounts list."""
        return self.client.get('/api/v1/accounts/', params=filters)
    
    def get_account(self, account_id: int) -> Dict[str, Any]:
        """Get account details.""" 
        return self.client.get(f'/api/v1/accounts/{account_id}/')
    
    def create_account(self, account_data: Dict) -> Dict[str, Any]:
        """Create new account."""
        return self.client.post('/api/v1/accounts/', data=account_data)
    
    def update_account(self, account_id: int, account_data: Dict) -> Dict[str, Any]:
        """Update account."""
        return self.client.put(f'/api/v1/accounts/{account_id}/', data=account_data)
    
    def delete_account(self, account_id: int) -> Dict[str, Any]:
        """Delete account."""
        return self.client.delete(f'/api/v1/accounts/{account_id}/')
    
    # Task management
    def get_bulk_tasks(self, **filters) -> Dict[str, Any]:
        """Get bulk upload tasks."""
        return self.client.get('/api/v1/bulk-tasks/', params=filters)
    
    def get_bulk_task(self, task_id: int) -> Dict[str, Any]:
        """Get bulk task details."""
        return self.client.get(f'/api/v1/bulk-tasks/{task_id}/')
    
    def create_bulk_task(self, task_data: Dict) -> Dict[str, Any]:
        """Create bulk upload task."""
        return self.client.post('/api/v1/bulk-tasks/', data=task_data)
    
    # Proxy management
    def get_proxies(self, **filters) -> Dict[str, Any]:
        """Get proxy list."""
        return self.client.get('/api/v1/proxies/', params=filters)
    
    def create_proxy(self, proxy_data: Dict) -> Dict[str, Any]:
        """Create new proxy."""
        return self.client.post('/api/v1/proxies/', data=proxy_data)


class WorkerAPI:
    """API client for Worker Service (task execution)."""
    
    def __init__(self):
        self.client = APIClient('worker')
    
    def start_bulk_task(self, task_id: int) -> Dict[str, Any]:
        """Start bulk upload task."""
        return self.client.post(f'/api/v1/bulk-tasks/{task_id}/start/')
    
    def get_task_status(self, task_id: int, kind: str = 'bulk') -> Dict[str, Any]:
        """Get task execution status."""
        return self.client.get(f'/api/v1/{kind}-tasks/{task_id}/status/')
    
    def get_health(self) -> Dict[str, Any]:
        """Get worker health status."""
        return self.client.get('/api/v1/health/')
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get worker metrics."""
        return self.client.get('/api/v1/metrics/')


class MonitoringAPI:
    """API client for Monitoring Service (real-time monitoring)."""
    
    def __init__(self):
        self.client = APIClient('monitoring')
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics."""
        return self.client.get('/api/v1/metrics/system/')
    
    def get_worker_metrics(self, worker_id: str) -> Dict[str, Any]:
        """Get specific worker metrics."""
        return self.client.get(f'/api/v1/metrics/workers/{worker_id}/')


# Global API instances
management_api = ManagementAPI()
worker_api = WorkerAPI()
monitoring_api = MonitoringAPI()