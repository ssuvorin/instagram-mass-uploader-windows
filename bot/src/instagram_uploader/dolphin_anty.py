#!/usr/bin/env python
"""
Dolphin{anty} Remote API Client
Provides functionality to interact with Dolphin{anty} Remote API
"""

import os
import json
import requests
import logging
import time
import random
import string
from typing import Dict, List, Optional, Union, Any, Tuple
from dotenv import load_dotenv
import asyncio
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
import threading
import queue
import subprocess
import sys
import tempfile
import platform
import uuid
import socket
import ipaddress
import http.client

# Импортируем Windows совместимость
try:
    # Пытаемся импортировать из uploader модуля
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'uploader'))
    from windows_compatibility import get_python_executable, run_subprocess_windows
except ImportError:
    # Fallback если модуль не найден
    def get_python_executable():
        if platform.system().lower() == "windows":
            return sys.executable
        else:
            return 'python'
    
    def run_subprocess_windows(cmd, timeout=300, cwd=None, capture_output=True, text=True):
        return subprocess.run(cmd, timeout=timeout, cwd=cwd, capture_output=capture_output, text=text)

# Load environment variables from .env file
load_dotenv()

def safe_log_message(message):
    """
    Remove or replace emoji characters that cause encoding issues on Windows
    """
    try:
        # Expanded emoji replacements for comprehensive coverage
        emoji_replacements = {
            '[SEARCH]': '[SEARCH]',
            '[OK]': '[SUCCESS]',
            '[FAIL]': '[ERROR]',
            '[START]': '[START]',
            '[RETRY]': '[PROCESS]',
            '🔗': '[LINK]',
            '🖼️': '[IMAGE]',
            '🛑': '[STOP]',
            '🖱️': '[MOUSE]',
            '[PAUSE]': '[PAUSE]',
            '[WARN]': '[WARNING]',
            '[TEXT]': '[TEXT]',
            '⬅️': '[BACK]',
            '🗂️': '[TABS]',
            '[CLIPBOARD]': '[LIST]',
            '[DELETE]': '[DELETE]',
            '[TOOL]': '[TOOL]',
            '📧': '[EMAIL]',
            '🌐': '[WEB]',
            '[LOCATION]': '[LOCATION]',
            '🎭': '[SIMULATION]',
            '📊': '[STATS]',
            '…': '...',
            # Additional emoji that might appear
            '📞': '[PHONE]',
            '🔒': '[SECURE]',
            '🔓': '[UNLOCK]',
            '⭐': '[STAR]',
            '💡': '[IDEA]',
            '🔥': '[FIRE]',
            '💻': '[COMPUTER]',
            '[PHONE]': '[MOBILE]',
            '🌟': '[STAR]',
            '[TARGET]': '[TARGET]',
            '[ALERT]': '[ALERT]',
            '[BELL]': '[NOTIFICATION]',
            '💬': '[CHAT]',
            '📂': '[FOLDER]',
            '[FOLDER]': '[DIRECTORY]',
            '🔑': '[KEY]',
            '🆔': '[ID]',
            '⌚': '[TIME]',
            '🕐': '[CLOCK]',
        }
        
        # Replace emoji characters with safe alternatives
        for emoji, replacement in emoji_replacements.items():
            message = message.replace(emoji, replacement)
        
        # Ensure the message only contains ASCII characters
        return message.encode('ascii', 'ignore').decode('ascii')
    except Exception:
        # If any error occurs, return a safe fallback
        return str(message).encode('ascii', 'ignore').decode('ascii')

class SafeLogger:
    """Wrapper around logger that automatically applies safe_log_message to all messages"""
    def __init__(self, logger):
        self._logger = logger
    
    def info(self, message, *args, **kwargs):
        safe_message = safe_log_message(str(message))
        self._logger.info(safe_message, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        safe_message = safe_log_message(str(message))
        self._logger.error(safe_message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        safe_message = safe_log_message(str(message))
        self._logger.warning(safe_message, *args, **kwargs)
    
    def debug(self, message, *args, **kwargs):
        safe_message = safe_log_message(str(message))
        self._logger.debug(safe_message, *args, **kwargs)

# Create safe logger wrapper using centralized logging
logger = SafeLogger(logging.getLogger('bot.instagram_uploader.dolphin_anty'))

class DolphinAntyAPIError(Exception):
    """Exception for Dolphin{anty} API errors"""
    def __init__(self, message, status_code=None, response=None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

class DolphinAnty:
    """
    Class for interacting with Dolphin{anty} Remote API
    """
    OS_PLATFORMS = ["windows"]
    SCREEN_RESOLUTIONS = [
        # Popular desktop resolutions
        "1920x1080", "2560x1440", "1366x768", "1440x900", "1536x864", "1680x1050",
        # Modern high-res displays
        "3440x1440", "2880x1800", "1920x1200", "2560x1600", "3840x2160",
        # Ultrawide and gaming
        "3440x1440", "2560x1080", "1920x1200", "2048x1152",
        # Laptop common resolutions
        "1600x900", "1280x800", "1280x720", "1024x768"
    ]
    BROWSER_VERSIONS = ["140"]
    
    # Stealth defaults for headers (Belarus locale with Russian interface)
    DEFAULT_ACCEPT_LANGUAGE = "ru-BY,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dolphin-anty-api.com",
        local_api_base: str = "http://localhost:3001/v1.0"
    ):
        self.api_key        = api_key
        self.base_url       = base_url.rstrip("/")
        self.local_api_base = local_api_base.rstrip("/")
        # Public Sync API base (used by "Export cookies for single profile")
        # Example: https://sync.dolphin-anty-api.com/?actionType=getCookies&browserProfileId=ID
        # Allow overriding via env to support mirrors / enterprise deployments
        self.sync_api_base  = os.environ.get("DOLPHIN_SYNC_API_BASE", "https://sync.dolphin-anty-api.com").rstrip("/")
        # Simple in-memory cache for geo-IP lookups per proxy host
        self._geoip_cache: Dict[str, Dict[str, Any]] = {}

    def _get_headers(self):
        """Get headers for API requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        data: Any = None,
        headers: Dict[str, Any] = None,
        json_data: Any = None,
        timeout: int = 60,
    ) -> Any:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            url = endpoint
        else:
            url = f"{self.base_url}{endpoint}"

        hdrs = {"Authorization": f"Bearer {self.api_key}"}
        if headers:
            hdrs.update(headers)

        # Retry logic with exponential backoff for rate limiting
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                # For PATCH requests with proxy data, use form data (urlencoded)
                if method.lower() == "patch" and data and isinstance(data, dict) and any(key.startswith("proxy[") for key in data.keys()):
                    hdrs["Content-Type"] = "application/x-www-form-urlencoded"
                    resp = requests.request(method, url, params=params, data=data, headers=hdrs, timeout=timeout)
                elif headers and headers.get("Content-Type") == "application/x-www-form-urlencoded":
                    resp = requests.request(method, url, params=params, data=data, headers=hdrs, timeout=timeout)
                else:
                    # Prefer explicit json_data if provided, fall back to data
                    if json_data is not None:
                        resp = requests.request(method, url, params=params, json=json_data, headers=hdrs, timeout=timeout)
                    else:
                        resp = requests.request(method, url, params=params, json=data, headers=hdrs, timeout=timeout)

                # Handle rate limiting (429) according to documentation
                if resp.status_code == 429:
                    if attempt < max_retries - 1:
                        # Get retry delay from headers if available
                        retry_after = resp.headers.get('Retry-After')
                        if retry_after:
                            delay = int(retry_after)
                        else:
                            delay = base_delay * (2 ** attempt)
                        
                        logger.warning(f"[RATE_LIMIT] Rate limited (429), retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"[RATE_LIMIT] Rate limited (429) after {max_retries} attempts")
                        resp.raise_for_status()
                
                resp.raise_for_status()
                return resp.json()
                
            except requests.exceptions.Timeout as e:
                logger.warning(f"[TIMEOUT] Request timeout on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"[RETRY] Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"[TIMEOUT] Request failed after {max_retries} attempts")
                    raise
            except requests.exceptions.RequestException as e:
                logger.warning(f"[REQUEST_ERROR] Request error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"[RETRY] Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"[REQUEST_ERROR] Request failed after {max_retries} attempts")
                    raise


    def authenticate(self):
        """Authenticate with Dolphin{anty} API and verify connection"""
        try:
            # Try to get a list of profiles to verify API connection
            profiles = self.get_profiles(limit=1)
            return True
        except DolphinAntyAPIError as e:
            logger.error(f"Authentication error with Dolphin API: {e.message}")
            return False

    def get_profiles(self, limit=50, page=1, query=None, tags=None, statuses=None, main_websites=None, users=None):
        params = {
            "limit": limit,
            "page": page
        }
        if query: params["query"] = query
        if tags: params["tags[]"] = tags
        if statuses: params["statuses[]"] = statuses
        if main_websites: params["mainWebsites[]"] = main_websites
        if users: params["users[]"] = users
        
        logger.info(f"Getting profile list with params: {params}")
        return self._make_request(
            method="get",
            endpoint="/browser_profiles",
            params=params
        )

    def generate_user_agent(self,
                            os_platform: str,
                            browser_version: str) -> Optional[str]:
        params = {
            "browser_type": "anty",
            "browser_version": browser_version,
            "platform": os_platform
        }
        
        try:
            resp = self._make_request("get", "/fingerprints/useragent", params=params)
            if resp and "data" in resp:
                ua = resp["data"]
                logger.info(f"[OK] Generated UA ({browser_version}): {ua[:40]}…")
                return ua
        except Exception as e:
            logger.warning(f"[WARN] UA generation failed for version {browser_version}: {e}")
        
        # Fallback: try with version 140 if the requested version fails
        if browser_version != "140":
            logger.info(f"[FALLBACK] Trying fallback UA generation with version 140")
            fallback_params = {
                "browser_type": "anty",
                "browser_version": "140",
                "platform": os_platform
            }
            try:
                resp = self._make_request("get", "/fingerprints/useragent", params=fallback_params)
                if resp and "data" in resp:
                    ua = resp["data"]
                    logger.info(f"[OK] Generated fallback UA (140): {ua[:40]}…")
                    return ua
            except Exception as fallback_error:
                logger.error(f"[FAIL] Fallback UA generation also failed: {fallback_error}")
        
        logger.error(f"[FAIL] UA generation failed completely for {browser_version}")
        return None

    def generate_webgl_info(self,
                             os_platform: str,
                             browser_version: str) -> Optional[Dict[str, Any]]:
        # Only Windows - use full range of resolutions
        screen = random.choice(self.SCREEN_RESOLUTIONS)
        params = {
            "browser_type":    "anty",
            "browser_version": browser_version,
            "platform":        os_platform,
            "type":            "fingerprint",
            "screen":          screen
        }
        resp = self._make_request("get", "/fingerprints/fingerprint", params=params)
        if not resp:
            return None

        # payload может быть либо в resp["data"], либо сразу в resp
        payload = resp.get("data", resp)

        # вытаскиваем webgl-блок
        webgl = payload.get("webgl", {})
        vendor   = webgl.get("unmaskedVendor")
        renderer = webgl.get("unmaskedRenderer")

        # вытаскиваем raw webgl2Maximum
        raw_wg2 = payload.get("webgl2Maximum") or payload.get("webgl2maximum")
        wg2max = None
        if isinstance(raw_wg2, str):
            try:
                wg2max = json.loads(raw_wg2)
            except json.JSONDecodeError:
                wg2max = None
        elif isinstance(raw_wg2, dict):
            wg2max = raw_wg2

        if vendor and renderer and isinstance(wg2max, dict):
            return {
                "vendor":        vendor,
                "renderer":      renderer,
                "webgl2Maximum": wg2max,
                "screen":        screen
            }

        # отладочный лог (без полного payload чтобы избежать спама)
        logger.error(f"[FAIL] WebGL parsing failed, payload size: {len(str(payload))} chars")
        return None

    def create_profile(
        self,
        name: str,
        proxy: Dict[str, Any],
        tags: List[str],
        locale: str = "ru_RU",
        strict_webrtc: bool = False
    ) -> Dict[str, Any]:
        """
        Create a fully randomized Dolphin Anty browser profile payload,
        with manual modes and configurable localization.
        """
        # 1) Proxy is required
        if not proxy:
            return {"success": False, "error": "Proxy configuration is required"}

        # 2) Choose OS and browser version - only Windows
        os_plat = self.OS_PLATFORMS[0]
        browser_ver = random.choice(self.BROWSER_VERSIONS)

        # 2b) Geo-IP for proxy to sync locale/TZ/geo and maybe WebRTC public IP
        geoip = self._geoip_lookup(proxy)
        public_ip = (geoip or {}).get("ip")

        # 3) Generate User-Agent
        ua = self.generate_user_agent(os_plat, browser_ver)
        if not ua:
            return {"success": False, "error": "UA generation failed"}

        # 4) Generate WebGL info + platformVersion
        webgl = self.generate_webgl_info(os_plat, browser_ver)
        if not webgl:
            return {"success": False, "error": "WebGL info generation failed"}

        # Fallback platform versions
        default_versions = {"windows": "10.0.0", "macos": "15.0.0", "linux": "0.0.0"}
        plat_ver = webgl.get("platformVersion") or default_versions[os_plat]

        # 5) Randomize modes per documentation
        webrtc_mode  = "altered"
        webgl_mode   = "real"
        webgl_info_mode = "manual"
        cpu_mode     = "manual"
        mem_mode     = "manual"
        cpu_value    = random.choice([4, 8, 16]) 
        mem_value    = random.choice([8, 16, 32])
        
        # 6) Randomize MAC address (manual) - using real OUI prefixes
        def random_mac():
            # Real OUI prefixes from major manufacturers
            oui_prefixes = [
                # Dell
                "00:14:22", "18:03:73", "B8:2A:72", "D4:AE:52", "F8:B1:56",
                # HP
                "00:1F:29", "70:5A:0F", "9C:8E:99", "A0:48:1C", "B4:99:BA",
                # Lenovo
                "00:21:CC", "54:EE:75", "8C:16:45", "E4:54:E8", "F0:DE:F1",
                # Apple
                "00:16:CB", "3C:07:54", "A4:5E:60", "BC:52:B7", "F0:18:98",
                # ASUS
                "00:1F:C6", "2C:56:DC", "50:46:5D", "AC:22:0B", "F8:32:E4",
                # MSI
                "00:21:85", "00:24:21", "70:85:C2", "E0:3F:49", "MSI123",
                # Acer
                "00:02:3F", "00:0E:9B", "B8:88:E3", "E0:94:67", "F0:76:1C",
                # Samsung
                "00:12:FB", "34:BE:00", "78:F8:82", "C8:BA:94", "E8:50:8B",
                # Intel (NUC/motherboards)
                "00:15:17", "94:C6:91", "A0:36:9F", "B4:96:91", "D8:CB:8A",
                # Realtek (network cards)
                "00:E0:4C", "52:54:00", "70:4D:7B", "E0:91:F5", "F8:59:71"
            ]
            
            # Choose random OUI prefix
            oui = random.choice(oui_prefixes)
            
            # Generate random last 3 bytes
            last_bytes = ":".join(f"{random.randint(0,255):02X}" for _ in range(3))
            
            return f"{oui}:{last_bytes}"
        
        mac_mode = "manual"
        mac_payload: Dict[str, Any] = {"mode": mac_mode}
        if mac_mode == "manual":
            mac_payload["value"] = random_mac()
        
        # 7) Randomize DeviceName (manual) - realistic device names
        dev_mode = "manual"
        dev_payload: Dict[str, Any] = {"mode": dev_mode}
        if dev_mode == "manual":
            def generate_realistic_device_name():
                # Common first names for personal devices
                first_names = [
                    "Alex", "John", "Mike", "Anna", "Kate", "Tom", "Lisa", "Mark", 
                    "Sarah", "David", "Emma", "Chris", "Maria", "Paul", "Julia",
                    "Steve", "Helen", "Nick", "Amy", "Dan", "Sophie", "Max", "Eva"
                ]
                
                # Windows device name patterns
                patterns = [
                    # Personal computers
                    lambda: f"{random.choice(first_names)}-PC",
                    lambda: f"{random.choice(first_names)}-DESKTOP",
                    lambda: f"{random.choice(first_names)}-LAPTOP",
                    # Windows default patterns
                    lambda: f"DESKTOP-{random.choice(string.ascii_uppercase)}{random.randint(10,99)}{random.choice(string.ascii_uppercase)}{random.randint(100,999)}",
                    lambda: f"LAPTOP-{random.choice(string.ascii_uppercase)}{random.randint(10,99)}{random.choice(string.ascii_uppercase)}{random.randint(100,999)}",
                    # Company/office patterns
                    lambda: f"WIN-{random.choice(string.ascii_uppercase)}{random.randint(10,99)}{random.choice(string.ascii_uppercase)}{random.randint(100,999)}",
                    lambda: f"PC-{random.choice(['USER', 'OFFICE', 'HOME'])}{random.randint(10,99)}",
                    # Brand-specific patterns
                    lambda: f"DELL-{random.choice(string.ascii_uppercase)}{random.randint(1000,9999)}",
                    lambda: f"HP-{random.choice(['PAVILION', 'ELITEBOOK', 'PROBOOK'])}{random.randint(100,999)}",
                    lambda: f"LENOVO-{random.choice(['THINKPAD', 'IDEAPAD'])}{random.randint(100,999)}",
                ]
                
                # Choose random pattern and execute it
                pattern_func = random.choice(patterns)
                return pattern_func()
            
            dev_payload["value"] = generate_realistic_device_name()

        # 8) Randomize Fonts
        fonts_mode = "auto"
        fonts_payload: Dict[str, Any] = {"mode": fonts_mode}

        # 9) Randomize Audio
        audio_mode = "real"
        audio_payload = {"mode": audio_mode}
        
        # 10) Timezone & Geolocation based on locale or GeoIP
        # Determine locale if not provided, from geoip country
        ip_cc = (geoip or {}).get("country_code")
        if not locale or locale.strip() == "":
            if ip_cc == "BY":
                locale = "ru_BY"
            elif ip_cc == "IN":
                locale = "en_IN"
            elif ip_cc == "US":
                locale = "en_US"
            else:
                locale = "ru_BY"
        normalized_locale = (locale or "ru_BY").strip()
        lang_value_dash = normalized_locale.replace("_", "-")

        tz_payload: Dict[str, Any]
        geo_payload: Dict[str, Any]

        if (geoip and geoip.get("timezone") and geoip.get("latitude") and geoip.get("longitude")):
            # Normalize timezone to string ID (ipwho.is returns an object)
            tz_val = geoip.get("timezone")
            if isinstance(tz_val, dict):
                tz_str = tz_val.get("id") or tz_val.get("name") or tz_val.get("timezone") or "Europe/Minsk"
            else:
                tz_str = str(tz_val)
            tz_payload = {"mode": "manual", "value": tz_str}
            try:
                lat = float(geoip.get("latitude"))
                lon = float(geoip.get("longitude"))
            except Exception:
                lat, lon = None, None
            if lat is not None and lon is not None:
                geo_payload = {"mode": "manual", "latitude": lat, "longitude": lon}
            else:
                geo_payload = {"mode": "off"}
        elif normalized_locale == "en_IN":
            # India
            tz_payload = {"mode": "manual", "value": "Asia/Kolkata"}
            # Randomly pick between Delhi and Mumbai for simple variety
            if random.choice([True, False]):
                geo_payload = {"mode": "manual", "latitude": 28.6139, "longitude": 77.2090}  # Delhi
            else:
                geo_payload = {"mode": "manual", "latitude": 19.0760, "longitude": 72.8777}  # Mumbai
        elif normalized_locale == "en_US":
            # USA
            us_timezones = [
                "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"
            ]
            tz_payload = {"mode": "manual", "value": random.choice(us_timezones)}
            # Random popular US city coords
            cities = [
                (40.7128, -74.0060),  # NYC
                (34.0522, -118.2437), # LA
                (41.8781, -87.6298),  # Chicago
                (29.7604, -95.3698),  # Houston
            ]
            lat, lon = random.choice(cities)
            geo_payload = {"mode": "manual", "latitude": lat, "longitude": lon}
        elif normalized_locale in {"ru_BY", "ru-BY"}:
            tz_payload = {"mode": "manual", "value": "Europe/Minsk"}
            by_cities = [
                (53.9006, 27.5590),  # Minsk
                (52.4412, 30.9878),  # Gomel
                (53.9138, 30.3364),  # Mogilev
                (55.1904, 30.2049),  # Vitebsk
                (53.6778, 23.8295),  # Hrodna
                (52.0976, 23.7341),  # Brest
            ]
            lat, lon = random.choice(by_cities)
            geo_payload = {"mode": "manual", "latitude": lat, "longitude": lon}
        elif normalized_locale in {"es_CL", "es-CL"}:
            # Chile
            tz_payload = {"mode": "manual", "value": "America/Santiago"}
            cl_cities = [
                (-33.4489, -70.6693),  # Santiago
                (-33.0472, -71.6127),  # Valparaíso
                (-36.8269, -73.0498),  # Concepción
                (-41.4689, -72.9411),  # Puerto Montt
                (-27.1127, -109.3497), # Hanga Roa (Easter Island) - rare
            ]
            lat, lon = random.choice(cl_cities)
            geo_payload = {"mode": "manual", "latitude": lat, "longitude": lon}
        elif normalized_locale in {"es_MX", "es-MX"}:
            # Mexico
            mx_timezones = [
                "America/Mexico_City",  # central
                "America/Monterrey",
                "America/Guadalajara",
                "America/Tijuana",      # pacific
                "America/Cancun",       # eastern-like (Quintana Roo)
            ]
            tz_payload = {"mode": "manual", "value": random.choice(mx_timezones)}
            mx_cities = [
                (19.4326, -99.1332),  # Mexico City
                (25.6866, -100.3161), # Monterrey
                (20.6597, -103.3496), # Guadalajara
                (32.5149, -117.0382), # Tijuana
                (21.1619, -86.8515),  # Cancun
                (20.9674, -89.5926),  # Mérida
                (19.4978, -96.8460),  # Veracruz
            ]
            lat, lon = random.choice(mx_cities)
            geo_payload = {"mode": "manual", "latitude": lat, "longitude": lon}
        elif normalized_locale in {"pt_BR", "pt-BR"}:
            # Brazil (Português, Brasil)
            tz_payload = {"mode": "manual", "value": "America/Sao_Paulo"}
            br_cities = [
                (-23.5505, -46.6333),  # São Paulo
                (-22.9068, -43.1729),  # Rio de Janeiro
                (-15.8267, -47.9218),  # Brasília
                (-19.9167, -43.9345),  # Belo Horizonte
                (-12.9777, -38.5016),  # Salvador
                (-8.0476,  -34.8770),  # Recife
                (-3.1190,  -60.0217),  # Manaus
                (-30.0346, -51.2177),  # Porto Alegre
                (-25.4284, -49.2733),  # Curitiba
            ]
            lat, lon = random.choice(br_cities)
            geo_payload = {"mode": "manual", "latitude": lat, "longitude": lon}
        elif normalized_locale in {"el_GR", "el-GR"}:
            # Greece (Ελληνικά, Ελλάδα)
            tz_payload = {"mode": "manual", "value": "Europe/Athens"}
            gr_cities = [
                (37.9755, 23.7348),   # Athens
                (40.6403, 22.9439),   # Thessaloniki
                (38.2466, 21.7346),   # Patras
                (35.3397, 25.1372),   # Heraklion
                (36.3932, 25.4615),   # Rhodes
                (39.0742, 21.8243),   # Larissa
                (38.0428, 23.7561),   # Piraeus
                (40.9375, 24.4129),   # Kavala
            ]
            lat, lon = random.choice(gr_cities)
            geo_payload = {"mode": "manual", "latitude": lat, "longitude": lon}
        elif normalized_locale in {"de_DE", "de-DE"}:
            # Germany (Deutsch, Deutschland)
            de_timezones = [
                "Europe/Berlin",
                "Europe/Munich",
                "Europe/Hamburg",
                "Europe/Cologne",
            ]
            tz_payload = {"mode": "manual", "value": random.choice(de_timezones)}
            de_cities = [
                (52.5200, 13.4050),   # Berlin
                (48.1351, 11.5820),   # Munich
                (53.5511, 9.9937),    # Hamburg
                (50.9375, 6.9603),    # Cologne
                (51.2277, 6.7735),    # Düsseldorf
                (49.4521, 11.0767),   # Nuremberg
                (52.3759, 9.7320),    # Hanover
                (48.7758, 9.1829),    # Stuttgart
                (51.0504, 13.7373),   # Dresden
                (50.1109, 8.6821),    # Frankfurt
            ]
            lat, lon = random.choice(de_cities)
            geo_payload = {"mode": "manual", "latitude": lat, "longitude": lon}
        else:
            # Default: Russia (original behavior)
            ru_timezones = [
                "Europe/Moscow"
            ]
            tz_payload = {"mode": "manual", "value": ru_timezones[0]}
            geo_payload = {"mode": "manual", "latitude": 55.7558, "longitude": 37.6173}  # Moscow

        # 11) Build payload
        payload: Dict[str, Any] = {
            "name":            name,
            "tags":            tags,
            "platform":        os_plat,
            "platformVersion": plat_ver,
            "mainWebsite":     self._get_realistic_main_website(normalized_locale, geoip),
            "browserType":     "anty",

            "useragent": {
                "mode":  "manual",
                "value": ua
            },

            "webrtc": {
                "mode":     ("manual" if (strict_webrtc and public_ip) else webrtc_mode),
                **({"ipAddress": public_ip} if (strict_webrtc and public_ip) else {})
            },

            "canvas": {
                "mode": "real"
            },

            "webgl": {
                "mode": webgl_mode
            },

            "webglInfo": {
                "mode":           webgl_info_mode,
                "vendor":         webgl["vendor"],
                "renderer":       webgl["renderer"],
                "webgl2Maximum":  webgl["webgl2Maximum"]
            },

            "screen": {
                "mode":       "manual",
                "resolution": webgl["screen"]
            },

            "timezone":    tz_payload,
            "locale":      {"mode": "manual", "value": normalized_locale},
            "language":    {"mode": "manual", "value": lang_value_dash},
            "geolocation": geo_payload,

            "cpu": {
                "mode": cpu_mode,
                **({"value": cpu_value} if cpu_value is not None else {})
            },

            "memory": {
                "mode": mem_mode,
                **({"value": mem_value} if mem_value is not None else {})
            },

            "mediaDevices": {"mode":"real"},
            "doNotTrack":   0,

            "macAddress":   mac_payload,
            "deviceName":   dev_payload,
            "fonts":        fonts_payload,
            "audio":        audio_payload,

            "proxy": {
                "type":     proxy.get("type", "http"),
                "host":     proxy["host"],
                "port":     proxy["port"],
                "login":    proxy.get("user"),
                "password": proxy.get("pass")
            }
        }

        # 13) Send request
        logger.info(f"[PROFILE] Creating with locale={normalized_locale}, language={lang_value_dash}, timezone={tz_payload.get('value')}")
        try:
            resp = self._make_request("post", "/browser_profiles", data=payload)
        except DolphinAntyAPIError as e:
            logger.error(f"[FAIL] Profile creation failed: {e.message}")
            return {"success": False, "error": e.message}

        # Attach payload/meta to response for persistence
        try:
            if isinstance(resp, dict):
                resp.setdefault("_payload_used", payload)
                resp.setdefault("_meta", {
                    "geoip": geoip,
                    "public_ip": public_ip,
                    "strict_webrtc": bool(strict_webrtc)
                })
        except Exception:
            pass

        # 14) Log result
        if resp and ("browserProfileId" in resp or resp.get("data", {}).get("id")):
            logger.info(f"[OK] Profile created: {resp}")
        else:
            logger.error(f"[FAIL] Profile creation failed: {resp}")

        return resp

    def _get_realistic_main_website(self, locale: str, geoip: Optional[Dict] = None) -> str:
        """
        Choose realistic main website - simplified version
        """
        # Simple list of popular international websites
        websites = ["google", "youtube", "facebook", "instagram", "twitter", "amazon"]
        return random.choice(websites)

    def get_profile(self, profile_id: Union[str, int]) -> Dict:
        """Get information about a specific browser profile"""
        return self._make_request("get", f"/browser_profiles/{profile_id}")

    def delete_profile(self, profile_id: Union[str, int]) -> Dict[str, Any]:
        """
        Delete a browser profile by ID permanently (forceDelete=1 required on Free plan).
        Returns a dict with success flag and either message or error.
        """
        logger.info(f"[DELETE] Attempting to delete Dolphin profile: {profile_id} (forceDelete=1)")
        try:
            resp = self._make_request(
                method="delete",
                endpoint=f"/browser_profiles/{profile_id}",
                params={"forceDelete": 1}
            )
        except DolphinAntyAPIError as e:
            logger.error(f"[FAIL] API error deleting profile {profile_id}: {e.message}")
            return {"success": False, "error": e.message}

        # Determine success
        success_flag = False
        if isinstance(resp, dict):
            success_flag = bool(
                resp.get("success") or
                (isinstance(resp.get("data"), dict) and resp["data"].get("success"))
            )

        if success_flag:
            logger.info(f"[OK] Successfully deleted Dolphin profile: {profile_id}")
            return {"success": True, "message": f"Profile {profile_id} deleted successfully."}

        # Extract error details
        error_msg = "Failed to delete profile."
        status_code = resp.get("status_code", "N/A") if isinstance(resp, dict) else "N/A"

        if isinstance(resp, dict):
            # Look for error_detail or error fields
            detail = None
            if isinstance(resp.get("data"), dict) and resp["data"].get("error_detail"):
                detail = resp["data"]["error_detail"]
            elif resp.get("error_detail"):
                detail = resp["error_detail"]
            elif resp.get("error"):
                detail = resp["error"]
            if isinstance(detail, dict):
                error_msg = json.dumps(detail)
            elif detail:
                error_msg = str(detail)

            if status_code == 403:
                logger.warning(f"[WARN] Permission denied (403) deleting profile {profile_id}")
                error_msg = f"Permission denied (403 Forbidden) for profile {profile_id}."

        logger.error(f"[FAIL] {error_msg}")
        return {"success": False, "error": error_msg, "status_code": status_code}

    def create_profile_for_account(self, account_data: Dict[str, Any], proxy_data: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Create a profile specifically configured for an Instagram account
        Returns (profile_id, response) tuple if successful, (None, None) otherwise
        """
        username = account_data.get('username', 'unknown')
        name = f"Instagram {username}"
        
        tags = ["instagram", "bot_profile"]
        if account_data.get('tags'):
            if isinstance(account_data['tags'], list):
                tags.extend(account_data['tags'])
            elif isinstance(account_data['tags'], str):
                tags.append(account_data['tags'])
        
        logger.info(f"[TOOL] Creating profile for Instagram account: {username}")
        # Prefer ru_BY (Belarus region) with Russian interface if using BY proxy
        inferred_locale = None
        try:
            if proxy_data and isinstance(proxy_data, dict):
                country = (proxy_data.get('country') or '').upper()
                if country == 'BY' or 'belarus' in (proxy_data.get('region', '') or '').lower():
                    inferred_locale = 'ru_BY'
        except Exception:
            inferred_locale = None

        locale = account_data.get('locale') or inferred_locale or 'ru_BY'
        if locale not in {'ru_BY', 'en_IN', 'es_CL', 'es_MX', 'pt_BR', 'el_GR', 'de_DE'}:
            locale = 'ru_BY'

        # Optional: select proxy according to locale selection policy if not provided
        try:
            proxy_selection = (account_data.get('proxy_selection') or 'locale_only') if isinstance(account_data, dict) else 'locale_only'
            proxy_pool = account_data.get('proxy_pool') if isinstance(account_data, dict) else None

            # If proxy_data explicitly provided, optionally enforce strict locale match
            strict_flag = bool(account_data.get('proxy_locale_strict')) if isinstance(account_data, dict) else False
            if proxy_data and strict_flag:
                target_country = self._country_from_locale(locale) or 'BY'
                provided_country = self._extract_country_from_proxy(proxy_data)
                if provided_country and provided_country != target_country:
                    logger.error(f"[FAIL] Provided proxy country {provided_country} does not match required locale country {target_country}")
                    return None

            # If no proxy provided, try to select from pool
            if not proxy_data and isinstance(proxy_pool, list) and proxy_pool:
                selected = self._select_proxy_for_locale(locale, proxy_pool, mode=str(proxy_selection))
                if not selected:
                    logger.error(f"[FAIL] No suitable proxy found for selection mode '{proxy_selection}' and locale '{locale}'")
                    return None
                proxy_data = selected
        except Exception as e:
            logger.warning(f"[WARN] Proxy selection step failed, proceeding with given proxy: {str(e)}")

        response = self.create_profile(name=name, proxy=proxy_data, tags=tags, locale=locale)
        
        # Extract profile ID from response
        profile_id = None
        if response and isinstance(response, dict):
            # Check different possible locations for profile ID
            profile_id = response.get("browserProfileId")
            if not profile_id and "data" in response and isinstance(response["data"], dict):
                profile_id = response["data"].get("id")
        
        if profile_id:
            logger.info(f"[OK] Successfully created profile for {username}: {profile_id}")
            return profile_id, response
        else:
            logger.error(f"[FAIL] Failed to create profile for {username}")
            return None, None

    def start_profile(
        self,
        profile_id: Union[str, int],
        headless: bool = False
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Start a browser profile via Local API:
        GET {local_api_base}/browser_profiles/{profile_id}/start?automation=1[&headless=1]
        Returns (success, automation_data) or (False, None).
        """
        logger.info(f"[START] Starting Dolphin profile {profile_id} (headless={headless})")
        
        # Step 1: Check if Dolphin Anty local API is available
        logger.info(f"[SEARCH] [Step 1/3] Checking Dolphin Anty local API availability...")
        try:
            # Use authentication endpoint to check API availability
            auth_data = {"token": self.api_key}
            status_resp = requests.post(
                f"{self.local_api_base}/auth/login-with-token",
                headers={"Content-Type": "application/json"},
                json=auth_data,
                timeout=5
            )
            if status_resp.status_code == 200:
                logger.info(f"[OK] Dolphin Anty local API is responding and authenticated")
            elif status_resp.status_code == 401:
                logger.error(f"[FAIL] Dolphin Anty API authentication failed - invalid token")
                return False, None
            else:
                logger.error(f"[FAIL] Dolphin Anty local API error (HTTP {status_resp.status_code})")
                logger.error("💡 Please make sure Dolphin Anty application is running")
                return False, None
        except requests.exceptions.RequestException as e:
            logger.error(f"[FAIL] Cannot connect to Dolphin Anty local API: {e}")
            logger.error("💡 Please make sure Dolphin Anty application is running on port 3001")
            return False, None
        
        # Step 2: Prepare start request
        params = {"automation": 1}
        if headless:
            params["headless"] = 1

        url = f"{self.local_api_base}/browser_profiles/{profile_id}/start"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Step 3: Start the profile directly (no Remote API validation to avoid 403 errors)
        logger.info(f"[RETRY] [Step 2/3] Sending request to start profile {profile_id}")
        # Retry logic with exponential backoff
        max_retries = 3
        base_delay = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[START_PROFILE] Attempt {attempt + 1}/{max_retries} for profile {profile_id}")
                resp = requests.get(url, params=params, headers=headers, timeout=120)
                
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if data.get("success") and isinstance(data.get("automation"), dict):
                            automation_data = data["automation"]
                            logger.info(f"[OK] [Step 3/3] Profile {profile_id} started successfully")
                            logger.info(f"🔗 Connection details: port={automation_data.get('port')}, wsEndpoint={automation_data.get('wsEndpoint')}")
                            return True, automation_data
                        else:
                            logger.error(f"[FAIL] API returned success=false or missing automation data: {data}")
                            if "error" in data:
                                logger.error(f"[EXPLODE] API Error: {data['error']}")
                            if attempt < max_retries - 1:
                                delay = base_delay * (2 ** attempt)
                                logger.info(f"[START_PROFILE] Retrying in {delay} seconds...")
                                time.sleep(delay)
                                continue
                            return False, None
                    except json.JSONDecodeError:
                        logger.error(f"[FAIL] Invalid JSON response from Dolphin API: {resp.text[:200]}")
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            logger.info(f"[START_PROFILE] Retrying in {delay} seconds...")
                            time.sleep(delay)
                            continue
                        return False, None
                elif resp.status_code == 404:
                    logger.error(f"[FAIL] Profile {profile_id} not found (HTTP 404)")
                    logger.error("💡 The profile may have been deleted from Dolphin Anty or doesn't exist")
                    return False, None
                elif resp.status_code == 400:
                    logger.error(f"[FAIL] Bad request (HTTP 400): {resp.text[:200]}")
                    logger.error("💡 Check if profile is already running or has invalid configuration")
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.info(f"[START_PROFILE] Retrying in {delay} seconds...")
                        time.sleep(delay)
                        continue
                    return False, None
                else:
                    logger.error(f"[FAIL] Start profile failed with HTTP {resp.status_code}: {resp.text[:200]}")
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.info(f"[START_PROFILE] Retrying in {delay} seconds...")
                        time.sleep(delay)
                        continue
                    return False, None
                    
            except requests.exceptions.Timeout as e:
                logger.warning(f"[START_PROFILE] Timeout on attempt {attempt + 1}/{max_retries} for profile {profile_id}: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"[START_PROFILE] Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"[FAIL] Timeout (120s) starting profile {profile_id} after {max_retries} attempts")
                    logger.error("💡 Profile may be taking too long to start, try again later")
                    return False, None
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"[START_PROFILE] Connection error on attempt {attempt + 1}/{max_retries} for profile {profile_id}: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"[START_PROFILE] Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"[FAIL] Connection error starting profile {profile_id}: {e}")
                    logger.error("💡 Make sure Dolphin Anty application is running")
                    return False, None
            except requests.exceptions.RequestException as e:
                logger.warning(f"[START_PROFILE] Request error on attempt {attempt + 1}/{max_retries} for profile {profile_id}: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"[START_PROFILE] Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"[FAIL] Request error starting profile {profile_id}: {e}")
                    return False, None
            except Exception as e:
                logger.warning(f"[START_PROFILE] Unexpected error on attempt {attempt + 1}/{max_retries} for profile {profile_id}: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"[START_PROFILE] Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"[FAIL] Unexpected error starting profile {profile_id}: {e}")
                    return False, None
        
        return False, None

    def stop_profile(self, profile_id: Union[str, int]) -> bool:
        """
        Stop a running browser profile via Local API
        Returns True if successful, False otherwise
        """
        logger.info(f"🛑 Stopping Dolphin profile: {profile_id}")
        
        try:
            # Use local API to stop the profile with GET request (according to documentation)
            url = f"{self.local_api_base}/browser_profiles/{profile_id}/stop"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success", True):  # Some versions may not return success field
                        logger.info(f"[OK] Successfully stopped profile: {profile_id}")
                        return True
                    else:
                        logger.error(f"[FAIL] Failed to stop profile {profile_id}: {data}")
                        return False
                except json.JSONDecodeError:
                    # If response is not JSON, assume success if status is 200
                    logger.info(f"[OK] Successfully stopped profile: {profile_id} (non-JSON response)")
                    return True
            else:
                logger.error(f"[FAIL] Failed to stop profile {profile_id}, HTTP {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[FAIL] Network error stopping profile {profile_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[FAIL] Unexpected error stopping profile {profile_id}: {str(e)}")
            return False

    def update_profile_proxy(self, profile_id: Union[str, int], proxy: Dict) -> Dict:
        """
        Update only the proxy settings for a profile using PATCH method.
        Proxy dict keys: type, host, port, user/login, pass/password
        
        Returns:
            dict: Result of the operation
        """
        logger.info(f"🌐 Updating proxy for Dolphin profile {profile_id}")
        
        # Verify required proxy fields
        required_fields = ["host", "port"]
        missing_fields = [field for field in required_fields if field not in proxy]
        if missing_fields:
            error_msg = f"Missing required proxy fields: {', '.join(missing_fields)}"
            logger.error(f"[FAIL] {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Prepare proxy data in the format expected by the PATCH API
        # According to API docs, proxy fields should be sent as form data
        proxy_data = {
            "proxy[type]": proxy.get("type", "http"),
            "proxy[host]": proxy.get("host"),
            "proxy[port]": str(proxy.get("port")),  # Convert to string for form data
        }
        
        # Add optional login/password if provided
        login = proxy.get("user") or proxy.get("login")
        password = proxy.get("pass") or proxy.get("password")
        
        if login:
            proxy_data["proxy[login]"] = login
        if password:
            proxy_data["proxy[password]"] = password
        
        try:
            # Update the profile with new proxy data using PATCH
            response = self._make_request(
                method="patch",
                endpoint=f"/browser_profiles/{profile_id}",
                data=proxy_data
            )
            
            # Check if response indicates success
            if response:
                # API might return different success indicators
                if isinstance(response, dict):
                    # Check for explicit success field
                    if response.get("success") is True:
                        logger.info(f"[OK] Successfully updated proxy for profile {profile_id}")
                        return {"success": True, "message": f"Proxy updated for profile {profile_id}"}
                    # Check for error field
                    elif "error" in response:
                        error_msg = response.get("error", "Unknown API error")
                        logger.error(f"[FAIL] API error updating proxy for profile {profile_id}: {error_msg}")
                        return {"success": False, "error": error_msg}
                    # If no explicit success/error, assume success if we got a response
                    else:
                        logger.info(f"[OK] Successfully updated proxy for profile {profile_id} (assumed from response)")
                        return {"success": True, "message": f"Proxy updated for profile {profile_id}"}
                else:
                    # Non-dict response, assume success if we got any response
                    logger.info(f"[OK] Successfully updated proxy for profile {profile_id}")
                    return {"success": True, "message": f"Proxy updated for profile {profile_id}"}
            else:
                # No response or empty response
                error_msg = "No response from API"
                logger.error(f"[FAIL] Failed to update proxy for profile {profile_id}: {error_msg}")
                return {"success": False, "error": error_msg}
            
        except DolphinAntyAPIError as e:
            error_msg = f"API error updating proxy for profile {profile_id}: {e.message}"
            logger.error(f"[FAIL] {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error updating proxy for profile {profile_id}: {str(e)}"
            logger.error(f"[FAIL] {error_msg}")
            return {"success": False, "error": error_msg}

    def _local_api_auth(self) -> Tuple[bool, Optional[str]]:
        """
        Авторизация в локальном API Dolphin с использованием токена
        POST http://localhost:3001/v1.0/auth/login-with-token
        Content-Type: application/json
        {"token": "API_TOKEN"}
        
        Returns:
            Tuple[bool, Optional[str]]: (успех, сообщение об ошибке)
        """
        if not self.api_key:
            logger.error("[FAIL] No API token provided for local API authentication")
            return False, "No API token provided"
            
        endpoint = f"{self.local_api_base}/auth/login-with-token"
        headers = {"Content-Type": "application/json"}
        data = {"token": self.api_key}
        
        try:
            logger.info("🔑 Authenticating with local Dolphin API")
            
            # Сначала проверяем, что сервер вообще отвечает
            try:
                response = requests.get(
                    f"{self.local_api_base}/status", 
                    timeout=5
                )
                if response.status_code != 200:
                    logger.warning(f"[WARN] Local API is not responding correctly: {response.status_code}")
                    # В некоторых случаях API может работать и без авторизации
                    # или авторизация уже была выполнена ранее
                    return True, None
            except requests.exceptions.RequestException as e:
                logger.warning(f"[WARN] Could not connect to local API server: {e}")
                # Для локального API на старых версиях, продолжаем работу без авторизации
                return True, None
            
            # Пробуем авторизоваться
            try:
                response = requests.post(endpoint, json=data, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    # Проверяем ответ на успешность
                    try:
                        resp_data = response.json()
                        if resp_data.get("success") or resp_data.get("status") == "ok":
                            logger.info("[OK] Successfully authenticated with local Dolphin API")
                            return True, None
                        else:
                            # Несмотря на ошибку в ответе, продолжаем выполнение
                            # В некоторых версиях API статус не возвращается, но авторизация проходит
                            logger.warning(f"[WARN] API returned success=false, but continuing: {resp_data}")
                            return True, None
                    except json.JSONDecodeError:
                        # Если не смогли распарсить JSON, продолжаем без авторизации
                        logger.warning(f"[WARN] Invalid JSON response from auth endpoint: {response.text}")
                        return True, None
                        
                elif response.status_code == 401:
                    # Неверный токен - это критическая ошибка
                    error_msg = f"Invalid API token: {response.text}"
                    logger.error(f"[FAIL] {error_msg}")
                    return False, error_msg
                    
                else:
                    # Другие ошибки - пытаемся продолжить работу
                    logger.warning(f"[WARN] Auth request failed with status {response.status_code}: {response.text}")
                    return True, None
                    
            except requests.exceptions.RequestException as e:
                # Ошибка при запросе к API - не критичная
                logger.warning(f"[WARN] Auth request failed: {e}")
                return True, None
                
        except Exception as e:
            # Общая ошибка - продолжаем работу
            logger.warning(f"[WARN] Authentication process error: {str(e)}")
            return True, None

    async def _ensure_page_available(self, context, page, imageless=False, task_logger=None):
        """
        Убеждаемся, что у нас есть рабочая страница
        """
        def log_action(message, level="info"):
            if level == "info":
                logger.info(message)
            elif level == "warning":
                logger.warning(message)
            elif level == "error":
                logger.error(message)
            
            if task_logger:
                task_logger(message)
        
        try:
            # Проверяем, что страница все еще доступна
            if page and not page.is_closed():
                # Страница существует, проверяем что с ней можно работать
                try:
                    await page.evaluate("() => document.readyState")
                    return page  # Страница в порядке
                except Exception:
                    log_action("[WARN] Page evaluation failed, recreating page", "warning")
            else:
                log_action("[WARN] Page is closed, creating new page", "warning")
            
            # Создаем новую страницу
            page = await context.new_page()
            log_action("[OK] Created new browser page", "info")
            
            # Применяем настройки imageless если нужно
            if imageless:
                await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico}", lambda route: route.abort())
                log_action("[BLOCK] Images blocked for new page", "info")
            
            return page
            
        except Exception as e:
            log_action(f"[FAIL] Critical error ensuring page availability: {str(e)}", "error")
            raise e

    async def _check_for_human_verification_dialog_async(self, page, task_logger=None):
        """
        Асинхронная проверка на наличие окна верификации человека в Instagram
        Возвращает True если требуется верификация, False если все в порядке
        """
        try:
            def log_action(message, level="info"):
                if level == "info":
                    logger.info(message)
                elif level == "warning":
                    logger.warning(message)
                elif level == "error":
                    logger.error(message)
                
                if task_logger:
                    task_logger(message)
            
            log_action("[SEARCH] Checking for human verification dialog...", "info")
            
            # Ждем немного для загрузки страницы
            await asyncio.sleep(random.uniform(1, 2))
            
            # Получаем текст страницы для проверки
            try:
                page_text = await page.inner_text('body') or ""
            except Exception:
                page_text = ""
            
            # Ключевые слова для обнаружения верификации человека
            human_verification_keywords = [
                'подтвердите, что вы человек',
                'подтвердите что вы человек',
                'подтвердите, что вы — человек',
                'confirm that you are human',
                'prove you are human',
                'целостности аккаунта',
                'целостность аккаунта',
                'account integrity',
                'вы не сможете использовать свой аккаунт',
                'you cannot use your account',
                'подтвердить, что вы — человек',
                'подтвердите свою личность',
                'confirm your identity'
            ]
            
            # Проверяем наличие ключевых слов
            verification_detected = any(keyword.lower() in page_text.lower() for keyword in human_verification_keywords)
            
            if verification_detected:
                log_action("[WARN] Human verification keywords found in page text", "warning")
                
                # Дополнительная проверка на специфические элементы диалога
                verification_selectors = [
                    # Русские селекторы
                    'span:has-text("подтвердите, что вы")',
                    'span:has-text("подтвердите что вы")',
                    'span:has-text("человек")',
                    'div:has-text("целостности аккаунта")',
                    'div:has-text("целостность аккаунта")',
                    'span:has-text("Почему вы это видите")',
                    'span:has-text("Что это означает")',
                    'span:has-text("Что можно сделать")',
                    
                    # Английские селекторы
                    'span:has-text("confirm that you are human")',
                    'span:has-text("prove you are human")',
                    'div:has-text("account integrity")',
                    'span:has-text("Why you are seeing this")',
                    'span:has-text("What this means")',
                    'span:has-text("What you can do")',
                    
                    # Общие селекторы диалога
                    'div[data-bloks-name="bk.components.Flexbox"]',
                    'div[role="dialog"]',
                    'button:has-text("Продолжить")',
                    'button:has-text("Continue")',
                    'button:has-text("Fortfahren")',  # DE
                    'button:has-text("Συνέχεια")',     # EL
                ]
                
                # Ищем элементы диалога верификации
                dialog_elements_found = []
                for selector in verification_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element and await element.is_visible():
                            dialog_elements_found.append(selector)
                    except Exception:
                        continue
                
                if dialog_elements_found:
                    log_action(f"[FAIL] Human verification dialog confirmed! Found elements: {dialog_elements_found[:3]}", "error")
                    
                    # Логируем образец текста для отладки
                    verification_text_sample = page_text[:500] if page_text else "No text found"
                    log_action(f"[SEARCH] Verification dialog text sample: {verification_text_sample}", "error")
                    
                    return True
                else:
                    log_action("[OK] Verification keywords found but no dialog elements detected", "info")
                    return False
            else:
                log_action("[OK] No human verification dialog detected", "info")
                return False
                
        except Exception as e:
            log_action(f"[WARN] Error checking for human verification dialog: {str(e)}", "warning")
            return False

    async def _apply_stealth_patches(self, context, accept_language: Optional[str] = None, profile_id: Optional[Union[str,int]] = None):
        """Apply additional anti-detection patches at context level."""
        try:
            # Accept-Language aligned with RU/EN mix by default (can be adjusted)
            try:
                # Fallback to ru-BY mapping if not provided (profile-aware resolution is applied by caller)
                fallback_al = 'ru-BY,ru;q=0.9,en-US;q=0.8,en;q=0.7'
                await context.set_extra_http_headers({"Accept-Language": (accept_language or fallback_al)})
            except Exception:
                pass
            # Try to fetch cpu/memory from profile for JS overrides
            cpu_js = None
            mem_js = None
            if profile_id is not None:
                try:
                    prof = self.get_profile(profile_id)
                    data = prof.get('data', prof)
                    cpu_v = None
                    mem_v = None
                    try:
                        cpu_obj = data.get('cpu') or (data.get('browserProfile') or {}).get('cpu')
                        if isinstance(cpu_obj, dict):
                            cpu_v = cpu_obj.get('value')
                    except Exception:
                        cpu_v = None
                    try:
                        mem_obj = data.get('memory') or (data.get('browserProfile') or {}).get('memory')
                        if isinstance(mem_obj, dict):
                            mem_v = mem_obj.get('value')
                    except Exception:
                        mem_v = None
                    if isinstance(cpu_v, int) and cpu_v > 0:
                        cpu_js = cpu_v
                    if isinstance(mem_v, int) and mem_v > 0:
                        # navigator.deviceMemory usually small ints (e.g., 4/8/16)
                        mem_candidates = [2,4,8,16,32]
                        mem_js = mem_v if mem_v in mem_candidates else 8
                except Exception:
                    pass
            # Mask common automation flags
            stealth_script = r"""
                // navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                // chrome runtime
                if (!window.chrome) {
                  Object.defineProperty(window, 'chrome', { get: () => ({ runtime: {} }) });
                }
                // languages
                Object.defineProperty(navigator, 'languages', { get: () => navigator.language ? [navigator.language.split('-')[0], navigator.language] : ['en','en-US'] });
                // permissions query override (avoid notifications prompt anomalies)
                const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
                if (originalQuery) {
                  window.navigator.permissions.query = (parameters) => (
                    parameters && parameters.name === 'notifications' ?
                      Promise.resolve({ state: Notification.permission }) : originalQuery(parameters)
                  );
                }
                // WebGL vendor/renderer presence guards (Dolphin sets real values)
                try {
                  const getParameter = WebGLRenderingContext.prototype.getParameter;
                  WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    // 37445 UNMASKED_VENDOR_WEBGL, 37446 UNMASKED_RENDERER_WEBGL
                    if (parameter === 37445 || parameter === 37446) {
                      const val = getParameter.call(this, parameter);
                      return val || 'Intel Inc.';
                    }
                    return getParameter.call(this, parameter);
                  };
                } catch (e) {}
            """
            # Inject hardwareConcurrency/deviceMemory overrides if available
            if cpu_js is not None or mem_js is not None:
                overrides = ""
                if cpu_js is not None:
                    overrides += f"Object.defineProperty(navigator,'hardwareConcurrency',{{get:()=> {cpu_js}}});\n"
                if mem_js is not None:
                    overrides += f"Object.defineProperty(navigator,'deviceMemory',{{get:()=> {mem_js}}});\n"
                stealth_script = overrides + stealth_script
            try:
                await context.add_init_script(stealth_script)
            except Exception:
                pass
        except Exception:
            # Fail silently; Dolphin's own fingerprinting still applies
            pass

    async def run_cookie_robot(
        self,
        profile_id: Union[str, int],
        urls: List[str],
        headless: bool = False,
        imageless: bool = False,
        duration: int = 300,
        poll_interval: int = 5,
        task_logger=None
    ) -> Dict[str, Any]:
        if not urls:
            return {"success": False, "error": "No URLs provided"}

        # Define log_action function for consistent logging within this method
        def log_action(message, level="info"):
            if level == "info":
                logger.info(message)
            elif level == "warning":
                logger.warning(message)
            elif level == "error":
                logger.error(message)
            
            if task_logger:
                task_logger(message)

        # 1) Запускаем профиль и получаем данные для подключения
        profile_started = False
        automation_data = None
        successful_visits = 0
        failed_visits = 0
        shuffled_urls = urls.copy()
        
        try:
            logger.info(f"[RETRY] Starting Dolphin profile {profile_id}...")
            if task_logger:
                task_logger(f"[RETRY] Starting Dolphin profile {profile_id}...")
            
            # Debug: check Dolphin status before starting profile
            dolphin_status = self.check_dolphin_status()
            logger.info(f"[SEARCH] Dolphin status before starting profile: {dolphin_status}")
            if task_logger:
                task_logger(f"[SEARCH] Dolphin status: {dolphin_status}")
            
            # Retry starting profile a few times with small backoff
            automation_data = None
            profile_started = False
            start_errors = []
            for attempt in range(3):
                success, profile_data = self.start_profile(profile_id, headless=headless)
                profile_started = success
                automation_data = profile_data
                logger.info(f"[RETRY] Profile start attempt {attempt+1}/3 - Success: {success}, Data: {profile_data}")
                if task_logger:
                    task_logger(f"[RETRY] Profile start attempt {attempt+1}/3 - Success: {success}")
                if success and automation_data:
                    logger.info(f"[OK] Profile {profile_id} started successfully")
                    logger.info(f"[LINK] Automation data: {automation_data}")
                    if task_logger:
                        task_logger(f"[OK] Profile {profile_id} started successfully")
                    break
                else:
                    start_errors.append(str(profile_data))
                    await asyncio.sleep(1 + attempt)
            if not (profile_started and automation_data):
                logger.error(f"[FAIL] Could not start profile {profile_id} or get automation data")
                if task_logger:
                    task_logger(f"[FAIL] Failed to start profile {profile_id}")
                return {"success": False, "error": "Failed to start profile or get automation data"}
                
        except Exception as e:
            logger.error(f"[FAIL] Exception during profile start: {e}")
            if task_logger:
                task_logger(f"[FAIL] Profile start error: {str(e)}")
            return {"success": False, "error": f"Profile start error: {str(e)}"}

        # 2) Подключаемся к браузеру через Playwright
        browser = None
        try:
            # Извлекаем данные для подключения
            port = automation_data.get("port")
            ws_endpoint = automation_data.get("wsEndpoint")
            
            if not port or not ws_endpoint:
                logger.error(f"[FAIL] Missing connection data: port={port}, wsEndpoint={ws_endpoint}")
                if profile_started:
                    self.stop_profile(profile_id)
                return {"success": False, "error": "Missing port or wsEndpoint in automation data"}
            
            # Формируем WebSocket URL для подключения
            ws_url = f"ws://127.0.0.1:{port}{ws_endpoint}"
            logger.info(f"[WEB] Connecting to browser via: {ws_url}")
            
            async with async_playwright() as p:
                # Подключаемся к уже запущенному браузеру
                connect_errors = []
                for attempt in range(5):
                    try:
                        browser = await p.chromium.connect_over_cdp(ws_url)
                        break
                    except Exception as ce:
                        connect_errors.append(str(ce))
                        await asyncio.sleep(1 + attempt)
                    if not browser:
                        # Ensure profile stopped if we cannot connect
                        try:
                            if profile_started:
                                self.stop_profile(profile_id)
                        except Exception:
                            pass
                        return {"success": False, "error": f"Playwright automation error: BrowserType.connect_over_cdp failed: {connect_errors[-1] if connect_errors else 'unknown error'}"}
                logger.info(f"[OK] Successfully connected to Dolphin browser")
                
                try:
                    # Получаем существующий контекст или создаем новый
                    contexts = browser.contexts
                    if contexts:
                        context = contexts[0]
                        logger.info(f"[FILE] Using existing browser context")
                    else:
                        context = await browser.new_context()
                        logger.info(f"[FILE] Created new browser context")
                    
                    # Apply stealth patches to reduce automation detection
                    resolved_al = self._resolve_accept_language(profile_id)
                    await self._apply_stealth_patches(context, accept_language=resolved_al, profile_id=profile_id)
                    
                    # Создаем новую страницу
                    page = await context.new_page()
                    
                    # Рандомизируем порядок URL для более естественного поведения
                    random.shuffle(shuffled_urls)
                    if task_logger:
                        task_logger(f"[TARGET] Starting Cookie Robot simulation...")
                        task_logger(f"[LIST] Processing {len(shuffled_urls)} URLs")
                    
                    # Обходим каждый URL
                    for i, url in enumerate(shuffled_urls, 1):
                        try:
                            if task_logger:
                                task_logger(f"[PROCESS] [{i}/{len(shuffled_urls)}] Starting: {url}")
                            
                            # Ensure page available
                            try:
                                page = await self._ensure_page_available(context, page, imageless, task_logger)
                            except Exception as page_error:
                                failed_visits += 1
                                if task_logger:
                                    task_logger(f"[ERROR] [{i}/{len(shuffled_urls)}] Page recovery failed for: {url}")
                                continue
                            
                            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                            
                            # Simulate user activity
                            base_duration = duration / len(shuffled_urls)
                            random_delay = random.uniform(base_duration * 0.8, base_duration * 1.2)
                            if task_logger:
                                task_logger(f"[WAIT] [{i}/{len(shuffled_urls)}] Simulating user activity for {random_delay:.1f} seconds")
                            try:
                                await self._simulate_user_activity(page, random_delay, task_logger)
                            except Exception:
                                pass
                            
                            successful_visits += 1
                            if task_logger:
                                task_logger(f"[SUCCESS] [{i}/{len(shuffled_urls)}] Successfully completed: {url}")
                            
                            # Cleanup extra tabs
                            try:
                                all_pages = context.pages
                                for p in all_pages:
                                    if p != page and not p.is_closed():
                                        await p.close()
                            except Exception:
                                pass
                        except Exception as e:
                            failed_visits += 1
                            if task_logger:
                                task_logger(f"[ERROR] [{i}/{len(shuffled_urls)}] Failed {url}: {str(e)}")
                            # Attempt to recover page for next iteration
                            try:
                                page = await self._ensure_page_available(context, page, imageless, task_logger)
                            except Exception:
                                page = None
                            continue
                    
                    # Close page and context
                    try:
                        if page and not page.is_closed():
                            await page.close()
                    except Exception:
                        pass
                    try:
                        await context.close()
                    except Exception:
                        pass
                    
                    # Build result
                    result = {
                        "success": True,
                        "data": {
                            "message": "Cookie Robot executed successfully via Playwright",
                            "urls_total": len(urls),
                            "urls_randomized": len(shuffled_urls),
                            "urls_processed": len(shuffled_urls),
                            "successful_visits": successful_visits,
                            "failed_visits": failed_visits,
                            "success_rate": round((successful_visits / len(shuffled_urls)) * 100, 2) if shuffled_urls else 0,
                            "total_duration": duration,
                            "visit_order": shuffled_urls
                        }
                    }
                    if task_logger:
                        task_logger(f"[TARGET] Cookie Robot completed successfully!")
                    return result
                    
                except asyncio.TimeoutError:
                    # Convert timeout into partial success if any progress
                    if successful_visits >= 10:
                        partial = {
                            "success": False,
                            "error": "Cookie Robot timeout during execution",
                            "data": {
                                "successful_visits": successful_visits,
                                "failed_visits": failed_visits,
                                "success_rate": round((successful_visits / max(1, (successful_visits + failed_visits))) * 100, 2)
                            }
                        }
                        return partial
                    return {"success": False, "error": "Cookie Robot timeout during execution"}
                except Exception as e:
                    # If we have >=10 successes, surface as partial data for upper layer
                    if successful_visits >= 10:
                        return {
                            "success": False,
                            "error": f"Unexpected error in Cookie Robot: {str(e)}",
                            "data": {
                                "successful_visits": successful_visits,
                                "failed_visits": failed_visits,
                                "success_rate": round((successful_visits / max(1, (successful_visits + failed_visits))) * 100, 2)
                            }
                        }
                    return {"success": False, "error": f"Unexpected error in Cookie Robot: {str(e)}"}
                
                finally:
                    # Disconnect from browser
                    if browser:
                        try:
                            await browser.close()
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"[FAIL] Error during Playwright automation: {str(e)}")
            # Partial surface if possible
            if successful_visits >= 10:
                return {
                    "success": False,
                    "error": f"Playwright automation error: {str(e)}",
                    "data": {
                        "successful_visits": successful_visits,
                        "failed_visits": failed_visits,
                        "success_rate": round((successful_visits / max(1, (successful_visits + failed_visits))) * 100, 2)
                    }
                }
            return {"success": False, "error": f"Playwright automation error: {str(e)}"}
            
        finally:
            # Export cookies to database before stopping profile
            try:
                if profile_id:
                    cookies_list = self.get_cookies(profile_id)
                    if cookies_list:
                        logger.info(f"[COOKIES] [ASYNC_COOKIE_ROBOT] Exported {len(cookies_list)} cookies for profile {profile_id}")
                        # Note: Cookies will be saved to DB by the calling code
                    else:
                        logger.warning(f"[COOKIES] [ASYNC_COOKIE_ROBOT] No cookies found for profile {profile_id}")
            except Exception as e:
                logger.error(f"[COOKIES] [ASYNC_COOKIE_ROBOT] Failed to export cookies for profile {profile_id}: {e}")
            
            # Ensure profile is stopped if we started it
            if profile_started:
                try:
                    logger.info(f"[STOP] Stopping browser profile {profile_id}")
                    self.stop_profile(profile_id)
                except Exception:
                    pass

    async def _simulate_user_activity(self, page, duration: float, task_logger=None):
        """
        Имитирует активность пользователя на странице с более человечными действиями
        """
        def log_action(message, level="info"):
            """Helper function to log both to logger and task"""
            if level == "debug":
                # Убираем debug логи из task_logger для чистоты
                logger.debug(message)
            elif level == "info":
                logger.info(message)
                # В task_logger только важные info сообщения
                if task_logger and any(keyword in message.lower() for keyword in ["start", "complete", "error", "warning", "success"]):
                    task_logger(message)
            elif level == "warning":
                logger.warning(message)
                if task_logger:
                    task_logger(message)
            elif level == "error":
                logger.error(message)
                if task_logger:
                    task_logger(message)
        
        try:
            start_time = time.time()
            end_time = start_time + duration
            actions_performed = 0
            
            log_action(f"🎭 Starting user activity simulation for {duration:.1f} seconds", "info")
            
            # Статистика действий для отчета
            action_stats = {
                "scroll_down": 0, "scroll_up": 0, "smooth_scroll": 0,
                "move_mouse": 0, "random_click": 0, "hover_element": 0,
                "select_text": 0, "double_click": 0, "wait": 0
            }
            
            # Логируем прогресс каждые 30 секунд
            last_progress_log = start_time
            
            while time.time() < end_time:
                remaining_time = end_time - time.time()
                if remaining_time <= 0:
                    break
                
                # Проверяем, что страница еще открыта перед каждым действием
                if page.is_closed():
                    log_action("[WARN] Page was closed during user activity simulation, stopping", "warning")
                    break
                    
                # Случайное действие каждые 2-6 секунд (более частые действия)
                action_interval = min(random.uniform(2, 6), remaining_time)
                await asyncio.sleep(action_interval)
                
                # Еще одна проверка после sleep
                if page.is_closed():
                    log_action("[WARN] Page was closed during sleep, stopping", "warning")
                    break
                
                # Логируем прогресс каждые 30 секунд
                current_time = time.time()
                if current_time - last_progress_log >= 30:
                    elapsed = current_time - start_time
                    remaining = duration - elapsed
                    log_action(f"[WAIT] Activity progress: {elapsed:.0f}s elapsed, {remaining:.0f}s remaining", "info")
                    last_progress_log = current_time
                
                # Выбираем случайное действие с весами (более человечные действия чаще)
                actions = [
                    "scroll_down", "scroll_down", "scroll_down",  # скролл вниз чаще
                    "scroll_up", 
                    "move_mouse", "move_mouse", "move_mouse",    # движение мыши чаще
                    "random_click", "random_click", "random_click", # случайные клики
                    "hover_element", "hover_element",               # наведение на элементы
                    "smooth_scroll",              # плавный скролл
                    "select_text",                # выделение текста
                    "double_click",               # двойной клик
                    "wait", "wait"                # пауза для чтения
                ]
                action = random.choice(actions)
                action_stats[action] += 1
                
                try:
                    # Проверяем состояние страницы перед каждым действием
                    if page.is_closed():
                        log_action("[WARN] Page closed before action execution, stopping", "warning")
                        break
                    
                    # Дополнительная проверка - пытаемся получить URL страницы
                    try:
                        current_url = page.url
                    except Exception as url_error:
                        # Если не можем получить URL, страница скорее всего недоступна
                        error_str = str(url_error).lower()
                        if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                            log_action("[WARN] Page became unavailable during activity simulation, stopping", "warning")
                            break
                        else:
                            # Убираем избыточные warning логи
                            logger.debug(f"Could not get page URL: {str(url_error)[:50]}")
                    
                    if action == "scroll_down":
                        # Более естественный скролл с разной интенсивностью
                        scroll_amount = random.uniform(0.2, 0.5)
                        await page.evaluate(f"window.scrollBy(0, window.innerHeight * {scroll_amount})")
                        logger.debug(f"📜 Scrolled down ({scroll_amount:.2f} screen heights)")
                        
                    elif action == "scroll_up":
                        scroll_amount = random.uniform(0.1, 0.3)
                        await page.evaluate(f"window.scrollBy(0, -window.innerHeight * {scroll_amount})")
                        logger.debug(f"📜 Scrolled up ({scroll_amount:.2f} screen heights)")
                        
                    elif action == "smooth_scroll":
                        # Плавный скролл с анимацией
                        target_y = random.randint(100, 500)
                        await page.evaluate(f"""
                            window.scrollTo({{
                                top: window.scrollY + {target_y},
                                behavior: 'smooth'
                            }})
                        """)
                        logger.debug(f"🌊 Smooth scrolled {target_y}px down")
                        
                    elif action == "move_mouse":
                        # Более естественное движение мыши с плавными переходами
                        x = random.randint(50, 1200)
                        y = random.randint(50, 800)
                        steps = random.randint(3, 8)
                        
                        # Плавное движение мыши
                        await page.mouse.move(x, y, steps=steps)
                        
                        # Иногда делаем паузу
                        if random.random() < 0.3:
                            pause_time = random.uniform(0.5, 1.5)
                            await asyncio.sleep(pause_time)
                            logger.debug(f"🖱️ Moved mouse to ({x}, {y}) in {steps} steps, paused {pause_time:.1f}s")
                        else:
                            logger.debug(f"🖱️ Moved mouse to ({x}, {y}) in {steps} steps)")
                        
                    elif action == "random_click":
                        # Реалистичные клики как у настоящего пользователя
                        click_success = False
                        try:
                            # Проверяем состояние страницы перед кликом
                            if page.is_closed():
                                log_action("[WARN] Page closed before click, skipping", "warning")
                                continue
                            
                            # Сохраняем текущий URL для возможного возврата
                            try:
                                current_url = page.url
                            except Exception:
                                logger.debug("Could not get current URL for click action, skipping")
                                continue
                            
                            # Ищем интерактивные элементы (как настоящий пользователь)
                            interactive_selectors = [
                                "a", "button", "input[type='button']", "input[type='submit']",
                                "[onclick]", "[role='button']", ".btn", ".button", 
                                "div[onclick]", "span[onclick]", "li[onclick]",
                                "p", "div", "span", "h1", "h2", "h3", "img"  # Обычные элементы тоже
                            ]
                            
                            # Выбираем случайный тип элемента
                            selector = random.choice(interactive_selectors)
                            
                            try:
                                elements = await page.query_selector_all(selector)
                            except Exception as selector_error:
                                # Если не можем найти элементы, делаем обычный клик
                                error_str = str(selector_error).lower()
                                if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                                    log_action("[WARN] Page closed during element search, stopping", "warning")
                                    break
                                else:
                                    # Обычный клик по координатам
                                    x = random.randint(200, 800)
                                    y = random.randint(200, 600)
                                    await page.mouse.click(x, y)
                                    logger.debug(f"🖱️ Fallback click at ({x}, {y}) due to selector error")
                                    continue
                            
                            if elements:
                                # Фильтруем только критически опасные элементы
                                filtered_elements = []
                                for element in elements[:30]:  # Проверяем больше элементов
                                    try:
                                        is_visible = await element.is_visible()
                                        if not is_visible:
                                            continue
                                            
                                        # Блокируем только критически опасные действия
                                        text_content = await element.text_content() or ""
                                        critical_danger_words = [
                                            'close window', 'close tab', 'exit browser', 'quit',
                                            'закрыть окно', 'закрыть вкладку', 'выйти из браузера',
                                            'window.close', 'tab.close'
                                        ]
                                        
                                        # Проверяем только на критически опасный текст
                                        is_critical_danger = any(
                                            danger.lower() in text_content.lower() 
                                            for danger in critical_danger_words
                                        )
                                        
                                        if is_critical_danger:
                                            continue
                                            
                                        # Проверяем href на критически опасные javascript команды
                                        href = await element.get_attribute('href')
                                        if href and ('window.close()' in href or 'tab.close()' in href):
                                            continue
                                            
                                        filtered_elements.append(element)
                                    except Exception:
                                        continue
                                
                                if filtered_elements:
                                    # Кликаем как настоящий пользователь
                                    element = random.choice(filtered_elements)
                                    
                                    # Реалистичный клик с коротким таймаутом
                                    await element.click(timeout=2000)
                                    logger.debug(f"🖱️ User-like clicked on {selector} element")
                                    
                                    # Ждем немного чтобы увидеть что произошло
                                    await asyncio.sleep(random.uniform(0.5, 1.5))
                                    
                                    # Проверяем, произошла ли навигация
                                    try:
                                        new_url = page.url
                                        if new_url != current_url:
                                            logger.debug(f"🌐 Navigation detected: {current_url} → {new_url}")
                                            
                                            # Случайно решаем - остаться или вернуться (как пользователь)
                                            should_return = random.choice([True, True, False])  # 66% вернуться
                                            
                                            if should_return:
                                                # Возвращаемся назад (как пользователь нажал "назад")
                                                try:
                                                    await page.go_back(wait_until="domcontentloaded", timeout=5000)
                                                    logger.debug(f"⬅️ User went back to original page")
                                                except Exception:
                                                    # Если не получается вернуться, переходим напрямую
                                                    try:
                                                        await page.goto(current_url, wait_until="domcontentloaded", timeout=5000)
                                                        logger.debug(f"[RETRY] Returned to original page via direct navigation")
                                                    except Exception:
                                                        logger.debug(f"Could not return to original page")
                                            else:
                                                logger.debug(f"[LOCATION] User stayed on new page")
                                    except Exception as nav_check_error:
                                        # Если не можем проверить навигацию, продолжаем
                                        error_str = str(nav_check_error).lower()
                                        if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                                            log_action("[WARN] Page closed during navigation check, stopping", "warning")
                                            break
                                        else:
                                            logger.debug(f"Could not check navigation: {str(nav_check_error)[:50]}")
                                    
                                    click_success = True
                                else:
                                    # Обычный клик по координатам (пользователь кликнул на пустое место)
                                    x = random.randint(100, 900)
                                    y = random.randint(100, 700)
                                    await page.mouse.click(x, y)
                                    logger.debug(f"🖱️ User clicked on empty area ({x}, {y})")
                                    click_success = True
                            
                            if not click_success:
                                # Пользователь кликнул случайно
                                x = random.randint(100, 900)
                                y = random.randint(100, 700)
                                await page.mouse.click(x, y)
                                logger.debug(f"🖱️ Random user click at ({x}, {y})")
                                
                        except Exception as click_error:
                            # Проверяем, связана ли ошибка с закрытием страницы
                            error_str = str(click_error).lower()
                            if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                                log_action("[WARN] Page closed during click action, stopping", "warning")
                                break
                            else:
                                # Обычный клик при ошибке
                                try:
                                    x = random.randint(200, 800)
                                    y = random.randint(200, 600)
                                    await page.mouse.click(x, y)
                                    logger.debug(f"🖱️ Fallback click at ({x}, {y}) after error: {str(click_error)[:30]}")
                                except Exception:
                                    logger.debug(f"🖱️ Click completely failed: {str(click_error)[:50]}")
                            
                    elif action == "hover_element":
                        # Реалистичное наведение на элементы
                        try:
                            hover_selectors = ["a", "button", "img", "div", "span", "p", "h1", "h2", "h3", "[title]"]
                            selector = random.choice(hover_selectors)
                            
                            try:
                                elements = await page.query_selector_all(selector)
                            except Exception as selector_error:
                                error_str = str(selector_error).lower()
                                if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                                    log_action("[WARN] Page closed during hover element search, stopping", "warning")
                                    break
                                else:
                                    # Обычное движение мыши
                                    x = random.randint(100, 900)
                                    y = random.randint(100, 700)
                                    await page.mouse.move(x, y)
                                    logger.debug(f"👆 Fallback mouse movement to ({x}, {y})")
                                    continue
                            
                            if elements:
                                element = random.choice(elements[:15])
                                try:
                                    is_visible = await element.is_visible()
                                    if is_visible:
                                        hover_time = random.uniform(0.8, 2.5)  # Более реалистичное время
                                        await element.hover(timeout=1000)
                                        await asyncio.sleep(hover_time)
                                        logger.debug(f"👆 Hovered over {selector} element for {hover_time:.1f}s")
                                    else:
                                        # Движение мыши как у пользователя
                                        x = random.randint(100, 900)
                                        y = random.randint(100, 700)
                                        await page.mouse.move(x, y)
                                        logger.debug(f"👆 Mouse moved to ({x}, {y})")
                                except Exception as hover_error:
                                    error_str = str(hover_error).lower()
                                    if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                                        log_action("[WARN] Page closed during hover action, stopping", "warning")
                                        break
                                    else:
                                        # Обычное движение мыши
                                        x = random.randint(100, 900)
                                        y = random.randint(100, 700)
                                        await page.mouse.move(x, y)
                                        logger.debug(f"👆 Fallback mouse movement after hover error")
                            else:
                                # Обычное движение мыши
                                x = random.randint(100, 900)
                                y = random.randint(100, 700)
                                await page.mouse.move(x, y)
                                logger.debug(f"👆 Random mouse movement to ({x}, {y})")
                        except Exception as e:
                            error_str = str(e).lower()
                            if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                                log_action("[WARN] Page closed during hover action, stopping", "warning")
                                break
                            else:
                                logger.debug(f"👆 Hover error: {str(e)[:50]}")
                            
                    elif action == "select_text":
                        # Реалистичное выделение текста (пользователь читает)
                        try:
                            text_selectors = ["p", "span", "div", "h1", "h2", "h3", "a", "li"]
                            selector = random.choice(text_selectors)
                            
                            try:
                                text_elements = await page.query_selector_all(selector)
                            except Exception as selector_error:
                                error_str = str(selector_error).lower()
                                if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                                    log_action("[WARN] Page closed during text selection search, stopping", "warning")
                                    break
                                else:
                                    logger.debug(f"[TEXT] Text selection search failed: {str(selector_error)[:50]}")
                                    continue
                            
                            if text_elements:
                                element = random.choice(text_elements[:15])
                                try:
                                    is_visible = await element.is_visible()
                                    
                                    if is_visible:
                                        text_content = await element.text_content()
                                        if text_content and len(text_content.strip()) > 3:
                                            # Реалистичное выделение текста
                                            await element.click(click_count=3, timeout=1000)
                                            selection_time = random.uniform(0.5, 2.0)
                                            await asyncio.sleep(selection_time)
                                            
                                            # Снимаем выделение
                                            await page.mouse.click(random.randint(100, 200), random.randint(100, 200))
                                            logger.debug(f"[TEXT] Selected text for {selection_time:.1f}s (user reading)")
                                        else:
                                            logger.debug(f"[TEXT] Skipped text selection - no meaningful text")
                                    else:
                                        logger.debug(f"[TEXT] Skipped text selection - element not visible")
                                except Exception as text_error:
                                    error_str = str(text_error).lower()
                                    if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                                        log_action("[WARN] Page closed during text selection, stopping", "warning")
                                        break
                                    else:
                                        logger.debug(f"[TEXT] Text selection error: {str(text_error)[:50]}")
                            else:
                                logger.debug(f"[TEXT] No text elements found for selection")
                        except Exception as e:
                            error_str = str(e).lower()
                            if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                                log_action("[WARN] Page closed during text selection action, stopping", "warning")
                                break
                            else:
                                logger.debug(f"[TEXT] Text selection error: {str(e)[:50]}")
                            
                    elif action == "double_click":
                        # Реалистичный двойной клик (пользователь хочет что-то выделить/открыть)
                        try:
                            x = random.randint(200, 800)
                            y = random.randint(200, 600)
                            await page.mouse.dblclick(x, y)
                            logger.debug(f"🖱️ Double clicked at ({x}, {y}) (user action)")
                        except Exception as e:
                            error_str = str(e).lower()
                            if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                                log_action("[WARN] Page closed during double click, stopping", "warning")
                                break
                            else:
                                logger.debug(f"🖱️ Double click failed: {str(e)[:50]}")
                        
                    elif action == "wait":
                        # Просто ждем (как пользователь читает)
                        wait_time = min(random.uniform(1, 4), remaining_time)
                        time.sleep(wait_time)
                        logger.debug(f"[PAUSE] Reading pause for {wait_time:.1f} seconds")
                    
                    actions_performed += 1
                    
                    # Иногда делаем короткие паузы между действиями
                    if random.random() < 0.4:
                        mini_pause = random.uniform(0.2, 0.8)
                        time.sleep(mini_pause)
                    
                except Exception as e:
                    # Проверяем, связана ли ошибка с закрытием страницы
                    error_str = str(e).lower()
                    if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                        log_action(f"[WARN] Page closed during {action}, stopping simulation", "warning")
                        break
                    else:
                        logger.debug(f"[WARN] Error during {action}: {str(e)[:100]}")
                        continue
            
            # Финальная статистика - только важная информация
            total_time = time.time() - start_time
            log_action(f"🎭 Simulation complete! {actions_performed} actions in {total_time:.1f}s", "info")
            
            # Логируем только основные статистики
            main_actions = {k: v for k, v in action_stats.items() if v > 0}
            if main_actions:
                stats_summary = ", ".join([f"{k}: {v}" for k, v in main_actions.items()])
                log_action(f"📊 Main actions: {stats_summary}", "info")
            
        except Exception as e:
            log_action(f"[WARN] Critical error in user activity simulation: {str(e)}", "warning")

    def run_cookie_robot_sync(
        self,
        profile_id: Union[str, int],
        urls: List[str],
        headless: bool = False,
        imageless: bool = False,
        duration: int = 300,
        poll_interval: int = 5,
        task_logger=None
    ) -> Dict[str, Any]:
        """
        Synchronous Cookie Robot implementation - используем subprocess для полной изоляции на Windows
        """
        if not urls:
            return {"success": False, "error": "No URLs provided"}
        
        try:
            import platform
            import subprocess
            import json
            import tempfile
            import os
            
            logger.info(f"[START] Starting Cookie Robot sync for profile {profile_id} via subprocess")
            
            # Создаем временный файл для передачи параметров
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                params = {
                    'profile_id': profile_id,
                    'urls': urls,
                    'headless': headless,
                    'imageless': imageless,
                    'duration': duration,
                    'api_key': self.api_key,
                    'local_api_base': self.local_api_base
                }
                json.dump(params, temp_file)
                temp_file_path = temp_file.name
            
            try:
                # Запускаем изолированный скрипт
                script_path = os.path.join(os.path.dirname(__file__), 'isolated_cookie_robot.py')
                
                # Для Windows используем полный путь к Python
                python_exe = get_python_executable()
                
                cmd = [python_exe, script_path, temp_file_path]
                
                logger.info(f"[PROCESS] Running subprocess: {' '.join(cmd)}")
                
                # Запускаем subprocess с увеличенным таймаутом
                # Увеличиваем таймаут до 20 минут, чтобы Cookie Robot мог пройти все сайты
                # Даже если некоторые сайты медленные или зависают
                timeout = max(duration + 900, 1200)  # Минимум 20 минут
                
                try:
                    # Используем Windows-совместимый subprocess
                    # Ensure isolated mode env so that logs go to stderr
                    env = os.environ.copy()
                    env['COOKIE_ROBOT_ISOLATED'] = '1'
                    env['FORCE_LOG_TO_STDERR'] = '1'
                    result = run_subprocess_windows(
                        cmd,
                        timeout=timeout,
                        cwd=os.getcwd()
                    )
                except subprocess.TimeoutExpired:
                    logger.error(f"[FAIL] Subprocess timeout after {timeout} seconds")
                    # Принудительно завершаем subprocess
                    try:
                        import psutil
                        # Ищем и завершаем все дочерние процессы
                        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                            try:
                                if any('isolated_cookie_robot.py' in str(arg) for arg in proc.info['cmdline'] or []):
                                    logger.info(f"[PROCESS] Force killing subprocess {proc.info['pid']}")
                                    proc.terminate()
                                    proc.wait(timeout=5)
                            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                                pass
                    except ImportError:
                        logger.warning("[WARN] psutil not available, cannot force kill subprocess")
                    
                    return {"success": False, "error": f"Subprocess timeout after {timeout} seconds - Cookie Robot took too long to complete"}
                except Exception as e:
                    logger.error(f"[FAIL] Subprocess execution error: {str(e)}")
                    return {"success": False, "error": f"Subprocess execution error: {str(e)}"}
                
                # Обрабатываем результат subprocess
                if result.returncode == 0:
                    # We expect stdout to contain only JSON; stderr contains logs
                    stdout_text = result.stdout or ''
                    stderr_text = result.stderr or ''
                    try:
                        stdout_clean = (stdout_text or '').strip()
                        if not stdout_clean:
                            logger.error("[FAIL] Subprocess returned empty stdout")
                            logger.error(f"Stderr: {stderr_text[:1000]}")
                            return {"success": False, "error": "Subprocess returned empty stdout"}
                        # Strict parse first
                        return json.loads(stdout_clean)
                    except json.JSONDecodeError as e:
                        logger.error(f"[ERROR] Failed to parse subprocess stdout as JSON: {e}")
                        logger.error(f"[DEBUG] Stdout (first 500): {stdout_text[:500]}")
                        logger.error(f"[DEBUG] Stderr (first 500): {stderr_text[:500]}")
                        
                        # Attempt to extract JSON object from stdout or stderr
                        import re
                        json_candidate = None
                        for text in (stdout_text, stderr_text):
                            try:
                                start_idx = text.find('{')
                                end_idx = text.rfind('}')
                                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                                    candidate = text[start_idx:end_idx+1]
                                    # Validate
                                    json_candidate = json.loads(candidate)
                                    break
                            except Exception:
                                pass
                        if json_candidate is not None:
                            logger.info(f"[OK] Successfully parsed JSON from mixed output")
                            return json_candidate
                        
                        # Regex fallback for nested braces
                        try:
                            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                            for text in (stdout_text, stderr_text):
                                matches = re.findall(json_pattern, text)
                                if matches:
                                    longest_match = max(matches, key=len)
                                    return json.loads(longest_match)
                        except Exception as cleanup_error:
                            logger.error(f"[ERROR] Regex JSON parsing failed: {cleanup_error}")
                        
                        # Final fallback
                        return {"success": False, "error": f"Failed to parse subprocess output: {str(e)}"}
                else:
                    # Non-zero return code; still attempt to parse stdout JSON for partial data
                    stdout_text = result.stdout or ''
                    stderr_text = result.stderr or ''
                    try:
                        if stdout_text.strip():
                            return json.loads(stdout_text.strip())
                    except Exception:
                        pass
                    # Return error with diagnostics
                    return {
                        "success": False,
                        "error": f"Subprocess returned code {result.returncode}",
                        "data": {
                            "stdout_head": stdout_text[:300],
                            "stderr_head": stderr_text[:300]
                        }
                    }
            finally:
                # Cleanup temp parameters file
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"[FAIL] Error in run_cookie_robot_sync: {str(e)}")
            return {"success": False, "error": str(e)}

    def _simulate_user_activity_sync(self, page, duration, urls, task_logger=None):
        """УСТАРЕВШИЙ МЕТОД - теперь используется run_cookie_robot_sync с изоляцией"""
        # Этот метод больше не используется, так как логика перенесена в изолированный subprocess
        return {"success": False, "error": "This method is deprecated, use run_cookie_robot_sync instead"}

    def check_dolphin_status(self) -> Dict[str, Any]:
        """
        Check if Dolphin Anty application is running and responsive
        Returns status information
        """
        status = {
            "app_running": False,
            "local_api_available": False,
            "authenticated": False,
            "error": None
        }
        
        try:
            # Check if local API is responding by trying to authenticate
            logger.info("[SEARCH] Checking Dolphin Anty application status...")
            
            auth_data = {"token": self.api_key}
            response = requests.post(
                f"{self.local_api_base}/auth/login-with-token",
                headers={"Content-Type": "application/json"},
                json=auth_data,
                timeout=5
            )
            
            if response.status_code == 200:
                status["app_running"] = True
                status["local_api_available"] = True
                status["authenticated"] = True
                logger.info("[OK] Dolphin Anty application is running and responsive")
            elif response.status_code == 401:
                status["app_running"] = True
                status["local_api_available"] = True
                status["authenticated"] = False
                status["error"] = "Invalid API token"
                logger.error("[FAIL] Dolphin Anty is running but API token is invalid")
            elif response.status_code == 404:
                status["app_running"] = True
                status["local_api_available"] = False
                status["error"] = "API endpoint not found - check Dolphin version"
                logger.error("[FAIL] Dolphin Anty is running but API endpoint not found")
            else:
                status["app_running"] = True
                status["local_api_available"] = False
                status["error"] = f"Unexpected HTTP {response.status_code}"
                logger.error(f"[FAIL] Dolphin Anty API returned HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            status["error"] = "Connection refused - Dolphin Anty not running"
            logger.error("[FAIL] Cannot connect to Dolphin Anty - application not running")
        except requests.exceptions.Timeout:
            status["error"] = "Timeout connecting to Dolphin Anty"
            logger.error("[FAIL] Timeout connecting to Dolphin Anty")
        except Exception as e:
            status["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"[FAIL] Unexpected error checking Dolphin status: {e}")
        
        return status

    def _resolve_accept_language(self, profile_id: Union[str, int]) -> Optional[str]:
        """Resolve Accept-Language header value from Dolphin profile locale/language if available."""
        try:
            prof = self.get_profile(profile_id)
            # Profile data can be nested in different ways; try several paths
            data = prof.get('data', prof)
            # Try to extract locale or language value
            locale_val = None
            def _val(obj, key):
                try:
                    v = obj.get(key)
                    if isinstance(v, dict):
                        return v.get('value') or v.get('lang') or v.get('locale')
                    return v
                except Exception:
                    return None
            locale_val = _val(data, 'locale') or _val(data, 'language')
            if not locale_val and isinstance(data, dict):
                # Sometimes profile is under 'browserProfile'
                bp = data.get('browserProfile') or {}
                locale_val = _val(bp, 'locale') or _val(bp, 'language')
            # If no locale found, fallback to ru_BY mapping
            if not locale_val or not isinstance(locale_val, str):
                return 'ru-BY,ru;q=0.9,en-US;q=0.8,en;q=0.7'
            return self._accept_language_for_locale_str(locale_val)
        except Exception:
            # Robust fallback
            return 'ru-BY,ru;q=0.9,en-US;q=0.8,en;q=0.7'

    def _accept_language_for_locale_str(self, locale_str: str) -> str:
        """Map a locale string like 'ru_BY' or 'en-US' to an Accept-Language header value."""
        try:
            norm = (locale_str or '').strip().replace('_', '-')
            lv = norm.lower()
            # Consolidate all Russian locales to ru-BY policy per project requirement
            if lv.startswith('ru-by') or lv.startswith('ru'):
                return 'ru-BY,ru;q=0.9,en-US;q=0.8,en;q=0.7'
            if lv.startswith('en-in'):
                return 'en-IN,en;q=0.9'
            if lv.startswith('en-us') or lv.startswith('en'):
                return 'en-US,en;q=0.9'
            if lv.startswith('pt-br') or lv.startswith('pt'):
                return 'pt-BR,pt;q=0.9,en-US;q=0.7,en;q=0.6'
            # Generic fallback using the detected locale
            base = norm if norm else 'ru-BY'
            primary = (base.split('-')[0] if '-' in base else base) or 'ru'
            return f"{base},{primary};q=0.9,en-US;q=0.8,en;q=0.7"
        except Exception:
            return 'ru-BY,ru;q=0.9,en-US;q=0.8,en;q=0.7'

    # ===== Proxy selection helpers =====
    def _country_from_locale(self, locale: Optional[str]) -> Optional[str]:
        """Extract ISO2 country code from locale string like 'ru_BY' or 'en-US'."""
        try:
            if not locale:
                return None
            norm = locale.replace('_', '-')
            parts = norm.split('-')
            if len(parts) >= 2 and len(parts[1]) == 2:
                return parts[1].upper()
            # Common explicit mappings
            mapping = {
                'ru_by': 'BY', 'ru-by': 'BY', 'ru_ru': 'RU', 'ru-ru': 'RU',
                'en_us': 'US', 'en-us': 'US', 'en_in': 'IN', 'en-in': 'IN',
                'es_cl': 'CL', 'es-cl': 'CL', 'es_mx': 'MX', 'es-mx': 'MX',
                'pt_br': 'BR', 'pt-br': 'BR',
            }
            key = norm.lower()
            return mapping.get(key)
        except Exception:
            return None

    def _extract_country_from_proxy(self, proxy: Dict[str, Any]) -> Optional[str]:
        """Best-effort extraction of country code from proxy metadata."""
        try:
            for key in ['country', 'countryCode', 'cc', 'iso', 'iso2']:
                val = proxy.get(key)
                if isinstance(val, str) and len(val.strip()) >= 2:
                    return val.strip().upper()[:2]
            # Try region text
            region = (proxy.get('region') or proxy.get('location') or '')
            if isinstance(region, str) and 'belarus' in region.lower():
                return 'BY'
        except Exception:
            pass
        return None

    def _is_proxy_available(self, proxy: Dict[str, Any]) -> bool:
        """Heuristic check if a proxy is marked available/free/active."""
        try:
            if isinstance(proxy.get('available'), bool):
                return proxy['available'] is True
            status = (proxy.get('status') or proxy.get('state') or '').lower()
            if status in {'free', 'available', 'idle', 'active', 'alive', 'working'}:
                return True
            return True  # default permissive if unknown
        except Exception:
            return True

    def _select_proxy_for_locale(self, locale: str, proxy_pool: List[Dict[str, Any]], mode: str = 'locale_only') -> Optional[Dict[str, Any]]:
        """Select a proxy from pool according to selection mode:
        - 'locale_only': pick only proxies whose country matches locale
        - 'any': pick randomly among available proxies
        Returns a proxy dict or None if not found.
        """
        try:
            candidates: List[Dict[str, Any]] = []
            pool = [p for p in proxy_pool if isinstance(p, dict)]
            if not pool:
                return None
            if (mode or '').lower() == 'any':
                candidates = [p for p in pool if self._is_proxy_available(p)] or pool
            else:
                target_country = self._country_from_locale(locale) or 'BY'
                for p in pool:
                    if not self._is_proxy_available(p):
                        continue
                    pc = self._extract_country_from_proxy(p)
                    if pc == target_country:
                        candidates.append(p)
            if not candidates:
                return None
            return random.choice(candidates)
        except Exception:
            return None

    def _geoip_lookup(self, proxy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Resolve proxy host to public geo-IP info. Returns dict with keys:
        country_code, region, city, latitude, longitude, timezone, ip.
        Caches results per host for the life of this instance.
        """
        try:
            host = (proxy or {}).get("host")
            if not host:
                return None
            if host in self._geoip_cache:
                return self._geoip_cache[host]

            # Resolve host to IP if hostname
            ip_str = None
            try:
                ipaddress.ip_address(host)
                ip_str = host
            except ValueError:
                try:
                    ip_str = socket.gethostbyname(host)
                except Exception:
                    ip_str = None

            if not ip_str:
                return None

            # Try ipapi.co
            info = None
            try:
                r = requests.get(f"https://ipapi.co/{ip_str}/json/", timeout=5)
                if r.status_code == 200:
                    j = r.json()
                    info = {
                        "ip": j.get("ip", ip_str),
                        "country_code": (j.get("country") or j.get("country_code") or "").upper(),
                        "region": j.get("region"),
                        "city": j.get("city"),
                        "latitude": j.get("latitude"),
                        "longitude": j.get("longitude"),
                        "timezone": j.get("timezone"),
                    }
            except Exception:
                info = None

            # Fallback ipwho.is
            if not info:
                try:
                    r = requests.get(f"https://ipwho.is/{ip_str}", timeout=5)
                    if r.status_code == 200:
                        j = r.json()
                        if j.get("success"):
                            info = {
                                "ip": j.get("ip", ip_str),
                                "country_code": (j.get("country_code") or "").upper(),
                                "region": j.get("region"),
                                "city": j.get("city"),
                                "latitude": j.get("latitude"),
                                "longitude": j.get("longitude"),
                                "timezone": j.get("timezone"),
                            }
                except Exception:
                    info = None

            # Normalize timezone field to string ID if possible
            try:
                if info and isinstance(info.get("timezone"), dict):
                    tz_obj = info.get("timezone")
                    tz_str = tz_obj.get("id") or tz_obj.get("name") or tz_obj.get("timezone")
                    info["timezone"] = tz_str or "Europe/Minsk"
            except Exception:
                pass

            if info:
                self._geoip_cache[host] = info
            return info
        except Exception:
            return None

    # --- Cookies API helpers ---
    def get_cookies(self, profile_id: Union[str, int]) -> List[Dict[str, Any]]:
        """
        Return cookies using only the working Sync API method.
        """
        cookies = self.export_cookies(profile_id)
        if cookies:
            logger.info(f"[GET_COOKIES] Success! Got {len(cookies)} cookies for profile {profile_id}")
            return cookies
        logger.warning(f"[GET_COOKIES] No cookies found for profile {profile_id}")
        return []

    def export_cookies(self, profile_id: Union[str, int], timeout_seconds: int = 60) -> List[Dict[str, Any]]:
        """
        Exact sample from docs: GET with headers only.
        Increased timeout to 60 seconds for better reliability.
        Added retry logic with exponential backoff.
        """
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                url = f"{self.sync_api_base}/?actionType=getCookies&browserProfileId={profile_id}"
                token = self.api_key or os.environ.get("TOKEN") or os.environ.get("DOLPHIN_API_TOKEN")
                headers = {"Content-Type": "application/json"}
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                
                logger.info(f"[EXPORT_COOKIES] Attempt {attempt + 1}/{max_retries} for profile {profile_id}")
                res = requests.request("GET", url, headers=headers, timeout=timeout_seconds)
                res.raise_for_status()
                payload = res.json()
                if isinstance(payload, dict) and "data" in payload:
                    cookies_data = payload.get("data") or []
                    logger.info(f"[EXPORT_COOKIES] Success! Got {len(cookies_data)} cookies for profile {profile_id}")
                    return cookies_data
                if isinstance(payload, list):
                    logger.info(f"[EXPORT_COOKIES] Success! Got {len(payload)} cookies for profile {profile_id}")
                    return payload
                logger.warning(f"[EXPORT_COOKIES] Unexpected payload format for profile {profile_id}: {type(payload)}")
                return []
                
            except requests.exceptions.Timeout as e:
                logger.warning(f"[EXPORT_COOKIES] Timeout on attempt {attempt + 1}/{max_retries} for profile {profile_id}: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"[EXPORT_COOKIES] Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"[FAIL] export_cookies sync call failed for {profile_id} after {max_retries} attempts: {e}")
            except Exception as e:
                logger.error(f"[FAIL] export_cookies sync call failed for {profile_id}: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"[EXPORT_COOKIES] Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"[FAIL] export_cookies sync call failed for {profile_id} after {max_retries} attempts: {e}")
        return []

    def update_cookies(self, profile_id: Union[str, int], cookies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """PATCH cookies for a profile via Remote API (add/overwrite)."""
        try:
            resp = self._make_request(
                method="patch",
                endpoint=f"/browser_profiles/{profile_id}/cookies",
                json_data=cookies,
                headers={"Content-Type": "application/json"},
            )
            return resp if isinstance(resp, dict) else {"success": True}
        except Exception as e:
            logger.error(f"[FAIL] Failed to update cookies for profile {profile_id}: {e}")
            return {"success": False, "error": str(e)}

    def delete_cookies(self, profile_id: Union[str, int]) -> Dict[str, Any]:
        """DELETE all cookies for a profile via Remote API."""
        try:
            resp = self._make_request(
                method="delete",
                endpoint=f"/browser_profiles/{profile_id}/cookies",
            )
            return resp if isinstance(resp, dict) else {"success": True}
        except Exception as e:
            logger.error(f"[FAIL] Failed to delete cookies for profile {profile_id}: {e}")
            return {"success": False, "error": str(e)}

    def get_cookies_local_export(self, profile_id: Union[str, int], timeout_seconds: int = 60) -> List[Dict[str, Any]]:
        """
        Retrieve cookies for a browser profile via Local API export endpoint.
        Tries GET with query param, then POST with JSON body as fallback.
        """
        # Some Local API setups expect token in body instead of header. Try both strategies.
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        # Try GET first
        try:
            url = f"{self.local_api_base}/cookies/export"
            resp = requests.get(url, headers=headers, params={"profileId": profile_id}, timeout=timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "data" in data:
                return data.get("data") or []
            if isinstance(data, list):
                return data
        except Exception:
            pass
        # Try POST fallback
        try:
            url = f"{self.local_api_base}/cookies/export"
            headers_post = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            # Include Authorization in JSON body as some versions require
            body = {
                "profileId": profile_id,
                "Authorization": f"Bearer {self.api_key}",
            }
            # Optional: include explicit login/password if provided via env for local API
            local_login = os.environ.get("DOLPHIN_LOCAL_LOGIN") or os.environ.get("LOCAL_API_LOGIN")
            local_password = os.environ.get("DOLPHIN_LOCAL_PASSWORD") or os.environ.get("LOCAL_API_PASSWORD")
            if local_login and local_password:
                body.update({"login": local_login, "password": local_password})
            resp = requests.post(url, headers=headers_post, json=body, timeout=timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "data" in data:
                return data.get("data") or []
            if isinstance(data, list):
                return data
        except Exception as e:
            logger.error(f"[FAIL] Local export cookies failed for profile {profile_id}: {e}")
        return []

    def get_cookies_via_sync_api(self, profile_id: Union[str, int], timeout_seconds: int = 60) -> List[Dict[str, Any]]:
        """
        Fallback method - redirects to the working export_cookies method.
        """
        return self.export_cookies(profile_id, timeout_seconds)



    def import_cookies_local(
        self,
        profile_id: Union[str, int],
        cookies: List[Dict[str, Any]],
        transfer: int = 0,
        cloud_sync_disabled: bool = False,
        timeout_seconds: int = 20,
    ) -> Dict[str, Any]:
        """
        Import cookies into a profile using the Local API endpoint:
        POST {local_api_base}/cookies/import
        Body: {"cookies": [...], "profileId": id, "transfer": 0, "cloudSyncDisabled": false}
        """
        url = f"{self.local_api_base}/cookies/import"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "cookies": cookies or [],
            "profileId": profile_id,
            "transfer": transfer,
            "cloudSyncDisabled": bool(cloud_sync_disabled),
        }
        try:
            logger.info(f"[TOOL] Importing {len(cookies or [])} cookies to profile {profile_id} via Local API")
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except Exception:
                    data = {"success": True}
                logger.info(f"[OK] Cookies imported into profile {profile_id}")
                return data if isinstance(data, dict) else {"success": True}
            # If unauthorized or other error, try body-auth fallback
            local_login = os.environ.get("DOLPHIN_LOCAL_LOGIN") or os.environ.get("LOCAL_API_LOGIN")
            local_password = os.environ.get("DOLPHIN_LOCAL_PASSWORD") or os.environ.get("LOCAL_API_PASSWORD")
            headers_fallback = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            body = dict(payload)
            body["Authorization"] = f"Bearer {self.api_key}"
            if local_login and local_password:
                body.update({"login": local_login, "password": local_password})
            resp_fb = requests.post(url, headers=headers_fallback, json=body, timeout=timeout_seconds)
            if resp_fb.status_code == 200:
                try:
                    data = resp_fb.json()
                except Exception:
                    data = {"success": True}
                logger.info(f"[OK] Cookies imported (body-auth) into profile {profile_id}")
                return data if isinstance(data, dict) else {"success": True}
            logger.error(f"[FAIL] Local import cookies failed (HTTP {resp_fb.status_code}): {resp_fb.text[:200]}")
            return {"success": False, "error": f"HTTP {resp_fb.status_code}", "details": resp_fb.text}
        except Exception as e:
            logger.error(f"[FAIL] Exception during local cookies import: {e}")
            # Final fallback using low-level http.client to avoid any requests/SSL quirks
            try:
                headers_low = {
                    "Content-Type": "application/json",
                }
                body_low = dict(payload)
                body_low["Authorization"] = f"Bearer {self.api_key}"
                conn = http.client.HTTPConnection("127.0.0.1", 3001, timeout=timeout_seconds)
                conn.request("POST", "/v1.0/cookies/import", json.dumps(body_low), headers_low)
                resp_low = conn.getresponse()
                raw = resp_low.read()
                if resp_low.status == 200:
                    try:
                        data = json.loads(raw)
                    except Exception:
                        data = {"success": True}
                    logger.info(f"[OK] Cookies imported into profile {profile_id} (http.client fallback)")
                    return data if isinstance(data, dict) else {"success": True}
                logger.error(f"[FAIL] Local import cookies failed (HTTP {resp_low.status}): {raw[:200]}")
                return {"success": False, "error": f"HTTP {resp_low.status}", "details": raw[:200].decode(errors='ignore')}
            except Exception as ee:
                logger.error(f"[FAIL] http.client fallback error during local cookies import: {ee}")
                return {"success": False, "error": str(e)}