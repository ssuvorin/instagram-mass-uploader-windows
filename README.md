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

# 🚀 Instagram Mass Uploader - Windows Edition

Professional Instagram mass uploader with Dolphin Anty browser integration, optimized for Windows deployment.

## 🎯 Windows Deployment Features

- ✅ **Docker Windows Support** - Fully optimized for Windows containers
- ✅ **Dolphin Anty Integration** - Works with Windows Dolphin Anty instances  
- ✅ **Automated Database Setup** - SQLite database automatically configured
- ✅ **Resource Optimized** - Memory and CPU limits for stable operation
- ✅ **One-Click Deployment** - Automated setup scripts
- ✅ **Volume Persistence** - Data survives container restarts

## ⚡ Quick Start

### Option 1: Automated Setup (Recommended)
```cmd
restart_clean.cmd
```

### Option 2: Manual Setup
```cmd
docker-compose -f docker-compose.windows.simple.yml up -d
```

## 🔧 Fixed Database Issues

**Previous Issue:** SQLite "unable to open database file" on Windows Docker
**Solution:** Database now stored in Docker volume instead of host mount

### Database Features:
- 📊 **Automatic Creation** - Database created on first startup
- 👤 **Default Admin** - Pre-created superuser (admin/admin123)
- 💾 **Volume Persistence** - Data survives container restarts
- 🔄 **Auto Migrations** - Django migrations run automatically

## 🚨 Troubleshooting

If you encounter issues:

1. **Quick Diagnosis:** `check_status.cmd`
2. **Full Reset:** `restart_clean.cmd`
3. **Detailed Guide:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Common Issues:
- ❌ Database connection errors → Run `restart_clean.cmd`
- ❌ Container won't start → Check port 8000 availability
- ❌ Dolphin Anty not accessible → Verify `DOLPHIN_API_HOST` in `.env`

## 📁 Project Structure

```
instagram-mass-uploader-windows/
├── restart_clean.cmd              # Complete clean restart
├── check_status.cmd               # System diagnostics
├── docker-compose.windows.simple.yml  # Simplified config
├── Dockerfile.windows.simple      # Optimized Dockerfile
├── TROUBLESHOOTING.md             # Detailed troubleshooting
└── windows_deployment.env.example # Environment variables
```

## 🔑 Default Credentials

- **Username:** admin
- **Password:** admin123
- **URL:** http://localhost:8000

⚠️ **Security:** Change default password after first login!

## 🐳 Docker Configuration

### Resource Limits (Windows Optimized):
- **Memory:** 2GB (increase to 4GB for heavy usage)
- **CPU:** 1 core (increase to 2 cores for better performance)
- **Networking:** `host.docker.internal` for Dolphin Anty access

### Volumes:
- `db_data` - Database storage (persistent)
- `./media` - Uploaded media files
- `./logs` - Application logs
- `./static` - Static web files

## 🌐 Network Configuration

### Host Connectivity:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

This allows Docker container to access:
- Dolphin Anty API at `host.docker.internal:3001`
- Windows host services
- Local network resources

## 🎬 Usage Workflow

1. **Start Dolphin Anty** on Windows (port 3001)
2. **Run Application** with `restart_clean.cmd`
3. **Access Interface** at http://localhost:8000
4. **Login** with admin/admin123
5. **Configure Accounts** and start uploading!

## 🔧 Advanced Configuration

### Environment Variables:
```env
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
DOLPHIN_API_HOST=http://host.docker.internal:3001
DOLPHIN_API_TOKEN=your-dolphin-token
RUCAPTCHA_API_KEY=your-captcha-key
DATABASE_PATH=/app/db_data/db.sqlite3
```

### Performance Tuning:
```yaml
# docker-compose.windows.simple.yml
deploy:
  resources:
    limits:
      memory: 4G      # Increase for heavy usage
      cpus: '2'       # Increase for better performance
```

## 🛠️ Maintenance Commands

```cmd
# System status check
check_status.cmd

# View live logs
docker-compose -f docker-compose.windows.simple.yml logs -f

# Access container shell
docker-compose -f docker-compose.windows.simple.yml exec web bash

# Stop application
docker-compose -f docker-compose.windows.simple.yml down

# Complete reset (DANGER: deletes all data)
restart_clean.cmd
```

## 📚 Documentation

- 📋 [Troubleshooting Guide](TROUBLESHOOTING.md)
- 🔧 [Windows Deployment Guide](WINDOWS_DEPLOYMENT.md)
- 🌐 [Original Repository](https://github.com/ssuvorin/playwright_instagram_uploader)

## 🚀 Deployment Options

### Development:
- Use `docker-compose.windows.simple.yml`
- DEBUG=True, local testing

### Production:
- Use `docker-compose.windows.yml`  
- DEBUG=False, Gunicorn server
- Resource monitoring enabled

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Test on Windows environment
4. Submit pull request

## 📞 Support

- 🐛 **Issues:** [GitHub Issues](https://github.com/ssuvorin/instagram-mass-uploader-windows/issues)
- 📖 **Documentation:** See `/docs` folder
- 🔧 **Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## ⚠️ Important Notes

1. **Always backup** your data before major updates
2. **Monitor resource usage** - Instagram automation is resource-intensive
3. **Follow Instagram ToS** - Use responsibly and within rate limits
4. **Security** - Change default passwords and keep tokens secure

---

**Made with ❤️ for Windows deployments** 