import time
import random
import os
from playwright.sync_api import Page, expect

from bot.src import logger
from bot.src.instagram_uploader import config
from bot.src.instagram_uploader.browser_dolphin import close_browser
from bot.src.instagram_uploader.util import random_delay, realistic_type, human_action


class Upload:
    """
    Класс для загрузки видео в Instagram с помощью Playwright
    """
    def __init__(self, page: Page):
        self.page = page
    
    def upload_video(self, video: str, title=None, location=None, mentions=None):
        """
        Upload a video to Instagram using Playwright
        """
        page = self.page
        logger.info(f'[VIDEO] Начинаем загрузку видео: {video}')
        
        if title:
            logger.info(f'[TEXT] Заголовок: {title}')
            title = title.encode('utf-8', 'ignore').decode('utf-8')
        else:
            title = "Instagram Video"
            logger.info(f'[TEXT] Используем стандартный заголовок: {title}')
            
        if location:
            location = location.encode('utf-8', 'ignore').decode('utf-8')
            logger.info(f'[LOCATION] Локация: {location}')
        else:
            logger.info('[LOCATION] Локация не указана')
        
        if mentions:
            logger.info(f'[USERS] Упоминания: {", ".join(mentions)}')
        else:
            logger.info('[USERS] Упоминания не указаны')

        logger.info('[WAIT] Начальная задержка перед загрузкой...')
        random_delay("major")
        
        try:
            # Find and click the new post button - используем несколько методов поиска
            logger.info('[SEARCH] Поиск кнопки нового поста...')
            
            # Метод 1: Стандартный XPath из конфига
            try:
                logger.info('[SEARCH] Поиск кнопки нового поста по стандартному XPath...')
                new_post_button = page.locator("xpath=" + config['selectors']['upload']['new_post_button'])
                if new_post_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                    logger.info('👆 Нажатие кнопки нового поста (стандартный XPath)')
                    new_post_button.click()
                    logger.info('[WAIT] Ожидание после нажатия кнопки нового поста...')
                    time.sleep(3)
                else:
                    raise Exception("Кнопка не найдена по стандартному XPath")
            except Exception as e:
                logger.info(f'[WARN] Стандартная кнопка не найдена, пробуем альтернативные методы: {str(e)}')
                
                # Метод 2: Поиск по роли и имени кнопки
                try:
                    logger.info('[SEARCH] Поиск кнопки нового поста по роли...')
                    create_button = page.get_by_role("button", name="Create")
                    if create_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                        logger.info('👆 Нажатие кнопки Create (по роли)')
                        create_button.click()
                        logger.info('[WAIT] Ожидание после нажатия кнопки Create...')
                        time.sleep(3)
                    else:
                        raise Exception("Кнопка не найдена по роли")
                except Exception as e:
                    logger.info(f'[WARN] Кнопка Create не найдена по роли, пробуем дальше: {str(e)}')
                    
                    # Метод 3: Поиск по aria-label
                    try:
                        logger.info('[SEARCH] Поиск кнопки нового поста по aria-label...')
                        create_aria_button = page.locator('[aria-label="New post"]')
                        if create_aria_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                            logger.info('👆 Нажатие кнопки с aria-label="New post"')
                            create_aria_button.click()
                            logger.info('[WAIT] Ожидание после нажатия кнопки New post...')
                            time.sleep(3)
                        else:
                            raise Exception("Кнопка не найдена по aria-label")
                    except Exception as e:
                        logger.info(f'[WARN] Кнопка не найдена по aria-label, пробуем дальше: {str(e)}')
                        
                        # Метод 4: Поиск по SVG иконке
                        try:
                            logger.info('[SEARCH] Поиск кнопки нового поста по SVG иконке...')
                            create_svg = page.locator('svg[aria-label="New post"]')
                            if create_svg.is_visible(timeout=config['implicitly_wait'] * 1000):
                                logger.info('👆 Нажатие на SVG иконку New post')
                                # Кликаем по родительскому элементу, так как сам SVG может быть не кликабельным
                                create_svg.locator('xpath=..').click()
                                logger.info('[WAIT] Ожидание после нажатия на SVG иконку...')
                                time.sleep(3)
                            else:
                                raise Exception("SVG иконка не найдена")
                        except Exception as e:
                            logger.info(f'[WARN] SVG иконка не найдена, пробуем еще варианты: {str(e)}')
                            
                            # Метод 5: Поиск по тексту "Create" на странице
                            try:
                                logger.info('[SEARCH] Поиск текста "Create" на странице...')
                                create_text = page.get_by_text("Create", exact=True)
                                if create_text.is_visible(timeout=config['implicitly_wait'] * 1000):
                                    logger.info('👆 Нажатие на текст "Create"')
                                    create_text.click()
                                    logger.info('[WAIT] Ожидание после нажатия на текст "Create"...')
                                    time.sleep(3)
                                else:
                                    raise Exception('Текст "Create" не найден')
                            except Exception as e:
                                logger.info(f'[WARN] Текст "Create" не найден: {str(e)}')
                                
                                # Метод 6: Прямой переход на URL создания поста
                                try:
                                    logger.info('[SEARCH] Пробуем прямой переход на URL создания поста...')
                                    page.goto("https://www.instagram.com/create/select/")
                                    logger.info('[WAIT] Ожидание после перехода на URL создания поста...')
                                    time.sleep(5)
                                except Exception as e:
                                    logger.error(f'[FAIL] Не удалось перейти на URL создания поста: {str(e)}')
                                    raise Exception("Не удалось найти кнопку создания нового поста")
            
            # Check for alternate post button
            try:
                logger.info('[SEARCH] Проверка наличия альтернативной кнопки поста...')
                alternate_post_button = page.locator("xpath=" + config['selectors']['upload']['alternate_post_button'])
                if alternate_post_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                    logger.info('👆 Нажатие альтернативной кнопки поста')
                    alternate_post_button.click()
                    logger.info('[WAIT] Ожидание после нажатия альтернативной кнопки поста...')
                    time.sleep(3)
            except Exception as e:
                logger.info(f'[WARN] Альтернативная кнопка не найдена, продолжаем: {str(e)}')
                pass
            
            logger.info('[WAIT] Ожидание загрузки интерфейса...')
            time.sleep(5)
            
            # Try to find and click "Select from device" button if it appears
            try:
                logger.info('[SEARCH] Поиск кнопки "Select from device"...')
                select_from_device = page.get_by_role("button", name="Select from device")
                
                if select_from_device.is_visible(timeout=config['implicitly_wait'] * 1000):
                    logger.info('🔎 Кнопка "Select from device" найдена')
                    
                    # Вместо клика по кнопке, находим скрытый input[type="file"] и загружаем через него
                    logger.info('[SEARCH] Поиск скрытого элемента загрузки файла...')
                    upload_input = page.locator("input[type='file']")
                    
                    # Проверяем, что элемент существует
                    if upload_input.count() > 0:
                        logger.info(f'📤 Загрузка файла напрямую через input: {video}')
                        upload_input.set_input_files(video)
                        logger.info('[WAIT] Ожидание после загрузки файла...')
                        time.sleep(5)
                    else:
                        # Если не нашли скрытый input, пробуем сначала кликнуть по кнопке
                        logger.info('👆 Нажатие кнопки "Select from device"')
                        select_from_device.click()
                        logger.info('[WAIT] Ожидание после нажатия кнопки "Select from device"...')
                        time.sleep(3)
                        
                        # После клика пробуем найти input снова
                        logger.info('[SEARCH] Повторный поиск элемента загрузки файла...')
                        upload_input = page.locator("input[type='file']")
                        if upload_input.count() > 0:
                            logger.info(f'📤 Загрузка файла после клика: {video}')
                            upload_input.set_input_files(video)
                            logger.info('[WAIT] Ожидание после загрузки файла...')
                            time.sleep(5)
                        else:
                            logger.error('[FAIL] Не удалось найти элемент для загрузки файла')
                else:
                    logger.info('ℹ️ Кнопка "Select from device" не найдена, используем стандартный метод загрузки')
            except Exception as e:
                logger.info(f'[WARN] Кнопка "Select from device" не найдена, продолжаем: {str(e)}')
                
                # Стандартный метод загрузки файла
                logger.info('[SEARCH] Поиск стандартного элемента загрузки файла...')
                upload_input = page.locator("input[type='file']")
                logger.info('[WAIT] Ожидание появления элемента загрузки файла...')
                upload_input.wait_for(state="attached", timeout=config['explicit_wait'] * 1000)
                logger.info(f'📤 Загрузка файла стандартным методом: {video}')
                upload_input.set_input_files(video)
                logger.info('[WAIT] Ожидание после загрузки файла...')
                time.sleep(15)  # Увеличиваем время ожидания после загрузки файла до 15 секунд
            
            # Check for confirmation dialog
            try:
                logger.info('[SEARCH] Проверка диалога подтверждения...')
                ok_button = page.locator("xpath=" + config['selectors']['upload']['OK'])
                if ok_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                    logger.info('👆 Нажатие кнопки OK')
                    ok_button.click()
                    logger.info('[WAIT] Ожидание после нажатия кнопки OK...')
                    time.sleep(3)
            except Exception as e:
                logger.info(f'[WARN] Диалог подтверждения не найден, продолжаем: {str(e)}')
                pass
                
            # Configure crop settings
            logger.info('🖼️ Настройка кадрирования видео...')
            
            # Попытка найти элемент выбора кадрирования несколькими способами
            try:
                logger.info('[SEARCH] Поиск элемента выбора кадрирования...')
                
                # Метод 1: по XPath из конфига
                try:
                    select_crop = page.locator("xpath=" + config['selectors']['upload']['select_crop'])
                    logger.info('[WAIT] Ожидание появления элемента выбора кадрирования (XPath)...')
                    if select_crop.is_visible(timeout=config['implicitly_wait'] * 1000):
                        logger.info('👆 Открытие меню кадрирования (XPath)')
                        select_crop.click()
                        logger.info('[WAIT] Ожидание после открытия меню кадрирования...')
                        time.sleep(3)
                    else:
                        raise Exception("Элемент не найден через XPath")
                except Exception as e:
                    logger.info(f'[WARN] Не удалось найти элемент кадрирования через XPath: {str(e)}')
                    
                    # Метод 2: по тексту "Select crop"
                    try:
                        logger.info('[SEARCH] Поиск элемента выбора кадрирования по тексту...')
                        select_crop_text = page.get_by_text("Select crop", exact=False)
                        if select_crop_text.is_visible(timeout=config['implicitly_wait'] * 1000):
                            logger.info('👆 Открытие меню кадрирования (по тексту)')
                            select_crop_text.click()
                            logger.info('[WAIT] Ожидание после открытия меню кадрирования...')
                            time.sleep(3)
                        else:
                            raise Exception("Элемент не найден по тексту")
                    except Exception as e:
                        logger.info(f'[WARN] Не удалось найти элемент кадрирования по тексту: {str(e)}')
                        
                        # Метод 3: по роли кнопки
                        try:
                            logger.info('[SEARCH] Поиск элемента выбора кадрирования по роли...')
                            select_crop_button = page.get_by_role("button", name="Select crop")
                            if select_crop_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                                logger.info('👆 Открытие меню кадрирования (по роли)')
                                select_crop_button.click()
                                logger.info('[WAIT] Ожидание после открытия меню кадрирования...')
                                time.sleep(3)
                            else:
                                raise Exception("Элемент не найден по роли")
                        except Exception as e:
                            logger.info(f'[WARN] Не удалось найти элемент кадрирования по роли: {str(e)}')
                            
                            # Если все методы не сработали, пробуем пропустить этот шаг
                            logger.info('[WARN] Не удалось найти элемент кадрирования, пропускаем этот шаг')
                            # Переходим к следующему шагу напрямую
                            self._next_page()
                            time.sleep(3)
                            # Пропускаем оставшуюся часть настройки кадрирования
                            raise Exception("Пропускаем настройку кадрирования")
                
                # Поиск опции оригинального кадрирования
                logger.info('[SEARCH] Поиск опции оригинального кадрирования...')
                
                # Метод 1: по XPath из конфига
                try:
                    original_crop = page.locator("xpath=" + config['selectors']['upload']['original_crop'])
                    logger.info('[WAIT] Ожидание появления опции оригинального кадрирования (XPath)...')
                    if original_crop.is_visible(timeout=config['implicitly_wait'] * 1000):
                        logger.info('👆 Выбор оригинального кадрирования (XPath)')
                        original_crop.click()
                        logger.info('[WAIT] Ожидание после выбора оригинального кадрирования...')
                        time.sleep(2)
                    else:
                        raise Exception("Элемент не найден через XPath")
                except Exception as e:
                    logger.info(f'[WARN] Не удалось найти опцию оригинального кадрирования через XPath: {str(e)}')
                    
                    # Метод 2: по тексту "Original"
                    try:
                        logger.info('[SEARCH] Поиск опции оригинального кадрирования по тексту...')
                        original_crop_text = page.get_by_text("Original", exact=True)
                        if original_crop_text.is_visible(timeout=config['implicitly_wait'] * 1000):
                            logger.info('👆 Выбор оригинального кадрирования (по тексту)')
                            original_crop_text.click()
                            logger.info('[WAIT] Ожидание после выбора оригинального кадрирования...')
                            time.sleep(2)
                        else:
                            raise Exception("Элемент не найден по тексту")
                    except Exception as e:
                        logger.info(f'[WARN] Не удалось найти опцию оригинального кадрирования по тексту: {str(e)}')
                        
                        # Метод 3: по роли опции
                        try:
                            logger.info('[SEARCH] Поиск опции оригинального кадрирования по роли...')
                            original_crop_option = page.get_by_role("option", name="Original")
                            if original_crop_option.is_visible(timeout=config['implicitly_wait'] * 1000):
                                logger.info('👆 Выбор оригинального кадрирования (по роли)')
                                original_crop_option.click()
                                logger.info('[WAIT] Ожидание после выбора оригинального кадрирования...')
                                time.sleep(2)
                            else:
                                raise Exception("Элемент не найден по роли")
                        except Exception as e:
                            logger.info(f'[WARN] Не удалось найти опцию оригинального кадрирования по роли: {str(e)}')
                
                # Закрытие меню кадрирования
                try:
                    logger.info('👆 Закрытие меню кадрирования')
                    # Используем первый найденный элемент select_crop
                    select_crop.click()
                except Exception as e:
                    logger.info(f'[WARN] Не удалось закрыть меню кадрирования: {str(e)}')
                    # Пробуем нажать Escape для закрытия меню
                    page.keyboard.press("Escape")
                
                logger.info('[WAIT] Ожидание после настройки кадрирования...')
                time.sleep(3)
                
            except Exception as e:
                logger.info(f'[WARN] Пропущена настройка кадрирования: {str(e)}')
            
            # Navigate through the upload steps
            for i in range(2):
                logger.info(f'⏭️ Переход к следующему шагу ({i+1}/2)...')
                self._next_page()
                logger.info(f'[WAIT] Ожидание после перехода к шагу {i+1}...')
                time.sleep(4)
            
            # Add description
            logger.info(f'[TEXT] Ввод описания: {title}')
            try:
                logger.info('[SEARCH] Поиск поля для ввода описания...')
                description_field = page.locator("xpath=" + config['selectors']['upload']['description_field'])
                logger.info('[WAIT] Ожидание появления поля для ввода описания...')
                description_field.wait_for(state="visible", timeout=config['implicitly_wait'] * 1000)
                logger.info('⌨️ Ввод текста описания...')
                # Используем realistic_type вместо fill для имитации человеческого набора
                realistic_type(page, "xpath=" + config['selectors']['upload']['description_field'], title)
            except Exception as e:
                logger.error(f'[FAIL] Ошибка при вводе описания: {str(e)}')
            
            # Add location if specified
            if location:
                logger.info(f'[LOCATION] Ввод локации: {location}')
                logger.info('[SEARCH] Поиск поля для ввода локации...')
                location_field = page.locator("xpath=" + config['selectors']['upload']['location_field'])
                logger.info('[WAIT] Ожидание появления поля для ввода локации...')
                location_field.wait_for(state="visible", timeout=config['implicitly_wait'] * 1000)
                logger.info('⌨️ Ввод текста локации...')
                realistic_type(page, "xpath=" + config['selectors']['upload']['location_field'], location)
                
                logger.info('[SEARCH] Поиск подходящей локации в выпадающем списке...')
                first_location = page.locator("xpath=" + config['selectors']['upload']['first_location'])
                logger.info('[WAIT] Ожидание появления локации в списке...')
                first_location.wait_for(state="visible", timeout=config['explicit_wait'] * 1000)
                logger.info('👆 Выбор локации')
                first_location.click()
                logger.info('[WAIT] Ожидание после выбора локации...')
                time.sleep(3)
            
            # Add mentions if specified
            if mentions:
                logger.info(f'[USERS] Добавление упоминаний: {", ".join(mentions)}')
                for mention in mentions:
                    logger.info(f'➕ Добавление упоминания: {mention}')
                    logger.info('[SEARCH] Поиск поля для ввода упоминания...')
                    mention_field = page.locator("xpath=" + config['selectors']['upload']['mentions_field'])
                    logger.info('⌨️ Ввод имени пользователя для упоминания...')
                    mention_field.fill(mention)
                    logger.info('[WAIT] Ожидание после ввода имени пользователя...')
                    time.sleep(3)
                    
                    logger.info('[SEARCH] Поиск пользователя для упоминания в выпадающем списке...')
                    first_mention = page.locator("xpath=" + config['selectors']['upload']['first_mention'].format(mention))
                    logger.info('[WAIT] Ожидание появления пользователя в списке...')
                    first_mention.wait_for(state="visible", timeout=config['explicit_wait'] * 1000)
                    logger.info('👆 Выбор пользователя')
                    first_mention.click()
                    logger.info('[WAIT] Ожидание после выбора пользователя...')
                    time.sleep(2)
                
                logger.info('[OK] Завершение добавления упоминаний')
                logger.info('[SEARCH] Поиск кнопки "Готово"...')
                done_btn = page.locator("xpath=" + config['selectors']['upload']['done_mentions'])
                logger.info('👆 Нажатие кнопки "Готово"')
                done_btn.click()
                logger.info('[WAIT] Ожидание после нажатия кнопки "Готово"...')
                time.sleep(3)
            
            # Post the video
            logger.info('[START] Публикация видео...')
            logger.info('[SEARCH] Поиск кнопки публикации видео...')
            post_video_button = page.locator("xpath=" + config['selectors']['upload']['post_video'])
            logger.info('👆 Нажатие кнопки публикации')
            post_video_button.click()
            logger.info('[WAIT] Длительное ожидание процесса публикации...')
            time.sleep(10)  # Увеличенное время ожидания публикации
            
            try:
                # Wait for confirmation that the video was posted
                logger.info('[WAIT] Ожидание подтверждения публикации...')
                is_posted = page.locator("xpath=" + config['selectors']['upload']['is_posted'])
                logger.info('[WAIT] Ожидание появления индикатора успешной публикации...')
                is_posted.wait_for(state="visible", timeout=config['explicit_wait'] * 1000)
                logger.info(f'[OK] Видео {video} успешно опубликовано!')
            except Exception as e:
                logger.error(f'[FAIL] Видео {video} не опубликовано. Проверьте наличие ошибок: {str(e)}')
            
            # Refresh the page
            logger.info('[RETRY] Обновление страницы...')
            page.reload()
            logger.info('[WAIT] Ожидание после обновления страницы...')
            time.sleep(5)
            
            return True
        except Exception as e:
            logger.error(f'[FAIL] Ошибка при загрузке видео {video}: {str(e)}')
            return False

    def _next_page(self):
        """Click the next button during video upload"""
        logger.info('[SEARCH] Поиск кнопки "Далее"...')
        time.sleep(5)  # Увеличиваем время ожидания перед поиском кнопки
        
        # Попробуем несколько способов найти кнопку Next
        try:
            # Метод 1: по XPath из конфига
            logger.info('[SEARCH] Поиск кнопки "Далее" по XPath...')
            next_button = self.page.locator("xpath=" + config['selectors']['upload']['next'])
            if next_button.is_visible(timeout=config['implicitly_wait'] * 1000):
                logger.info('👆 Нажатие кнопки "Далее" (XPath)')
                next_button.click()
                logger.info('[WAIT] Ожидание после нажатия кнопки "Далее"...')
                time.sleep(5)  # Увеличиваем время ожидания после нажатия кнопки
                return True
        except Exception as e:
            logger.info(f'[WARN] Не удалось найти кнопку "Далее" по XPath: {str(e)}')
        
        # Метод 2: по тексту
        try:
            logger.info('[SEARCH] Поиск кнопки "Далее" по тексту...')
            next_button_text = self.page.get_by_text("Next", exact=True)
            if next_button_text.is_visible(timeout=config['implicitly_wait'] * 1000):
                logger.info('👆 Нажатие кнопки "Далее" (по тексту)')
                next_button_text.click()
                logger.info('[WAIT] Ожидание после нажатия кнопки "Далее"...')
                time.sleep(5)
                return True
        except Exception as e:
            logger.info(f'[WARN] Не удалось найти кнопку "Далее" по тексту: {str(e)}')
        
        # Метод 3: по роли кнопки
        try:
            logger.info('[SEARCH] Поиск кнопки "Далее" по роли...')
            next_button_role = self.page.get_by_role("button", name="Next")
            if next_button_role.is_visible(timeout=config['implicitly_wait'] * 1000):
                logger.info('👆 Нажатие кнопки "Далее" (по роли)')
                next_button_role.click()
                logger.info('[WAIT] Ожидание после нажатия кнопки "Далее"...')
                time.sleep(5)
                return True
        except Exception as e:
            logger.info(f'[WARN] Не удалось найти кнопку "Далее" по роли: {str(e)}')
        
        # Метод 4: по атрибуту aria-label
        try:
            logger.info('[SEARCH] Поиск кнопки "Далее" по aria-label...')
            next_button_aria = self.page.locator('[aria-label="Next"]')
            if next_button_aria.is_visible(timeout=config['implicitly_wait'] * 1000):
                logger.info('👆 Нажатие кнопки "Далее" (по aria-label)')
                next_button_aria.click()
                logger.info('[WAIT] Ожидание после нажатия кнопки "Далее"...')
                time.sleep(5)
                return True
        except Exception as e:
            logger.info(f'[WARN] Не удалось найти кнопку "Далее" по aria-label: {str(e)}')
        
        # Если все методы не сработали, пробуем нажать Tab и Enter
        try:
            logger.info('[SEARCH] Попытка использования клавиатуры для перехода к следующему шагу...')
            # Нажимаем Tab несколько раз, чтобы переместиться к кнопке Next
            for _ in range(5):
                self.page.keyboard.press("Tab")
                time.sleep(0.5)
            
            # Нажимаем Enter, предполагая, что мы на кнопке Next
            self.page.keyboard.press("Enter")
            logger.info('[WAIT] Ожидание после нажатия Enter...')
            time.sleep(5)
            return True
        except Exception as e:
            logger.error(f'[FAIL] Все методы поиска кнопки "Далее" не сработали: {str(e)}')
            return False

    def upload_videos(self, videos: list[dict]):
        """Upload multiple videos"""
        success = True
        
        logger.info(f'[CLIPBOARD] Начинаем загрузку {len(videos)} видео')
        
        for i, video in enumerate(videos):
            try:
                logger.info(f'[VIDEO] Загрузка видео {i+1}/{len(videos)}')
                result = self.upload_video(
                    video=video['video_path'],
                    title=video['title'] if video['title'] else video['video_path'],
                    location=video['location'] if video['location'] else None,
                    mentions=video['mentions'] if video['mentions'] else None
                )
                if not result:
                    logger.error(f'[FAIL] Не удалось загрузить видео {i+1}/{len(videos)}')
                    success = False
                else:
                    logger.info(f'[OK] Видео {i+1}/{len(videos)} успешно загружено')
                    
                # Добавляем случайную задержку между загрузками видео
                if i < len(videos) - 1:  # Если это не последнее видео
                    logger.info('[WAIT] Ожидание перед загрузкой следующего видео...')
                    random_delay("major")
            except Exception as e:
                logger.error(f'[FAIL] Ошибка при загрузке видео {i+1}/{len(videos)}: {str(e)}')
                success = False
        
        # Close the browser
        logger.info('🔒 Закрытие браузера...')
        close_browser(browser_data)
        
        if success:
            logger.info('[OK] Все видео успешно загружены')
        else:
            logger.warning('[WARN] Некоторые видео не были загружены')
            
        return success 