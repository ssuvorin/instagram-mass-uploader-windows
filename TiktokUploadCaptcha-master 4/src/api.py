import os
import json
import random
import shutil
import sqlite3
import time
from os.path import exists
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright
from pydantic import BaseModel
import requests

from src.db import DataBase
from src import logger
from src.dolphin.dolphin import Dolphin
from src.dolphin.profile import Profile
from src.telegram import send_message
from src.tiktok.getCode import Email
from src.tiktok.upload import Uploader
from src.tiktok.auth import Auth
from src.tiktok.video import Video
from src.tiktok.booster import Booster

app = FastAPI()
db = DataBase(os.path.abspath(__file__).replace('src\\api.py', 'temp.db'))
dolphin = Dolphin()

db.create_table('accounts', (
    ('username', 'TEXT UNIQUE'),
    ('password', 'TEXT'),
    ('email_username', 'TEXT'),
    ('email_password', 'TEXT'),
    ('cookies', 'TEXT'),
    ('proxy', 'TEXT')
))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

upload_router = APIRouter(prefix='/upload', tags=['upload'])
booster_router = APIRouter(prefix='/booster', tags=['booster'])


# Классы для модуля загрузки

class PrepareAccounts(BaseModel):
    count: int = 20


class PrepareConfig(BaseModel):
    music_name: Optional[str] = None
    location: Optional[str] = None
    mentions: Optional[list[str]] = None
    upload_cycles: int = 5


@upload_router.post('/prepare_accounts')
def prepare_accounts(data: PrepareAccounts):
    """
    Получает аккаунты из БД в формате json и записывает их в temp.db
    """
    api_path = "http://91.108.227.166/get-accounts"
    data = {
        'server_name': os.environ.get('SERVER_NAME'),
        'count': data.count,
        'order': 'newest'
    }
    logger.info('Getting accounts from DB')
    response = requests.get(api_path, json=data)
    if response.status_code != 200:
        try:
            while response.json()['detail'] == 'Not your turn':
                response = requests.get(api_path, json=data)
                time.sleep(5)
        except:
            pass
    result = response.json()
    if 'accounts' not in result.keys():
        logger.error(f'No accounts from DB: {result['detail']}')
        return
    accounts = result['accounts']
    for account in accounts:
        db.insert('accounts', {
            'username': account['username'],
            'password': account['password'],
            'email_username': account['email_username'],
            'email_password': account['email_password'],
            'cookies': account['cookies'],
            'proxy': account['proxy']})

    # Очищаем дельфин, если нужно, и добавляем свои аккаунты
    try:
        profiles = dolphin.get_profiles()
        if profiles:
            logger.info('Dolphin has profiles, deleting...')
            dolphin.delete_accounts()
            logger.info('Profiles successfully deleted')
    except Exception as e:
        logger.error(f"Error managing Dolphin profiles: {str(e)}")
        raise HTTPException(status_code=502, detail="Error managing Dolphin profiles")

    accounts = db.select('accounts')
    for account in accounts:
        try:
            dolphin.make_profile(name=account['username'])
        except Exception as e:
            logger.error(f"Error creating Dolphin profile for {account['username']}: {str(e)}")
            continue

    dolphin.set_profiles()
    for profile in dolphin.get_profiles():
        profile.update_profile_proxy(
            proxy=json.loads(db.select_one('accounts', where="username = ?", params=(profile.name,))['proxy'])
        )
        dolphin.import_cookies_local(profile_id=profile.id, cookies=json.loads(db.select_one('accounts', where="username = ?", params=(profile.name,))['cookies']))

    return {'message': 'Accounts prepared successfully'}


@upload_router.post('/upload_videos/')
def upload_videos(files: List[UploadFile] = File(...)):
    """
    Загружает несколько видео в папку videos
    """
    os.makedirs(os.path.abspath(__file__).replace('src\\api.py', 'videos'), exist_ok=True)
    for file in files:
        file_path = os.path.join(os.path.abspath(__file__).replace('src\\api.py', 'videos'), file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    return {'message': 'Videos uploaded successfully'}


@upload_router.post('/upload_titles')
def upload_titles(file: UploadFile = File(...)):
    """
    Загружает txt файл с заголовками
    """
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=502, detail='File must be a .txt file')
    os.makedirs(os.path.abspath(__file__).replace('src\\api.py', 'titles'), exist_ok=True)
    file_path = os.path.join(os.path.abspath(__file__).replace('src\\api.py', 'titles'), file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"message": "Titles file uploaded successfully"}


@upload_router.post('/prepare_config')
def prepare_config(data: PrepareConfig):
    """
    Делает конфиг с параметрами для загрузки
    """
    config = {
        'accounts': [],
        'music_name': '',
        'location': '',
        'mentions': []
    }
    if data.music_name:
        config['music_name'] = data.music_name
    if data.location:
        config['location'] = data.location
    if data.mentions:
        config['mentions'] = data.mentions

    # Проверяем, достаточно ли видео для загрузки
    accounts = [account['username'] for account in db.select('accounts')]  # Получаем все аккаунты из БД
    total_videos_needed = int(data.upload_cycles) * len(accounts)  # Сколько видео нужно для загрузки
    all_videos = os.listdir(os.path.abspath(__file__).replace('src\\api.py', 'videos'))
    if len(all_videos) < total_videos_needed:
        raise HTTPException(status_code=502, detail=f'Need more {total_videos_needed - len(all_videos)} videos')

    # Проверяем, достаточно ли заголовков для загрузки
    titles_file = os.listdir(os.path.abspath(__file__).replace('src\\api.py', 'titles'))[0]
    with open(f'{os.path.abspath(__file__).replace('src\\api.py', 'titles')}\\{titles_file}', 'r') as f:
        all_titles = f.readlines()
        for title in all_titles:
            title.replace('\n', '')
    if len(all_titles) < total_videos_needed:
        raise HTTPException(status_code=502, detail=f'Need more {total_videos_needed - len(all_titles)} titles')

    selected_videos = random.sample(all_videos, total_videos_needed)
    selected_titles = random.sample(all_titles, total_videos_needed)

    video_index = 0
    for _ in range(int(data.upload_cycles)):
        for account in accounts:
            config['accounts'].append({
                'name': account,
                'video': selected_videos[video_index],
                'title': selected_titles[video_index]
            })
            video_index += 1

    with open('config.json', 'w') as f:
        json.dump(config, f)

    return {'message': 'Config prepared successfully'}


@upload_router.post('/start_upload')
def start_upload():
    if not os.path.exists('config.json'):
        raise HTTPException(status_code=502, detail='Need config to start upload')

    # Подготовка профилей
    send_message('Бот начал работу')
    start_time = time.time()

    path_to_config = os.path.abspath(__file__).replace('src\\api.py', 'config.json')
    with open(path_to_config, 'r') as f:
        cfg = json.load(f)

    try:
        with sync_playwright() as playwright:
            main_upload_loop(cfg, playwright)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        dolphin.stop_profiles()
        t = round((time.time() - start_time) / 60, 2)
        videos_count = 0
        for i in cfg['accounts']:
            videos_count += len(i['video'])
        logger.info(f'Затраченое время: {str(t)} минут')
        logger.info(f'Скорость постинга: {str(round(videos_count / t, 2))} в/мин')
        send_message('Бот завершил работу')
        send_message(f'Затраченое время: {str(t)} минут')
        send_message(f'Скорость постинга: {str(round(videos_count / t, 2))} в/мин')

        # Выгрузка отработавших аккаунтов в БД
        url = "http://91.108.227.166/release-accounts"
        response = requests.post(
            url=url,
            json={
                'server_name': os.environ.get('SERVER_NAME'),
                'usernames': [account['username'] for account in db.select('accounts')]
            }
        )
        if response.status_code == 200:
            logger.info('Accounts released')
            db.delete('accounts')
        else:
            logger.error(f'Accounts not released. Reason: {response.text}')
            raise HTTPException(status_code=502, detail=str(response.text))


# Методы API для модуля прогрева

@booster_router.post('/upload_accounts')
def upload_accounts(file: UploadFile):
    """
    Принимает на вход аккаунты в формате username:password:email_username:email_password
    """
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=502, detail='Accounts file must be a .txt file')
    os.makedirs(os.path.abspath(__file__).replace('src\\api.py', 'accounts'), exist_ok=True)
    file_path = os.path.join(os.path.abspath(__file__).replace('src\\api.py', 'accounts'), file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"message": "Accounts file uploaded successfully"}


@booster_router.post('/upload_proxies')
def upload_proxies(file: UploadFile):
    """
    Принимает на вход прокси в формате host:port@user:pass
    """
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=502, detail='Proxy file must be a .txt file')
    os.makedirs(os.path.abspath(__file__).replace('src\\api.py', 'proxy'), exist_ok=True)
    file_path = os.path.join(os.path.abspath(__file__).replace('src\\api.py', 'proxy'), file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"message": "Proxy file uploaded successfully"}


@booster_router.post('/prepare_accounts')
def prepare_accounts():
    """
    Записывает аккаунты в БД, выставляет прокси и прогревает куки.
    """

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Корень проекта (предполагая src/api.py)
    accounts_dir = os.path.join(base_dir, 'accounts')
    proxy_dir = os.path.join(base_dir, 'proxy')

    # Проверка директорий
    if not os.path.exists(accounts_dir):
        logger.error(f"Accounts directory not found: {accounts_dir}")
        raise HTTPException(status_code=502, detail="Accounts directory not found")
    if not os.path.exists(proxy_dir):
        logger.error(f"Proxy directory not found: {proxy_dir}")
        raise HTTPException(status_code=502, detail="Proxy directory not found")

    if not os.listdir(accounts_dir):
        logger.error('No accounts files provided')
        raise HTTPException(status_code=502, detail='No accounts files provided')
    if not os.listdir(proxy_dir):
        logger.error('No proxies files provided')
        raise HTTPException(status_code=502, detail='No proxies files provided')

    # Шаг 1: Запись аккаунтов в БД
    inserted_count = 0
    for file in os.listdir(accounts_dir):
        path_to_file = os.path.join(accounts_dir, file)
        if not os.path.isfile(path_to_file):
            logger.warning(f"Skipping non-file: {path_to_file}")
            continue
        try:
            with open(path_to_file, 'r') as f:
                data = f.read().splitlines()
            for line in data:
                if not line.strip():
                    continue
                parts = line.split(':')
                username, password, email_username, email_password, cookies = None, None, None, None, None
                if len(parts) != 4:
                    parts = line.split(':', 2)
                    if len(parts) != 3:
                        logger.warning(f"Invalid account format in {file}: {line}")
                    username, password, cookies = parts
                else:
                    username, password, email_username, email_password = parts
                if db.select('accounts', where="username = ?", params=(username,)):
                    logger.info(f"Account {username} already exists, skipping")
                    continue
                db.insert('accounts', {
                    'username': username,
                    'password': password,
                    'email_username': email_username,
                    'email_password': email_password,
                    'cookies': cookies
                })
                inserted_count += 1
        except Exception as e:
            logger.error(f"Error processing file {path_to_file}: {str(e)}")
            continue

    logger.info(f"Inserted {inserted_count} accounts into DB")

    # Добавляем профили в Dolphin
    try:
        profiles = dolphin.get_profiles()
        if profiles:
            logger.info('Dolphin has profiles, deleting...')
            dolphin.delete_accounts()
            logger.info('Profiles successfully deleted')
    except Exception as e:
        logger.error(f"Error managing Dolphin profiles: {str(e)}")
        raise HTTPException(status_code=502, detail="Error managing Dolphin profiles")

    accounts = db.select('accounts')
    for account in accounts:
        try:
            dolphin.make_profile(name=account['username'])
        except Exception as e:
            logger.error(f"Error creating Dolphin profile for {account['username']}: {str(e)}")
            continue  # Пропускаем неудачные

    def _get_proxies():
        proxies = []
        for file in os.listdir(proxy_dir):
            file_path = os.path.join(proxy_dir, file)
            if not os.path.isfile(file_path):
                logger.warning(f"Skipping non-file: {file_path}")
                continue
            try:
                with open(file_path, 'r') as f:
                    data = f.read().splitlines()
                for line in data:
                    if not line.strip():
                        continue
                    parts = line.split('@')
                    if len(parts) != 2:
                        logger.warning(f"Invalid proxy format in {file}: {line}")
                        continue
                    host_port, user_pass = parts
                    hp_parts = host_port.split(':')
                    up_parts = user_pass.split(':')
                    if len(hp_parts) != 2 or len(up_parts) != 2:
                        logger.warning(f"Invalid proxy parts in {line}")
                        continue
                    try:
                        port = int(hp_parts[1])  # Валидация порта
                    except ValueError:
                        logger.warning(f"Invalid port in {line}")
                        continue
                    proxies.append({
                        'host': hp_parts[0],
                        'port': hp_parts[1],
                        'user': up_parts[0],
                        'pass': up_parts[1],
                        'type': 'http'
                    })
            except Exception as e:
                logger.error(f"Error processing proxy file {file_path}: {str(e)}")
                continue
        if not proxies:
            logger.error("No valid proxies found")
            raise HTTPException(status_code=500, detail="No valid proxies found")
        return proxies

    proxies = _get_proxies()

    # Выставление прокси и прогрев куки
    index = 0
    dolphin_profiles = dolphin.get_profiles()
    for profile in dolphin_profiles:
        for attempt in range(3):
            try:
                pr = proxies[index % len(proxies)]
                profile.update_profile_proxy(pr)
                db.update('accounts', {'proxy': json.dumps(pr)}, where="username = ?", params=(profile.name,))
                # profile.start_cookie_robot()
                cookies = db.select_one('accounts', where="username = ?", params=(profile.name,))['cookies']
                if cookies:
                    dolphin.import_cookies_local(
                        profile_id=profile.id,
                        cookies=json.loads(cookies)
                    )
                break
            except Exception as e:
                logger.error(f"Error updating profile {profile.name} (attempt {attempt + 1}): {str(e)}")
                if attempt == 2:
                    continue
                time.sleep(2)
        index += 1

    for i in os.listdir(accounts_dir):
        os.remove(accounts_dir + '\\' + i)
    for i in os.listdir(proxy_dir):
        os.remove(proxy_dir + '\\' + i)

    send_message('Подготовка аккаунт к прогреву завершена')

    return {'message': 'Accounts prepared successfully', 'inserted_accounts': inserted_count,
            'processed_profiles': len(dolphin_profiles)}


@booster_router.post('/start_booster')
def start_booster():
    accounts = db.select('accounts')
    if not accounts:
        logger.error('No accounts for booster provided')
        raise HTTPException(status_code=502, detail='No accounts for booster provided')
    try:
        with sync_playwright() as playwright:
            main_booster_loop(accounts, playwright)
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        dolphin.stop_profiles()
        send_message('Прогрев аккаунтов завершен')
        accounts = db.select('accounts')
        payload = {
            'server_name': os.environ.get('SERVER_NAME'),
            'accounts': []
        }
        for account in accounts:
            if account['cookies']:
                payload['accounts'].append({
                    'username': account['username'],
                    'password': account['password'],
                    'email_username': account['email_username'],
                    'email_password': account['email_password'],
                    'proxy': account['proxy'],
                    'cookies': account['cookies']
                })
        url = "http://91.108.227.166/add-accounts"
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Successfully added {result.get("message")} accounts")
            db.delete('accounts')
        else:
            logger.error(f'Failed to add accounts to DB. Reason: {response.text}')
        return {'message': 'Booster finished'}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Received request: {request.method} {request.url}")
    try:
        body = await request.json()
        print(f"Request body: {body}")
    except:
        pass
    response = await call_next(request)
    return response


def main_upload_loop(config, playwright):
    """
    Основная функция, ответственная за загрузку
    """
    start_time = time.time()
    timer = 0
    for account in config['accounts']:
        account_data = db.select_one('accounts', columns='*', where='username = ?', params=(account['name'],))
        profile = dolphin.get_profile_by_name(account['name'])
        uploader = Uploader(Auth(
            login=account_data['username'],
            password=account_data['password'],
            email=Email(account_data['email_username'], account_data['email_password']),
            profile=profile,
            playwright=playwright,
            db=db
        ))
        video = Video(name=account['video'], path=os.path.abspath(f'videos\\{account['video']}'),
                      description=account['title'])
        try:
            uploader.upload_videos([video])
        except:
            logger.log_err()
        uploader.auth.profile.stop()
        timer += 1
        if timer == len(db.select('accounts')):
            l = int(round((time.time() - start_time) // 60))
            timer = 1
            logger.info(f'All videos for this cycle uploaded, waiting for {30 - l} minutes')
            if l < 30:
                time.sleep(30 * 60)


def main_booster_loop(accounts, playwright):
    for account in accounts:
        ac = Auth(
            login=account['username'],
            password=account['password'],
            email=Email(account['email_username'], account['email_password']),
            profile=dolphin.get_profile_by_name(account['username']),
            playwright=playwright,
            db=db
        )
        pg = ac.authenticate()
        if pg != 1 and pg != 2:
            # booster = Booster(ac)
            # booster.start(pg)
            db.update('accounts',
                      data={'cookies': json.dumps(ac.export_cookies())},
                      where="username = ?",
                      params=(account['username'],))
        elif pg == 2:
            logger.error(f'Failed to boost profile {ac.login}')
        else:
            db.delete('accounts', where="username = ?", params=(account['username'],))
        ac.stop_browser()


# Функция, ответственная за получение логов
@app.get("/logs")
def get_logs(lines: int = 100):
    """
    Get recent logs from the log.txt file
    
    Args:
        lines (int): Number of last lines to retrieve (default: 100, max: 1000)
    """
    try:
        # Validate lines parameter
        if lines < 1:
            lines = 100
        elif lines > 1000:
            lines = 1000
            
        log_file = "log.txt"
        logs = []
        
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    selected_lines = all_lines[-lines:] if len(all_lines) >= lines else all_lines
                    logs = [line.strip() for line in selected_lines if line.strip()]
            except Exception as e:
                logs.append(f"Error reading {log_file}: {str(e)}")
        else:
            logs = [
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Log file 'log.txt' not found",
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] API server running on {os.environ.get('SERVER_NAME', 'unknown')}",
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Available endpoints: /upload/*, /booster/*, /logs, /docs"
            ]

        return {
            "logs": logs,
            "log_file": log_file,
            "lines_requested": lines,
            "lines_returned": len(logs),
            "server_name": os.environ.get('SERVER_NAME', 'unknown'),
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "logs": [f"Error getting logs: {str(e)}"],
            "log_file": "log.txt",
            "lines_requested": lines,
            "lines_returned": 0,
            "server_name": os.environ.get('SERVER_NAME', 'unknown'),
            "timestamp": time.time()
        }


app.include_router(upload_router)
app.include_router(booster_router)

if __name__ == '__main__':
    prepare_config()
