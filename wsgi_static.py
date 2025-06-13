import os
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')

application = get_wsgi_application()
application = WhiteNoise(application)
application.add_files(settings.STATIC_ROOT, prefix="static/")
application.add_files(os.path.join(settings.BASE_DIR, 'uploader/static'), prefix="static/") 