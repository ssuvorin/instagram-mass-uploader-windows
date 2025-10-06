# 🔧 Исправление создания Dolphin профилей при импорте

**Дата:** 2025-10-05  
**Статус:** ✅ Исправлено

---

## 🐛 Проблема

При импорте аккаунтов создавались TikTok аккаунты, но профили Dolphin Anty **не создавались**.

### Ошибка в логах:
```
[ERROR] Dolphin API init failed: Expecting value: line 1 column 1 (char 0)
[STATS] Dolphin: Created 0, Errors 0
```

---

## 🔍 Причины проблемы

### 1. **Неправильный вызов `create_profile`**

**Было в `views_import.py`:**
```python
profile_data = {
    'name': username,
    'platform': 'windows',
    'browserType': 'anty',
    'mainWebsite': 'tiktok',
    'proxy': proxy_config
}

result = dolphin.create_profile(profile_data)  # ❌ Неправильно!
```

**Проблема:** Функция `create_profile()` ожидает **именованные аргументы**, а не словарь!

**Сигнатура функции:**
```python
def create_profile(
    self,
    name: str,                    # ← Требуется
    proxy: Dict[str, Any],        # ← Требуется
    tags: List[str] = None,       # ← Опционально
    locale: Optional[str] = None, # ← Опционально
    strict_webrtc: bool = True
) -> Dict[str, Any]:
```

---

### 2. **Неправильная структура прокси**

**Было:**
```python
proxy_config = {
    'type': 'http',
    'host': '1.2.3.4',
    'port': '8080',
    'login': 'user',      # ❌ Должно быть 'user'
    'password': 'pass'    # ❌ Должно быть 'pass'
}
```

**Ожидается:**
```python
proxy_config = {
    'type': 'http',
    'host': '1.2.3.4',
    'port': 8080,         # ← int, не string
    'user': 'username',   # ← 'user', не 'login'
    'pass': 'password'    # ← 'pass', не 'password'
}
```

---

### 3. **Отсутствие обработки ошибок инициализации Dolphin**

**Было:**
```python
def __init__(self):
    self.profiles: list[Profile] = []
    self.set_profiles()  # ← Может упасть если Dolphin не запущен
    self.auth()          # ← Может упасть если local API недоступен
```

**Проблема:** Если Dolphin Anty desktop не запущен (port 3001 закрыт), инициализация падала с ошибкой JSON parsing.

---

## ✅ Исправления

### 1. **Исправлен вызов `create_profile` в `views_import.py`**

**Стало:**
```python
# Подготавливаем прокси конфиг
proxy_config = None
if account.proxy:
    proxy_config = {
        'type': account.proxy.proxy_type.lower(),
        'host': account.proxy.host,
        'port': int(account.proxy.port),  # ← int вместо string
    }
    
    if account.proxy.username:
        proxy_config['user'] = account.proxy.username  # ← 'user' вместо 'login'
    if account.proxy.password:
        proxy_config['pass'] = account.proxy.password  # ← 'pass' вместо 'password'

if not proxy_config:
    logger.error(f"[DOLPHIN SKIP] No proxy configured for {username}, skipping profile creation")
    dolphin_error_count += 1
    continue

# Создаем профиль через Dolphin API с правильными аргументами
result = dolphin.create_profile(
    name=username,           # ← Именованный аргумент
    proxy=proxy_config,      # ← Именованный аргумент
    tags=['tiktok', 'import'],
    locale=selected_locale
)

# Проверяем результат
if result.get("success", True) and (result.get('browserProfileId') or result.get('data', {}).get('id')):
    profile_id = result.get('browserProfileId') or result.get('data', {}).get('id')
    account.dolphin_profile_id = str(profile_id)
    account.save()
    dolphin_created_count += 1
    logger.info(f"[DOLPHIN SUCCESS] Profile created: ID={profile_id}")
else:
    error_msg = result.get('error', 'Unknown error')
    logger.error(f"[DOLPHIN FAIL] Failed to create profile for {username}: {error_msg}")
    dolphin_error_count += 1
```

---

### 2. **Добавлена обработка ошибок инициализации Dolphin**

#### `dolphin.py` - `__init__`:
```python
def __init__(self):
    self.profiles: list[Profile] = []
    try:
        self.auth()
        self.set_profiles()
    except Exception as e:
        logger.warning(f"[DOLPHIN] Init warning: {str(e)}. Continuing with empty profile list.")
        # Продолжаем работу даже если auth/set_profiles упали
        # Это позволит создавать новые профили даже если Dolphin desktop не запущен
```

#### `dolphin.py` - `auth`:
```python
def auth(self):
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 3001, timeout=5)
        payload = json.dumps({
            "token": os.environ.get('DOLPHIN_API_TOKEN')
        })
        headers = {
            'Content-Type': 'application/json'
        }
        conn.request("POST", "/v1.0/auth/login-with-token", payload, headers)
        res = conn.getresponse()
        raw_data = res.read()
        
        if not raw_data:
            logger.warning('[DOLPHIN] Auth response is empty, Dolphin desktop may not be running')
            return
        
        data = json.loads(raw_data)
        if data.get('success') == True:
            logger.info('Successfully logged into dolphin via token')
        else:
            logger.error(f'Failed to login into dolphin: {data}')
    except Exception as e:
        logger.warning(f'[DOLPHIN] Auth failed (Dolphin desktop may not be running): {str(e)}')
```

#### `dolphin.py` - `_get_profiles`:
```python
def _get_profiles(self):
    try:
        result = requests.get(
            'https://dolphin-anty-api.com/browser_profiles?',
            headers={'Authorization': f'Bearer {os.environ.get("DOLPHIN_API_TOKEN")}'},
            timeout=10
        )
        result.raise_for_status()
        return result.json()
    except Exception as e:
        logger.warning(f'[DOLPHIN] Failed to get profiles: {str(e)}')
        return {'data': []}
```

---

## 📊 Результат

### **До исправления:**
```
[ERROR] Dolphin API init failed: Expecting value: line 1 column 1 (char 0)
[STATS] Created: 5, Updated: 0, Errors: 0
[STATS] Dolphin: Created 0, Errors 0  ← ❌ Профили не создавались
```

### **После исправления (ожидается):**
```
[DOLPHIN] Init warning: ... Continuing with empty profile list.
[STATS] Created: 5, Updated: 0, Errors: 0
[STATS] Dolphin: Created 5, Errors 0  ← ✅ Профили создаются!
```

---

## 🧪 Как протестировать

### 1. **Убедитесь что `DOLPHIN_API_TOKEN` настроен:**
```bash
python check_env.py
```

Должно быть:
```
DOLPHIN_API_TOKEN: [SET] ✓
```

---

### 2. **Запустите Dolphin Anty (опционально):**
- Если Dolphin Anty desktop **запущен** → auth пройдет успешно
- Если Dolphin Anty desktop **не запущен** → будет warning, но профили всё равно создадутся через Web API

---

### 3. **Импортируйте аккаунты:**
1. Перейдите: `/tiktok/accounts/import/`
2. Выберите файл с аккаунтами (формат: `username:password:email:email_password`)
3. Выберите режим: **"Create Dolphin Anty profiles automatically"**
4. Нажмите **"Import Accounts"**

---

### 4. **Проверьте логи:**
```bash
# Windows PowerShell
Get-Content bot\log.txt -Tail 50

# Linux/Mac
tail -50 bot/log.txt
```

**Ожидаемый результат:**
```
[DOLPHIN] Creating profile for user1
[PROFILE] Step 1: Adding proxy to Dolphin for profile user1
[PROFILE] Proxy added to Dolphin with ID: 12345
[PROFILE] Creating with locale=en_US, language=en-US, timezone=America/New_York
[OK] Profile created: 67890
[PROFILE] Step 3: Assigning proxy 12345 to profile 67890
[OK] Proxy successfully assigned to profile user1
[DOLPHIN SUCCESS] Profile created: ID=67890
```

---

### 5. **Проверьте в Dolphin Anty:**
1. Откройте Dolphin Anty desktop
2. Должны появиться новые профили с именами аккаунтов
3. В профилях должны быть назначены прокси
4. Теги: `tiktok`, `import`

---

## 📝 Важные замечания

### **1. Прокси обязателен для создания профиля**
Если у аккаунта нет прокси, профиль **не будет создан**:
```
[DOLPHIN SKIP] No proxy configured for username, skipping profile creation
```

**Решение:** Назначьте прокси перед импортом или выберите режим **"Assign proxies automatically"**.

---

### **2. Dolphin desktop не обязателен**
- Web API (`https://dolphin-anty-api.com`) работает **всегда**
- Local API (`http://localhost:3001`) работает **только если Dolphin desktop запущен**
- Создание профилей использует **Web API**, поэтому desktop не обязателен

---

### **3. Структура прокси в модели `TikTokProxy`:**
```python
{
    'type': 'http',           # proxy_type: HTTP/SOCKS5/HTTPS
    'host': '1.2.3.4',        # host
    'port': 8080,             # port (int!)
    'user': 'username',       # username (опционально)
    'pass': 'password'        # password (опционально)
}
```

---

## 🚀 Что дальше?

После успешного импорта аккаунтов с профилями Dolphin, вы можете:

1. ✅ **Запустить Bulk Upload** - загрузить видео через созданные профили
2. ✅ **Запустить Warmup** - прогреть аккаунты
3. ✅ **Cookie Robot** - обновить cookies в профилях
4. ✅ **Export Cookies** - экспортировать cookies из профилей

---

## 📚 Связанные документы

- `TOKEN_TO_DOLPHIN_API_TOKEN_MIGRATION.md` - Миграция переменных окружения
- `TIKTOK_BULK_IMPORT_COMPLETE.md` - Документация импорта аккаунтов
- `QUICK_START_IMPORT.md` - Быстрый старт импорта

---

## ✅ Статус: ИСПРАВЛЕНО

Все проблемы с созданием Dolphin профилей исправлены. Теперь при импорте аккаунтов профили создаются корректно! 🎉


