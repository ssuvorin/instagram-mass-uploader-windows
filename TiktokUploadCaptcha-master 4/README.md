# Модуль автоматизации TikTok с интеграцией Dolphin Anty

Этот модуль предоставляет инструмент на Python для автоматизации взаимодействия с TikTok, с акцентом на аутентификацию аккаунтов, загрузку видео и управление профилями с использованием Dolphin Anty (браузер с функцией анти-детекта для работы с множеством аккаунтов). Он использует Playwright для автоматизации браузера, обрабатывает коды подтверждения по электронной почте, решает CAPTCHA и управляет профилями браузера через API Dolphin Anty. Модуль предназначен для программного управления несколькими аккаунтами TikTok, например, для массовой загрузки видео с описаниями в течение нескольких циклов, избегая обнаружения благодаря изолированным профилям браузера.

Скрипт `main.py` является точкой входа, координируя процесс: загрузка конфигураций, запуск профилей Dolphin, аутентификация аккаунтов, загрузка видео и отправка уведомлений в Telegram по завершении.

Скрипт `prepare_accounts.py` — это утилита для подготовки, которая создает профили Dolphin, настраивает прокси, копирует видео и заголовки и генерирует основной файл `config.json` для автоматической загрузки в несколько циклов.

**Примечание:** Этот модуль автоматизирует взаимодействие с браузером и может нарушать условия использования TikTok. Используйте его ответственно и на свой страх и риск. Требуются внешние сервисы, такие как Dolphin Anty, провайдеры электронной почты (например, Rambler), решатели CAPTCHA и Telegram для уведомлений.

## Возможности

- **Подготовка аккаунтов**: Создание профилей Dolphin с рандомизированными отпечатками (UA, WebGL, CPU/RAM, разрешение), настройка прокси и создание конфигураций из входных файлов.
- **Интеграция с Dolphin Anty**: Управление профилями браузера для предотвращения обнаружения, включая запуск/остановку профилей, аутентификацию через API и импорт cookies с случайных сайтов.
- **Аутентификация**: Вход в аккаунты TikTok с использованием логина/пароля, обработка кодов подтверждения по email, CAPTCHA и сброс паролей.
- **Загрузка видео**: Загрузка видео в TikTok с настраиваемыми описаниями (включая хэштеги; упоминания частично реализованы).
- **Интеграция с email**: Получение кодов подтверждения из сервисов электронной почты, таких как Rambler или Notletters через IMAP.
- **Решение CAPTCHA**: Автоматическое решение CAPTCHA с использованием стороннего сервиса (например, через `tiktok_captcha_solver`).
- **Массовое выполнение**: Обработка нескольких аккаунтов и видео в течение настраиваемых циклов с логированием времени и производительности, а также проверкой уникальности видео/заголовков.
- **Утилиты**: Удаление видео, заголовков и профилей; отправка сообщений в Telegram для обновления статуса.
- **Локаторы**: Предопределённые селекторы XPath и CSS для элементов интерфейса TikTok для надёжной автоматизации.
- **Основной скрипт**: Автоматизирует весь процесс, включая обработку ошибок и метрики производительности (например, скорость публикации).
- **Скрипт подготовки**: Подготавливает папки, прокси, аккаунты, видео, заголовки и генерирует конфигурацию для загрузки в несколько циклов.

## Зависимости

- Python 3.12+ (совместим с последними версиями).
- Внешние библиотеки (установка через pip):
  - `playwright`: Для автоматизации браузера.
  - `playwright-stealth`: Для предотвращения обнаружения браузера.
  - `tiktok_captcha_solver`: Для обработки CAPTCHA (требуется API-ключ).
  - `python-dotenv`: Для загрузки переменных окружения.
  - `requests`: Для взаимодействия с API Dolphin.
- Стандартные библиотеки: `email`, `imaplib`, `re`, `json`, `os`, `shutil`, `random`, `time`, `http.client`, `urllib`.
- Менеджер профилей браузера: **Dolphin Anty** (обязателен для изоляции профилей; установите и запустите приложение локально на порту 3001).
- Переменные окружения (в `.env` или системе):
  - `TOKEN`: Токен API Dolphin Anty.
  - `TIKTOK_SOLVER_API_KEY`: API-ключ для решателя CAPTCHA.

Установка зависимостей:
```
pip install playwright requests python-dotenv tiktok-captcha-solver playwright-stealth
```
Запустите `playwright install` для загрузки бинарных файлов браузера.

## Установка

1. Склонируйте или загрузите файлы модуля в директорию (например, `src/`).
2. Убедитесь, что структура директорий соответствует:
   ```
   src/
   │   ├── dolphin/
   │   │   ├── __init__.py
   │   │   ├── dolphin.py
   │   │   └── profile.py
   │   ├── tiktok/
   │   │   ├── __init__.py
   │   │   ├── auth.py
   │   │   ├── browser.py
   │   │   ├── captcha.py
   │   │   ├── email.py
   │   │   ├── locators.py
   │   │   ├── upload.py
   │   │   ├── utils.py
   │   │   └── video.py
   │   ├── telegram.py  # Реализуйте для отправки сообщений
   │   ├── logger.py   # Реализуйте для логирования
   │   └── sites.txt   # Список сайтов (по одному на строку) для импорта cookies
   ├── accounts/
   │   ├── accounts.txt  # Входные данные: username:password:email_username:email_password (по одному на строку)
   │   ├── config.json   # Генерируется: Основной конфиг для загрузок
   │   ├── titles.txt    # Генерируется: Список заголовков (по одному на строку)
   │   ├── accounts_data/  # Генерируется: Подпапки для профилей с config.json
   │   └── videos/         # Генерируется: Видео для загрузки
   ├── prepare_accounts/
   │   ├── prepare_accounts.py  # Скрипт подготовки
   │   ├── videos/              # Исходные видео (.mp4 и т.д.)
   │   └── titles/              # Исходный titles.txt (по одному заголовку на строку)
   ├── proxy/
   │   └── proxies.txt  # Входные данные: host:port@login:password (по одному на строку)
   └── main.py             # Точка входа для автоматизации
   ```
3. Настройте Dolphin Anty: Установите приложение, создайте профили (или позвольте скрипту их сгенерировать), получите API-токен, укажите в `.env` как `TOKEN`, запустите приложение на localhost:3001.
4. Подготовьте входные файлы:
   - `accounts/accounts.txt`: Аккаунты TikTok, формат: `username:password:email_username:email_password` (по умолчанию ограничено первыми 20 строками).
   - `proxy/proxies.txt`: Прокси, формат: `host:port@login:password`.
   - `prepare_accounts/videos/`: Папка с уникальными видео (не менее `количество_аккаунтов * UPLOAD_CYCLES`).
   - `prepare_accounts/titles/titles.txt`: По одному заголовку/описани на строку (достаточно для всех видео).
   - `src/sites.txt`: Список сайтов (по одному на строку) для импорта случайных cookies (40-50 на профиль).
5. Настройте глобальные переменные в `prepare_accounts.py` (или через окружение): `MUSIC_NAME`, `LOCATION`, `MENTIONS`, `VIDEOS_PER_ACCOUNT=1`, `UPLOAD_CYCLES=15`.
6. Запустите подготовку: `python prepare_accounts/prepare_accounts.py`, чтобы сгенерировать папки, профили и конфиги. Скрипт удаляет существующие `accounts/accounts_data` и `accounts/videos`, так что сделайте резервную копию.

## Использование

### Подготовка с prepare_accounts.py

Сначала запустите этот скрипт для подготовки всего необходимого для `main.py`:
```bash
python prepare_accounts/prepare_accounts.py
```
- Создаёт профили Dolphin (до 20 из accounts.txt) с рандомизированными отпечатками (по умолчанию platform='windows').
- Добавляет прокси в Dolphin.
- Копирует видео и заголовки в `accounts/`.
- Генерирует `accounts/config.json` с `UPLOAD_CYCLES * num_accounts` записями, каждая из которых назначает уникальное видео и заголовок аккаунту.
- Импортирует cookies с случайных сайтов для реализма профилей.
- Отправляет сообщение в Telegram по завершении.

Настройка:
- Измените `platform` в вызовах `set_profile`, если нужно (например, 'macos').
- Настройте `UPLOAD_CYCLES` для количества циклов загрузки (обеспечивает уникальность видео/заголовков).

### Основные классы и функции

- **Dolphin (dolphin/dolphin.py)**: Управляет профилями Dolphin и аутентификацией через API.
  ```python
  from src.dolphin.dolphin import Dolphin

  dolphin = Dolphin()  # Аутентификация через TOKEN
  profiles = dolphin.get_profiles()  # Список объектов Profile
  profile = dolphin.get_profile_by_name("profile_name")
  dolphin.start_profiles()  # Запускает все профили
  dolphin.stop_profiles()  # Останавливает все профили
  ```

- **Profile (dolphin/profile.py)**: Управляет отдельными профилями.
  ```python
  from src.dolphin.profile import Profile

  profile = Profile(id=123, name="profile_name")
  port, endpoint = profile.start()  # Запускает, возвращает порт/эндпоинт CDP
  profile.stop()  # Останавливает
  ```

- **Email (tiktok/email.py)**: Получает коды подтверждения.
  ```python
  from src.tiktok.getCode import Email

  email = Email("email@example.com", "pass")
  code = email.get_code()
  ```

- **Auth (tiktok/auth.py)**: Аутентификация через профили Dolphin.
  ```python
  from playwright.sync_api import sync_playwright
  from src.tiktok.auth import Auth
  from src.tiktok.getCode import Email
  from src.dolphin.profile import Profile

  with sync_playwright() as pw:
      email = Email("email_login", "email_pass")
      profile = Profile(123, "name")
      auth = Auth("tiktok_user", "tiktok_pass", email, profile, pw)
      page = auth.authenticate()
      auth.stop_browser()
  ```

- **Uploader (tiktok/upload.py)**: Загружает видео.
  ```python
  from src.tiktok.auth import Auth
  from src.tiktok.upload import Uploader
  from src.tiktok.video import Video

  uploader = Uploader(auth)
  videos = [Video("vid1", "/path/vid.mp4", "Desc #tag")]
  uploader.upload_videos(videos)
  ```

- **Video (tiktok/video.py)**: Класс данных для видео.
  ```python
  video = Video("example", "/path/file.mp4", "Desc #tag", "Music")
  ```

- **Утилиты (tiktok/utils.py)**: Очистка.
  ```python
  from src.tiktok.utils import delete_video, delete_title, delete_profile
  ```

- **Основной скрипт (main.py)**: Полная автоматизация.
  ```python
  from playwright.sync_api import sync_playwright

  if __name__ == '__main__':
      with sync_playwright() as pw:
          main(pw)  # Загружает по config.json, логирует метрики
  ```
  - Проходит по `config.json['accounts']`, загружает одно видео на запись (аккаунт + видео + заголовок), спит 30 секунд между загрузками.
  - Вычисляет общее время и скорость публикации (видео/мин).
  - Отправляет Telegram-сообщения о начале/конце с метриками.

### Пример рабочего процесса

1. Подготовьте входные файлы: accounts.txt, proxies.txt, videos/, titles.txt, sites.txt.
2. Запустите `prepare_accounts.py` для генерации конфигураций и профилей.
3. Запустите `main.py`: аутентификация, загрузка видео в течение циклов, уведомления через Telegram.

## Конфигурация

- **API Dolphin**: `TOKEN` в .env. Профили через `https://dolphin-anty-api.com`.
- **Конфигурации профилей**: Генерируются в `accounts/accounts_data/<index>/config.json` с логином, паролем, данными email.
- **Основной конфиг (генерируется)**: `accounts/config.json`. Структура:
  ```json
  {
    "accounts": [
      {"name": "0", "video": "vid1.mp4", "title": "Title1"},
      ...  // Повторяется для UPLOAD_CYCLES * num_accounts
    ],
    "location": "Moscow",
    "mentions": [],
    "music_name": "Даня Милохин"
  }
  ```
- **Входные данные**:
  - `accounts/accounts.txt`: Строки с аккаунтами.
  - `proxy/proxies.txt`: Строки с прокси.
  - `prepare_accounts/videos/`: Исходные уникальные видео.
  - `prepare_accounts/titles/titles.txt`: Исходные заголовки.
  - `src/sites.txt`: Сайты для импорта cookies.
- **Глобальные переменные в prepare_accounts.py**: `MUSIC_NAME`, `LOCATION`, `MENTIONS` (массив), `VIDEOS_PER_ACCOUNT=1`, `UPLOAD_CYCLES=15`.
- **Домены email**: В `tiktok/email.py`.
- **Таймауты/задержки**: Жёстко закодированы; настройте при необходимости.
- **Telegram/Logger**: Реализуйте `src.telegram.send_message` и `src.logger`.

## Ограничения и TODO

- Выбор музыки не реализован (используется `music_name` в конфиге, но заглушка в загрузке).
- Упоминания частично реализованы (TODO).
- Обработка ошибок базовая.
- Нет функций планирования/аналитики.
- Уклонение от обнаружения через отпечатки/stealth, но не гарантировано.
- Сброс пароля перетасовывает символы.
- Удаление профилей закомментировано.
- Предполагается запуск Dolphin на localhost:3001.
- Подготовка удаляет существующие данные; делайте резервные копии.

## Логирование

Используется `src.logger` для info/error/debug. Реализуйте через модуль `logging`.

## Лицензия

Предоставляется как есть, без конкретной лицензии. Рассмотрите добавление MIT для продакшна. Соблюдайте условия TikTok и Dolphin Anty.