"""
Django settings for servia_backend project.
"""
import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-prod')

DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'channels',
    'websocket',
    'apps.users',
    'apps.job',
    'apps.candidate',
    'apps.interview',    
    'apps.ai_reports',
    'apps.reporting',
    'django_rest_passwordreset',
    'drf_spectacular',
    'django_celery_results',

]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'servia_backend.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'servia_backend.wsgi.application'
ASGI_APPLICATION = 'servia_backend.asgi.application'

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Fallback for Docker
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'servia'),
            'USER': os.getenv('POSTGRES_USER', 'servia'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'servia123'),
            'HOST': 'db',  # Only for Docker!
            'PORT': '5432',
        }
    }

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {"hosts": [os.getenv('REDIS_URL', 'redis://redis:6379')]},
    },
}
AUTH_USER_MODEL = 'auth.User'  # Default user model
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


SENTRY_DSN = os.getenv('SENTRY_DSN', '')

if SENTRY_DSN:  
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        send_default_pii=False,
        traces_sample_rate=1.0,
        environment='development',
        before_send=lambda event, hint: _filter_event(event, hint),
    )
def _filter_event(event, hint):
    """Strip any remaining PII from Sentry events 
    Removes: email, username, ip_address, phone from user context
    Keeps: anonymized user ID for correlation"""
    if 'user' in event:
        event['user'] = {
            'id': event['user'].get('id'),  
        }
    return event
# Allow all origins only in development (and only if credentials are NOT used)
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False') == 'True'

# Parse explicit origins from env var - '*' is NOT valid here
cors_allowed_raw = os.getenv('CORS_ALLOWED_ORIGINS', '')
if cors_allowed_raw and cors_allowed_raw != '*':
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in cors_allowed_raw.split(',') if origin.strip()
    ]
else:
    # Default development origins
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:8000',
    ]

# Allow credentials (cookies, auth headers) - requires explicit origins
CORS_ALLOW_CREDENTIALS = os.getenv('CORS_ALLOW_CREDENTIALS', 'True') == 'True'


# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication', 
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
       'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',   # For unauthenticated users
        'rest_framework.throttling.UserRateThrottle',   # For authenticated users
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',       
        'user': '1000/day',         
        'bulk_update': '10/min',    
    }, 
}
SPECTACULAR_SETTINGS = {
    'TITLE': 'ServiaAI API',
    'DESCRIPTION': 'AI-powered hospitality recruitment platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Cloudflare R2 Settings (required for CV storage)
CLOUDFLARE_R2_ACCESS_KEY = os.environ.get('CLOUDFLARE_R2_ACCESS_KEY')
CLOUDFLARE_R2_SECRET_KEY = os.environ.get('CLOUDFLARE_R2_SECRET_KEY')
CLOUDFLARE_R2_BUCKET = os.environ.get('CLOUDFLARE_R2_BUCKET', 'servia-cv-storage')
CLOUDFLARE_R2_PUBLIC_URL = os.environ.get('CLOUDFLARE_R2_PUBLIC_URL')
CLOUDFLARE_R2_ACCOUNT_ID = os.environ.get('CLOUDFLARE_R2_ACCOUNT_ID')
CLOUDFLARE_R2_ENDPOINT = os.environ.get('CLOUDFLARE_R2_ENDPOINT')

CLOUDFLARE_STREAM_TOKEN = os.environ.get('CLOUDFLARE_STREAM_TOKEN', None)

# Validate required settings for CV storage
if not all([CLOUDFLARE_R2_ACCESS_KEY, CLOUDFLARE_R2_SECRET_KEY, CLOUDFLARE_R2_ENDPOINT]):
    raise ValueError("Missing required Cloudflare R2 environment variables")

# File upload limits
MAX_CV_SIZE_MB = 10
MAX_VIDEO_SIZE_MB = 50
MAX_VIDEO_DURATION_SECONDS = 120


# Email Configuration (Brevo SMTP)
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp-relay.brevo.com')
# EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
# EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
# EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False') == 'True'
# EMAIL_USE_SSL = False
# EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
# DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'misginameaza@gmail.com')

FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# Tesseract OCR path
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Celery Config (add to settings.py)
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Nairobi'
CELERY_RESULT_BACKEND = 'django-db'

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}