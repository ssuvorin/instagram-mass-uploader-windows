import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
DEBUG = os.getenv('DEBUG', 'False').lower() in ('1','true','yes','on')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS','*').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'uploader',  # reuse existing UI app
    'dashboard', # thin layer for API wiring and starts
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'remote_ui.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'uploader', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'remote_ui.wsgi.application'

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=False)}
else:
    DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME': BASE_DIR / 'db.sqlite3'}}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Worker integration
WORKER_BASE_URL = os.getenv('WORKER_BASE_URL', '')
WORKER_API_TOKEN = os.getenv('WORKER_API_TOKEN', '')
# Dispatcher (optional multi-worker routing)
WORKER_POOL = [h.strip() for h in os.getenv('WORKER_POOL', '').split(',') if h.strip()]
DISPATCH_BATCH_SIZE = int(os.getenv('DISPATCH_BATCH_SIZE', '5'))
DISPATCH_CONCURRENCY = int(os.getenv('DISPATCH_CONCURRENCY', '2')) 

# Security: multiple tokens support and IP allowlist for API
WORKER_API_TOKENS = [t.strip() for t in os.getenv('WORKER_API_TOKENS', '').split(',') if t.strip()]
WORKER_ALLOWED_IPS = [ip.strip() for ip in os.getenv('WORKER_ALLOWED_IPS', '').split(',') if ip.strip()]

# Optional reverse-proxy/HTTPS hints
if os.getenv('SECURE_PROXY_SSL_HEADER', '0') in ('1','true','yes','on'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = os.getenv('USE_X_FORWARDED_HOST', '1') in ('1','true','yes','on')