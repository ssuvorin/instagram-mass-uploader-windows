# 🎨 TikTok Uploader - Templates Guide

## 📋 Быстрый старт

### 1. Структура шаблонов создана

```
tiktok_uploader/templates/tiktok_uploader/
├── base.html                       ✅ Базовый layout
├── dashboard.html                  ✅ Главная страница
├── accounts/
│   └── account_list.html           ✅ Список аккаунтов
├── bulk_upload/
│   ├── list.html                   ✅ Список задач
│   └── create.html                 ✅ Создание задачи
├── warmup/                         📁 Готова к заполнению
├── follow/                         📁 Готова к заполнению
├── proxies/                        📁 Готова к заполнению
└── cookies/                        📁 Готова к заполнению
```

### 2. Доступ к страницам

После запуска сервера:
```bash
python manage.py runserver
```

Страницы доступны по адресам:
- **Dashboard**: http://localhost:8000/tiktok/
- **Accounts**: http://localhost:8000/tiktok/accounts/
- **Bulk Upload**: http://localhost:8000/tiktok/bulk-upload/
- **Create Task**: http://localhost:8000/tiktok/bulk-upload/create/

---

## 🎨 Дизайн-система TikTok

### Цвета

```css
/* Primary Colors */
--tiktok-red: #FE2C55      /* Основной бренд */
--tiktok-blue: #00F2EA     /* Акцент */
--tiktok-black: #000000    /* Темный */
--tiktok-white: #FFFFFF    /* Светлый */
--tiktok-gray: #F1F1F2     /* Фон */
```

### Компоненты

#### TikTok Card
```html
<div class="tiktok-card">
    <div class="card-body">
        <!-- Контент -->
    </div>
</div>
```

#### TikTok Button
```html
<button class="btn btn-tiktok">
    <i class="bi bi-plus-circle"></i> Action
</button>
```

#### Status Badge
```html
<span class="status-badge-tiktok badge-active">ACTIVE</span>
<span class="status-badge-tiktok badge-running">RUNNING</span>
<span class="status-badge-tiktok badge-completed">COMPLETED</span>
```

#### Progress Bar
```html
<div class="progress-tiktok">
    <div class="progress-bar-tiktok" style="width: 45%;"></div>
</div>
```

---

## 🔧 Кастомизация

### Добавление новой страницы

1. **Создайте файл в нужной директории:**
```bash
New-Item -ItemType File -Path "tiktok_uploader\templates\tiktok_uploader\my_page.html"
```

2. **Используйте базовый template:**
```django
{% extends "tiktok_uploader/base.html" %}

{% block title %}My Page - TikTok Uploader{% endblock %}

{% block extra_css %}
<style>
    /* Ваши стили */
</style>
{% endblock %}

{% block content %}
    <!-- Ваш контент -->
{% endblock %}
```

3. **Добавьте URL в `urls.py`**

---

## 📦 Готовые блоки

### Empty State
```django
<div class="text-center py-5">
    <i class="bi bi-inbox" style="font-size: 4rem; color: #f1f1f2;"></i>
    <h4 class="mt-3 mb-2 fw-bold">No Data</h4>
    <p class="text-muted mb-4">Description text</p>
    <a href="#" class="btn btn-tiktok">
        <i class="bi bi-plus-circle"></i> Create First
    </a>
</div>
```

### Stat Card
```django
<div class="col-md-3">
    <div class="stat-card">
        <div class="stat-value">{{ count }}</div>
        <div class="stat-label">Label</div>
    </div>
</div>
```

### Action Card
```django
<div class="col-md-2 col-6">
    <a href="{% url 'some_url' %}" class="quick-action-item">
        <div class="quick-action-content">
            <i class="bi bi-icon quick-action-icon"></i>
            <div class="quick-action-label">Label</div>
        </div>
    </a>
</div>
```

---

## 🚀 Примеры использования

### Создание страницы списка

```django
{% extends "tiktok_uploader/base.html" %}

{% block title %}My List - TikTok Uploader{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col-md-6">
        <h2 class="fw-bold">
            <i class="bi bi-list" style="color: #FE2C55;"></i>
            My List
        </h2>
    </div>
    <div class="col-md-6 text-end">
        <a href="{% url 'create' %}" class="btn btn-tiktok">
            <i class="bi bi-plus-circle"></i> New Item
        </a>
    </div>
</div>

<div class="card tiktok-card">
    <div class="card-body">
        <table class="table">
            <!-- Ваша таблица -->
        </table>
    </div>
</div>
{% endblock %}
```

---

## 📱 Адаптивность

Все шаблоны используют Bootstrap 5.3 grid:
- **xs**: < 576px (mobile)
- **sm**: ≥ 576px
- **md**: ≥ 768px (tablet)
- **lg**: ≥ 992px
- **xl**: ≥ 1200px (desktop)
- **xxl**: ≥ 1400px

Пример:
```html
<div class="col-md-4 col-sm-6 col-12">
    <!-- На desktop: 3 колонки, tablet: 2, mobile: 1 -->
</div>
```

---

## 🌗 Dark Mode

Dark mode реализован через класс `.dark-theme` на `<body>`:

```css
/* Light mode (default) */
.tiktok-card { background: white; border-color: #f1f1f2; }

/* Dark mode */
.dark-theme .tiktok-card { background: #1a1a1a; border-color: #333; }
```

Theme switcher сохраняет выбор в localStorage.

---

## 🎯 Best Practices

1. **Используйте готовые компоненты** из `base.html`
2. **Следуйте TikTok color scheme** (red, blue, black)
3. **Добавляйте hover эффекты** для интерактивности
4. **Используйте gradients** для акцентов
5. **Empty states** для пустых списков
6. **Loading states** для async операций
7. **Responsive design** для всех экранов
8. **Icons** из Bootstrap Icons

---

## 📚 Полезные ссылки

- [Bootstrap 5.3 Docs](https://getbootstrap.com/docs/5.3/)
- [Bootstrap Icons](https://icons.getbootstrap.com/)
- [Django Templates](https://docs.djangoproject.com/en/5.0/topics/templates/)
- [TikTok Brand Guidelines](https://www.tiktok.com/brand-guidelines)

---

## 🤝 Создание остальных шаблонов

### Рекомендуемый порядок:

1. **Accounts** (высокий приоритет)
   - `account_detail.html`
   - `create_account.html`
   - `edit_account.html`
   - `import_accounts.html`

2. **Bulk Upload** (высокий приоритет)
   - `detail.html`
   - `add_videos.html`
   - `add_captions.html`

3. **Proxies** (средний приоритет)
   - `proxy_list.html`
   - `create_proxy.html`
   - `import_proxies.html`

4. **Warmup, Follow, Cookies** (низкий приоритет)
   - Создать по аналогии с Instagram

### Шаблон для копирования из Instagram:

1. Откройте аналогичный файл из `uploader/templates/uploader/`
2. Скопируйте структуру
3. Замените:
   - `uploader` → `tiktok_uploader`
   - `Instagram` → `TikTok`
   - Цветовую схему на TikTok
   - URL namespace: `'url_name'` → `'tiktok_uploader:url_name'`

---

## ✅ Чеклист создания нового template

- [ ] Extends `base.html`
- [ ] Title block установлен
- [ ] TikTok color scheme использован
- [ ] Responsive grid (Bootstrap)
- [ ] Icons добавлены (Bootstrap Icons)
- [ ] Hover эффекты реализованы
- [ ] Empty state добавлен
- [ ] Forms используют TikTok стили
- [ ] Кнопки используют `.btn-tiktok`
- [ ] Dark mode поддержан
- [ ] URL namespace корректный

---

**Все шаблоны готовы к использованию! 🎉**


