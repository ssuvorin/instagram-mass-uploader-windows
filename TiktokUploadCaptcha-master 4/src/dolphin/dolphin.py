import http.client
import json
import os
import random
from typing import Dict, Union, List, Any

import requests

from src import logger
from src.dolphin.profile import Profile


class Dolphin:

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

    def make_profile(self, name, platform='windows', proxy=None):
        url = "https://dolphin-anty-api.com/browser_profiles"

        null = None
        false = False
        webgl = self.__get_WEBGLinfo(platform=platform)

        payload = json.dumps(
            {"name": name, "tags": [], "platform": platform, "browserType": "anty", "mainWebsite": "https://tiktok.com",
             "useragent": {"mode": "manual",
                           "value": self.__get_ua(platform)},
             "webrtc": {"mode": "altered", "ipAddress": null}, "canvas": {"mode": "real"}, "webgl": {"mode": "real"},
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
            return result['data']['id']
        else:
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
        headers = {
            "Content-Type": "application/json",
        }
        payload = json.dumps({
            "cookies": cookies or [],
            "profileId": profile_id,
            "transfer": transfer,
            "cloudSyncDisabled": bool(cloud_sync_disabled),
            'Authorization': f'Bearer {os.environ.get("TOKEN")}',
        })
        try:
            logger.info(f"[TOOL] Importing {len(cookies or [])} cookies to profile {profile_id} via Local API")
            conn = http.client.HTTPConnection("127.0.0.1", 3001)
            conn.request("POST", "/v1.0/cookies/import", payload, headers)
            resp = conn.getresponse()
            if resp.status == 200:
                try:
                    data = json.loads(resp.read())
                except Exception:
                    data = {"success": True}
                logger.info(f"[OK] Cookies imported into profile {profile_id}")
                return data if isinstance(data, dict) else {"success": True}
            else:
                logger.error(f"[FAIL] Local import cookies failed (HTTP {resp.status}): {resp.read()[:200]}")
                return {"success": False, "error": f"HTTP {resp.status}", "details": resp.read()}
        except Exception as e:
            logger.error(f"[FAIL] Exception during local cookies import: {e}")
            return {"success": False, "error": str(e)}
