"""
Django settings for instagram_uploader project.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

# Parse ALLOWED_HOSTS from environment variable
ALLOWED_HOSTS_ENV = os.environ.get('ALLOWED_HOSTS', '0.0.0.0,localhost,127.0.0.1,*')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_ENV.split(',') if host.strip()]

# Add common problematic hosts that might appear in logs
PROBLEMATIC_HOSTS = [
    'example.com',
    'ipv4-internet.yandex.net',
    '*.example.com',
    '*.yandex.net',
    'api.ipify.org',
    'www.shadowserver.org',
    '*.ipify.org',
    '*.shadowserver.org'
]

# Add problematic hosts to prevent DisallowedHost errors
for host in PROBLEMATIC_HOSTS:
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

# Allow all hosts in DEBUG to prevent DisallowedHost during local/dev runs
if DEBUG and '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('*')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cabinet',
    'uploader',
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
    'uploader.middleware.RequestLoggingMiddleware',
]

ROOT_URLCONF = 'instagram_uploader.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'uploader/templates')],
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

WSGI_APPLICATION = 'instagram_uploader.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

# Prefer DATABASE_URL (PostgreSQL) when provided; otherwise, fallback to SQLite
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DB_CONN_MAX_AGE = int(os.environ.get('DB_CONN_MAX_AGE', '60'))
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=DB_CONN_MAX_AGE,
            ssl_require=False,
        )
    }

    DATABASES['default']['OPTIONS'] = DATABASES['default'].get('OPTIONS', {})
    app_name = os.environ.get('DB_APPLICATION_NAME', 'instagram_uploader')
    DATABASES['default']['OPTIONS']['application_name'] = app_name
    DATABASES['default']['OPTIONS']['connect_timeout'] = int(os.environ.get('DB_CONN_TIMEOUT', '30'))
    # ВАЖНО: Отключаем server-side cursors для совместимости с PgBouncer
    DATABASES['default']['OPTIONS']['DISABLE_SERVER_SIDE_CURSORS'] = True
    DATABASES['default']['CONN_HEALTH_CHECKS'] = True

    PGBOUNCER_MODE = os.environ.get('PGBOUNCER_MODE', '').lower()

    if PGBOUNCER_MODE == 'transaction':
        # ВАЖНО: для PgBouncer transaction pooling
        DATABASES['default']['CONN_MAX_AGE'] = 0
        # Никаких ручных autocommit/isolation_level
        DATABASES['default']['OPTIONS'].pop('autocommit', None)
        DATABASES['default']['OPTIONS'].pop('isolation_level', None)

    elif PGBOUNCER_MODE == 'session':
        DATABASES['default']['CONN_MAX_AGE'] = min(DB_CONN_MAX_AGE, 300)

    DATABASES['default']['CONN_MAX_RETRIES'] = int(os.environ.get('DB_CONN_RETRIES', '3'))
else:
    # Use DATABASE_PATH environment variable if set, otherwise use default location
    DATABASE_PATH = os.environ.get('DATABASE_PATH', BASE_DIR / 'db.sqlite3')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': DATABASE_PATH,
        }
    }

# Cookie Robot concurrency limit (global), default 5
COOKIE_ROBOT_CONCURRENCY = int(os.environ.get('COOKIE_ROBOT_CONCURRENCY', '5'))


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'uploader', 'static'),
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Worker service token for API auth
WORKER_API_TOKEN = os.environ.get('WORKER_API_TOKEN', '')

# Login settings
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# Session settings to prevent database connection issues
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 24 hours (24 * 60 * 60)
SESSION_SAVE_EVERY_REQUEST = True  # Update session on every request
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Keep session after browser close
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True  # Prevent XSS attacks
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection

# File upload settings
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600
DATA_UPLOAD_MAX_NUMBER_FILES = 1000  # Allow up to 1000 files per request

# Server timeout settings to prevent TimeoutError
SERVER_TIMEOUT = int(os.environ.get('SERVER_TIMEOUT', '300'))  # 5 minutes default
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000  # Increase field limit for bulk operations

# Connection settings for better stability
CONN_MAX_AGE = int(os.environ.get('CONN_MAX_AGE', '600'))  # 10 minutes
CONN_HEALTH_CHECKS = True

# Request timeout settings
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '60'))  # 1 minute

# reCAPTCHA settings
RUCAPTCHA_API_KEY = os.environ.get('RUCAPTCHA_API_KEY', '')
CAPTCHA_API_KEY = os.environ.get('CAPTCHA_API_KEY', '')  # Fallback

# If neither is set, log a warning
if not RUCAPTCHA_API_KEY and not CAPTCHA_API_KEY:
    import logging
    # logger = logging.getLogger(__name__)
    # logger.warning("[WARN] No reCAPTCHA API key configured. Set RUCAPTCHA_API_KEY environment variable for automatic captcha solving.")

# Dolphin Anty settings
DOLPHIN_API_TOKEN = os.environ.get('DOLPHIN_API_TOKEN', '')

# Centralized Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': os.getenv('CONSOLE_LOG_LEVEL', 'INFO'),
            'filters': ['mask_secrets', 'truncate_long', 'deduplicate'],
        },
        'file': {
            'class': 'uploader.logging_handlers.SafeRotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'django.log'),
            'formatter': 'verbose',
            'level': 'DEBUG',
            'maxBytes': int(os.getenv('LOG_MAX_BYTES', '50000000')),  # 50MB default
            'backupCount': int(os.getenv('LOG_BACKUP_COUNT', '5')),
            'filters': ['mask_secrets', 'truncate_long'],
        },
        'web': {
            'class': 'uploader.logging_handlers.WebLogHandler',
            'formatter': 'verbose',
            'level': os.getenv('WEB_LOG_LEVEL', 'INFO'),
            'filters': ['mask_secrets', 'truncate_long'],
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'filters': {
        'mask_secrets': {
            '()': 'uploader.logging_filters.MaskSecretsFilter'
        },
        'truncate_long': {
            '()': 'uploader.logging_filters.TruncateLongFilter'
        },
        'deduplicate': {
            '()': 'uploader.logging_filters.DeduplicateFilter'
        },
    },
    'root': {
        'handlers': ['console', 'file', 'web'],
        'level': 'DEBUG',
    },
    'loggers': {
        # Django core loggers
        'django': {
            'level': 'INFO',
            'propagate': True,
        },
        'django.db.backends': {
            'level': 'WARNING',
            'propagate': True,
        },
        'django.request': {
            'level': 'ERROR',
            'propagate': True,
        },
        'django.server': {
            'handlers': ['null'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.template': {
            'level': 'WARNING',
            'propagate': True,
        },
        
        # Application loggers
        'uploader': {
            'level': 'DEBUG',
            'propagate': True,
        },
        'uploader.middleware': {
            'level': os.getenv('REQUEST_LOG_LEVEL', 'INFO'),
            'propagate': True,
        },
        'uploader.bulk_tasks': {
            'level': os.getenv('BULK_LOG_LEVEL', 'INFO'),
            'propagate': True,
        },
        
        # Bot loggers
        'bot': {
            'level': 'INFO',
            'propagate': True,
        },
        'bot.run_bot_playwright': {
            'level': 'INFO',
            'propagate': True,
        },
        'bot.instagram_uploader': {
            'level': 'INFO',
            'propagate': True,
        },
        'bot.instagram_uploader.auth': {
            'level': 'INFO',
            'propagate': True,
        },
        'bot.instagram_uploader.upload': {
            'level': 'INFO',
            'propagate': True,
        },
        'bot.instagram_uploader.dolphin_anty': {
            'level': 'INFO',
            'propagate': True,
        },
        'bot.instagram_uploader.browser_dolphin': {
            'level': 'INFO',
            'propagate': True,
        },
        'bot.instagram_uploader.util': {
            'level': 'INFO',
            'propagate': True,
        },
        'bot.instagram_uploader.tfa_api': {
            'level': 'INFO',
            'propagate': True,
        },
        'bot.videos': {
            'level': 'INFO',
            'propagate': True,
        },
        
        # YouTube loggers
        'youtube': {
            'level': os.getenv('YOUTUBE_LOG_LEVEL', 'INFO'),
            'propagate': True,
        },
        'youtube.async_bulk_tasks': {
            'level': os.getenv('YOUTUBE_LOG_LEVEL', 'INFO'),
            'propagate': True,
        },
        'youtube.automation': {
            'level': os.getenv('YOUTUBE_LOG_LEVEL', 'INFO'),
            'propagate': True,
        },
        
        # Instagram API loggers
        'instagrapi': {
            'level': os.getenv('INSTAGRAPI_LOG_LEVEL', 'DEBUG'),
            'propagate': True,
        },
        'public_request': {
            'level': os.getenv('IG_HTTP_LOG_LEVEL', 'DEBUG'),
            'propagate': True,
        },
        'private_request': {
            'level': os.getenv('IG_HTTP_LOG_LEVEL', 'DEBUG'),
            'propagate': True,
        },
        
        # Instagram service loggers
        'insta.auth': {
            'level': 'DEBUG',
            'propagate': True,
        },
        'insta.avatar': {
            'level': 'DEBUG',
            'propagate': True,
        },
        'insta.follow': {
            'level': 'DEBUG',
            'propagate': True,
        },
        'insta.hashtag': {
            'level': 'DEBUG',
            'propagate': True,
        },
        'insta.bio': {
            'level': 'DEBUG',
            'propagate': True,
        },
        'insta.account.analytics': {
            'level': 'DEBUG',
            'propagate': True,
        },
        'insta.warmup': {
            'level': 'DEBUG',
            'propagate': True,
        },
        'insta.password_reset': {
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# WhiteNoise settings for static files in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
CONN_MAX_AGE = 0
CONN_HEALTH_CHECKS = True

