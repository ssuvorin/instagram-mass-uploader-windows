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
            '🔍': '[SEARCH]',
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
            '📋': '[LIST]',
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
            '🚨': '[ALERT]',
            '🔔': '[NOTIFICATION]',
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

# Create safe logger wrapper
logger = SafeLogger(logging.getLogger(__name__))

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
        "1920x1080", "2560x1440", "1366x768",
        "1440x900", "1536x864", "1680x1050"
    ]
    BROWSER_VERSIONS = ["133","134", "135", "136"]
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dolphin-anty-api.com",
        local_api_base: str = "http://localhost:3001/v1.0"
    ):
        self.api_key        = api_key
        self.base_url       = base_url.rstrip("/")
        self.local_api_base = local_api_base.rstrip("/")

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
        headers: Dict[str, Any] = None
    ) -> Any:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            url = endpoint
        else:
            url = f"{self.base_url}{endpoint}"

        hdrs = {"Authorization": f"Bearer {self.api_key}"}
        if headers:
            hdrs.update(headers)

        # For PATCH requests with proxy data, use form data (urlencoded)
        if method.lower() == "patch" and data and isinstance(data, dict) and any(key.startswith("proxy[") for key in data.keys()):
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
            resp = requests.request(method, url, params=params, data=data, headers=hdrs)
        elif headers and headers.get("Content-Type") == "application/x-www-form-urlencoded":
            resp = requests.request(method, url, params=params, data=data, headers=hdrs)
        else:
            resp = requests.request(method, url, params=params, json=data, headers=hdrs)

        resp.raise_for_status()
        return resp.json()


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
        resp = self._make_request("get", "/fingerprints/useragent", params=params)
        if resp and "data" in resp:
            ua = resp["data"]
            logger.info(f"[OK] Generated UA ({browser_version}): {ua[:40]}…")
            return ua
        logger.error(f"[FAIL] UA generation failed: {resp}")
        return None

    def generate_webgl_info(self,
                             os_platform: str,
                             browser_version: str) -> Optional[Dict[str, Any]]:
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

        # отладочный лог
        logger.error(f"[FAIL] WebGL parsing failed, payload was: {json.dumps(payload)}")
        return None

    def create_profile(
        self,
        name: str,
        proxy: Dict[str, Any],
        tags: List[str]
    ) -> Dict[str, Any]:
        """
        Create a fully randomized Dolphin Anty browser profile payload,
        with manual modes and Russian localization.
        """
        # 1) Proxy is required
        if not proxy:
            return {"success": False, "error": "Proxy configuration is required"}

        # 2) Choose OS and browser version
        os_plat     = self.OS_PLATFORMS[0]
        browser_ver = random.choice(self.BROWSER_VERSIONS)

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
        webrtc_mode  = random.choice(["off", "real", "altered", "manual"])
        # canvas_mode  = random.choice(["off", "real", "noise"])
        webgl_mode   = "noise"
        webgl_info_mode = "manual"
        cpu_mode     = "manual"
        mem_mode     = "manual"
        cpu_value    = random.choice([2,4,8,16]) 
        mem_value    = random.choice([2,4,8,16,32,64,128])
        
        # 6) Randomize MAC address (manual)
        def random_mac():
            return ":".join(f"{random.randint(0,255):02X}" for _ in range(6))
        mac_mode = random.choice(["off","manual"])
        mac_payload: Dict[str, Any] = {"mode": mac_mode}
        if mac_mode == "manual":
            mac_payload["value"] = random_mac()
        
        # 7) Randomize DeviceName (manual)
        dev_mode = random.choice(["off","manual"])
        dev_payload: Dict[str, Any] = {"mode": dev_mode}
        if dev_mode == "manual":
            # e.g. DESKTOP-XXXXXXX
            suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
            dev_payload["value"] = f"DESKTOP-{suffix}"

        # 8) Randomize Fonts
        fonts_mode = random.choice(["auto","manual"])
        fonts_payload: Dict[str, Any] = {"mode": fonts_mode}
        if fonts_mode == "manual":
            # pick a few common fonts
            sample_fonts = ["Arial","Calibri","Times New Roman","Segoe UI","Verdana"]
            fonts_payload["value"] = random.sample(sample_fonts, k=random.randint(2, len(sample_fonts)))

        # 9) Randomize Audio
        audio_mode = random.choice(["real","noise"])
        audio_payload = {"mode": audio_mode}
        
        # 10) Randomize Timezone
        ru_timezones = [
            "Europe/Moscow", "Europe/Kaliningrad", "Europe/Samara",
            "Asia/Yekaterinburg", "Asia/Novosibirsk", "Asia/Irkutsk",
            "Asia/Yakutsk", "Asia/Vladivostok"
        ]
        tz_mode = random.choice(["auto", "manual"])
        tz_payload: Dict[str, Any] = {"mode": tz_mode}
        if tz_mode == "manual":
            tz_payload["value"] = random.choice(ru_timezones)

        # 11) Geolocation: auto or manual (Moscow coords if manual)
        geo_mode = random.choice(["auto", "manual"])
        geo_payload: Dict[str, Any] = {"mode": geo_mode}
        if geo_mode == "manual":
            geo_payload.update({"latitude": 55.7558, "longitude": 37.6173})

        # 12) Build payload
        payload: Dict[str, Any] = {
            "name":            name,
            "tags":            tags,
            "platform":        os_plat,
            "platformVersion": plat_ver,
            "mainWebsite":     random.choice(["google", "facebook", "crypto", "tiktok"]),
            "browserType":     "anty",

            "useragent": {
                "mode":  "manual",
                "value": ua
            },

            "webrtc": {
                "mode":     webrtc_mode,
                **({"ipAddress": proxy["host"]} if webrtc_mode == "manual" else {})
            },

            "canvas": {
                "mode": 'noise'
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
            "locale":      {"mode": "manual", "value": "ru_RU"},
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
            "doNotTrack":   random.choice([0,1]),

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
        try:
            resp = self._make_request("post", "/browser_profiles", data=payload)
        except DolphinAntyAPIError as e:
            logger.error(f"[FAIL] Profile creation failed: {e.message}")
            return {"success": False, "error": e.message}

        # 14) Log result
        if resp and ("browserProfileId" in resp or resp.get("data", {}).get("id")):
            logger.info(f"[OK] Profile created: {resp}")
        else:
            logger.error(f"[FAIL] Profile creation failed: {resp}")

        return resp

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

    def create_profile_for_account(self, account_data: Dict[str, Any], proxy_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Create a profile specifically configured for an Instagram account
        Returns the profile ID if successful, None otherwise
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
        response = self.create_profile(name=name, proxy=proxy_data, tags=tags)
        
        # Extract profile ID from response
        profile_id = None
        if response and isinstance(response, dict):
            # Check different possible locations for profile ID
            profile_id = response.get("browserProfileId")
            if not profile_id and "data" in response and isinstance(response["data"], dict):
                profile_id = response["data"].get("id")
        
        if profile_id:
            logger.info(f"[OK] Successfully created profile for {username}: {profile_id}")
            return profile_id
        else:
            logger.error(f"[FAIL] Failed to create profile for {username}")
            return None

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
        logger.info(f"🔍 [Step 1/3] Checking Dolphin Anty local API availability...")
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
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            
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
                        return False, None
                except json.JSONDecodeError:
                    logger.error(f"[FAIL] Invalid JSON response from Dolphin API: {resp.text[:200]}")
                    return False, None
            elif resp.status_code == 404:
                logger.error(f"[FAIL] Profile {profile_id} not found (HTTP 404)")
                logger.error("💡 The profile may have been deleted from Dolphin Anty or doesn't exist")
                return False, None
            elif resp.status_code == 400:
                logger.error(f"[FAIL] Bad request (HTTP 400): {resp.text[:200]}")
                logger.error("💡 Check if profile is already running or has invalid configuration")
                return False, None
            else:
                logger.error(f"[FAIL] Start profile failed with HTTP {resp.status_code}: {resp.text[:200]}")
                return False, None
                
        except requests.exceptions.Timeout:
            logger.error(f"[FAIL] Timeout (30s) starting profile {profile_id}")
            logger.error("💡 Profile may be taking too long to start, try again later")
            return False, None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[FAIL] Connection error starting profile {profile_id}: {e}")
            logger.error("💡 Make sure Dolphin Anty application is running")
            return False, None
        except requests.exceptions.RequestException as e:
            logger.error(f"[FAIL] Request error starting profile {profile_id}: {e}")
            return False, None
        except Exception as e:
            logger.error(f"[FAIL] Unexpected error starting profile {profile_id}: {e}")
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
            
            log_action("🔍 Checking for human verification dialog...", "info")
            
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
                    'button:has-text("Continue")'
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
                    log_action(f"🔍 Verification dialog text sample: {verification_text_sample}", "error")
                    
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
        
        try:
            logger.info(f"[RETRY] Starting Dolphin profile {profile_id}...")
            if task_logger:
                task_logger(f"[RETRY] Starting Dolphin profile {profile_id}...")
            
            # Debug: check Dolphin status before starting profile
            dolphin_status = self.check_dolphin_status()
            logger.info(f"🔍 Dolphin status before starting profile: {dolphin_status}")
            if task_logger:
                task_logger(f"🔍 Dolphin status: {dolphin_status}")
            
            success, profile_data = self.start_profile(profile_id, headless=headless)
            profile_started = success
            automation_data = profile_data
            
            logger.info(f"[RETRY] Profile start result - Success: {success}, Data: {profile_data}")
            if task_logger:
                task_logger(f"[RETRY] Profile start result - Success: {success}")
            
            if success and automation_data:
                logger.info(f"[OK] Profile {profile_id} started successfully")
                logger.info(f"🔗 Automation data: {automation_data}")
                if task_logger:
                    task_logger(f"[OK] Profile {profile_id} started successfully")
            else:
                logger.error(f"[FAIL] Could not start profile {profile_id} or get automation data")
                logger.error(f"[FAIL] Success: {success}, Profile data: {profile_data}")
                if task_logger:
                    task_logger(f"[FAIL] Failed to start profile {profile_id}")
                    task_logger(f"[FAIL] Success: {success}, Profile data: {profile_data}")
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
            logger.info(f"🌐 Connecting to browser via: {ws_url}")
            
            async with async_playwright() as p:
                # Подключаемся к уже запущенному браузеру
                browser = await p.chromium.connect_over_cdp(ws_url)
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
                    
                    # Создаем новую страницу
                    page = await context.new_page()
                    
                    
                        
                    # Cookie Robot - сразу переходим к основной логике набивания куков
                    log_action("Starting Cookie Robot - focusing on cookie collection...", "info")
                    
                    # 4) Запускаем собственно Cookie Robot на заданных URLs
                    # Настройки для imageless режима
                    if imageless:
                        await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico}", lambda route: route.abort())
                        logger.info(f"[BLOCK] Images blocked (imageless mode)")
                    
                    successful_visits = 0
                    failed_visits = 0
                    
                    # Рандомизируем порядок URL для более естественного поведения
                    shuffled_urls = urls.copy()
                    random.shuffle(shuffled_urls)
                    
                    if task_logger:
                        task_logger(f"🔀 URL order randomized for natural behavior")
                        task_logger(f"📋 Processing {len(shuffled_urls)} URLs")
                        task_logger(f"⏱️ Total duration: {duration} seconds")
                        task_logger(f"[TARGET] Starting Cookie Robot simulation...")
                    
                    # Обходим каждый URL
                    for i, url in enumerate(shuffled_urls, 1):
                        try:
                            if task_logger:
                                task_logger(f"[RETRY] [{i}/{len(shuffled_urls)}] Starting: {url}")
                            
                            # Убеждаемся, что у нас есть рабочая страница перед каждым URL
                            try:
                                page = await self._ensure_page_available(context, page, imageless, task_logger)
                            except Exception as page_error:
                                logger.error(f"[FAIL] Cannot ensure page availability for URL {i}/{len(shuffled_urls)}: {url}")
                                logger.error(f"[EXPLODE] Page recovery failed: {str(page_error)}")
                                
                                if task_logger:
                                    task_logger(f"[FAIL] [{i}/{len(shuffled_urls)}] Page recovery failed for: {url}")
                                    task_logger(f"[EXPLODE] Error: {str(page_error)}")
                                
                                failed_visits += 1
                                continue
                            
                            # Убираем избыточные логи о каждом URL
                            logger.debug(f"🌐 Visiting URL {i}/{len(shuffled_urls)}: {url}")
                            
                            if task_logger:
                                task_logger(f"🌐 [{i}/{len(shuffled_urls)}] Navigating to: {url}")
                            
                            # Переходим на страницу с улучшенной обработкой ошибок
                            navigation_success = False
                            max_nav_attempts = 3
                            
                            for attempt in range(max_nav_attempts):
                                try:
                                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                                    navigation_success = True
                                    break
                                    
                                except Exception as nav_error:
                                    error_str = str(nav_error).lower()
                                    
                                    # Если страница была закрыта или контекст потерян
                                    if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                                        logger.warning(f"[WARN] Navigation attempt {attempt + 1}/{max_nav_attempts} failed due to page/context loss: {url}")
                                        
                                        if task_logger:
                                            task_logger(f"[WARN] [{i}/{len(shuffled_urls)}] Navigation attempt {attempt + 1}/{max_nav_attempts} failed")
                                        
                                        if attempt < max_nav_attempts - 1:  # Не последняя попытка
                                            try:
                                                # Пытаемся восстановить страницу
                                                page = await self._ensure_page_available(context, page, imageless, task_logger)
                                                logger.debug(f"[RETRY] Page recovered, retrying navigation to: {url}")
                                                continue
                                            except Exception as recovery_error:
                                                logger.error(f"[FAIL] Page recovery failed on attempt {attempt + 1}: {str(recovery_error)}")
                                                break
                                        else:
                                            logger.error(f"[FAIL] All navigation attempts failed for: {url}")
                                            break
                                    else:
                                        # Другая ошибка навигации
                                        logger.error(f"[FAIL] Navigation error (attempt {attempt + 1}/{max_nav_attempts}): {str(nav_error)}")
                                        if attempt == max_nav_attempts - 1:
                                            raise nav_error
                                        await asyncio.sleep(1)  # Небольшая пауза перед повтором
                            
                            if not navigation_success:
                                failed_visits += 1
                                logger.error(f"[FAIL] Failed to navigate to {url} after {max_nav_attempts} attempts")
                                
                                if task_logger:
                                    task_logger(f"[FAIL] [{i}/{len(shuffled_urls)}] Navigation failed after {max_nav_attempts} attempts: {url}")
                                
                                continue
                            
                            # Случайная задержка для имитации человеческого поведения
                            base_duration = duration / len(shuffled_urls)
                            random_delay = random.uniform(base_duration * 0.8, base_duration * 1.2)
                            
                            # Убираем избыточные логи о времени
                            logger.debug(f"[WAIT] Staying on {url} for {random_delay:.1f} seconds")
                            
                            if task_logger:
                                task_logger(f"[WAIT] [{i}/{len(shuffled_urls)}] Simulating user activity for {random_delay:.1f} seconds")
                            
                            # Имитируем активность пользователя с улучшенной обработкой ошибок
                            try:
                                await self._simulate_user_activity(page, random_delay, task_logger)
                            except Exception as activity_error:
                                error_str = str(activity_error).lower()
                                
                                if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                                    logger.warning(f"[WARN] User activity stopped due to page/context loss: {str(activity_error)}")
                                    
                                    if task_logger:
                                        task_logger(f"[WARN] [{i}/{len(shuffled_urls)}] User activity interrupted by page closure")
                                    
                                    # Пытаемся восстановить страницу для следующего URL
                                    try:
                                        page = await self._ensure_page_available(context, page, imageless, task_logger)
                                        logger.debug(f"[RETRY] Page recovered after activity interruption")
                                    except Exception as recovery_error:
                                        logger.error(f"[FAIL] Failed to recover page after activity interruption: {str(recovery_error)}")
                                        # Продолжаем с текущей страницей (может быть None)
                                else:
                                    logger.warning(f"[WARN] Non-critical error in user activity simulation: {str(activity_error)}")
                            
                            successful_visits += 1
                            logger.info(f"[OK] Successfully processed {url}")
                            
                            if task_logger:
                                task_logger(f"[OK] [{i}/{len(shuffled_urls)}] Successfully completed: {url}")
                            
                            # Очищаем все вкладки кроме текущей после каждого сайта для оптимизации памяти
                            try:
                                all_pages = context.pages
                                if len(all_pages) > 1:
                                    logger.debug(f"🗂️ Cleaning up {len(all_pages)-1} extra tabs after visiting {url}")
                                    
                                    for p in all_pages:
                                        if p != page and not p.is_closed():
                                            try:
                                                await p.close()
                                                logger.debug(f"[FILE] Closed extra tab")
                                            except Exception as e:
                                                logger.warning(f"[WARN] Could not close extra tab: {str(e)}")
                                    
                                    if task_logger:
                                        task_logger(f"🗂️ Cleaned up extra tabs after: {url}")
                            except Exception as cleanup_error:
                                logger.warning(f"[WARN] Error during tab cleanup: {str(cleanup_error)}")
                            
                        except Exception as e:
                            failed_visits += 1
                            error_str = str(e).lower()
                            
                            logger.error(f"[FAIL] Error processing {url}: {str(e)}")
                            
                            if task_logger:
                                task_logger(f"[FAIL] [{i}/{len(shuffled_urls)}] Failed {url}: {str(e)}")
                            
                            # Если ошибка связана с потерей страницы/контекста, пытаемся восстановить
                            if any(keyword in error_str for keyword in ["page was closed", "target page", "context or browser has been closed"]):
                                try:
                                    logger.info(f"[RETRY] Attempting to recover page after error for next URL...")
                                    page = await self._ensure_page_available(context, page, imageless, task_logger)
                                    logger.info(f"[OK] Page recovered successfully after error")
                                    
                                    if task_logger:
                                        task_logger(f"[RETRY] Page recovered for next URL")
                                        
                                except Exception as recovery_error:
                                    logger.error(f"[FAIL] Failed to recover page after error: {str(recovery_error)}")
                                    
                                    if task_logger:
                                        task_logger(f"[EXPLODE] Page recovery failed, may affect remaining URLs")
                                    
                                    # Если восстановление не удалось, устанавливаем page в None
                                    # Функция _ensure_page_available попытается создать новую на следующей итерации
                                    page = None
                            
                            continue
                    
                    # Закрываем страницу после всех URL только если она еще открыта
                    try:
                        if not page.is_closed():
                            await page.close()
                            logger.debug(f"[FILE] Page closed after processing all URLs")
                        else:
                            logger.debug(f"[FILE] Page was already closed")
                    except Exception as close_error:
                        logger.warning(f"[WARN] Error closing main page: {str(close_error)}")
                    
                    # Закрываем все остальные вкладки перед завершением
                    try:
                        all_pages = context.pages
                        if all_pages:
                            logger.debug(f"🗂️ Found {len(all_pages)} pages/tabs total")
                            
                            for i, p in enumerate(all_pages):
                                try:
                                    if not p.is_closed():
                                        logger.debug(f"[FILE] Closing page/tab {i+1}/{len(all_pages)}")
                                        await p.close()
                                except Exception as e:
                                    logger.warning(f"[WARN] Could not close page {i+1}: {str(e)}")
                            
                            logger.debug(f"[OK] All pages/tabs closed successfully")
                        else:
                            logger.debug(f"[FILE] No pages to close")
                        
                        if task_logger:
                            task_logger(f"🗂️ Cleanup completed")
                            
                    except Exception as e:
                        logger.warning(f"[WARN] Error closing some pages: {str(e)}")
                        if task_logger:
                            task_logger(f"[WARN] Some tabs could not be closed: {str(e)[:100]}")
                    
                    # Закрываем контекст браузера
                    try:
                        await context.close()
                        logger.debug(f"🌐 Browser context closed")
                    except Exception as e:
                        logger.warning(f"[WARN] Error closing browser context: {str(e)}")
                    
                    # Результат выполнения
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
                    
                    logger.info(f"[OK] Cookie Robot completed: {successful_visits}/{len(shuffled_urls)} URLs processed successfully")
                    
                    if task_logger:
                        task_logger(f"[TARGET] Cookie Robot completed successfully!")
                        task_logger(f"📊 Results: {successful_visits}/{len(shuffled_urls)} URLs processed ({round((successful_visits / len(shuffled_urls)) * 100, 2)}% success rate)")
                    
                    return result
                    
                except asyncio.TimeoutError:
                    logger.error(f"[FAIL] Cookie Robot timeout during execution")
                    if task_logger:
                        task_logger(f"[FAIL] Cookie Robot timeout - forcing completion")
                    return {"success": False, "error": "Cookie Robot timeout during execution"}
                except Exception as e:
                    logger.error(f"[FAIL] Unexpected error in Cookie Robot: {str(e)}")
                    if task_logger:
                        task_logger(f"[FAIL] Unexpected error: {str(e)}")
                    return {"success": False, "error": f"Unexpected error in Cookie Robot: {str(e)}"}
                    
                finally:
                    # Отключаемся от браузера (не закрываем его)
                    if browser:
                        await browser.close()
                        logger.debug(f"🔌 Disconnected from browser")
                    
        except Exception as e:
            logger.error(f"[FAIL] Error during Playwright automation: {str(e)}")
            return {"success": False, "error": f"Playwright automation error: {str(e)}"}
            
        finally:
            # Останавливаем профиль только если мы его запустили
            if profile_started:
                logger.info(f"🛑 Stopping browser profile {profile_id}")
                self.stop_profile(profile_id)

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
                
                logger.info(f"[RETRY] Running subprocess: {' '.join(cmd)}")
                
                # Запускаем subprocess с увеличенным таймаутом
                # Увеличиваем таймаут до 20 минут, чтобы Cookie Robot мог пройти все сайты
                # Даже если некоторые сайты медленные или зависают
                timeout = max(duration + 900, 1200)  # Минимум 20 минут
                
                try:
                    # Используем Windows-совместимый subprocess
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
                                    logger.info(f"[RETRY] Force killing subprocess {proc.info['pid']}")
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
                    try:
                        # Очищаем stdout от возможных лишних символов
                        stdout_clean = result.stdout.strip()
                        
                        # Проверяем, что stdout не пустой
                        if not stdout_clean:
                            logger.error("[FAIL] Subprocess returned empty stdout")
                            logger.error(f"Stderr: {result.stderr}")
                            return {"success": False, "error": "Subprocess returned empty stdout"}
                        
                        # Дополнительная очистка - убираем все до первого '{'
                        json_start = stdout_clean.find('{')
                        if json_start != -1:
                            stdout_clean = stdout_clean[json_start:]
                        
                        # Парсим результат
                        output_data = json.loads(stdout_clean)
                        logger.info(f"[OK] Subprocess completed successfully")
                        return output_data
                    except json.JSONDecodeError as e:
                        logger.error(f"[FAIL] Failed to parse subprocess output: {e}")
                        logger.error(f"Raw stdout (first 500 chars): {result.stdout[:500]}")
                        logger.error(f"Raw stderr: {result.stderr}")
                        
                        # Попробуем найти JSON в stdout - более агрессивный поиск
                        try:
                            # Ищем начало JSON объекта
                            start_idx = result.stdout.find('{')
                            if start_idx != -1:
                                potential_json = result.stdout[start_idx:]
                                # Убираем все после последнего '}'
                                end_idx = potential_json.rfind('}')
                                if end_idx != -1:
                                    potential_json = potential_json[:end_idx+1]
                                output_data = json.loads(potential_json)
                                logger.info(f"[OK] Successfully parsed JSON after cleanup")
                                return output_data
                        except Exception as cleanup_error:
                            logger.error(f"[FAIL] JSON cleanup also failed: {cleanup_error}")
                        
                        # Последняя попытка - ищем любой валидный JSON в stdout
                        try:
                            import re
                            # Ищем JSON объект с помощью regex
                            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                            matches = re.findall(json_pattern, result.stdout)
                            if matches:
                                # Берем самый длинный match
                                longest_match = max(matches, key=len)
                                output_data = json.loads(longest_match)
                                logger.info(f"[OK] Successfully parsed JSON using regex fallback")
                                return output_data
                        except Exception as regex_error:
                            logger.error(f"[FAIL] Regex JSON parsing also failed: {regex_error}")
                        
                        # Если все попытки не удались, возвращаем ошибку с детальной диагностикой
                        logger.error(f"[FAIL] All JSON parsing attempts failed")
                        logger.error(f"[FAIL] Stdout length: {len(result.stdout)}")
                        logger.error(f"[FAIL] Stderr length: {len(result.stderr)}")
                        logger.error(f"[FAIL] First 100 chars of stdout: {repr(result.stdout[:100])}")
                        
                        return {"success": False, "error": f"Failed to parse subprocess output: {str(e)}"}
                else:
                    logger.error(f"[FAIL] Subprocess failed with return code {result.returncode}")
                    logger.error(f"Stdout: {result.stdout}")
                    logger.error(f"Stderr: {result.stderr}")
                    return {"success": False, "error": f"Subprocess failed: {result.stderr}"}
                
            except subprocess.TimeoutExpired:
                logger.error(f"[FAIL] Subprocess timeout after {timeout} seconds")
                return {"success": False, "error": f"Subprocess timeout after {timeout} seconds"}
            except Exception as e:
                logger.error(f"[FAIL] Subprocess execution error: {str(e)}")
                return {"success": False, "error": f"Subprocess execution error: {str(e)}"}
            finally:
                # Удаляем временный файл
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass
            
        except Exception as e:
            logger.error(f"[FAIL] Error in sync Cookie Robot: {str(e)}")
            return {"success": False, "error": f"Sync execution error: {str(e)}"}

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
            logger.info("🔍 Checking Dolphin Anty application status...")
            
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