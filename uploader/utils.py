import requests
import logging
from requests.exceptions import RequestException, Timeout, ProxyError
import socket
import socks

logger = logging.getLogger(__name__)

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
    # Convert port to int if it's a string
    try:
        port = int(port)
    except (ValueError, TypeError):
        return False, "Invalid port number", {"country": None, "city": None}
    
    # HTTPS targets must pass for the proxy to be considered valid
    https_test_urls = [
        "https://httpbin.org/ip",
        "https://www.google.com",
        "https://www.instagram.com"
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
    for test_url in https_test_urls:
        try:
            logger.debug(f"Testing proxy {host}:{port} with URL: {test_url}")
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            if response.status_code == 200:
                https_ok = True
                # If successful against httpbin HTTPS endpoint, try to log external IP
                if "httpbin.org/ip" in test_url:
                    try:
                        ip_data = response.json()
                        proxy_ip = ip_data.get('origin', '').split(',')[0].strip()
                        if proxy_ip and proxy_ip != host:
                            logger.info(f"Proxy {host}:{port} working, external IP: {proxy_ip}")
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
        ip_info = get_proxy_location(host, username)
        if ip_info:
            geo_info = ip_info
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