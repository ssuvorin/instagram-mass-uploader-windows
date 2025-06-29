# Instagram Mass Uploader with Playwright & Dolphin Anty

🚀 **Professional Instagram mass video uploader** with browser automation using Playwright and Dolphin Anty integration.

## ✨ Features

- 📱 **Multi-account support** with Dolphin Anty profiles
- 🎬 **Bulk video upload** with automatic processing
- 🤖 **Human-like behavior** simulation
- 🔐 **2FA support** (Email, Authenticator)
- 🧩 **reCAPTCHA solving** integration
- 🌐 **Proxy support** for each account
- 📊 **Real-time monitoring** and logging
- 🐳 **Docker deployment** ready
- 🪟 **Windows Server optimized**

## 🏗️ Architecture

- **Backend**: Django + Celery
- **Browser Automation**: Playwright + Dolphin Anty
- **Database**: SQLite/PostgreSQL
- **Frontend**: Bootstrap + HTMX
- **Containerization**: Docker + Docker Compose

## 🚀 Quick Start (Windows Server)

### Prerequisites

1. **Windows Server** with Docker Desktop
2. **Dolphin Anty** installed and running
3. **Git** for repository cloning

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/instagram-mass-uploader.git
cd instagram-mass-uploader
```

### 2. Environment Setup

```bash
# Copy Windows environment template
copy windows_deployment.env.example windows_deployment.env

# Edit configuration
notepad windows_deployment.env
```

**Critical settings for Windows:**
```env
# ВАЖНО: Для Docker на Windows используйте host.docker.internal
DOLPHIN_API_HOST=http://host.docker.internal:3001
DOLPHIN_API_TOKEN=your-dolphin-api-token

# Your server settings
ALLOWED_HOSTS=localhost,127.0.0.1,YOUR_WINDOWS_SERVER_IP
SECRET_KEY=your-super-secret-key-change-this

# Optional: reCAPTCHA solving
RUCAPTCHA_API_KEY=your-rucaptcha-api-key
```

### 3. Deploy with Docker

```bash
# Build and start services
docker-compose -f docker-compose.windows.yml up -d

# Check logs
docker-compose -f docker-compose.windows.yml logs -f
```

### 4. Access Dashboard

Open browser: `http://YOUR_SERVER_IP:8000`

## 🐳 Docker Deployment Options

### Option 1: Windows Docker Compose (Recommended)
```bash
docker-compose -f docker-compose.windows.yml up -d
```

### Option 2: PowerShell Automation
```powershell
.\deploy_windows.ps1
```

### Option 3: Manual Docker Build
```bash
docker build -f Dockerfile.windows -t instagram-uploader .
docker run -d -p 8000:8000 --name instagram-app instagram-uploader
```

## 📋 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DOLPHIN_API_HOST` | Dolphin Anty API URL | `http://localhost:3001` | ✅ |
| `DOLPHIN_API_TOKEN` | Dolphin Anty API token | - | ✅ |
| `RUCAPTCHA_API_KEY` | reCAPTCHA solving API key | - | ⚠️ |
| `SECRET_KEY` | Django secret key | - | ✅ |
| `ALLOWED_HOSTS` | Allowed hosts | `localhost` | ✅ |

### Dolphin Anty Setup

1. **Install Dolphin Anty** on Windows host
2. **Create profiles** for each Instagram account
3. **Get API token** from Dolphin settings
4. **Configure proxy** for each profile

### Account Configuration

1. **Add Instagram accounts** in dashboard
2. **Assign Dolphin profiles** to accounts
3. **Configure proxies** (optional)
4. **Test login** for each account

## 🎬 Usage

### 1. Create Bulk Upload Task
```
Dashboard → Bulk Upload → Create New Task
```

### 2. Add Videos and Accounts
- Upload video files
- Add captions/titles
- Select Instagram accounts
- Configure upload settings

### 3. Start Upload Process
```
Task Detail → Start Upload
```

### 4. Monitor Progress
- Real-time logs
- Account status
- Upload statistics
- Error handling

## 🔧 Advanced Configuration

### Custom Delays and Behavior
```python
# uploader/constants.py
TimeConstants.ACCOUNT_DELAY_MIN = 120  # 2 minutes
TimeConstants.ACCOUNT_DELAY_MAX = 300  # 5 minutes
TimeConstants.VIDEO_DELAY_MIN = 300   # 5 minutes
TimeConstants.VIDEO_DELAY_MAX = 900   # 15 minutes
```

### Proxy Configuration
```python
# Support for HTTP/HTTPS/SOCKS5
proxy_format = "protocol://username:password@host:port"
```

### Human Behavior Simulation
```python
# Automatic mouse movements, scrolling, delays
# Randomized typing speeds
# Smart break patterns
# Activity simulation
```

## 🚨 Troubleshooting

### Common Issues

#### ❌ "Connection to Dolphin Anty failed"
**Solution:**
```bash
# Check Dolphin Anty is running on Windows host
# Verify API token is correct
# For Docker: Use host.docker.internal:3001
```

#### ❌ "Phone verification required"
**Solution:**
```bash
# Check account status in dashboard
# Manual verification may be needed
# Account will be marked for manual review
```

#### ❌ "Docker build fails"
**Solution:**
```bash
# Ensure Docker Desktop is running
# Check network connectivity
# Try: docker system prune -a
```

### Logs and Monitoring

```bash
# Docker logs
docker-compose -f docker-compose.windows.yml logs -f

# Application logs
docker exec -it container_name tail -f /app/logs/app.log

# Task-specific logs
Dashboard → Task Detail → View Logs
```

## 🔒 Security

- ✅ **Environment variables** for sensitive data
- ✅ **Secure token handling**
- ✅ **Proxy authentication**
- ✅ **Rate limiting** protection
- ✅ **Account isolation**

## 📊 Monitoring

### Real-time Dashboard
- Account health status
- Upload progress
- Error tracking
- Performance metrics

### Web Interface Features
- Task management
- Account configuration
- Proxy management
- Log viewing
- Statistics

## 🤝 Support

### Architecture Compatibility
- ✅ **Windows Server** (Primary target)
- ✅ **Linux** (Ubuntu, CentOS)
- ✅ **macOS** (Development)
- ✅ **Docker** (All platforms)

### Browser Support
- ✅ **Chromium** (Playwright)
- ✅ **Dolphin Anty** profiles
- ✅ **Headless** mode
- ✅ **Multi-profile** management

## 📝 License

This project is for educational and personal use only. Please comply with Instagram's Terms of Service.

## 🔗 Dependencies

- Django 4.2+
- Playwright 1.35+
- Celery 5.3+
- Docker 20.10+
- Python 3.11+

---

**⚠️ Important**: This tool is designed for legitimate use cases. Always respect Instagram's rate limits and terms of service. 