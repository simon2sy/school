import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

INSECURE_FALLBACK_KEY = "django-insecure-fallback-key-change-in-production"
SECRET_KEY = os.getenv("SECRET_KEY", INSECURE_FALLBACK_KEY)
DEBUG = True

# DEBUG defaults ON for local development. Set DEBUG=False in your server .env
# so the app runs hardened (security middleware + secret-key guard below).


# Refuse to boot in production with a weak/placeholder secret key.
if not DEBUG and SECRET_KEY == INSECURE_FALLBACK_KEY:
    raise ImproperlyConfigured(
        "Production requires a real SECRET_KEY. Set it in your .env file. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(50))\""
    )

ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS", "localhost,127.0.0.1,*"
).split(",")

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
]

THIRD_PARTY_APPS = [
    'widget_tweaks',
]

# Add django-celery-beat only if installed (graceful fallback without Redis/Celery)
try:
    import django_celery_beat  # noqa: F401
    THIRD_PARTY_APPS.append('django_celery_beat')
except ImportError:
    pass

LOCAL_APPS = [
    'apps.core.apps.CoreConfig',
    'apps.academics.apps.AcademicsConfig',
    'apps.content.apps.ContentConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    # SecurityMiddleware must be first. Whienoise goes right after it so
    # static files are served through WSGI (no separate static mapping needed).
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.school_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# SQLite fallback for development
if os.getenv('USE_SQLITE', 'True') == 'True':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── Caching ─────────────────────────────────────────────────────────
# Use Redis when REDIS_URL is set (production / multi-worker);
# fall back to LocMemCache for single-server dev.
REDIS_URL = os.getenv('REDIS_URL', '')

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'KEY_PREFIX': 'galaxy',
            'TIMEOUT': 300,  # 5 min default TTL
        }
    }
    # Store sessions in Redis for shared access across workers
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'galaxy-default-cache',
        }
    }

# Email configuration for the contact form. Configure these in your .env
# file when going live (e.g. a SendGrid / SMTP provider).
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    'Galaxy English School <info@galaxyenglishschool.edu.np>'
)
CONTACT_TO_EMAIL = os.getenv(
    'CONTACT_TO_EMAIL',
    'info@galaxyenglishschool.edu.np'
)

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kathmandu'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Whitenoise: compress + cache static files with an immutable "max-age=1 year"
# on hashed filenames. Works with compress=True for smaller payloads.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ── Celery ───────────────────────────────────────────────────────────
# All celery config is defined regardless of whether celery is installed,
# so that the settings file itself is always importable. The actual Celery
# app (config/celery.py) is only loaded when celery is available.
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL or 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL or 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 min hard limit per task
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 min soft limit
try:
    import celery  # noqa: F401
    import django_celery_beat  # noqa: F401
    CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
except ImportError:
    pass  # celery / django-celery-beat not installed — skip beat scheduler

# Admin customization
ADMIN_SITE_HEADER = "Galaxy English School Administration"
ADMIN_SITE_TITLE = "Galaxy English School Admin"
ADMIN_INDEX_TITLE = "Welcome to Galaxy English School Admin Panel"