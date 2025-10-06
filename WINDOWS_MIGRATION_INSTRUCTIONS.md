# Инструкция по добавлению системы аналитики в Windows версию

## Проблема
Windows версия не имеет миграций 0031-0040, что вызывает ошибку `NodeNotFoundError`.

## Решение
Скопировать все файлы аналитики из macOS версии в Windows версию.

## Файлы для копирования

### 1. Миграции (uploader/migrations/)
```
0033_clientanalytics.py
0034_alter_clientanalytics_instagram_reels_views_and_more.py
0035_clientanalytics_hashtag.py
0036_alter_clientanalytics_unique_together.py
0037_hashtaganalytics_client_hashtaganalytics_created_by_and_more.py
0038_alter_hashtaganalytics_growth_rate_and_more.py
0039_add_advanced_account_metrics.py
0040_remove_period_fields.py
```

### 2. Формы и views (uploader/)
```
analytics_forms.py
views_mod/analytics_collector.py
views_mod/analytics.py
```

### 3. Шаблоны (uploader/templates/uploader/)
```
analytics/ (вся папка)
```

### 4. Обновленные файлы cabinet/
```
services.py
views.py
templates/cabinet/agency_dashboard.html
templates/cabinet/client_dashboard.html
urls.py
```

## Команды для применения

После копирования файлов выполните:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

## Проверка

После применения миграций проверьте:
1. Доступность `/analytics/add/` - форма сбора аналитики
2. Доступность `/cabinet/` - дашборды с новой аналитикой
3. Кнопка "Excel" в дашбордах - экспорт данных

## Примечание

Все зависимости миграций исправлены для работы с последней миграцией Windows версии (0028_proxy_external_ip).
