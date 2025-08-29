# Web UI Service - Distributed Architecture

## 🎯 Overview

This UI module provides a **complete web interface** for the Instagram Uploader system using **API-based communication** instead of direct database access. It's designed for **distributed architecture** where the UI is decoupled from backend services.

## 🏗️ Architecture

### **Before (Monolithic):**
```
UI Module → Direct Django ORM → Database
```

### **After (Distributed):**
```
UI Module → HTTP API → Backend Services → Database
                 ↓
            Management API (8089)
            Worker API (8088)
            Monitoring API (8090)
```

## 📁 Structure

```
web_ui_service/
├── ui_core/                 # Main UI functionality via API
│   ├── api_client.py       # API communication layer
│   ├── views.py            # API-based views
│   └── urls.py             # URL patterns
├── dashboard/              # Production monitoring
│   ├── monitoring_views.py # System monitoring
│   └── templates/          # Monitoring templates
├── templates/              # All UI templates (copied from main project)
├── static/                 # All static files (CSS, JS, images)
└── remote_ui/              # Django settings
    ├── settings.py         # API-based configuration
    └── urls.py             # Main URL routing
```

## 🔧 Setup

### 1. **Copy Templates and Static Files**
```bash
# Templates and static files are automatically copied from main project
cp -r ../../uploader/templates ./
cp -r ../../uploader/static ./
```

### 2. **Configure API Services**
```bash
cp .env.example .env
# Edit .env with your API endpoints and tokens
```

### 3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 4. **Run UI Service**
```bash
python manage.py runserver 8000
```

## 🌐 API Communication

### **Service Endpoints:**
- **Management API** (8089): CRUD operations (accounts, tasks, proxies)
- **Worker API** (8088): Task execution, status updates
- **Monitoring API** (8090): Real-time monitoring, metrics

### **API Client Usage:**
```python
from ui_core.api_client import management_api, worker_api

# Get accounts
accounts = management_api.get_accounts()

# Start task  
result = worker_api.start_bulk_task(task_id)

# Check status
status = worker_api.get_task_status(task_id)
```

## 📱 Available Pages

### **Core Application:**
- `/` - Dashboard
- `/accounts/` - Account management
- `/bulk-upload/` - Bulk upload tasks
- `/avatars/` - Avatar tasks
- `/warmup/` - Warmup tasks
- `/bio/` - Bio link tasks
- `/follow/` - Follow tasks

### **Production Monitoring:**
- `/monitoring/` - System monitoring dashboard
- `/monitoring/errors/` - Error logs with server IPs
- `/monitoring/performance/` - Performance metrics
- `/monitoring/worker/<id>/` - Worker details

## 🔐 Authentication

API communication uses **Bearer tokens**:

```bash
# Environment variables
API_TOKEN_MANAGEMENT=your-management-token
API_TOKEN_WORKER=your-worker-token  
API_TOKEN_MONITORING=your-monitoring-token
```

## 🎨 Templates

### **Template Inheritance:**
- All original templates are **preserved**
- Enhanced with **API error handling**
- Added **connection status indicators**
- Improved **loading states**

### **Key Enhancements:**
```html
<!-- API Status Indicator -->
<div id="apiStatus" class="api-status">
    <i class="bi bi-wifi"></i> API Online
</div>

<!-- Enhanced Error Display -->
{% if 'API' in message.message %}
    <i class="bi bi-wifi-off"></i> {{ message }}
{% endif %}
```

## ⚡ Features

### **✅ Advantages:**
1. **Complete Decoupling** - No direct database dependencies
2. **Scalable Architecture** - UI can be deployed separately
3. **API-First Design** - All functionality via REST APIs
4. **Production Monitoring** - Real-time system monitoring with server IPs
5. **Error Resilience** - Graceful API failure handling
6. **Same UI Experience** - All original templates preserved

### **🔧 API Error Handling:**
- Connection failure detection
- Automatic retry for transient errors
- User-friendly error messages
- Fallback UI states

## 📊 Monitoring Integration

The UI includes comprehensive **production monitoring**:

- **Server IP Tracking** - See which server has issues
- **Real-time Metrics** - CPU, memory, task status
- **Error Logs** - Filterable by server, worker, error type
- **SSH Access** - Direct troubleshooting commands

## 🚀 Deployment

### **Development:**
```bash
python manage.py runserver 8000
```

### **Production:**
```bash
gunicorn remote_ui.wsgi:application --bind 0.0.0.0:8000
```

### **Docker (Optional):**
```dockerfile
FROM python:3.11
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["gunicorn", "remote_ui.wsgi:application"]
```

## 🔄 Migration Guide

### **From Monolithic to Distributed:**

1. **Templates** ✅ - Automatically copied and enhanced
2. **Static Files** ✅ - Copied with API status indicators
3. **Views** ✅ - Converted to use API calls
4. **Models** ✅ - Replaced with API client calls
5. **Forms** ✅ - Enhanced with API error handling

### **What Changed:**
- Django ORM calls → API HTTP requests
- Direct model access → API client methods
- Local database → Remote API services
- Form validation → API response handling

### **What Stayed The Same:**
- All URL patterns preserved
- Template structure unchanged
- User interface identical
- Navigation and features complete

This architecture ensures **complete functionality** while enabling **distributed deployment** and **horizontal scaling**.