# Руководство по созданию TikTok аккаунтов

## 📝 Создание нового аккаунта

### Через веб-интерфейс

1. **Перейдите на страницу создания**
   - Dashboard → Accounts → "New Account"
   - Или прямая ссылка: `/tiktok/accounts/create/`

2. **Заполните форму**

   **Обязательные поля:**
   - `Username` - имя пользователя TikTok (без @)
   - `Password` - пароль от аккаунта

   **Рекомендуемые поля:**
   - `Email` - email для получения кодов подтверждения
   - `Email Password` - пароль от email
   - `Proxy` - выберите прокси из списка
   - `Locale` - язык и регион (en_US, ru_RU, es_ES и т.д.)

   **Опциональные поля:**
   - `Phone Number` - номер телефона (формат: +1234567890)
   - `Client` - привязка к клиенту (для агентств)
   - `Notes` - дополнительные заметки

3. **Настройки Dolphin профиля**
   - ✅ Отметьте чекбокс "Create Dolphin Anty profile automatically"
   - Профиль будет создан автоматически при сохранении
   - **Требуется:** выбранный прокси

4. **Сохраните аккаунт**
   - Нажмите "Create Account"
   - Система создаст аккаунт и (опционально) Dolphin профиль
   - Вы будете перенаправлены на страницу деталей аккаунта

### Программное создание

```python
from tiktok_uploader.models import TikTokAccount, TikTokProxy
from tiktok_uploader.bot_integration.services import create_dolphin_profile_for_account

# Выбрать прокси
proxy = TikTokProxy.objects.filter(is_active=True).first()

# Создать аккаунт
account = TikTokAccount.objects.create(
    username='my_tiktok_user',
    password='secure_password',
    email='my_email@example.com',
    email_password='email_password',
    phone_number='+1234567890',
    proxy=proxy,
    current_proxy=proxy,
    locale='en_US',
    status='ACTIVE',
    notes='Created via API'
)

# Создать Dolphin профиль
result = create_dolphin_profile_for_account(account)

if result['success']:
    print(f"✅ Account and profile created! Profile ID: {result['profile_id']}")
else:
    print(f"❌ Account created, but Dolphin profile failed: {result['error']}")
```

## 🔍 Валидация

### Username
- Только буквы, цифры, точки и подчеркивания
- Без пробелов и специальных символов
- Должен быть уникальным

### Email
- Валидный email формат
- Рекомендуется использовать реальный email для получения кодов

### Phone Number
- Формат: +[код страны][номер]
- Пример: +12345678901
- Только цифры, пробелы, тире и скобки

### Proxy
- Должен быть активным (`is_active=True`)
- Обязателен для создания Dolphin профиля

## ⚡ Что происходит при создании

1. **Создание записи в БД**
   - Создается запись `TikTokAccount`
   - Статус устанавливается в `ACTIVE`
   - Proxy копируется в `current_proxy`

2. **Создание Dolphin профиля** (если выбрано)
   - Генерируется уникальный fingerprint
   - Настраивается WebGL, Canvas, User-Agent
   - Устанавливается timezone по прокси
   - Настраивается локализация
   - Привязывается прокси

3. **Сохранение снимка профиля**
   - Создается `DolphinProfileSnapshot`
   - Сохраняется payload для восстановления
   - Сохраняется metadata (GeoIP, timezone)

4. **Уведомления**
   - Success сообщения в интерфейсе
   - Логирование в `logs/tiktok_bot.log`
   - Telegram уведомления (если настроены)

## 🎯 Лучшие практики

### 1. Используйте уникальные прокси
```python
# Плохо: один прокси на все аккаунты
proxy = TikTokProxy.objects.first()

# Хорошо: разные прокси для разных аккаунтов
proxies = TikTokProxy.objects.filter(is_active=True, accounts__isnull=True)
proxy = proxies.first()
```

### 2. Заполняйте email и email_password
Это критично для получения кодов подтверждения при аутентификации:
```python
account = TikTokAccount.objects.create(
    username='user123',
    password='pass123',
    email='user123@example.com',  # ✅ Обязательно
    email_password='email_pass',   # ✅ Обязательно
    ...
)
```

### 3. Правильно выбирайте locale
Locale должен соответствовать региону прокси:
- USA прокси → `en_US`
- Russia прокси → `ru_RU`
- Spain прокси → `es_ES`
- Brazil прокси → `pt_BR`

### 4. Создавайте Dolphin профили сразу
Лучше создать профиль при создании аккаунта, чем потом:
```python
# ✅ Хорошо: создаем сразу
create_dolphin = True

# ❌ Плохо: создаем потом отдельно
create_dolphin = False
# ... потом отдельный запрос на создание профиля
```

## 🐛 Troubleshooting

### Ошибка: "Username already exists"
- Этот username уже используется
- Выберите другое имя пользователя

### Ошибка: "Cannot create Dolphin profile: No proxy"
- Прокси не выбран
- Выберите активный прокси из списка

### Ошибка: "Failed to create Dolphin profile"
- Проверьте, что Dolphin Anty запущен на `localhost:3001`
- Проверьте токен `TOKEN` в `.env`
- Проверьте логи: `logs/tiktok_bot.log`

### Профиль создан, но не работает аутентификация
- Проверьте правильность username и password
- Убедитесь, что email и email_password указаны
- Проверьте работу прокси
- Проверьте, что аккаунт не заблокирован TikTok

## 📊 Примеры использования

### Создание одного аккаунта
```python
from tiktok_uploader.models import TikTokAccount, TikTokProxy

proxy = TikTokProxy.objects.get(id=1)

account = TikTokAccount.objects.create(
    username='testuser1',
    password='SecurePass123!',
    email='testuser1@gmail.com',
    email_password='GmailPass123!',
    proxy=proxy,
    current_proxy=proxy,
    locale='en_US',
    status='ACTIVE'
)

from tiktok_uploader.bot_integration.services import create_dolphin_profile_for_account
result = create_dolphin_profile_for_account(account)
print(f"Profile created: {result}")
```

### Массовое создание аккаунтов
```python
from tiktok_uploader.models import TikTokAccount, TikTokProxy
from tiktok_uploader.bot_integration.services import create_dolphin_profile_for_account

accounts_data = [
    {
        'username': 'user1',
        'password': 'pass1',
        'email': 'user1@example.com',
        'email_password': 'email_pass1'
    },
    {
        'username': 'user2',
        'password': 'pass2',
        'email': 'user2@example.com',
        'email_password': 'email_pass2'
    },
    # ... еще аккаунты
]

proxies = TikTokProxy.objects.filter(is_active=True)

for i, data in enumerate(accounts_data):
    proxy = proxies[i % len(proxies)]  # Распределяем прокси
    
    account = TikTokAccount.objects.create(
        username=data['username'],
        password=data['password'],
        email=data['email'],
        email_password=data['email_password'],
        proxy=proxy,
        current_proxy=proxy,
        locale='en_US',
        status='ACTIVE'
    )
    
    # Создаем Dolphin профиль
    result = create_dolphin_profile_for_account(account)
    
    if result['success']:
        print(f"✅ {account.username}: Profile {result['profile_id']}")
    else:
        print(f"❌ {account.username}: {result['error']}")
```

### Создание через форму в Django Admin
```python
# В Django Admin можно создать аккаунт через интерфейс
# 1. Перейдите в Admin → TikTok Accounts → Add TikTok Account
# 2. Заполните форму
# 3. Сохраните
# 4. Затем создайте Dolphin профиль через действие "Create Dolphin Profile"
```

## 🔗 Связанные страницы

- [Список аккаунтов](../accounts/) - просмотр всех аккаунтов
- [Импорт аккаунтов](../accounts/import/) - массовый импорт из файла
- [Создание прокси](../proxies/create/) - создание нового прокси
- [Dashboard](../) - главная страница

## 📖 Дополнительная информация

- Документация по интеграции бота: `TIKTOK_BOT_INTEGRATION.md`
- Руководство пользователя: `tiktok_uploader/USER_JOURNEY_GUIDE.md`
- Модели данных: `tiktok_uploader/models.py`

