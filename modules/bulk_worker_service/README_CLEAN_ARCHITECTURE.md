# Bulk Worker Service - Clean Architecture Implementation

## Overview

This implementation provides a complete refactor of the bulk worker service following **SOLID principles**, **Clean Architecture**, and best practices including **DRY**, **KISS**, and comprehensive error handling.

## Architecture Principles Applied

### SOLID Principles

1. **Single Responsibility Principle (SRP)**
   - Each class has one reason to change
   - `JobManager` only manages jobs
   - `TaskRunner` only executes tasks
   - `MetricsCollector` only handles metrics

2. **Open/Closed Principle (OCP)**
   - System is open for extension, closed for modification
   - New task types can be added via `TaskRunnerFactory.register_runner()`
   - New implementations can be plugged in via interfaces

3. **Liskov Substitution Principle (LSP)**
   - All implementations are substitutable through interfaces
   - Any `ITaskRunner` implementation works with the orchestrator

4. **Interface Segregation Principle (ISP)**
   - Small, focused interfaces
   - Clients depend only on methods they use

5. **Dependency Inversion Principle (DIP)**
   - High-level modules don't depend on low-level modules
   - Both depend on abstractions (interfaces)

### Additional Principles

- **DRY (Don't Repeat Yourself)**: Common functionality extracted to base classes and shared services
- **KISS (Keep It Simple, Stupid)**: Simple, focused implementations
- **Clean Code**: Readable, maintainable, well-documented code

## Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   FastAPI App   │  │   Error Handler │  │  Validation  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ WorkerOrchestrator│ │   JobManager    │  │   Metrics    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ TaskRunnerFactory│ │   BaseTaskRunner│  │ UiClientFactory│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Repository Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  JobRepository  │  │  MetricsCollector│  │   UiClient   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Interfaces (`interfaces.py`)

- `IJobManager`: Job lifecycle management
- `ITaskRunner`: Task execution interface
- `ITaskRunnerFactory`: Factory for creating runners
- `IMetricsCollector`: Metrics collection interface
- `IJobRepository`: Job data persistence interface
- `IUiClientFactory`: UI client creation interface

### 2. Services (`services.py`)

- `JobManager`: Main job management implementation
- `InMemoryJobRepository`: In-memory job storage
- `SimpleMetricsCollector`: Basic metrics collection
- `DefaultUiClientFactory`: Default UI client factory

### 3. Factories (`factories.py`)

- `TaskRunnerFactory`: Creates appropriate task runners
- Task runner implementations for each task type:
  - `BulkUploadTaskRunner`
  - `WarmupTaskRunner`
  - `AvatarTaskRunner`
  - `BioTaskRunner`
  - `FollowTaskRunner`
  - `ProxyDiagTaskRunner`
  - `MediaUniqTaskRunner`
  - `CookieRobotTaskRunner`

### 4. Error Handling (`exceptions.py`)

- Comprehensive exception hierarchy
- Centralized error handling
- Circuit breaker pattern for resilience
- Retry mechanisms for transient failures

### 5. Dependency Injection (`container.py`)

- `DIContainer`: Manages dependencies
- Auto-wiring for common types
- Singleton and factory registration
- Easy testing with mock dependencies

## API Endpoints

### Job Management
```
GET    /api/v1/jobs                    # List all jobs
GET    /api/v1/jobs/{job_id}/status    # Get job status
POST   /api/v1/jobs/{job_id}/stop      # Stop running job
DELETE /api/v1/jobs/{job_id}           # Delete job
```

### Task Execution
```
POST /api/v1/bulk-tasks/start          # Bulk upload (legacy)
POST /api/v1/bulk-login/start          # Bulk login
POST /api/v1/warmup/start              # Account warmup
POST /api/v1/avatar/start              # Avatar change
POST /api/v1/bio/start                 # Bio link change
POST /api/v1/follow/start              # Follow tasks
POST /api/v1/proxy-diagnostics/start   # Proxy diagnostics
POST /api/v1/media-uniq/start          # Media uniquifier
POST /api/v1/cookie-robot/start        # Cookie robot
```

### Monitoring
```
GET /api/v1/health                     # Health check
GET /api/v1/metrics                    # Worker metrics
```

## Usage Examples

### Starting a Task

```python
from bulk_worker_service.container import get_orchestrator
from bulk_worker_service.domain import StartOptions

orchestrator = get_orchestrator()

# Start a warmup task
options = StartOptions(concurrency=4, headless=True)
job_id = await orchestrator.start_warmup(task_id=123, options=options)

# Check status
status = await orchestrator.get_job_status(job_id)
print(f"Job {job_id} status: {status.status}")
```

### Adding a Custom Task Runner

```python
from bulk_worker_service.factories import BaseTaskRunner
from bulk_worker_service.container import get_container

class CustomTaskRunner(BaseTaskRunner):
    @property
    def task_type(self) -> str:
        return "custom_task"
    
    async def _execute_task(self, ui_client, task_id, options):
        # Custom task implementation
        return success_count, failure_count

# Register the new runner
factory = get_container().get(ITaskRunnerFactory)
factory.register_runner("custom_task", CustomTaskRunner)
```

### Dependency Injection Configuration

```python
from bulk_worker_service.container import get_container

# Get configured services
container = get_container()

# Register custom implementations
container.register_singleton(IJobRepository, CustomJobRepository())
container.register_factory(IMetricsCollector, lambda: CustomMetrics())

# Get orchestrator with custom dependencies
orchestrator = container.get(WorkerOrchestrator)
```

## Testing

### Running Tests

```bash
# Run all tests
pytest modules/bulk_worker_service/bulk_worker_service/test_*.py -v

# Run specific test file
pytest modules/bulk_worker_service/bulk_worker_service/test_architecture.py -v

# Run with coverage
pytest --cov=bulk_worker_service modules/bulk_worker_service/bulk_worker_service/test_*.py
```

### Test Categories

1. **Unit Tests** (`test_architecture.py`)
   - Individual component testing
   - Interface compliance
   - Business logic validation

2. **Integration Tests** (`test_api.py`)
   - API endpoint testing
   - Error handling validation
   - End-to-end workflows

### Mocking Dependencies

```python
import pytest
from unittest.mock import Mock
from bulk_worker_service.container import DIContainer

@pytest.fixture
def mock_container():
    container = DIContainer()
    container.register_singleton(IJobRepository, Mock())
    container.register_singleton(IMetricsCollector, Mock())
    return container
```

## Configuration

### Environment Variables

```bash
# UI Communication
UI_API_BASE=http://ui-server:8000
UI_API_TOKEN=your_api_token

# Worker Configuration
CONCURRENCY_LIMIT=4
BATCH_SIZE=2
HEADLESS=true
UPLOAD_METHOD=playwright

# Dolphin Browser
DOLPHIN_API_TOKEN=your_dolphin_token
DOLPHIN_API_HOST=http://dolphin-host:3001
```

### Settings Class

```python
from bulk_worker_service.config import settings

# Access configuration
print(f"Concurrency: {settings.concurrency_limit}")
print(f"UI Base: {settings.ui_api_base}")
```

## Error Handling

### Exception Hierarchy

```
WorkerServiceError
├── JobNotFoundError
├── InvalidTaskTypeError
├── JobExecutionError
├── ConfigurationError
├── UiClientError
├── ValidationError
├── ResourceNotAvailableError
├── TimeoutError
├── AuthenticationError
└── RateLimitError
```

### Error Handling Patterns

```python
from bulk_worker_service.exceptions import handle_exceptions, ErrorHandler

@handle_exceptions
async def my_task():
    # Task implementation
    pass

# Manual error handling
try:
    await some_operation()
except Exception as e:
    error = ErrorHandler.handle_job_error(job_id, e, context)
    raise error
```

## Monitoring and Metrics

### Available Metrics

- `total_jobs`: Total number of jobs processed
- `completed_jobs`: Successfully completed jobs
- `failed_jobs`: Failed jobs
- `total_accounts_processed`: Total accounts processed
- `total_uploads_success`: Successful uploads
- `total_uploads_failed`: Failed uploads
- `jobs_by_type`: Job counts by type
- `running_jobs_count`: Currently running jobs

### Accessing Metrics

```python
orchestrator = get_orchestrator()
metrics = await orchestrator.get_metrics()
print(f"Total jobs: {metrics['total_jobs']}")
```

## Migration from Legacy Code

### Backward Compatibility

The new architecture maintains backward compatibility with existing endpoints while providing a clean migration path:

1. **Legacy orchestrator** (`orchestrator.py`) still available
2. **New orchestrator** (`orchestrator_v2.py`) with clean architecture
3. **Gradual migration** of endpoints to new system
4. **Existing API contracts** preserved

### Migration Steps

1. **Phase 1**: Deploy new architecture alongside legacy
2. **Phase 2**: Migrate endpoints one by one
3. **Phase 3**: Remove legacy components
4. **Phase 4**: Full clean architecture deployment

## Performance Considerations

### Scalability Features

- **Asynchronous execution**: All operations are async
- **Concurrency control**: Configurable semaphores
- **Batch processing**: Efficient resource utilization
- **Circuit breaker**: Prevents cascade failures
- **Retry mechanisms**: Handles transient failures

### Resource Management

- **Connection pooling**: Efficient HTTP client usage
- **Memory management**: Proper cleanup of resources
- **Graceful shutdown**: Clean termination of tasks

## Contributing

### Adding New Task Types

1. Create task runner class extending `BaseTaskRunner`
2. Implement `task_type` property and `_execute_task` method
3. Register runner in `TaskRunnerFactory`
4. Add corresponding API endpoint
5. Write comprehensive tests

### Code Style

- Follow PEP 8 conventions
- Use type hints throughout
- Write comprehensive docstrings
- Include unit tests for new functionality
- Maintain backward compatibility

## Future Enhancements

### Planned Features

1. **Database persistence**: Replace in-memory storage
2. **Distributed task queue**: Redis/RabbitMQ integration
3. **Real-time monitoring**: WebSocket endpoints
4. **Advanced metrics**: Prometheus integration
5. **Health checks**: Detailed system diagnostics
6. **Configuration management**: Dynamic configuration updates

### Extension Points

- Custom task runners via factory registration
- Pluggable storage backends via `IJobRepository`
- Custom metrics collectors via `IMetricsCollector`
- Alternative UI clients via `IUiClientFactory`