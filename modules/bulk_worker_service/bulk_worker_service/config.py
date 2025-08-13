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


settings = Settings() 