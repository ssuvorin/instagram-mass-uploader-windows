"""
Centralized logging handlers for the Instagram uploader project.
"""

import logging
import logging.handlers
from django.core.cache import cache
from django.utils import timezone


class WebLogHandler(logging.Handler):
    """
    Handler for sending logs to web interface through Django cache.
    
    This handler stores log entries in cache for display in the web interface,
    with automatic rotation and size limits to prevent memory issues.
    """
    
    def __init__(self, max_logs=1000, cache_timeout=3600):
        """
        Initialize the web log handler.
        
        Args:
            max_logs (int): Maximum number of log entries to keep in cache
            cache_timeout (int): Cache timeout in seconds (default: 1 hour)
        """
        super().__init__()
        self.max_logs = max_logs
        self.cache_timeout = cache_timeout
    
    def emit(self, record):
        """
        Emit a log record to the web interface cache.
        
        Args:
            record (LogRecord): The log record to emit
        """
        try:
            log_entry = {
                'timestamp': timezone.now().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': self.format(record),
                'module': getattr(record, 'module', record.name.split('.')[-1]),
            }
            
            # Get current logs from cache
            cache_key = 'system_logs'
            logs = cache.get(cache_key, [])
            
            # Add new log entry
            logs.append(log_entry)
            
            # Limit the number of logs to prevent memory issues
            if len(logs) > self.max_logs:
                logs = logs[-self.max_logs:]
            
            # Save back to cache
            cache.set(cache_key, logs, self.cache_timeout)
            
        except Exception:
            # Handle errors gracefully to prevent logging from breaking the application
            self.handleError(record)


class SafeFileHandler(logging.handlers.RotatingFileHandler):
    """
    Safe file handler with error recovery for disk space and permission issues.
    
    This handler provides graceful degradation when file system errors occur,
    falling back to console output when necessary.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the safe file handler."""
        super().__init__(*args, **kwargs)
        self._console_fallback = None
    
    def emit(self, record):
        """
        Emit a log record with error recovery.
        
        Args:
            record (LogRecord): The log record to emit
        """
        try:
            super().emit(record)
        except (OSError, IOError) as e:
            # File system error - fall back to console
            if not self._console_fallback:
                self._console_fallback = logging.StreamHandler()
                self._console_fallback.setFormatter(self.formatter)
            
            # Log the error to console
            error_record = logging.LogRecord(
                name='logging.error',
                level=logging.ERROR,
                pathname='',
                lineno=0,
                msg=f"File logging error: {e}. Falling back to console.",
                args=(),
                exc_info=None
            )
            self._console_fallback.emit(error_record)
            
            # Emit the original record to console
            self._console_fallback.emit(record)
        except Exception:
            # Handle any other errors gracefully
            self.handleError(record)


class SafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    Safe rotating file handler that handles Windows permission errors during log rotation.

    On Windows, file rotation can fail if another process has the log file open.
    This handler catches such errors and creates a timestamped backup instead.
    """

    def doRollover(self):
        """
        Perform log file rotation with error handling for Windows permission issues.
        """
        try:
            # Try the normal rotation first
            super().doRollover()
        except (OSError, PermissionError) as e:
            # On Windows, rotation can fail if file is locked by another process
            # Create a timestamped backup as fallback
            import time
            import os

            try:
                # Create timestamped backup filename
                timestamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
                backup_name = f"{self.baseFilename}.{timestamp}"

                # Copy current log to backup
                with open(self.baseFilename, 'rb') as src, open(backup_name, 'wb') as dst:
                    dst.write(src.read())

                # Truncate the original log file
                with open(self.baseFilename, 'w') as f:
                    f.truncate(0)

                # Clean up old backups (keep only the most recent ones)
                self._cleanup_old_backups()

            except Exception as backup_error:
                # If backup also fails, log to console and continue
                console = logging.StreamHandler()
                console.setLevel(logging.ERROR)
                console.emit(logging.LogRecord(
                    name='logging.error',
                    level=logging.ERROR,
                    pathname='',
                    lineno=0,
                    msg=f"Log rotation failed: {e}. Backup creation failed: {backup_error}",
                    args=(),
                    exc_info=None
                ))

    def _cleanup_old_backups(self):
        """
        Clean up old backup files, keeping only the most recent ones.
        """
        import glob
        import os

        try:
            # Find all backup files
            backup_pattern = f"{self.baseFilename}.*"
            backup_files = glob.glob(backup_pattern)

            # Sort by modification time (newest first)
            backup_files.sort(key=os.path.getmtime, reverse=True)

            # Keep only the most recent backups (backupCount - 1, since current log is active)
            max_backups = max(1, self.backupCount - 1)
            if len(backup_files) > max_backups:
                for old_backup in backup_files[max_backups:]:
                    try:
                        os.remove(old_backup)
                    except OSError:
                        pass  # Ignore cleanup errors
        except Exception:
            # Ignore cleanup errors to prevent breaking logging
            pass