"""
Custom Template Tags for TikTok Uploader
==========================================

Дополнительные фильтры и теги для шаблонов Django.
"""

from django import template

register = template.Library()


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Получить значение из словаря по ключу.
    
    Использование в шаблоне:
        {{ my_dict|get_item:key_variable }}
    
    Args:
        dictionary: Словарь (dict)
        key: Ключ для поиска
    
    Returns:
        Значение по ключу или None если ключ не найден
    """
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)


@register.filter(name='percentage')
def percentage(value, total):
    """
    Вычислить процент.
    
    Использование:
        {{ completed|percentage:total }}
    
    Args:
        value: Числитель
        total: Знаменатель
    
    Returns:
        Процент (0-100) или 0 если total = 0
    """
    try:
        value = float(value)
        total = float(total)
        if total == 0:
            return 0
        return round((value / total) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter(name='duration')
def duration(seconds):
    """
    Преобразовать секунды в читаемый формат (X days, Y hours, Z minutes).
    
    Args:
        seconds: Количество секунд (int)
    
    Returns:
        Отформатированная строка
    """
    try:
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"
    except (ValueError, TypeError):
        return "Unknown"


@register.filter(name='status_badge_class')
def status_badge_class(status):
    """
    Получить CSS класс для badge в зависимости от статуса.
    
    Args:
        status: Статус задачи (str)
    
    Returns:
        CSS класс (str): 'bg-success', 'bg-danger', etc.
    """
    status_map = {
        'COMPLETED': 'bg-success',
        'RUNNING': 'bg-primary',
        'PENDING': 'bg-warning',
        'QUEUED': 'bg-info',
        'FAILED': 'bg-danger',
        'PAUSED': 'bg-secondary',
        'STOPPED': 'bg-secondary',
    }
    return status_map.get(str(status).upper(), 'bg-secondary')


@register.filter(name='status_icon')
def status_icon(status):
    """
    Получить Bootstrap Icon для статуса.
    
    Args:
        status: Статус задачи (str)
    
    Returns:
        CSS класс иконки (str)
    """
    status_map = {
        'COMPLETED': 'bi-check-circle-fill',
        'RUNNING': 'bi-play-circle-fill',
        'PENDING': 'bi-clock-history',
        'QUEUED': 'bi-hourglass-split',
        'FAILED': 'bi-x-circle-fill',
        'PAUSED': 'bi-pause-circle-fill',
        'STOPPED': 'bi-stop-circle-fill',
    }
    return status_map.get(str(status).upper(), 'bi-question-circle')

