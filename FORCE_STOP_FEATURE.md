# 🛑 Функция принудительной остановки задач прогрева

**Дата:** 2025-10-05  
**Статус:** ✅ Реализовано

---

## 📋 Описание

Добавлена кнопка **"Force Stop"** для принудительной остановки зависших задач прогрева со статусом `RUNNING`.

### **Зачем это нужно?**

Иногда задача прогрева может "зависнуть" со статусом `RUNNING`, хотя фактически не выполняется:
- ❌ Сбой в фоновом потоке
- ❌ Ошибка при выполнении
- ❌ Перезапуск сервера во время выполнения
- ❌ Некорректное завершение процесса

В таких случаях задачу **невозможно удалить** и **невозможно перезапустить**.

---

## 🎯 Функциональность

### **Кнопка "Force Stop"**

Появляется на странице детализации задачи (`/tiktok/warmup/<task_id>/`) **только** для задач со статусом `RUNNING`.

```
╔════════════════════════════════════════════════╗
║  🔥 Warmup Task #4                             ║
║  [RUNNING] ⚠️ (зависла)                       ║
║                                                ║
║  [🛑 Force Stop]                               ║
╚════════════════════════════════════════════════╝
```

---

### **Что происходит при Force Stop:**

1. **Задача:**
   - `status` → `FAILED`
   - `completed_at` → текущее время
   - В лог добавляется: `⚠️ Task force stopped by {username}`

2. **Все RUNNING аккаунты в задаче:**
   - `status` → `FAILED`
   - `completed_at` → текущее время
   - В лог добавляется: `⚠️ Force stopped by {username}`

3. **После Force Stop:**
   - ✅ Появляется кнопка **"Restart Task"**
   - ✅ Появляется кнопка **"Delete"**
   - ✅ Можно удалить или перезапустить задачу

---

## 💻 Реализация

### 1. **View: `force_stop_warmup_task` в `views_warmup.py`**

```python
@login_required
def force_stop_warmup_task(request, task_id):
    """
    Принудительная остановка зависшей задачи прогрева.
    Используется когда задача имеет статус RUNNING, но фактически не выполняется.
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
    
    try:
        task = get_object_or_404(WarmupTask, id=task_id)
        
        # Проверяем что задача в статусе RUNNING
        if task.status != 'RUNNING':
            messages.warning(request, f'Task is not running (current status: {task.status})')
            return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
        
        # Принудительно останавливаем задачу
        task.status = 'FAILED'
        task.completed_at = timezone.now()
        task.log += f"\n[{timezone.now()}] ⚠️ Task force stopped by {request.user.username}"
        task.save()
        
        # Останавливаем все RUNNING аккаунты в задаче
        stopped_count = 0
        for warmup_account in task.accounts.filter(status='RUNNING'):
            warmup_account.status = 'FAILED'
            warmup_account.completed_at = timezone.now()
            warmup_account.log += f"\n[{timezone.now()}] ⚠️ Force stopped by {request.user.username}"
            warmup_account.save()
            stopped_count += 1
        
        logger.warning(f"Warmup task {task_id} ({task.name}) force stopped by user {request.user.username}")
        messages.warning(
            request,
            f'Task "{task.name}" has been force stopped. '
            f'{stopped_count} running account(s) were also stopped. '
            f'You can now delete or restart the task.'
        )
        
    except Exception as e:
        logger.error(f"Error force stopping warmup task {task_id}: {str(e)}")
        messages.error(request, f'Error stopping task: {str(e)}')
    
    return redirect('tiktok_uploader:warmup_task_detail', task_id=task_id)
```

---

### 2. **URL в `urls.py`**

```python
path('warmup/<int:task_id>/force-stop/', views_warmup.force_stop_warmup_task, name='force_stop_warmup_task'),
```

---

### 3. **Кнопка в шаблоне `detail.html`**

```html
{% if task.status == 'RUNNING' %}
    <form method="post" action="{% url 'tiktok_uploader:force_stop_warmup_task' task.id %}" style="display:inline;">
        {% csrf_token %}
        <button type="submit" class="btn btn-danger btn-lg" 
                onclick="return confirm('⚠️ Force stop this task?\n\nThis will mark the task as FAILED and stop all running accounts.\n\nUse this if the task is stuck or not actually running.')">
            <i class="bi bi-stop-circle"></i> Force Stop
        </button>
    </form>
{% endif %}
```

---

## 🎨 UI/UX

### **Визуальное отображение:**

#### **Задача со статусом RUNNING (кнопка видна):**
```
╔════════════════════════════════════════════════╗
║  🔥 Warmup Task #4                             ║
║  [RUNNING] 🔄  Created: 2025-10-05 15:46      ║
║                                                ║
║  [🛑 Force Stop]  (красная кнопка)            ║
╚════════════════════════════════════════════════╝
```

---

#### **Confirmation Dialog:**

При нажатии на **"Force Stop"** появляется подтверждение:

```
⚠️ Are you sure?

Force stop this task?

This will mark the task as FAILED and stop all running accounts.

Use this if the task is stuck or not actually running.

[Cancel]  [OK]
```

---

#### **Success Message:**

После успешной остановки:

```
⚠️ Task "Warmup 2025-10-05 15:46" has been force stopped. 
   2 running account(s) were also stopped. 
   You can now delete or restart the task.
```

---

#### **После Force Stop (кнопки изменились):**
```
╔════════════════════════════════════════════════╗
║  🔥 Warmup Task #4                             ║
║  [FAILED] ⚠️  Created: 2025-10-05 15:46       ║
║                                                ║
║  [🔄 Restart Task]  [🗑️ Delete]               ║
╚════════════════════════════════════════════════╝
```

---

## 📊 Лог задачи после Force Stop

```
[2025-10-05 15:46:44] Task started
[2025-10-05 16:36:07] Started warming up account user1
[2025-10-05 16:36:10] Authentication failed
[2025-10-05 18:59:37] ⚠️ Task force stopped by kewsen
```

---

## 🧪 Тестирование

### **Сценарий 1: Остановка зависшей задачи**

1. Задача имеет статус `RUNNING`, но фактически не выполняется
2. Перейдите на страницу задачи: `/tiktok/warmup/<task_id>/`
3. Нажмите **"Force Stop"** (красная кнопка)
4. Подтвердите действие
5. ✅ Задача сбрасывается в статус `FAILED`
6. ✅ Появляются кнопки "Restart" и "Delete"

---

### **Сценарий 2: Попытка остановить не-RUNNING задачу**

1. Задача имеет статус `PENDING`, `COMPLETED` или `FAILED`
2. Кнопка **"Force Stop"** не отображается
3. ✅ Защита от случайного использования

---

## 🔒 Безопасность

### **Проверки:**

1. ✅ **Только POST запросы** - защита от CSRF
2. ✅ **Только для RUNNING задач** - нельзя остановить завершенную задачу
3. ✅ **Требуется авторизация** - `@login_required`
4. ✅ **Логирование действий** - записывается кто остановил задачу

---

## 📈 Преимущества

1. ✅ **Удобство** - не нужно запускать скрипты или Django shell
2. ✅ **Быстро** - один клик вместо команд в терминале
3. ✅ **Безопасно** - подтверждение + логирование
4. ✅ **Понятно** - четкие сообщения о том, что произошло
5. ✅ **Отслеживаемо** - в логах остается информация кто и когда остановил

---

## 🔗 Связанные документы

- `WARMUP_COMPLETE.md` - Полная документация Warmup Tasks
- `WARMUP_RESTART_FEATURE.md` - Функция перезапуска задач
- `WARMUP_DB_ISOLATION_COMPLETE.md` - Исправление async контекста

---

## 📝 Changelog

### **2025-10-05:**
- ✅ Добавлена функция `force_stop_warmup_task` в `views_warmup.py`
- ✅ Добавлен URL `/warmup/<task_id>/force-stop/`
- ✅ Добавлена кнопка "Force Stop" в `detail.html`
- ✅ Добавлены проверки и логирование
- ✅ Добавлены warning сообщения для пользователя

---

## ✅ Статус: РЕАЛИЗОВАНО

Функция принудительной остановки зависших задач полностью реализована и готова к использованию! 🎉

**Больше не нужно запускать скрипты для исправления зависших задач - просто нажмите "Force Stop"!** 🛑

---

## 💡 Использование

### **Когда использовать Force Stop:**

✅ Задача "зависла" со статусом RUNNING  
✅ Задача фактически не выполняется  
✅ Нужно удалить или перезапустить задачу  
✅ Произошел сбой во время выполнения  
✅ Сервер был перезапущен во время выполнения  

### **Когда НЕ использовать:**

❌ Задача реально выполняется (можно увидеть активность в логах)  
❌ Задача только что запущена (дайте ей время)  
❌ Задача уже завершена (COMPLETED/FAILED)  



