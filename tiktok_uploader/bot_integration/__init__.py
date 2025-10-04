"""
Bot Integration Module
=======================

Интеграция бота TikTokUploadCaptcha в Django веб-интерфейс.
Все модули бота сохраняют свою оригинальную логику.
"""

import os
from .logger import Logger

# Инициализируем глобальный логгер для бота
logger = Logger(debug=bool(os.environ.get('DEBUG', False)), log_file='logs/tiktok_bot.log')
