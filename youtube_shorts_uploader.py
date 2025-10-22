
import asyncio
import json
import time
import random
from pathlib import Path
from playwright.async_api import async_playwright, expect
from typing import List, Dict, Tuple
import logging
import os

# Use centralized logging - all logs go to django.log
logger = logging.getLogger('scripts.youtube_shorts_uploader')

class YouTubeUploader:
    """Класс для автоматической загрузки YouTube Shorts через Playwright и Dolphin Anty"""

    def __init__(self, dolphin_api_url: str = "http://localhost:3001/v1.0"):
        self.dolphin_api_url = dolphin_api_url
        self.browser = None
        self.context = None
        self.page = None

        # XPath селекторы для надежного поиска элементов
        self.selectors = {
            # Вход в Google
            'email_input': [
                'input[type="email"]#identifierId',
                '//input[@type="email" and @id="identifierId"]',
                'input[name="identifier"]'
            ],
            'email_next': [
                '//div[@id="identifierNext"]//button',
                '#identifierNext button',
                'button[jsname="LgbsSe"]'
            ],
            'password_input': [
                'input[type="password"][name="Passwd"]',
                '//input[@type="password" and @name="Passwd"]',
                '#password input[type="password"]'
            ],
            'password_next': [
                '//div[@id="passwordNext"]//button',
                '#passwordNext button',
                'button[jsname="LgbsSe"]'
            ],

            # Верификация
            'verify_title': '//h1[contains(text(), "Verify that it")]',
            'try_another_way': '//button[contains(text(), "Try another way")]',
            'captcha_img': '#captchaimg',
            'captcha_input': 'input[name="ca"]',

            # YouTube Studio
            'create_channel': '//button[contains(text(), "Create channel")]',
            'channel_name_input': 'input[maxlength="50"][required]',
            'create_channel_btn': '//button[contains(text(), "Create")]',

            # Загрузка видео
            'file_input': 'input[type="file"][name="Filedata"]',
            'select_files_btn': '#select-files-button button',
            'title_input': 'div[contenteditable="true"][aria-label*="title"]',
            'description_input': 'div[contenteditable="true"][aria-label*="description"]',
            'shorts_checkbox': '//tp-yt-paper-checkbox[@id="shorts-checkbox"]',
            'next_button': '//button[contains(text(), "Next")]',
            'publish_button': [
                '//button[contains(text(), "Publish")]',
                '//button[contains(text(), "Upload")]',
                '//ytcp-button[@id="done-button"]'
            ],

            # Попапы и модальные окна
            'close_buttons': [
                '[aria-label="Close"]',
                '//button[contains(text(), "Skip")]',
                '//button[contains(text(), "Maybe later")]',
                '//button[contains(text(), "Not now")]',
                '//button[contains(text(), "Continue")]'
            ]
        }

    async def start_dolphin_profile(self, profile_id: str) -> dict:
        """Запуск профиля Dolphin Anty"""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.dolphin_api_url}/browser_profiles/{profile_id}/start") as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        raise Exception(f"Dolphin API error: {resp.status}")
        except Exception as e:
            logger.error(f"Ошибка запуска Dolphin профиля {profile_id}: {str(e)}")
            raise

    async def stop_dolphin_profile(self, profile_id: str):
        """Остановка профиля Dolphin Anty"""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(f"{self.dolphin_api_url}/browser_profiles/{profile_id}/stop") as resp:
                    return await resp.json()
        except Exception as e:
            logger.warning(f"Ошибка остановки Dolphin профиля {profile_id}: {str(e)}")

    async def init_browser(self, profile_id: str):
        """Инициализация браузера через Dolphin Anty"""
        try:
            profile_data = await self.start_dolphin_profile(profile_id)

            playwright = await async_playwright().start()

            # Подключение к CDP порту Dolphin
            cdp_port = profile_data.get('automation', {}).get('port', 9222)
            self.browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{cdp_port}")

            # Использование существующего контекста или создание нового
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
            else:
                self.context = await self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )

            self.page = await self.context.new_page()

            # Настройки для обхода детекции автоматизации
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });

                window.chrome = {
                    runtime: {},
                };
            """)

            logger.info(f"Браузер инициализирован для профиля {profile_id}")

        except Exception as e:
            logger.error(f"Ошибка инициализации браузера: {str(e)}")
            raise

    async def human_like_delay(self, min_ms: int = 1000, max_ms: int = 3000):
        """Человекоподобная задержка с рандомизацией"""
        delay = random.uniform(min_ms / 1000, max_ms / 1000)
        await asyncio.sleep(delay)

    async def find_element_by_selectors(self, selectors: List[str], timeout: int = 30000):
        """Поиск элемента по списку селекторов"""
        if isinstance(selectors, str):
            selectors = [selectors]

        for selector in selectors:
            try:
                element = self.page.locator(selector)
                await element.wait_for(state='visible', timeout=timeout)
                return element
            except:
                continue
        return None

    async def human_like_type(self, element_or_selector, text: str):
        """Человекоподобный ввод текста с рандомизацией"""
        try:
            if isinstance(element_or_selector, str):
                element = await self.find_element_by_selectors([element_or_selector])
                if not element:
                    raise Exception(f"Элемент не найден: {element_or_selector}")
            else:
                element = element_or_selector

            # Фокус на элемент
            await element.click()
            await self.human_like_delay(300, 800)

            # Очистка существующего текста
            await element.select_all()
            await element.press('Delete')
            await self.human_like_delay(200, 500)

            # Посимвольный ввод с случайными задержками
            for i, char in enumerate(text):
                await element.type(char, delay=random.randint(50, 200))

                # Случайные паузы в процессе набора
                if i % random.randint(5, 15) == 0 and i > 0:
                    await self.human_like_delay(200, 800)

        except Exception as e:
            logger.error(f"Ошибка ввода текста: {str(e)}")
            raise

    async def login_to_google(self, email: str, password: str) -> bool:
        """Надежный вход в Google аккаунт с обработкой различных сценариев"""
        try:
            logger.info(f"Начало входа в аккаунт {email}")

            # Переход на страницу входа
            await self.page.goto('https://studio.youtube.com/', wait_until='networkidle')
            await self.human_like_delay(2000, 4000)

            # Ввод email
            email_element = await self.find_element_by_selectors(self.selectors['email_input'])
            if not email_element:
                raise Exception("Поле email не найдено")

            await self.human_like_type(email_element, email)
            await self.human_like_delay(1000, 2000)

            # Клик Next после email
            next_button = await self.find_element_by_selectors(self.selectors['email_next'])
            if not next_button:
                raise Exception("Кнопка Next после email не найдена")

            await next_button.click()
            await self.human_like_delay(3000, 6000)

            # Ожидание загрузки страницы с паролем
            password_element = await self.find_element_by_selectors(self.selectors['password_input'], timeout=30000)
            if not password_element:
                raise Exception("Поле пароля не найдено")

            # Ввод пароля
            await self.human_like_type(password_element, password)
            await self.human_like_delay(1000, 2000)

            # Клик Next после пароля
            password_next = await self.find_element_by_selectors(self.selectors['password_next'])
            if not password_next:
                raise Exception("Кнопка Next после пароля не найдена")

            await password_next.click()
            await self.human_like_delay(5000, 8000)

            # Обработка дополнительных вызовов безопасности
            await self.handle_verification_challenges(password)

            # Проверка успешного входа
            try:
                await self.page.wait_for_url('**/myaccount.google.com/**', timeout=30000)
                logger.info(f"✅ Успешный вход для {email}")
                return True
            except:
                # Альтернативная проверка - переход на YouTube
                await self.page.goto('https://www.youtube.com', wait_until='networkidle')

                # Проверка на наличие аватара пользователя
                user_avatar = self.page.locator('button[aria-label*="Account menu"]')
                if await user_avatar.is_visible():
                    logger.info(f"✅ Успешный вход для {email} (проверка через YouTube)")
                    return True
                else:
                    raise Exception("Не удалось подтвердить вход")

        except Exception as e:
            logger.error(f"❌ Ошибка входа для {email}: {str(e)}")
            return False

    async def handle_verification_challenges(self, password: str):
        """Обработка дополнительных вызовов безопасности"""
        try:
            await self.human_like_delay(2000, 4000)

            # Проверка на страницу верификации
            verify_element = self.page.locator(self.selectors['verify_title'])
            if await verify_element.is_visible():
                logger.info("🔐 Обнаружена страница верификации")

                # Попытка выбрать альтернативный способ
                try_another = self.page.locator(self.selectors['try_another_way'])
                attempts = 0
                while await try_another.is_visible() and attempts < 3:
                    await try_another.click()
                    await self.human_like_delay(2000, 4000)
                    attempts += 1

            # Обработка CAPTCHA
            captcha_img = self.page.locator(self.selectors['captcha_img'])
            if await captcha_img.is_visible():
                logger.warning("🤖 Обнаружена CAPTCHA - требуется решение")
                # Здесь можно интегрировать автоматическое решение CAPTCHA
                await self.human_like_delay(5000, 10000)

            # Обработка восстановления аккаунта
            recovery_input = self.page.locator('input[type="password"]')
            if await recovery_input.is_visible():
                logger.info("🔑 Запрос пароля для восстановления")
                await self.human_like_type(recovery_input, password)

                next_btn = self.page.locator('//button[contains(text(), "Next")]')
                if await next_btn.is_visible():
                    await next_btn.click()
                    await self.human_like_delay(3000, 6000)

            # Проверка на ошибку входа
            error_message = self.page.locator('//span[contains(text(), "Couldn\'t sign you in")]')
            if await error_message.is_visible():
                logger.error("❌ Google сообщил о невозможности входа")
                raise Exception("Не удалось войти - аккаунт заблокирован или неверные данные")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка при обработке верификации: {str(e)}")

    async def navigate_to_youtube_studio(self):
        """Переход в YouTube Studio и создание канала при необходимости"""
        try:
            logger.info("📺 Переход в YouTube Studio")

            await self.page.goto('https://studio.youtube.com', wait_until='networkidle')
            await self.human_like_delay(3000, 6000)

            # Проверка на необходимость создания канала
            create_channel = self.page.locator(self.selectors['create_channel'])
            if await create_channel.is_visible():
                logger.info("🆕 Создание YouTube канала")

                await create_channel.click()
                await self.human_like_delay(2000, 4000)

                # Заполнение имени канала
                name_input = self.page.locator(self.selectors['channel_name_input'])
                if await name_input.is_visible():
                    channel_name = f"Channel_{random.randint(10000, 99999)}"
                    await self.human_like_type(name_input, channel_name)
                    await self.human_like_delay(1000, 2000)

                # Создание канала
                create_btn = self.page.locator(self.selectors['create_channel_btn'])
                if await create_btn.is_visible():
                    await create_btn.click()
                    await self.human_like_delay(5000, 10000)

                # Закрытие всплывающих окон
                await self.close_popups()

            logger.info("✅ Переход в YouTube Studio завершен")

        except Exception as e:
            logger.error(f"❌ Ошибка перехода в YouTube Studio: {str(e)}")
            raise

    async def close_popups(self):
        """Закрытие всплывающих окон и модальных диалогов"""
        try:
            await self.human_like_delay(1000, 2000)

            # Клик мимо модального окна
            try:
                await self.page.click('body', position={"x": 100, "y": 100}, timeout=2000)
                await self.human_like_delay(1000, 2000)
            except:
                pass

            # Поиск и закрытие кнопок
            for selector in self.selectors['close_buttons']:
                try:
                    close_btn = self.page.locator(selector)
                    if await close_btn.is_visible():
                        await close_btn.click()
                        await self.human_like_delay(1000, 2000)
                        logger.info(f"Закрыт попап: {selector}")
                except:
                    continue

        except Exception as e:
            logger.warning(f"⚠️ Ошибка закрытия попапов: {str(e)}")

    async def upload_video(self, video_path: str, title: str = None, description: str = None) -> bool:
        """Загрузка видео на YouTube с полной обработкой процесса"""
        try:
            logger.info(f"📤 Начало загрузки видео: {video_path}")

            # Переход к странице загрузки
            await self.page.goto('https://studio.youtube.com/channel/UC/videos/upload', wait_until='networkidle')
            await self.human_like_delay(3000, 6000)

            # Поиск и использование input file
            file_input = self.page.locator(self.selectors['file_input'])

            # Если input скрыт, нажимаем на кнопку выбора файлов
            if not await file_input.is_visible():
                select_btn = self.page.locator(self.selectors['select_files_btn'])
                if await select_btn.is_visible():
                    # Устанавливаем файл перед кликом
                    await file_input.set_input_files(video_path)
                    await select_btn.click()
                else:
                    # Прямое использование скрытого input
                    await file_input.set_input_files(video_path)
            else:
                await file_input.set_input_files(video_path)

            logger.info("📁 Файл выбран, ожидание загрузки...")
            await self.human_like_delay(5000, 10000)

            # Ожидание появления полей метаданных
            await self.page.wait_for_selector('div[contenteditable="true"]', timeout=60000)

            # Заполнение заголовка
            if title:
                title_input = self.page.locator(self.selectors['title_input']).first
                if await title_input.is_visible():
                    await self.human_like_type(title_input, title)
                    logger.info(f"✏️ Заголовок установлен: {title}")

            # Заполнение описания
            if description:
                desc_input = self.page.locator(self.selectors['description_input']).first
                if await desc_input.is_visible():
                    await self.human_like_type(desc_input, description)
                    logger.info("✏️ Описание добавлено")

            # Настройка как Shorts (если применимо)
            shorts_checkbox = self.page.locator(self.selectors['shorts_checkbox'])
            if await shorts_checkbox.is_visible():
                await shorts_checkbox.check()
                logger.info("📱 Отмечено как Shorts")
                await self.human_like_delay(1000, 2000)

            # Процесс публикации
            await self.publish_video()

            logger.info(f"✅ Видео успешно загружено: {video_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки видео {video_path}: {str(e)}")
            return False

    async def publish_video(self):
        """Прохождение через процесс публикации видео"""
        try:
            logger.info("🚀 Начало публикации видео")

            # Переход через этапы публикации (до 4 шагов)
            for step in range(4):
                await self.human_like_delay(2000, 4000)

                next_btn = self.page.locator(self.selectors['next_button'])
                if await next_btn.is_visible():
                    await next_btn.click()
                    logger.info(f"➡️ Переход к шагу {step + 2}")
                    await self.human_like_delay(3000, 5000)
                else:
                    break

            # Финальная публикация
            await self.human_like_delay(2000, 4000)

            published = False
            for selector in self.selectors['publish_button']:
                publish_btn = self.page.locator(selector)
                if await publish_btn.is_visible():
                    await publish_btn.click()
                    logger.info("📢 Видео опубликовано!")
                    published = True
                    await self.human_like_delay(3000, 6000)
                    break

            if not published:
                logger.warning("⚠️ Кнопка публикации не найдена")

        except Exception as e:
            logger.error(f"❌ Ошибка публикации: {str(e)}")
            raise

    async def close_browser(self, profile_id: str):
        """Корректное закрытие браузера и профиля Dolphin"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()

            await self.stop_dolphin_profile(profile_id)
            logger.info(f"🔚 Браузер закрыт для профиля {profile_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка закрытия браузера: {str(e)}")


class AccountManager:
    """Управление аккаунтами из файла"""

    def __init__(self, accounts_file: str):
        self.accounts_file = accounts_file
        self.accounts = []

    def load_accounts(self):
        """Загрузка аккаунтов из файла в формате email:password:submail"""
        try:
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            for line_num, line in enumerate(content.split('\n'), 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split(':')
                if len(parts) >= 2:
                    account = {
                        'email': parts[0].strip(),
                        'password': parts[1].strip(),
                        'submail': parts[2].strip() if len(parts) > 2 else None,
                        'profile_id': f"profile_{len(self.accounts) + 1:04d}",
                        'line_number': line_num
                    }
                    self.accounts.append(account)
                else:
                    logger.warning(f"⚠️ Неверный формат строки {line_num}: {line}")

            logger.info(f"📋 Загружено {len(self.accounts)} аккаунтов")
            return True

        except FileNotFoundError:
            logger.error(f"❌ Файл аккаунтов не найден: {self.accounts_file}")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки аккаунтов: {str(e)}")
            return False

    def get_accounts(self) -> List[Dict]:
        """Получение списка всех аккаунтов"""
        return self.accounts

    def get_account_batch(self, batch_size: int, start_index: int = 0) -> List[Dict]:
        """Получение батча аккаунтов"""
        end_index = start_index + batch_size
        return self.accounts[start_index:end_index]


class VideoManager:
    """Управление видео файлами"""

    def __init__(self, videos_folder: str):
        self.videos_folder = Path(videos_folder)
        self.videos = []

    def load_videos(self):
        """Загрузка списка видео из папки"""
        try:
            if not self.videos_folder.exists():
                logger.error(f"❌ Папка с видео не найдена: {self.videos_folder}")
                return False

            # Поддерживаемые форматы
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']

            for ext in video_extensions:
                pattern = f'*{ext}'
                found_videos = list(self.videos_folder.glob(pattern))
                self.videos.extend(found_videos)

                # Проверяем также в подпапках
                found_in_subdirs = list(self.videos_folder.rglob(pattern))
                self.videos.extend([v for v in found_in_subdirs if v not in found_videos])

            # Удаляем дубликаты
            self.videos = list(set(self.videos))

            logger.info(f"🎬 Найдено {len(self.videos)} видео файлов")

            if not self.videos:
                logger.error("❌ Видео файлы не найдены")
                return False

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки видео: {str(e)}")
            return False

    def get_random_video(self) -> Path:
        """Получение случайного видео файла"""
        if self.videos:
            return random.choice(self.videos)
        return None

    def get_video_by_index(self, index: int) -> Path:
        """Получение видео по индексу"""
        if 0 <= index < len(self.videos):
            return self.videos[index]
        return None


class UploadPipeline:
    """Основной пайплайн для массовой загрузки YouTube Shorts"""

    def __init__(self, accounts_file: str, videos_folder: str, max_concurrent: int = 3):
        self.account_manager = AccountManager(accounts_file)
        self.video_manager = VideoManager(videos_folder)
        self.max_concurrent = max_concurrent
        self.upload_semaphore = asyncio.Semaphore(max_concurrent)
        self.results = {
            'successful': 0,
            'failed': 0,
            'total': 0,
            'errors': []
        }

    def setup(self) -> bool:
        """Инициализация пайплайна"""
        logger.info("🚀 Инициализация пайплайна загрузки")

        accounts_loaded = self.account_manager.load_accounts()
        videos_loaded = self.video_manager.load_videos()

        if not accounts_loaded or not videos_loaded:
            return False

        logger.info("✅ Пайплайн готов к запуску")
        return True

    async def process_account(self, account: Dict, video_index: int = None) -> Dict:
        """Обработка одного аккаунта"""
        async with self.upload_semaphore:
            uploader = YouTubeUploader()
            result = {
                'account': account['email'],
                'success': False,
                'error': None,
                'video_path': None,
                'upload_time': None
            }

            start_time = time.time()

            try:
                logger.info(f"🔄 Обработка аккаунта: {account['email']}")

                # Инициализация браузера
                await uploader.init_browser(account['profile_id'])
                await uploader.human_like_delay(2000, 4000)

                # Вход в аккаунт
                login_success = await uploader.login_to_google(
                    account['email'], 
                    account['password']
                )

                if not login_success:
                    result['error'] = "Не удалось войти в аккаунт"
                    return result

                # Переход в YouTube Studio
                await uploader.navigate_to_youtube_studio()

                # Выбор видео
                if video_index is not None:
                    video_path = self.video_manager.get_video_by_index(video_index)
                else:
                    video_path = self.video_manager.get_random_video()

                if not video_path:
                    result['error'] = "Нет доступных видео"
                    return result

                result['video_path'] = str(video_path)

                # Создание метаданных
                timestamp = time.strftime('%Y%m%d_%H%M%S')
                title = f"Short Video {timestamp}"
                description = f"Uploaded automatically on {time.strftime('%Y-%m-%d %H:%M:%S')}"

                # Загрузка видео
                upload_success = await uploader.upload_video(
                    str(video_path), 
                    title, 
                    description
                )

                result['success'] = upload_success
                result['upload_time'] = time.time() - start_time

                if upload_success:
                    logger.info(f"✅ Аккаунт {account['email']} - успешно загружено")
                    self.results['successful'] += 1
                else:
                    logger.error(f"❌ Аккаунт {account['email']} - загрузка не удалась")
                    result['error'] = "Ошибка во время загрузки"
                    self.results['failed'] += 1

                return result

            except Exception as e:
                error_msg = str(e)
                result['error'] = error_msg
                logger.error(f"❌ Критическая ошибка для {account['email']}: {error_msg}")
                self.results['failed'] += 1
                self.results['errors'].append({
                    'account': account['email'],
                    'error': error_msg,
                    'time': time.strftime('%Y-%m-%d %H:%M:%S')
                })
                return result

            finally:
                self.results['total'] += 1
                await uploader.close_browser(account['profile_id'])

                # Человекоподобная пауза между аккаунтами
                pause_time = random.randint(60, 180)  # 1-3 минуты
                logger.info(f"⏸️ Пауза {pause_time}с перед следующим аккаунтом")
                await asyncio.sleep(pause_time)

    async def run_batch(self, batch_size: int = 10, start_index: int = 0):
        """Запуск обработки батча аккаунтов"""
        accounts = self.account_manager.get_accounts()

        if not accounts:
            logger.error("❌ Нет доступных аккаунтов")
            return

        total_accounts = len(accounts)
        end_index = min(start_index + batch_size, total_accounts)
        batch = accounts[start_index:end_index]

        logger.info(f"🎯 Обработка батча: аккаунты {start_index + 1}-{end_index} из {total_accounts}")

        # Создание задач для батча
        tasks = []
        for i, account in enumerate(batch):
            video_index = (start_index + i) % len(self.video_manager.videos)
            task = self.process_account(account, video_index)
            tasks.append(task)

        # Выполнение с ограничением concurrency
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Анализ результатов батча
        batch_successful = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
        batch_failed = len(results) - batch_successful

        logger.info(f"📊 Батч завершен: {batch_successful} успешных, {batch_failed} неудачных")

        return results

    async def run_full_pipeline(self, batch_size: int = 10):
        """Запуск полного пайплайна для всех аккаунтов"""
        accounts = self.account_manager.get_accounts()
        total_accounts = len(accounts)

        logger.info(f"🎬 Запуск полного пайплайна для {total_accounts} аккаунтов")

        for start_idx in range(0, total_accounts, batch_size):
            batch_num = (start_idx // batch_size) + 1
            total_batches = (total_accounts + batch_size - 1) // batch_size

            logger.info(f"📦 Батч {batch_num}/{total_batches}")

            await self.run_batch(batch_size, start_idx)

            # Пауза между батчами
            if start_idx + batch_size < total_accounts:
                pause_time = random.randint(600, 1800)  # 10-30 минут
                logger.info(f"⏳ Большая пауза между батчами: {pause_time//60} минут")
                await asyncio.sleep(pause_time)

        # Финальный отчет
        self.print_final_report()

    def print_final_report(self):
        """Печать финального отчета"""
        logger.info("=" * 50)
        logger.info("📋 ФИНАЛЬНЫЙ ОТЧЕТ")
        logger.info("=" * 50)
        logger.info(f"Всего аккаунтов обработано: {self.results['total']}")
        logger.info(f"Успешных загрузок: {self.results['successful']}")
        logger.info(f"Неудачных загрузок: {self.results['failed']}")

        if self.results['total'] > 0:
            success_rate = (self.results['successful'] / self.results['total']) * 100
            logger.info(f"Процент успеха: {success_rate:.1f}%")

        if self.results['errors']:
            logger.info("\n❌ Ошибки:")
            for error in self.results['errors'][-10:]:  # Показываем последние 10 ошибок
                logger.info(f"  {error['account']}: {error['error']}")

        logger.info("=" * 50)


async def main():
    """Главная функция запуска пайплайна"""

    # Конфигурация
    CONFIG = {
        'ACCOUNTS_FILE': 'accounts.txt',    # email:password:submail
        'VIDEOS_FOLDER': 'videos',          # Папка с видео файлами
        'BATCH_SIZE': 5,                    # Размер батча
        'MAX_CONCURRENT': 2,                # Максимум одновременных загрузок
        'START_INDEX': 0                    # С какого аккаунта начать
    }

    logger.info("🚀 ЗАПУСК ПАЙПЛАЙНА YOUTUBE SHORTS UPLOADER")
    logger.info("=" * 60)

    try:
        # Создание и настройка пайплайна
        pipeline = UploadPipeline(
            accounts_file=CONFIG['ACCOUNTS_FILE'],
            videos_folder=CONFIG['VIDEOS_FOLDER'],
            max_concurrent=CONFIG['MAX_CONCURRENT']
        )

        # Инициализация
        if not pipeline.setup():
            logger.error("❌ Ошибка инициализации пайплайна")
            return

        # Запуск
        await pipeline.run_full_pipeline(
            batch_size=CONFIG['BATCH_SIZE']
        )

        logger.info("🏁 Пайплайн завершен успешно")

    except KeyboardInterrupt:
        logger.info("⚠️ Пайплайн прерван пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка пайплайна: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Запуск асинхронного пайплайна
    asyncio.run(main())
