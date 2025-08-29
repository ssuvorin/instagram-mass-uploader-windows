# Production Deployment Checklist

## 🚨 Critical Production Issues & Solutions

### 1. Database & State Management

#### Issues:
- **Task locks can become stuck** if workers crash unexpectedly
- **Database connection exhaustion** under high load
- **Race conditions** when multiple workers access same tasks

#### Solutions:
```python
# Add TTL for task locks
class TaskLock(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # TTL field
    
    class Meta:
        indexes = [
            models.Index(fields=['expires_at']),
        ]

# Cleanup expired locks
@periodic_task(run_every=timedelta(minutes=5))
def cleanup_expired_locks():
    TaskLock.objects.filter(expires_at__lt=timezone.now()).delete()

# Atomic task acquisition
from django.db import transaction

@transaction.atomic
def acquire_next_task(task_type):
    return Task.objects.select_for_update(
        skip_locked=True
    ).filter(status='PENDING', task_type=task_type).first()
```

#### Checklist:
- [ ] Implement task lock TTL
- [ ] Add periodic cleanup job
- [ ] Use SELECT FOR UPDATE for task acquisition
- [ ] Configure database connection pooling
- [ ] Set up database monitoring (slow queries, connections)

### 2. Network Communication

#### Issues:
- **Network timeouts** between UI and workers
- **Authentication token expiration** not handled
- **Service discovery failures** in distributed setup

#### Solutions:
```python
# Robust HTTP client with retries
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class RobustHttpClient:
    def __init__(self, base_url, token, timeout=30):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def post(self, url, **kwargs):
        try:
            response = await self.client.post(url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.TimeoutException:
            logger.error(f"Timeout calling {url}")
            raise
        except httpx.ConnectError:
            logger.error(f"Connection error to {url}")
            raise

# Circuit breaker for external services
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
```

#### Checklist:
- [ ] Implement retry logic with exponential backoff
- [ ] Add circuit breaker for external calls
- [ ] Configure connection pooling
- [ ] Set up network monitoring
- [ ] Handle token refresh/rotation

### 3. Resource Management

#### Issues:
- **Browser processes accumulating** if not properly closed
- **Memory leaks** in long-running worker processes  
- **File descriptor exhaustion** from unclosed resources

#### Solutions:
```python
# Context manager for browser automation
class SafeDolphinAutomation:
    def __init__(self):
        self.automation = None
        
    async def __aenter__(self):
        self.automation = DolphinAutomation()
        return self.automation
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.automation:
            try:
                await self.automation.close()
            except Exception as e:
                logger.error(f"Error closing automation: {e}")

# Usage
async def process_account(account):
    async with SafeDolphinAutomation() as automation:
        # Work with automation
        await automation.visit_url(profile_id, url)
        # Automatically cleaned up

# Memory monitoring
import psutil
import gc

class ResourceMonitor:
    def __init__(self, memory_limit_mb=2048):
        self.memory_limit = memory_limit_mb * 1024 * 1024
        
    def check_memory(self):
        process = psutil.Process()
        memory_usage = process.memory_info().rss
        
        if memory_usage > self.memory_limit:
            logger.warning(f"Memory usage {memory_usage/1024/1024:.1f}MB exceeds limit")
            gc.collect()  # Force garbage collection
            return False
        return True
```

#### Checklist:
- [ ] Use context managers for all resources
- [ ] Implement memory monitoring and limits
- [ ] Add graceful shutdown handling
- [ ] Monitor file descriptor usage
- [ ] Set up process restart policies

### 4. Concurrency & Scaling

#### Issues:
- **Race conditions** in task assignment
- **Worker overloading** without proper queuing
- **Uneven task distribution** across workers

#### Solutions:
```python
# Distributed task queue with Redis
import redis
import json
from datetime import datetime

class DistributedTaskQueue:
    def __init__(self, redis_url):
        self.redis = redis.from_url(redis_url)
        
    async def enqueue_task(self, task_type, task_id, priority=0):
        task_data = {
            'task_type': task_type,
            'task_id': task_id,
            'enqueued_at': datetime.utcnow().isoformat(),
            'priority': priority
        }
        
        # Use sorted set for priority queuing
        score = priority * -1  # Higher priority = lower score
        await self.redis.zadd(
            f"queue:{task_type}", 
            {json.dumps(task_data): score}
        )
    
    async def dequeue_task(self, task_type, worker_id):
        # Atomic dequeue with worker assignment
        pipe = self.redis.pipeline()
        task_key = f"queue:{task_type}"
        processing_key = f"processing:{worker_id}"
        
        # Pop highest priority task
        task_data = await self.redis.zpopmin(task_key)
        if task_data:
            # Assign to worker for tracking
            await self.redis.setex(
                f"{processing_key}:{task_data[0]}", 
                3600,  # 1 hour TTL
                task_data[0]
            )
            return json.loads(task_data[0])
        return None

# Load balancing for workers
class WorkerLoadBalancer:
    def __init__(self):
        self.worker_loads = {}  # worker_id -> current_task_count
        
    def get_least_loaded_worker(self):
        if not self.worker_loads:
            return None
        return min(self.worker_loads.items(), key=lambda x: x[1])[0]
        
    def assign_task(self, worker_id):
        self.worker_loads[worker_id] = self.worker_loads.get(worker_id, 0) + 1
        
    def complete_task(self, worker_id):
        if worker_id in self.worker_loads:
            self.worker_loads[worker_id] = max(0, self.worker_loads[worker_id] - 1)
```

#### Checklist:
- [ ] Implement distributed task queue (Redis/RabbitMQ)
- [ ] Add worker load balancing
- [ ] Configure task prioritization
- [ ] Set worker capacity limits
- [ ] Monitor queue depths and processing times

### 5. Configuration Management

#### Issues:
- **Configuration drift** between environments
- **Sensitive data exposure** in config files
- **Hard to update** configuration in running services

#### Solutions:
```python
# Centralized configuration with validation
from pydantic import BaseSettings, validator
from typing import Optional

class ProductionSettings(BaseSettings):
    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Security
    secret_key: str
    api_token: str
    allowed_hosts: list[str]
    
    # Worker configuration
    worker_capacity: int = 5
    worker_timeout: int = 300
    heartbeat_interval: int = 30
    
    # Resource limits
    max_memory_mb: int = 2048
    max_concurrent_tasks: int = 3
    
    @validator('database_url')
    def validate_database_url(cls, v):
        if not v.startswith(('postgresql://', 'postgres://')):
            raise ValueError('Database URL must be PostgreSQL')
        return v
    
    @validator('worker_capacity')
    def validate_worker_capacity(cls, v):
        if v < 1 or v > 20:
            raise ValueError('Worker capacity must be between 1 and 20')
        return v
    
    class Config:
        env_file = '.env'
        case_sensitive = False

# Configuration validation on startup
def validate_production_config():
    try:
        settings = ProductionSettings()
        logger.info("Configuration validated successfully")
        return settings
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise SystemExit(1)
```

#### Checklist:
- [ ] Use environment-specific configurations
- [ ] Validate all configuration on startup
- [ ] Store secrets in secure vault (HashiCorp Vault)
- [ ] Implement configuration hot-reload
- [ ] Version control configuration schemas

## 🔍 Monitoring & Observability

### Essential Metrics

```python
# Application metrics
from prometheus_client import Counter, Histogram, Gauge

TASK_COUNTER = Counter('tasks_total', 'Total tasks processed', ['task_type', 'status'])
TASK_DURATION = Histogram('task_duration_seconds', 'Task processing time', ['task_type'])
ACTIVE_WORKERS = Gauge('active_workers', 'Number of active workers')
QUEUE_SIZE = Gauge('queue_size', 'Number of pending tasks', ['task_type'])

# Health check endpoint
@app.get("/health")
async def health_check():
    checks = {
        'database': await check_database_connection(),
        'redis': await check_redis_connection(),
        'memory': check_memory_usage(),
        'disk': check_disk_space(),
    }
    
    healthy = all(checks.values())
    status_code = 200 if healthy else 503
    
    return Response(
        content=json.dumps({
            'status': 'healthy' if healthy else 'unhealthy',
            'checks': checks,
            'timestamp': datetime.utcnow().isoformat()
        }),
        status_code=status_code,
        media_type='application/json'
    )
```

### Checklist:
- [ ] Set up application metrics (Prometheus)
- [ ] Configure log aggregation (ELK stack)
- [ ] Implement distributed tracing (Jaeger)
- [ ] Add alerting rules (PagerDuty/Slack)
- [ ] Monitor business metrics (task success rates)

## 🚀 Deployment Strategy

### Blue-Green Deployment
```bash
# Zero-downtime deployment script
#!/bin/bash

BLUE_PORT=8088
GREEN_PORT=8089
HEALTH_ENDPOINT="/api/v1/health"

deploy_green() {
    echo "Starting green deployment..."
    docker run -d --name worker-green -p $GREEN_PORT:8088 worker:latest
    
    # Wait for health check
    for i in {1..30}; do
        if curl -f http://localhost:$GREEN_PORT$HEALTH_ENDPOINT; then
            echo "Green deployment healthy"
            return 0
        fi
        sleep 2
    done
    
    echo "Green deployment failed health check"
    return 1
}

switch_traffic() {
    echo "Switching traffic to green..."
    # Update load balancer config
    # Stop blue deployment
    docker stop worker-blue
    docker rm worker-blue
    docker rename worker-green worker-blue
}
```

### Checklist:
- [ ] Implement blue-green deployment
- [ ] Test rollback procedures
- [ ] Configure load balancer health checks
- [ ] Set up automated deployment pipeline
- [ ] Test disaster recovery procedures

## 📋 Pre-Production Testing

### Load Testing
```python
# Load test script
import asyncio
import httpx
import time

async def load_test():
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(100):  # 100 concurrent requests
            task = client.post(
                "http://localhost:8088/api/v1/bulk-upload/start",
                params={"task_id": i},
                timeout=30
            )
            tasks.append(task)
        
        start_time = time.time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        success_count = sum(1 for r in responses if not isinstance(r, Exception))
        print(f"Load test: {success_count}/{len(tasks)} successful in {duration:.2f}s")

if __name__ == "__main__":
    asyncio.run(load_test())
```

### Checklist:
- [ ] Load test all API endpoints
- [ ] Test worker failover scenarios
- [ ] Validate database performance under load
- [ ] Test network partition recovery
- [ ] Verify monitoring and alerting works

## 🔒 Security Considerations

### API Security
```python
# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/bulk-upload/start")
@limiter.limit("5/minute")  # Max 5 requests per minute
async def start_bulk_upload(request: Request, task_id: int):
    # Implementation
    pass

# Input validation
from pydantic import BaseModel, validator

class TaskRequest(BaseModel):
    task_id: int
    options: Optional[dict] = None
    
    @validator('task_id')
    def validate_task_id(cls, v):
        if v <= 0:
            raise ValueError('Task ID must be positive')
        return v
```

### Checklist:
- [ ] Implement rate limiting
- [ ] Add input validation and sanitization
- [ ] Use HTTPS in production
- [ ] Rotate API tokens regularly
- [ ] Audit API access logs
- [ ] Implement proper CORS policies

This checklist covers the major production deployment pitfalls and provides concrete solutions for each issue.