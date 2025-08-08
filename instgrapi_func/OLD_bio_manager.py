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
import base64
from datetime import datetime
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bio_manager.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AccountParser:
    """Парсер строки аккаунта (используем существующий)"""
    
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
                'valid': bool(username and password)
            }
            
            logger.info("✅ Парсинг завершен успешно:")
            logger.info(f"   Username: {result['username']}")
            logger.info(f"   Valid: {result['valid']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга: {e}")
            return {'valid': False, 'error': str(e)}

class InstagramBioManager:
    """Менеджер для изменения биографии Instagram"""
    
    def __init__(self, account_data, proxy_url=None):
        logger.info("🚀 Инициализация InstagramBioManager")
        
        self.account_data = account_data
        self.username = account_data.get('username')
        self.password = account_data.get('password')
        self.uuid = account_data.get('uuid')
        self.android_device_id = account_data.get('android_device_id')
        self.phone_id = account_data.get('phone_id')
        self.client_session_id = account_data.get('client_session_id')
        
        self.proxy_url = proxy_url
        self.session_file = f"session_{self.username}.json"
        
        # Инициализируем клиент
        self.client = Client()
        self.setup_device_settings()
        
        logger.info("✅ InstagramBioManager инициализирован")
    
    def setup_device_settings(self):
        """Настройка устройства с использованием данных аккаунта"""
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
        
        if self.proxy_url:
            self.client.set_proxy(self.proxy_url)
        
        logger.info("✅ Настройки устройства установлены")
    
    def login(self):
        """Авторизация"""
        try:
            logger.info(f"🔐 Авторизация @{self.username}")
            print(f"🔐 Вход в аккаунт @{self.username}")
            
            # Проверяем существующую сессию
            if os.path.exists(self.session_file):
                logger.info("📂 Загружаем существующую сессию...")
                try:
                    self.client.load_settings(self.session_file)
                    
                    # Проверяем валидность
                    account_info = self.client.account_info()
                    logger.info("✅ Сессия валидна")
                    print("✅ Авторизация через сохраненную сессию")
                    return True
                except Exception as e:
                    logger.warning(f"⚠️ Сессия недействительна: {e}")
            
            # Новый вход
            self.client.login(self.username, self.password)
            
            # Проверяем авторизацию
            account_info = self.client.account_info()
            
            logger.info("✅ Авторизация успешна!")
            logger.info(f"👤 Username: {account_info.username}")
            
            print("✅ Авторизация успешна!")
            print(f"👤 Пользователь: {account_info.username}")
            
            # Сохраняем сессию
            self.client.dump_settings(self.session_file)
            logger.info("💾 Сессия сохранена")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка авторизации: {e}")
            return False
    
    def get_current_profile(self):
        """
        Получение текущих данных профиля
        
        Returns:
        --------
        dict : Текущие данные профиля
        """
        try:
            logger.info("📖 Получаем текущие данные профиля...")
            
            # Используем метод account_info() из account.py
            account_info = self.client.account_info()
            
            profile_data = {
                'username': account_info.username,
                'full_name': account_info.full_name,
                'biography': account_info.biography,
                'external_url': account_info.external_url,
                'email': account_info.email,
                'phone_number': account_info.phone_number,
                'is_private': account_info.is_private,
            }
            
            logger.info(f"📖 Текущая биография: {profile_data['biography']}")
            logger.info(f"📧 Email: {profile_data['email']}")
            logger.info(f"🔗 Внешняя ссылка: {profile_data['external_url']}")
            
            print("📖 Текущие данные профиля:")
            print(f"👤 Имя: {profile_data['full_name']}")
            print(f"📝 Биография: {profile_data['biography']}")
            print(f"🔗 Ссылка: {profile_data['external_url']}")
            
            return profile_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения профиля: {e}")
            return None
    
    def change_biography(self, new_biography, preserve_other_fields=True):
        """
        Изменение биографии через нативный метод account_edit()
        
        Parameters:
        -----------
        new_biography : str
            Новая биография
        preserve_other_fields : bool
            Сохранять ли остальные поля профиля
            
        Returns:
        --------
        Account or None
        """
        try:
            logger.info("📝 Изменяем биографию...")
            print("📝 Изменяем биографию...")
            print(f"📝 Новая биография: {new_biography}")
            
            if preserve_other_fields:
                # Получаем текущие данные для сохранения остальных полей
                current_profile = self.get_current_profile()
                if not current_profile:
                    logger.error("❌ Не удалось получить текущие данные профиля")
                    return None
                
                # ✅ ИСПОЛЬЗУЕМ НАТИВНЫЙ МЕТОД account_edit() из account.py
                updated_account = self.client.account_edit(
                    username=current_profile['username'],
                    full_name=current_profile['full_name'],
                    biography=new_biography,  # ← Новая биография
                    external_url=current_profile['external_url'] or "",
                    email=current_profile['email'] or "",
                    phone_number=current_profile['phone_number'] or ""
                )
            else:
                # Минимальное обновление только биографии
                updated_account = self.client.account_edit(biography=new_biography)
            
            logger.info("✅ Биография успешно изменена!")
            logger.info(f"📝 Новая биография: {updated_account.biography}")
            
            print("✅ Биография успешно изменена!")
            print(f"📝 Новая биография: {updated_account.biography}")
            
            return updated_account
            
        except Exception as e:
            logger.error(f"❌ Ошибка изменения биографии: {e}")
            print(f"❌ Ошибка изменения биографии: {e}")
            return None
    
    def change_external_url(self, new_url):
        """
        Изменение внешней ссылки
        
        Parameters:
        -----------
        new_url : str
            Новая внешняя ссылка
        """
        try:
            logger.info(f"🔗 Изменяем внешнюю ссылку на: {new_url}")
            print(f"🔗 Изменяем внешнюю ссылку на: {new_url}")
            
            # Используем нативный метод set_external_url() из account.py
            result = self.client.set_external_url(new_url)
            
            if result and result.get('status') == 'ok':
                logger.info("✅ Внешняя ссылка успешно изменена!")
                print("✅ Внешняя ссылка успешно изменена!")
                return True
            else:
                logger.error(f"❌ Ошибка изменения ссылки: {result}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка изменения внешней ссылки: {e}")
            print(f"❌ Ошибка изменения внешней ссылки: {e}")
            return False
    
    def change_profile_info(self, **kwargs):
        """
        Универсальное изменение данных профиля
        
        Parameters:
        -----------
        **kwargs : dict
            Поля для изменения: full_name, biography, external_url, etc.
        """
        try:
            logger.info("🔧 Изменяем данные профиля...")
            print("🔧 Изменяем данные профиля...")
            
            # Получаем текущие данные
            current_profile = self.get_current_profile()
            if not current_profile:
                return None
            
            # Объединяем текущие данные с новыми
            update_data = {
                'username': current_profile['username'],
                'full_name': current_profile['full_name'],
                'biography': current_profile['biography'],
                'external_url': current_profile['external_url'] or "",
                'email': current_profile['email'] or "",
                'phone_number': current_profile['phone_number'] or ""
            }
            
            # Обновляем только переданные поля
            update_data.update(kwargs)
            
            logger.info("📊 Изменяемые поля:")
            for key, value in kwargs.items():
                logger.info(f"   {key}: {value}")
                print(f"📝 {key}: {value}")
            
            # Применяем изменения
            updated_account = self.client.account_edit(**update_data)
            
            logger.info("✅ Данные профиля успешно изменены!")
            print("✅ Данные профиля успешно изменены!")
            
            return updated_account
            
        except Exception as e:
            logger.error(f"❌ Ошибка изменения профиля: {e}")
            print(f"❌ Ошибка изменения профиля: {e}")
            return None
    
    def batch_biography_changes(self, biography_list, delay_range=(10, 30)):
        """
        Пакетное изменение биографий с задержками
        
        Parameters:
        -----------
        biography_list : List[str]
            Список биографий для последовательного изменения
        delay_range : Tuple[int, int]
            Диапазон случайной задержки между изменениями (секунды)
        """
        try:
            logger.info(f"🔄 Начинаем пакетное изменение {len(biography_list)} биографий")
            print(f"🔄 Начинаем пакетное изменение {len(biography_list)} биографий")
            
            results = []
            
            for i, bio in enumerate(biography_list, 1):
                logger.info(f"📝 Изменение {i}/{len(biography_list)}")
                print(f"\n📝 Изменение {i}/{len(biography_list)}")
                print(f"➡️ Новая биография: {bio}")
                
                # Изменяем биографию
                result = self.change_biography(bio)
                results.append(bool(result))
                
                if result:
                    print("✅ Успешно изменено!")
                else:
                    print("❌ Ошибка изменения")
                    break
                
                # Задержка между изменениями (кроме последнего)
                if i < len(biography_list):
                    delay = random.uniform(*delay_range)
                    logger.info(f"⏳ Ждем {delay:.1f} сек перед следующим изменением...")
                    print(f"⏳ Ждем {delay:.1f} сек...")
                    time.sleep(delay)
            
            success_count = sum(results)
            logger.info(f"✅ Завершено: {success_count}/{len(biography_list)} успешных изменений")
            print(f"\n🎉 Завершено: {success_count}/{len(biography_list)} успешных изменений!")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка пакетного изменения: {e}")
            print(f"❌ Ошибка пакетного изменения: {e}")
            return []

# Вспомогательные функции
def create_bio_manager(account_string: str, proxy_url=None):
    """Создает био-менеджер из строки аккаунта"""
    account_data = AccountParser.parse_account_string(account_string)
    if not account_data.get('valid'):
        raise ValueError(f"Невалидная строка аккаунта: {account_data.get('error')}")
    
    return InstagramBioManager(account_data, proxy_url)

def quick_bio_change(account_string: str, new_bio: str, proxy_url=None):
    """Быстрое изменение биографии"""
    try:
        manager = create_bio_manager(account_string, proxy_url)
        
        if not manager.login():
            return False
        
        result = manager.change_biography(new_bio)
        return bool(result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка быстрого изменения: {e}")
        return False

def main():
    """Основная функция с примерами использования"""
    
    # ✅ КОНФИГУРАЦИЯ
    ACCOUNT_STRING = "Lorelai.Harrell.M134:lorelai!P7P||android-9e71ad1f7a1316cb;a3d198b5-739d-43c6-8963-43efca20b38d;92dcb9fe-9cfe-4561-8778-9684a7260ed3;92dcb9fe-9cfe-4561-8778-9684a7260ed3|mid=ZwISfAABAAEiQQ4Gdpgj-gFrQCp0;ds_user_id=76044084902;sessionid=76044084902%3ALHu5NnIHDgykl3%3A3%3AAYcaVG-aAyYsKRk4SPJXGPJEthhozGkHjwAy2PZYlA;IG-U-DS-USER-ID=76044084902;Authorization=Bearer IGT:2:eyJkc191c2VyX2lkIjoiNzYwNDQwODQ5MDIiLCJzZXNzaW9uaWQiOiI3NjA0NDA4NDkwMiUzQUxIdTVObklIRGd5a2wzJTNBMyUzQUFZY2FWRy1hQXlZc0tSazRTUEpYR1BKRXRoaG96R2tIandBeTJQWllsQSJ9;||"
    
    CONFIG = {
        "proxy_url": "http://UyBSdD63:rcx9ij7R@193.5.28.171:63686",
        
        # ✅ БИОГРАФИИ ДЛЯ ИЗМЕНЕНИЯ
        "single_bio": "facebook.com",
        
        # "batch_bios": [
        #     "📱 Добро пожаловать на мою страницу! ✨",
        #     "🎯 Достигаем целей вместе! 💪 #success",
        #     "💎 Качественный контент каждый день 🚀",
        #     "🌟 Следите за обновлениями! #updates",
        #     "🔥 Живи ярко, твори смело! #inspiration"
        # ]
    }
    
    print("🚀 Instagram Bio Manager")
    
    try:
        # Создаем менеджер
        manager = create_bio_manager(
            ACCOUNT_STRING,
            proxy_url=CONFIG["proxy_url"]
        )
        
        # Авторизация
        if not manager.login():
            print("❌ Ошибка авторизации")
            return
        
        print("✅ Авторизация успешна!\n")
        
        # ✅ ВЫБОР ДЕЙСТВИЯ
        print("🎯 Выберите действие:")
        print("1. 📖 Показать текущий профиль")
        print("2. 📝 Изменить биографию")
        print("3. 🔗 Изменить внешнюю ссылку")
        print("4. 🔄 Пакетное изменение биографий")
        print("5. 🔧 Изменить несколько полей")
        
        try:
            choice = input("Введите номер (1-5): ").strip()
            
            if choice == "1":
                # Показать текущий профиль
                print("\n📖 Получаем текущие данные профиля...")
                manager.get_current_profile()
                
            elif choice == "2":
                # Изменить биографию
                print("\n📝 Изменяем биографию...")
                result = manager.change_biography(CONFIG["single_bio"])
                if result:
                    print("🎉 Биография успешно изменена!")
                
            elif choice == "3":
                # Изменить внешнюю ссылку
                new_url = input("🔗 Введите новую ссылку: ").strip()
                if new_url:
                    result = manager.change_external_url(new_url)
                    if result:
                        print("🎉 Ссылка успешно изменена!")
                else:
                    print("❌ Ссылка не может быть пустой")
                
            elif choice == "4":
                # Пакетное изменение
                print("\n🔄 Начинаем пакетное изменение биографий...")
                results = manager.batch_biography_changes(
                    CONFIG["batch_bios"],
                    delay_range=(5, 15)  # Задержка 5-15 сек
                )
                success_count = sum(results)
                print(f"🎉 Завершено: {success_count}/{len(CONFIG['batch_bios'])} успешно!")
                
            elif choice == "5":
                # Изменить несколько полей
                print("\n🔧 Изменяем несколько полей профиля...")
                
                new_name = input("👤 Введите новое имя (или Enter для пропуска): ").strip()
                new_bio = input("📝 Введите новую биографию (или Enter для пропуска): ").strip()
                new_url = input("🔗 Введите новую ссылку (или Enter для пропуска): ").strip()
                
                update_data = {}
                if new_name:
                    update_data['full_name'] = new_name
                if new_bio:
                    update_data['biography'] = new_bio
                if new_url:
                    update_data['external_url'] = new_url
                
                if update_data:
                    result = manager.change_profile_info(**update_data)
                    if result:
                        print("🎉 Профиль успешно обновлен!")
                else:
                    print("❌ Не выбрано ни одного поля для изменения")
                
            else:
                print("❌ Неверный выбор")
                
        except KeyboardInterrupt:
            print("\n❌ Операция отменена пользователем")
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        print(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
