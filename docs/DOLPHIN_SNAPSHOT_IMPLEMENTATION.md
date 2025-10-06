# Dolphin Profile Snapshot Implementation

## Обзор

Реализовано автоматическое сохранение снимков профилей Dolphin в базу данных для возможности воссоздания профилей 1:1.

## Что было сделано

### 1. Создан сервис для работы со снимками профилей
**Файл:** `uploader/services/dolphin_snapshot.py`

Содержит функции:
- `save_dolphin_snapshot(account, profile_id, response)` - Сохраняет снимок профиля из ответа API
- `get_profile_data_from_api(dolphin_api, profile_id)` - Получает данные профиля из Dolphin API
- `save_existing_profile_snapshot(account, dolphin_api)` - Сохраняет снимок существующего профиля

### 2. Обновлен импорт аккаунтов
**Файл:** `uploader/views_mod/accounts.py`

Добавлено сохранение снимков в функциях:
- `import_accounts()` - строки 959-964
- `import_accounts_ua_cookies()` - строки 1544-1549

При создании профиля Dolphin теперь автоматически сохраняется полный снимок в таблицу `DolphinProfileSnapshot`.

### 3. Обновлен бот
**Файл:** `bot/src/instagram_uploader/dolphin_anty.py`
- Изменен метод `create_profile_for_account()` для возврата кортежа `(profile_id, response)` вместо только `profile_id`

**Файл:** `bot/src/instagram_uploader/browser_dolphin.py`
- Обновлен для работы с новой сигнатурой метода
- Сохраняет `dolphin_profile_response` для последующего использования

**Файл:** `bot/run_bot_playwright.py`
- Добавлено сохранение снимка профиля в БД при создании (строки 364-383)
- Работает если есть `account_id` в данных аккаунта

### 4. Добавлен UI для сохранения снимков
**Файл:** `uploader/views_mod/misc.py`
- Создана функция `save_dolphin_profile_snapshot()` (строки 1042-1083)
- Позволяет получить и сохранить снимок существующего профиля

**Файл:** `uploader/urls.py`
- Добавлен URL `accounts/<int:account_id>/save-profile-snapshot/`

**Файл:** `uploader/templates/uploader/account_detail.html`
- Добавлена кнопка "Save Snapshot" на странице аккаунта (строки 124-129)

## Структура DolphinProfileSnapshot

```python
class DolphinProfileSnapshot(models.Model):
    account = models.OneToOneField(InstagramAccount, on_delete=models.CASCADE)
    profile_id = models.CharField(max_length=100, db_index=True)
    payload_json = models.JSONField()      # Полный payload отправленный в Dolphin API
    response_json = models.JSONField()     # Полный ответ от Dolphin API
    meta_json = models.JSONField()         # Метаданные (geoip, public_ip, strict_webrtc)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## Где сохраняются снимки

1. **При импорте аккаунтов** - автоматически при создании профилей
2. **При работе бота** - автоматически если есть `account_id` в данных
3. **Вручную** - кнопка "Save Snapshot" на странице аккаунта

## Использование

### Автоматическое сохранение
Снимки сохраняются автоматически при:
- Импорте аккаунтов с созданием профилей
- Создании аккаунта через форму с профилем
- Работе бота (если передан account_id)

### Ручное сохранение
1. Перейти на страницу аккаунта
2. Нажать кнопку "Save Snapshot"
3. Система получит данные из Dolphin API и сохранит в БД

## Восстановление профиля 1:1

Для воссоздания профиля используйте данные из:
- `payload_json` - все параметры создания профиля
- `response_json` - полный ответ с fingerprint
- `meta_json` - дополнительные метаданные

## Примечания

- Снимок привязан к аккаунту через `OneToOneField`
- При повторном сохранении старый снимок обновляется
- `payload_json` может быть пустым для существующих профилей (fetched from API)
- Все данные хранятся в JSON для гибкости и полноты

