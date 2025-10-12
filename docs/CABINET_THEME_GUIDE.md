# Cabinet Theme - Минималистичный дизайн для кабинета клиента и агентства

## Обзор

Новая тема кабинета создана с использованием предоставленных брендовых цветов и вдохновлена дизайном [mr.Booster](https://mrbooster.com/) - современной маркетинговой агентства. Следует принципам минималистичного дизайна по лучшим практикам UI/UX.

## Цветовая схема

### Основные цвета
- **Clear White**: `#FFFFFF` - основной фон
- **Canary Yellow**: `#FFE608` - акцентный цвет для предупреждений  
- **Night Black**: `#0D0D0E` - основной текст

### Дополнительные акцентные цвета
- **Slate Blue**: `#8167FF` - основной акцентный цвет (Primary)
- **Green Yellow**: `#ACF639` - цвет успеха (Success)
- **Bittersweet**: `#FF4F52` - цвет ошибок (Danger)
- **Electric Blue**: `#4DE6F4` - информационный цвет (Info)

### Применение цветов
- **Primary** (Slate Blue) - основные действия, ссылки, акценты
- **Success** (Green Yellow) - успешные операции, положительные статусы
- **Warning** (Canary Yellow) - предупреждения, внимание
- **Danger** (Bittersweet) - ошибки, критические действия
- **Info** (Electric Blue) - информационные сообщения, подсказки

## Дизайн-подход mr.Booster

Тема вдохновлена дизайном [mr.Booster](https://mrbooster.com/) и включает:

### Ключевые особенности
- **Крупная типографика** - жирные заголовки с отрицательным letter-spacing
- **Градиентные акценты** - тонкие градиентные полосы для выделения
- **Четкие разделители** - толстые границы и контрастные элементы
- **Современные карточки** - минималистичные карточки с hover-эффектами
- **Анимации** - плавные переходы и трансформации
- **Uppercase текст** - для кнопок, бейджей и меток

### Брендинг mr.Booster
- **Шрифты**: Inter (основной), Onest (заголовки) - применяются только в кабинетах
- **Логотипы**: Цветной, черный, белый варианты - используются только в кабинетах
- **Фавиконы**: Различные размеры для всех устройств - применяются только в кабинетах
- **Цветовая палитра**: Точное соответствие брендовым цветам - используется только в кабинетах

## Использование

### Подключение темы

Тема автоматически подключается в шаблонах кабинетов клиента и агентства:

```html
{% extends "uploader/base.html" %}
{% load static %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/cabinet-theme.css' %}">
<!-- mr.Booster Favicons for Cabinet -->
<link rel="icon" type="image/png" sizes="16x16" href="{% static 'images/favicon-16x16.png' %}">
<link rel="icon" type="image/png" sizes="32x32" href="{% static 'images/favicon-32x32.png' %}">
<link rel="icon" type="image/svg+xml" href="{% static 'images/mrbooster-logo-color.svg' %}">
{% endblock %}
```

### Переопределение Bootstrap цветов

Тема автоматически переопределяет стандартные цвета Bootstrap с брендовыми цветами:

- `btn-primary` → Slate Blue (#8167FF)
- `btn-success` → Green Yellow (#ACF639)  
- `btn-warning` → Canary Yellow (#FFE608)
- `btn-danger` → Bittersweet (#FF4F52)
- `btn-info` → Electric Blue (#4DE6F4)

Аналогично для классов `badge-*`, `alert-*`, `text-*`, `bg-*`.

### Базовый контейнер

```html
<div class="cabinet-theme">
  <!-- Содержимое кабинета -->
</div>
```

### Заголовок дашборда

```html
<div class="dashboard-header">
  <div class="container">
    <div class="d-flex justify-content-between align-items-center">
      <div>
        <h1 class="dashboard-title">Dashboard Title</h1>
        <p class="dashboard-subtitle">Subtitle</p>
      </div>
      <div class="btn-toolbar gap-2">
        <!-- Кнопки действий -->
      </div>
    </div>
  </div>
</div>
```

### KPI карточки

```html
<div class="stats-grid">
  <div class="kpi-card fade-in">
    <div class="kpi-value">1,234</div>
    <div class="kpi-label">Total Views</div>
  </div>
  <div class="kpi-card fade-in">
    <div class="kpi-value">567</div>
    <div class="kpi-label">Total Videos</div>
  </div>
</div>
```

### Карточки

```html
<div class="card mb-8 slide-up">
  <div class="card-header">
    <h5 class="mb-0">Card Title</h5>
  </div>
  <div class="card-body">
    <!-- Содержимое карточки -->
  </div>
</div>
```

### Кнопки

```html
<!-- Основные кнопки -->
<button class="btn btn-primary">Primary</button>
<button class="btn btn-success">Success</button>
<button class="btn btn-warning">Warning</button>
<button class="btn btn-danger">Danger</button>
<button class="btn btn-info">Info</button>

<!-- Outline кнопки -->
<button class="btn btn-outline-primary">Outline Primary</button>
<button class="btn btn-outline-secondary">Outline Secondary</button>
```

### Таблицы

```html
<div class="table-responsive">
  <table class="table table-hover">
    <thead>
      <tr>
        <th>Column 1</th>
        <th>Column 2</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Data 1</td>
        <td>Data 2</td>
      </tr>
    </tbody>
  </table>
</div>
```

### Бейджи сетей

```html
<span class="network-badge instagram">
  <i class="bi bi-instagram"></i>Instagram
</span>
<span class="network-badge youtube">
  <i class="bi bi-youtube"></i>YouTube
</span>
<span class="network-badge tiktok">
  <i class="bi bi-music-note-beamed"></i>TikTok
</span>
```

### Хештеги

```html
<a href="#" class="hashtag-tag">#hashtag</a>
```

### Контейнеры для графиков

```html
<div class="chart-container">
  <div class="chart-header">
    <h5 class="chart-title">Chart Title</h5>
  </div>
  <div style="height: 300px;">
    <canvas id="chart"></canvas>
  </div>
</div>
```

### Дополнительные элементы mr.Booster стиля

```html
<!-- Разделитель секций -->
<hr class="section-divider">

<!-- Выделенная информация -->
<div class="feature-highlight">
  <h6>Important Information</h6>
  <p>This is highlighted content with gradient background.</p>
</div>

<!-- Метрические карточки -->
<div class="metric-card">
  <div class="metric-value">1,234</div>
  <div class="metric-label">Total Views</div>
</div>
```

### Типографика mr.Booster

Тема использует официальные шрифты mr.Booster:

- **Inter** - основной шрифт для текста и интерфейса
- **Onest** - шрифт для заголовков и акцентов

Шрифты автоматически загружаются из `static/fonts/` и применяются через CSS переменные:
- `--cabinet-font-family` - Inter для основного текста
- `--cabinet-font-heading` - Onest для заголовков

## Анимации

### Доступные классы анимации
- `fade-in` - плавное появление
- `slide-up` - появление снизу вверх

### Использование
```html
<div class="kpi-card fade-in">...</div>
<div class="card slide-up">...</div>
```

## Адаптивность

Тема полностью адаптивна и оптимизирована для:
- Десктопов (1200px+)
- Планшетов (768px - 1199px)
- Мобильных устройств (до 767px)

### Мобильные классы
- `mobile-header` - адаптивный заголовок
- `mobile-btn-group` - адаптивная группа кнопок
- `mobile-card-grid` - адаптивная сетка карточек
- `mobile-table` - адаптивная таблица
- `mobile-chart-container` - адаптивный контейнер графиков

## Темная тема

Для включения темной темы добавьте класс `dark-theme` к контейнеру:

```html
<div class="cabinet-theme dark-theme">
  <!-- Содержимое в темной теме -->
</div>
```

## Утилитарные классы

### Отступы
- `mb-0` до `mb-8` - нижние отступы
- `mt-0` до `mt-8` - верхние отступы
- `p-0` до `p-8` - внутренние отступы

### Выравнивание текста
- `text-center` - по центру
- `text-left` - по левому краю
- `text-right` - по правому краю

### Цвета текста
- `text-primary` - основной цвет
- `text-success` - цвет успеха
- `text-warning` - цвет предупреждения
- `text-danger` - цвет ошибки
- `text-info` - информационный цвет
- `text-muted` - приглушенный цвет

## Примеры использования

### Клиентский дашборд
```html
<div class="cabinet-theme">
  <div class="dashboard-header">
    <div class="container">
      <div class="d-flex justify-content-between align-items-center">
        <div>
          <h1 class="dashboard-title">Client Dashboard</h1>
          <p class="dashboard-subtitle">Client Name</p>
        </div>
        <div class="btn-toolbar gap-2">
          <a class="btn btn-success btn-sm" href="#">
            <i class="bi bi-file-earmark-excel"></i> Excel
          </a>
        </div>
      </div>
    </div>
  </div>

  <div class="container">
    <div class="stats-grid">
      <div class="kpi-card fade-in">
        <div class="kpi-value">1,234</div>
        <div class="kpi-label">Total Videos</div>
      </div>
      <div class="kpi-card fade-in">
        <div class="kpi-value">567,890</div>
        <div class="kpi-label">Total Views</div>
      </div>
    </div>

    <div class="card mb-8 slide-up">
      <div class="card-header">
        <h5 class="mb-0">Analytics</h5>
      </div>
      <div class="card-body">
        <!-- Содержимое -->
      </div>
    </div>
  </div>
</div>
```

### Агентский дашборд
```html
<div class="cabinet-theme">
  <div class="dashboard-header">
    <div class="container">
      <div class="d-flex justify-content-between align-items-center">
        <div>
          <h1 class="dashboard-title">Agency Dashboard</h1>
          <p class="dashboard-subtitle">Agency Name</p>
        </div>
        <div class="btn-toolbar gap-2">
          <a class="btn btn-outline-primary btn-sm" href="#">Manage Clients</a>
          <a class="btn btn-outline-secondary btn-sm" href="#">Calculator</a>
          <a class="btn btn-success btn-sm" href="#">Excel</a>
        </div>
      </div>
    </div>
  </div>

  <div class="container">
    <!-- Аналогично клиентскому дашборду -->
  </div>
</div>
```

## Лучшие практики

1. **Используйте семантические классы** - предпочитайте `kpi-card` вместо кастомных стилей
2. **Добавляйте анимации** - используйте `fade-in` и `slide-up` для улучшения UX
3. **Следуйте иерархии** - используйте правильные размеры заголовков и отступов
4. **Тестируйте адаптивность** - проверяйте на разных размерах экранов
5. **Используйте темную тему** - предоставляйте возможность переключения

## Совместимость

Тема совместима с:
- Bootstrap 5.3.0
- Bootstrap Icons 1.10.0
- Chart.js (для графиков)
- Современными браузерами (Chrome, Firefox, Safari, Edge)

## Поддержка

При возникновении проблем или предложений по улучшению темы, создавайте issue в репозитории проекта.
