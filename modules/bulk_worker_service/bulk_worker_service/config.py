import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Settings:
    ui_api_base: Optional[str] = os.getenv("UI_API_BASE")
    ui_api_token: Optional[str] = os.getenv("UI_API_TOKEN")

    dolphin_api_token: Optional[str] = os.getenv("DOLPHIN_API_TOKEN")
    dolphin_api_host: str = os.getenv("DOLPHIN_API_HOST", "http://127.0.0.1:3001")

    concurrency_limit: int = int(os.getenv("CONCURRENCY_LIMIT", "2"))
    batch_size: int = int(os.getenv("BATCH_SIZE", "2"))

    headless: bool = os.getenv("HEADLESS", "1") in ("1", "true", "yes", "on")
    visible_browser: bool = os.getenv("VISIBLE_BROWSER", "0") in ("1", "true", "yes", "on")

    request_timeout_secs: float = float(os.getenv("REQUEST_TIMEOUT_SECS", "60"))
    verify_ssl: bool = os.getenv("VERIFY_SSL", "1") in ("1", "true", "yes", "on")

    media_temp_dir: str = os.getenv("MEDIA_TEMP_DIR", os.path.join(os.getcwd(), "_tmp_media"))

    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Default upload method for bulk worker: 'playwright' or 'instagrapi'
    upload_method: str = os.getenv("UPLOAD_METHOD", "playwright").lower()

    # Worker self-identification/registration
    worker_name: str = os.getenv("WORKER_NAME", "")
    worker_base_url: str = os.getenv("WORKER_BASE_URL", "")
    worker_capacity: int = int(os.getenv("WORKER_CAPACITY", "1"))
    heartbeat_interval_secs: int = int(os.getenv("HEARTBEAT_INTERVAL_SECS", "30"))
    
    # Enhanced settings for new functionality
    worker_id: str = os.getenv("WORKER_ID", f"worker_{os.getpid()}")
    
    # Media processing settings
    media_output_dir: str = os.getenv("MEDIA_OUTPUT_DIR", os.path.join(os.getcwd(), "_processed_media"))
    media_processing_concurrency: int = int(os.getenv("MEDIA_PROCESSING_CONCURRENCY", "5"))
    
    # Proxy diagnostics settings
    proxy_slow_threshold: float = float(os.getenv("PROXY_SLOW_THRESHOLD", "5.0"))
    proxy_timeout_threshold: float = float(os.getenv("PROXY_TIMEOUT_THRESHOLD", "30.0"))
    proxy_test_concurrency: int = int(os.getenv("PROXY_TEST_CONCURRENCY", "10"))
    
    # Error handling settings
    error_log_file: Optional[str] = os.getenv("ERROR_LOG_FILE")
    max_retry_attempts: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    
    # Account management settings
    account_batch_size: int = int(os.getenv("ACCOUNT_BATCH_SIZE", "10"))
    dolphin_profile_concurrency: int = int(os.getenv("DOLPHIN_PROFILE_CONCURRENCY", "5"))
    
    # Cookie robot settings
    cookie_robot_concurrency: int = int(os.getenv("COOKIE_ROBOT_CONCURRENCY", "2"))
    cookie_robot_delay: float = float(os.getenv("COOKIE_ROBOT_DELAY", "1.0"))


settings = Settings() 