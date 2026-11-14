"""
Django settings for the ALVIX project.

All secrets and environment-specific values come from environment variables
(loaded from a `.env` file in the repository root or in `backend/`).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# backend/ directory
BASE_DIR = Path(__file__).resolve().parent.parent
# repository root (contains backend/ and frontend/)
REPO_DIR = BASE_DIR.parent

load_dotenv(REPO_DIR / '.env')
load_dotenv(BASE_DIR / '.env')
load_dotenv(BASE_DIR / 'alvix' / '.env')


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [item.strip() for item in os.environ.get(name, default).split(',') if item.strip()]


# ---------------------------------------------------------------------------
# Core / security
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

# Defaults to True for local development; set DJANGO_DEBUG=False in production.
DEBUG = env_bool('DJANGO_DEBUG', True)

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')

CSRF_TRUSTED_ORIGINS = env_list(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    'http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:5173,http://localhost:5173',
)


# Railway: its public domain is provided automatically; trust it without extra config.
RAILWAY_PUBLIC_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '').strip()
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)
    CSRF_TRUSTED_ORIGINS.append(f'https://{RAILWAY_PUBLIC_DOMAIN}')
if os.environ.get('RAILWAY_ENVIRONMENT'):
    ALLOWED_HOSTS.append('healthcheck.railway.app')  # Railway's deploy health check Host header

# Behind a TLS-terminating proxy (Railway edge, Vercel rewrites): trust X-Forwarded-Proto so
# request.is_secure() is right and secure cookies / CSRF origin checks work.
if env_bool('DJANGO_TRUST_PROXY_SSL_HEADER', not DEBUG):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    SESSION_COOKIE_SECURE = env_bool('DJANGO_SECURE_COOKIES', True)
    CSRF_COOKIE_SECURE = env_bool('DJANGO_SECURE_COOKIES', True)
    SECURE_CONTENT_TYPE_NOSNIFF = True


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'alvixapp',
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

ROOT_URLCONF = 'alvix.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'alvix.wsgi.application'


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# PostgreSQL (Supabase) is used when DB_HOST is set; otherwise local SQLite.
if os.environ.get('DB_HOST'):
    DB_PORT = os.environ.get('DB_PORT', '5432')
    # Supabase transaction pooler (port 6543): connections are shared per transaction, so
    # Django must not keep them open, use server-side cursors or prepared statements.
    DB_TRANSACTION_POOLER = env_bool('DB_TRANSACTION_POOLER', DB_PORT == '6543')
    _db_options = {
        'sslmode': os.environ.get('DB_SSLMODE', 'require'),
        'connect_timeout': 15,
    }
    if DB_TRANSACTION_POOLER:
        _db_options['prepare_threshold'] = None
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': os.environ['DB_HOST'],
            'PORT': DB_PORT,
            'NAME': os.environ.get('DB_NAME', 'postgres'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'CONN_MAX_AGE': 0 if DB_TRANSACTION_POOLER else int(os.environ.get('DB_CONN_MAX_AGE', '60')),
            'CONN_HEALTH_CHECKS': True,
            'DISABLE_SERVER_SIDE_CURSORS': DB_TRANSACTION_POOLER,
            'OPTIONS': _db_options,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.environ.get('DJANGO_DB_PATH') or (BASE_DIR / 'db.sqlite3'),
            'OPTIONS': {
                'timeout': 60,
            },
        }
    }

# Supabase project (for supabase-js / REST use; the secret key is server-side only)
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_PUBLISHABLE_KEY = os.environ.get('SUPABASE_PUBLISHABLE_KEY', '')
SUPABASE_SECRET_KEY = os.environ.get('SUPABASE_SECRET_KEY', '')
# Uploads (FileField/ImageField) go to this Supabase Storage bucket when it is set.
SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', '')
SUPABASE_STORAGE_PUBLIC = env_bool('SUPABASE_STORAGE_PUBLIC', True)
USE_SUPABASE_STORAGE = bool(SUPABASE_URL and SUPABASE_SECRET_KEY and SUPABASE_STORAGE_BUCKET)

STORAGES = {
    'default': {
        'BACKEND': 'alvixapp.supabase_storage.SupabaseStorage' if USE_SUPABASE_STORAGE
        else 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Argon2 (Django's recommended hasher) is much faster to verify than PBKDF2's ~1.2M rounds
# on modest hardware, so logins/signups stay quick. Used only when argon2-cffi is installed;
# existing PBKDF2 hashes keep working and are upgraded to Argon2 on the user's next login.
try:
    import argon2  # noqa: F401
except ImportError:
    pass
else:
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.Argon2PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
        'django.contrib.auth.hashers.ScryptPasswordHasher',
    ]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Sessions persist for 14 days and survive browser close
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 1209600
SESSION_ENGINE = 'django.contrib.sessions.backends.db'


# ---------------------------------------------------------------------------
# Django REST Framework (session auth, same origin as the React app)
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'alvixapp.api.common.CsrfSessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'EXCEPTION_HANDLER': 'alvixapp.api.exceptions.api_exception_handler',
}


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static, media, public and the React build
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static', BASE_DIR / 'public']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

PUBLIC_ROOT = BASE_DIR / 'public'

# Serve /media/ from Django (single-server deployments). Disable if a web server serves it.
ALVIX_SERVE_MEDIA = env_bool('ALVIX_SERVE_MEDIA', True)

# Output of `npm run build` in frontend/ — served by Django for SPA routes.
FRONTEND_DIST_DIR = Path(os.environ.get('FRONTEND_DIST_DIR', REPO_DIR / 'frontend' / 'dist'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = os.environ.get('DJANGO_DEFAULT_FROM_EMAIL', 'ALVIX <no-reply@alvix.local>')
EMAIL_HOST = os.environ.get('DJANGO_EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('DJANGO_EMAIL_PORT', '587') or 587)
EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('DJANGO_EMAIL_USE_TLS', True)


# ---------------------------------------------------------------------------
# AI integrations
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')


# ---------------------------------------------------------------------------
# ALVIX course rules
# ---------------------------------------------------------------------------
THEORETICAL_COURSE_DAYS = 7
PRACTICAL_COURSE_DAYS = 10
MIXED_COURSE_DAYS = 12

COURSE_PLAN_DURATIONS = {
    'Theoretical': THEORETICAL_COURSE_DAYS,
    'Theory': THEORETICAL_COURSE_DAYS,
    'Practical': PRACTICAL_COURSE_DAYS,
    'Mixed': MIXED_COURSE_DAYS,
}

# Daily scoring component weights (within each day: 20% / 40% / 40%)
DAY_SCORE_WEIGHTS = {
    'watch_time': 0.20,
    'assignment': 0.40,
    'quiz': 0.40,
}

# Course pass mark (%)
COURSE_PASS_MARK = 35

# Tests never call Gemini/YouTube (keys are blanked by the runner)
TEST_RUNNER = 'alvix.test_runner.HermeticTestRunner'

# Which UI answers page URLs: 'react' (SPA from frontend/dist) or 'templates' (legacy Django templates)
ALVIX_FRONTEND = os.environ.get('ALVIX_FRONTEND', 'react').strip().lower()
