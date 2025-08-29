#!/bin/bash

# Setup cron jobs for automated maintenance
# This script sets up periodic tasks to maintain system health

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_ROOT/venv"
LOG_DIR="$PROJECT_ROOT/logs"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create cron scripts directory
CRON_SCRIPTS_DIR="$PROJECT_ROOT/cron_scripts"
mkdir -p "$CRON_SCRIPTS_DIR"

# Create lock cleanup script
cat > "$CRON_SCRIPTS_DIR/cleanup_locks.sh" << 'EOF'
#!/bin/bash

# Automated task lock cleanup script
# Runs every 15 minutes to clean expired locks

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_ROOT/venv"
LOG_DIR="$PROJECT_ROOT/logs"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Navigate to Django project
cd "$PROJECT_ROOT/modules/web_ui_service"

# Run cleanup with timeout
timeout 300 python manage.py cleanup_locks >> "$LOG_DIR/lock_cleanup.log" 2>&1

# Log completion
echo "$(date): Lock cleanup completed" >> "$LOG_DIR/lock_cleanup.log"
EOF

# Create log rotation script
cat > "$CRON_SCRIPTS_DIR/rotate_logs.sh" << 'EOF'
#!/bin/bash

# Log rotation script
# Runs daily to prevent log files from growing too large

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"

# Max log file size (in MB)
MAX_SIZE=100

# Rotate log files
for log_file in "$LOG_DIR"/*.log; do
    if [ -f "$log_file" ]; then
        # Check file size
        size=$(du -m "$log_file" | cut -f1)
        
        if [ "$size" -gt "$MAX_SIZE" ]; then
            # Rotate the log
            mv "$log_file" "${log_file}.$(date +%Y%m%d_%H%M%S)"
            touch "$log_file"
            
            # Keep only last 5 rotated logs
            ls -t "${log_file}".* | tail -n +6 | xargs -r rm
            
            echo "$(date): Rotated $log_file (size: ${size}MB)" >> "$LOG_DIR/rotation.log"
        fi
    fi
done

# Clean old rotation logs
find "$LOG_DIR" -name "*.log.*" -mtime +30 -delete

echo "$(date): Log rotation completed" >> "$LOG_DIR/rotation.log"
EOF

# Create health check script
cat > "$CRON_SCRIPTS_DIR/health_check.sh" << 'EOF'
#!/bin/bash

# Health check script
# Runs every 5 minutes to monitor service health

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"

WORKERS_COUNT=5
WEB_UI_PORT=8000
WORKER_BASE_PORT=8088

# Health check results
HEALTH_LOG="$LOG_DIR/health_check.log"
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# Check Web UI
if curl -f -s "http://localhost:$WEB_UI_PORT/health/" > /dev/null; then
    web_status="OK"
else
    web_status="FAILED"
    echo "$timestamp: Web UI health check failed" >> "$HEALTH_LOG"
    
    # Try to restart Web UI
    if [ -f "$PROJECT_ROOT/pids/web_ui.pid" ]; then
        echo "$timestamp: Attempting to restart Web UI" >> "$HEALTH_LOG"
        "$PROJECT_ROOT/deploy_production.sh" restart >> "$HEALTH_LOG" 2>&1
    fi
fi

# Check Workers
failed_workers=0
for ((i=1; i<=WORKERS_COUNT; i++)); do
    worker_port=$((WORKER_BASE_PORT + i - 1))
    worker_name="worker_$i"
    
    if curl -f -s "http://localhost:$worker_port/api/v1/health/simple" > /dev/null; then
        worker_status="OK"
    else
        worker_status="FAILED"
        failed_workers=$((failed_workers + 1))
        echo "$timestamp: $worker_name health check failed" >> "$HEALTH_LOG"
    fi
done

# Log overall status
if [ "$web_status" = "OK" ] && [ "$failed_workers" -eq 0 ]; then
    status="HEALTHY"
else
    status="UNHEALTHY"
fi

echo "$timestamp: Overall status: $status (Web: $web_status, Failed workers: $failed_workers)" >> "$HEALTH_LOG"

# Keep only last 1000 lines of health log
tail -n 1000 "$HEALTH_LOG" > "$HEALTH_LOG.tmp" && mv "$HEALTH_LOG.tmp" "$HEALTH_LOG"
EOF

# Create database backup script
cat > "$CRON_SCRIPTS_DIR/backup_database.sh" << 'EOF'
#!/bin/bash

# Database backup script
# Runs daily to create database backups

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
LOG_DIR="$PROJECT_ROOT/logs"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Extract database credentials from DATABASE_URL
if [ -n "$DATABASE_URL" ]; then
    # Parse postgresql://user:password@host:port/database
    DB_USER=$(echo "$DATABASE_URL" | sed -n 's|postgresql://\([^:]*\):.*|\1|p')
    DB_PASSWORD=$(echo "$DATABASE_URL" | sed -n 's|postgresql://[^:]*:\([^@]*\)@.*|\1|p')
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|postgresql://[^@]*@\([^:]*\):.*|\1|p')
    DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|postgresql://[^@]*@[^:]*:\([^/]*\)/.*|\1|p')
    DB_NAME=$(echo "$DATABASE_URL" | sed -n 's|postgresql://[^/]*/\(.*\)|\1|p')
    
    # Create backup filename with timestamp
    backup_file="$BACKUP_DIR/iguploader_$(date +%Y%m%d_%H%M%S).sql"
    
    # Create database backup
    PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-password \
        --verbose \
        > "$backup_file" 2>> "$LOG_DIR/backup.log"
    
    if [ $? -eq 0 ]; then
        # Compress the backup
        gzip "$backup_file"
        echo "$(date): Database backup created: ${backup_file}.gz" >> "$LOG_DIR/backup.log"
        
        # Clean old backups (keep last 7 days)
        find "$BACKUP_DIR" -name "iguploader_*.sql.gz" -mtime +7 -delete
        
    else
        echo "$(date): Database backup failed" >> "$LOG_DIR/backup.log"
    fi
else
    echo "$(date): DATABASE_URL not found in .env file" >> "$LOG_DIR/backup.log"
fi
EOF

# Create metrics collection script
cat > "$CRON_SCRIPTS_DIR/collect_metrics.sh" << 'EOF'
#!/bin/bash

# Metrics collection script
# Runs every minute to collect system metrics

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
METRICS_DIR="$PROJECT_ROOT/metrics"

mkdir -p "$METRICS_DIR"

timestamp=$(date '+%Y-%m-%d %H:%M:%S')
date_key=$(date '+%Y%m%d')

# Collect system metrics
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
memory_usage=$(free -m | awk 'NR==2{printf "%.1f", $3*100/$2}')
disk_usage=$(df -h / | awk 'NR==2{print $5}' | cut -d'%' -f1)

# Collect application metrics
web_ui_port=8000
worker_base_port=8088
workers_count=5

# Check Web UI metrics
if curl -f -s "http://localhost:$web_ui_port/api/metrics/" > /dev/null; then
    web_metrics=$(curl -s "http://localhost:$web_ui_port/api/metrics/" | jq -c .)
else
    web_metrics='{"error": "unavailable"}'
fi

# Check Worker metrics
worker_metrics="[]"
for ((i=1; i<=workers_count; i++)); do
    worker_port=$((worker_base_port + i - 1))
    if curl -f -s "http://localhost:$worker_port/api/v1/metrics" > /dev/null; then
        metrics=$(curl -s "http://localhost:$worker_port/api/v1/metrics" | jq -c .)
        worker_metrics=$(echo "$worker_metrics" | jq ". + [$metrics]")
    fi
done

# Create metrics entry
metrics_entry=$(jq -n \
    --arg timestamp "$timestamp" \
    --arg cpu "$cpu_usage" \
    --arg memory "$memory_usage" \
    --arg disk "$disk_usage" \
    --argjson web "$web_metrics" \
    --argjson workers "$worker_metrics" \
    '{
        timestamp: $timestamp,
        system: {
            cpu_usage: $cpu,
            memory_usage: $memory,
            disk_usage: $disk
        },
        web_ui: $web,
        workers: $workers
    }')

# Append to daily metrics file
echo "$metrics_entry" >> "$METRICS_DIR/metrics_$date_key.jsonl"

# Keep only last 30 days of metrics
find "$METRICS_DIR" -name "metrics_*.jsonl" -mtime +30 -delete
EOF

# Make scripts executable
chmod +x "$CRON_SCRIPTS_DIR"/*.sh

log_info "Created maintenance scripts in $CRON_SCRIPTS_DIR"

# Generate crontab entries
CRONTAB_FILE="$PROJECT_ROOT/crontab_entries"

cat > "$CRONTAB_FILE" << EOF
# Instagram Automation System - Automated Maintenance Tasks
# Add these entries to your crontab with: crontab -e

# Clean expired task locks every 15 minutes
*/15 * * * * $CRON_SCRIPTS_DIR/cleanup_locks.sh

# Health check every 5 minutes
*/5 * * * * $CRON_SCRIPTS_DIR/health_check.sh

# Collect metrics every minute
* * * * * $CRON_SCRIPTS_DIR/collect_metrics.sh

# Rotate logs daily at 2 AM
0 2 * * * $CRON_SCRIPTS_DIR/rotate_logs.sh

# Database backup daily at 3 AM
0 3 * * * $CRON_SCRIPTS_DIR/backup_database.sh

# Clean temporary files weekly on Sunday at 4 AM
0 4 * * 0 find $PROJECT_ROOT/temp -type f -mtime +7 -delete

# Restart services weekly on Sunday at 5 AM (optional)
# 0 5 * * 0 $PROJECT_ROOT/deploy_production.sh restart
EOF

log_info "Generated crontab entries in $CRONTAB_FILE"

# Function to install cron jobs
install_cron() {
    log_info "Installing cron jobs..."
    
    # Backup existing crontab
    crontab -l > "$PROJECT_ROOT/crontab_backup_$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
    
    # Add new cron jobs
    (crontab -l 2>/dev/null; cat "$CRONTAB_FILE") | crontab -
    
    log_info "Cron jobs installed successfully"
    log_info "Current crontab:"
    crontab -l | grep -E "(cleanup_locks|health_check|collect_metrics|rotate_logs|backup_database)"
}

# Function to remove cron jobs
remove_cron() {
    log_info "Removing cron jobs..."
    
    # Remove lines containing our script paths
    crontab -l | grep -v "$CRON_SCRIPTS_DIR" | crontab -
    
    log_info "Cron jobs removed"
}

# Function to show cron status
show_cron_status() {
    log_info "Current cron jobs:"
    crontab -l | grep -E "(cleanup_locks|health_check|collect_metrics|rotate_logs|backup_database)" || echo "No automation cron jobs found"
    
    echo
    log_info "Recent log activity:"
    
    # Show recent health check logs
    if [ -f "$LOG_DIR/health_check.log" ]; then
        echo "Health checks (last 5):"
        tail -n 5 "$LOG_DIR/health_check.log"
        echo
    fi
    
    # Show recent lock cleanup logs
    if [ -f "$LOG_DIR/lock_cleanup.log" ]; then
        echo "Lock cleanup (last 3):"
        tail -n 3 "$LOG_DIR/lock_cleanup.log"
        echo
    fi
}

# Main command handling
case "$1" in
    "install")
        install_cron
        ;;
    "remove")
        remove_cron
        ;;
    "status")
        show_cron_status
        ;;
    "test")
        log_info "Testing maintenance scripts..."
        
        log_info "Testing health check..."
        "$CRON_SCRIPTS_DIR/health_check.sh"
        
        log_info "Testing lock cleanup (dry run)..."
        if [ -f "$PROJECT_ROOT/modules/web_ui_service/manage.py" ]; then
            cd "$PROJECT_ROOT/modules/web_ui_service"
            source "$VENV_DIR/bin/activate"
            python manage.py cleanup_locks --dry-run
        fi
        
        log_info "Testing log rotation..."
        "$CRON_SCRIPTS_DIR/rotate_logs.sh"
        
        log_info "Testing metrics collection..."
        "$CRON_SCRIPTS_DIR/collect_metrics.sh"
        
        log_info "All tests completed"
        ;;
    *)
        echo "Usage: $0 {install|remove|status|test}"
        echo ""
        echo "Commands:"
        echo "  install  - Install cron jobs for automated maintenance"
        echo "  remove   - Remove automation cron jobs"
        echo "  status   - Show current cron job status and recent logs"
        echo "  test     - Test all maintenance scripts manually"
        echo ""
        echo "Cron jobs will be installed for:"
        echo "  - Lock cleanup (every 15 minutes)"
        echo "  - Health monitoring (every 5 minutes)"
        echo "  - Metrics collection (every minute)"
        echo "  - Log rotation (daily at 2 AM)"
        echo "  - Database backup (daily at 3 AM)"
        echo ""
        exit 1
        ;;
esac