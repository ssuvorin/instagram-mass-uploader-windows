# Dolphin{anty} Remote API - Detailed Python Documentation

Эта документация содержит подробные примеры использования Dolphin{anty} Remote API с помощью Python, включая детальное описание заголовков (headers) и тел запросов (body) для каждого метода.

## Содержание

1. [Установка необходимых библиотек](#установка-необходимых-библиотек)
2. [Базовый класс клиента API](#базовый-класс-клиента-api)
3. [Работа с профилями браузера](#работа-с-профилями-браузера)
   - [GET /browser_profiles - Получение списка профилей](#get-browser_profiles---получение-списка-профилей)
   - [GET /browser_profiles/{id} - Получение информации о профиле](#get-browser_profilesid---получение-информации-о-профиле)
   - [POST /browser_profiles - Создание профиля браузера](#post-browser_profiles---создание-профиля-браузера)
   - [PATCH /browser_profiles/{id} - Обновление профиля браузера](#patch-browser_profilesid---обновление-профиля-браузера)
   - [DELETE /browser_profiles/{id} - Удаление профиля браузера](#delete-browser_profilesid---удаление-профиля-браузера)
   - [POST /browser_profiles/mass - Создание нескольких профилей](#post-browser_profilesmass---создание-нескольких-профилей)
   - [DELETE /browser_profiles - Удаление нескольких профилей](#delete-browser_profiles---удаление-нескольких-профилей)
   - [POST /browser_profiles/transfer - Передача профиля другому пользователю](#post-browser_profilestransfer---передача-профиля-другому-пользователю)
4. [Работа со статусами профилей](#работа-со-статусами-профилей)
   - [GET /browser_profiles/statuses - Получение списка статусов профилей](#get-browser_profilesstatuses---получение-списка-статусов-профилей)
5. [Работа с домашней страницей профиля](#работа-с-домашней-страницей-профиля)
   - [GET /browser_profiles/{id}/homepage - Получение домашней страницы профиля](#get-browser_profilesidhomepage---получение-домашней-страницы-профиля)
   - [PATCH /browser_profiles/{id}/homepage - Обновление домашней страницы профиля](#patch-browser_profilesidhomepage---обновление-домашней-страницы-профиля)
6. [Работа с прокси](#работа-с-прокси)
   - [GET /proxies - Получение списка прокси](#get-proxies---получение-списка-прокси)
   - [GET /proxies/{id} - Получение информации о прокси](#get-proxiesid---получение-информации-о-прокси)
   - [POST /proxies - Создание нового прокси](#post-proxies---создание-нового-прокси)
   - [PATCH /proxies/{id} - Обновление прокси](#patch-proxiesid---обновление-прокси)
   - [DELETE /proxies/{id} - Удаление прокси](#delete-proxiesid---удаление-прокси)
   - [POST /proxies/check - Проверка работоспособности прокси](#post-proxiescheck---проверка-работоспособности-прокси)
7. [Работа с cookies](#работа-с-cookies)
   - [GET /browser_profiles/{id}/cookies - Получение cookies профиля](#get-browser_profilesidcookies---получение-cookies-профиля)
   - [PATCH /browser_profiles/{id}/cookies - Обновление cookies профиля](#patch-browser_profilesidcookies---обновление-cookies-профиля)
   - [DELETE /browser_profiles/{id}/cookies - Удаление cookies профиля](#delete-browser_profilesidcookies---удаление-cookies-профиля)
8. [Работа с отпечатками браузера](#работа-с-отпечатками-браузера)
   - [GET /browser_profiles/{id}/fingerprints - Получение отпечатков браузера](#get-browser_profilesidfingerprints---получение-отпечатков-браузера)
   - [PATCH /browser_profiles/{id}/fingerprints - Обновление отпечатков браузера](#patch-browser_profilesidfingerprints---обновление-отпечатков-браузера)
9. [Работа с закладками](#работа-с-закладками)
   - [GET /browser_profiles/{id}/bookmarks - Получение закладок профиля](#get-browser_profilesidbookmarks---получение-закладок-профиля)
   - [PATCH /browser_profiles/{id}/bookmarks - Обновление закладок профиля](#patch-browser_profilesidbookmarks---обновление-закладок-профиля)
10. [Работа с расширениями](#работа-с-расширениями)
    - [GET /browser_profiles/{id}/extensions - Получение расширений профиля](#get-browser_profilesidextensions---получение-расширений-профиля)
    - [PATCH /browser_profiles/{id}/extensions - Обновление расширений профиля](#patch-browser_profilesidextensions---обновление-расширений-профиля)
    - [GET /extensions - Получение списка доступных расширений](#get-extensions---получение-списка-доступных-расширений)
11. [Работа с локальным хранилищем](#работа-с-локальным-хранилищем)
    - [GET /browser_profiles/{id}/local_storage - Получение данных локального хранилища](#get-browser_profilesidlocal_storage---получение-данных-локального-хранилища)
    - [PATCH /browser_profiles/{id}/local_storage - Обновление данных локального хранилища](#patch-browser_profilesidlocal_storage---обновление-данных-локального-хранилища)
    - [DELETE /browser_profiles/{id}/local_storage - Удаление данных локального хранилища](#delete-browser_profilesidlocal_storage---удаление-данных-локального-хранилища)
12. [Работа с папками](#работа-с-папками)
    - [GET /folders - Получение списка папок](#get-folders---получение-списка-папок)
    - [GET /folders/{id} - Получение информации о папке](#get-foldersid---получение-информации-о-папке)
    - [POST /folders - Создание новой папки](#post-folders---создание-новой-папки)
    - [PATCH /folders/{id} - Обновление папки](#patch-foldersid---обновление-папки)
    - [DELETE /folders/{id} - Удаление папки](#delete-foldersid---удаление-папки)
    - [GET /folders/{id}/profiles - Получение профилей в папке](#get-foldersidprofiles---получение-профилей-в-папке)
    - [POST /folders/mass/attach-profiles - Перемещение профилей в папку](#post-foldersmassattach-profiles---перемещение-профилей-в-папку)
13. [Управление доступом](#управление-доступом)
    - [POST /browser_profiles/access - Предоставление доступа к нескольким профилям](#post-browser_profilesaccess---предоставление-доступа-к-нескольким-профилям)
    - [PATCH /browser_profiles/{id}/access - Предоставление доступа к одному профилю](#patch-browser_profilesidaccess---предоставление-доступа-к-одному-профилю)
14. [Асинхронная версия клиента](#асинхронная-версия-клиента)
15. [Обработка ошибок](#обработка-ошибок)

## Установка необходимых библиотек

```python
# Установка библиотек
# pip install requests aiohttp

import requests
import json
import aiohttp
import asyncio
import logging

# Настройка логирования (опционально)
logging.basicConfig(
    level=logging.INFO,
    format=\'%(asctime)s - %(name)s - %(levelname)s - %(message)s\'
)
logger = logging.getLogger(\'dolphin_anty_api\')
```

## Базовый класс клиента API

```python
class DolphinAntyAPIError(Exception):
    """Исключение для ошибок API Dolphin{anty}"""
    def __init__(self, message, status_code=None, response=None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

class DolphinAntyAPI:
    """
    Базовый класс для работы с Dolphin{anty} Remote API
    """
    
    def __init__(self, api_token=None, base_url="https://dolphin-anty-api.com"):
        """
        Инициализация клиента API
        
        Args:
            api_token (str): Токен авторизации API. Получается в панели Dolphin{anty}.
            base_url (str): Базовый URL API. По умолчанию "https://dolphin-anty-api.com".
        """
        self.base_url = base_url.rstrip(\'/\')
        self.api_token = api_token
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}" if api_token else ""
        }
        logger.info(f"Инициализирован клиент API для {self.base_url}")
    
    def set_token(self, api_token):
        """
        Установка или обновление токена авторизации после инициализации.
        
        Args:
            api_token (str): Токен авторизации API.
        """
        self.api_token = api_token
        self.headers["Authorization"] = f"Bearer {api_token}"
        logger.info("Установлен новый токен API")
    
    def _make_request(self, method, endpoint, params=None, data=None, json_data=None):
        """
        Внутренний метод для выполнения HTTP-запросов к API.
        
        Args:
            method (str): HTTP-метод (GET, POST, PATCH, DELETE).
            endpoint (str): Конечная точка API (например, "/browser_profiles").
            params (dict, optional): Параметры URL-запроса (для GET).
            data (dict, optional): Данные формы (application/x-www-form-urlencoded).
            json_data (dict or list, optional): Данные в формате JSON (application/json).
            
        Returns:
            dict or list: Ответ API в формате JSON.
            
        Raises:
            DolphinAntyAPIError: В случае ошибки API (статус >= 400).
            requests.exceptions.RequestException: В случае ошибки сети или соединения.
        """
        url = f"{self.base_url}/{endpoint.lstrip(\'/\')}"
        current_headers = self.headers.copy()
        
        # Определяем Content-Type в зависимости от типа данных
        if data is not None:
            current_headers["Content-Type"] = "application/x-www-form-urlencoded"
            # Удаляем Content-Type: application/json, если передаем form-data
            if "application/json" in current_headers.get("Content-Type", ""):
                 del current_headers["Content-Type"]
        elif json_data is not None:
            current_headers["Content-Type"] = "application/json"
        else: # Для GET, DELETE без тела
            if "Content-Type" in current_headers:
                del current_headers["Content-Type"]

        logger.debug(f"Выполняется {method} запрос к {url}")
        logger.debug(f"Заголовки: {current_headers}")
        if params: logger.debug(f"Параметры: {params}")
        if data: logger.debug(f"Данные формы: {data}")
        if json_data: logger.debug(f"JSON тело: {json_data}")
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=current_headers,
                params=params,
                data=data,
                json=json_data,
                timeout=60  # Увеличиваем таймаут
            )
            
            logger.debug(f"Статус ответа: {response.status_code}")
            
            if response.status_code >= 400:
                error_msg = "Ошибка API"
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict):
                        error_msg = error_data.get(\'message\', error_data.get(\'error\', error_msg))
                except ValueError:
                    error_msg = response.text or error_msg
                
                logger.error(f"API вернул ошибку {response.status_code}: {error_msg}")
                raise DolphinAntyAPIError(
                    message=error_msg,
                    status_code=response.status_code,
                    response=response
                )
            
            # Обработка успешных ответов без тела (например, 204 No Content)
            if response.status_code == 204 or not response.content:
                logger.debug("Получен пустой успешный ответ (204 No Content или 0 байт).")
                return {"success": True, "status_code": response.status_code}
                
            # Попытка декодировать JSON
            try:
                result = response.json()
                logger.debug(f"Получен ответ: {result}")
                return result
            except ValueError as json_error:
                logger.error(f"Не удалось декодировать JSON из ответа: {response.text}")
                raise DolphinAntyAPIError(
                    message=f"Некорректный JSON в ответе: {json_error}",
                    status_code=response.status_code,
                    response=response
                )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса: {str(e)}")
            raise DolphinAntyAPIError(
                message=f"Ошибка сети или соединения: {str(e)}",
                status_code=None,
                response=getattr(e, \'response\', None)
            )

    # --- Методы API --- 

    ## Работа с профилями браузера

    def get_browser_profiles(self, limit=50, page=1, query=None, tags=None, statuses=None, mainWebsites=None, users=None):
        """
        Получение списка профилей браузера с фильтрацией.
        
        Эндпоинт: GET /browser_profiles
        
        Args:
            limit (int, optional): Количество профилей на странице. Макс. 50. По умолчанию 50.
            page (int, optional): Номер страницы. По умолчанию 1.
            query (str, optional): Текстовый поиск по имени профиля.
            tags (list[str], optional): Массив тегов для фильтрации (работает в режиме AND).
            statuses (list[int], optional): Массив ID статусов для фильтрации.
            mainWebsites (list[str], optional): Массив основных веб-сайтов для фильтрации (например, ["facebook", "google"]).
            users (list[int], optional): Массив ID пользователей для фильтрации.
            
        Returns:
            dict: Словарь с ключами "data" (список профилей) и "total" (общее количество).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        params = {
            "limit": limit,
            "page": page
        }
        if query: params["query"] = query
        if tags: params["tags[]"] = tags
        if statuses: params["statuses[]"] = statuses
        if mainWebsites: params["mainWebsites[]"] = mainWebsites
        if users: params["users[]"] = users
        
        logger.info(f"Получение списка профилей с параметрами: {params}")
        return self._make_request(
            method="GET",
            endpoint="/browser_profiles",
            params=params
        )

    def get_browser_profile(self, profile_id):
        """
        Получение детальной информации о конкретном профиле браузера.
        
        Эндпоинт: GET /browser_profiles/{id}
        
        Args:
            profile_id (int): ID профиля браузера.
            
        Returns:
            dict: Словарь с полной информацией о профиле.
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Получение информации о профиле ID: {profile_id}")
        return self._make_request(
            method="GET",
            endpoint=f"/browser_profiles/{profile_id}"
        )

    def create_browser_profile(self, profile_data):
        """
        Создание нового профиля браузера.
        
        Эндпоинт: POST /browser_profiles
        
        Args:
            profile_data (dict): Словарь с параметрами нового профиля.
                Обязательные поля:
                    name (str): Имя профиля.
                    platform (str): Платформа ("windows", "macos", "linux").
                    browserType (str): Тип браузера ("anty").
                Необязательные поля:
                    tags (list[str]): Список тегов.
                    mainWebsite (str): Основной веб-сайт ("facebook", "google", "tiktok", "crypto").
                    useragent (dict): Настройки User-Agent.
                        mode (str): "manual". # ВАЖНО: Только 'manual' согласно документации Postman
                        value (str, optional): Значение User-Agent (требуется, если mode="manual").
                    webrtc (dict): Настройки WebRTC.
                        mode (str): "off", "real", "altered", "manual". # Исправлено согласно документации Postman
                        ipAddress (str, optional): IP-адрес (требуется, если mode="manual").
                    canvas (dict): Настройки Canvas.
                        mode (str): "real", "noise", "off".
                    webgl (dict): Настройки WebGL.
                        mode (str): "real", "noise", "off".
                    webglInfo (dict): Детали WebGL.
                        mode (str): "off", "manual". # Исправлено согласно документации Postman
                        vendor (str, optional): Vendor (требуется, если mode="manual").
                        renderer (str, optional): Renderer (требуется, если mode="manual").
                        webgl2Maximum (dict, optional): Параметры WebGL2 (если mode="manual").
                    timezone (dict): Настройки часового пояса.
                        mode (str): "auto" или "manual".
                        value (str, optional): Часовой пояс (например, "Europe/Moscow", если mode="manual").
                    locale (dict): Настройки локали.
                        mode (str): "auto" или "manual".
                        value (str, optional): Локаль (например, "ru-RU", если mode="manual").
                    geolocation (dict): Настройки геолокации.
                        mode (str): "auto", "manual". # Исправлено согласно документации Postman
                        latitude (float, optional): Широта (требуется, если mode="manual").
                        longitude (float, optional): Долгота (требуется, если mode="manual").
                        accuracy (int, optional): Точность (требуется, если mode="manual").
                    cpu (dict): Настройки CPU.
                        mode (str): "manual" или "real".
                        value (int, optional): Количество ядер (если mode="manual").
                    memory (dict): Настройки памяти.
                        mode (str): "manual" или "real".
                        value (int, optional): Объем памяти (ГБ) (если mode="manual").
                    screen (dict): Настройки экрана.
                        mode (str): "real". # Исправлено согласно документации Postman
                        resolution (str, optional): Разрешение (например, "1920x1080").
                    mediaDevices (dict): Настройки медиа-устройств.
                        mode (str): "real". # Исправлено согласно документации Postman
                        audioInputs (int, optional): Количество аудиовходов.
                        videoInputs (int, optional): Количество видеовходов.
                        audioOutputs (int, optional): Количество аудиовыходов.
                    ports (dict): Настройки портов.
                        mode (str): "protect". # Исправлено согласно документации Postman
                        blacklist (str, optional): Список портов через запятую (например, "3389,5900,5800").
                    doNotTrack (bool): Значение Do Not Track (0 или 1).
                    proxy (dict): Настройки прокси.
                        id (int, optional): ID существующего прокси.
                        type (str, optional): Тип прокси ("http", "socks5", "ssh").
                        host (str, optional): Хост прокси.
                        port (int, optional): Порт прокси.
                        login (str, optional): Логин прокси.
                        password (str, optional): Пароль прокси.
                        name (str, optional): Имя нового прокси.
                        changeIpUrl (str, optional): URL для смены IP.
                    statusId (int, optional): ID статуса профиля.
                    notes (dict): Заметки к профилю.
                        content (str, optional): Текст заметки.
                        color (str, optional): Цвет ("blue", "green", "red", etc.).
                        icon (str, optional): Иконка.
                        style (str, optional): Стиль ("text").
            
        Returns:
            dict: Словарь с ID созданного профиля ("browserProfileId").
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Создание нового профиля с данными: {profile_data}")
        return self._make_request(
            method="POST",
            endpoint="/browser_profiles",
            json_data=profile_data
        )

    # ... (остальные методы будут добавлены аналогично) ...

```




    def update_browser_profile(self, profile_id, profile_data):
        """
        Обновление существующего профиля браузера.
        
        Эндпоинт: PATCH /browser_profiles/{id}
        
        Args:
            profile_id (int): ID профиля браузера для обновления.
            profile_data (dict): Словарь с параметрами для обновления. 
                Можно обновлять любые поля, доступные при создании (см. create_browser_profile).
                Пример полей для обновления:
                    name (str, optional): Новое имя профиля.
                    tags (list[str], optional): Новый список тегов (заменяет старый).
                    mainWebsite (str, optional): Новый основной веб-сайт.
                    useragent (dict, optional): Новые настройки User-Agent.
                    webrtc (dict, optional): Новые настройки WebRTC.
                    canvas (dict, optional): Новые настройки Canvas.
                    webgl (dict, optional): Новые настройки WebGL.
                    webglInfo (dict, optional): Новые детали WebGL.
                    timezone (dict, optional): Новые настройки часового пояса.
                    locale (dict, optional): Новые настройки локали.
                    geolocation (dict, optional): Новые настройки геолокации.
                    cpu (dict, optional): Новые настройки CPU.
                    memory (dict, optional): Новые настройки памяти.
                    screen (dict, optional): Новые настройки экрана.
                    mediaDevices (dict, optional): Новые настройки медиа-устройств.
                    ports (dict, optional): Новые настройки портов.
                    doNotTrack (bool, optional): Новое значение Do Not Track.
                    proxy (dict, optional): Новые настройки прокси (можно передать ID существующего или полные данные нового).
                    statusId (int, optional): Новый ID статуса профиля.
                    notes (dict, optional): Новые заметки к профилю.
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Обновление профиля ID: {profile_id} с данными: {profile_data}")
        return self._make_request(
            method="PATCH",
            endpoint=f"/browser_profiles/{profile_id}",
            json_data=profile_data
        )

    def delete_browser_profile(self, profile_id, force_delete=True):
        """
        Удаление профиля браузера.
        
        Эндпоинт: DELETE /browser_profiles/{id}
        
        Args:
            profile_id (int): ID профиля браузера для удаления.
            force_delete (bool, optional): Если True, удаляет профиль навсегда. 
                                         Если False, перемещает в корзину. По умолчанию True.
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        params = {}
        if force_delete:
            params["forceDelete"] = 1
        
        logger.info(f"Удаление профиля ID: {profile_id}, принудительно: {force_delete}")
        return self._make_request(
            method="DELETE",
            endpoint=f"/browser_profiles/{profile_id}",
            params=params
        )

    def create_multiple_profiles(self, common_data, profiles_data):
        """
        Создание нескольких профилей браузера одним запросом.
        
        Эндпоинт: POST /browser_profiles/mass
        
        Args:
            common_data (dict): Словарь с общими параметрами для всех создаваемых профилей 
                                (например, platform, browserType, общие настройки fingerprint).
            profiles_data (list[dict]): Список словарей, где каждый словарь содержит 
                                       уникальные параметры для одного профиля (например, name, tags).
                                       Поля такие же, как в `create_browser_profile`, но без общих.
            
        Returns:
            dict: Словарь с ключом "items", содержащим список ID созданных профилей.
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        data = {
            "common": common_data,
            "items": profiles_data
        }
        logger.info(f"Создание нескольких профилей. Общие данные: {common_data}, Уникальные: {len(profiles_data)} шт.")
        return self._make_request(
            method="POST",
            endpoint="/browser_profiles/mass",
            json_data=data
        )

    def delete_browser_profiles(self, profile_ids, force_delete=True):
        """
        Удаление нескольких профилей браузера одним запросом.
        
        Эндпоинт: DELETE /browser_profiles
        
        Args:
            profile_ids (list[int]): Список ID профилей для удаления.
            force_delete (bool, optional): Если True, удаляет профили навсегда. 
                                         Если False, перемещает в корзину. По умолчанию True.
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный, т.к. тело передается)
            Accept: application/json (Рекомендуемый)
        """
        params = {}
        if force_delete:
            params["forceDelete"] = 1
        
        body = {"ids": profile_ids}
        logger.info(f"Удаление профилей: {profile_ids}, принудительно: {force_delete}")
        return self._make_request(
            method="DELETE",
            endpoint="/browser_profiles",
            params=params,
            json_data=body
        )

    def transfer_browser_profile(self, profile_ids, username, with_proxy=True):
        """
        Передача профилей другому пользователю Dolphin{anty}.
        
        Эндпоинт: POST /browser_profiles/transfer
        
        Args:
            profile_ids (list[int]): Список ID профилей для передачи.
            username (str): Email пользователя-получателя.
            with_proxy (bool, optional): Передавать ли прокси вместе с профилем. По умолчанию True.
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
            # Content-Type не требуется, параметры передаются в URL
        """
        # Параметры передаются как query parameters, включая массив ID
        params = {
            "ids[]": profile_ids,
            "username": username,
            "withProxy": "true" if with_proxy else "false"
        }
        logger.info(f"Передача профилей {profile_ids} пользователю {username}, с прокси: {with_proxy}")
        return self._make_request(
            method="POST",
            endpoint="/browser_profiles/transfer",
            params=params
        )

    ## Работа со статусами профилей

    def get_profile_statuses(self, limit=50, page=1, query=None):
        """
        Получение списка доступных статусов профилей.
        
        Эндпоинт: GET /browser_profiles/statuses
        
        Args:
            limit (int, optional): Количество статусов на странице. По умолчанию 50.
            page (int, optional): Номер страницы. По умолчанию 1.
            query (str, optional): Текстовый поиск по названию статуса.
            
        Returns:
            dict: Словарь с ключами "data" (список статусов) и "total" (общее количество).
                Каждый статус содержит "id", "name", "color".
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        params = {
            "limit": limit,
            "page": page
        }
        if query: params["query"] = query
        
        logger.info(f"Получение списка статусов с параметрами: {params}")
        return self._make_request(
            method="GET",
            endpoint="/browser_profiles/statuses",
            params=params
        )

    ## Работа с домашней страницей профиля

    def get_browser_profile_homepage(self, profile_id):
        """
        Получение информации о домашней странице (стартовых вкладках) профиля браузера.
        
        Эндпоинт: GET /browser_profiles/{id}/homepage
        
        Args:
            profile_id (int): ID профиля браузера.
            
        Returns:
            dict: Словарь с ключом "homepages", содержащим список объектов страниц.
                Каждый объект страницы содержит "name" (str) и "url" (str).
                Пример: {"homepages": [{"name": "Google", "url": "https://google.com"}]}
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Получение домашней страницы профиля ID: {profile_id}")
        return self._make_request(
            method="GET",
            endpoint=f"/browser_profiles/{profile_id}/homepage"
        )

    def update_browser_profile_homepage(self, profile_id, homepages):
        """
        Обновление домашней страницы (стартовых вкладок) профиля браузера.
        Старые вкладки будут полностью заменены новыми.
        
        Эндпоинт: PATCH /browser_profiles/{id}/homepage
        
        Args:
            profile_id (int): ID профиля браузера.
            homepages (list[dict]): Список словарей, описывающих новые стартовые вкладки.
                Каждый словарь должен содержать:
                    name (str): Имя вкладки.
                    url (str): URL вкладки.
                Пример: [{"name": "Google", "url": "https://google.com"}, {"name": "Dolphin", "url": "https://dolphin.ru.com"}]
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        body = {"homepages": homepages}
        logger.info(f"Обновление домашней страницы профиля ID: {profile_id} на: {homepages}")
        return self._make_request(
            method="PATCH",
            endpoint=f"/browser_profiles/{profile_id}/homepage",
            json_data=body
        )

    ## Работа с прокси

    def get_proxies(self, limit=50, page=1, query=None):
        """
        Получение списка сохраненных прокси.
        
        Эндпоинт: GET /proxies
        
        Args:
            limit (int, optional): Количество прокси на странице. По умолчанию 50.
            page (int, optional): Номер страницы. По умолчанию 1.
            query (str, optional): Текстовый поиск по имени или хосту прокси.
            
        Returns:
            dict: Словарь с ключами "data" (список прокси) и "total" (общее количество).
                Каждый прокси содержит "id", "name", "type", "host", "port", "login", "password", "changeIpUrl".
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        params = {
            "limit": limit,
            "page": page
        }
        if query: params["query"] = query
        
        logger.info(f"Получение списка прокси с параметрами: {params}")
        return self._make_request(
            method="GET",
            endpoint="/proxies",
            params=params
        )

    def get_proxy(self, proxy_id):
        """
        Получение информации о конкретном сохраненном прокси.
        
        Эндпоинт: GET /proxies/{id}
        
        Args:
            proxy_id (int): ID прокси.
            
        Returns:
            dict: Словарь с информацией о прокси.
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Получение информации о прокси ID: {proxy_id}")
        return self._make_request(
            method="GET",
            endpoint=f"/proxies/{proxy_id}"
        )

    def create_proxy(self, proxy_data):
        """
        Создание и сохранение нового прокси.
        
        Эндпоинт: POST /proxies
        
        Args:
            proxy_data (dict): Словарь с параметрами нового прокси.
                Обязательные поля:
                    type (str): Тип прокси ("http", "socks5", "ssh").
                    host (str): Хост прокси.
                    port (int): Порт прокси.
                Необязательные поля:
                    name (str): Имя прокси.
                    login (str): Логин.
                    password (str): Пароль.
                    changeIpUrl (str): URL для смены IP.
            
        Returns:
            dict: Словарь с информацией о созданном прокси, включая его ID.
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Создание нового прокси с данными: {proxy_data}")
        return self._make_request(
            method="POST",
            endpoint="/proxies",
            json_data=proxy_data
        )

    def update_proxy(self, proxy_id, proxy_data):
        """
        Обновление существующего сохраненного прокси.
        
        Эндпоинт: PATCH /proxies/{id}
        
        Args:
            proxy_id (int): ID прокси для обновления.
            proxy_data (dict): Словарь с параметрами для обновления (любые поля из `create_proxy`).
            
        Returns:
            dict: Словарь с обновленной информацией о прокси.
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Обновление прокси ID: {proxy_id} с данными: {proxy_data}")
        return self._make_request(
            method="PATCH",
            endpoint=f"/proxies/{proxy_id}",
            json_data=proxy_data
        )

    def delete_proxy(self, proxy_id):
        """
        Удаление сохраненного прокси.
        
        Эндпоинт: DELETE /proxies/{id}
        
        Args:
            proxy_id (int): ID прокси для удаления.
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Удаление прокси ID: {proxy_id}")
        return self._make_request(
            method="DELETE",
            endpoint=f"/proxies/{proxy_id}"
        )

    def check_proxy(self, proxy_data):
        """
        Проверка работоспособности прокси без сохранения.
        
        Эндпоинт: POST /proxies/check
        
        Args:
            proxy_data (dict): Словарь с параметрами прокси для проверки (поля как в `create_proxy`).
            
        Returns:
            dict: Словарь с результатом проверки.
                Пример успеха: {"success": true, "message": "Proxy is working", "ip": "1.2.3.4", "country": "US", "city": "New York"}
                Пример ошибки: {"success": false, "message": "Connection timed out"}
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Проверка прокси с данными: {proxy_data}")
        return self._make_request(
            method="POST",
            endpoint="/proxies/check",
            json_data=proxy_data
        )

    ## Работа с cookies

    def get_cookies(self, profile_id):
        """
        Получение всех cookies для указанного профиля браузера.
        
        Эндпоинт: GET /browser_profiles/{id}/cookies
        
        Args:
            profile_id (int): ID профиля браузера.
            
        Returns:
            list[dict]: Список словарей, каждый из которых представляет один cookie.
                Поля cookie: "domain", "hostOnly", "httpOnly", "name", "path", "sameSite", 
                             "secure", "session", "storeId", "value", "expirationDate" (опционально).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Получение cookies для профиля ID: {profile_id}")
        return self._make_request(
            method="GET",
            endpoint=f"/browser_profiles/{profile_id}/cookies"
        )

    def update_cookies(self, profile_id, cookies_data):
        """
        Обновление (добавление или перезапись) cookies для профиля браузера.
        Существующие cookies с тем же `name` и `domain` будут перезаписаны.
        
        Эндпоинт: PATCH /browser_profiles/{id}/cookies
        
        Args:
            profile_id (int): ID профиля браузера.
            cookies_data (list[dict]): Список словарей с данными cookies для обновления/добавления.
                Формат каждого словаря см. в `get_cookies`.
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Обновление cookies для профиля ID: {profile_id}. Количество: {len(cookies_data)}")
        return self._make_request(
            method="PATCH",
            endpoint=f"/browser_profiles/{profile_id}/cookies",
            json_data=cookies_data
        )

    def delete_cookies(self, profile_id):
        """
        Удаление ВСЕХ cookies для указанного профиля браузера.
        
        Эндпоинт: DELETE /browser_profiles/{id}/cookies
        
        Args:
            profile_id (int): ID профиля браузера.
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Удаление всех cookies для профиля ID: {profile_id}")
        return self._make_request(
            method="DELETE",
            endpoint=f"/browser_profiles/{profile_id}/cookies"
        )

    ## Работа с отпечатками браузера

    def get_fingerprints(self, profile_id):
        """
        Получение текущих настроек отпечатков браузера для профиля.
        
        Эндпоинт: GET /browser_profiles/{id}/fingerprints
        
        Args:
            profile_id (int): ID профиля браузера.
            
        Returns:
            dict: Словарь с текущими настройками отпечатков (useragent, webrtc, canvas, webgl, etc.).
                  Структура соответствует полям, используемым при создании/обновлении профиля.
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Получение отпечатков для профиля ID: {profile_id}")
        return self._make_request(
            method="GET",
            endpoint=f"/browser_profiles/{profile_id}/fingerprints"
        )

    def update_fingerprints(self, profile_id, fingerprints_data):
        """
        Обновление настроек отпечатков браузера для профиля.
        
        Эндпоинт: PATCH /browser_profiles/{id}/fingerprints
        
        Args:
            profile_id (int): ID профиля браузера.
            fingerprints_data (dict): Словарь с новыми настройками отпечатков.
                Поля и структура соответствуют тем, что используются при создании/обновлении профиля 
                (useragent, webrtc, canvas, webgl, webglInfo, timezone, locale, geolocation, 
                 cpu, memory, screen, mediaDevices, ports, doNotTrack).
                Можно передавать только те поля, которые нужно изменить.
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Обновление отпечатков для профиля ID: {profile_id} с данными: {fingerprints_data}")
        return self._make_request(
            method="PATCH",
            endpoint=f"/browser_profiles/{profile_id}/fingerprints",
            json_data=fingerprints_data
        )

    ## Работа с закладками

    def get_bookmarks(self, profile_id):
        """
        Получение списка закладок для профиля браузера.
        
        Эндпоинт: GET /browser_profiles/{id}/bookmarks
        
        Args:
            profile_id (int): ID профиля браузера.
            
        Returns:
            list[dict]: Список словарей, каждый из которых представляет закладку.
                Поля закладки: "name" (str), "url" (str).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Получение закладок для профиля ID: {profile_id}")
        return self._make_request(
            method="GET",
            endpoint=f"/browser_profiles/{profile_id}/bookmarks"
        )

    def update_bookmarks(self, profile_id, bookmarks_data):
        """
        Обновление списка закладок для профиля браузера.
        Старый список закладок будет полностью заменен новым.
        
        Эндпоинт: PATCH /browser_profiles/{id}/bookmarks
        
        Args:
            profile_id (int): ID профиля браузера.
            bookmarks_data (list[dict]): Новый список словарей с закладками.
                Формат каждого словаря: {"name": "имя", "url": "адрес"}.
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Обновление закладок для профиля ID: {profile_id}. Количество: {len(bookmarks_data)}")
        return self._make_request(
            method="PATCH",
            endpoint=f"/browser_profiles/{profile_id}/bookmarks",
            json_data=bookmarks_data
        )

    ## Работа с расширениями

    def get_extensions(self, profile_id):
        """
        Получение списка расширений, установленных в профиле браузера.
        
        Эндпоинт: GET /browser_profiles/{id}/extensions
        
        Args:
            profile_id (int): ID профиля браузера.
            
        Returns:
            list[dict]: Список словарей, описывающих установленные расширения.
                Поля: "id" (str), "name" (str), "enabled" (bool).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Получение расширений для профиля ID: {profile_id}")
        return self._make_request(
            method="GET",
            endpoint=f"/browser_profiles/{profile_id}/extensions"
        )

    def update_extensions(self, profile_id, extensions_data):
        """
        Обновление списка и статуса расширений для профиля браузера.
        Старый список будет полностью заменен новым.
        
        Эндпоинт: PATCH /browser_profiles/{id}/extensions
        
        Args:
            profile_id (int): ID профиля браузера.
            extensions_data (list[dict]): Новый список словарей с расширениями.
                Формат каждого словаря: {"id": "extension_id", "enabled": true/false}.
                ID расширений можно получить из `get_available_extensions`.
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Обновление расширений для профиля ID: {profile_id}. Количество: {len(extensions_data)}")
        return self._make_request(
            method="PATCH",
            endpoint=f"/browser_profiles/{profile_id}/extensions",
            json_data=extensions_data
        )

    def get_available_extensions(self):
        """
        Получение списка всех расширений, доступных для установки в Dolphin{anty}.
        
        Эндпоинт: GET /extensions
        
        Returns:
            list[dict]: Список словарей, описывающих доступные расширения.
                Поля: "id" (str), "name" (str).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info("Получение списка доступных расширений")
        return self._make_request(
            method="GET",
            endpoint="/extensions"
        )

    ## Работа с локальным хранилищем

    def get_local_storage(self, profile_id, domain=None):
        """
        Получение данных локального хранилища (Local Storage) для профиля.
        
        Эндпоинт: GET /browser_profiles/{id}/local_storage
        
        Args:
            profile_id (int): ID профиля браузера.
            domain (str, optional): Если указан, возвращает данные только для этого домена.
            
        Returns:
            dict: Словарь, где ключи - домены, значения - словари с парами ключ-значение из Local Storage.
                Пример: {"example.com": {"key1": "value1"}, "site.org": {"token": "abc"}}
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        params = {}
        if domain: params["domain"] = domain
        logger.info(f"Получение Local Storage для профиля ID: {profile_id}, домен: {domain or 'все'}")
        return self._make_request(
            method="GET",
            endpoint=f"/browser_profiles/{profile_id}/local_storage",
            params=params
        )

    def update_local_storage(self, profile_id, storage_data):
        """
        Обновление (добавление или перезапись) данных в локальном хранилище профиля.
        
        Эндпоинт: PATCH /browser_profiles/{id}/local_storage
        
        Args:
            profile_id (int): ID профиля браузера.
            storage_data (dict): Словарь с данными для обновления.
                Ключи - домены, значения - словари с парами ключ-значение.
                Пример: {"example.com": {"key1": "new_value"}, "new-site.com": {"data": "123"}}
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Обновление Local Storage для профиля ID: {profile_id} с данными: {storage_data}")
        return self._make_request(
            method="PATCH",
            endpoint=f"/browser_profiles/{profile_id}/local_storage",
            json_data=storage_data
        )

    def delete_local_storage(self, profile_id, domain=None):
        """
        Удаление данных локального хранилища для профиля.
        
        Эндпоинт: DELETE /browser_profiles/{id}/local_storage
        
        Args:
            profile_id (int): ID профиля браузера.
            domain (str, optional): Если указан, удаляет данные только для этого домена.
                                  Если не указан, удаляет ВСЕ данные Local Storage для профиля.
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        params = {}
        if domain: params["domain"] = domain
        logger.info(f"Удаление Local Storage для профиля ID: {profile_id}, домен: {domain or 'все'}")
        return self._make_request(
            method="DELETE",
            endpoint=f"/browser_profiles/{profile_id}/local_storage",
            params=params
        )

    ## Работа с папками

    def get_folders(self):
        """
        Получение списка всех папок для профилей.
        
        Эндпоинт: GET /folders
        
        Returns:
            list[dict]: Список словарей, описывающих папки.
                Поля: "id" (int), "name" (str), "color" (str).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info("Получение списка папок")
        return self._make_request(
            method="GET",
            endpoint="/folders"
        )

    def get_folder(self, folder_id):
        """
        Получение информации о конкретной папке.
        
        Эндпоинт: GET /folders/{id}
        
        Args:
            folder_id (int): ID папки.
            
        Returns:
            dict: Словарь с информацией о папке ("id", "name", "color").
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Получение информации о папке ID: {folder_id}")
        return self._make_request(
            method="GET",
            endpoint=f"/folders/{folder_id}"
        )

    def create_folder(self, name, color=None):
        """
        Создание новой папки для профилей.
        
        Эндпоинт: POST /folders
        
        Args:
            name (str): Имя новой папки.
            color (str, optional): Цвет папки (например, "blue", "green").
            
        Returns:
            dict: Словарь с информацией о созданной папке, включая её ID.
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        body = {"name": name}
        if color: body["color"] = color
        logger.info(f"Создание папки с именем: {name}, цвет: {color}")
        return self._make_request(
            method="POST",
            endpoint="/folders",
            json_data=body
        )

    def update_folder(self, folder_id, name=None, color=None):
        """
        Обновление существующей папки.
        
        Эндпоинт: PATCH /folders/{id}
        
        Args:
            folder_id (int): ID папки для обновления.
            name (str, optional): Новое имя папки.
            color (str, optional): Новый цвет папки.
            
        Returns:
            dict: Словарь с обновленной информацией о папке.
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        body = {}
        if name: body["name"] = name
        if color: body["color"] = color
        if not body:
             logger.warning("Нет данных для обновления папки.")
             return {"success": False, "message": "No data provided for update"}
        logger.info(f"Обновление папки ID: {folder_id} с данными: {body}")
        return self._make_request(
            method="PATCH",
            endpoint=f"/folders/{folder_id}",
            json_data=body
        )

    def delete_folder(self, folder_id):
        """
        Удаление папки. Профили в папке не удаляются, а остаются без папки.
        
        Эндпоинт: DELETE /folders/{id}
        
        Args:
            folder_id (int): ID папки для удаления.
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        logger.info(f"Удаление папки ID: {folder_id}")
        return self._make_request(
            method="DELETE",
            endpoint=f"/folders/{folder_id}"
        )

    def get_folder_profiles(self, folder_id, limit=50, page=1):
        """
        Получение списка профилей, находящихся в указанной папке.
        
        Эндпоинт: GET /folders/{id}/profiles
        
        Args:
            folder_id (int): ID папки.
            limit (int, optional): Количество профилей на странице. По умолчанию 50.
            page (int, optional): Номер страницы. По умолчанию 1.
            
        Returns:
            dict: Словарь с ключами "data" (список профилей) и "total" (общее количество).
                  Формат профилей как в `get_browser_profiles`.
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        params = {
            "limit": limit,
            "page": page
        }
        logger.info(f"Получение профилей из папки ID: {folder_id} с параметрами: {params}")
        return self._make_request(
            method="GET",
            endpoint=f"/folders/{folder_id}/profiles",
            params=params
        )

    def move_profiles_to_folder(self, folder_id, profile_ids):
        """
        Перемещение одного или нескольких профилей в указанную папку.
        
        Эндпоинт: POST /folders/mass/attach-profiles
        
        Args:
            folder_id (int): ID папки назначения.
            profile_ids (list[int]): Список ID профилей для перемещения.
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        body = {
            "folderId": folder_id,
            "profileIds": profile_ids
        }
        logger.info(f"Перемещение профилей {profile_ids} в папку ID: {folder_id}")
        return self._make_request(
            method="POST",
            endpoint="/folders/mass/attach-profiles",
            json_data=body
        )

    ## Управление доступом

    def share_access_to_profiles(self, profile_ids, users_access, action="add"):
        """
        Предоставление или удаление доступа к нескольким профилям для пользователей.
        
        Эндпоинт: POST /browser_profiles/access
        
        Args:
            profile_ids (list[int]): Список ID профилей.
            users_access (list[dict]): Список словарей с правами доступа пользователей.
                Каждый словарь:
                    id (int): ID пользователя.
                    view (int): 1 - разрешить просмотр, 0 - запретить.
                    usage (int): 1 - разрешить использование, 0 - запретить.
                    update (int): 1 - разрешить обновление, 0 - запретить.
                    delete (int): 1 - разрешить удаление, 0 - запретить.
                    share (int): 1 - разрешить передачу, 0 - запретить.
            action (str, optional): Действие ("add" - добавить/обновить права, "remove" - удалить права). 
                                  По умолчанию "add".
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        body = {
            "ids": profile_ids,
            "users": users_access,
            "action": action
        }
        logger.info(f"Изменение доступа ({action}) для профилей {profile_ids}, пользователи: {users_access}")
        return self._make_request(
            method="POST",
            endpoint="/browser_profiles/access",
            json_data=body
        )

    def share_access_to_profile(self, profile_id, users_access):
        """
        Обновление прав доступа к одному профилю для пользователей.
        
        Эндпоинт: PATCH /browser_profiles/{id}/access
        
        Args:
            profile_id (int): ID профиля.
            users_access (list[dict]): Список словарей с правами доступа пользователей.
                Формат словарей как в `share_access_to_profiles`, но ключ "id" называется "userId".
                Пример: [{"userId": 1097599, "view": 1, "usage": 1, ...}]
            
        Returns:
            dict: Словарь с подтверждением успеха ("success": true).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Content-Type: application/json (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        body = {"users": users_access}
        logger.info(f"Обновление доступа для профиля {profile_id}, пользователи: {users_access}")
        return self._make_request(
            method="PATCH",
            endpoint=f"/browser_profiles/{profile_id}/access",
            json_data=body
        )

# --- Асинхронная версия клиента --- 

class AsyncDolphinAntyAPI:
    """
    Асинхронный клиент для работы с Dolphin{anty} Remote API (использует aiohttp)
    """
    
    def __init__(self, api_token=None, base_url="https://dolphin-anty-api.com"):
        self.base_url = base_url.rstrip(\"/\")
        self.api_token = api_token
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}" if api_token else ""
        }
        self.session = None
        logger.info(f"Инициализирован асинхронный клиент API для {self.base_url}")

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        logger.debug("Асинхронная сессия создана")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("Асинхронная сессия закрыта")
        self.session = None
    
    def set_token(self, api_token):
        self.api_token = api_token
        self.headers["Authorization"] = f"Bearer {api_token}"
        logger.info("Установлен новый токен API для асинхронного клиента")
    
    async def _make_request(self, method, endpoint, params=None, data=None, json_data=None):
        url = f"{self.base_url}/{endpoint.lstrip(\"/\")}"
        current_headers = self.headers.copy()
        
        if data is not None:
            current_headers["Content-Type"] = "application/x-www-form-urlencoded"
            if "application/json" in current_headers.get("Content-Type", ""):
                 del current_headers["Content-Type"]
        elif json_data is not None:
            current_headers["Content-Type"] = "application/json"
        else:
            if "Content-Type" in current_headers:
                del current_headers["Content-Type"]

        # Создаем сессию, если она не была создана через __aenter__
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            logger.warning("Асинхронная сессия была создана вне контекстного менеджера. Не забудьте закрыть ее вручную или использовать 'async with'.")

        logger.debug(f"Выполняется асинхронный {method} запрос к {url}")
        logger.debug(f"Заголовки: {current_headers}")
        if params: logger.debug(f"Параметры: {params}")
        if data: logger.debug(f"Данные формы: {data}")
        if json_data: logger.debug(f"JSON тело: {json_data}")

        try:
            async with self.session.request(
                method=method,
                url=url,
                headers=current_headers,
                params=params,
                data=data,
                json=json_data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                logger.debug(f"Статус ответа: {response.status}")
                
                if response.status >= 400:
                    error_msg = "Ошибка API"
                    try:
                        error_data = await response.json()
                        if isinstance(error_data, dict):
                             error_msg = error_data.get("message", error_data.get("error", error_msg))
                    except (ValueError, aiohttp.ContentTypeError):
                        error_text = await response.text()
                        error_msg = error_text or error_msg
                    
                    logger.error(f"API вернул ошибку {response.status}: {error_msg}")
                    raise DolphinAntyAPIError(
                        message=error_msg,
                        status_code=response.status,
                        response=response
                    )
                
                if response.status == 204 or response.content_length == 0:
                    logger.debug("Получен пустой успешный ответ (204 No Content или 0 байт).")
                    return {"success": True, "status_code": response.status}
                    
                try:
                    result = await response.json()
                    logger.debug(f"Получен ответ: {result}")
                    return result
                except (ValueError, aiohttp.ContentTypeError) as json_error:
                    error_text = await response.text()
                    logger.error(f"Не удалось декодировать JSON из ответа: {error_text}")
                    raise DolphinAntyAPIError(
                        message=f"Некорректный JSON в ответе: {json_error}",
                        status_code=response.status,
                        response=response
                    )

        except aiohttp.ClientError as e:
            logger.error(f"Ошибка клиента aiohttp: {str(e)}")
            raise DolphinAntyAPIError(
                message=f"Ошибка клиента aiohttp: {str(e)}",
                status_code=getattr(e, \'status\


', None)
            
    # Асинхронные методы API (аналогичны синхронным, но с префиксом 'async_')
    
    async def async_get_browser_profiles(self, limit=50, page=1, query=None, tags=None, statuses=None, mainWebsites=None, users=None):
        """
        Асинхронное получение списка профилей браузера с фильтрацией.
        
        Эндпоинт: GET /browser_profiles
        
        Args:
            limit (int, optional): Количество профилей на странице. Макс. 50. По умолчанию 50.
            page (int, optional): Номер страницы. По умолчанию 1.
            query (str, optional): Текстовый поиск по имени профиля.
            tags (list[str], optional): Массив тегов для фильтрации (работает в режиме AND).
            statuses (list[int], optional): Массив ID статусов для фильтрации.
            mainWebsites (list[str], optional): Массив основных веб-сайтов для фильтрации.
            users (list[int], optional): Массив ID пользователей для фильтрации.
            
        Returns:
            dict: Словарь с ключами "data" (список профилей) и "total" (общее количество).
            
        Headers:
            Authorization: Bearer {token} (Обязательный)
            Accept: application/json (Рекомендуемый)
        """
        params = {
            "limit": limit,
            "page": page
        }
        if query: params["query"] = query
        if tags: params["tags[]"] = tags
        if statuses: params["statuses[]"] = statuses
        if mainWebsites: params["mainWebsites[]"] = mainWebsites
        if users: params["users[]"] = users
        
        logger.info(f"Асинхронное получение списка профилей с параметрами: {params}")
        return await self._make_request(
            method="GET",
            endpoint="/browser_profiles",
            params=params
        )
    
    # ... (остальные асинхронные методы аналогичны синхронным) ...
```

## Примеры использования

### Пример 1: Базовое использование

```python
import requests
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация клиента API
api_token = "ваш_токен_api"  # Получите в панели Dolphin{anty}
api = DolphinAntyAPI(api_token=api_token)

# Получение списка профилей
profiles = api.get_browser_profiles(limit=10)
print(f"Найдено профилей: {profiles['total']}")

# Создание нового профиля
new_profile_data = {
    "name": "Тестовый профиль",
    "tags": ["test", "api"],
    "platform": "windows",
    "browserType": "anty",
    "mainWebsite": "google",
    "useragent": {
        "mode": "manual",
        "value": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    },
    "webrtc": {
        "mode": "altered"
    },
    "canvas": {
        "mode": "real"
    },
    "webgl": {
        "mode": "real"
    },
    "timezone": {
        "mode": "auto"
    },
    "geolocation": {
        "mode": "auto"
    },
    "cpu": {
        "mode": "real"
    },
    "memory": {
        "mode": "real"
    },
    "doNotTrack": 0
}

result = api.create_browser_profile(new_profile_data)
profile_id = result["browserProfileId"]
print(f"Создан новый профиль с ID: {profile_id}")

# Получение информации о профиле
profile_info = api.get_browser_profile(profile_id)
print(f"Информация о профиле: {profile_info}")

# Обновление профиля
update_data = {
    "name": "Обновленный профиль",
    "tags": ["updated", "test"],
    "notes": {
        "content": "Профиль обновлен через API",
        "color": "green",
        "icon": "info",
        "style": "text"
    }
}
api.update_browser_profile(profile_id, update_data)
print("Профиль обновлен")

# Получение и обновление cookies
cookies = api.get_cookies(profile_id)
print(f"Текущие cookies: {cookies}")

new_cookies = [
    {
        "domain": ".example.com",
        "name": "session",
        "value": "abc123",
        "path": "/",
        "expires": 1672531200,
        "httpOnly": True,
        "secure": True,
        "session": False
    }
]
api.update_cookies(profile_id, new_cookies)
print("Cookies обновлены")

# Удаление профиля
api.delete_browser_profile(profile_id)
print("Профиль удален")
```

### Пример 2: Асинхронное использование

```python
import asyncio
import aiohttp
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

async def main():
    api_token = "ваш_токен_api"  # Получите в панели Dolphin{anty}
    
    # Использование асинхронного клиента через контекстный менеджер
    async with AsyncDolphinAntyAPI(api_token=api_token) as api:
        # Получение списка профилей
        profiles = await api.async_get_browser_profiles(limit=10)
        print(f"Найдено профилей: {profiles['total']}")
        
        # Получение списка прокси
        proxies = await api.async_get_proxies()
        print(f"Найдено прокси: {proxies['total']}")
        
        # Создание нового профиля
        new_profile_data = {
            "name": "Асинхронный тест",
            "tags": ["async", "test"],
            "platform": "windows",
            "browserType": "anty",
            "mainWebsite": "google",
            "useragent": {
                "mode": "auto"
            },
            "webrtc": {
                "mode": "altered"
            }
        }
        
        result = await api.async_create_browser_profile(new_profile_data)
        profile_id = result["browserProfileId"]
        print(f"Создан новый профиль с ID: {profile_id}")
        
        # Получение информации о профиле
        profile_info = await api.async_get_browser_profile(profile_id)
        print(f"Информация о профиле: {profile_info}")
        
        # Удаление профиля
        await api.async_delete_browser_profile(profile_id)
        print("Профиль удален")

# Запуск асинхронной функции
asyncio.run(main())
```

### Пример 3: Полный пример с обработкой ошибок

```python
import requests
import json
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dolphin_api.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('dolphin_anty_api')

def main():
    try:
        # Инициализация клиента API
        api_token = "ваш_токен_api"  # Получите в панели Dolphin{anty}
        api = DolphinAntyAPI(api_token=api_token)
        
        # Получение списка профилей
        try:
            profiles = api.get_browser_profiles(limit=10)
            logger.info(f"Найдено профилей: {profiles['total']}")
            
            # Если есть профили, получим детали первого
            if profiles['total'] > 0:
                first_profile_id = profiles['data'][0]['id']
                try:
                    profile_details = api.get_browser_profile(first_profile_id)
                    logger.info(f"Детали профиля: {json.dumps(profile_details, indent=2)}")
                    
                    # Получим cookies профиля
                    try:
                        cookies = api.get_cookies(first_profile_id)
                        logger.info(f"Cookies профиля: {json.dumps(cookies, indent=2)}")
                    except DolphinAntyAPIError as e:
                        logger.error(f"Ошибка при получении cookies: {e.message}")
                    
                    # Получим закладки профиля
                    try:
                        bookmarks = api.get_bookmarks(first_profile_id)
                        logger.info(f"Закладки профиля: {json.dumps(bookmarks, indent=2)}")
                    except DolphinAntyAPIError as e:
                        logger.error(f"Ошибка при получении закладок: {e.message}")
                    
                except DolphinAntyAPIError as e:
                    logger.error(f"Ошибка при получении деталей профиля: {e.message}")
        except DolphinAntyAPIError as e:
            logger.error(f"Ошибка при получении списка профилей: {e.message}")
        
        # Создание нового профиля
        try:
            new_profile_data = {
                "name": "Полный тестовый профиль",
                "tags": ["test", "full", "example"],
                "platform": "windows",
                "browserType": "anty",
                "mainWebsite": "google",
                "useragent": {
                    "mode": "manual",
                    "value": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                },
                "webrtc": {
                    "mode": "altered"
                },
                "canvas": {
                    "mode": "real"
                },
                "webgl": {
                    "mode": "real"
                },
                "timezone": {
                    "mode": "auto"
                },
                "geolocation": {
                    "mode": "auto"
                },
                "cpu": {
                    "mode": "real"
                },
                "memory": {
                    "mode": "real"
                },
                "doNotTrack": 0,
                "notes": {
                    "content": "Тестовый профиль с полными настройками",
                    "color": "blue",
                    "icon": "info",
                    "style": "text"
                }
            }
            
            result = api.create_browser_profile(new_profile_data)
            profile_id = result["browserProfileId"]
            logger.info(f"Создан новый профиль с ID: {profile_id}")
            
            # Обновление профиля
            try:
                update_data = {
                    "name": "Обновленный полный профиль",
                    "tags": ["updated", "test", "full"],
                    "notes": {
                        "content": "Профиль обновлен через API с полной обработкой ошибок",
                        "color": "green",
                        "icon": "info",
                        "style": "text"
                    }
                }
                api.update_browser_profile(profile_id, update_data)
                logger.info("Профиль успешно обновлен")
                
                # Добавление закладок
                try:
                    bookmarks_data = [
                        {"name": "Google", "url": "https://www.google.com"},
                        {"name": "Dolphin Anty", "url": "https://anty.dolphin.ru.com"}
                    ]
                    api.update_bookmarks(profile_id, bookmarks_data)
                    logger.info("Закладки успешно добавлены")
                except DolphinAntyAPIError as e:
                    logger.error(f"Ошибка при добавлении закладок: {e.message}")
                
                # Обновление домашней страницы
                try:
                    homepages_data = [
                        {"name": "Google", "url": "https://www.google.com"},
                        {"name": "Dolphin", "url": "https://anty.dolphin.ru.com"}
                    ]
                    api.update_browser_profile_homepage(profile_id, homepages_data)
                    logger.info("Домашняя страница успешно обновлена")
                except DolphinAntyAPIError as e:
                    logger.error(f"Ошибка при обновлении домашней страницы: {e.message}")
                
                # Удаление профиля
                try:
                    api.delete_browser_profile(profile_id)
                    logger.info("Профиль успешно удален")
                except DolphinAntyAPIError as e:
                    logger.error(f"Ошибка при удалении профиля: {e.message}")
                
            except DolphinAntyAPIError as e:
                logger.error(f"Ошибка при обновлении профиля: {e.message}")
                
                # Удаление профиля даже в случае ошибки обновления
                try:
                    api.delete_browser_profile(profile_id)
                    logger.info("Профиль успешно удален после ошибки обновления")
                except DolphinAntyAPIError as e:
                    logger.error(f"Ошибка при удалении профиля после ошибки обновления: {e.message}")
            
        except DolphinAntyAPIError as e:
            logger.error(f"Ошибка при создании профиля: {e.message}")
        
        # Получение списка папок
        try:
            folders = api.get_folders()
            logger.info(f"Список папок: {json.dumps(folders, indent=2)}")
            
            # Создание новой папки
            try:
                folder_result = api.create_folder("Тестовая папка API", color="blue")
                folder_id = folder_result["id"]
                logger.info(f"Создана новая папка с ID: {folder_id}")
                
                # Обновление папки
                try:
                    api.update_folder(folder_id, name="Обновленная тестовая папка", color="green")
                    logger.info("Папка успешно обновлена")
                except DolphinAntyAPIError as e:
                    logger.error(f"Ошибка при обновлении папки: {e.message}")
                
                # Удаление папки
                try:
                    api.delete_folder(folder_id)
                    logger.info("Папка успешно удалена")
                except DolphinAntyAPIError as e:
                    logger.error(f"Ошибка при удалении папки: {e.message}")
                
            except DolphinAntyAPIError as e:
                logger.error(f"Ошибка при создании папки: {e.message}")
            
        except DolphinAntyAPIError as e:
            logger.error(f"Ошибка при получении списка папок: {e.message}")
        
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
```

## Обработка ошибок

Клиент API использует собственный класс исключений `DolphinAntyAPIError`, который содержит следующие атрибуты:

- `message`: Сообщение об ошибке
- `status_code`: HTTP-код ответа (если доступен)
- `response`: Объект ответа (если доступен)

Пример обработки ошибок:

```python
try:
    profiles = api.get_browser_profiles()
    # Обработка успешного ответа
except DolphinAntyAPIError as e:
    if e.status_code == 401:
        print("Ошибка авторизации. Проверьте токен API.")
    elif e.status_code == 429:
        print("Превышен лимит запросов. Попробуйте позже.")
    else:
        print(f"Ошибка API: {e.message}")
except Exception as e:
    print(f"Неожиданная ошибка: {str(e)}")
```

## Заключение

Эта документация предоставляет подробное описание всех методов Dolphin{anty} Remote API с примерами использования на Python. Для каждого метода указаны все необходимые заголовки (headers) и параметры тела запроса (body), а также приведены примеры использования.

Для получения дополнительной информации обратитесь к официальной документации API: https://documenter.getpostman.com/view/15402503/Tzm8Fb5f
