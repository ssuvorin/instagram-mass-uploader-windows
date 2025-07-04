#!/usr/bin/env python
import os
import sys
import json
import argparse
import logging
import time
import re
import shutil
import random
import string
import uuid
from pathlib import Path
from datetime import datetime
from PIL import Image, ExifTags
import subprocess
import traceback
from dotenv import load_dotenv

# Suppress verbose Playwright logging before any imports
os.environ['PLAYWRIGHT_QUIET'] = '1'
os.environ['PLAYWRIGHT_DISABLE_COLORS'] = '1'
os.environ['DEBUG'] = ''
os.environ['PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS'] = '1'

# Configure logging to suppress verbose Playwright logs
logging.getLogger('playwright').setLevel(logging.CRITICAL)
logging.getLogger('playwright._impl').setLevel(logging.CRITICAL)
logging.getLogger('playwright.sync_api').setLevel(logging.CRITICAL)

# Load environment variables from .env file
load_dotenv()

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем новые модули Dolphin Anty вместо старых
from bot.src.instagram_uploader.browser_dolphin import get_browser, get_page, close_browser
from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
from bot.src.instagram_uploader.auth_playwright import Auth, verify_ip_address
from bot.src.instagram_uploader.upload_playwright import Upload
from bot.src import logger
from bot.src.videos import get_videos_list, get_videos_by_folders
from bot.src.instagram_uploader.util import random_delay, realistic_type, human_action

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Вывод в консоль
        logging.FileHandler('bot/log.txt', encoding='utf-8')  # Вывод в файл
    ]
)
logger = logging.getLogger(__name__)

def check_proxy_config(proxy_data):
    """
    Проверяет конфигурацию прокси и возвращает информацию о текущем IP
    """
    if not proxy_data:
        logger.error("❌ Прокси не указан, но он обязателен для работы бота")
        return None
        
    logger.info("🔄 Инициализация временного браузера для проверки прокси...")
    # Создаем временный профиль Dolphin для проверки прокси
    api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
    if not api_key:
        logger.error("❌ Dolphin API token not found in environment variables")
        return None
    
    dolphin = DolphinAnty(api_key=api_key)
    
    try:
        # Создаем временный профиль с прокси
        temp_profile_data = {
            "name": f"Temp Profile - {uuid.uuid4().hex[:8]}",
            "tags": ["temp"],
            "browserType": "chrome",
            "proxy": {
                "mode": "manual",
                "host": proxy_data.get('host'),
                "port": proxy_data.get('port'),
                "username": proxy_data.get('username', ""),
                "password": proxy_data.get('password', ""),
                "type": proxy_data.get('type', "http")
            }
        }
        
        profile_response = dolphin.create_profile(temp_profile_data)
        if not profile_response or not profile_response.get("success"):
            logger.error("❌ Не удалось создать временный профиль для проверки прокси")
            return None
            
        profile_id = profile_response.get("browserProfileId")
        
        # Запускаем профиль
        logger.info("🔄 Запуск временного профиля для проверки прокси...")
        success, automation_data = dolphin.start_profile(profile_id, headless=True)
        
        if not success:
            logger.error("❌ Не удалось запустить временный профиль")
            dolphin.delete_profile(profile_id)
            return None
            
        # Создаем браузер
        browser = get_browser(headless=True, profile_id=profile_id)
        page = get_page(browser)
        
        if not page:
            logger.error("❌ Не удалось создать страницу браузера")
            close_browser(browser)
            dolphin.delete_profile(profile_id)
            return None
        
        logger.info("🌐 Проверка работы прокси...")
        ip = verify_ip_address(page)
        if ip:
            logger.info(f"✅ Прокси работает! Используемый IP-адрес: {ip}")
            result = ip
        else:
            logger.error("❌ Не удалось проверить IP-адрес или прокси не работает")
            result = None
    finally:
        # Закрываем браузер
        if 'browser' in locals():
            logger.info("🔒 Закрытие временного браузера...")
            close_browser(browser)
        
        # Удаляем временный профиль
        if 'profile_id' in locals():
            logger.info("🗑️ Удаление временного профиля...")
            dolphin.delete_profile(profile_id)
        
    return result

def prepare_video_for_upload(video_path):
    """
    Подготавливает видео для загрузки:
    - Копирует из временной директории в постоянную с человекоподобным именем
    - Возвращает путь к подготовленному файлу
    """
    try:
        logger.info(f"🔄 Подготовка видео для загрузки: {video_path}")
        
        # Проверяем, существует ли файл
        if not os.path.exists(video_path):
            logger.error(f"❌ Видео не найдено: {video_path}")
            return None
        
        # Создаем директорию для подготовленных видео, если её нет
        prepared_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prepared_videos")
        os.makedirs(prepared_dir, exist_ok=True)
        
        # Генерируем человекоподобное имя файла
        current_date = datetime.now().strftime("%Y%m%d")
        
        # Более реалистичные имена файлов
        human_prefixes = ["video", "clip", "moment", "insta", "story", "reel", "memory", "capture", "shot"]
        human_names = [
            "vacation", "friends", "family", "party", "trip", "beach", "fun", 
            "memories", "moments", "sunset", "weekend", "birthday", "holiday",
            "summer", "winter", "spring", "autumn", "concert", "wedding",
            "graduation", "celebration", "adventure", "travel", "food", "pet"
        ]
        human_suffixes = ["edit", "final", "share", "post", "upload", "cut", "trim", "export"]
        
        # Создаем реалистичное имя файла
        random_prefix = random.choice(human_prefixes)
        random_name = random.choice(human_names)
        
        # С вероятностью 50% добавляем суффикс
        if random.random() > 0.5:
            random_suffix = random.choice(human_suffixes)
            base_name = f"{random_prefix}_{random_name}_{random_suffix}"
        else:
            base_name = f"{random_prefix}_{random_name}"
        
        # С вероятностью 70% добавляем дату
        if random.random() > 0.3:
            # Выбираем формат даты
            date_formats = [
                current_date,  # YYYYMMDD
                datetime.now().strftime("%d%m%Y"),  # DDMMYYYY
                datetime.now().strftime("%m%d"),  # MMDD
                datetime.now().strftime("%Y_%m_%d"),  # YYYY_MM_DD
                datetime.now().strftime("%d_%m_%Y"),  # DD_MM_YYYY
            ]
            date_str = random.choice(date_formats)
            base_name = f"{base_name}_{date_str}"
        
        # С вероятностью 30% добавляем случайные цифры
        if random.random() > 0.7:
            random_digits = ''.join(random.choices(string.digits, k=random.randint(2, 4)))
            base_name = f"{base_name}_{random_digits}"
        
        # Получаем расширение файла
        file_ext = os.path.splitext(video_path)[1]
        
        # Создаем новое имя файла
        new_filename = f"{base_name}{file_ext}"
        new_path = os.path.join(prepared_dir, new_filename)
        
        logger.info(f"🔄 Копирование видео из {video_path} в {new_path}")
        
        # Копируем файл
        shutil.copy2(video_path, new_path)
        logger.info(f"✅ Видео успешно скопировано с новым именем: {new_filename}")
        
        # Добавляем случайную задержку для имитации человеческого поведения
        random_delay(1, 3)
        
        # Проверяем, нужно ли изменить метаданные видео
        if random.random() > 0.5:
            logger.info(f"🔄 Изменение метаданных видео для большей естественности...")
            try:
                # Используем exiftool для изменения метаданных, если он установлен
                if shutil.which('exiftool'):
                    # Генерируем случайную дату создания в пределах последних 7 дней
                    days_ago = random.randint(0, 7)
                    hours_ago = random.randint(0, 23)
                    minutes_ago = random.randint(0, 59)
                    
                    # Создаем команду для изменения даты создания
                    cmd = [
                        'exiftool',
                        f'-CreateDate-={days_ago}:0:0 {hours_ago}:{minutes_ago}:0',
                        f'-ModifyDate-={days_ago}:0:0 {hours_ago}:{minutes_ago}:0',
                        new_path
                    ]
                    
                    # Выполняем команду
                    subprocess.run(cmd, capture_output=True, text=True)
                    logger.info(f"✅ Метаданные видео успешно изменены")
                else:
                    logger.info(f"ℹ️ exiftool не установлен, пропуск изменения метаданных")
            except Exception as e:
                logger.info(f"⚠️ Не удалось изменить метаданные: {str(e)}")
        
        return new_path
    except Exception as e:
        logger.error(f"❌ Ошибка при копировании файла: {str(e)}")
        return None

def main():
    logger.info("🚀 Запуск Instagram Uploader Bot (Playwright + Dolphin Anty)")
    
    parser = argparse.ArgumentParser(description='Instagram Uploader Bot')
    parser.add_argument('--account', required=True, help='Path to account data JSON file')
    parser.add_argument('--videos', required=True, help='Path to videos list JSON file')
    parser.add_argument('--proxy', help='Path to proxy data JSON file')
    parser.add_argument('--non-interactive', action='store_true', help='Run in non-interactive mode (no user prompts)')
    parser.add_argument('--visible', action='store_true', help='Force browser to run in visible mode')
    parser.add_argument('--dolphin-token', help='Dolphin Anty API token')
    args = parser.parse_args()
    
    # Определяем, нужно ли запускать браузер в видимом режиме
    # Приоритет: 1) аргумент --visible, 2) переменная окружения HEADLESS=0, 3) переменная окружения VISIBLE=1
    headless_mode = True  # По умолчанию - скрытый режим
    
    if args.visible:
        headless_mode = False
        logger.info("ℹ️ Браузер будет запущен в видимом режиме (указан аргумент --visible)")
    elif os.environ.get("HEADLESS", "1") == "0":
        headless_mode = False
        logger.info("ℹ️ Браузер будет запущен в видимом режиме (HEADLESS=0)")
    elif os.environ.get("VISIBLE", "0") == "1":
        headless_mode = False
        logger.info("ℹ️ Браузер будет запущен в видимом режиме (VISIBLE=1)")
    else:
        logger.info("ℹ️ Браузер будет запущен в скрытом режиме (headless)")
    
    # Получаем API токен Dolphin Anty
    dolphin_token = args.dolphin_token or os.environ.get("DOLPHIN_API_TOKEN")
    if not dolphin_token:
        logger.warning("⚠️ API токен Dolphin Anty не указан! Используйте --dolphin-token или переменную окружения DOLPHIN_API_TOKEN")
    
    logger.info(f"📋 Параметры запуска: account={args.account}, videos={args.videos}, proxy={args.proxy if args.proxy else 'не используется'}, non-interactive={args.non_interactive}, visible={not headless_mode}")

    # Инициализируем browser как None перед try-блоком
    browser = None

    try:
        # Загружаем данные аккаунта
        logger.info(f"📂 Загрузка данных аккаунта из файла: {args.account}")
        try:
            with open(args.account, 'r') as f:
                account_data = json.load(f)
            logger.info(f"✅ Данные аккаунта успешно загружены: {account_data.get('username')}")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки данных аккаунта: {str(e)}")
            return 1
        
        # Загружаем данные прокси (если указаны)
        proxy_data = None
        if args.proxy:
            logger.info(f"🔄 Загрузка данных прокси из файла: {args.proxy}")
            try:
                with open(args.proxy, 'r') as f:
                    proxy_data = json.load(f)
                logger.info(f"✅ Данные прокси успешно загружены: {proxy_data.get('host')}:{proxy_data.get('port')}")
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки данных прокси: {str(e)}")
                return 1
        
        # Проверяем конфигурацию прокси (если он указан)
        if proxy_data:
            ip_info = check_proxy_config(proxy_data)
            if not ip_info and not args.non_interactive:
                user_answer = input("Прокси не работает. Продолжить без прокси? (y/n): ")
                if user_answer.lower() != 'y':
                    logger.error("❌ Выход по запросу пользователя")
                    return 1
                proxy_data = None  # Отключаем прокси
        
        # Загружаем список видео
        logger.info(f"🔄 Загрузка списка видео из файла: {args.videos}")
        try:
            with open(args.videos, 'r') as f:
                video_paths = json.load(f)
            logger.info(f"✅ Список видео успешно загружен, найдено {len(video_paths)} видео")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки списка видео: {str(e)}")
            return 1

        # Проверяем, есть ли у аккаунта уже созданный профиль Dolphin
        dolphin_profile_id = account_data.get('dolphin_profile_id')
        
        # Инициализируем браузер
        logger.info("🔄 Инициализация браузера с Dolphin Anty...")
        
        if dolphin_profile_id:
            # Используем существующий профиль
            logger.info(f"🔍 Используем существующий профиль Dolphin: {dolphin_profile_id}")
            browser = get_browser(
                headless=headless_mode, 
                api_token=dolphin_token, 
                profile_id=dolphin_profile_id
            )
        else:
            # Создаем новый профиль для аккаунта
            logger.info(f"🔧 Создаем новый профиль Dolphin для аккаунта {account_data.get('username')}")
            browser = get_browser(
                headless=headless_mode, 
                proxy=proxy_data, 
                api_token=dolphin_token, 
                account_data=account_data
            )
            
            # Сохраняем ID созданного профиля в данных аккаунта
            if browser and hasattr(browser, 'dolphin_profile_id') and browser.dolphin_profile_id:
                dolphin_profile_id = browser.dolphin_profile_id
                account_data['dolphin_profile_id'] = dolphin_profile_id
                logger.info(f"✅ Профиль Dolphin {dolphin_profile_id} сохранен для аккаунта")
                
                # Сохраняем обновленные данные аккаунта обратно в файл
                try:
                    with open(args.account, 'w') as f:
                        json.dump(account_data, f, indent=2)
                    logger.info("✅ Данные аккаунта обновлены с ID профиля Dolphin")
                except Exception as e:
                    logger.error(f"❌ Не удалось сохранить обновленные данные аккаунта: {str(e)}")
        
        if not browser:
            logger.error("❌ Не удалось инициализировать браузер")
            return 1
            
        logger.info("🔄 Получение страницы браузера...")
        page = get_page(browser)
        if not page:
            logger.error("❌ Не удалось получить страницу браузера")
            close_browser(browser)
            return 1
            
        logger.info("✅ Браузер успешно инициализирован")
        random_delay(2, 4)  # Случайная задержка после инициализации браузера

        # Авторизация
        logger.info(f"🔑 Начало процесса авторизации для аккаунта {account_data['username']}...")
        auth = Auth(page, account_data)
        
        # Если в account_data есть account_id, добавляем его к объекту Auth
        if 'account_id' in account_data:
            auth.account_id = account_data['account_id']
            logger.info(f"🆔 Используем ID аккаунта: {account_data['account_id']}")
        
        logger.info("⏳ Выполнение входа в аккаунт...")
        if not auth.login_with_tfa():
            logger.error("❌ Ошибка авторизации! Не удалось войти в аккаунт.")
            logger.info("🔒 Закрытие браузера...")
            close_browser(browser)
            return
        
        logger.info("✅ Авторизация успешно выполнена!")
        random_delay(3, 5)  # Случайная задержка после успешной авторизации

        # Загрузка видео
        uploader = Upload(page)
        logger.info(f"📤 Начинаем процесс загрузки {len(video_paths)} видео...")
        
        prepared_videos = []
        
        # Подготавливаем все видео перед загрузкой
        logger.info("🔄 Подготовка видео для загрузки...")
        for video_path in video_paths:
            prepared_path = prepare_video_for_upload(video_path)
            if prepared_path:
                prepared_videos.append(prepared_path)
        
        if not prepared_videos:
            logger.error("❌ Не удалось подготовить ни одного видео для загрузки")
            logger.info("🔒 Закрытие браузера...")
            close_browser(browser)
            return
            
        logger.info(f"✅ Подготовлено {len(prepared_videos)} видео для загрузки")
        
        # Перемешиваем порядок видео для большей естественности (с вероятностью 30%)
        if random.random() > 0.7 and len(prepared_videos) > 1:
            logger.info("🔄 Перемешивание порядка загрузки видео для большей естественности...")
            random.shuffle(prepared_videos)
        
        for i, video_path in enumerate(prepared_videos):
            logger.info(f"🎬 Загрузка видео {i+1}/{len(prepared_videos)}: {video_path}")
            logger.info("⏳ Процесс загрузки может занять некоторое время...")
            
            # Добавляем случайную задержку для имитации человеческого поведения
            random_delay(3, 8)
            
            # Имитация просмотра ленты перед загрузкой (с вероятностью 40%)
            if random.random() > 0.6:
                browse_time = random.randint(15, 45)
                logger.info(f"🔍 Имитация просмотра ленты Instagram перед загрузкой видео ({browse_time} секунд)...")
                try:
                    # Прокрутка ленты
                    for _ in range(random.randint(3, 8)):
                        # Случайная прокрутка вниз
                        page.mouse.wheel(0, random.randint(300, 800))
                        random_delay(1, 3)
                        
                        # Случайные лайки (с вероятностью 20%)
                        if random.random() > 0.8:
                            logger.info("👍 Имитация лайка поста...")
                            # Ищем кнопки лайков (не реализовано полностью)
                            try:
                                like_button = page.locator("svg[aria-label='Like']").first
                                if like_button and like_button.is_visible():
                                    like_button.click()
                                    logger.info("❤️ Лайк поставлен")
                                    random_delay(1, 3)
                            except Exception as e:
                                logger.info(f"⚠️ Не удалось поставить лайк: {str(e)}")
                    
                    # Посещение случайного профиля (с вероятностью 30%)
                    if random.random() > 0.7:
                        logger.info("👤 Имитация посещения случайного профиля...")
                        try:
                            # Ищем имена пользователей в ленте (не реализовано полностью)
                            # Здесь должна быть логика для поиска и клика по имени пользователя
                            random_delay(3, 8)
                            page.goto("https://www.instagram.com/")
                            logger.info("🔙 Возврат на главную страницу")
                            random_delay(1, 3)
                        except Exception as e:
                            logger.info(f"⚠️ Не удалось посетить профиль: {str(e)}")
                except Exception as e:
                    logger.info(f"⚠️ Ошибка при имитации просмотра ленты: {str(e)}")
                    # Возвращаемся на главную страницу в случае ошибки
                    page.goto("https://www.instagram.com/")
                    random_delay(1, 3)
                
                logger.info("✅ Имитация просмотра ленты завершена")
            
            # Загрузка видео
            upload_success = uploader.upload_video(video_path)
            if upload_success:
                logger.info(f"✅ Видео {i+1}/{len(prepared_videos)} успешно загружено!")
            else:
                logger.error(f"❌ Ошибка при загрузке видео {i+1}/{len(prepared_videos)}")
            
            # Задержка между загрузками видео с вариативностью
            if i < len(prepared_videos) - 1:  # Если это не последнее видео
                # Более реалистичные задержки между загрузками
                if random.random() > 0.7:
                    # Длинная пауза (имитация перерыва)
                    delay = random.randint(60, 180)  # От 1 до 3 минут
                    logger.info(f"⏳ Длительная пауза между загрузками: {delay} секунд...")
                    time.sleep(delay)
                else:
                    # Обычная пауза
                    delay = random.randint(30, 60)  # От 30 секунд до 1 минуты
                    logger.info(f"⏳ Ожидание {delay} секунд перед загрузкой следующего видео...")
                    time.sleep(delay)

        logger.info("✅ Процесс загрузки видео завершен!")

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        logger.info("🔒 Закрытие браузера...")
        close_browser(browser)
        logger.info("👋 Работа бота завершена")

if __name__ == "__main__":
    main() 