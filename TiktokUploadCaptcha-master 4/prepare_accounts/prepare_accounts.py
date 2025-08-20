import json
import os
import random
import shutil
import urllib
from http import client
import sqlite3

from src.telegram import send_message

import requests
from dotenv import load_dotenv

TIKTOK_SOLVER_API_KEY = os.environ.get('TIKTOK_SOLVER_API_KEY')
MUSIC_NAME = "Даня Милохин"
LOCATION = "Moscow"
MENTIONS = []

VIDEOS_PER_ACCOUNT = 1
UPLOAD_CYCLES = 5

ABSPATH = os.path.abspath(__file__).replace('\\prepare_accounts\\prepare_accounts.py', '')

load_dotenv()

TOKEN = os.environ.get('TOKEN')

import datetime
import sqlite3

from src import logger


class DataBase:

    def __init__(self, db_name='accounts.db'):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()

    def close(self):
        self.connection.close()

    def execute(self, query, params=()):
        self.cursor.execute(query, params)
        self.connection.commit()

    def fetch_all(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def fetch_one(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchone()

    def create_table(self, table_name, columns):
        column_defs = ', '.join([f"{col[0]} {col[1]}" for col in columns])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_defs})"
        self.execute(query)

    def insert(self, table_name, data):
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        values = tuple(data.values())
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.execute(query, values)

    def select(self, table_name, columns='*', where=None, params=()):
        query = f"SELECT {columns} FROM {table_name}"
        if where:
            query += f" WHERE {where}"
        return self.fetch_all(query, params)

    def select_one(self, table_name, columns='*', where=None, params=()):
        query = f"SELECT {columns} FROM {table_name}"
        if where:
            query += f" WHERE {where}"
        return self.fetch_one(query, params)

    def update(self, table_name, data, where=None, params=()):
        set_clause = ', '.join([f"{col}=?" for col in data.keys()])
        values = tuple(data.values())
        query = f"UPDATE {table_name} SET {set_clause}"
        if where:
            query += f" WHERE {where}"
            values += params
        self.execute(query, values)

    def delete(self, table_name, where=None, params=()):
        query = f"DELETE FROM {table_name}"
        if where:
            query += f" WHERE {where}"
        self.execute(query, params)

    def insert_and_get_id(self, table_name, data):
        self.insert(table_name, data)
        return self.cursor.lastrowid

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_ua(platform='windows'):
    url = f'https://dolphin-anty-api.com/fingerprints/useragent?browser_type=anty&browser_version=120&platform={platform}'
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'content-type': 'application/json'
    }
    res = requests.get(url, headers=headers)
    return res.json()['data']


def get_WEBGLinfo(platform='windows'):
    url = f'https://anty-api.com/fingerprints/webgl?browser_type=anty&browser_version=137&platform={platform}'
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'content-type': 'application/json'
    }
    res = requests.get(url, headers=headers)
    result = res.json()
    result['mode'] = "manual"
    return result


def __get_random_cpu_and_ram():
    m = [2, 4, 6, 8, 12, 16]
    return random.choice(m)


def __get_random_resolution():
    r = ["1920X1080", "1600X1200", "1920X1200"]
    return random.choice(r)


def set_profile(name, proxy_id, login, password, platform='windows'):
    url = "https://dolphin-anty-api.com/browser_profiles"

    null = None
    false = False
    webgl = get_WEBGLinfo(platform=platform)

    payload = json.dumps(
        {"name": name, "tags": [], "platform": platform, "browserType": "anty", "mainWebsite": "https://tiktok.com",
         "useragent": {"mode": "manual",
                       "value": get_ua(platform)},
         "webrtc": {"mode": "altered", "ipAddress": null}, "canvas": {"mode": "real"}, "webgl": {"mode": "real"},
         "webglInfo": {"mode": "manual", "vendor": webgl['webglUnmaskedVendor'],
                       "renderer": webgl['webgl_unmasked_renderer']},
         "webgpu": {"mode": "manual"}, "clientRect": {"mode": "real"},
         "notes": {"content": null, "color": "blue", "style": "text", "icon": "info"},
         "timezone": {"mode": "auto", "value": null}, "locale": {"mode": "manual", "value": "en"},
         "proxy": {"id": proxy_id},
         "statusId": 0,
         "geolocation": {"mode": "auto", "latitude": null, "longitude": null, "accuracy": null},
         "cpu": {"mode": "manual", "value": __get_random_cpu_and_ram()},
         "memory": {"mode": "manual", "value": __get_random_cpu_and_ram()},
         "screen": {"mode": "manual", "resolution": __get_random_resolution()}, "audio": {"mode": "real"},
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
        'Authorization': f'Bearer {TOKEN}',
        'content-type': 'application/json'
    }

    res = requests.post(url, headers=headers, data=payload)

    if res.status_code == 200:
        result = res.json()
        print(f'Profile {result['data']['id']} is set. Setting cookies...')
        _set_cookies(result['data']['id'])
    else:
        print(res.text)


def prepare_proxies():
    with open('proxy\\proxies.txt') as f:
        data = f.read()
    proxies = []
    for i in data.split('\n'):
        proxies.append(
            {
                'host': i.split('@')[0].split(':')[0],
                'port': i.split('@')[0].split(':')[1],
                'login': i.split('@')[1].split(':')[0],
                'password': i.split('@')[1].split(':')[1],
                'type': 'http',
            }
        )
    index = 0
    for proxy in proxies:
        payload = f'type=http&host={proxy["host"]}&port={proxy["port"]}&login={proxy["login"]}&password={proxy["password"]}&name={index}'

        url = "https://dolphin-anty-api.com/proxy?Content-Type=application/json"

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Bearer {TOKEN}',
        }

        res = requests.post(url, headers=headers, data=payload)
        if res.status_code == 200:
            print('Proxy OK')
        else:
            print(f'Error while adding {proxy['host']}: {res.status_code} {res.text}')
        index += 1


def prepare_accounts():
    db = DataBase()
    all_accounts = db.select('Accounts')
    account_names = [account[0] for account in all_accounts]
    for account in account_names:
        create_folder(f'{ABSPATH}\\accounts\\accounts_data\\{str(account)}')
        data = db.select_one('Accounts', columns='username, password, email_username, email_password',
                             where='profile_name = ?', params=(account,))
        with open(f'{ABSPATH}\\accounts\\accounts_data\\{str(account)}\\config.json', 'w') as f:
            json.dump(
                {
                    "username": data[0],
                    "password": data[1],
                    "email_username": data[2],
                    "email_password": data[3]
                }, f
            )


def prepare_titles():
    shutil.copy('titles\\titles.txt', f'{ABSPATH}\\accounts\\titles.txt')


def prepare_videos():
    for video in os.listdir('videos'):
        shutil.copy(f'{ABSPATH}\\prepare_accounts\\videos\\{video}', f'{ABSPATH}\\accounts\\videos\\{video}')


def prepare_config():
    music_name = ""
    if MUSIC_NAME:
        music_name = MUSIC_NAME.encode('utf-8', 'ignore').decode('utf-8')

    # Получаем список всех аккаунтов
    account_names = os.listdir(f'{ABSPATH}\\accounts\\accounts_data')
    total_accounts = len(account_names)

    # Рассчитываем общее количество необходимых видео
    total_videos_needed = total_accounts * UPLOAD_CYCLES

    # Получаем список всех доступных видео
    all_videos = os.listdir(f'{ABSPATH}\\accounts\\videos')
    with open(f'{ABSPATH}\\accounts\\titles.txt', 'r', encoding='utf-8') as f:
        all_titles = f.readlines()

    # Проверяем доступность уникальных видео
    if total_videos_needed > len(all_videos):
        raise ValueError(f"Not enough unique videos. Needed: {total_videos_needed}, Available: {len(all_videos)}")

    # Выбираем уникальные видео для всей конфигурации
    selected_videos = random.sample(all_videos, total_videos_needed)
    selected_titles = random.sample(all_titles, total_videos_needed)

    # Формируем конфигурацию
    config = {
        "accounts": [],
        "location": LOCATION,
        "mentions": MENTIONS,
        "music_name": music_name
    }

    # Распределяем видео по аккаунтам и циклам
    video_index = 0
    for _ in range(UPLOAD_CYCLES):
        for account in account_names:
            config['accounts'].append({
                'name': account,
                'video': selected_videos[video_index],
                'title': selected_titles[video_index]
            })
            video_index += 1

    # Сохраняем конфигурацию
    with open(f'{ABSPATH}\\accounts\\config.json', 'w', encoding='utf-8-sig') as f:
        json.dump(config, f, ensure_ascii=False)


def prepare_folders():
    if os.path.exists(f'{ABSPATH}\\accounts\\accounts_data'):
        shutil.rmtree(f'{ABSPATH}\\accounts\\accounts_data')
    if os.path.exists(f'{ABSPATH}\\accounts\\videos'):
        shutil.rmtree(f'{ABSPATH}\\accounts\\videos')
    create_folder(f'{ABSPATH}\\accounts')
    create_folder(f'{ABSPATH}\\accounts\\accounts_data')
    create_folder(f'{ABSPATH}\\accounts\\videos')


def create_folder(name):
    if not os.path.exists(name):
        os.mkdir(name)


def get_proxies():
    url = "https://dolphin-anty-api.com/proxy"
    headers = {
        'Authorization': f'Bearer {os.environ.get("TOKEN")}'
    }
    response = requests.get(url, headers=headers)
    ids = []
    for i in response.json()['data']:
        ids.append(i['id'])
    return ids


def _set_cookies(id):
    conn = client.HTTPConnection("127.0.0.1", 3001)
    payload = [('data', site) for site in __get_sites()]
    payload.append(('headless', 'true'))
    payload.append(('imageless', 'false'))
    encoded_payload = urllib.parse.urlencode(payload).encode('utf-8')
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    conn.request("POST", f"/v1.0/import/cookies/{str(id)}/robot", encoded_payload, headers)
    res = conn.getresponse()
    data = res.read()
    if int(res.status) == 200:
        print(f'Cookies for {id} is done')


def __get_sites():
    with open(os.path.abspath('prepare_accounts.py').replace('prepare_accounts\\prepare_accounts.py',
                                                             'src\\sites.txt')) as f:
        sites = f.read().split('\n')
    return random.sample(sites, random.randint(40, 50))


def main():
    prepare_folders()
    prepare_accounts()
    prepare_titles()
    prepare_videos()

    prepare_config()
    send_message('Подготовка аккаунтов закончена')


if __name__ == '__main__':
    main()
