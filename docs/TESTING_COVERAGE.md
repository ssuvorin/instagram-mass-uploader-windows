## Тестовая стратегия: UI + Worker + Контракты

Цель: зафиксировать соответствие после обновлений, предотвратить дрейф контрактов и обеспечить готовность к масштабированию 20+ воркеров.

### Уровни тестов
- Unit:
  - UI: `dashboard/api_views` (аутентификация, агрегаты, статусы, локи)
  - Worker: `services.JobManager`, `ui_client`, `runners/*`, `media_processing`
- Integration (in-process):
  - UI: `Client` → реальный маршрут → модель/сериализация
  - Worker: TestClient FastAPI → orchestrator → mock UiClient
- Contract (UI↔Worker):
  - Зафиксированные примеры (golden files) агрегатов и статусов
  - Pydantic схемы, валидация запроса/ответа с обеих сторон
- E2E Smoke:
  - Локально поднять UI и Worker, выполнить старт задачи в pull‑режиме

### Быстрый план покрытия
- UI
  - test_api_auth_ip_allowlist
  - test_aggregate_endpoints_consistency (сравнить с pydantic‑схемами)
  - test_status_update_endpoints (200/400/401)
  - test_lock_acquire_release_ttl
- Worker
  - test_orchestrator_start_per_type (bulk, login, warmup, ...)
  - test_job_manager_lifecycle
  - test_ui_client_endpoints_mapping (mock UI)
  - test_media_uniquification_distribution

### Схемы контрактов
- Вынести общий пакет `contracts/` (pydantic) с версиями схем.
- Генерация OpenAPI для Worker; для UI — описать JSON‑схемы агрегатов.
- Тесты: фолдинг/обязательность полей, обратная совместимость.

### Инструменты
- pytest + pytest-django + httpx/anyio + respx
- factory_boy для моделей
- docker-compose для e2e smoke (опционально)

### Пример скелета (Worker API)
```python
# tests/test_worker_api_smoke.py
import pytest
from httpx import AsyncClient
from bulk_worker_service.app import app

@pytest.mark.anyio
async def test_health_and_metrics():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/api/v1/health")
        assert r.status_code == 200
        m = await ac.get("/api/v1/metrics")
        assert m.status_code == 200
```

### CI рекомендации
- Запуск unit/contract на PR.
- Ночные e2e smoke с ограниченными ресурсами.
- Порог покрытия ≥70% на core‑модулях.
