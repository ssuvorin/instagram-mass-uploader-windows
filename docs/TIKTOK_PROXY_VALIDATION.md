# TikTok Proxy Validation System

## Обзор

Реализована система валидации прокси для TikTok модуля с интеграцией в основное приложение. Система позволяет проверять валидность прокси, получать геоинформацию и заменять невалидные прокси.

## Архитектура

### TikTok Module (TiktokUploadCaptcha-master)

#### База данных
- **Таблица `accounts`** расширена полями:
  - `proxy_status` - статус прокси (unknown/valid/invalid/error/no_proxy)
  - `proxy_country` - страна прокси
  - `proxy_validation_date` - дата последней валидации

#### Новые модули
1. **`src/proxy_validator.py`** - основной класс валидации прокси
   - `ProxyValidator` - валидация HTTP/HTTPS и SOCKS5 прокси
   - Получение геоинформации через внешние API
   - Пакетная валидация

2. **`src/api/proxy_validation.py`** - API эндпоинты
   - `POST /proxy/validate` - валидация прокси
   - `GET /proxy/status/{client}` - статус прокси по клиенту
   - `GET /proxy/invalid-countries/{client}` - страны с невалидными прокси
   - `POST /proxy/replace-invalid` - замена невалидных прокси

### Root Project Integration

#### API Endpoints (uploader/urls.py)
- `api/tiktok/proxy/validate/` - прокси к валидации
- `api/tiktok/proxy/status/<client>/` - получение статуса
- `api/tiktok/proxy/invalid-countries/<client>/` - невалидные страны
- `api/tiktok/proxy/replace-invalid/` - замена прокси

#### UI Integration
- **Страница**: `/tiktok/videos/upload/`
- **Step 0** - добавлена кнопка "Validate Proxies"
- **Функциональность**:
  - Валидация прокси для выбранного клиента
  - Отображение результатов по статусам
  - Детальный показ стран с количеством невалидных прокси
  - Загрузка файла с новыми прокси
  - Валидация загруженных прокси
  - Проверка соответствия стран и количества
  - Автоматическая замена прокси у аккаунтов

## Использование

### 1. Валидация прокси
1. Перейти на страницу `/tiktok/videos/upload/`
2. Выбрать клиента в Step 0
3. Нажать кнопку "Validate Proxies"
4. Просмотреть результаты валидации

### 2. Просмотр невалидных стран
1. После валидации, если есть невалидные прокси
2. Нажать кнопку "Show Invalid Countries"
3. Просмотреть детальную таблицу с количеством невалидных прокси по странам

### 3. Загрузка и замена прокси
1. Нажать кнопку "Upload Replacement Proxies"
2. Выбрать файл с прокси (формат: `host:port:username:password` или `host:port`)
3. Указать целевые страны через запятую
4. Нажать "Upload and Replace"
5. Система:
   - Загрузит и валидирует прокси
   - Проверит соответствие стран
   - Покажет предупреждения если что-то не совпадает
   - Позволит продолжить или отменить
   - Автоматически заменит прокси у нужных аккаунтов

## API Endpoints

### Валидация прокси
```http
POST /proxy/validate
Content-Type: application/json

{
    "client": "client_name",
    "validate_all": false,
    "account_usernames": ["username1", "username2"]
}
```

### Получение статуса
```http
GET /proxy/status/{client}
```

### Невалидные страны
```http
GET /proxy/invalid-countries/{client}
```

### Замена прокси
```http
POST /proxy/replace-invalid
Content-Type: application/json

{
    "client": "client_name",
    "invalid_proxy_countries": ["US", "GB"],
    "replacement_count": 1
}
```

### Загрузка и валидация прокси
```http
POST /proxy/upload-and-validate
Content-Type: multipart/form-data

file: proxy_file.txt
client: client_name
target_countries: US,GB,DE
```

### Замена с загруженными прокси
```http
POST /proxy/replace-with-uploaded
Content-Type: application/json

{
    "client": "client_name",
    "target_countries": ["US", "GB"],
    "validated_proxies": [
        {
            "proxy": {"host": "1.2.3.4", "port": 8080},
            "geo_info": {"country": "US", "city": "New York"}
        }
    ]
}
```

## Статусы прокси

- `unknown` - не проверялся
- `valid` - валидный, работает
- `invalid` - невалидный, не работает
- `error` - ошибка при проверке
- `no_proxy` - прокси не настроен

## Геоинформация

Система получает следующую информацию о прокси:
- Страна (country)
- Город (city)
- Регион (region)
- Внешний IP (external_ip)
- Часовой пояс (timezone)

## Технические детали

### Валидация прокси
1. **HTTP/HTTPS прокси**: проверка через HTTPS endpoints
2. **SOCKS5 прокси**: проверка через SOCKS5 сокеты
3. **Геоинформация**: получение через ip-api.com, ipapi.co, ipinfo.io

### Безопасность
- IP whitelist для API доступа
- CSRF защита для всех эндпоинтов
- Таймауты для предотвращения зависания

### Производительность
- Пакетная валидация с задержками
- Кэширование результатов
- Асинхронная обработка

## Логирование

Все операции логируются в систему логирования TikTok модуля:
- Результаты валидации
- Ошибки подключения
- Обновления статусов
- Замены прокси

## Расширения

Система готова для расширения:
- Дополнительные гео API
- Настраиваемые таймауты
- Массовая замена прокси
- Интеграция с внешними прокси провайдерами
