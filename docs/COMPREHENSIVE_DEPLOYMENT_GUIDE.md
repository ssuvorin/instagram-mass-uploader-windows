# Comprehensive Deployment Guide: 5 Workers + Web Interface

## TikTok Functionality Coverage Analysis

### ❌ **TikTok Functionality is NOT covered by Worker API**

Based on my analysis of the codebase:

#### **Current TikTok Implementation:**
- **UI Only**: TikTok functionality exists only as web interface (`/tiktok/booster/`)
- **External API Calls**: TikTok features call external FastAPI servers (not integrated with workers)
- **Separate System**: TikTok automation runs independently from Instagram worker architecture

#### **TikTok Features Available:**
```bash
# TikTok UI Endpoints (Web Only)
GET  /tiktok/booster/                    # TikTok dashboard UI
POST /api/tiktok/upload/videos/          # Upload video files  
POST /api/tiktok/upload/accounts/        # Upload accounts file
POST /api/tiktok/prepare-booster-accounts/ # Prepare booster accounts
POST /api/tiktok/start-booster/          # Start account boosting
```

#### **Missing from Worker Architecture:**
- ❌ No TikTok task runners in `bulk_worker_service`
- ❌ No TikTok domain models in worker system
- ❌ No TikTok API integration in distributed architecture
- ❌ TikTok calls external APIs instead of worker endpoints

### **Recommendation for TikTok Integration:**

To integrate TikTok into the distributed worker architecture, you would need:

1. **Create TikTok Task Runner:**
```python
class TikTokTaskRunner(BaseTaskRunner):
    @property 
    def task_type(self) -> str:
        return "tiktok_upload"
    
    async def _execute_task(self, ui_client, task_id, options):
        # TikTok automation implementation
        pass
```

2. **Add TikTok API Endpoints:**
```python
@app.post("/api/v1/tiktok/start", response_model=StartResponse)
async def start_tiktok_task(task_id: int):
    # TikTok worker endpoint
    pass
```

---

## Dual Runner Architecture Explanation

### **Why Two Orchestrators?**

The system has **two orchestrator implementations** for different architectural approaches:

#### **1. Legacy Orchestrator** (`orchestrator.py`)
- **Purpose**: Backward compatibility and monolithic approach
- **Pattern**: Direct implementation with specific methods per task type
- **Usage**: Maintains existing API contracts

```python
# Legacy approach - specific methods
async def start_warmup_pull(self, task_id: int) -> str:
    # Direct implementation
    
async def start_avatar_pull(self, task_id: int) -> str:
    # Direct implementation
```

#### **2. Clean Architecture Orchestrator** (`orchestrator_v2.py`)
- **Purpose**: Modern clean architecture following SOLID principles
- **Pattern**: Generic task handling with dependency injection
- **Usage**: New implementations and extensions

```python
# Clean architecture - generic approach
async def start_task(self, task_type: str, task_id: int, options: StartOptions) -> str:
    runner = self._task_runner_factory.create_runner(task_type)
    return await self._execute_job(job_id, task_type, task_id, runner, options)
```

### **Current Usage in app.py:**

```python
# app.py uses BOTH orchestrators
_orchestrator = BulkUploadOrchestrator()          # Legacy
_orchestrator_v2 = get_orchestrator()             # Clean Architecture

# Legacy endpoints use old orchestrator
@app.post("/api/v1/bulk-tasks/start")
async def start_bulk_task(req: StartRequest):
    return await _orchestrator.start_pull(task_id=req.task_id)

# New endpoints use clean orchestrator  
@app.post("/api/v1/warmup/start")
async def start_warmup(task_id: int):
    return await _orchestrator_v2.start_warmup(task_id)
```

### **Migration Strategy:**

1. **Phase 1**: Both orchestrators coexist (current state)
2. **Phase 2**: Gradually migrate endpoints to clean architecture
3. **Phase 3**: Remove legacy orchestrator
4. **Phase 4**: Full clean architecture

---

## Deployment Architecture: 5 Workers + 1 Web Interface

### **Target Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                    Production Deployment                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI Server │    │  Worker Node 1  │    │  Worker Node 2  │
│   (Django)      │    │   (FastAPI)     │    │   (FastAPI)     │
│   Port: 8000    │    │   Port: 8088    │    │   Port: 8088    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐    ┌─────────────────┐
         │              │  Worker Node 3  │    │  Worker Node 4  │
         │              │   (FastAPI)     │    │   (FastAPI)     │
         │              │   Port: 8088    │    │   Port: 8088    │
         │              └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────│  Worker Node 5  │──────────────┘
                        │   (FastAPI)     │
                        │   Port: 8088    │
                        └─────────────────┘
                                 │
                   ┌─────────────────────────┐
                   │    PostgreSQL DB        │
                   │      Port: 5432         │
                   └─────────────────────────┘
```

---

## Required Files and Folders Structure

### **Server 1: Web UI (Django)**

```bash
# Server 1: Web Interface
/opt/instagram-automation/
├── .env                              # Main environment config
├── manage.py                         # Django management
├── requirements.txt                  # Python dependencies
├── instagram_uploader/               # Django project
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── uploader/                         # Main Django app
│   ├── models.py                     # Database models
│   ├── views.py                      # Web views
│   ├── urls.py                       # URL routing
│   ├── templates/                    # HTML templates
│   ├── static/                       # CSS/JS files
│   └── migrations/                   # Database migrations
├── modules/web_ui_service/           # Web UI microservice
│   ├── dashboard/                    # Dashboard app
│   │   ├── api_views.py             # API endpoints for workers
│   │   ├── models.py                # Worker management models
│   │   └── views.py                 # Worker management views
│   ├── remote_ui/                   # Remote UI settings
│   └── manage.py
└── instgrapi_func/                  # Instagram API functions
    ├── services/                    # Business logic services
    └── *.py                        # Instagram automation
```

### **Servers 2-6: Workers (FastAPI)**

```bash
# Servers 2-6: Worker Nodes
/opt/instagram-worker/
├── .env                             # Worker-specific config
├── requirements.txt                 # Python dependencies
├── modules/bulk_worker_service/     # Worker microservice
│   ├── bulk_worker_service/
│   │   ├── app.py                  # FastAPI application
│   │   ├── orchestrator_v2.py      # Clean architecture orchestrator
│   │   ├── interfaces.py           # SOLID interfaces
│   │   ├── services.py             # Business logic services
│   │   ├── factories.py            # Task runner factories
│   │   ├── exceptions.py           # Error handling
│   │   ├── container.py            # Dependency injection
│   │   ├── domain.py               # Domain models
│   │   ├── config.py               # Configuration
│   │   ├── ui_client.py            # UI communication
│   │   └── runners/                # Task runners
│   │       ├── warmup_runner.py
│   │       ├── avatar_runner.py
│   │       ├── bio_runner.py
│   │       ├── follow_runner.py
│   │       ├── proxy_diag_runner.py
│   │       ├── media_uniq_runner.py
│   │       └── cookie_robot_runner.py
│   ├── requirements.txt
│   └── start_server.sh
├── uploader/                        # Shared Instagram logic
│   ├── async_impl/                  # Async automation
│   └── models.py                    # Model definitions (read-only)
├── instgrapi_func/                  # Instagram API functions
└── bot/                            # Automation scripts
    └── src/
```

---

## Step-by-Step Deployment Instructions

### **Prerequisites:**

1. **6 Servers** (1 Web UI + 5 Workers)
2. **PostgreSQL Database** (can be on Web UI server or separate)
3. **Python 3.11+** on all servers
4. **Network connectivity** between all servers

### **Step 1: Database Setup**

```bash
# On database server (or Web UI server)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
```

```sql
CREATE ROLE iguploader WITH LOGIN PASSWORD 'your_strong_password';
CREATE DATABASE iguploader WITH OWNER iguploader ENCODING 'UTF8';
GRANT ALL PRIVILEGES ON DATABASE iguploader TO iguploader;
\q
```

### **Step 2: Web UI Server Setup (Server 1)**

#### **2.1: Deploy Code**
```bash
# Clone repository
cd /opt
git clone https://github.com/your-repo/playwright_instagram_uploader.git instagram-automation
cd instagram-automation

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### **2.2: Configure Environment**
```bash
# Create .env file
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://iguploader:your_strong_password@localhost:5432/iguploader

# Django Settings
SECRET_KEY=your_very_long_random_secret_key_here
DEBUG=False
ALLOWED_HOSTS=your-web-server.com,localhost,127.0.0.1

# Worker Configuration
WORKER_API_TOKEN=worker_api_token_very_secure_here
WORKER_POOL=http://worker1.com:8088,http://worker2.com:8088,http://worker3.com:8088,http://worker4.com:8088,http://worker5.com:8088

# Worker Distribution Settings
DISPATCH_BATCH_SIZE=5
DISPATCH_CONCURRENCY=2

# Worker Health Monitoring
WORKER_ALLOWED_IPS=worker1-ip,worker2-ip,worker3-ip,worker4-ip,worker5-ip
EOF
```

#### **2.3: Database Migration**
```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

#### **2.4: Start Web Service**
```bash
# Production deployment with gunicorn
pip install gunicorn
gunicorn instagram_uploader.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### **Step 3: Worker Servers Setup (Servers 2-6)**

#### **3.1: Deploy Worker Code**
```bash
# On each worker server
cd /opt
git clone https://github.com/your-repo/playwright_instagram_uploader.git instagram-worker
cd instagram-worker

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r modules/bulk_worker_service/requirements.txt

# Install Playwright browsers
python -m playwright install
```

#### **3.2: Configure Worker Environment**
```bash
# Create worker-specific .env (adapt for each worker)
cat > .env << 'EOF'
# UI Communication
UI_API_BASE=http://your-web-server.com:8000
UI_API_TOKEN=worker_api_token_very_secure_here

# Worker Identity
WORKER_BASE_URL=http://this-worker-server.com:8088
WORKER_NAME=Worker Node 1
WORKER_CAPACITY=4

# Task Configuration
CONCURRENCY_LIMIT=4
BATCH_SIZE=2
HEADLESS=true
UPLOAD_METHOD=playwright

# Database (read-only access)
DATABASE_URL=postgresql://iguploader:your_strong_password@db-server:5432/iguploader

# Dolphin Browser (optional)
DOLPHIN_API_TOKEN=your_dolphin_token
DOLPHIN_API_HOST=http://dolphin-host:3001

# Request Settings
REQUEST_TIMEOUT_SECS=30
HEARTBEAT_INTERVAL_SECS=30
VERIFY_SSL=true
EOF
```

#### **3.3: Start Worker Service**
```bash
# Production deployment with uvicorn
cd modules/bulk_worker_service
pip install uvicorn[standard]
uvicorn bulk_worker_service.app:app --host 0.0.0.0 --port 8088 --workers 1
```

### **Step 4: Systemd Service Configuration**

#### **4.1: Web UI Service**
```bash
# Create systemd service for Web UI
sudo cat > /etc/systemd/system/instagram-web.service << 'EOF'
[Unit]
Description=Instagram Automation Web UI
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/instagram-automation
Environment=PATH=/opt/instagram-automation/venv/bin
EnvironmentFile=/opt/instagram-automation/.env
ExecStart=/opt/instagram-automation/venv/bin/gunicorn instagram_uploader.wsgi:application --bind 0.0.0.0:8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable instagram-web
sudo systemctl start instagram-web
sudo systemctl status instagram-web
```

#### **4.2: Worker Services**
```bash
# Create systemd service for each worker (adapt server names)
sudo cat > /etc/systemd/system/instagram-worker.service << 'EOF'
[Unit]
Description=Instagram Automation Worker
After=network.target

[Service]
Type=simple
User=worker
Group=worker
WorkingDirectory=/opt/instagram-worker/modules/bulk_worker_service
Environment=PATH=/opt/instagram-worker/venv/bin
EnvironmentFile=/opt/instagram-worker/.env
ExecStart=/opt/instagram-worker/venv/bin/uvicorn bulk_worker_service.app:app --host 0.0.0.0 --port 8088 --workers 1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable instagram-worker
sudo systemctl start instagram-worker
sudo systemctl status instagram-worker
```

### **Step 5: Load Balancer Configuration (Optional)**

#### **5.1: Nginx Load Balancer for Workers**
```nginx
# /etc/nginx/sites-available/instagram-workers
upstream instagram_workers {
    server worker1.com:8088 max_fails=3 fail_timeout=30s;
    server worker2.com:8088 max_fails=3 fail_timeout=30s;
    server worker3.com:8088 max_fails=3 fail_timeout=30s;
    server worker4.com:8088 max_fails=3 fail_timeout=30s;
    server worker5.com:8088 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name workers.instagram-automation.com;

    location / {
        proxy_pass http://instagram_workers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### **5.2: Web UI Nginx Configuration**
```nginx
# /etc/nginx/sites-available/instagram-web
server {
    listen 80;
    server_name instagram-automation.com;

    client_max_body_size 100M;

    location /static/ {
        alias /opt/instagram-automation/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /opt/instagram-automation/media/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

---

## Scaling and Monitoring

### **Worker Distribution Strategy:**

#### **Automatic Task Distribution:**
The Web UI automatically distributes tasks across workers using:

1. **Round-robin assignment** based on worker capacity
2. **Batch splitting** for large tasks
3. **Health monitoring** with automatic failover
4. **Load balancing** based on worker metrics

#### **Manual Worker Management:**
```bash
# Check worker status
curl http://worker1.com:8088/api/v1/health

# View worker metrics
curl http://worker1.com:8088/api/v1/metrics

# List active jobs
curl http://worker1.com:8088/api/v1/jobs
```

### **Monitoring Commands:**

#### **Web UI Health:**
```bash
# Check web service
systemctl status instagram-web
journalctl -u instagram-web -f

# Check database connections
python manage.py dbshell
```

#### **Worker Health:**
```bash
# Check worker service
systemctl status instagram-worker
journalctl -u instagram-worker -f

# Monitor worker logs
tail -f /var/log/instagram-worker.log
```

### **Scaling Operations:**

#### **Add New Worker:**
1. Deploy worker code to new server
2. Configure environment variables
3. Add to `WORKER_POOL` in Web UI
4. Start worker service
5. Verify registration in Web UI

#### **Remove Worker:**
1. Stop accepting new tasks
2. Wait for current tasks to complete
3. Remove from `WORKER_POOL`
4. Stop worker service

#### **Database Scaling:**
- **Read Replicas**: Configure read-only database replicas for workers
- **Connection Pooling**: Use pgbouncer for connection management
- **Partitioning**: Partition large tables by date/account

---

## Security Considerations

### **Network Security:**
- **Firewall Rules**: Only allow required ports between servers
- **VPN/Private Network**: Deploy all servers in private network
- **SSL/TLS**: Use HTTPS for all communications

### **API Security:**
- **Token Authentication**: Strong API tokens for worker communication
- **IP Restrictions**: Limit worker API access by IP address
- **Rate Limiting**: Implement rate limits on API endpoints

### **Data Security:**
- **Database Encryption**: Enable PostgreSQL encryption at rest
- **Backup Encryption**: Encrypt database backups
- **Credential Management**: Use environment variables for all secrets

---

## Troubleshooting Guide

### **Common Issues:**

#### **Worker Registration Failed:**
```bash
# Check network connectivity
curl http://web-ui-server:8000/api/worker/register

# Verify API token
echo $UI_API_TOKEN

# Check worker logs
journalctl -u instagram-worker -n 100
```

#### **Task Distribution Not Working:**
```bash
# Check worker pool configuration
echo $WORKER_POOL

# Verify worker health
curl http://worker1.com:8088/api/v1/health

# Check Web UI logs
journalctl -u instagram-web -n 100
```

#### **Database Connection Issues:**
```bash
# Test database connection
psql "postgresql://iguploader:password@db-server:5432/iguploader" -c "SELECT 1;"

# Check database logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### **Performance Optimization:**

1. **Database Tuning**: Optimize PostgreSQL configuration
2. **Worker Sizing**: Adjust worker capacity based on server resources
3. **Batch Sizing**: Tune batch sizes for optimal throughput
4. **Caching**: Implement Redis caching for frequent operations

---

## Deployment Checklist

### **Pre-Deployment:**
- [ ] 6 servers provisioned and accessible
- [ ] Database server configured
- [ ] Domain names/IP addresses assigned
- [ ] SSL certificates obtained (if using HTTPS)
- [ ] Firewall rules configured

### **Deployment:**
- [ ] Web UI deployed and running
- [ ] Database migrated successfully
- [ ] All 5 workers deployed and registered
- [ ] Load balancer configured (if used)
- [ ] Monitoring systems enabled
- [ ] Systemd services enabled and started

### **Post-Deployment:**
- [ ] End-to-end task execution tested
- [ ] Worker failover tested
- [ ] Database backup configured
- [ ] Log rotation configured
- [ ] Alerting systems configured
- [ ] Documentation updated

This comprehensive deployment guide provides everything needed to scale your Instagram automation platform to 5 workers with full distributed operation! 🚀