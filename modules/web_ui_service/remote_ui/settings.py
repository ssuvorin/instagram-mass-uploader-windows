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
    # UI modules for distributed architecture
    'ui_core',    # New app for core UI functionality (replacing direct uploader dependency)
    'dashboard',  # API integration and monitoring
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
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),  # Local UI module templates
        ],
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

# API Communication Settings
API_SERVICES = {
    'management': {
        'url': os.getenv('MANAGEMENT_API_URL', 'http://localhost:8089'),
        'token': os.getenv('API_TOKEN_MANAGEMENT', ''),
    },
    'worker': {
        'url': os.getenv('WORKER_API_URL', 'http://localhost:8088'), 
        'token': os.getenv('API_TOKEN_WORKER', ''),
    },
    'monitoring': {
        'url': os.getenv('MONITORING_API_URL', 'http://localhost:8090'),
        'token': os.getenv('API_TOKEN_MONITORING', ''),
    }
}

# Monitoring refresh interval
MONITORING_REFRESH_INTERVAL = int(os.getenv('MONITORING_REFRESH_INTERVAL', '30'))

# Optional reverse-proxy/HTTPS hints
if os.getenv('SECURE_PROXY_SSL_HEADER', '0') in ('1','true','yes','on'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = os.getenv('USE_X_FORWARDED_HOST', '1') in ('1','true','yes','on')