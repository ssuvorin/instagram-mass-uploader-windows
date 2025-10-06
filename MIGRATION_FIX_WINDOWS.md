# Решение проблемы с миграциями на Windows

## Проблема
При попытке применить миграции на Windows возникает ошибка:
```
django.db.utils.ProgrammingError: column "updated_at" of relation "uploader_hashtaganalytics" already exists
```

## Причина
Колонка `updated_at` уже существует в базе данных на Windows, но миграция пытается ее добавить снова.

## Решение

### Вариант 1: Применить безопасную миграцию (рекомендуется)
```bash
# Перейдите в директорию проекта
cd C:\Users\Admin\instagram-mass-uploader-windows

# Активируйте виртуальное окружение
venv\Scripts\activate

# Примените миграции
python manage.py migrate
```

Если все еще возникает ошибка, используйте Вариант 2.

### Вариант 2: Пропустить проблемную миграцию
```bash
# Отметьте миграцию как примененную без выполнения
python manage.py migrate uploader 0044_add_updated_at_to_hashtaganalytics --fake

# Затем примените остальные миграции
python manage.py migrate
```

### Вариант 3: Сброс миграций (только если нет важных данных)
```bash
# Удалите все таблицы (ОСТОРОЖНО: это удалит все данные!)
python manage.py flush

# Примените все миграции заново
python manage.py migrate
```

## Проверка
После применения миграций проверьте:
```bash
python manage.py check
python manage.py showmigrations uploader
```

Все миграции должны быть отмечены как [X] (примененные).

## Что было исправлено
- Создана безопасная миграция `0045_safe_add_missing_columns`
- Миграция проверяет существование колонок перед их добавлением
- Удалена проблемная миграция `0044_add_updated_at_to_hashtaganalytics`
- Теперь система работает корректно на всех платформах
