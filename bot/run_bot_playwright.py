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
from bot.src.videos import get_videos_list, get_videos_by_folders
from bot.src.instagram_uploader.util import random_delay, realistic_type, human_action

# Use centralized Django logging
logger = logging.getLogger('bot.run_bot_playwright')

def check_proxy_config(proxy_data):
    """
    Проверяет конфигурацию прокси и возвращает информацию о текущем IP
    """
    if not proxy_data:
        logger.error("[FAIL] Прокси не указан, но он обязателен для работы бота")
        return None
        
    logger.info("[RETRY] Инициализация временного браузера для проверки прокси...")
    # Создаем временный профиль Dolphin для проверки прокси
    api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
    if not api_key:
        logger.error("[FAIL] Dolphin API token not found in environment variables")
        return None
    
    dolphin = DolphinAnty(api_key=api_key)
    
    try:
        # Создаем временный профиль с прокси
        temp_profile_name = f"Temp Profile - {uuid.uuid4().hex[:8]}"
        proxy_payload = {
            'type': proxy_data.get('type', 'http'),
            'host': proxy_data.get('host'),
            'port': proxy_data.get('port'),
            'user': proxy_data.get('username', ''),
            'pass': proxy_data.get('password', '')
        }
        
        profile_response = dolphin.create_profile(
            name=temp_profile_name,
            proxy=proxy_payload,
            tags=["temp"],
            locale='ru_RU'
        )
        if not profile_response or not profile_response.get("success"):
            logger.error("[FAIL] Не удалось создать временный профиль для проверки прокси")
            return None
            
        profile_id = profile_response.get("browserProfileId")
        
        # Запускаем профиль
        logger.info("[RETRY] Запуск временного профиля для проверки прокси...")
        success, automation_data = dolphin.start_profile(profile_id, headless=True)
        
        if not success:
            logger.error("[FAIL] Не удалось запустить временный профиль")
            dolphin.delete_profile(profile_id)
            return None
            
        # Создаем браузер
        browser = get_browser(headless=True, profile_id=profile_id)
        page = get_page(browser)
        
        if not page:
            logger.error("[FAIL] Не удалось создать страницу браузера")
            close_browser(browser)
            dolphin.delete_profile(profile_id)
            return None
        
        logger.info("🌐 Проверка работы прокси...")
        ip = verify_ip_address(page)
        if ip:
            logger.info(f"[OK] Прокси работает! Используемый IP-адрес: {ip}")
            result = ip
        else:
            logger.error("[FAIL] Не удалось проверить IP-адрес или прокси не работает")
            result = None
    finally:
        # Закрываем браузер
        if 'browser' in locals():
            logger.info("🔒 Закрытие временного браузера...")
            close_browser(browser)
        
        # Удаляем временный профиль
        if 'profile_id' in locals():
            logger.info("[DELETE] Удаление временного профиля...")
            dolphin.delete_profile(profile_id)
        
    return result

def prepare_video_for_upload(video_path):
    """
    Подготавливает видео для загрузки:
    - Копирует из временной директории в постоянную с человекоподобным именем
    - Возвращает путь к подготовленному файлу
    """
    try:
        logger.info(f"[RETRY] Подготовка видео для загрузки: {video_path}")
        
        # Проверяем, существует ли файл
        if not os.path.exists(video_path):
            logger.error(f"[FAIL] Видео не найдено: {video_path}")
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
        
        logger.info(f"[RETRY] Копирование видео из {video_path} в {new_path}")
        
        # Копируем файл
        shutil.copy2(video_path, new_path)
        logger.info(f"[OK] Видео успешно скопировано с новым именем: {new_filename}")
        
        # Добавляем случайную задержку для имитации человеческого поведения
        random_delay(1, 3)
        
        # Проверяем, нужно ли изменить метаданные видео
        if random.random() > 0.5:
            logger.info(f"[RETRY] Изменение метаданных видео для большей естественности...")
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
                    logger.info(f"[OK] Метаданные видео успешно изменены")
                else:
                    logger.info(f"ℹ️ exiftool не установлен, пропуск изменения метаданных")
            except Exception as e:
                logger.info(f"[WARN] Не удалось изменить метаданные: {str(e)}")
        
        return new_path
    except Exception as e:
        logger.error(f"[FAIL] Ошибка при копировании файла: {str(e)}")
        return None

def main():
    logger.info("[START] Запуск Instagram Uploader Bot (Playwright + Dolphin Anty)")
    
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
        logger.warning("[WARN] API токен Dolphin Anty не указан! Используйте --dolphin-token или переменную окружения DOLPHIN_API_TOKEN")
    
    logger.info(f"[CLIPBOARD] Параметры запуска: account={args.account}, videos={args.videos}, proxy={args.proxy if args.proxy else 'не используется'}, non-interactive={args.non_interactive}, visible={not headless_mode}")

    # Инициализируем browser как None перед try-блоком
    browser = None

    try:
        # Загружаем данные аккаунта
        logger.info(f"📂 Загрузка данных аккаунта из файла: {args.account}")
        try:
            with open(args.account, 'r') as f:
                account_data = json.load(f)
            logger.info(f"[OK] Данные аккаунта успешно загружены: {account_data.get('username')}")
        except Exception as e:
            logger.error(f"[FAIL] Ошибка загрузки данных аккаунта: {str(e)}")
            return 1
        
        # Загружаем данные прокси (если указаны)
        proxy_data = None
        if args.proxy:
            logger.info(f"[RETRY] Загрузка данных прокси из файла: {args.proxy}")
            try:
                with open(args.proxy, 'r') as f:
                    proxy_data = json.load(f)
                logger.info(f"[OK] Данные прокси успешно загружены: {proxy_data.get('host')}:{proxy_data.get('port')}")
            except Exception as e:
                logger.error(f"[FAIL] Ошибка загрузки данных прокси: {str(e)}")
                return 1
        
        # Проверяем конфигурацию прокси (если он указан)
        if proxy_data:
            ip_info = check_proxy_config(proxy_data)
            if not ip_info and not args.non_interactive:
                user_answer = input("Прокси не работает. Продолжить без прокси? (y/n): ")
                if user_answer.lower() != 'y':
                    logger.error("[FAIL] Выход по запросу пользователя")
                    return 1
                proxy_data = None  # Отключаем прокси
        
        # Загружаем список видео
        logger.info(f"[RETRY] Загрузка списка видео из файла: {args.videos}")
        try:
            with open(args.videos, 'r') as f:
                video_paths = json.load(f)
            logger.info(f"[OK] Список видео успешно загружен, найдено {len(video_paths)} видео")
        except Exception as e:
            logger.error(f"[FAIL] Ошибка загрузки списка видео: {str(e)}")
            return 1

        # Проверяем, есть ли у аккаунта уже созданный профиль Dolphin
        dolphin_profile_id = account_data.get('dolphin_profile_id')
        
        # Инициализируем браузер
        logger.info("[RETRY] Инициализация браузера с Dolphin Anty...")
        
        if dolphin_profile_id:
            # Используем существующий профиль
            logger.info(f"[SEARCH] Используем существующий профиль Dolphin: {dolphin_profile_id}")
            browser = get_browser(
                headless=headless_mode, 
                api_token=dolphin_token, 
                profile_id=dolphin_profile_id
            )
        else:
            # Создаем новый профиль для аккаунта
            logger.info(f"[TOOL] Создаем новый профиль Dolphin для аккаунта {account_data.get('username')}")
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
                logger.info(f"[OK] Профиль Dolphin {dolphin_profile_id} сохранен для аккаунта")
                
                # Сохраняем обновленные данные аккаунта обратно в файл
                try:
                    with open(args.account, 'w') as f:
                        json.dump(account_data, f, indent=2)
                    logger.info("[OK] Данные аккаунта обновлены с ID профиля Dolphin")
                except Exception as e:
                    logger.error(f"[FAIL] Не удалось сохранить обновленные данные аккаунта: {str(e)}")
                
                # Сохраняем snapshot профиля в БД если есть account_id и response
                if account_data.get('account_id') and hasattr(browser, 'dolphin_profile_response'):
                    try:
                        # Import Django settings
                        import django
                        import sys
                        import os
                        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
                        django.setup()
                        
                        from uploader.models import InstagramAccount
                        from uploader.services.dolphin_snapshot import save_dolphin_snapshot
                        
                        account = InstagramAccount.objects.filter(id=account_data['account_id']).first()
                        if account:
                            save_dolphin_snapshot(account, dolphin_profile_id, browser.dolphin_profile_response)
                            logger.info(f"[OK] Dolphin profile snapshot saved to database for account {account.username}")
                    except Exception as snap_err:
                        logger.warning(f"[WARN] Could not save Dolphin snapshot to database: {str(snap_err)}")
        
        if not browser:
            logger.error("[FAIL] Не удалось инициализировать браузер")
            return 1
            
        logger.info("[RETRY] Получение страницы браузера...")
        page = get_page(browser)
        if not page:
            logger.error("[FAIL] Не удалось получить страницу браузера")
            close_browser(browser)
            return 1
            
        logger.info("[OK] Браузер успешно инициализирован")
        random_delay(2, 4)  # Случайная задержка после инициализации браузера

        # Авторизация
        logger.info(f"🔑 Начало процесса авторизации для аккаунта {account_data['username']}...")
        auth = Auth(page, account_data)
        
        # Если в account_data есть account_id, добавляем его к объекту Auth
        if 'account_id' in account_data:
            auth.account_id = account_data['account_id']
            logger.info(f"🆔 Используем ID аккаунта: {account_data['account_id']}")
        
        logger.info("[WAIT] Выполнение входа в аккаунт...")
        if not auth.login_with_tfa():
            logger.error("[FAIL] Ошибка авторизации! Не удалось войти в аккаунт.")
            logger.info("🔒 Закрытие браузера...")
            close_browser(browser)
            return
        
        logger.info("[OK] Авторизация успешно выполнена!")
        random_delay(3, 5)  # Случайная задержка после успешной авторизации

        # Загрузка видео
        uploader = Upload(page)
        logger.info(f"📤 Начинаем процесс загрузки {len(video_paths)} видео...")
        
        prepared_videos = []
        
        # Подготавливаем все видео перед загрузкой
        logger.info("[RETRY] Подготовка видео для загрузки...")
        for video_path in video_paths:
            prepared_path = prepare_video_for_upload(video_path)
            if prepared_path:
                prepared_videos.append(prepared_path)
        
        if not prepared_videos:
            logger.error("[FAIL] Не удалось подготовить ни одного видео для загрузки")
            logger.info("🔒 Закрытие браузера...")
            close_browser(browser)
            return
            
        logger.info(f"[OK] Подготовлено {len(prepared_videos)} видео для загрузки")
        
        # Перемешиваем порядок видео для большей естественности (с вероятностью 30%)
        if random.random() > 0.7 and len(prepared_videos) > 1:
            logger.info("[RETRY] Перемешивание порядка загрузки видео для большей естественности...")
            random.shuffle(prepared_videos)
        
        for i, video_path in enumerate(prepared_videos):
            logger.info(f"[VIDEO] Загрузка видео {i+1}/{len(prepared_videos)}: {video_path}")
            logger.info("[WAIT] Процесс загрузки может занять некоторое время...")
            
            # Добавляем случайную задержку для имитации человеческого поведения
            random_delay(3, 8)
            
            # Имитация просмотра ленты перед загрузкой (с вероятностью 40%)
            if random.random() > 0.6:
                browse_time = random.randint(15, 45)
                logger.info(f"[SEARCH] Имитация просмотра ленты Instagram перед загрузкой видео ({browse_time} секунд)...")
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
                                logger.info(f"[WARN] Не удалось поставить лайк: {str(e)}")
                    
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
                            logger.info(f"[WARN] Не удалось посетить профиль: {str(e)}")
                except Exception as e:
                    logger.info(f"[WARN] Ошибка при имитации просмотра ленты: {str(e)}")
                    # Возвращаемся на главную страницу в случае ошибки
                    page.goto("https://www.instagram.com/")
                    random_delay(1, 3)
                
                logger.info("[OK] Имитация просмотра ленты завершена")
            
            # Загрузка видео
            upload_success = uploader.upload_video(video_path)
            if upload_success:
                logger.info(f"[OK] Видео {i+1}/{len(prepared_videos)} успешно загружено!")
            else:
                logger.error(f"[FAIL] Ошибка при загрузке видео {i+1}/{len(prepared_videos)}")
            
            # Задержка между загрузками видео с вариативностью
            if i < len(prepared_videos) - 1:  # Если это не последнее видео
                # Более реалистичные задержки между загрузками
                if random.random() > 0.7:
                    # Длинная пауза (имитация перерыва)
                    delay = random.randint(60, 180)  # От 1 до 3 минут
                    logger.info(f"[WAIT] Длительная пауза между загрузками: {delay} секунд...")
                    time.sleep(delay)
                else:
                    # Обычная пауза
                    delay = random.randint(30, 60)  # От 30 секунд до 1 минуты
                    logger.info(f"[WAIT] Ожидание {delay} секунд перед загрузкой следующего видео...")
                    time.sleep(delay)

        logger.info("[OK] Процесс загрузки видео завершен!")

    except Exception as e:
        logger.error(f"[FAIL] Критическая ошибка: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        logger.info("🔒 Закрытие браузера...")
        close_browser(browser)
        logger.info("👋 Работа бота завершена")

if __name__ == "__main__":
    main() 