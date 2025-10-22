from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired,
    ChallengeRequired,
    TwoFactorRequired,
    PleaseWaitFewMinutes,
    RecaptchaChallengeForm
)
from instagrapi.mixins.challenge import ChallengeChoice
import os
import time
import random
import json
import logging
import requests
import re
import uuid
import base64
from datetime import datetime
from email_client import Email

# Use centralized logging - all logs go to django.log
logger = logging.getLogger('instgrapi_func.mainsess')

class AccountParser:
    """Автоматический парсер строки аккаунта"""
    
    @staticmethod
    def parse_account_string(account_string: str) -> dict:
        """
        Парсит строку аккаунта в формате:
        Username:Password||device_info|cookies_and_session_data
        
        Parameters:
        -----------
        account_string : str
            Полная строка аккаунта из файла
            
        Returns:
        --------
        dict : Распарсенные данные аккаунта
        """
        try:
            logger.info("🔧 Начинаем парсинг строки аккаунта...")
            
            # Очищаем строку
            line = account_string.strip()
            
            if not line or '||' not in line:
                raise ValueError(f"Неверный формат строки: {line}")
            
            # Разделяем на основные части: auth_part||data_part
            auth_part, data_part = line.split('||', 1)
            
            # Извлекаем username и password
            if ':' in auth_part:
                username, password = auth_part.split(':', 1)
            else:
                username = auth_part
                password = ""
            
            logger.info(f"👤 Username: {username}")
            logger.info(f"🔑 Password: {'*' * len(password)}")
            
            # Разделяем device_info и cookies_part
            parts = data_part.split('|')
            device_info = parts[0] if len(parts) > 0 else ""
            cookies_part = '|'.join(parts[1:]) if len(parts) > 1 else ""
            
            logger.info(f"📱 Device info: {device_info}")
            logger.info(f"🍪 Cookies part length: {len(cookies_part)}")
            
            # Парсим device_info: android-device_id;uuid1;uuid2;uuid3
            device_parts = device_info.split(';')
            android_device_id = device_parts[0] if len(device_parts) > 0 else ""
            uuid_main = device_parts[1] if len(device_parts) > 1 else ""
            phone_id = device_parts[2] if len(device_parts) > 2 else ""
            client_session_id = device_parts[3] if len(device_parts) > 3 else ""
            
            # Извлекаем данные из cookies_part
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
            
            # Формируем результат
            result = {
                # Основные данные
                'username': username,
                'password': password,
                
                # UUID данные
                'uuid': uuid_main,
                'android_device_id': android_device_id,
                'phone_id': phone_id,
                'client_session_id': client_session_id,
                
                # Сессионные данные
                'sessionid': sessionid,
                'ds_user_id': user_id,
                'mid': mid,
                'authorization_token': auth_token,
                'authorization_data': authorization_data,
                
                # Сырые данные
                'device_info_raw': device_info,
                'cookies_raw': cookies_part,
                
                # Валидность
                'valid': bool(sessionid and user_id and uuid_main)
            }
            
            logger.info("✅ Парсинг завершен успешно:")
            logger.info(f"   Username: {result['username']}")
            logger.info(f"   UUID: {result['uuid']}")
            logger.info(f"   Device ID: {result['android_device_id']}")
            logger.info(f"   SessionID: {result['sessionid'][:20]}...")
            logger.info(f"   User ID: {result['ds_user_id']}")
            logger.info(f"   Valid: {result['valid']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга строки: {e}")
            logger.error(f"   Строка: {account_string[:100]}...")
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
            logger.info(f"📡 2FA API Response: {json.dumps(data, indent=2)}")
            
            if data.get('ok') and 'data' in data and 'otp' in data['data']:
                otp_code = data['data']['otp']
                time_remaining = data['data'].get('timeRemaining', 0)
                
                logger.info(f"✅ 2FA код получен: {otp_code} (осталось времени: {time_remaining}сек)")
                return otp_code
            else:
                logger.error(f"❌ Неверный формат ответа 2FA API: {data}")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Ошибка при получении 2FA кода: {e}")
            return ""

class InstagramFullLogger:
    """Полное логирование всех API запросов и ответов Instagram"""
    
    def __init__(self, client):
        self.client = client
        self.setup_full_logging()
    
    def setup_full_logging(self):
        """Настройка полного логирования всех API взаимодействий"""
        logger.info("🔧 Настраиваем ПОЛНОЕ логирование API...")
        
        # Сохраняем оригинальные методы
        original_private_request = self.client.private_request
        original_public_request = self.client.public_request
        
        def logged_private_request(endpoint, data=None, params=None, **kwargs):
            """Логирование private API запросов"""
            logger.info("=" * 80)
            logger.info(f"📤 PRIVATE API REQUEST")
            logger.info("=" * 80)
            logger.info(f"🔗 Endpoint: {endpoint}")
            logger.info(f"📊 Method: POST")
            
            if data:
                if isinstance(data, dict):
                    logger.info(f"📋 Data (dict): {json.dumps(data, indent=2, ensure_ascii=False, default=str)}")
                elif isinstance(data, str):
                    logger.info(f"📋 Data (str): {data}")
                else:
                    logger.info(f"📋 Data (type: {type(data)}): {str(data)}")
            
            if params:
                logger.info(f"🔍 Params: {json.dumps(params, indent=2, ensure_ascii=False, default=str)}")
            
            if kwargs:
                logger.info(f"⚙️ Kwargs: {json.dumps(kwargs, indent=2, ensure_ascii=False, default=str)}")
            
            # Логируем headers
            if hasattr(self.client.private, 'headers'):
                logger.info(f"📨 Headers: {json.dumps(dict(self.client.private.headers), indent=2, ensure_ascii=False, default=str)}")
            
            try:
                # Выполняем запрос
                start_time = time.time()
                response = original_private_request(endpoint, data, params, **kwargs)
                duration = time.time() - start_time
                
                logger.info("=" * 80)
                logger.info(f"📥 PRIVATE API RESPONSE")
                logger.info("=" * 80)
                logger.info(f"⏱️ Duration: {duration:.3f}s")
                logger.info(f"✅ Success Response: {json.dumps(response, indent=2, ensure_ascii=False, default=str)}")
                
                return response
                
            except Exception as e:
                duration = time.time() - start_time
                logger.info("=" * 80)
                logger.info(f"📥 PRIVATE API ERROR RESPONSE")
                logger.info("=" * 80)
                logger.info(f"⏱️ Duration: {duration:.3f}s")
                logger.error(f"❌ Error: {e}")
                
                # Логируем last_json при ошибке
                if hasattr(self.client, 'last_json') and self.client.last_json:
                    logger.info(f"🔍 Last JSON: {json.dumps(self.client.last_json, indent=2, ensure_ascii=False, default=str)}")
                
                # Логируем last_response при ошибке
                if hasattr(self.client, 'last_response') and self.client.last_response:
                    logger.info(f"📡 Response Status: {self.client.last_response.status_code}")
                    logger.info(f"📨 Response Headers: {json.dumps(dict(self.client.last_response.headers), indent=2, ensure_ascii=False, default=str)}")
                    logger.info(f"📄 Response Text: {self.client.last_response.text}")
                
                raise
        
        def logged_public_request(url, **kwargs):
            """Логирование public API запросов"""
            logger.info("=" * 80)
            logger.info(f"📤 PUBLIC API REQUEST")
            logger.info("=" * 80)
            logger.info(f"🔗 URL: {url}")
            logger.info(f"⚙️ Kwargs: {json.dumps(kwargs, indent=2, ensure_ascii=False, default=str)}")
            
            try:
                start_time = time.time()
                response = original_public_request(url, **kwargs)
                duration = time.time() - start_time
                
                logger.info("=" * 80)
                logger.info(f"📥 PUBLIC API RESPONSE")
                logger.info("=" * 80)
                logger.info(f"⏱️ Duration: {duration:.3f}s")
                logger.info(f"✅ Response: {response}")
                
                return response
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"❌ Public API Error ({duration:.3f}s): {e}")
                raise
        
        # Подменяем методы
        self.client.private_request = logged_private_request
        self.client.public_request = logged_public_request
        
        logger.info("✅ Полное API логирование настроено")

class InstagramNativeUploader:
    def __init__(self, account_string: str, additional_config: dict = None):
        logger.info("🚀 Инициализация InstagramNativeUploader")
        
        # Парсим строку аккаунта
        self.account_data = AccountParser.parse_account_string(account_string)
        
        if not self.account_data.get('valid'):
            raise ValueError(f"Невалидная строка аккаунта: {self.account_data.get('error', 'Неизвестная ошибка')}")
        
        # Дополнительная конфигурация
        additional_config = additional_config or {}
        self.proxy_url = additional_config.get('proxy_url')
        self.email_login = additional_config.get('email_login')
        self.email_password = additional_config.get('email_password')
        self.twofa_token = additional_config.get('twofa_token')
        
        # Email клиент
        if self.email_login and self.email_password:
            try:
                self.email_client = Email(self.email_login, self.email_password)
                logger.info("✅ Email клиент создан")
            except Exception as e:
                logger.error(f"❌ Ошибка email клиента: {e}")
                self.email_client = None
        else:
            self.email_client = None
        
        # 2FA обработчик
        if self.twofa_token:
            self.twofa_handler = TwoFactorAuthHandler()
            logger.info("✅ 2FA обработчик создан")
        else:
            self.twofa_handler = None
        
        # Инициализируем клиент
        self.client = Client()
        
        # ✅ НАСТРАИВАЕМ ПОЛНОЕ ЛОГИРОВАНИЕ
        self.full_logger = InstagramFullLogger(self.client)
        
        # Настраиваем нативную сессию через auth.py
        self.setup_native_session()
        
        # Устанавливаем обработчики
        self.client.challenge_code_handler = self.challenge_code_handler
        
        logger.info("✅ InstagramNativeUploader инициализирован")
    
    def setup_native_session(self):
        """
        ✅ Настройка сессии через нативные методы auth.py
        """
        try:
            logger.info("🔧 Настраиваем нативную сессию через auth.py...")
            
            # Генерируем недостающие UUID
            def generate_uuid():
                return str(uuid.uuid4())
            
            # ✅ СОЗДАЕМ ПОЛНЫЕ SETTINGS согласно get_settings() в auth.py
            settings = {
                # UUID данные (используем из аккаунта + генерируем недостающие)
                "uuids": {
                    "phone_id": self.account_data.get('phone_id') or generate_uuid(),
                    "uuid": self.account_data.get('uuid'),
                    "client_session_id": self.account_data.get('client_session_id') or generate_uuid(),
                    "advertising_id": generate_uuid(),  # Всегда генерируем новый
                    "android_device_id": self.account_data.get('android_device_id'),
                    "request_id": generate_uuid(),  # Всегда генерируем новый
                    "tray_session_id": generate_uuid(),  # Всегда генерируем новый
                },
                
                # MID из данных аккаунта
                "mid": self.account_data.get('mid'),
                
                # Authorization data (главное!)
                "authorization_data": self.account_data.get('authorization_data', {
                    "ds_user_id": self.account_data.get('ds_user_id'),
                    "sessionid": self.account_data.get('sessionid'),
                    "should_use_header_over_cookies": True,
                }),
                
                # Cookies
                "cookies": {
                    "sessionid": self.account_data.get('sessionid'),
                    "ds_user_id": self.account_data.get('ds_user_id'),
                    "mid": self.account_data.get('mid'),
                    "csrftoken": self.generate_csrf_token(),
                },
                
                # Device settings (совместимые с auth.py)
                "device_settings": {
                    "app_version": "269.0.0.18.75",
                    "android_version": 29,
                    "android_release": "10",
                    "dpi": "640dpi",
                    "resolution": "1440x3040",
                    "manufacturer": "samsung",
                    "device": "beyond1",
                    "model": "SM-G973F",
                    "cpu": "h1",
                    "version_code": "314665256",
                },
                
                # User agent
                "user_agent": "Instagram 269.0.0.18.75 Android (29/10; 640dpi; 1440x3040; samsung; SM-G973F; beyond1; exynos9820; en_US; 314665256)",
                
                # Локализация
                "country": "US",
                "country_code": 1,
                "locale": "en_US",
                "timezone_offset": -28800,
                
                # Дополнительные данные
                "ig_u_rur": "",
                "ig_www_claim": "",
                "last_login": None,
            }
            
            logger.info("📋 Созданы полные settings:")
            logger.info(f"   Username: {self.account_data['username']}")
            logger.info(f"   UUID: {settings['uuids']['uuid']}")
            logger.info(f"   Android Device ID: {settings['uuids']['android_device_id']}")
            logger.info(f"   SessionID: {settings['authorization_data']['sessionid'][:20]}...")
            logger.info(f"   User ID: {settings['authorization_data']['ds_user_id']}")
            logger.info(f"   MID: {settings['mid']}")
            
            # ✅ ПРИМЕНЯЕМ SETTINGS через нативный метод set_settings() из auth.py
            logger.info("🔧 Применяем settings через set_settings() из auth.py...")
            self.client.set_settings(settings)
            
            logger.info("✅ Нативная сессия настроена через auth.py")
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки нативной сессии: {e}")
            raise
    
    def generate_csrf_token(self):
        """Генерация CSRF токена"""
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=64))
    
    def challenge_code_handler(self, username, choice):
        """Обработчик challenge с полным JSON логированием"""
        logger.info("=" * 80)
        logger.info("🔐 CHALLENGE HANDLER АКТИВИРОВАН С ПОЛНЫМ ЛОГИРОВАНИЕМ")
        logger.info("=" * 80)
        logger.info(f"👤 Username: {username}")
        logger.info(f"📧 Choice: {choice}")
        logger.info(f"📧 Choice Type: {type(choice)}")
        
        print(f"\n🔐 CHALLENGE ДЕТАЛИ:")
        print(f"👤 Username: {username}")
        print(f"📧 Choice: {choice}")
        
        # ✅ ПОЛНАЯ ДИАГНОСТИКА CHALLENGE JSON
        try:
            if hasattr(self.client, 'last_json') and self.client.last_json:
                logger.info("📋 ПОЛНАЯ ИНФОРМАЦИЯ О CHALLENGE:")
                logger.info("=" * 60)
                
                # Красиво форматируем JSON
                challenge_json = json.dumps(self.client.last_json, indent=2, ensure_ascii=False, default=str)
                logger.info(f"🔍 Challenge JSON:\n{challenge_json}")
                
                print("\n📋 ДЕТАЛИ CHALLENGE:")
                print("=" * 60)
                print(challenge_json)
                print("=" * 60)
                
            else:
                logger.warning("⚠️ Нет данных last_json от Instagram")
                print("⚠️ Нет данных last_json от Instagram")
                
        except Exception as e:
            logger.error(f"❌ Ошибка диагностики challenge: {e}")
            print(f"❌ Ошибка диагностики: {e}")
        
        # Email challenge обработка
        if choice == ChallengeChoice.EMAIL and self.email_client:
            logger.info("📧 Получаем код из email...")
            print("📧 Получение кода из email...")
            
            time.sleep(10)
            
            for attempt in range(3):
                try:
                    code = self.email_client.get_verification_code()
                    if code and len(code) == 6 and code.isdigit():
                        logger.info(f"✅ Код получен: {code}")
                        print(f"✅ Код получен: {code}")
                        return code
                except Exception as e:
                    logger.error(f"❌ Ошибка: {e}")
                
                if attempt < 2:
                    time.sleep(15)
        
        # Ручной ввод
        logger.info("⌨️ Переходим к ручному вводу")
        print("⌨️ Введите код из email/SMS:")
        
        while True:
            try:
                code = input("Введите 6-значный код: ").strip()
                if len(code) == 6 and code.isdigit():
                    logger.info(f"✅ Код введен: {code}")
                    return code
                else:
                    print("❌ Код должен содержать 6 цифр")
            except KeyboardInterrupt:
                logger.error("❌ Ввод кода прерван")
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
    
    def verify_native_session(self):
        """Упрощенная проверка валидности сессии"""
        try:
            logger.info("🔍 Проверяем нативную сессию...")
            
            # Простая проверка - любой authenticated запрос
            response = self.client.private_request("accounts/current_user/?edit=true")
            
            if response and response.get('status') == 'ok':
                username = response.get('user', {}).get('username', 'unknown')
                full_name = response.get('user', {}).get('full_name', '')
                
                logger.info("✅ Нативная сессия валидна!")
                logger.info(f"👤 Username: {username}")
                logger.info(f"📝 Full Name: {full_name}")
                
                print("✅ Авторизация через нативную сессию успешна!")
                print(f"👤 Пользователь: {username}")
                
                return True
            else:
                logger.error("❌ Неверный ответ от API")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки нативной сессии: {e}")
            return False

    
    def upload_reel(self, video_path, caption):
        """Загрузка рилса с полным логированием"""
        try:
            if not os.path.exists(video_path):
                logger.error(f"❌ Файл не найден: {video_path}")
                return None
            
            logger.info("🎬 Загружаем рилс через нативный клиент...")
            print("🎬 Загружаем рилс...")
            
            # Добавляем небольшую задержку
            delay = random.uniform(2, 5)
            logger.info(f"⏳ Задержка перед загрузкой: {delay:.2f}с")
            time.sleep(delay)
            
            media = self.client.clip_upload(
                path=video_path,
                caption=caption
            )
            
            logger.info(f"✅ Рилс загружен: {media.code}")
            print(f"✅ Рилс опубликован!")
            print(f"🔗 https://www.instagram.com/p/{media.code}/")
            
            return media
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки: {e}")
            print(f"❌ Ошибка загрузки: {e}")
            return None


def main():
    # ✅ ПРОСТАЯ КОНФИГУРАЦИЯ - ОДНА СТРОКА АККАУНТА
    ACCOUNT_STRING = "Itzel_Bryant_C432:itzel@A4A||android-android-8535sa7s;648333d1-0bd5-4d08-7e94-c1bf2cdfe708;4fa9206b-d663-4780-00e9-3d347b945589;4fa9206b-d663-4780-00e9-3d347b945589|mid=Zv2WtgABAAFRmIQPJb1vnPY9DgRe;ds_user_id=76236682361;sessionid=76236682361%3AAoCiIzI8NpDVvd%3A18%3AAYf16kMIlcoMHJPydY3Vkl0f3JRLyLDV9Z5SdQGoRQ;IG-U-DS-USER-ID=76236682361;Authorization=Bearer IGT:2:eyJkc191c2VyX2lkIjoiNzYyMzY2ODIzNjEiLCJzZXNzaW9uaWQiOiI3NjIzNjY4MjM2MSUzQUFvQ2lJekk4TnBEVnZkJTNBMTglM0FBWWYxNmtNSWxjb01ISlB5ZFkzVmtsMGYzSlJMeUxEVjlaNVNkUUdvUlEifQ==;||"
    
    # ✅ ДОПОЛНИТЕЛЬНАЯ КОНФИГУРАЦИЯ
    ADDITIONAL_CONFIG = {
        "proxy_url": "http://UyBSdD63:rcx9ij7R@45.89.231.68:64936",
        "email_login": "",  # Для challenge (если потребуется)
        "email_password": "",
        "twofa_token": "",  # Для 2FA (если потребуется)
        
        # Контент для загрузки
        "video_path": "/Users/ssuvorin/FindWork/1.mp4",
        "caption": """Улыбнулись? Тогда сделайте ещё один маленький, но важный шаг – поддержите меня! 😌Поставьте лайк ❤️ и подпишитесь 🔔, чтобы не пропустить ещё больше интересных и смешных роликов! #caspin11 #caspin12 #funny"""
    }
    
    print("🚀 Instagram Uploader с полным API логированием и автопарсингом")
    
    try:
        # Создаем uploader с автопарсингом строки
        uploader = InstagramNativeUploader(ACCOUNT_STRING, ADDITIONAL_CONFIG)
        
        # Настраиваем прокси
        if not uploader.setup_proxy():
            print("❌ Ошибка настройки прокси")
            return
        
        # Небольшая задержка
        time.sleep(random.uniform(2, 5))
        
        # Проверяем нативную сессию
        if uploader.verify_native_session():
            print("✅ Нативная авторизация успешна!")
            
            # Задержка перед загрузкой
            time.sleep(random.uniform(3, 7))
            
            # Загружаем рилс
            media = uploader.upload_reel(
                video_path=ADDITIONAL_CONFIG["video_path"],
                caption=ADDITIONAL_CONFIG["caption"]
            )
            
            if media:
                print("🎉 Успешно через нативные методы с полным логированием!")
            else:
                print("❌ Ошибка загрузки")
        else:
            print("❌ Ошибка нативной авторизации")
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        print(f"❌ Критическая ошибка: {e}")


if __name__ == "__main__":
    main()
