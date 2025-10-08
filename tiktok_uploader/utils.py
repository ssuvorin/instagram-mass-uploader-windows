"""
Utility functions for TikTok Uploader
======================================

Вспомогательные функции для работы с прокси и другими утилитами.
"""

import requests
import logging
from requests.exceptions import RequestException, Timeout, ProxyError
import socket

logger = logging.getLogger(__name__)


def normalize_proxy_host(host: str) -> str:
    """Нормализация хоста прокси (убирает subnet mask)."""
    try:
        s = (host or '').strip()
        if '/' in s:
            s = s.split('/', 1)[0]
        return s
    except Exception:
        return host


def validate_proxy(host, port, username=None, password=None, timeout=10, proxy_type='HTTP'):
    """
    Валидация прокси путем подключения к внешним HTTPS сервисам.
    
    Прокси считается ВАЛИДНЫМ только если доступен хотя бы один HTTPS endpoint.
    
    Args:
        host (str): Хост прокси
        port (str/int): Порт прокси
        username (str, optional): Имя пользователя
        password (str, optional): Пароль
        timeout (int, optional): Таймаут подключения в секундах
        proxy_type (str, optional): Тип прокси ('HTTP', 'HTTPS', 'SOCKS5')
        
    Returns:
        tuple: (bool, str, dict) - (is_valid, message, geo_info)
            - is_valid: True если прокси работает
            - message: Сообщение о результате проверки
            - geo_info: Словарь с информацией о локации (country, city, external_ip)
    """
    # Нормализация хоста и конвертация порта
    host = normalize_proxy_host(host)
    try:
        port = int(port)
    except (ValueError, TypeError):
        return False, "Invalid port number", {"country": None, "city": None, "external_ip": None}
    
    # HTTPS endpoints для проверки
    https_test_endpoints = [
        ("https://httpbin.org/ip", "json_ip"),
        ("https://api.ipify.org?format=json", "json_ip"),
        ("https://ifconfig.me/ip", "plain_ip"),
    ]
    
    geo_info = {"country": None, "city": None, "external_ip": None}
    proxy_type = proxy_type.upper()
    
    # Для SOCKS5 используем другой метод
    if proxy_type == 'SOCKS5':
        return _validate_socks5_proxy(host, port, username, password, timeout)
    
    # Для HTTP/HTTPS прокси
    proxy_url = f"http://{host}:{port}"
    if username and password:
        proxy_url = f"http://{username}:{password}@{host}:{port}"
    
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    https_ok = False
    
    # Проверка HTTPS подключения
    for test_url, mode in https_test_endpoints:
        try:
            logger.debug(f"Testing proxy {host}:{port} with URL: {test_url}")
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            
            if response.status_code == 200:
                https_ok = True
                
                # Попытка получить external IP из ответа
                proxy_ip = None
                if mode == "json_ip":
                    try:
                        ip_data = response.json()
                        candidate = ip_data.get('origin') or ip_data.get('ip')
                        proxy_ip = (candidate or '').split(',')[0].strip() if candidate else None
                    except Exception:
                        pass
                elif mode == "plain_ip":
                    try:
                        proxy_ip = (response.text or '').strip().split()[0]
                    except Exception:
                        proxy_ip = None
                
                if proxy_ip:
                    logger.info(f"Proxy {host}:{port} working, external IP: {proxy_ip}")
                    geo_info['external_ip'] = proxy_ip
                    
                    # Попытка получить геолокацию
                    try:
                        location_info = _get_proxy_geolocation(proxy_ip)
                        if location_info:
                            geo_info.update(location_info)
                    except Exception as e:
                        logger.warning(f"Could not get geolocation for {proxy_ip}: {str(e)}")
                
                break
            else:
                logger.warning(f"Proxy {host}:{port} returned status {response.status_code} for {test_url}")
                
        except Timeout:
            logger.warning(f"Timeout testing proxy {host}:{port} with {test_url}")
        except ProxyError as e:
            logger.warning(f"Proxy error for {host}:{port} with {test_url}: {str(e)}")
        except RequestException as e:
            logger.warning(f"Request error for {host}:{port} with {test_url}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error testing proxy {host}:{port} with {test_url}: {str(e)}")
    
    if not https_ok:
        return False, "HTTPS check failed for all test URLs", geo_info
    
    country_info = f" ({geo_info.get('country', 'Unknown')})" if geo_info.get('country') else ""
    return True, f"Proxy is working correctly{country_info}", geo_info


def _validate_socks5_proxy(host, port, username=None, password=None, timeout=10):
    """
    Валидация SOCKS5 прокси через попытку подключения.
    
    Returns:
        tuple: (bool, str, dict)
    """
    geo_info = {"country": None, "city": None, "external_ip": None}
    
    try:
        # Простая проверка SOCKS5 через requests с socks5 scheme
        proxy_url = f"socks5://{host}:{port}"
        if username and password:
            proxy_url = f"socks5://{username}:{password}@{host}:{port}"
        
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        # Попытка подключения
        response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=timeout)
        
        if response.status_code == 200:
            try:
                ip_data = response.json()
                proxy_ip = ip_data.get('origin', '').split(',')[0].strip()
                if proxy_ip:
                    geo_info['external_ip'] = proxy_ip
                    
                    # Получение геолокации
                    try:
                        location_info = _get_proxy_geolocation(proxy_ip)
                        if location_info:
                            geo_info.update(location_info)
                    except Exception:
                        pass
            except Exception:
                pass
            
            return True, "SOCKS5 proxy is working correctly", geo_info
        else:
            return False, f"SOCKS5 proxy returned status {response.status_code}", geo_info
            
    except Exception as e:
        logger.error(f"SOCKS5 proxy validation failed: {str(e)}")
        return False, f"SOCKS5 proxy validation failed: {str(e)}", geo_info


def _get_proxy_geolocation(ip_address):
    """
    Получение геолокации IP адреса.
    
    Args:
        ip_address (str): IP адрес
        
    Returns:
        dict: Словарь с country и city или None
    """
    try:
        # Используем бесплатный сервис ip-api.com (без ограничений для некоммерческого использования)
        response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return {
                    'country': data.get('country'),
                    'city': data.get('city'),
                }
    except Exception as e:
        logger.warning(f"Could not get geolocation for IP {ip_address}: {str(e)}")
    
    return None


def parse_proxy_string(proxy_string, default_type='HTTP'):
    """
    Парсинг строки прокси в различных форматах.
    
    Поддерживаемые форматы:
        - host:port
        - host:port:username:password
        - protocol://host:port
        - protocol://username:password@host:port
    
    Args:
        proxy_string (str): Строка с прокси
        default_type (str): Тип прокси по умолчанию
        
    Returns:
        dict: Словарь с данными прокси или None если не удалось распарсить
    """
    import re
    
    proxy_string = proxy_string.strip()
    
    # Формат: protocol://username:password@host:port
    url_pattern = r'^(https?|socks5)://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$'
    match = re.match(url_pattern, proxy_string, re.IGNORECASE)
    if match:
        protocol, username, password, host, port = match.groups()
        return {
            'host': host,
            'port': int(port),
            'username': username,
            'password': password,
            'proxy_type': protocol.upper()
        }
    
    # Формат: host:port:username:password
    parts = proxy_string.split(':')
    if len(parts) == 4:
        host, port, username, password = parts
        try:
            return {
                'host': host,
                'port': int(port),
                'username': username,
                'password': password,
                'proxy_type': default_type
            }
        except ValueError:
            pass
    
    # Формат: host:port
    if len(parts) == 2:
        host, port = parts
        try:
            return {
                'host': host,
                'port': int(port),
                'username': None,
                'password': None,
                'proxy_type': default_type
            }
        except ValueError:
            pass
    
    return None



