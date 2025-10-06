import http
import json
import os
import random
import time
import urllib.parse
from http import client
from typing import Dict, Any, Union, List

import requests

from tiktok_uploader.bot_integration import logger

TOKEN = os.environ.get('DOLPHIN_API_TOKEN')


class Profile:

    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

    def delete_profile(self):
        url = f"https://dolphin-anty-api.com/browser_profiles/{self.id}?forceDelete=1"
        payload = {}
        headers = {
            'Authorization': f'Bearer {os.environ.get("DOLPHIN_API_TOKEN")}',
            'content-type': 'application/json'
        }
        response = requests.request("DELETE", url, headers=headers, data=payload)
        data = response.json()
        if 'success' in data.keys():
            logger.debug(f'Profile {self.id} successfully deleted')
        else:
            logger.error(f'Failed to delete profile id {self.name}')

    def start(self):
        for attempt in range(3):
            try:
                conn = client.HTTPConnection("127.0.0.1", 3001)
                conn.request("GET", f"/v1.0/browser_profiles/{self.id}/start?automation=1")
                res = conn.getresponse()
                
                # Проверяем статус HTTP ответа
                if res.status != 200:
                    logger.error(f'HTTP error {res.status} when starting profile {self.name}')
                    time.sleep(5)
                    continue
                
                raw_data = res.read()
                if not raw_data:
                    logger.error(f'Empty response when starting profile {self.name}')
                    time.sleep(5)
                    continue
                    
                data = json.loads(raw_data)
                logger.debug(f'Profile start response for {self.name}: {data}')
                
                # Проверяем наличие ключа 'success' и его значение
                success = data.get('success', False)
                
                # Проверяем наличие необходимых данных для успешного запуска
                if (success is not False and 
                    'automation' in data and 
                    isinstance(data['automation'], dict) and
                    'port' in data['automation'] and 
                    'wsEndpoint' in data['automation']):
                    
                    port = data['automation']['port']
                    endpoint = data['automation']['wsEndpoint']
                    logger.info(f'Profile {self.name} successfully started. Port: {port}, endpoint: {endpoint}')
                    return port, endpoint
                else:
                    logger.error(f'Failed to start profile {self.name}. Response: {data}')
                    
                    # Обрабатываем специфические ошибки
                    if 'errorObject' in data and isinstance(data['errorObject'], dict):
                        error_code = data['errorObject'].get('code', 'UNKNOWN')
                        error_message = data['errorObject'].get('message', 'No message')
                        logger.error(f'Error code: {error_code}, message: {error_message}')
                        
                        if error_code == 'E_BROWSER_RUN_DUPLICATE':
                            logger.info('Duplicate browser detected, stopping existing instance')
                            self.stop()
                            time.sleep(3)  # Дополнительная пауза после остановки
                        elif error_code == 'E_PROFILE_NOT_FOUND':
                            logger.error(f'Profile {self.name} not found, cannot retry')
                            return None
                    
                    if attempt < 2:  # Не логируем "trying again" на последней попытке
                        logger.info(f'Retrying to start profile {self.name} (attempt {attempt + 2}/3)')
                        time.sleep(5)
                        
            except json.JSONDecodeError as e:
                logger.error(f'Invalid JSON response when starting profile {self.name}: {e}')
                if attempt < 2:
                    time.sleep(5)
                    
            except Exception as e:
                logger.error(f'Unexpected error starting profile {self.name}: {e}')
                if attempt < 2:
                    time.sleep(5)
        
        logger.error(f'Failed to start profile {self.name} after 3 attempts')
        return None

    def stop(self):
        conn = client.HTTPConnection("127.0.0.1", 3001)
        conn.request("GET", f"/v1.0/browser_profiles/{self.id}/stop")
        res = conn.getresponse()
        data = json.loads(res.read())
        if 'success' in data.keys():
            logger.debug(f'Profile {self.name} successfully stopped')
        else:
            logger.error(f'Failed to stop profile id {self.name}')

    def update_profile_proxy(self, proxy):
        url = f"https://dolphin-anty-api.com/browser_profiles/{self.id}"

        params = {
            'proxy[host]': proxy.get('host', ''),
            'proxy[port]': proxy.get('port', ''),
            'proxy[login]': proxy.get('user', ''),
            'proxy[password]': proxy.get('pass', ''),
            'proxy[type]': 'http'
        }
        payload = urllib.parse.urlencode(params)

        headers = {
            'Authorization': f'Bearer {os.environ.get("DOLPHIN_API_TOKEN")}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        res = requests.patch(url, headers=headers, data=payload)

        if res.status_code == 200:

            logger.info(f'Proxy {proxy} for profile {self.name} is set')
        else:
            logger.error(f'Failed to add proxy for {self.name}. Reason: {res.text}')

    def start_cookie_robot(self):
        logger.info(f'Strarting cookie robot for profile {self.name}')

        def __get_sites():
            with open(os.path.abspath(__file__).replace('dolphin\\profile.py', 'sites.json'), 'r') as f:
                sites = json.load(f)
            return random.sample(sites, random.randint(30, 45))

        for attempt in range(3):
            conn = client.HTTPConnection("127.0.0.1", 3001)
            payload = [('data', site) for site in __get_sites()]
            payload.append(('headless', 'true'))
            payload.append(('imageless', 'false'))
            encoded_payload = urllib.parse.urlencode(payload).encode('utf-8')
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            conn.request("POST", f"/v1.0/import/cookies/{str(self.id)}/robot", encoded_payload, headers)
            res = conn.getresponse()
            data = res.read()
            if int(res.status) == 200:
                logger.info(f'Cookies for {self.name} is done')
                return
            else:
                logger.error(f'Failed cookie robot for profile id {self.name}. Reason: {data}')
                if attempt != 3:
                    logger.info('Trying to start cookie robot again')

    def export_cookies(self):
        logger.debug(f'Exporting cookies for profile {self.name}')
        # 1) Пытаемся через Local API: POST /v1.0/export-cookies
        try:
            conn = client.HTTPConnection("127.0.0.1", 3001)
            payload = json.dumps({
                "browserProfiles": [
                    {"id": int(self.id), "name": str(self.name)}
                ],
                "doNotSave": True
            })
            headers = {
                'Content-Type': 'application/json'
            }
            token = os.environ.get('DOLPHIN_API_TOKEN')
            if token:
                headers['Authorization'] = f'Bearer {token}'
            conn.request("POST", "/v1.0/export-cookies", payload, headers)
            res = conn.getresponse()
            raw = res.read()
            if int(res.status) == 200:
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict) and data.get('success') and isinstance(data.get('cookies'), list):
                        logger.debug(f'Obtained cookies via Local API for profile {self.name}: {len(data["cookies"])})')
                        return data['cookies']
                except Exception as e:
                    logger.warning(f'Local API export parse error for {self.name}: {str(e)}')
            else:
                logger.warning(f'Local API export failed (HTTP {res.status}) for {self.name}')
        except Exception as e:
            logger.warning(f'Local API export exception for {self.name}: {str(e)}')

        # 2) Fallback: старый sync API getCookies
        url = f"https://sync.dolphin-anty-api.com/?actionType=getCookies&browserProfileId={self.id}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {os.environ.get("DOLPHIN_API_TOKEN")}'
        }
        res = requests.request("GET", url, headers=headers)
        cookies = res.json().get('data', [])
        logger.debug(f'Obtained cookies via sync API for profile {self.name}: {len(cookies)})')
        return cookies

    def _fetch_profile_details(self) -> Dict[str, Any]:
        """
        Fetch Dolphin profile details to read locale/language for Accept-Language alignment.
        """
        try:
            url = f"https://dolphin-anty-api.com/browser_profiles/{self.id}"
            headers = {
                'Authorization': f'Bearer {os.environ.get("DOLPHIN_API_TOKEN")}',
                'Content-Type': 'application/json'
            }
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                return res.json()
        except Exception as _:
            pass
        return {}

    def resolve_accept_language(self) -> str:
        """
        Resolve Accept-Language header value from Dolphin profile locale/language if available.
        Fallback to sensible defaults if not.
        """
        def _al_for_locale(locale_str: str) -> str:
            s = (locale_str or '').strip().replace('_', '-')
            if not s:
                return 'en-US,en;q=0.9'
            lang = s.split('-')[0].lower()
            if lang == 'ru':
                return f'{s},ru;q=0.9,en-US;q=0.8,en;q=0.7'
            if lang == 'en':
                return f'{s},en;q=0.9'
            if lang == 'es':
                return f'{s},es;q=0.9,en;q=0.8'
            if lang == 'pt':
                return f'{s},pt;q=0.9,en;q=0.8'
            return f'{s},en;q=0.9'

        data = self._fetch_profile_details()
        # Try extract locale/language from response structure
        try:
            bp = (data or {}).get('data') or {}
            def _val(obj: Dict[str, Any], key: str) -> str:
                v = obj.get(key)
                if isinstance(v, dict):
                    return v.get('value') or v.get('lang') or v.get('locale')
                if isinstance(v, str):
                    return v
                return ''
            locale_val = _val(bp, 'locale') or _val(bp, 'language')
            if not locale_val:
                return _al_for_locale('en-US')
            return _al_for_locale(locale_val)
        except Exception:
            return _al_for_locale('en-US')

    def get_id(self):
        return self.id

    def get_endpoint(self):
        return self.endpoint

    def get_port(self):
        return self.port

    def get_name(self):
        return self.name
    
    def change_ip(self, proxy: Dict[str, Any], timeout: int = 10) -> bool:
        """
        Меняет IP прокси по URL, если он указан
        
        Args:
            proxy (dict): Словарь с данными прокси, включая 'changeip_url'
            timeout (int): Таймаут запроса в секундах
        
        Returns:
            bool: True если IP успешно изменен или URL не указан, False при ошибке
        """
        changeip_url = proxy.get('changeip_url', '')
        
        if not changeip_url:
            logger.debug(f"No changeip_url provided for profile {self.name}")
            return True
        
        try:
            logger.info(f"Changing IP for profile {self.name} via {changeip_url}")
            response = requests.get(changeip_url, timeout=timeout)
            
            if response.status_code == 200:
                logger.info(f"IP successfully changed for profile {self.name}")
                return True
            else:
                logger.warning(f"IP change request returned status {response.status_code} for profile {self.name}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout changing IP for profile {self.name}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error changing IP for profile {self.name}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error changing IP for profile {self.name}: {str(e)}")
            return False