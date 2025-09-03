# SSL Fix для Instagram Uploader

## Проблема
При использовании прокси с Instagram API возникают SSL ошибки:
```
SSLError(1, '[SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:1010)')
```

## Решение
Добавлен модуль `ssl_fix.py`, который автоматически отключает проверку SSL сертификатов для совместимости с прокси.

## Что исправлено

### 1. Глобальные SSL настройки
- Отключена проверка SSL сертификатов
- Отключены SSL предупреждения
- Установлен неверифицированный SSL контекст

### 2. Файлы с исправлениями
- `ssl_fix.py` - основной модуль исправлений
- `uploader/async_bulk_tasks.py` - асинхронные задачи
- `uploader/bulk_tasks_playwright.py` - Playwright задачи
- `instgrapi_func/services/client_factory.py` - Instagram клиент
- `manage.py` - Django управление

### 3. Автоматическое применение
SSL исправления применяются автоматически при импорте модулей.

## Использование

### Автоматическое (рекомендуется)
SSL исправления применяются автоматически при запуске приложения.

### Ручное применение
```python
import ssl_fix
ssl_fix.apply_ssl_fix()
```

### Для requests сессий
```python
import ssl_fix
import requests

session = requests.Session()
ssl_fix.configure_requests_session(session)
```

## Безопасность
⚠️ **Внимание**: Отключение SSL проверки снижает безопасность соединений. Используйте только с доверенными прокси.

## Альтернативные решения

### 1. Использование HTTPS прокси
Попробуйте использовать прокси с поддержкой HTTPS:
```
https://username:password@proxy-host:port
```

### 2. Обновление прокси
Убедитесь, что прокси поддерживает современные SSL протоколы.

### 3. Проверка прокси
Проверьте работоспособность прокси:
```bash
curl --proxy http://username:password@proxy-host:port https://www.instagram.com
```

## Логирование
При успешном применении SSL исправлений вы увидите:
```
[SSL_FIX] SSL verification disabled globally for proxy compatibility
```

## Поддержка
Если проблемы с SSL продолжаются, проверьте:
1. Формат прокси (должен быть `http://user:pass@host:port`)
2. Работоспособность прокси
3. Версию Python (рекомендуется 3.8+)
4. Версию urllib3 и requests
