import logging
import os
import sys

def setup_django_logging():
    """
    Setup Django logging configuration for bot modules.
    This ensures bot modules use the centralized Django logging system.
    """
    # Add project root to Python path for Django imports
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Setup Django if not already configured
    try:
        import django
        from django.conf import settings
        
        if not settings.configured:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
            django.setup()
            
    except ImportError:
        # Fallback if Django is not available - use minimal logging
        # Note: This should rarely happen as bot should run with Django available
        logger = logging.getLogger('bot.fallback')
        logger.warning("Django not available, using fallback logging")

# Initialize Django logging
setup_django_logging()

# Create logger using Django's centralized configuration
logger = logging.getLogger('bot') 