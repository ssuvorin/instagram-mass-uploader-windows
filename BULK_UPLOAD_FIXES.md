# Исправление проблем с Bulk Upload

## Основные проблемы и их решения

### 1. Ошибка "cannot access local variable 'auth' where it is not associated with a value"

**Проблема**: Переменная `auth` не была инициализирована в некоторых сценариях.

**Решение**: ✅ Исправлено в `uploader/async_impl/instagrapi.py`
- Добавлена инициализация `auth = None` перед использованием
- Создается объект `auth` даже при успешном восстановлении сессии

### 2. RuntimeWarning: coroutine was never awaited

**Проблема**: Корутины не ожидались должным образом.

**Решение**: ✅ Исправлено в `uploader/async_bulk_tasks.py`
- Все корутины правильно передаются в `asyncio.gather()`
- Добавлена проверка на существование `auth` объекта

### 3. DisallowedHost ошибки

**Проблема**: Django отклоняет запросы от неразрешенных хостов.

**Решение**: ✅ Исправлено в `instagram_uploader/settings.py`
- Добавлены проблемные хосты: `example.com`, `ipv4-internet.yandex.net`
- Добавлена поддержка wildcard хостов

### 4. TimeoutError в Django сервере

**Проблема**: Сервер не отвечает в течение установленного времени.

**Решение**: ✅ Исправлено в `instagram_uploader/settings.py`
- Увеличены таймауты сервера
- Добавлены настройки для стабильности соединений
- Увеличен лимит полей для bulk операций

### 5. Улучшенная обработка ошибок

**Решение**: ✅ Улучшено в `uploader/async_impl/instagrapi.py`
- Добавлена детальная диагностика ошибок
- Улучшена проверка на `None` для объекта `auth`
- Добавлены более информативные сообщения об ошибках

## Скрипт диагностики

Создан скрипт `fix_bulk_upload_issues.py` для автоматической диагностики и исправления проблем:

```bash
python fix_bulk_upload_issues.py
```

Скрипт выполняет:
- Проверку активных задач
- Сброс зависших аккаунтов
- Очистку старых логов
- Проверку настроек окружения

## Рекомендации по предотвращению проблем

1. **Мониторинг**: Регулярно проверяйте логи на наличие ошибок
2. **Ограничения**: Не запускайте слишком много параллельных аккаунтов
3. **Прокси**: Убедитесь, что прокси работают корректно
4. **Dolphin Anty**: Проверьте доступность Dolphin API
5. **Ресурсы**: Мониторьте использование памяти и CPU

## Переменные окружения

Убедитесь, что настроены следующие переменные:

```bash
DOLPHIN_API_TOKEN=your_token
DOLPHIN_API_HOST=http://localhost:3001/v1.0
ALLOWED_HOSTS=0.0.0.0,localhost,127.0.0.1,*,example.com,ipv4-internet.yandex.net
SERVER_TIMEOUT=300
REQUEST_TIMEOUT=60
```

## Мониторинг

Для мониторинга состояния системы используйте:

```bash
# Проверка активных задач
python manage.py shell -c "from uploader.models import BulkUploadTask; print(BulkUploadTask.objects.filter(status='RUNNING').count())"

# Проверка зависших аккаунтов  
python manage.py shell -c "from uploader.models import BulkUploadAccount; print(BulkUploadAccount.objects.filter(status='RUNNING').count())"
```
