# 🎯 Полный путь пользователя: От создания аккаунтов до загрузки видео

## Обзор системы

TikTok Uploader - это автоматизированная система для массовой загрузки видео на TikTok через множество аккаунтов с использованием браузерной автоматизации (Playwright) и антидетект браузера (Dolphin Anty).

---

## 📋 Этап 1: Создание TikTok аккаунтов

### 1.1. Действия пользователя (UI)

**Путь:** Dashboard → Accounts → Create Account

**URL:** `http://127.0.0.1:8000/tiktok/accounts/create/`

**Пользователь заполняет форму:**
- Username: `testuser123`
- Password: `SecurePass123!`
- Email: `testuser@example.com` (опционально)
- Phone: `+1234567890` (опционально)
- Proxy: Выбирает из списка
- Locale: `en_US`
- Create Dolphin Profile: ✓ (чекбокс)

**Нажимает:** "Create Account"

### 1.2. Что происходит на сервере

#### Django View (Backend)
```python
# Файл: tiktok_uploader/views.py
# Функция: create_account(request)

1. POST запрос приходит на view
2. Валидация данных:
   - Проверка уникальности username
   - Валидация email формата
   - Валидация phone формата
   - Проверка существования proxy_id

3. Создание записи в БД:
   account = TikTokAccount.objects.create(
       username='testuser123',
       password='SecurePass123!',  # Хранится в зашифрованном виде
       email='testuser@example.com',
       proxy=proxy_object,
       status='ACTIVE',
       locale='en_US',
       created_at=timezone.now()
   )
```

#### Dolphin Anty Integration (Антидетект браузер)
```python
# Если чекбокс "Create Dolphin Profile" отмечен:

4. Обращение к Dolphin Anty API:
   
   import requests
   
   dolphin_api_url = "http://localhost:3001/v1.0/browser_profiles"
   
   # Создание профиля
   profile_data = {
       "name": f"TikTok_{account.username}",
       "platform": "windows",
       "browserType": "anty",
       "mainWebsite": "tiktok.com",
       "useragent": {
           "mode": "manual",
           "value": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
       },
       "webrtc": {
           "mode": "altered",
           "ipAddress": proxy.external_ip
       },
       "timezone": {
           "mode": "auto",
           "value": account.locale
       },
       "geolocation": {
           "mode": "auto",
           "latitude": proxy.latitude,
           "longitude": proxy.longitude
       },
       "proxy": {
           "type": proxy.proxy_type.lower(),  # http/socks5
           "host": proxy.host,
           "port": proxy.port,
           "username": proxy.username,
           "password": proxy.password
       },
       "canvas": {"mode": "noise"},
       "webgl": {"mode": "noise"},
       "fonts": {"mode": "mask"}
   }
   
   response = requests.post(dolphin_api_url, json=profile_data)
   dolphin_profile = response.json()
   
   # Сохраняем ID профиля
   account.dolphin_profile_id = dolphin_profile['browserProfileId']
   account.save()
```

#### Результат
```
✅ Аккаунт создан в БД (таблица tiktok_uploader_tiktokaccount)
✅ Dolphin профиль создан (сохранен ID в поле dolphin_profile_id)
✅ Прокси привязан к аккаунту
✅ Redirect на страницу деталей аккаунта
```

**Структура БД после создания:**
```sql
INSERT INTO tiktok_uploader_tiktokaccount (
    id=1,
    username='testuser123',
    password='encrypted_password',
    email='testuser@example.com',
    proxy_id=5,
    dolphin_profile_id='abc123xyz',
    status='ACTIVE',
    locale='en_US',
    created_at='2025-10-03 15:30:00'
)
```

---

## 📋 Этап 2: Прогрев аккаунтов (Warmup)

### 2.1. Действия пользователя (UI)

**Путь:** Dashboard → Warmup → New Warmup

**URL:** `http://127.0.0.1:8000/tiktok/warmup/create/`

**Пользователь выбирает:**
- Аккаунты: ✓ testuser123, ✓ testuser456, ✓ testuser789 (3 аккаунта)
- Concurrency: 2 (параллельно 2 аккаунта)
- Min Delay: 30 сек
- Max Delay: 60 сек

**Action Ranges:**
- Feed Scroll: min=5, max=10
- Likes: min=3, max=7
- Watch Videos: min=5, max=15
- Follows: min=0, max=2
- Comments: min=0, max=1

**Нажимает:** "Create Warmup Task"

### 2.2. Что происходит на сервере

#### Django View
```python
# Файл: tiktok_uploader/views_warmup.py
# Функция: warmup_task_create(request)

1. POST запрос с данными формы
2. Валидация:
   - Минимум 1 аккаунт выбран
   - delay_min <= delay_max
   - Все range min <= max
   - concurrency 1-4

3. Создание WarmupTask:
   task = WarmupTask.objects.create(
       name=f"Warmup {timezone.now().strftime('%Y-%m-%d %H:%M')}",
       status='PENDING',
       delay_min_sec=30,
       delay_max_sec=60,
       concurrency=2,
       feed_scroll_min_count=5,
       feed_scroll_max_count=10,
       like_min_count=3,
       like_max_count=7,
       watch_video_min_count=5,
       watch_video_max_count=15,
       follow_min_count=0,
       follow_max_count=2,
       comment_min_count=0,
       comment_max_count=1,
       created_at=timezone.now()
   )

4. Привязка аккаунтов к задаче:
   for account_id in selected_account_ids:
       account = TikTokAccount.objects.get(id=account_id)
       WarmupTaskAccount.objects.create(
           task=task,
           account=account,
           proxy=account.proxy,  # Копируем текущий прокси
           status='PENDING'
       )

5. Redirect на warmup_task_detail
```

**Структура БД:**
```sql
-- Таблица задачи
INSERT INTO tiktok_uploader_warmuptask (id=1, name='Warmup 2025-10-03', status='PENDING', ...)

-- Связь задачи с аккаунтами
INSERT INTO tiktok_uploader_warmuptaskaccount (task_id=1, account_id=1, status='PENDING')
INSERT INTO tiktok_uploader_warmuptaskaccount (task_id=1, account_id=2, status='PENDING')
INSERT INTO tiktok_uploader_warmuptaskaccount (task_id=1, account_id=3, status='PENDING')
```

### 2.3. Запуск задачи прогрева

**Пользователь:** Кликает "Start" на странице задачи

**URL:** `POST /tiktok/warmup/1/start/`

#### Что происходит на сервере

```python
# Файл: tiktok_uploader/views_warmup.py
# Функция: warmup_task_start(request, task_id)

1. Проверка статуса задачи (должен быть PENDING)
2. Изменение статуса на RUNNING:
   task.status = 'RUNNING'
   task.started_at = timezone.now()
   task.save()

3. Запуск асинхронного worker (Celery):
   from tiktok_uploader.tasks import execute_warmup_task
   execute_warmup_task.delay(task_id)
```

#### Celery Worker (Фоновый процесс)
```python
# Файл: tiktok_uploader/tasks.py
# Функция: execute_warmup_task(task_id)

@shared_task
def execute_warmup_task(task_id):
    task = WarmupTask.objects.get(id=task_id)
    accounts = task.accounts.filter(status='PENDING')
    
    # Параллельная обработка (concurrency=2)
    with ThreadPoolExecutor(max_workers=task.concurrency) as executor:
        futures = []
        
        for task_account in accounts:
            future = executor.submit(
                warmup_single_account,
                task_account.id,
                task.settings
            )
            futures.append(future)
        
        # Ожидание завершения
        wait(futures)
    
    # Финализация
    task.status = 'COMPLETED'
    task.completed_at = timezone.now()
    task.save()
```

#### Прогрев одного аккаунта (Playwright + Dolphin)
```python
# Функция: warmup_single_account(task_account_id, settings)

def warmup_single_account(task_account_id, settings):
    task_account = WarmupTaskAccount.objects.get(id=task_account_id)
    account = task_account.account
    
    # 1. Обновление статуса
    task_account.status = 'RUNNING'
    task_account.started_at = timezone.now()
    task_account.save()
    
    try:
        # 2. Запуск Dolphin профиля
        dolphin_api = f"http://localhost:3001/v1.0/browser_profiles/{account.dolphin_profile_id}/start"
        response = requests.get(dolphin_api)
        automation_port = response.json()['automation']['port']  # WebSocket порт
        
        # 3. Подключение Playwright к Dolphin браузеру
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Подключение к запущенному Dolphin профилю
            browser = p.chromium.connect_over_cdp(
                f"ws://127.0.0.1:{automation_port}"
            )
            context = browser.contexts[0]
            page = context.pages[0]
            
            # 4. Логин в TikTok (если нет cookies)
            page.goto("https://www.tiktok.com/login")
            
            # Проверка: залогинены ли мы?
            if page.url.startswith("https://www.tiktok.com/login"):
                # Логин через username/password
                page.fill('input[name="username"]', account.username)
                page.fill('input[type="password"]', account.password)
                page.click('button[type="submit"]')
                page.wait_for_url("https://www.tiktok.com/foryou", timeout=30000)
            
            # 5. WARMUP ACTIONS - Имитация реального пользователя
            
            # a) Feed Scroll (прокрутка ленты)
            scroll_count = random.randint(
                settings['feed_scroll_min_count'],
                settings['feed_scroll_max_count']
            )
            
            for i in range(scroll_count):
                # Скролл вниз
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                
                # Случайная задержка (human-like)
                delay = random.uniform(
                    settings['delay_min_sec'],
                    settings['delay_max_sec']
                )
                time.sleep(delay)
                
                # Логирование
                task_account.log += f"[{timezone.now()}] Scrolled feed {i+1}/{scroll_count}\n"
                task_account.save()
            
            # b) Watch Videos (просмотр видео)
            watch_count = random.randint(
                settings['watch_video_min_count'],
                settings['watch_video_max_count']
            )
            
            videos = page.locator('[data-e2e="recommend-list-item-container"]').all()
            
            for i in range(min(watch_count, len(videos))):
                video = videos[i]
                video.scroll_into_view_if_needed()
                
                # Клик на видео
                video.click()
                
                # Смотрим случайное время (5-30 сек)
                watch_duration = random.uniform(5, 30)
                time.sleep(watch_duration)
                
                task_account.log += f"[{timezone.now()}] Watched video {i+1}/{watch_count} for {watch_duration:.1f}s\n"
                task_account.save()
            
            # c) Likes (лайки)
            like_count = random.randint(
                settings['like_min_count'],
                settings['like_max_count']
            )
            
            for i in range(like_count):
                # Находим кнопку лайка
                like_button = page.locator('[data-e2e="like-icon"]').first
                like_button.click()
                
                time.sleep(random.uniform(2, 5))
                
                task_account.log += f"[{timezone.now()}] Liked video {i+1}/{like_count}\n"
                task_account.save()
            
            # d) Follows (подписки)
            follow_count = random.randint(
                settings['follow_min_count'],
                settings['follow_max_count']
            )
            
            for i in range(follow_count):
                follow_button = page.locator('[data-e2e="follow-button"]').first
                
                if follow_button.is_visible():
                    follow_button.click()
                    time.sleep(random.uniform(3, 8))
                    
                    task_account.log += f"[{timezone.now()}] Followed user {i+1}/{follow_count}\n"
                    task_account.save()
            
            # e) Comments (комментарии) - опционально
            comment_count = random.randint(
                settings['comment_min_count'],
                settings['comment_max_count']
            )
            
            if comment_count > 0:
                comments_pool = [
                    "Nice! 🔥",
                    "Amazing 😍",
                    "Love it! ❤️",
                    "Great content 👍",
                    "Cool! 😎"
                ]
                
                for i in range(comment_count):
                    comment_input = page.locator('[data-e2e="comment-input"]').first
                    
                    if comment_input.is_visible():
                        random_comment = random.choice(comments_pool)
                        comment_input.fill(random_comment)
                        
                        post_button = page.locator('[data-e2e="comment-post"]').first
                        post_button.click()
                        
                        time.sleep(random.uniform(5, 10))
                        
                        task_account.log += f"[{timezone.now()}] Posted comment: {random_comment}\n"
                        task_account.save()
            
            # 6. Сохранение cookies после warmup
            cookies = context.cookies()
            task_account.cookies_json = json.dumps(cookies)
            
            # 7. Закрытие браузера
            browser.close()
        
        # 8. Остановка Dolphin профиля
        stop_api = f"http://localhost:3001/v1.0/browser_profiles/{account.dolphin_profile_id}/stop"
        requests.get(stop_api)
        
        # 9. Успешное завершение
        task_account.status = 'COMPLETED'
        task_account.completed_at = timezone.now()
        task_account.log += f"[{timezone.now()}] ✅ Warmup completed successfully!\n"
        task_account.save()
        
        # Обновление аккаунта
        account.last_warmed = timezone.now()
        account.last_used = timezone.now()
        account.save()
        
    except Exception as e:
        # Обработка ошибок
        task_account.status = 'FAILED'
        task_account.log += f"[{timezone.now()}] ❌ Error: {str(e)}\n"
        task_account.save()
```

**Результат прогрева:**
```
✅ Аккаунт "прогрет" - имитирована активность реального пользователя
✅ TikTok видит аккаунт как "живой" (не бот)
✅ Снижается риск блокировки при загрузке
✅ Cookies сохранены для будущего использования
✅ Логи записаны для отслеживания действий
```

---

## 📋 Этап 3: Массовая загрузка видео (Bulk Upload)

### 3.1. Действия пользователя (UI)

**Путь:** Dashboard → Bulk Upload → New Task

**URL:** `http://127.0.0.1:8000/tiktok/bulk-upload/create/`

**Многошаговая форма:**

**Step 1: Basic Information**
- Task Name: "Daily Content Upload"
- Description: "Upload today's content to all accounts"

**Step 2: Select Accounts**
- ✓ testuser123
- ✓ testuser456
- ✓ testuser789

**Step 3: Upload Videos**
- Drag & Drop 5 видео файлов:
  - video1.mp4 (15 MB)
  - video2.mp4 (12 MB)
  - video3.mp4 (18 MB)
  - video4.mp4 (10 MB)
  - video5.mp4 (14 MB)

**Step 4: Configure Settings**
- Min Delay: 300 сек (5 мин)
- Max Delay: 600 сек (10 мин)
- Concurrency: 2

**TikTok Options:**
- Caption Template: "Check out this amazing content! 🔥 #{hashtag1} #{hashtag2}"
- Hashtags: #viral, #foryou, #trending
- Privacy: Public
- Allow Comments: Yes
- Allow Duet: Yes
- Allow Stitch: Yes

**Distribution:**
- Videos per Account: 2 (rotate)

**Нажимает:** "Create Task"

### 3.2. Что происходит на сервере

#### Django View - Создание задачи
```python
# Файл: tiktok_uploader/views_mod/views_bulk.py
# Функция: create_bulk_upload(request)

1. POST запрос с FormData (включая файлы)

2. Сохранение загруженных файлов:
   import os
   from django.conf import settings
   
   upload_dir = os.path.join(settings.MEDIA_ROOT, 'bulk_uploads', str(task.id))
   os.makedirs(upload_dir, exist_ok=True)
   
   for video_file in request.FILES.getlist('videos'):
       # Сохранение файла на диск
       file_path = os.path.join(upload_dir, video_file.name)
       
       with open(file_path, 'wb+') as destination:
           for chunk in video_file.chunks():
               destination.write(chunk)
       
       # Создание записи в БД
       BulkVideo.objects.create(
           task=task,
           original_filename=video_file.name,
           file_path=file_path,
           file_size=video_file.size,
           uploaded=False
       )

3. Создание BulkUploadTask:
   task = BulkUploadTask.objects.create(
       name="Daily Content Upload",
       description="Upload today's content",
       status='PENDING',
       delay_min_sec=300,
       delay_max_sec=600,
       concurrency=2,
       caption_template="Check out this amazing content! 🔥 #{hashtag1} #{hashtag2}",
       hashtags="#viral #foryou #trending",
       privacy='PUBLIC',
       allow_comments=True,
       allow_duet=True,
       allow_stitch=True,
       videos_per_account=2,
       created_at=timezone.now()
   )

4. Привязка аккаунтов:
   for account_id in selected_account_ids:
       BulkUploadAccount.objects.create(
           task=task,
           account=account,
           assigned_videos=2,  # videos_per_account
           uploaded_videos=0,
           status='PENDING'
       )

5. Распределение видео по аккаунтам (rotation):
   videos = task.videos.all()
   accounts = task.bulk_accounts.all()
   
   # Rotate: video1→acc1, video2→acc2, video3→acc3, video4→acc1, video5→acc2
   for i, video in enumerate(videos):
       account_index = i % len(accounts)
       account = accounts[account_index]
       
       VideoCaption.objects.create(
           video=video,
           account=account.account,
           caption=generate_caption(task.caption_template, task.hashtags),
           privacy=task.privacy
       )
```

**Структура БД:**
```sql
-- Задача
INSERT INTO bulkuploadtask (id=1, name='Daily Content Upload', status='PENDING', ...)

-- Видео
INSERT INTO bulkvideo (id=1, task_id=1, file_path='/media/bulk_uploads/1/video1.mp4', uploaded=False)
INSERT INTO bulkvideo (id=2, task_id=1, file_path='/media/bulk_uploads/1/video2.mp4', uploaded=False)
INSERT INTO bulkvideo (id=3, task_id=1, file_path='/media/bulk_uploads/1/video3.mp4', uploaded=False)
...

-- Аккаунты в задаче
INSERT INTO bulkuploadaccount (task_id=1, account_id=1, assigned_videos=2, uploaded_videos=0)
INSERT INTO bulkuploadaccount (task_id=1, account_id=2, assigned_videos=2, uploaded_videos=0)
INSERT INTO bulkuploadaccount (task_id=1, account_id=3, assigned_videos=2, uploaded_videos=0)

-- Описания для видео
INSERT INTO videocaption (video_id=1, account_id=1, caption='Check out this amazing content! 🔥 #viral #foryou')
INSERT INTO videocaption (video_id=2, account_id=2, caption='Check out this amazing content! 🔥 #viral #trending')
...
```

### 3.3. Запуск загрузки

**Пользователь:** Кликает "Start" на странице задачи

**URL:** `POST /tiktok/bulk-upload/1/start/`

#### Celery Worker - Массовая загрузка
```python
# Файл: tiktok_uploader/tasks.py
# Функция: execute_bulk_upload(task_id)

@shared_task
def execute_bulk_upload(task_id):
    task = BulkUploadTask.objects.get(id=task_id)
    
    # Изменение статуса
    task.status = 'RUNNING'
    task.started_at = timezone.now()
    task.save()
    
    # Получение аккаунтов
    bulk_accounts = task.bulk_accounts.filter(status='PENDING')
    
    # Параллельная обработка (concurrency=2)
    with ThreadPoolExecutor(max_workers=task.concurrency) as executor:
        futures = []
        
        for bulk_account in bulk_accounts:
            future = executor.submit(
                upload_videos_for_account,
                bulk_account.id,
                task.settings
            )
            futures.append(future)
        
        wait(futures)
    
    # Завершение
    task.status = 'COMPLETED'
    task.completed_at = timezone.now()
    task.save()
```

#### Загрузка видео для одного аккаунта
```python
# Функция: upload_videos_for_account(bulk_account_id, settings)

def upload_videos_for_account(bulk_account_id, settings):
    bulk_account = BulkUploadAccount.objects.get(id=bulk_account_id)
    account = bulk_account.account
    
    # Получение видео для этого аккаунта
    video_captions = VideoCaption.objects.filter(
        account=account,
        video__task=bulk_account.task,
        video__uploaded=False
    )
    
    # Обновление статуса
    bulk_account.status = 'RUNNING'
    bulk_account.started_at = timezone.now()
    bulk_account.save()
    
    try:
        # 1. Запуск Dolphin профиля
        dolphin_api = f"http://localhost:3001/v1.0/browser_profiles/{account.dolphin_profile_id}/start"
        response = requests.get(dolphin_api)
        automation_port = response.json()['automation']['port']
        
        # 2. Подключение Playwright
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"ws://127.0.0.1:{automation_port}")
            context = browser.contexts[0]
            page = context.pages[0]
            
            # 3. Переход на TikTok upload page
            page.goto("https://www.tiktok.com/upload")
            
            # Проверка логина
            if "login" in page.url:
                # Автологин через сохраненные cookies
                if account.cookies_json:
                    cookies = json.loads(account.cookies_json)
                    context.add_cookies(cookies)
                    page.goto("https://www.tiktok.com/upload")
            
            # 4. ЗАГРУЗКА КАЖДОГО ВИДЕО
            for video_caption in video_captions:
                video = video_caption.video
                
                # a) Загрузка файла
                file_input = page.locator('input[type="file"]')
                file_input.set_input_files(video.file_path)
                
                # Ожидание обработки видео
                page.wait_for_selector('[data-e2e="upload-preview"]', timeout=60000)
                
                # b) Заполнение описания
                caption_input = page.locator('[data-e2e="video-caption"]')
                caption_input.fill(video_caption.caption)
                
                # c) Настройка privacy
                if settings['privacy'] == 'PUBLIC':
                    page.click('[data-e2e="privacy-public"]')
                elif settings['privacy'] == 'FRIENDS':
                    page.click('[data-e2e="privacy-friends"]')
                elif settings['privacy'] == 'PRIVATE':
                    page.click('[data-e2e="privacy-private"]')
                
                # d) Настройка разрешений
                if not settings['allow_comments']:
                    page.click('[data-e2e="allow-comments-toggle"]')
                
                if not settings['allow_duet']:
                    page.click('[data-e2e="allow-duet-toggle"]')
                
                if not settings['allow_stitch']:
                    page.click('[data-e2e="allow-stitch-toggle"]')
                
                # e) Публикация
                publish_button = page.locator('[data-e2e="publish-button"]')
                publish_button.click()
                
                # Ожидание успешной публикации
                page.wait_for_url("https://www.tiktok.com/@*", timeout=120000)
                
                # f) Извлечение URL опубликованного видео
                video_url = page.url
                
                # g) Обновление БД
                video.uploaded = True
                video.uploaded_at = timezone.now()
                video.tiktok_url = video_url
                video.save()
                
                bulk_account.uploaded_videos += 1
                bulk_account.log += f"[{timezone.now()}] ✅ Uploaded: {video.original_filename} → {video_url}\n"
                bulk_account.save()
                
                # h) Задержка между загрузками (anti-detection)
                delay = random.uniform(
                    settings['delay_min_sec'],
                    settings['delay_max_sec']
                )
                
                bulk_account.log += f"[{timezone.now()}] ⏳ Waiting {delay:.0f}s before next upload...\n"
                bulk_account.save()
                
                time.sleep(delay)
            
            # 5. Сохранение обновленных cookies
            cookies = context.cookies()
            account.cookies_json = json.dumps(cookies)
            account.save()
            
            # 6. Закрытие браузера
            browser.close()
        
        # 7. Остановка Dolphin профиля
        stop_api = f"http://localhost:3001/v1.0/browser_profiles/{account.dolphin_profile_id}/stop"
        requests.get(stop_api)
        
        # 8. Успешное завершение
        bulk_account.status = 'COMPLETED'
        bulk_account.completed_at = timezone.now()
        bulk_account.save()
        
        account.last_used = timezone.now()
        account.save()
        
    except Exception as e:
        bulk_account.status = 'FAILED'
        bulk_account.log += f"[{timezone.now()}] ❌ Error: {str(e)}\n"
        bulk_account.save()
```

**Результат загрузки:**
```
✅ 5 видео загружено на TikTok
✅ Распределены по 3 аккаунтам (rotation)
✅ У каждого видео свой caption с хештегами
✅ Настройки privacy применены
✅ URL опубликованных видео сохранены
✅ Логи детализируют каждый шаг
✅ Delays между загрузками соблюдены (anti-detection)
```

---

## 🔄 Полный цикл работы системы

### Диаграмма процесса

```
USER ACTION                  SERVER PROCESS                    EXTERNAL SERVICES
─────────────────────────────────────────────────────────────────────────────────

1. Create Account
   │
   ├──> POST /accounts/create/
   │       │
   │       ├──> Django View validates
   │       ├──> Creates TikTokAccount in DB
   │       ├──> Dolphin API call ────────────> Dolphin Anty Server
   │       │                                   │
   │       │                                   ├──> Creates browser profile
   │       │                                   └──> Returns profile_id
   │       └──> Saves profile_id
   │
   └──> ✅ Account created

2. Warmup Account
   │
   ├──> POST /warmup/create/
   │       │
   │       ├──> Creates WarmupTask
   │       ├──> Links accounts to task
   │       └──> Status: PENDING
   │
   ├──> POST /warmup/1/start/
   │       │
   │       ├──> Status: RUNNING
   │       └──> Celery task.delay()
   │               │
   │               └──> Background Worker
   │                       │
   │                       ├──> For each account:
   │                       │    │
   │                       │    ├──> Dolphin API start ───────> Dolphin starts browser
   │                       │    │
   │                       │    ├──> Playwright connect ──────> Chrome with profile
   │                       │    │
   │                       │    ├──> TikTok login ────────────> TikTok.com
   │                       │    │
   │                       │    ├──> Human-like actions:
   │                       │    │    • Scroll feed
   │                       │    │    • Watch videos
   │                       │    │    • Like content
   │                       │    │    • Follow users
   │                       │    │    • Post comments
   │                       │    │
   │                       │    ├──> Save cookies
   │                       │    │
   │                       │    └──> Dolphin API stop ────────> Browser closed
   │                       │
   │                       └──> Status: COMPLETED
   │
   └──> ✅ Account warmed up

3. Bulk Upload Videos
   │
   ├──> POST /bulk-upload/create/
   │       │
   │       ├──> Upload video files to /media/
   │       ├──> Creates BulkUploadTask
   │       ├──> Creates BulkVideo records
   │       ├──> Links accounts to task
   │       ├──> Distributes videos (rotation)
   │       └──> Status: PENDING
   │
   ├──> POST /bulk-upload/1/start/
   │       │
   │       ├──> Status: RUNNING
   │       └──> Celery task.delay()
   │               │
   │               └──> Background Worker (concurrency=2)
   │                       │
   │                       ├──> Thread 1: Account testuser123
   │                       │    │
   │                       │    ├──> Dolphin API start ───────> Browser 1
   │                       │    │
   │                       │    ├──> Playwright connect ──────> Chrome 1
   │                       │    │
   │                       │    ├──> TikTok /upload ──────────> TikTok.com
   │                       │    │
   │                       │    ├──> Upload video1.mp4
   │                       │    │    • Select file
   │                       │    │    • Fill caption
   │                       │    │    • Set privacy
   │                       │    │    • Click Publish
   │                       │    │    • Get video URL
   │                       │    │
   │                       │    ├──> Delay 5-10 min
   │                       │    │
   │                       │    ├──> Upload video4.mp4
   │                       │    │
   │                       │    └──> Status: COMPLETED
   │                       │
   │                       └──> Thread 2: Account testuser456
   │                            │
   │                            └──> (Same process for video2, video5)
   │
   └──> ✅ All videos uploaded

4. Monitor & Logs
   │
   └──> GET /bulk-upload/1/
           │
           └──> Real-time progress:
                • 3 accounts processed
                • 5/5 videos uploaded
                • Logs for each action
                • Status: COMPLETED
```

---

## 🛠️ Технический стек

### Backend
- **Django** - Web framework
- **PostgreSQL/SQLite** - База данных
- **Celery** - Асинхронные задачи
- **Redis** - Брокер сообщений для Celery

### Automation
- **Playwright** - Браузерная автоматизация
- **Dolphin Anty** - Антидетект браузер (fingerprint masking)

### Infrastructure
- **Python 3.11+**
- **WebSocket** - Для real-time логов
- **File Storage** - /media/ для видео

---

## 📊 Мониторинг и логирование

### Логи в реальном времени

**Frontend (JavaScript):**
```javascript
// Файл: bulk_upload/detail.html

setInterval(async () => {
    const response = await fetch(`/tiktok/bulk-upload/1/logs/`);
    const data = await response.json();
    
    // Обновление UI
    document.getElementById('logs').textContent = data.logs;
    document.getElementById('progress').style.width = data.progress_percent + '%';
    
    // Обновление статистики
    document.getElementById('uploaded').textContent = data.uploaded_count;
    document.getElementById('total').textContent = data.total_count;
}, 3000);  // Каждые 3 секунды
```

**Backend (API endpoint):**
```python
# Файл: views_mod/views_bulk.py

def get_bulk_upload_logs(request, task_id):
    task = BulkUploadTask.objects.get(id=task_id)
    
    # Агрегация логов со всех аккаунтов
    logs = ""
    for bulk_account in task.bulk_accounts.all():
        logs += f"\n=== {bulk_account.account.username} ===\n"
        logs += bulk_account.log
    
    return JsonResponse({
        'logs': logs,
        'task_status': task.status,
        'uploaded_count': task.videos.filter(uploaded=True).count(),
        'total_count': task.videos.count(),
        'progress_percent': (uploaded_count / total_count * 100) if total_count > 0 else 0
    })
```

---

## 🎯 Итоговая схема

```
USER                                    SYSTEM                                  TIKTOK
────                                    ──────                                  ──────

Creates Account                         
    │
    ├──> Saves to DB                   
    └──> Creates Dolphin Profile       
                                        
Starts Warmup                           
    │
    └──> Celery Worker                 
            │
            ├──> Launches Browser ──────────────> Logs in
            │                                     │
            ├──> Scrolls feed     <───────────────┤
            ├──> Watches videos   <───────────────┤
            ├──> Likes content    ──────────────> Registers activity
            └──> Saves cookies                    

Uploads Videos                          
    │
    └──> Celery Worker                 
            │
            ├──> Launches Browser ──────────────> TikTok Upload Page
            │                                     │
            ├──> Selects file     ──────────────> Processes video
            ├──> Fills caption    ──────────────> │
            ├──> Sets privacy     ──────────────> │
            └──> Publishes        ──────────────> ✅ Video Live!

Monitors Progress                       
    │
    └──> API polling /logs/            
            │
            └──> Returns real-time status        
```

---

## ✅ Преимущества системы

1. **Масштабируемость** - параллельная обработка множества аккаунтов
2. **Anti-detection** - использование Dolphin Anty для обхода блокировок
3. **Human-like behavior** - случайные задержки и паттерны поведения
4. **Мониторинг** - real-time логи и статистика
5. **Гибкость** - настройка всех параметров загрузки
6. **Надежность** - обработка ошибок и retry механизмы

---

**Это полный путь от создания аккаунтов до массовой загрузки видео! 🚀**

