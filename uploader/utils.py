import requests
import logging
from requests.exceptions import RequestException, Timeout, ProxyError
import socket
import socks

logger = logging.getLogger(__name__)

def normalize_proxy_host(host: str) -> str:
    try:
        s = (host or '').strip()
        if '/' in s:
            s = s.split('/', 1)[0]
        return s
    except Exception:
        return host

def validate_proxy(host, port, username=None, password=None, timeout=10, proxy_type='HTTP'):
    """
    Validate if a proxy is working by attempting to connect to external HTTPS services.

    A proxy is considered VALID only if at least one HTTPS endpoint is reachable via the proxy.
    HTTP-only success will NOT mark the proxy as valid.
    
    Args:
        host (str): Proxy host
        port (str/int): Proxy port
        username (str, optional): Proxy username
        password (str, optional): Proxy password
        timeout (int, optional): Connection timeout in seconds
        proxy_type (str, optional): Proxy type ('HTTP', 'HTTPS', 'SOCKS5')
        
    Returns:
        tuple: (bool, str, dict) - (is_valid, message, geo_info)
    """
    # Normalize host and convert port
    host = normalize_proxy_host(host)
    # Convert port to int if it's a string
    try:
        port = int(port)
    except (ValueError, TypeError):
        return False, "Invalid port number", {"country": None, "city": None}
    
    # HTTPS targets must pass for the proxy to be considered valid
    # Use multiple lightweight HTTPS endpoints (some providers may block specific ones)
    https_test_endpoints = [
        ("https://httpbin.org/ip", "json_ip"),              # returns { origin }
        ("https://api.ipify.org?format=json", "json_ip"),   # returns { ip }
        ("https://ifconfig.me/ip", "plain_ip"),             # returns plain text IP
    ]
    # Optional HTTP endpoint used only for IP info retrieval; not used to decide validity
    http_info_url = "http://httpbin.org/ip"
    
    geo_info = {"country": None, "city": None}
    proxy_type = proxy_type.upper()
    
    # For SOCKS5 proxies, use a different validation method
    if proxy_type == 'SOCKS5':
        return _validate_socks5_proxy(host, port, username, password, timeout)
    
    # For HTTP/HTTPS proxies
    proxy_url = f"http://{host}:{port}"
    if username and password:
        proxy_url = f"http://{username}:{password}@{host}:{port}"
    
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    https_ok = False
    
    # First, require HTTPS connectivity
    for test_url, mode in https_test_endpoints:
        try:
            logger.debug(f"Testing proxy {host}:{port} with URL: {test_url}")
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            if response.status_code == 200:
                https_ok = True
                # Try to parse external IP from the response
                proxy_ip = None
                if mode == "json_ip":
                    try:
                        ip_data = response.json()
                        # httpbin: origin; ipify: ip
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
                    # Prefer RIPE Database GEO; fallback to ip-api
                    try:
                        ripe_geo = get_geo_via_ripe(proxy_ip)
                    except Exception:
                        ripe_geo = {}
                    if ripe_geo:
                        for k, v in ripe_geo.items():
                            if v is not None:
                                geo_info[k] = v
                    else:
                        try:
                            ext_geo = get_ip_location(proxy_ip)
                            if ext_geo:
                                for k, v in ext_geo.items():
                                    if v is not None:
                                        geo_info[k] = v
                        except Exception:
                            pass
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
    
    # Optionally attempt to enrich geo info (best-effort; does not affect validity)
    try:
        # If we already have external_ip, location likely filled; otherwise fallback to host-derived GEO
        ip_info = get_proxy_location(host, username)
        if ip_info:
            # Merge location info with existing geo_info (preserve external_ip)
            geo_info.update(ip_info)
            return True, f"Proxy is working correctly ({geo_info.get('country', 'Unknown')})", geo_info
    except Exception as e:
        logger.error(f"Error getting proxy location: {str(e)}")
    
    return True, "Proxy is working correctly", geo_info


def _validate_socks5_proxy(host, port, username=None, password=None, timeout=10):
    """
    Validate SOCKS5 proxy by attempting to connect through it
    """
    geo_info = {"country": None, "city": None}
    
    try:
        # Create a socket and configure it to use SOCKS5
        sock = socks.socksocket()
        sock.set_proxy(socks.SOCKS5, host, port, username=username, password=password)
        sock.settimeout(timeout)
        
        # Try to connect to a test server
        test_host = "httpbin.org"
        test_port = 80
        
        sock.connect((test_host, test_port))
        sock.close()
        
        # If successful, try to get country information
        try:
            ip_info = get_proxy_location(host, username)
            if ip_info:
                geo_info = ip_info
                return True, f"SOCKS5 proxy is working correctly ({geo_info.get('country', 'Unknown')})", geo_info
        except Exception as e:
            logger.error(f"Error getting SOCKS5 proxy location: {str(e)}")
            
        return True, "SOCKS5 proxy is working correctly", geo_info
        
    except socks.ProxyConnectionError:
        return False, "Failed to connect to SOCKS5 proxy server", geo_info
    except socks.SOCKS5AuthError:
        return False, "SOCKS5 authentication failed", geo_info
    except socks.SOCKS5Error as e:
        return False, f"SOCKS5 error: {str(e)}", geo_info
    except socket.timeout:
        return False, "SOCKS5 proxy connection timed out", geo_info
    except Exception as e:
        logger.error(f"Unexpected error validating SOCKS5 proxy {host}:{port}: {str(e)}")
        return False, f"Unexpected SOCKS5 error: {str(e)}", geo_info


def get_proxy_location(host, username=None):
    """
    Get the location information of a proxy using ip-api.com
    
    Args:
        host (str): Proxy host/IP address
        username (str, optional): Username for extracting country from format like 
                                 'country-XY-state-123456' if present
    
    Returns:
        dict: Location information including country and city
    """
    geo_info = {"country": None, "city": None}
    host = normalize_proxy_host(host)
    
    # Try to extract country from username if it follows a pattern
    if username and '-country-' in username:
        try:
            country_part = username.split('-country-')[1]
            if '-' in country_part:
                country_code = country_part.split('-')[0]
                if len(country_code) == 2:  # Standard country code length
                    geo_info["country"] = country_code.upper()
        except Exception:
            pass
    
    # Also try other common patterns
    if username and not geo_info["country"]:
        # Pattern: US-state-123456 or country_US_state_123456
        for separator in ['-', '_']:
            parts = username.split(separator)
            for part in parts:
                if len(part) == 2 and part.isalpha():
                    geo_info["country"] = part.upper()
                    break
            if geo_info["country"]:
                break
    
    # Only use API if we couldn't extract from username
    if not geo_info["country"]:
        try:
            response = requests.get(f"http://ip-api.com/json/{host}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    geo_info["country"] = data.get("countryCode")
                    geo_info["city"] = data.get("city")
        except Exception as e:
            logger.error(f"Error getting proxy location from API: {str(e)}")
    
    return geo_info 


def get_ip_location(ip: str) -> dict:
    """
    Get GEO by explicit IP address (external IP as seen by remote service).
    Returns dict with keys: country (countryCode), city.
    """
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                return {
                    "country": data.get("countryCode"),
                    "city": data.get("city"),
                }
    except Exception as e:
        logger.error(f"Error getting location for IP {ip}: {str(e)}")
    return {}


def get_geo_via_ripe(ip: str) -> dict:
    """
    Query RIPE Database for IP assignment and parse country code.
    Uses the public REST endpoint. Best-effort.
    """
    try:
        url = f"https://rest.db.ripe.net/search.json?query-string={ip}&type-filter=inetnum&flags=no-filtering"
        resp = requests.get(url, timeout=6)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        objs = (data.get('objects') or {}).get('object') or []
        for obj in objs:
            attrs = obj.get('attributes', {}).get('attribute', [])
            country = None
            for a in attrs:
                if a.get('name', '').lower() == 'country':
                    cval = (a.get('value') or '').strip().upper()
                    if len(cval) == 2:
                        country = cval
                        break
            if country:
                return {"country": country}
    except Exception as e:
        logger.error(f"Error querying RIPE for IP {ip}: {str(e)}")
    return {}