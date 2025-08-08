from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired,
    ChallengeRequired,
    TwoFactorRequired,
    PleaseWaitFewMinutes,
    RecaptchaChallengeForm
)
from instagrapi.mixins.challenge import ChallengeChoice
from instagrapi.types import StoryMention, StoryMedia, StoryLink, StoryHashtag, StoryLocation, StorySticker
import os
import time
import random
import json
import logging
import requests
import re
import base64
import string
import uuid
from datetime import datetime
from pathlib import Path
from email_client import Email

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('instagram_upload.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DeviceRandomizer:
    """Генератор случайных отпечатков устройств разных производителей"""
    
    # ✅ РАСШИРЕННЫЙ СПИСОК УСТРОЙСТВ РАЗНЫХ ПРОИЗВОДИТЕЛЕЙ
    DEVICE_DATABASE = [
        # Samsung Galaxy серия
        {"model": "SM-G973F", "device": "beyond1", "cpu": "exynos9820", "manufacturer": "samsung", "brand": "Samsung Galaxy S10"},
        {"model": "SM-G975F", "device": "beyond2", "cpu": "exynos9820", "manufacturer": "samsung", "brand": "Samsung Galaxy S10+"},
        {"model": "SM-G970F", "device": "beyond0", "cpu": "exynos9820", "manufacturer": "samsung", "brand": "Samsung Galaxy S10e"},
        {"model": "SM-N975F", "device": "d2s", "cpu": "exynos9825", "manufacturer": "samsung", "brand": "Samsung Galaxy Note10+"},
        {"model": "SM-G980F", "device": "x1s", "cpu": "exynos990", "manufacturer": "samsung", "brand": "Samsung Galaxy S20"},
        {"model": "SM-G985F", "device": "y2s", "cpu": "exynos990", "manufacturer": "samsung", "brand": "Samsung Galaxy S20+"},
        {"model": "SM-A515F", "device": "a51", "cpu": "exynos9611", "manufacturer": "samsung", "brand": "Samsung Galaxy A51"},
        
        # Xiaomi/Redmi серия
        {"model": "M2101K9G", "device": "alioth", "cpu": "sm8250", "manufacturer": "Xiaomi", "brand": "Xiaomi Mi 11"},
        {"model": "M2012K11AG", "device": "venus", "cpu": "sm8350", "manufacturer": "Xiaomi", "brand": "Xiaomi 11T Pro"},
        {"model": "M2007J20CG", "device": "lmi", "cpu": "sm8250", "manufacturer": "Xiaomi", "brand": "POCO F2 Pro"},
        {"model": "M2102K1G", "device": "munch", "cpu": "sm8250", "manufacturer": "Xiaomi", "brand": "POCO F3"},
        {"model": "21081111RG", "device": "lisa", "cpu": "sm7325", "manufacturer": "Xiaomi", "brand": "Xiaomi 11 Lite"},
        {"model": "22041219NY", "device": "peux", "cpu": "sm8250", "manufacturer": "Xiaomi", "brand": "POCO X4 Pro"},
        
        # OnePlus серия
        {"model": "LE2123", "device": "OnePlus9Pro", "cpu": "sm8350", "manufacturer": "OnePlus", "brand": "OnePlus 9 Pro"},
        {"model": "LE2117", "device": "OnePlus9", "cpu": "sm8350", "manufacturer": "OnePlus", "brand": "OnePlus 9"},
        {"model": "IN2023", "device": "OnePlus8T", "cpu": "sm8250", "manufacturer": "OnePlus", "brand": "OnePlus 8T"},
        {"model": "HD1903", "device": "OnePlus7T", "cpu": "sm8150", "manufacturer": "OnePlus", "brand": "OnePlus 7T"},
        {"model": "CPH2413", "device": "OnePlus10Pro", "cpu": "sm8450", "manufacturer": "OnePlus", "brand": "OnePlus 10 Pro"},
        
        # Google Pixel серия
        {"model": "Pixel 4", "device": "flame", "cpu": "sm8150", "manufacturer": "Google", "brand": "Google Pixel 4"},
        {"model": "Pixel 4 XL", "device": "coral", "cpu": "sm8150", "manufacturer": "Google", "brand": "Google Pixel 4 XL"},
        {"model": "Pixel 5", "device": "redfin", "cpu": "sm7250", "manufacturer": "Google", "brand": "Google Pixel 5"},
        {"model": "Pixel 6", "device": "oriole", "cpu": "gs101", "manufacturer": "Google", "brand": "Google Pixel 6"},
        {"model": "Pixel 6 Pro", "device": "raven", "cpu": "gs101", "manufacturer": "Google", "brand": "Google Pixel 6 Pro"},
        {"model": "Pixel 7", "device": "panther", "cpu": "gs201", "manufacturer": "Google", "brand": "Google Pixel 7"},
        
        # Huawei серия
        {"model": "ELS-NX9", "device": "HWELS", "cpu": "kirin990", "manufacturer": "HUAWEI", "brand": "Huawei P40 Pro"},
        {"model": "VOG-L29", "device": "HWVOG", "cpu": "kirin980", "manufacturer": "HUAWEI", "brand": "Huawei P30 Pro"},
        {"model": "LYA-L29", "device": "HWLYA", "cpu": "kirin980", "manufacturer": "HUAWEI", "brand": "Huawei Mate 20 Pro"},
        
        # Oppo серия
        {"model": "CPH2173", "device": "OP4F2F", "cpu": "sm8250", "manufacturer": "OPPO", "brand": "OPPO Find X3 Pro"},
        {"model": "CPH2127", "device": "OP4EC9", "cpu": "sm8150", "manufacturer": "OPPO", "brand": "OPPO Reno4 Pro"},
        {"model": "CPH2025", "device": "OP4A57", "cpu": "sm7125", "manufacturer": "OPPO", "brand": "OPPO A74"},
        
        # Vivo серия
        {"model": "V2056A", "device": "PD2056", "cpu": "sm8250", "manufacturer": "vivo", "brand": "Vivo X60 Pro+"},
        {"model": "V2031A", "device": "PD2031", "cpu": "sm7250", "manufacturer": "vivo", "brand": "Vivo S7"},
        {"model": "V2045", "device": "PD2045", "cpu": "sm6350", "manufacturer": "vivo", "brand": "Vivo Y53s"},
        
        # Realme серия  
        {"model": "RMX3085", "device": "RMX3085", "cpu": "sm8350", "manufacturer": "realme", "brand": "Realme GT"},
        {"model": "RMX2202", "device": "RMX2202", "cpu": "sm7125", "manufacturer": "realme", "brand": "Realme 8 Pro"},
        {"model": "RMX3031", "device": "RMX3031", "cpu": "sm8250", "manufacturer": "realme", "brand": "Realme X7 Max"},
    ]
    
    # Различные разрешения экранов
    RESOLUTIONS = [
        {"resolution": "1440x3040", "dpi": "640dpi"},  # QHD+
        {"resolution": "1440x2960", "dpi": "640dpi"},  # QHD+ Samsung
        {"resolution": "1080x2400", "dpi": "480dpi"},  # FHD+
        {"resolution": "1080x2340", "dpi": "480dpi"},  # FHD+ 19.5:9
        {"resolution": "1080x2280", "dpi": "480dpi"},  # FHD+ 19:9
        {"resolution": "1080x1920", "dpi": "420dpi"},  # FHD классический
        {"resolution": "720x1600", "dpi": "320dpi"},   # HD+ 
        {"resolution": "720x1560", "dpi": "320dpi"},   # HD+ 19.5:9
        {"resolution": "720x1280", "dpi": "320dpi"},   # HD классический
    ]
    
    # Версии Android
    ANDROID_VERSIONS = [
        {"android_version": 28, "android_release": "9"},
        {"android_version": 29, "android_release": "10"},
        {"android_version": 30, "android_release": "11"},
        {"android_version": 31, "android_release": "12"},
        {"android_version": 32, "android_release": "12L"},
        {"android_version": 33, "android_release": "13"},
        {"android_version": 34, "android_release": "14"},
    ]
    
    # Версии Instagram
    INSTAGRAM_VERSIONS = [
        {"app_version": "269.0.0.18.75", "version_code": "314665256"},
        {"app_version": "270.0.0.19.109", "version_code": "315467891"},
        {"app_version": "271.0.0.19.107", "version_code": "316234567"},
        {"app_version": "272.0.0.20.108", "version_code": "317123456"},
        {"app_version": "273.0.0.21.119", "version_code": "318987654"},
        {"app_version": "274.0.0.21.107", "version_code": "319876543"},
        {"app_version": "275.0.0.22.120", "version_code": "320765432"},
    ]
    
    # Локали и страны
    LOCALES = [
        {"country": "US", "country_code": 1, "locale": "en_US", "timezone_offset": -28800},
        {"country": "GB", "country_code": 44, "locale": "en_GB", "timezone_offset": 0},
        {"country": "CA", "country_code": 1, "locale": "en_CA", "timezone_offset": -21600},
        {"country": "AU", "country_code": 61, "locale": "en_AU", "timezone_offset": 36000},
        {"country": "DE", "country_code": 49, "locale": "de_DE", "timezone_offset": 3600},
        {"country": "FR", "country_code": 33, "locale": "fr_FR", "timezone_offset": 3600},
        {"country": "IT", "country_code": 39, "locale": "it_IT", "timezone_offset": 3600},
        {"country": "ES", "country_code": 34, "locale": "es_ES", "timezone_offset": 3600},
    ]
    
    @staticmethod
    def generate_android_device_id() -> str:
        """Генерирует случайный Android Device ID"""
        random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
        return f"android-{random_part}"
    
    @staticmethod 
    def generate_uuid() -> str:
        """Генерирует случайный UUID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_phone_number() -> str:
        """Генерирует случайный номер телефона"""
        return f"+1{random.randint(2000000000, 9999999999)}"
    
    @staticmethod
    def generate_mac_address() -> str:
        """Генерирует случайный MAC адрес"""
        mac = [0x02, 0x00, 0x00,
               random.randint(0x00, 0x7f),
               random.randint(0x00, 0xff),
               random.randint(0x00, 0xff)]
        return ':'.join(map(lambda x: "%02x" % x, mac))
    
    @classmethod
    def generate_random_device_settings(cls) -> dict:
        """Генерирует полный набор случайных настроек устройства"""
        
        # Выбираем случайные компоненты
        device_info = random.choice(cls.DEVICE_DATABASE)
        resolution_info = random.choice(cls.RESOLUTIONS) 
        android_info = random.choice(cls.ANDROID_VERSIONS)
        instagram_info = random.choice(cls.INSTAGRAM_VERSIONS)
        locale_info = random.choice(cls.LOCALES)
        
        settings = {
            # Основные параметры устройства
            **device_info,
            **resolution_info,
            **android_info,
            **instagram_info,
            **locale_info,
            
            # Уникальные идентификаторы
            "android_device_id": cls.generate_android_device_id(),
            "uuid": cls.generate_uuid(),
            "phone_id": cls.generate_uuid(),
            "client_session_id": cls.generate_uuid(),
            "advertising_id": cls.generate_uuid(),
            "request_id": cls.generate_uuid(),
            "tray_session_id": cls.generate_uuid(),
            
            # Дополнительные параметры
            "phone_number": cls.generate_phone_number(),
            "mac_address": cls.generate_mac_address(),
        }
        
        logger.info("🎲 Сгенерированы настройки нового устройства:")
        logger.info(f"   📱 Устройство: {settings['brand']}")
        logger.info(f"   🏭 Производитель: {settings['manufacturer']}")
        logger.info(f"   📱 Модель: {settings['model']}")
        logger.info(f"   🔍 Разрешение: {settings['resolution']} ({settings['dpi']})")
        logger.info(f"   🤖 Android: {settings['android_release']} (API {settings['android_version']})")
        logger.info(f"   📲 Instagram: {settings['app_version']}")
        logger.info(f"   🌍 Локаль: {settings['locale']} ({settings['country']})")
        logger.info(f"   🆔 Device ID: {settings['android_device_id']}")
        
        return settings
    
    @classmethod
    def generate_user_agent(cls, device_settings: dict) -> str:
        """Генерирует User Agent на основе настроек устройства"""
        return (
            f"Instagram {device_settings['app_version']} "
            f"Android ({device_settings['android_version']}/{device_settings['android_release']}; "
            f"{device_settings['dpi']}; {device_settings['resolution']}; "
            f"{device_settings['manufacturer']}; {device_settings['model']}; "
            f"{device_settings['device']}; {device_settings['cpu']}; "
            f"{device_settings['locale']}; {device_settings['version_code']})"
        )

class AccountParser:
    """Парсер строки аккаунта из файла"""
    
    @staticmethod
    def parse_account_string(account_string: str) -> dict:
        """
        Парсит строку аккаунта в формате:
        Username:Password||device_info|cookies_and_session_data
        """
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
            
            # Извлекаем Authorization Bearer токен
            auth_match = re.search(r'Authorization=Bearer\s+([^;]+)', cookies_part)
            auth_token = auth_match.group(1) if auth_match else ""
            
            # Декодируем Authorization для получения authorization_data
            authorization_data = {}
            if auth_token and auth_token.startswith('IGT:2:'):
                try:
                    b64_part = auth_token.split('IGT:2:')[1]
                    decoded = base64.b64decode(b64_part).decode()
                    authorization_data = json.loads(decoded)
                    logger.info("✅ Authorization data декодирован")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка декодирования authorization: {e}")
            
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
                'authorization_token': auth_token,
                'authorization_data': authorization_data,
                'device_info_raw': device_info,
                'cookies_raw': cookies_part,
                'valid': bool(sessionid and user_id and uuid_main) or bool(username and password)
            }
            
            logger.info("✅ Парсинг завершен успешно:")
            logger.info(f"   Username: {result['username']}")
            logger.info(f"   SessionID: {result['sessionid'][:20]}..." if result['sessionid'] else "   SessionID: None")
            logger.info(f"   Valid: {result['valid']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга: {e}")
            return {'valid': False, 'error': str(e)}

class TwoFactorAuthHandler:
    """Обработчик 2FA кодов через внешний API"""
    
    def __init__(self, api_base_url: str = "https://2fa.fb.rip/api/otp"):
        self.api_base_url = api_base_url
        
    def get_2fa_code(self, account_token: str) -> str:
        """Получение 2FA кода из внешнего API"""
        try:
            url = f"{self.api_base_url}/{account_token}"
            logger.info(f"🔐 Получаем 2FA код с API: {url}")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"📡 Ответ API: {data}")
            
            if data.get('ok') and 'data' in data and 'otp' in data['data']:
                otp_code = data['data']['otp']
                time_remaining = data['data'].get('timeRemaining', 0)
                
                logger.info(f"✅ 2FA код получен: {otp_code} (осталось времени: {time_remaining}сек)")
                return otp_code
            else:
                logger.error(f"❌ Неверный формат ответа API: {data}")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Ошибка при получении 2FA кода: {e}")
            return ""

class InstagramReelsUploader:
    def __init__(self, account_data=None, username=None, password=None, proxy_url=None,
                 email_login=None, email_password=None, twofa_token=None, randomize_device=True):
        logger.info("🚀 Инициализация InstagramReelsUploader")
        
        # Поддержка двух режимов инициализации
        if account_data:
            # Режим с парсингом строки аккаунта
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
            self.authorization_data = account_data.get('authorization_data', {})
        else:
            # Обычный режим
            self.account_data = {}
            self.username = username
            self.password = password
            self.sessionid = None
            self.ds_user_id = None
            self.uuid = None
            self.android_device_id = None
            self.phone_id = None
            self.client_session_id = None
            self.mid = None
            self.authorization_data = {}
        
        self.proxy_url = proxy_url
        self.email_login = email_login
        self.email_password = email_password
        self.twofa_token = twofa_token
        
        # ✅ РАНДОМИЗАЦИЯ УСТРОЙСТВА
        self.randomize_device = randomize_device
        if randomize_device:
            logger.info("🎲 Генерируем новый случайный отпечаток устройства...")
            self.device_settings = DeviceRandomizer.generate_random_device_settings()
            
            print("🎲 Новый отпечаток устройства сгенерирован!")
            print(f"📱 Устройство: {self.device_settings['brand']}")
            print(f"🏭 Производитель: {self.device_settings['manufacturer']}")
            print(f"🔍 Разрешение: {self.device_settings['resolution']} ({self.device_settings['dpi']})")
            print(f"🤖 Android: {self.device_settings['android_release']}")
            print(f"📲 Instagram: {self.device_settings['app_version']}")
        else:
            self.device_settings = None
        
        # Создаем уникальное имя сессии для рандомизированных устройств
        if randomize_device and self.device_settings:
            device_hash = self.device_settings['android_device_id'][-8:]
            self.session_file = f"session_{self.username}_{device_hash}.json"
        else:
            self.session_file = f"session_{self.username}.json"
        
        # Email клиент
        if email_login and email_password:
            try:
                self.email_client = Email(email_login, email_password)
                logger.info("✅ Email клиент создан")
            except Exception as e:
                logger.error(f"❌ Ошибка email клиента: {e}")
                self.email_client = None
        else:
            self.email_client = None
        
        # 2FA обработчик
        if twofa_token:
            self.twofa_handler = TwoFactorAuthHandler()
            logger.info("✅ 2FA обработчик создан")
        else:
            self.twofa_handler = None
        
        # Инициализируем клиент
        self.client = Client()
        self.setup_device_settings()
        
        # Устанавливаем обработчики
        self.client.challenge_code_handler = self.challenge_code_handler
        self.client.two_factor_code_handler = self.two_factor_code_handler
        
        logger.info("✅ InstagramReelsUploader инициализирован")
    
    def setup_device_settings(self):
        """Настройка устройства с рандомизацией или использование данных аккаунта"""
        if self.randomize_device and self.device_settings:
            # ✅ ИСПОЛЬЗУЕМ РАНДОМНЫЕ НАСТРОЙКИ
            device_config = {
                "cpu": self.device_settings["cpu"],
                "dpi": self.device_settings["dpi"],
                "model": self.device_settings["model"],
                "device": self.device_settings["device"], 
                "resolution": self.device_settings["resolution"],
                "app_version": self.device_settings["app_version"],
                "manufacturer": self.device_settings["manufacturer"],
                "version_code": self.device_settings["version_code"],
                "android_release": self.device_settings["android_release"],
                "android_version": self.device_settings["android_version"]
            }
            
            # Устанавливаем настройки устройства
            self.client.set_device(device_config)
            
            # UUID и идентификаторы из рандомизации
            self.client.uuid = self.device_settings["uuid"]
            self.client.android_device_id = self.device_settings["android_device_id"]
            self.client.phone_id = self.device_settings["phone_id"]
            self.client.client_session_id = self.device_settings["client_session_id"]
            
            # User Agent
            user_agent = DeviceRandomizer.generate_user_agent(self.device_settings)
            self.client.set_user_agent(user_agent)
            
            # Локализация из рандомных настроек
            self.client.set_country(self.device_settings["country"])
            self.client.set_locale(self.device_settings["locale"])
            
            logger.info("✅ Рандомизированные настройки устройства применены")
            
        else:
            # ✅ ИСПОЛЬЗУЕМ СТАНДАРТНЫЕ ИЛИ ИЗ АККАУНТА НАСТРОЙКИ
            device_settings = {
                "cpu": "exynos9820",
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
            
            # Устанавливаем данные из аккаунта если доступны
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
            
            logger.info("✅ Стандартные настройки устройства установлены")
        
        # Прокси
        if self.proxy_url:
            self.client.set_proxy(self.proxy_url)
    
    def login_by_sessionid(self) -> bool:
        """Авторизация через sessionid"""
        if not self.sessionid:
            logger.warning("❌ SessionID не предоставлен")
            return False
        
        try:
            logger.info("🔑 Авторизация через sessionid...")
            logger.info(f"🔑 SessionID: {self.sessionid[:20]}...")
            
            # Устанавливаем полные настройки сессии
            settings = {
                "cookies": {
                    "sessionid": self.sessionid,
                    "ds_user_id": self.ds_user_id,
                    "mid": self.mid,
                },
                "authorization_data": self.authorization_data or {
                    "ds_user_id": self.ds_user_id,
                    "sessionid": self.sessionid,
                    "should_use_header_over_cookies": True,
                },
                "mid": self.mid,
                "user_agent": self.client.user_agent,
                "device_settings": self.client.device_settings,
                "uuids": {
                    "uuid": self.client.uuid,
                    "android_device_id": self.client.android_device_id,
                    "phone_id": self.client.phone_id,
                    "client_session_id": self.client.client_session_id,
                }
            }
            
            # Применяем настройки
            self.client.set_settings(settings)
            logger.info("🔧 Настройки сессии применены")
            
            # Проверяем валидность
            try:
                user_info = self.client.account_info()
                
                # Обновляем username если не был указан
                if not self.username:
                    self.username = user_info.username
                    logger.info(f"👤 Username получен из сессии: {self.username}")
                
                logger.info("✅ Авторизация через sessionid успешна!")
                logger.info(f"👤 Username: {user_info.username}")
                
                print("✅ Авторизация через sessionid успешна!")
                print(f"👤 Пользователь: {user_info.username}")
                
                # Сохраняем дамп сессии
                self.client.dump_settings(self.session_file)
                logger.info("💾 Дамп сессии сохранен")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ SessionID недействителен: {e}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка авторизации через sessionid: {e}")
            return False
    
    def two_factor_code_handler(self, username, two_factor_identifier):
        """Обработчик 2FA login"""
        logger.info("=" * 80)
        logger.info("🔐 2FA LOGIN HANDLER АКТИВИРОВАН")
        logger.info("=" * 80)
        logger.info(f"👤 Username: {username}")
        logger.info(f"🔑 Two Factor Identifier: {two_factor_identifier}")
        
        print(f"\n🔐 ТРЕБУЕТСЯ 2FA КОД ДЛЯ ВХОДА")
        print(f"👤 Аккаунт: {username}")
        
        # Автоматическое получение 2FA кода
        if self.twofa_handler and self.twofa_token:
            logger.info("🤖 Получаем 2FA код автоматически...")
            print("🤖 Автоматическое получение 2FA кода...")
            
            for attempt in range(3):
                logger.info(f"🔍 Попытка {attempt + 1}/3")
                print(f"🔍 Попытка {attempt + 1}/3...")
                
                twofa_code = self.twofa_handler.get_2fa_code(self.twofa_token)
                
                if twofa_code and len(twofa_code) == 6 and twofa_code.isdigit():
                    logger.info(f"✅ 2FA код получен автоматически: {twofa_code}")
                    print(f"✅ 2FA код получен: {twofa_code}")
                    return twofa_code
                else:
                    logger.warning(f"⚠️ 2FA код неверного формата: {twofa_code}")
                
                if attempt < 2:
                    time.sleep(5)
        
        # Ручной ввод
        logger.info("⌨️ Ручной ввод 2FA кода")
        print("\n⌨️ Введите 2FA код из приложения:")
        
        while True:
            try:
                code = input("Введите 6-значный 2FA код: ").strip()
                
                if len(code) == 6 and code.isdigit():
                    logger.info(f"✅ 2FA код введен: {code}")
                    return code
                else:
                    print("❌ 2FA код должен содержать 6 цифр")
                    
            except KeyboardInterrupt:
                logger.error("❌ Ввод 2FA кода прерван")
                raise Exception("Ввод 2FA кода прерван")
    
    def challenge_code_handler(self, username, choice):
        """Обработчик challenge (подозрительная активность)"""
        logger.info("=" * 80)
        logger.info("🔐 CHALLENGE HANDLER АКТИВИРОВАН")
        logger.info("=" * 80)
        logger.info(f"👤 Username: {username}")
        logger.info(f"📧 Choice: {choice}")
        
        print(f"\n🔐 Challenge для {username}, способ: {choice}")
        
        # Email challenge
        if choice == ChallengeChoice.EMAIL and self.email_client:
            logger.info("📧 Получаем challenge код из email...")
            print("📧 Получение кода из email...")
            
            time.sleep(10)
            
            for attempt in range(3):
                try:
                    code = self.email_client.get_verification_code()
                    if code and len(code) == 6 and code.isdigit():
                        logger.info(f"✅ Challenge код получен: {code}")
                        print(f"✅ Код получен: {code}")
                        return code
                except Exception as e:
                    logger.error(f"❌ Ошибка: {e}")
                
                if attempt < 2:
                    time.sleep(15)
        
        # Ручной ввод
        print("⌨️ Введите код из email/SMS:")
        
        while True:
            try:
                code = input("Введите 6-значный код: ").strip()
                if len(code) == 6 and code.isdigit():
                    logger.info(f"✅ Challenge код введен: {code}")
                    return code
                else:
                    print("❌ Код должен содержать 6 цифр")
            except KeyboardInterrupt:
                logger.error("❌ Ввод challenge кода прерван")
                raise Exception("Ввод кода прерван")
    
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
    
    def login_with_session_management(self):
        """
        Универсальная авторизация с fallback логикой:
        1. Загрузка существующего дампа сессии
        2. Авторизация через sessionid (если доступен)
        3. Обычная авторизация с логином/паролем/2FA
        """
        try:
            logger.info(f"🔑 Начинаем универсальную авторизацию @{self.username}")
            
            # ПРИОРИТЕТ 1: Загружаем существующий дамп сессии (только если НЕ рандомизируем устройство)
            if not self.randomize_device and os.path.exists(self.session_file):
                logger.info("📂 Загружаем существующий дамп сессии...")
                try:
                    self.client.load_settings(self.session_file)
                    self.client.account_info()  # Проверяем валидность
                    logger.info("✅ Дамп сессии валиден")
                    print("✅ Авторизация через сохраненную сессию")
                    return True
                except Exception as e:
                    logger.warning(f"⚠️ Дамп сессии недействителен: {e}")
            
            # ПРИОРИТЕТ 2: Авторизация через sessionid (если доступен и НЕ рандомизируем)
            if not self.randomize_device and self.sessionid:
                logger.info("🔑 Пытаемся авторизацию через sessionid...")
                if self.login_by_sessionid():
                    return True
                else:
                    logger.warning("⚠️ SessionID не сработал, переходим к обычному входу")
            
            # ПРИОРИТЕТ 3: Обычная авторизация с логином/паролем
            if self.username and self.password:
                if self.randomize_device:
                    logger.info("🎲 Обычная авторизация с НОВЫМ рандомным устройством...")
                    print("🎲 Вход с новым устройством для лучших просмотров...")
                else:
                    logger.info("🔐 Обычная авторизация с логином и паролем...")
                
                try:
                    self.client.login(self.username, self.password)
                    
                except TwoFactorRequired as e:
                    logger.info("🔐 Требуется 2FA")
                    
                    two_factor_info = e.two_factor_info if hasattr(e, 'two_factor_info') else {}
                    two_factor_identifier = two_factor_info.get('two_factor_identifier', '')
                    
                    verification_code = self.two_factor_code_handler(self.username, two_factor_identifier)
                    
                    if verification_code:
                        self.client.login(
                            self.username, 
                            self.password,
                            verification_code=verification_code
                        )
                        logger.info("✅ 2FA авторизация успешна!")
                        print("✅ 2FA авторизация успешна!")
                    else:
                        logger.error("❌ Не удалось получить 2FA код")
                        return False
                
                # Сохраняем дамп сессии после успешного входа
                self.client.dump_settings(self.session_file)
                logger.info("💾 Дамп сессии сохранен после входа")
                
                logger.info("✅ Обычная авторизация завершена успешно")
                print("✅ Авторизация успешна!")
                return True
            
            logger.error("❌ Нет доступных методов авторизации")
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка авторизации: {e}")
            return False
    
    def upload_reel(self, video_path, caption):
        """Загрузка рилса с рандомизированным устройством"""
        try:
            if not os.path.exists(video_path):
                logger.error(f"❌ Файл не найден: {video_path}")
                return None
            
            if self.randomize_device:
                logger.info("🎬 Загружаем рилс с рандомизированным устройством...")
                print("🎬 Загружаем рилс с новым устройством...")
                print(f"📱 Устройство: {self.device_settings['brand']}")
            else:
                logger.info("🎬 Загружаем рилс...")
                print("🎬 Загружаем рилс...")
            
            delay = random.uniform(2, 5)
            logger.info(f"⏳ Задержка: {delay:.2f} сек")
            time.sleep(delay)
            
            media = self.client.clip_upload(
                path=video_path,
                caption=caption
            )
            
            logger.info(f"✅ Рилс загружен: {media.code}")
            print(f"✅ Рилс опубликован!")
            print(f"🔗 https://www.instagram.com/p/{media.code}/")
            
            if self.randomize_device:
                print(f"🎲 Устройство: {self.device_settings['brand']}")
                print(f"🆔 Device ID: {self.device_settings['android_device_id'][-12:]}")
                print("📈 Ожидайте лучшие показатели просмотров с новым устройством!")
            
            return media
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки: {e}")
            print(f"❌ Ошибка загрузки: {e}")
            return None
    
    def upload_video_story_with_links(self, video_path, caption="", links_urls=None):
        """Загрузка видео в сторис со ссылками"""
        try:
            if not os.path.exists(video_path):
                logger.error(f"❌ Видео не найдено: {video_path}")
                return None
            
            logger.info("📱 Загружаем видео в сторис...")
            print("📱 Загружаем видео в сторис...")
            
            # Создаем ссылки
            links = []
            if links_urls:
                for url in links_urls:
                    try:
                        link = StoryLink(webUri=url)
                        links.append(link)
                        logger.info(f"✅ Создана ссылка: {url}")
                        print(f"🔗 Ссылка добавлена: {url}")
                    except Exception as e:
                        logger.error(f"❌ Ошибка создания ссылки {url}: {e}")
            
            delay = random.uniform(2, 5)
            logger.info(f"⏳ Задержка: {delay:.2f} сек")
            time.sleep(delay)
            
            story = self.client.video_upload_to_story(
                path=Path(video_path),
                caption=caption,
                links=links
            )
            
            logger.info(f"✅ Видео сторис загружено: {story.pk}")
            print(f"✅ Видео сторис со ссылками опубликовано!")
            print(f"🔗 Story ID: {story.pk}")
            
            if self.randomize_device:
                print(f"🎲 С новым устройством: {self.device_settings['brand']}")
            
            return story
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки видео сторис: {e}")
            print(f"❌ Ошибка загрузки видео сторис: {e}")
            return None

# Вспомогательная функция для создания uploader из строки аккаунта
def create_uploader_from_string(account_string: str, randomize_device=True, **kwargs):
    """Создает uploader из строки аккаунта с опцией рандомизации"""
    account_data = AccountParser.parse_account_string(account_string)
    if not account_data.get('valid'):
        raise ValueError(f"Невалидная строка аккаунта: {account_data.get('error')}")
    
    return InstagramReelsUploader(
        account_data=account_data, 
        randomize_device=randomize_device,
        **kwargs
    )

def main():
    # Конфигурация аккаунта
    ACCOUNT_STRING = "Lorelai.Harrell.M134:lorelai!P7P||android-9e71ad1f7a1316cb;a3d198b5-739d-43c6-8963-43efca20b38d;92dcb9fe-9cfe-4561-8778-9684a7260ed3;92dcb9fe-9cfe-4561-8778-9684a7260ed3|mid=ZwISfAABAAEiQQ4Gdpgj-gFrQCp0;ds_user_id=76044084902;sessionid=76044084902%3ALHu5NnIHDgykl3%3A3%3AAYcaVG-aAyYsKRk4SPJXGPJEthhozGkHjwAy2PZYlA;IG-U-DS-USER-ID=76044084902;Authorization=Bearer IGT:2:eyJkc191c2VyX2lkIjoiNzYwNDQwODQ5MDIiLCJzZXNzaW9uaWQiOiI3NjA0NDA4NDkwMiUzQUxIdTVObklIRGd5a2wzJTNBMyUzQUFZY2FWRy1hQXlZc0tSazRTUEpYR1BKRXRoaG96R2tIandBeTJQWllsQSJ9;||"
    
    CONFIG = {
        "proxy_url": "http://UyBSdD63:rcx9ij7R@193.5.28.171:63686",
        "email_login": "",
        "email_password": "",
        "twofa_token": "",
        
        # ===== 📱 КОНТЕНТ =====
        "reel_video_path": "/Users/ssuvorin/FindWork/2.mp4",
        "reel_caption": """Улыбнулись? Тогда сделайте ещё один маленький, но важный шаг – поддержите меня! 😌Поставьте лайк ❤️ и подпишитесь 🔔, чтобы не пропустить ещё больше интересных и смешных роликов! #caspin11 #caspin12 #funny""",
        
        "story_video_path": "/Users/ssuvorin/FindWork/2.mp4",
        "story_caption": "📱 Новая история с новым устройством!",
        "story_links": ["https://t.me/your_channel", "https://github.com/username"],
    }
    
    print("🚀 Instagram Uploader с рандомизацией устройств разных производителей")
    print("🎯 Цель: Повышение просмотров рилсов за счет нового device fingerprint\n")
    
    try:
        # ✅ ВЫБОР РЕЖИМА РАБОТЫ
        print("🎯 Выберите режим работы:")
        print("1. 🎲 С рандомизацией устройства (для лучших просмотров)")
        print("2. 🔧 Стандартный режим (без рандомизации)")
        
        mode_choice = input("Введите номер (1-2): ").strip()
        
        if mode_choice == "1":
            randomize_device = True
            print("\n🎲 Режим рандомизации активирован!")
        elif mode_choice == "2":
            randomize_device = False
            print("\n🔧 Стандартный режим активирован!")
        else:
            print("❌ Неверный выбор, используем режим рандомизации по умолчанию")
            randomize_device = True
        
        # Создаем uploader
        uploader = create_uploader_from_string(
            ACCOUNT_STRING,
            randomize_device=randomize_device,
            proxy_url=CONFIG["proxy_url"],
            email_login=CONFIG["email_login"],
            email_password=CONFIG["email_password"],
            twofa_token=CONFIG["twofa_token"]
        )
        
        if not uploader.setup_proxy():
            print("❌ Ошибка настройки прокси")
            return
        
        # Авторизация
        if uploader.login_with_session_management():
            print("✅ Авторизация успешна!\n")
            
            # ✅ ВЫБОР КОНТЕНТА
            print("🎯 Выберите что загрузить:")
            print("1. 🎬 Рилс (видео в ленту)")
            print("2. 📱 Видео в сторис со ссылками")
            print("3. 🎭 И рилс, и сторис")
            
            try:
                choice = input("Введите номер (1-3): ").strip()
                
                if choice == "1":
                    # Загружаем рилс
                    print("\n🎬 Загружаем рилс...")
                    media = uploader.upload_reel(
                        video_path=CONFIG["reel_video_path"],
                        caption=CONFIG["reel_caption"]
                    )
                    
                    if media:
                        print("🎉 Рилс успешно опубликован!")
                        if randomize_device:
                            print("📈 Новое устройство должно дать лучшие просмотры!")
                    
                elif choice == "2":
                    # Загружаем сторис
                    print("\n📱 Загружаем видео в сторис...")
                    story = uploader.upload_video_story_with_links(
                        video_path=CONFIG["story_video_path"],
                        caption=CONFIG["story_caption"],
                        links_urls=CONFIG["story_links"]
                    )
                    
                    if story:
                        print("🎉 Сторис со ссылками опубликовано!")
                    
                elif choice == "3":
                    # Загружаем все
                    print("\n🎭 Загружаем и рилс, и сторис...")
                    
                    # Рилс
                    print("\n1️⃣ Загружаем рилс...")
                    reel = uploader.upload_reel(
                        video_path=CONFIG["reel_video_path"],
                        caption=CONFIG["reel_caption"]
                    )
                    
                    # Задержка между загрузками
                    if reel:
                        delay = random.uniform(10, 20)
                        print(f"⏳ Ждем {delay:.1f} сек между загрузками...")
                        time.sleep(delay)
                        
                        # Сторис
                        print("\n2️⃣ Загружаем сторис...")
                        story = uploader.upload_video_story_with_links(
                            video_path=CONFIG["story_video_path"],
                            caption=CONFIG["story_caption"],
                            links_urls=CONFIG["story_links"]
                        )
                        
                        success_count = sum([bool(reel), bool(story)])
                        print(f"\n🎉 Успешно загружено: {success_count}/2!")
                        if randomize_device:
                            print("📈 Рандомизация устройства активна - ждите лучших результатов!")
                
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
