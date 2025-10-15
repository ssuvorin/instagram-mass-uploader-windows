"""
Context Processors for TikTok Uploader
=====================================

Глобальные контекстные процессоры для всех шаблонов.
"""

from tiktok_uploader.models import TikTokServer


def servers_context(request):
    """
    Добавляет список серверов в контекст всех шаблонов.
    """
    if request.user.is_authenticated:
        servers = TikTokServer.objects.filter(is_active=True).order_by('priority', 'name')
        selected_server_id = request.session.get('selected_server_id')
        
        return {
            'available_servers': servers,
            'selected_server_id': selected_server_id,
        }
    
    return {
        'available_servers': [],
        'selected_server_id': None,
    }

