"""Django app configuration for TikTok Uploader"""
from django.apps import AppConfig


class TiktokUploaderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tiktok_uploader'
    verbose_name = 'TikTok Uploader'

    def ready(self):
        """
        Инициализация при запуске приложения.
        Здесь можно регистрировать сигналы, задачи Celery и т.д.
        """
        # Import signals if needed
        # import tiktok_uploader.signals
        pass


