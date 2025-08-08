from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired,
    ChallengeRequired,
    TwoFactorRequired,
    PleaseWaitFewMinutes,
    RecaptchaChallengeForm
)
from instagrapi.mixins.challenge import ChallengeChoice
from instagrapi.types import StoryLink
import os
import time
import random
import json
import logging
import requests
import re
import base64
from datetime import datetime
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('instagram_upload.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AccountParser:
    """Парсер строки аккаунта из файла"""
    
    @staticmethod
    def parse_account_string(account_string: str) -> dict:
        """Парсит строку аккаунта"""
        try:
            logger.info("🔧 Парсим строку аккаунта...")
            
            line = account_string.strip()
            if not line or '||' not in line:
                raise ValueError(f"Неверный формат строки: {line}")
            
            # Разделяем на auth_part||data_part
            auth_part, data_part = line.split('||', 1)
            
            # Извлекаем username и password
            if ':' in auth_part:
                username, password = auth_part.split(':', 1)
            else:
                username = auth_part
                password = ""
            
            # Разделяем device_info и cookies_part
            parts = data_part.split('|')
            device_info = parts[0] if len(parts) > 0 else ""
            cookies_part = '|'.join(parts[1:]) if len(parts) > 1 else ""
            
            # Парсим device_info
            device_parts = device_info.split(';')
            android_device_id = device_parts[0] if len(device_parts) > 0 else ""
            uuid_main = device_parts[1] if len(device_parts) > 1 else ""
            phone_id = device_parts[2] if len(device_parts) > 2 else ""
            client_session_id = device_parts[3] if len(device_parts) > 3 else ""
            
            # Извлекаем данные из cookies
            sessionid_match = re.search(r'sessionid=([^;]+)', cookies_part)
            sessionid = sessionid_match.group(1) if sessionid_match else ""
            
            user_id_match = re.search(r'ds_user_id=(\d+)', cookies_part)
            user_id = user_id_match.group(1) if user_id_match else ""
            
            mid_match = re.search(r'mid=([^;]+)', cookies_part)
            mid = mid_match.group(1) if mid_match else ""
            
            result = {
                'username': username,
                'password': password,
                'uuid': uuid_main,
                'android_device_id': android_device_id,
                'phone_id': phone_id,
                'client_session_id': client_session_id,
                'sessionid': sessionid,
                'ds_user_id': user_id,
                'mid': mid,
                'valid': bool(sessionid and user_id and uuid_main)
            }
            
            logger.info("✅ Парсинг завершен успешно:")
            logger.info(f"   Username: {result['username']}")
            logger.info(f"   Valid: {result['valid']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга: {e}")
            return {'valid': False, 'error': str(e)}

class InstagramStoriesUploader:
    def __init__(self, account_data, proxy_url=None):
        logger.info("🚀 Инициализация InstagramStoriesUploader")
        
        self.account_data = account_data
        self.username = account_data.get('username')
        self.password = account_data.get('password')
        self.sessionid = account_data.get('sessionid')
        self.ds_user_id = account_data.get('ds_user_id')
        self.uuid = account_data.get('uuid')
        self.android_device_id = account_data.get('android_device_id')
        self.phone_id = account_data.get('phone_id')
        self.client_session_id = account_data.get('client_session_id')
        self.mid = account_data.get('mid')
        
        self.proxy_url = proxy_url
        self.session_file = f"session_{self.username}.json"
        
        # Инициализируем клиент
        self.client = Client()
        self.setup_device_settings()
        
        logger.info("✅ InstagramStoriesUploader инициализирован")
    
    def setup_device_settings(self):
        """Настройка устройства"""
        device_settings = {
            "cpu": "h1",
            "dpi": "640dpi",
            "model": "SM-G973F", 
            "device": "beyond1",
            "resolution": "1440x3040",
            "app_version": "269.0.0.18.75",
            "manufacturer": "samsung",
            "version_code": "314665256",
            "android_release": "10",
            "android_version": 29
        }
        
        self.client.set_device(device_settings)
        self.client.set_user_agent("Instagram 269.0.0.18.75 Android (29/10; 640dpi; 1440x3040; samsung; SM-G973F; beyond1; exynos9820; en_US; 314665256)")
        
        # Устанавливаем данные из аккаунта
        if self.uuid:
            self.client.uuid = self.uuid
            logger.info(f"🔑 UUID установлен: {self.uuid}")
        
        if self.android_device_id:
            self.client.android_device_id = self.android_device_id
            logger.info(f"📱 Device ID установлен: {self.android_device_id}")
        
        if self.phone_id:
            self.client.phone_id = self.phone_id
            logger.info(f"📞 Phone ID установлен: {self.phone_id}")
        
        if self.client_session_id:
            self.client.client_session_id = self.client_session_id
            logger.info(f"📱 Client Session ID установлен: {self.client_session_id}")
        
        self.client.set_country("US")
        self.client.set_locale("en_US")
        logger.info("✅ Настройки устройства установлены")
    
    def setup_proxy(self):
        """Настройка прокси"""
        if self.proxy_url:
            try:
                logger.info("🔧 Настройка прокси...")
                self.client.set_proxy(self.proxy_url)
                logger.info("✅ Прокси настроен")
                return True
            except Exception as e:
                logger.error(f"❌ Ошибка прокси: {e}")
                return False
        return True
    
    def verify_authentication(self) -> bool:
        """Проверка авторизации"""
        try:
            logger.info("🔍 Проверяем авторизацию...")
            
            response = self.client.private_request("accounts/current_user/?edit=true")
            
            if response and response.get('status') == 'ok':
                user_data = response.get('user', {})
                username = user_data.get('username', 'unknown')
                
                logger.info("✅ Авторизация подтверждена!")
                logger.info(f"👤 Username: {username}")
                
                print("✅ Авторизация подтверждена!")
                print(f"👤 Пользователь: {username}")
                
                return True
            else:
                logger.error(f"❌ Неверный ответ API: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки авторизации: {e}")
            return False
    
    def login_with_password(self):
        """Обычная авторизация через логин/пароль"""
        try:
            logger.info(f"🔐 Авторизация через логин/пароль @{self.username}")
            print(f"🔐 Вход в аккаунт @{self.username}")
            
            # Очищаем клиент
            self.client = Client()
            self.setup_device_settings()
            
            if self.proxy_url:
                self.client.set_proxy(self.proxy_url)
            
            # Вход
            self.client.login(self.username, self.password)
            
            # Проверяем авторизацию
            if self.verify_authentication():
                # Сохраняем сессию
                self.client.dump_settings(self.session_file)
                logger.info("💾 Сессия сохранена")
                return True
            else:
                logger.error("❌ Вход выполнен, но авторизация не работает")
                return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка авторизации: {e}")
            return False
    
    def create_story_links(self, urls_list):
        """
        Создание ссылок для сторис
        
        Parameters:
        -----------
        urls_list : List[str]
            Список URL для создания ссылок
            
        Returns:
        --------
        List[StoryLink]
        """
        links = []
        
        for url in urls_list:
            try:
                # ✅ ПРОСТОЕ создание ссылки
                link = StoryLink(webUri=url)
                links.append(link)
                logger.info(f"✅ Создана ссылка: {url}")
                print(f"🔗 Ссылка добавлена: {url}")
            except Exception as e:
                logger.error(f"❌ Ошибка создания ссылки {url}: {e}")
                print(f"❌ Ошибка создания ссылки {url}: {e}")
        
        return links
    
    def upload_video_story_with_links(self, video_path, caption="", links_urls=None):
        """
        ✅ ОСНОВНОЙ МЕТОД: Загрузка видео в сторис со ссылками
        
        Parameters:
        -----------
        video_path : str
            Путь к видео файлу
        caption : str, optional
            Подпись к сторис
        links_urls : List[str], optional
            Список ссылок для добавления
            
        Returns:
        --------
        Story or None
        """
        try:
            if not os.path.exists(video_path):
                logger.error(f"❌ Видео не найдено: {video_path}")
                return None
            
            logger.info("📱 Загружаем видео в сторис со ссылками...")
            print("📱 Загружаем видео в сторис со ссылками...")
            print(f"🎥 Файл: {Path(video_path).name}")
            print(f"📝 Подпись: {caption}")
            
            # Создаем ссылки
            links = []
            if links_urls:
                print(f"🔗 Добавляем {len(links_urls)} ссылок:")
                for url in links_urls:
                    print(f"   • {url}")
                links = self.create_story_links(links_urls)
            
            delay = random.uniform(2, 5)
            logger.info(f"⏳ Задержка: {delay:.2f} сек")
            time.sleep(delay)
            
            # ✅ ЗАГРУЖАЕМ видео со ссылками
            story = self.client.video_upload_to_story(
                path=Path(video_path),
                caption=caption,
                links=links
            )
            
            logger.info(f"✅ Видео сторис загружено: {story.pk}")
            print(f"✅ Видео сторис со ссылками опубликовано!")
            print(f"🔗 Story ID: {story.pk}")
            print(f"📊 Добавлено ссылок: {len(links)}")
            
            return story
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки видео сторис: {e}")
            print(f"❌ Ошибка загрузки видео сторис: {e}")
            return None
    
    def upload_photo_story_with_links(self, photo_path, caption="", links_urls=None):
        """
        ✅ Загрузка фото в сторис со ссылками
        
        Parameters:
        -----------
        photo_path : str
            Путь к фото файлу
        caption : str, optional
            Подпись к сторис
        links_urls : List[str], optional
            Список ссылок для добавления
            
        Returns:
        --------
        Story or None
        """
        try:
            if not os.path.exists(photo_path):
                logger.error(f"❌ Фото не найдено: {photo_path}")
                return None
            
            logger.info("📱 Загружаем фото в сторис со ссылками...")
            print("📱 Загружаем фото в сторис со ссылками...")
            print(f"📄 Файл: {Path(photo_path).name}")
            print(f"📝 Подпись: {caption}")
            
            # Создаем ссылки
            links = []
            if links_urls:
                print(f"🔗 Добавляем {len(links_urls)} ссылок:")
                for url in links_urls:
                    print(f"   • {url}")
                links = self.create_story_links(links_urls)
            
            delay = random.uniform(2, 5)
            logger.info(f"⏳ Задержка: {delay:.2f} сек")
            time.sleep(delay)
            
            # ✅ ЗАГРУЖАЕМ фото со ссылками
            story = self.client.photo_upload_to_story(
                path=Path(photo_path),
                caption=caption,
                links=links
            )
            
            logger.info(f"✅ Фото сторис загружено: {story.pk}")
            print(f"✅ Фото сторис со ссылками опубликовано!")
            print(f"🔗 Story ID: {story.pk}")
            print(f"📊 Добавлено ссылок: {len(links)}")
            
            return story
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки фото сторис: {e}")
            print(f"❌ Ошибка загрузки фото сторис: {e}")
            return None

def create_uploader_from_string(account_string: str, **kwargs):
    """Создает uploader из строки аккаунта"""
    account_data = AccountParser.parse_account_string(account_string)
    if not account_data.get('valid'):
        raise ValueError(f"Невалидная строка аккаунта: {account_data.get('error')}")
    
    return InstagramStoriesUploader(account_data=account_data, **kwargs)

def main():
    # ✅ КОНФИГУРАЦИЯ
    ACCOUNT_STRING = "Lorelai.Harrell.M134:lorelai!P7P||android-9e71ad1f7a1316cb;a3d198b5-739d-43c6-8963-43efca20b38d;92dcb9fe-9cfe-4561-8778-9684a7260ed3;92dcb9fe-9cfe-4561-8778-9684a7260ed3|mid=ZwISfAABAAEiQQ4Gdpgj-gFrQCp0;ds_user_id=76044084902;sessionid=76044084902%3ALHu5NnIHDgykl3%3A3%3AAYcaVG-aAyYsKRk4SPJXGPJEthhozGkHjwAy2PZYlA;IG-U-DS-USER-ID=76044084902;Authorization=Bearer IGT:2:eyJkc191c2VyX2lkIjoiNzYwNDQwODQ5MDIiLCJzZXNzaW9uaWQiOiI3NjA0NDA4NDkwMiUzQUxIdTVObklIRGd5a2wzJTNBMyUzQUFZY2FWRy1hQXlZc0tSazRTUEpYR1BKRXRoaG96R2tIandBeTJQWllsQSJ9;||"
    
    CONFIG = {
        "proxy_url": "http://UyBSdD63:rcx9ij7R@193.5.28.171:63686",
        
        # ✅ КОНТЕНТ ДЛЯ СТОРИС СО ССЫЛКАМИ
        "story_video_path": "/Users/ssuvorin/FindWork/8.mp4",
        "story_photo_path": "/Users/ssuvorin/FindWork/photo.jpg",  # если есть фото
        "story_caption": "📱 Новая история со ссылками! Swipe up ⬆️",
        
        # ✅ ССЫЛКИ ДЛЯ ДОБАВЛЕНИЯ В СТОРИС
        "story_links": [
            "https://facebook.com"
        ]
    }
    
    print("🚀 Instagram Stories Uploader со ссылками")
    
    try:
        # Создаем uploader
        uploader = create_uploader_from_string(
            ACCOUNT_STRING,
            proxy_url=CONFIG["proxy_url"]
        )
        
        if not uploader.setup_proxy():
            print("❌ Ошибка настройки прокси")
            return
        
        # ✅ АВТОРИЗАЦИЯ через логин/пароль (избегаем проблем с sessionid)
        if uploader.login_with_password():
            print("✅ Авторизация успешна!\n")
            
            # ✅ ВЫБОР ТИПА КОНТЕНТА
            print("🎯 Выберите что загрузить:")
            print("1. 🎥 Видео в сторис со ссылками")
            print("2. 📷 Фото в сторис со ссылками")
            
            try:
                choice = input("Введите номер (1-2): ").strip()
                
                if choice == "1":
                    print("\n🎥 Загружаем видео в сторис со ссылками...")
                    story = uploader.upload_video_story_with_links(
                        video_path=CONFIG["story_video_path"],
                        caption=CONFIG["story_caption"],
                        links_urls=CONFIG["story_links"]
                    )
                    if story:
                        print("🎉 Видео сторис со ссылками успешно опубликовано!")
                    
                elif choice == "2":
                    print("\n📷 Загружаем фото в сторис со ссылками...")
                    story = uploader.upload_photo_story_with_links(
                        photo_path=CONFIG["story_photo_path"],
                        caption=CONFIG["story_caption"],
                        links_urls=CONFIG["story_links"]
                    )
                    if story:
                        print("🎉 Фото сторис со ссылками успешно опубликовано!")
                    
                else:
                    print("❌ Неверный выбор")
                    
            except KeyboardInterrupt:
                print("\n❌ Операция отменена пользователем")
            
        else:
            print("❌ Ошибка авторизации")
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        print(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
