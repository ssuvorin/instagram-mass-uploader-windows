# БЫСТРОЕ РЕШЕНИЕ ПРОБЛЕМЫ С МИГРАЦИЯМИ

## Выполните эти команды по порядку:

```bash
# 1. Перейдите в директорию проекта
cd C:\Users\Admin\instagram-mass-uploader-windows

# 2. Активируйте виртуальное окружение
venv\Scripts\activate

# 3. Получите исправления
git pull

# 4. Примените миграции
python manage.py migrate

# 5. Запустите сервер
python manage.py runserver 0.0.0.0:8000
```

## Если все еще не работает:

```bash
# Принудительно отметьте все миграции как примененные
python manage.py migrate uploader --fake

# Затем примените только нужные изменения
python manage.py migrate uploader 0045_safe_add_missing_columns
```

## Готово! Больше никаких ошибок с миграциями.
