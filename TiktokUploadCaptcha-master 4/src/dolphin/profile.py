import http
import json
import os
import random
import urllib.parse
from http import client
from typing import Dict, Any, Union, List

import requests

from src import logger

TOKEN = os.environ.get('TOKEN')


class Profile:

    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

    def delete_profile(self):
        url = f"https://dolphin-anty-api.com/browser_profiles/{self.id}?forceDelete=1"
        payload = {}
        headers = {
            'Authorization': f'Bearer {os.environ.get("TOKEN")}',
            'content-type': 'application/json'
        }
        response = requests.request("DELETE", url, headers=headers, data=payload)
        data = response.json()
        if 'success' in data.keys():
            logger.debug(f'Profile {self.id} successfully deleted')
        else:
            logger.error(f'Failed to delete profile id {self.id}')

    def start(self):
        for attempt in range(3):
            conn = client.HTTPConnection("127.0.0.1", 3001)
            conn.request("GET", f"/v1.0/browser_profiles/{self.id}/start?automation=1")
            res = conn.getresponse().read()
            data = json.loads(res)
            if 'success' in data.keys():
                port = data['automation']['port']
                endpoint = data['automation']['wsEndpoint']
                logger.info(f'Profile {self.id} successfully started. Port: {port}, endpoint: {endpoint}')
                return port, endpoint
            else:
                logger.error(f'Failed to start profile id {self.id}. Reason: {data}')
                # if data['error']['errorObject']['code'] == 'E_BROWSER_RUN_DUPLICATE':
                #     self.stop()
                # logger.info('Trying again to start profile')
                # continue
        return None

    def stop(self):
        conn = client.HTTPConnection("127.0.0.1", 3001)
        conn.request("GET", f"/v1.0/browser_profiles/{self.id}/stop")
        res = conn.getresponse()
        data = json.loads(res.read())
        if 'success' in data.keys():
            logger.debug(f'Profile {self.id} successfully stopped')
        else:
            logger.error(f'Failed to stop profile id {self.id}')

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
            'Authorization': f'Bearer {os.environ.get("TOKEN")}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        res = requests.patch(url, headers=headers, data=payload)

        if res.status_code == 200:

            logger.info(f'Proxy {proxy} for profile {self.id} is set')
        else:
            logger.error(f'Failed to add proxy for {self.id}. Reason: {res.text}')

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
                logger.info(f'Cookies for {self.id} is done')
                return
            else:
                logger.error(f'Failed cookie robot for profile id {self.id}. Reason: {data}')
                if attempt != 3:
                    logger.info('Trying to start cookie robot again')

    def export_cookies(self):
        url = f"https://sync.dolphin-anty-api.com/?actionType=getCookies&browserProfileId={self.id}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {os.environ.get("TOKEN")}'
        }
        res = requests.request("GET", url, headers=headers)
        return res.json()['data']

    def get_id(self):
        return self.id

    def get_endpoint(self):
        return self.endpoint

    def get_port(self):
        return self.port

    def get_name(self):
        return self.name
