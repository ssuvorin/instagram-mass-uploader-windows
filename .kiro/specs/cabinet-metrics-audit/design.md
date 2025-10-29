# Design Document

## Overview

Система кабинета имеет сложную архитектуру для подсчета метрик, которая включает несколько источников данных и методов агрегации. Основные проблемы:

1. **Дублирование данных** - одни и те же данные учитываются несколько раз
2. **Смешивание источников** - ручные и автоматические данные агрегируются некорректно
3. **Несогласованность между страницами** - разные страницы показывают разные значения
4. **Сложная логика фильтрации** - запутанная логика по периодам и ролям пользователей
5. **Отсутствие валидации** - нет проверки корректности агрегированных данных

## Architecture

### Current Problems Analysis

#### 1. Data Sources Confusion
```python
# Проблема: смешивание источников данных
# В AnalyticsService.get_manual_analytics_by_network()
filter_kwargs = {
    'hashtag__in': client_hashtags,  # Фильтр по хештегам
    **time_filter
}
# Но потом также добавляются данные из get_hashtag_details()
# что может привести к дублированию Instagram данных
```

#### 2. Inconsistent Aggregation Logic
```python
# Проблема: разная логика агрегации в разных местах
# В agency_dashboard() используется один подход:
agg = HashtagAnalytics.objects.filter(...).aggregate(views=Sum("total_views"))

# В AnalyticsService используется другой подход:
networks_data = HashtagAnalytics.objects.filter(...).values('social_network').annotate(...)
```

#### 3. Time Period Filtering Issues
```python
# Проблема: несогласованная фильтрация по времени
# Некоторые функции используют created_at
# Другие используют period_start/period_end
# Третьи не учитывают время вообще
```

### Proposed Solution Architecture

#### 1. Unified Data Layer
```
┌─────────────────────────────────────────────────────────────┐
│                    MetricsDataLayer                         │
├─────────────────────────────────────────────────────────────┤
│  + get_raw_analytics(client, period, networks)             │
│  + get_aggregated_metrics(client, period, networks)        │
│  + validate_data_consistency()                             │
│  + get_data_sources_info()                                 │
└─────────────────────────────────────────────────────────────┘
```

#### 2. Metrics Calculation Engine
```
┌─────────────────────────────────────────────────────────────┐
│                MetricsCalculationEngine                     │
├─────────────────────────────────────────────────────────────┤
│  + calculate_totals(raw_data)                              │
│  + calculate_averages(raw_data)                            │
│  + calculate_engagement_rates(raw_data)                    │
│  + calculate_growth_rates(raw_data)                        │
│  + detect_duplicates(raw_data)                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3. Unified Analytics Service
```
┌─────────────────────────────────────────────────────────────┐
│                 UnifiedAnalyticsService                     │
├─────────────────────────────────────────────────────────────┤
│  + get_client_metrics(client, period, options)             │
│  + get_agency_metrics(agency, period, options)             │
│  + get_admin_metrics(period, filters, options)             │
│  + export_metrics(scope, period, format)                   │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. MetricsDataLayer

**Purpose**: Единый слой доступа к данным аналитики

**Key Methods**:
```python
class MetricsDataLayer:
    def get_raw_analytics(
        self, 
        client: Optional[Client] = None,
        agency: Optional[Agency] = None,
        period: Optional[DateRange] = None,
        networks: Optional[List[str]] = None,
        include_manual: bool = True,
        include_automatic: bool = True
    ) -> QuerySet[HashtagAnalytics]:
        """Получить сырые данные аналитики с четкими фильтрами"""
        
    def get_aggregated_metrics(
        self,
        scope: MetricsScope,
        period: Optional[DateRange] = None,
        group_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Получить агрегированные метрики с предотвращением дублирования"""
        
    def validate_data_consistency(
        self,
        data: QuerySet[HashtagAnalytics]
    ) -> ValidationResult:
        """Валидировать данные на предмет дублирования и несогласованности"""
```

### 2. MetricsCalculationEngine

**Purpose**: Единые алгоритмы расчета метрик

**Key Methods**:
```python
class MetricsCalculationEngine:
    def calculate_network_metrics(
        self,
        raw_data: QuerySet[HashtagAnalytics],
        network: str
    ) -> NetworkMetrics:
        """Рассчитать метрики для конкретной социальной сети"""
        
    def calculate_time_series(
        self,
        raw_data: QuerySet[HashtagAnalytics],
        granularity: TimeGranularity
    ) -> List[TimeSeriesPoint]:
        """Рассчитать временные ряды метрик"""
        
    def detect_and_resolve_duplicates(
        self,
        raw_data: QuerySet[HashtagAnalytics]
    ) -> QuerySet[HashtagAnalytics]:
        """Обнаружить и устранить дублирование данных"""
```

### 3. UnifiedAnalyticsService

**Purpose**: Единый интерфейс для получения аналитики

**Key Methods**:
```python
class UnifiedAnalyticsService:
    def __init__(self, data_layer: MetricsDataLayer, calc_engine: MetricsCalculationEngine):
        self.data_layer = data_layer
        self.calc_engine = calc_engine
        
    def get_dashboard_metrics(
        self,
        user: User,
        period: Optional[DateRange] = None
    ) -> DashboardMetrics:
        """Получить метрики для дашборда с учетом роли пользователя"""
        
    def get_detailed_analytics(
        self,
        scope: MetricsScope,
        period: Optional[DateRange] = None,
        breakdown: Optional[List[str]] = None
    ) -> DetailedAnalytics:
        """Получить детальную аналитику с разбивкой"""
```

## Data Models

### Enhanced Data Structures

```python
@dataclass
class DateRange:
    start: Optional[datetime]
    end: Optional[datetime]
    
    def is_all_time(self) -> bool:
        return self.start is None and self.end is None

@dataclass
class MetricsScope:
    client: Optional[Client] = None
    agency: Optional[Agency] = None
    admin_view: bool = False
    
    def get_filter_kwargs(self) -> Dict[str, Any]:
        """Получить kwargs для фильтрации QuerySet"""

@dataclass
class NetworkMetrics:
    network: str
    total_posts: int
    total_views: int
    total_likes: int
    total_comments: int
    total_shares: int
    total_followers: int
    average_views: float
    engagement_rate: float
    growth_rate: float
    accounts_count: int
    data_sources: List[str]  # Источники данных
    calculation_method: str  # Метод расчета
    
@dataclass
class ValidationResult:
    is_valid: bool
    warnings: List[str]
    errors: List[str]
    duplicate_records: List[int]
    inconsistencies: List[str]

@dataclass
class DashboardMetrics:
    total_views: int
    total_posts: int
    total_accounts: int
    average_views: float
    engagement_rate: float
    networks: Dict[str, NetworkMetrics]
    time_series: List[TimeSeriesPoint]
    data_quality: ValidationResult
```

## Error Handling

### Data Quality Checks

1. **Duplicate Detection**:
   - Проверка на дублирование записей по (client, hashtag, social_network, created_at)
   - Проверка на дублирование при агрегации данных

2. **Consistency Validation**:
   - Проверка соответствия агрегированных данных сумме исходных записей
   - Проверка корректности временных периодов

3. **Data Source Tracking**:
   - Отслеживание источников данных для каждой метрики
   - Предупреждения о смешивании ручных и автоматических данных

### Error Recovery

```python
class MetricsErrorHandler:
    def handle_duplicate_data(
        self,
        duplicates: List[HashtagAnalytics]
    ) -> List[HashtagAnalytics]:
        """Обработать дублирующиеся записи"""
        
    def handle_inconsistent_aggregation(
        self,
        raw_total: int,
        aggregated_total: int
    ) -> int:
        """Обработать несогласованность агрегации"""
        
    def log_data_quality_issues(
        self,
        validation_result: ValidationResult
    ) -> None:
        """Логировать проблемы качества данных"""
```

## Testing Strategy

### Unit Tests
- Тестирование каждого метода расчета метрик
- Тестирование обнаружения дублирования
- Тестирование валидации данных

### Integration Tests
- Тестирование полного цикла получения метрик
- Тестирование согласованности между разными представлениями
- Тестирование экспорта данных

### Data Quality Tests
- Автоматические проверки качества данных
- Сравнение метрик между старой и новой системой
- Проверка производительности агрегации

### Performance Tests
- Тестирование производительности агрегации больших объемов данных
- Тестирование кэширования метрик
- Тестирование оптимизации запросов

## Migration Strategy

### Phase 1: Data Layer Refactoring
1. Создать MetricsDataLayer
2. Рефакторить существующие методы для использования нового слоя
3. Добавить валидацию данных

### Phase 2: Calculation Engine
1. Создать MetricsCalculationEngine
2. Перенести логику расчета из представлений в движок
3. Добавить обнаружение дублирования

### Phase 3: Service Unification
1. Создать UnifiedAnalyticsService
2. Обновить все представления для использования единого сервиса
3. Добавить логирование и мониторинг

### Phase 4: UI Improvements
1. Добавить индикаторы качества данных
2. Добавить объяснения методов расчета
3. Улучшить отображение ошибок

## Performance Considerations

### Database Optimization
- Добавить индексы для часто используемых фильтров
- Оптимизировать запросы агрегации
- Использовать материализованные представления для сложных расчетов

### Caching Strategy
- Кэшировать агрегированные метрики на уровне клиента/агентства
- Инвалидировать кэш при добавлении новых данных
- Использовать Redis для кэширования временных рядов

### Query Optimization
- Использовать select_related и prefetch_related
- Минимизировать количество запросов к базе данных
- Использовать bulk операции для обработки больших объемов данных