import http.client
import json
import os
import random
import string
from typing import Dict, Union, List, Any, Optional

import requests

from tiktok_uploader.bot_integration import logger
from tiktok_uploader.bot_integration.dolphin.profile import Profile


class DolphinAntyAPIError(Exception):
    """Исключение для ошибок API Dolphin Anty"""

    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class Dolphin:
    # Константы для генерации профилей
    OS_PLATFORMS = ["windows"]  # Только Windows как в оригинальном коде

    BROWSER_VERSIONS = [
        "120.0.5845.96", "120.0.5845.97", "120.0.5845.110", "120.0.5845.111",
        "119.0.6045.105", "119.0.6045.123", "119.0.6045.124", "119.0.6045.159",
        "118.0.5993.70", "118.0.5993.88", "118.0.5993.117", "118.0.5993.159"
    ]

    def __init__(self):
        self.profiles: list[Profile] = []
        self.set_profiles()
        self.auth()

    def auth(self):
        conn = http.client.HTTPConnection("127.0.0.1", 3001)
        payload = json.dumps({
            "token": os.environ.get('TOKEN')
        })
        headers = {
            'Content-Type': 'application/json'
        }
        conn.request("POST", "/v1.0/auth/login-with-token", payload, headers)
        res = conn.getresponse()
        data = json.loads(res.read())
        if data['success'] == True:
            logger.info('Successfully logged into dolphin via token')
        else:
            logger.error('Failed to login into dolphin')

    def start_profiles(self):
        for profile in self.profiles:
            profile.start()

    def stop_profiles(self):
        for profile in self.profiles:
            profile.stop()

    def _get_profiles(self):
        result = requests.get(
            'https://dolphin-anty-api.com/browser_profiles?',
            headers={'Authorization': f'Bearer {os.environ.get("TOKEN")}'}
        )
        return result.json()

    def set_profiles(self):
        for i in self._get_profiles()['data']:
            self.profiles.append(
                Profile(id=i['id'], name=i['name'])
            )

    def get_profiles(self):
        return self.profiles

    def get_profile_by_name(self, name):
        for acc in self.get_profiles():
            if acc.name == name:
                return acc
        return False

    def delete_accounts(self):
        for profile in self.profiles:
            profile.delete_profile()
        self.profiles = []

    def make_profile(self, name, platform='windows', profile_data: str = '', proxy: Dict[str, Any] = None):
        """
        Создает профиль в Dolphin Anty. Если передан прокси, использует новую логику:
        1. Добавляет прокси в Dolphin
        2. Создает профиль без прокси
        3. Привязывает прокси к профилю
        """
        # Если передан прокси, используем новую логику через create_profile
        if proxy:
            logger.info(f"[MAKE_PROFILE] Using new proxy logic for profile {name}")
            result = self.create_profile(
                name=name,
                proxy=proxy,
                tags=[],
                locale="en_US"
            )

            if result.get("success", True):
                logger.info(f"[MAKE_PROFILE] Profile {name} created successfully with new logic")
                return json.dumps(result)
            else:
                logger.error(f"[MAKE_PROFILE] Failed to create profile {name} with new logic: {result.get('error')}")
                # Fallback к старой логике
                logger.info(f"[MAKE_PROFILE] Falling back to old logic for profile {name}")

        # Старая логика (без прокси или fallback)
        url = "https://dolphin-anty-api.com/browser_profiles"

        null = None
        false = False
        webgl = self.__get_WEBGLinfo(platform=platform)

        if profile_data == '':
            payload = json.dumps(
                {"name": name, "tags": [], "platform": platform, "browserType": "anty",
                 "mainWebsite": "https://tiktok.com",
                 "useragent": {"mode": "manual",
                               "value": self.__get_ua(platform)},
                 "webrtc": {"mode": "altered", "ipAddress": null}, "canvas": {"mode": "real"},
                 "webgl": {"mode": "real"},
                 "webglInfo": {"mode": "manual", "vendor": webgl['webglUnmaskedVendor'],
                               "renderer": webgl['webgl_unmasked_renderer']},
                 "webgpu": {"mode": "manual"}, "clientRect": {"mode": "real"},
                 "notes": {"content": null, "color": "blue", "style": "text", "icon": "info"},
                 "timezone": {"mode": "auto", "value": null}, "locale": {"mode": "manual", "value": "en"},
                 "statusId": 0,
                 "geolocation": {"mode": "auto", "latitude": null, "longitude": null, "accuracy": null},
                 "cpu": {"mode": "manual", "value": self.__get_random_cpu_and_ram()},
                 "memory": {"mode": "manual", "value": self.__get_random_cpu_and_ram()},
                 "screen": {"mode": "manual", "resolution": self.__get_random_resolution()}, "audio": {"mode": "real"},
                 "mediaDevices": {"mode": "real", "audioInputs": null, "videoInputs": null, "audioOutputs": null},
                 "ports": {"mode": "protect", "blacklist": "3389,5900,5800,7070,6568,5938"}, "doNotTrack": false,
                 "args": ["--start-maximized",
                          '--mute-audio',
                          '--lang=en'],
                 "platformVersion": "13.4.1", "uaFullVersion": "120.0.5845.96", "login": "", "password": "",
                 "appCodeName": "Mozilla", "platformName": platform, "connectionDownlink": 2.05,
                 "connectionEffectiveType": "4g", "connectionRtt": 150, "connectionSaveData": 0, "cpuArchitecture": "",
                 "osVersion": "10.15.7", "vendorSub": "", "productSub": "20030107", "vendor": "Google Inc.",
                 "product": "Gecko"})
        else:
            # Проверяем, не является ли profile_data результатом новой логики
            try:
                parsed_data = json.loads(profile_data)
                if isinstance(parsed_data, dict) and '_payload_used' in parsed_data:
                    payload = json.dumps(parsed_data['_payload_used'])
                else:
                    # Это результат новой логики - профиль уже создан
                    logger.info(f"[MAKE_PROFILE] Profile {name} already created with new logic, skipping creation")
                    return profile_data
            except:
                # Если не удается распарсить, используем как есть
                payload = profile_data

        headers = {
            'Authorization': f'Bearer {os.environ.get("TOKEN")}',
            'content-type': 'application/json'
        }

        res = requests.post(url, headers=headers, data=payload)

        if res.status_code == 200:
            result = res.json()
            logger.info(f'Profile {result['data']['id']} is set')
            self.profiles.append(
                Profile(id=result['data']['id'], name=name)
            )
            return payload
        else:
            logger.error(f"[MAKE_PROFILE] Failed to create profile {name}: {res.text}")
            print(res.text)

    def __get_ua(self, platform='windows'):
        url = f'https://dolphin-anty-api.com/fingerprints/useragent?browser_type=anty&browser_version=120&platform={platform}'
        headers = {
            'Authorization': f'Bearer {os.environ.get("TOKEN")}',
            'content-type': 'application/json'
        }
        res = requests.get(url, headers=headers)
        return res.json()['data']

    def __get_WEBGLinfo(self, platform='windows'):
        url = f'https://anty-api.com/fingerprints/webgl?browser_type=anty&browser_version=137&platform={platform}'
        headers = {
            'Authorization': f'Bearer {os.environ.get("TOKEN")}',
            'content-type': 'application/json'
        }
        res = requests.get(url, headers=headers)
        result = res.json()
        result['mode'] = "manual"
        return result

    def __get_random_cpu_and_ram(self):
        m = [2, 4, 6, 8, 12, 16]
        return random.choice(m)

    def __get_random_resolution(self):
        r = ["1920X1080", "1600X1200", "1920X1200"]
        return random.choice(r)

    def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Унифицированный метод для API запросов к Dolphin Anty"""
        url = f"https://dolphin-anty-api.com{endpoint}"
        headers = {
            'Authorization': f'Bearer {os.environ.get("TOKEN")}',
            'Content-Type': 'application/json'
        }

        try:
            if method.lower() == 'post':
                response = requests.post(url, headers=headers, json=data)
            elif method.lower() == 'get':
                response = requests.get(url, headers=headers, params=data)
            elif method.lower() == 'put':
                response = requests.put(url, headers=headers, json=data)
            elif method.lower() == 'delete':
                response = requests.delete(url, headers=headers)
            elif method.lower() == 'patch':
                response = requests.patch(url, headers=headers, json=data)
            else:
                raise DolphinAntyAPIError(f"Unsupported HTTP method: {method}")

            if response.status_code == 200:
                return response.json()
            else:
                try:
                    error_data = response.json()
                    error_msg = f"API request failed with status {response.status_code}: {json.dumps(error_data, indent=2)}"
                except:
                    error_msg = f"API request failed with status {response.status_code}: {response.text}"
                logger.error(f"[API ERROR] {method.upper()} {endpoint}: {error_msg}")
                raise DolphinAntyAPIError(error_msg, response.status_code)

        except requests.exceptions.RequestException as e:
            raise DolphinAntyAPIError(f"Network error: {str(e)}")

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
        url = f"http://localhost:3001/v1.0/cookies/import"
        headers = {
            "Authorization": f"Bearer {os.environ.get("TOKEN")}",
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
                # Post-validate by exporting cookies and checking key names
                validation = self.validate_profile_cookies(profile_id)
                if not validation.get("success"):
                    logger.error(
                        f"[FAIL] Cookies post-validation failed for profile {profile_id}: missing {validation.get('missing')}")
                    return {"success": False, "error": "post_validation_failed", "method": "local_api", **validation}
                logger.info(f"[OK] Cookies imported into profile {profile_id}")
                return {"success": True, "method": "local_api", "data": data, **validation}
            # If unauthorized or other error, try body-auth fallback
            local_login = os.environ.get("DOLPHIN_LOCAL_LOGIN") or os.environ.get("LOCAL_API_LOGIN")
            local_password = os.environ.get("DOLPHIN_LOCAL_PASSWORD") or os.environ.get("LOCAL_API_PASSWORD")
            headers_fallback = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            body = dict(payload)
            body["Authorization"] = f"Bearer {os.environ.get("TOKEN")}"
            if local_login and local_password:
                body.update({"login": local_login, "password": local_password})
            resp_fb = requests.post(url, headers=headers_fallback, json=body, timeout=timeout_seconds)
            if resp_fb.status_code == 200:
                try:
                    data = resp_fb.json()
                except Exception:
                    data = {"success": True}
                validation = self.validate_profile_cookies(profile_id)
                if not validation.get("success"):
                    logger.error(
                        f"[FAIL] Cookies post-validation failed for profile {profile_id}: missing {validation.get('missing')}")
                    return {"success": False, "error": "post_validation_failed", "method": "local_api_body",
                            **validation}
                logger.info(f"[OK] Cookies imported (body-auth) into profile {profile_id}")
                return {"success": True, "method": "local_api_body", "data": data, **validation}
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
                body_low["Authorization"] = f"Bearer {os.environ.get("TOKEN")}"
                conn = http.client.HTTPConnection("127.0.0.1", 3001, timeout=timeout_seconds)
                conn.request("POST", "/v1.0/cookies/import", json.dumps(body_low), headers_low)
                resp_low = conn.getresponse()
                raw = resp_low.read()
                if resp_low.status == 200:
                    try:
                        data = json.loads(raw)
                    except Exception:
                        data = {"success": True}
                    validation = self.validate_profile_cookies(profile_id)
                    if not validation.get("success"):
                        logger.error(
                            f"[FAIL] Cookies post-validation failed for profile {profile_id}: missing {validation.get('missing')}")
                        return {"success": False, "error": "post_validation_failed", "method": "http_client",
                                **validation}
                    logger.info(f"[OK] Cookies imported into profile {profile_id} (http.client fallback)")
                    return {"success": True, "method": "http_client", "data": data, **validation}
                logger.error(
                    f"[FAIL] Local import cookies failed (HTTP {resp_low.status}): {raw[:200].decode(errors='ignore')}")
                return {"success": False, "error": f"HTTP {resp_low.status}",
                        "details": raw[:200].decode(errors='ignore')}
            except Exception as ee:
                logger.error(f"[FAIL] http.client fallback error during local cookies import: {ee}")
                return {"success": False, "error": str(ee)}

    def validate_profile_cookies(self, profile_id: Union[str, int], required: Optional[set] = None) -> Dict[str, Any]:
        """
        Export cookies for profile and verify presence of key cookies.
        Returns dict with success, found, missing.
        """
        try:
            from src.dolphin.profile import Profile
            req = required or {"sessionid", "sessionid_ss", "tt_webid_v2", "tt_csrf_token"}
            temp_prof = Profile(id=profile_id, name=str(profile_id))
            exported = temp_prof.export_cookies() or []
            found = {c.get('name') for c in exported if c.get('name') in req}
            missing = list(req - found)
            return {"success": len(found) >= 2, "found": list(found), "missing": missing}
        except Exception as e:
            logger.warning(f"[COOKIES] validate_profile_cookies failed for {profile_id}: {e}")
            return {"success": False, "error": str(e)}

    def _check_profile_exists(self, profile_id: Union[str, int]) -> bool:
        """Проверяет, существует ли профиль"""
        try:
            headers = {
                'Authorization': f'Bearer {os.environ.get("TOKEN")}',
                'Content-Type': 'application/json'
            }

            response = requests.get(
                f"https://dolphin-anty-api.com/browser_profiles/{profile_id}",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                logger.debug(f"[COOKIES] Profile {profile_id} exists: {data.get('data', {}).get('name', 'Unknown')}")
                return True
            else:
                logger.warning(f"[COOKIES] Profile {profile_id} check failed: HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.warning(f"[COOKIES] Profile {profile_id} check error: {str(e)}")
            return True  # Предполагаем, что профиль существует, если не можем проверить

    def _import_cookies_web_api(self, profile_id: Union[str, int], cookies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Import cookies via Web API using the correct endpoint and method
        """
        try:
            # Пробуем несколько методов согласно документации
            methods = [
                # Метод 1: Прямой API endpoint для импорта куки
                {
                    "url": f"https://dolphin-anty-api.com/browser_profiles/{profile_id}/cookies",
                    "method": "POST",
                    "payload": cookies,
                    "name": "direct_api"
                },
                # Метод 2: Sync API с правильным actionType
                {
                    "url": f"https://sync.dolphin-anty-api.com/",
                    "method": "POST",
                    "payload": {
                        "actionType": "importCookies",
                        "browserProfileId": str(profile_id),
                        "data": cookies
                    },
                    "name": "sync_api_import"
                },
                # Метод 3: Альтернативный sync API
                {
                    "url": f"https://sync.dolphin-anty-api.com/",
                    "method": "POST",
                    "payload": {
                        "actionType": "updateCookies",
                        "browserProfileId": str(profile_id),
                        "cookies": cookies
                    },
                    "name": "sync_api_update"
                }
            ]

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {os.environ.get("TOKEN")}'
            }

            for method_config in methods:
                try:
                    logger.debug(f"[COOKIES] Trying {method_config['name']} for profile {profile_id}")

                    if method_config["method"] == "POST":
                        response = requests.post(
                            method_config["url"],
                            headers=headers,
                            json=method_config["payload"],
                            timeout=20
                        )
                    else:
                        response = requests.get(
                            method_config["url"],
                            headers=headers,
                            params=method_config["payload"],
                            timeout=20
                        )

                    logger.debug(f"[COOKIES] {method_config['name']} response: {response.status_code}")

                    if response.status_code == 200:
                        try:
                            result = response.json()
                            if result.get("success", True):
                                logger.info(
                                    f"[OK] Cookies imported via {method_config['name']} to profile {profile_id}")
                                return {"success": True, "method": f"web_api_{method_config['name']}", "data": result}
                            else:
                                error_msg = result.get("error", "Unknown error")
                                logger.warning(f"[FAIL] {method_config['name']} failed: {error_msg}")
                                continue
                        except json.JSONDecodeError:
                            # Если ответ не JSON, но статус 200, считаем успехом
                            logger.info(
                                f"[OK] Cookies imported via {method_config['name']} to profile {profile_id} (non-JSON response)")
                            return {"success": True, "method": f"web_api_{method_config['name']}"}
                    elif response.status_code == 422:
                        logger.warning(f"[FAIL] {method_config['name']} validation error: {response.text[:200]}")
                        continue
                    else:
                        logger.warning(
                            f"[FAIL] {method_config['name']} HTTP {response.status_code}: {response.text[:200]}")
                        continue

                except requests.exceptions.RequestException as e:
                    logger.warning(f"[FAIL] {method_config['name']} network error: {str(e)}")
                    continue
                except Exception as e:
                    logger.warning(f"[FAIL] {method_config['name']} unexpected error: {str(e)}")
                    continue

            # Если все методы не сработали
            return {"success": False, "error": "All Web API methods failed", "method": "web_api"}

        except Exception as e:
            logger.error(f"[FAIL] Web API cookies import critical error: {str(e)}")
            return {"success": False, "error": str(e), "method": "web_api"}

    def _import_cookies_local_api(
            self,
            profile_id: Union[str, int],
            cookies: List[Dict[str, Any]],
            transfer: int = 0,
            cloud_sync_disabled: bool = False
    ) -> Dict[str, Any]:
        """
        Import cookies via Local API (fallback method)
        """
        headers = {
            "Content-Type": "application/json",
        }
        payload = json.dumps({
            "cookies": cookies,
            "profileId": str(profile_id),  # Убеждаемся, что это строка
            "transfer": transfer,
            "cloudSyncDisabled": bool(cloud_sync_disabled),
        })

        try:
            logger.debug(f"[COOKIES] Local API request for profile {profile_id}")
            conn = http.client.HTTPConnection("127.0.0.1", 3001)
            conn.request("POST", "/v1.0/cookies/import", payload, headers)
            resp = conn.getresponse()
            response_data = resp.read()

            if resp.status == 200:
                try:
                    data = json.loads(response_data)
                    logger.debug(f"[COOKIES] Local API response data: {data}")

                    # Проверяем реальный результат импорта
                    if isinstance(data, dict):
                        if data.get("success") is False:
                            error_msg = data.get("error", "Unknown error from Local API")
                            logger.error(f"[FAIL] Local API cookies import failed: {error_msg}")
                            return {"success": False, "error": error_msg, "method": "local_api"}
                        elif "error" in data and data["error"]:
                            logger.error(f"[FAIL] Local API cookies import error: {data['error']}")
                            return {"success": False, "error": data["error"], "method": "local_api"}

                    logger.info(f"[OK] Cookies imported via Local API to profile {profile_id}")
                    return {"success": True, "method": "local_api", "data": data}
                except Exception as parse_error:
                    # Если не можем распарсить JSON, логируем сырой ответ
                    raw_response = response_data.decode('utf-8', errors='ignore')
                    logger.warning(f"[COOKIES] Local API non-JSON response: {raw_response[:200]}")

                    # Если в ответе есть слово "success" или "imported", считаем успехом
                    if any(word in raw_response.lower() for word in ["success", "imported", "ok"]):
                        logger.info(f"[OK] Cookies imported via Local API to profile {profile_id} (text response)")
                        return {"success": True, "method": "local_api", "raw_response": raw_response}
                    else:
                        logger.error(f"[FAIL] Local API cookies import unclear response: {raw_response}")
                        return {"success": False, "error": f"Parse error: {parse_error}", "method": "local_api"}
            else:
                error_msg = f"HTTP {resp.status}: {response_data.decode('utf-8', errors='ignore')[:200]}"
                logger.error(f"[FAIL] Local API cookies import failed: {error_msg}")
                return {"success": False, "error": error_msg, "method": "local_api"}

        except Exception as e:
            logger.error(f"[FAIL] Local API cookies import exception: {str(e)}")
            return {"success": False, "error": str(e), "method": "local_api"}

    def _geoip_lookup(self, proxy: Dict[str, Any]) -> Dict[str, Any]:
        """Получение GeoIP информации по прокси"""
        try:
            # Используем прокси для получения реальной геолокации
            proxy_url = f"http://{proxy.get('user', '')}:{proxy.get('pass', '')}@{proxy['host']}:{proxy['port']}"
            proxies = {"http": proxy_url, "https": proxy_url}

            # Запрос к ipwho.is через прокси
            response = requests.get("http://ipwho.is/", proxies=proxies, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success", True):  # ipwho.is возвращает success: true
                    return {
                        "ip": data.get("ip"),
                        "country_code": data.get("country_code"),
                        "timezone": data.get("timezone"),
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude")
                    }
        except Exception as e:
            logger.warning(f"GeoIP lookup failed: {str(e)}")

        return {}

    def generate_user_agent(self, os_platform: str, browser_version: str) -> str:
        """Генерация User-Agent строки"""
        try:
            url = f'https://dolphin-anty-api.com/fingerprints/useragent?browser_type=anty&browser_version={browser_version}&platform={os_platform}'
            headers = {
                'Authorization': f'Bearer {os.environ.get("TOKEN")}',
                'Content-Type': 'application/json'
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', '')
        except Exception as e:
            logger.error(f"User-Agent generation failed: {str(e)}")

        # Fallback User-Agent
        return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{browser_version} Safari/537.36"

    def generate_webgl_info(self, os_platform: str, browser_version: str) -> Dict[str, Any]:
        """Генерация WebGL информации"""
        try:
            url = f'https://anty-api.com/fingerprints/webgl?browser_type=anty&browser_version={browser_version}&platform={os_platform}'
            headers = {
                'Authorization': f'Bearer {os.environ.get("TOKEN")}',
                'Content-Type': 'application/json'
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    webgl_data = data['data']
                    # Добавляем информацию о экране
                    webgl_data['screen'] = self.__get_random_resolution()
                    # Добавляем версию платформы для Windows
                    if os_platform == 'windows':
                        webgl_data['platformVersion'] = "10.0.0"
                    return webgl_data
        except Exception as e:
            logger.error(f"WebGL info generation failed: {str(e)}")

        # Fallback WebGL info
        return {
            "vendor": "Google Inc. (Intel)",
            "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 620 (0x00005917) Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "webgl2Maximum": {
                "MAX_TEXTURE_SIZE": 16384,
                "MAX_RENDERBUFFER_SIZE": 16384,
                "MAX_VIEWPORT_DIMS": [16384, 16384]
            },
            "screen": self.__get_random_resolution(),
            "platformVersion": "10.0.0"
        }

    def _get_realistic_main_website(self, locale: str, geoip: Dict[str, Any] = None) -> str:
        """Генерация реалистичного основного веб-сайта на основе локали"""
        locale_websites = {
            "ru_RU": ["yandex.ru", "mail.ru", "vk.com", "ok.ru", "rambler.ru"],
            "ru_BY": ["yandex.by", "tut.by", "onliner.by", "mail.ru", "vk.com"],
            "en_US": ["google.com", "facebook.com", "amazon.com", "youtube.com", "netflix.com"],
            "en_IN": ["google.co.in", "flipkart.com", "amazon.in", "hotstar.com", "paytm.com"],
            "es_MX": ["google.com.mx", "mercadolibre.com.mx", "facebook.com", "youtube.com", "netflix.com"],
            "es_CL": ["google.cl", "mercadolibre.cl", "facebook.com", "youtube.com", "netflix.com"],
            "pt_BR": ["google.com.br", "mercadolibre.com.br", "globo.com", "uol.com.br", "facebook.com"]
        }

        # Попробуем определить по GeoIP
        if geoip and geoip.get("country_code"):
            cc = geoip["country_code"].upper()
            if cc == "US":
                websites = locale_websites.get("en_US", [])
            elif cc == "BR":
                websites = locale_websites.get("pt_BR", [])
            elif cc == "MX":
                websites = locale_websites.get("es_MX", [])
            elif cc == "CL":
                websites = locale_websites.get("es_CL", [])
            elif cc == "IN":
                websites = locale_websites.get("en_IN", [])
            elif cc == "BY":
                websites = locale_websites.get("ru_BY", [])
            elif cc in ["RU", "KZ", "UZ"]:
                websites = locale_websites.get("ru_RU", [])
            else:
                websites = locale_websites.get(locale, locale_websites.get("en_US", []))
        else:
            websites = locale_websites.get(locale, locale_websites.get("en_US", []))

        return random.choice(websites) if websites else "google.com"

    def create_profile(
            self,
            name: str,
            proxy: Dict[str, Any],
            tags: List[str] = None,
            locale: Optional[str] = None,
            strict_webrtc: bool = True
    ) -> Dict[str, Any]:
        """
        Create a fully randomized Dolphin Anty browser profile with new logic:
        1. First add proxy to Dolphin
        2. Then create profile without proxy
        3. Finally assign proxy to profile
        """
        if tags is None:
            tags = []

        # Валидация входящих параметров
        if not name or not isinstance(name, str) or not name.strip():
            return {"success": False, "error": "Profile name is required and must be a non-empty string"}

        # 1) Proxy is required
        if not proxy:
            return {"success": False, "error": "Proxy configuration is required"}

        # НОВАЯ ЛОГИКА: Шаг 1 - Добавляем прокси в Dolphin
        logger.info(f"[PROFILE] Step 1: Adding proxy to Dolphin for profile {name}")
        proxy_name = f"proxy_{name}_{proxy['host']}_{proxy['port']}"
        proxy_result = self.add_proxy_to_dolphin(proxy, proxy_name)

        proxy_id = None
        if proxy_result.get("success"):
            proxy_id = proxy_result["proxy_id"]
            logger.info(f"[PROFILE] Proxy added to Dolphin with ID: {proxy_id}")
        else:
            logger.warning(
                f"[PROFILE] Failed to add proxy to Dolphin: {proxy_result.get('error')}. Will use fallback method.")
            # Продолжаем со старой логикой если не удалось добавить прокси

        # 2) Choose OS and browser version - only Windows
        os_plat = self.OS_PLATFORMS[0]
        browser_ver = random.choice(self.BROWSER_VERSIONS)

        # 2b) Geo-IP for proxy to sync locale/TZ/geo and maybe WebRTC public IP
        geoip = self._geoip_lookup(proxy)
        public_ip = (geoip or {}).get("ip")

        # 3) Generate User-Agent
        ua = self.generate_user_agent(os_plat, browser_ver)
        if not ua:
            logger.warning("UA generation failed, using fallback")
            ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{browser_ver} Safari/537.36"

        # 4) Generate WebGL info + platformVersion
        webgl = self.generate_webgl_info(os_plat, browser_ver)
        if not webgl:
            return {"success": False, "error": "WebGL info generation failed"}

        # Fallback platform versions
        default_versions = {"windows": "10.0.0", "macos": "15.0.0", "linux": "0.0.0"}
        plat_ver = webgl.get("platformVersion") or default_versions[os_plat]

        # 5) Randomize modes per documentation
        webrtc_mode = "altered"
        webgl_mode = "real"
        webgl_info_mode = "manual"
        cpu_mode = "manual"
        mem_mode = "manual"
        cpu_value = random.choice([4, 8, 16])
        mem_value = random.choice([8, 16, 32])

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
                "00:21:85", "00:24:21", "70:85:C2", "E0:3F:49",
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
            last_bytes = ":".join(f"{random.randint(0, 255):02X}" for _ in range(3))

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
                    lambda: f"DESKTOP-{random.choice(string.ascii_uppercase)}{random.randint(10, 99)}{random.choice(string.ascii_uppercase)}{random.randint(100, 999)}",
                    lambda: f"LAPTOP-{random.choice(string.ascii_uppercase)}{random.randint(10, 99)}{random.choice(string.ascii_uppercase)}{random.randint(100, 999)}",
                    # Company/office patterns
                    lambda: f"WIN-{random.choice(string.ascii_uppercase)}{random.randint(10, 99)}{random.choice(string.ascii_uppercase)}{random.randint(100, 999)}",
                    lambda: f"PC-{random.choice(['USER', 'OFFICE', 'HOME'])}{random.randint(10, 99)}",
                    # Brand-specific patterns
                    lambda: f"DELL-{random.choice(string.ascii_uppercase)}{random.randint(1000, 9999)}",
                    lambda: f"HP-{random.choice(['PAVILION', 'ELITEBOOK', 'PROBOOK'])}{random.randint(100, 999)}",
                    lambda: f"LENOVO-{random.choice(['THINKPAD', 'IDEAPAD'])}{random.randint(100, 999)}",
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
                (34.0522, -118.2437),  # LA
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
                (-27.1127, -109.3497),  # Hanga Roa (Easter Island) - rare
            ]
            lat, lon = random.choice(cl_cities)
            geo_payload = {"mode": "manual", "latitude": lat, "longitude": lon}
        elif normalized_locale in {"es_MX", "es-MX"}:
            # Mexico
            mx_timezones = [
                "America/Mexico_City",  # central
                "America/Monterrey",
                "America/Guadalajara",
                "America/Tijuana",  # pacific
                "America/Cancun",  # eastern-like (Quintana Roo)
            ]
            tz_payload = {"mode": "manual", "value": random.choice(mx_timezones)}
            mx_cities = [
                (19.4326, -99.1332),  # Mexico City
                (25.6866, -100.3161),  # Monterrey
                (20.6597, -103.3496),  # Guadalajara
                (32.5149, -117.0382),  # Tijuana
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
                (-8.0476, -34.8770),  # Recife
                (-3.1190, -60.0217),  # Manaus
                (-30.0346, -51.2177),  # Porto Alegre
                (-25.4284, -49.2733),  # Curitiba
            ]
            lat, lon = random.choice(br_cities)
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
            "name": name,
            "tags": tags,
            "platform": os_plat,
            "platformVersion": plat_ver,
            "mainWebsite": self._get_realistic_main_website(normalized_locale, geoip),
            "browserType": "anty",

            "useragent": {
                "mode": "manual",
                "value": ua
            },

            "webrtc": {
                "mode": ("manual" if (strict_webrtc and public_ip) else webrtc_mode),
                **({"ipAddress": public_ip} if (strict_webrtc and public_ip) else {})
            },

            "canvas": {
                "mode": "real"
            },

            "webgl": {
                "mode": webgl_mode
            },

            "webglInfo": {
                "mode": webgl_info_mode,
                "vendor": webgl["vendor"],
                "renderer": webgl["renderer"],
                "webgl2Maximum": webgl["webgl2Maximum"]
            },

            "screen": {
                "mode": "manual",
                "resolution": webgl["screen"]
            },

            "timezone": tz_payload,
            "locale": {"mode": "manual", "value": normalized_locale},
            "language": {"mode": "manual", "value": lang_value_dash},
            "geolocation": geo_payload,

            "cpu": {
                "mode": cpu_mode,
                **({"value": cpu_value} if cpu_value is not None else {})
            },

            "memory": {
                "mode": mem_mode,
                **({"value": mem_value} if mem_value is not None else {})
            },

            "mediaDevices": {"mode": "real"},
            "doNotTrack": 0,

            "macAddress": mac_payload,
            "deviceName": dev_payload,
            "fonts": fonts_payload,
            "audio": audio_payload,

            # Прокси не добавляем в payload - будем привязывать отдельно
        }

        # 12) Send request
        logger.info(
            f"[PROFILE] Creating with locale={normalized_locale}, language={lang_value_dash}, timezone={tz_payload.get('value')}")

        # Проверяем обязательные поля перед отправкой
        required_fields = ["name", "platform", "browserType"]
        for field in required_fields:
            if not payload.get(field):
                error_msg = f"Required field '{field}' is missing or empty"
                logger.error(f"[FAIL] {error_msg}")
                return {"success": False, "error": error_msg}

        logger.debug(
            f"[PROFILE] Payload: name={payload['name']}, platform={payload['platform']}, browserType={payload['browserType']}")

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

        # 13) Log result and handle proxy assignment
        if resp and ("browserProfileId" in resp or resp.get("data", {}).get("id")):
            profile_id = resp.get("browserProfileId") or resp.get("data", {}).get("id")
            logger.info(f"[OK] Profile created: {profile_id}")

            # Add to local profiles list
            self.profiles.append(Profile(id=profile_id, name=name))

            # НОВАЯ ЛОГИКА: Шаг 3 - Привязываем прокси к профилю
            if proxy_id:
                logger.info(f"[PROFILE] Step 3: Assigning proxy {proxy_id} to profile {profile_id}")
                assign_result = self.assign_proxy_to_profile(profile_id, proxy_id)

                if assign_result.get("success"):
                    logger.info(f"[OK] Proxy successfully assigned to profile {name}")
                    # Добавляем информацию о прокси в ответ
                    resp["proxy_assigned"] = True
                    resp["proxy_id"] = proxy_id
                else:
                    logger.warning(
                        f"[PROFILE] Failed to assign proxy to profile: {assign_result.get('error')}. Using fallback method.")
                    # Fallback: используем старый метод через Profile.update_profile_proxy
                    try:
                        profile_obj = Profile(id=profile_id, name=name)
                        profile_obj.update_profile_proxy(proxy)
                        logger.info(f"[OK] Proxy assigned using fallback method for profile {name}")
                        resp["proxy_assigned"] = True
                        resp["proxy_method"] = "fallback"
                    except Exception as e:
                        logger.error(f"[FAIL] Fallback proxy assignment also failed: {str(e)}")
                        resp["proxy_assigned"] = False
                        resp["proxy_error"] = str(e)
            else:
                # Используем старый метод если прокси не был добавлен в Dolphin
                logger.info(f"[PROFILE] Using old proxy method for profile {name}")
                try:
                    profile_obj = Profile(id=profile_id, name=name)
                    profile_obj.update_profile_proxy(proxy)
                    logger.info(f"[OK] Proxy assigned using old method for profile {name}")
                    resp["proxy_assigned"] = True
                    resp["proxy_method"] = "old"
                except Exception as e:
                    logger.error(f"[FAIL] Old proxy assignment method failed: {str(e)}")
                    resp["proxy_assigned"] = False
                    resp["proxy_error"] = str(e)

            return resp
        else:
            logger.error(f"[FAIL] Profile creation failed: {resp}")
            return {"success": False, "error": "Profile creation failed", "details": resp}

    def add_proxy_to_dolphin(self, proxy: Dict[str, Any], name: str = None) -> Dict[str, Any]:
        """
        Добавляет прокси в Dolphin Anty и возвращает его ID
        
        Args:
            proxy (Dict[str, Any]): Данные прокси с полями host, port, user, pass, type
            name (str, optional): Имя прокси. Если не указано, генерируется автоматически
        
        Returns:
            Dict[str, Any]: Результат добавления прокси с ID
        """
        if not proxy or not proxy.get("host") or not proxy.get("port"):
            return {"success": False, "error": "Invalid proxy data: host and port are required"}

        # Генерируем имя прокси если не указано
        if not name:
            name = f"proxy_{proxy['host']}_{proxy['port']}"

        payload = {
            "name": name,
            "host": proxy["host"],
            "port": int(proxy["port"]),
            "type": proxy.get("type", "http").lower(),
        }

        # Добавляем аутентификацию если есть
        if proxy.get("user") and proxy.get("pass"):
            payload["login"] = proxy["user"]
            payload["password"] = proxy["pass"]

        if proxy.get('username') and proxy.get('password'):
            payload["login"] = proxy["username"]
            payload["password"] = proxy["password"]

        try:
            logger.info(f"[PROXY] Adding proxy {proxy['host']}:{proxy['port']} to Dolphin")
            resp = self._make_request("post", "/proxy", data=payload)

            if resp and resp.get("data", {}).get("id"):
                proxy_id = resp["data"]["id"]
                logger.info(f"[OK] Proxy added to Dolphin with ID: {proxy_id}")
                return {"success": True, "proxy_id": proxy_id, "data": resp}
            else:
                logger.error(f"[FAIL] Failed to add proxy to Dolphin: {resp}")
                return {"success": False, "error": "Failed to add proxy", "details": resp}

        except DolphinAntyAPIError as e:
            logger.error(f"[FAIL] Proxy addition failed: {e.message}")
            return {"success": False, "error": e.message}

    def assign_proxy_to_profile(self, profile_id: Union[str, int], proxy_id: Union[str, int]) -> Dict[str, Any]:
        """
        Привязывает существующий прокси к профилю в Dolphin Anty
        
        Args:
            profile_id (Union[str, int]): ID профиля
            proxy_id (Union[str, int]): ID прокси в Dolphin
        
        Returns:
            Dict[str, Any]: Результат привязки прокси
        """
        if not profile_id or not proxy_id:
            return {"success": False, "error": "Profile ID and Proxy ID are required"}

        payload = {
            "proxy": {
                "id": str(proxy_id)
            }
        }

        try:
            logger.info(f"[PROXY] Assigning proxy {proxy_id} to profile {profile_id}")
            resp = self._make_request("patch", f"/browser_profiles/{profile_id}", data=payload)

            if resp:
                logger.info(f"[OK] Proxy {proxy_id} assigned to profile {profile_id}")
                return {"success": True, "data": resp}
            else:
                logger.error(f"[FAIL] Failed to assign proxy to profile: {resp}")
                return {"success": False, "error": "Failed to assign proxy", "details": resp}

        except DolphinAntyAPIError as e:
            logger.error(f"[FAIL] Proxy assignment failed: {e.message}")
            return {"success": False, "error": e.message}
