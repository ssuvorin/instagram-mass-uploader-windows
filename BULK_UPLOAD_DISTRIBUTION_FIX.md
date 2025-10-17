# Исправление логики распределения видео в Bulk Upload

## Проблема

В предыдущей реализации bulk upload была серьезная ошибка в логике распределения видео между аккаунтами:

### Что было неправильно:
- **Каждый аккаунт получал ВСЕ видео задачи**
- Если было 10 аккаунтов и 10 видео, то каждое видео загружалось на все 10 аккаунтов
- Это приводило к 100 загрузкам вместо 10
- Описания тоже дублировались между аккаунтами

### Пример проблемы:
```
Аккаунт 1: video_1, video_2, video_3, ..., video_10
Аккаунт 2: video_1, video_2, video_3, ..., video_10  ← ДУБЛИРОВАНИЕ!
Аккаунт 3: video_1, video_2, video_3, ..., video_10  ← ДУБЛИРОВАНИЕ!
...
```

## Решение

### Новая логика распределения:
- **Каждый аккаунт получает уникальные видео без повторений**
- Видео распределяются равномерно между аккаунтами
- Описания назначаются случайно, но без дублирования

### Пример правильного распределения:
```
Аккаунт 1: video_1
Аккаунт 2: video_2
Аккаунт 3: video_3
...
Аккаунт 10: video_10
```

## Изменения в коде

### 1. Асинхронная версия (`uploader/async_bulk_tasks.py`)

#### Добавлен метод `_get_unique_videos_for_account()`:
```python
async def _get_unique_videos_for_account(self) -> List[VideoData]:
    """Получает уникальные видео для аккаунта без повторений между аккаунтами"""
    all_videos = list(self.task_data.videos)
    all_accounts = list(self.task_data.accounts)
    
    # Находим индекс текущего аккаунта в списке
    current_account_index = -1
    for i, account in enumerate(all_accounts):
        if account.id == self.account_task.account.id:
            current_account_index = i
            break
    
    # Распределяем видео равномерно между аккаунтами
    videos_per_account = len(all_videos) // len(all_accounts)
    remainder = len(all_videos) % len(all_accounts)
    
    # Определяем диапазон видео для текущего аккаунта
    start_index = current_account_index * videos_per_account + min(current_account_index, remainder)
    end_index = start_index + videos_per_account + (1 if current_account_index < remainder else 0)
    
    # Получаем видео для текущего аккаунта
    account_videos = all_videos[start_index:end_index]
    random.shuffle(account_videos)
    
    return account_videos
```

#### Обновлен метод `_prepare_videos_for_account()`:
```python
async def _prepare_videos_for_account(self) -> List[VideoData]:
    """Подготавливает видео для аккаунта с правильным распределением без повторений"""
    # ИСПРАВЛЕНИЕ: Получаем уникальные видео для этого аккаунта
    videos_for_account = await self._get_unique_videos_for_account()
    # ... остальная логика
```

#### Исправлен режим rounds:
```python
if use_rounds:
    # ИСПРАВЛЕНИЕ: В rounds режиме распределяем видео равномерно между аккаунтами
    all_video_datas = list(task_data.videos)
    all_accounts = list(account_tasks)
    
    # Распределяем видео между аккаунтами
    videos_per_account = len(all_video_datas) // len(all_accounts)
    remainder = len(all_video_datas) % len(all_accounts)
    
    # Создаем задачи для каждого аккаунта с его уникальными видео
    for account_index, account_task in enumerate(all_accounts):
        start_index = account_index * videos_per_account + min(account_index, remainder)
        end_index = start_index + videos_per_account + (1 if account_index < remainder else 0)
        account_videos = all_video_datas[start_index:end_index]
        # ...
```

### 2. Синхронная версия (`uploader/bulk_tasks_playwright.py`)

#### Добавлена функция `get_unique_videos_for_account()`:
```python
def get_unique_videos_for_account(account_task, task, all_videos):
    """Получает уникальные видео для аккаунта без повторений между аккаунтами"""
    all_accounts = list(task.accounts.all())
    
    # Находим индекс текущего аккаунта в списке
    current_account_index = -1
    for i, account_task_item in enumerate(all_accounts):
        if account_task_item.id == account_task.id:
            current_account_index = i
            break
    
    # Распределяем видео равномерно между аккаунтами
    videos_per_account = len(all_videos) // len(all_accounts)
    remainder = len(all_videos) % len(all_accounts)
    
    # Определяем диапазон видео для текущего аккаунта
    start_index = current_account_index * videos_per_account + min(current_account_index, remainder)
    end_index = start_index + videos_per_account + (1 if current_account_index < remainder else 0)
    
    # Получаем видео для текущего аккаунта
    account_videos = all_videos[start_index:end_index]
    random.shuffle(account_videos)
    
    return account_videos
```

#### Обновлена функция `process_account_videos()`:
```python
def process_account_videos(account_task, task, all_videos, all_titles, task_id):
    """Process videos for a single account with proper distribution without repetitions"""
    # ИСПРАВЛЕНИЕ: Получаем уникальные видео для этого аккаунта
    videos_for_account = get_unique_videos_for_account(account_task, task, all_videos)
    # ... остальная логика
```

## Алгоритм распределения

### Формула распределения:
```python
videos_per_account = total_videos // total_accounts
remainder = total_videos % total_accounts

for account_index in range(total_accounts):
    start_index = account_index * videos_per_account + min(account_index, remainder)
    end_index = start_index + videos_per_account + (1 if account_index < remainder else 0)
    account_videos = all_videos[start_index:end_index]
```

### Примеры распределения:

#### Случай 1: Равное количество (10 видео, 10 аккаунтов)
- Каждый аккаунт получает 1 видео
- Аккаунт 0: video_0
- Аккаунт 1: video_1
- ...
- Аккаунт 9: video_9

#### Случай 2: Больше видео чем аккаунтов (15 видео, 10 аккаунтов)
- Первые 5 аккаунтов получают по 2 видео
- Остальные 5 аккаунтов получают по 1 видео
- Аккаунт 0: video_0, video_1
- Аккаунт 1: video_2, video_3
- ...
- Аккаунт 4: video_8, video_9
- Аккаунт 5: video_10
- ...
- Аккаунт 9: video_14

#### Случай 3: Больше аккаунтов чем видео (5 видео, 10 аккаунтов)
- Первые 5 аккаунтов получают по 1 видео
- Остальные 5 аккаунтов не получают видео
- Аккаунт 0: video_0
- Аккаунт 1: video_1
- ...
- Аккаунт 4: video_4
- Аккаунт 5-9: нет видео

## Тестирование

Создан тест `test_distribution_logic.py` который проверяет:
- ✅ Правильность распределения видео без повторений
- ✅ Равномерность распределения
- ✅ Корректность работы с граничными случаями
- ✅ Правильность назначения описаний

## Результат

### До исправления:
- 10 аккаунтов × 10 видео = 100 загрузок
- Дублирование контента между аккаунтами

### После исправления:
- 10 аккаунтов × 1 уникальное видео = 10 загрузок
- Каждый аккаунт получает уникальный контент
- Эффективное использование ресурсов

## Совместимость

Исправления работают для:
- ✅ Обычного bulk upload (синхронная версия)
- ✅ Async bulk upload (асинхронная версия)
- ✅ API режима (instagrapi)
- ✅ Rounds режима
- ✅ Все типы задач (Instagram, YouTube Shorts)

## Логирование

Добавлено подробное логирование распределения:
```
[DISTRIBUTION] Account username gets videos 1-1 (1 videos)
[ROUNDS] Distributing 10 videos among 10 accounts
[ROUNDS] Each account gets 1 videos, 0 accounts get 1 extra
```

Это помогает отслеживать правильность распределения в реальном времени.
