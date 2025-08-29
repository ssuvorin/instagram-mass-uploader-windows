#!/bin/bash

# Production Deployment Script for Instagram Automation System
# Optimized for environments where Dolphin Anty cannot run in Docker

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/pids"
VENV_DIR="$PROJECT_ROOT/venv"

# Default configuration
WORKERS_COUNT=5
WEB_UI_PORT=8000
WORKER_BASE_PORT=8088
DB_HOST="localhost"
DB_PORT=5432
DB_NAME="iguploader"
DB_USER="iguploader"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    mkdir -p "$LOG_DIR" "$PID_DIR" "$PROJECT_ROOT/temp" "$PROJECT_ROOT/media"
    
    # Set appropriate permissions
    chmod 755 "$LOG_DIR" "$PID_DIR"
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$python_version < 3.8" | bc -l) -eq 1 ]]; then
        log_error "Python 3.8+ is required, found $python_version"
        exit 1
    fi
    
    log_info "Python version: $python_version ✓"
    
    # Check PostgreSQL
    if ! command -v psql &> /dev/null; then
        log_warn "PostgreSQL client not found. Please ensure PostgreSQL is accessible."
    else
        log_info "PostgreSQL client found ✓"
    fi
    
    # Check if Dolphin Anty is running
    if ! curl -s "http://localhost:3001/v1.0/browser_profiles" &> /dev/null; then
        log_warn "Dolphin Anty API not accessible at localhost:3001"
        log_warn "Please ensure Dolphin Anty is running and API is enabled"
    else
        log_info "Dolphin Anty API accessible ✓"
    fi
}

# Setup Python virtual environment
setup_virtualenv() {
    log_info "Setting up Python virtual environment..."
    
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        log_info "Created virtual environment"
    fi
    
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    log_info "Installing dependencies..."
    
    # Web UI dependencies
    if [ -f "$PROJECT_ROOT/modules/web_ui_service/requirements.txt" ]; then
        pip install -r "$PROJECT_ROOT/modules/web_ui_service/requirements.txt"
    fi
    
    # Worker service dependencies
    if [ -f "$PROJECT_ROOT/modules/bulk_worker_service/requirements.txt" ]; then
        pip install -r "$PROJECT_ROOT/modules/bulk_worker_service/requirements.txt"
    fi
    
    # Production dependencies
    pip install gunicorn uvicorn[standard] psutil redis
    
    log_info "Dependencies installed ✓"
}

# Setup database
setup_database() {
    log_info "Setting up database..."
    
    # Check if database exists
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
        log_info "Database connection successful ✓"
    else
        log_error "Cannot connect to database. Please ensure PostgreSQL is running and credentials are correct."
        exit 1
    fi
    
    # Run migrations
    source "$VENV_DIR/bin/activate"
    cd "$PROJECT_ROOT/modules/web_ui_service"
    python manage.py migrate
    
    # Create superuser if not exists
    python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF
    
    log_info "Database setup complete ✓"
}

# Generate configuration files
generate_configs() {
    log_info "Generating configuration files..."
    
    # Generate .env file if not exists
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        cat > "$PROJECT_ROOT/.env" << EOF
# Database Configuration
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME

# Django Configuration
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Worker Configuration
WORKER_API_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
UI_API_BASE=http://localhost:$WEB_UI_PORT
HEARTBEAT_INTERVAL_SECS=30

# Resource Limits
MAX_CONCURRENT_TASKS=3
MEMORY_LIMIT_MB=2048
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=True

# Dolphin Configuration
DOLPHIN_API_HOST=http://localhost:3001

# Performance Settings
DB_MIN_CONNECTIONS=5
DB_MAX_CONNECTIONS=20
EOF
        log_info "Generated .env file"
    else
        log_info ".env file already exists"
    fi
    
    # Generate nginx configuration
    cat > "$PROJECT_ROOT/nginx.conf" << EOF
upstream web_backend {
    server 127.0.0.1:$WEB_UI_PORT;
}

upstream worker_backend {
    least_conn;
EOF

    for ((i=1; i<=WORKERS_COUNT; i++)); do
        port=$((WORKER_BASE_PORT + i - 1))
        echo "    server 127.0.0.1:$port;" >> "$PROJECT_ROOT/nginx.conf"
    done

    cat >> "$PROJECT_ROOT/nginx.conf" << EOF
}

server {
    listen 80;
    server_name localhost;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://web_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /api/worker/ {
        proxy_pass http://worker_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /static/ {
        alias $PROJECT_ROOT/modules/web_ui_service/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias $PROJECT_ROOT/media/;
        expires 7d;
    }
}
EOF
    
    log_info "Generated nginx configuration"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    source "$VENV_DIR/bin/activate"
    
    # Start Web UI
    log_info "Starting Web UI service..."
    cd "$PROJECT_ROOT/modules/web_ui_service"
    nohup gunicorn \
        --bind 0.0.0.0:$WEB_UI_PORT \
        --workers 4 \
        --worker-class gthread \
        --threads 2 \
        --worker-connections 1000 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --timeout 30 \
        --keep-alive 2 \
        --pid "$PID_DIR/web_ui.pid" \
        --access-logfile "$LOG_DIR/web_ui_access.log" \
        --error-logfile "$LOG_DIR/web_ui_error.log" \
        --log-level info \
        web_ui_service.wsgi:application \
        > "$LOG_DIR/web_ui.log" 2>&1 &
    
    sleep 3
    
    # Check if Web UI started successfully
    if curl -f "http://localhost:$WEB_UI_PORT/health/" &> /dev/null; then
        log_info "Web UI service started ✓"
    else
        log_error "Web UI service failed to start"
        exit 1
    fi
    
    # Start Worker services
    for ((i=1; i<=WORKERS_COUNT; i++)); do
        worker_port=$((WORKER_BASE_PORT + i - 1))
        worker_name="worker_$i"
        
        log_info "Starting $worker_name on port $worker_port..."
        
        cd "$PROJECT_ROOT/modules/bulk_worker_service"
        nohup uvicorn \
            bulk_worker_service.app:app \
            --host 0.0.0.0 \
            --port $worker_port \
            --workers 1 \
            --loop uvloop \
            --log-level info \
            --access-log \
            --env-file "$PROJECT_ROOT/.env" \
            > "$LOG_DIR/$worker_name.log" 2>&1 &
        
        echo $! > "$PID_DIR/$worker_name.pid"
        
        # Set environment variables for this worker
        export WORKER_BASE_URL="http://localhost:$worker_port"
        export WORKER_NAME="$worker_name"
        
        sleep 2
        
        # Check if worker started successfully
        if curl -f "http://localhost:$worker_port/api/v1/health/simple" &> /dev/null; then
            log_info "$worker_name started ✓"
        else
            log_warn "$worker_name may have failed to start (check logs)"
        fi
    done
}

# Stop services
stop_services() {
    log_info "Stopping services..."
    
    # Stop workers
    for ((i=1; i<=WORKERS_COUNT; i++)); do
        worker_name="worker_$i"
        pid_file="$PID_DIR/$worker_name.pid"
        
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                log_info "Stopping $worker_name (PID: $pid)..."
                kill -TERM "$pid"
                
                # Wait for graceful shutdown
                for j in {1..30}; do
                    if ! kill -0 "$pid" 2>/dev/null; then
                        break
                    fi
                    sleep 1
                done
                
                # Force kill if still running
                if kill -0 "$pid" 2>/dev/null; then
                    log_warn "Force killing $worker_name..."
                    kill -KILL "$pid"
                fi
            fi
            rm -f "$pid_file"
        fi
    done
    
    # Stop Web UI
    if [ -f "$PID_DIR/web_ui.pid" ]; then
        pid=$(cat "$PID_DIR/web_ui.pid")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping Web UI (PID: $pid)..."
            kill -TERM "$pid"
            
            # Wait for graceful shutdown
            for i in {1..30}; do
                if ! kill -0 "$pid" 2>/dev/null; then
                    break
                fi
                sleep 1
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                log_warn "Force killing Web UI..."
                kill -KILL "$pid"
            fi
        fi
        rm -f "$PID_DIR/web_ui.pid"
    fi
    
    log_info "All services stopped"
}

# Check service status
check_status() {
    log_info "Checking service status..."
    
    # Check Web UI
    if curl -f "http://localhost:$WEB_UI_PORT/health/" &> /dev/null; then
        log_info "Web UI: RUNNING ✓"
    else
        log_warn "Web UI: NOT RUNNING ✗"
    fi
    
    # Check workers
    for ((i=1; i<=WORKERS_COUNT; i++)); do
        worker_port=$((WORKER_BASE_PORT + i - 1))
        worker_name="worker_$i"
        
        if curl -f "http://localhost:$worker_port/api/v1/health/simple" &> /dev/null; then
            log_info "$worker_name: RUNNING ✓"
        else
            log_warn "$worker_name: NOT RUNNING ✗"
        fi
    done
}

# Cleanup expired locks
cleanup_locks() {
    log_info "Cleaning up expired task locks..."
    
    source "$VENV_DIR/bin/activate"
    cd "$PROJECT_ROOT/modules/web_ui_service"
    
    if [ "$1" = "--dry-run" ]; then
        python manage.py cleanup_locks --dry-run
    else
        python manage.py cleanup_locks
    fi
}

# Show logs
show_logs() {
    service="$1"
    lines="${2:-50}"
    
    case "$service" in
        "web"|"ui")
            tail -n "$lines" "$LOG_DIR/web_ui.log"
            ;;
        "worker")
            worker_num="${3:-1}"
            tail -n "$lines" "$LOG_DIR/worker_$worker_num.log"
            ;;
        "all")
            log_info "=== Web UI Logs ==="
            tail -n 20 "$LOG_DIR/web_ui.log"
            echo
            for ((i=1; i<=WORKERS_COUNT; i++)); do
                log_info "=== Worker $i Logs ==="
                tail -n 10 "$LOG_DIR/worker_$i.log"
                echo
            done
            ;;
        *)
            log_error "Unknown service: $service"
            log_info "Available services: web, worker, all"
            ;;
    esac
}

# Main script logic
case "$1" in
    "setup")
        create_directories
        check_requirements
        setup_virtualenv
        setup_database
        generate_configs
        log_info "Setup complete! Run '$0 start' to start services."
        ;;
    "start")
        create_directories
        start_services
        sleep 5
        check_status
        log_info "Services started! Web UI: http://localhost:$WEB_UI_PORT"
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        sleep 3
        start_services
        sleep 5
        check_status
        ;;
    "status")
        check_status
        ;;
    "logs")
        show_logs "$2" "$3" "$4"
        ;;
    "cleanup")
        cleanup_locks "$2"
        ;;
    "update")
        log_info "Updating application..."
        source "$VENV_DIR/bin/activate"
        cd "$PROJECT_ROOT/modules/web_ui_service"
        python manage.py migrate
        python manage.py collectstatic --noinput
        log_info "Update complete! Run '$0 restart' to apply changes."
        ;;
    *)
        echo "Usage: $0 {setup|start|stop|restart|status|logs|cleanup|update}"
        echo ""
        echo "Commands:"
        echo "  setup     - Initial setup (run once)"
        echo "  start     - Start all services"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart all services"
        echo "  status    - Check service status"
        echo "  logs      - Show logs (logs web|worker [lines] [worker_num])"
        echo "  cleanup   - Clean expired locks (cleanup [--dry-run])"
        echo "  update    - Update application and run migrations"
        echo ""
        echo "Configuration:"
        echo "  WORKERS_COUNT=$WORKERS_COUNT"
        echo "  WEB_UI_PORT=$WEB_UI_PORT"
        echo "  WORKER_BASE_PORT=$WORKER_BASE_PORT"
        echo ""
        exit 1
        ;;
esac