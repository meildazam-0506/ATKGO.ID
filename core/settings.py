"""
Django settings for core project.
ATKGO.ID Production & Development Settings.
"""

import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Deteksi lingkungan Vercel / Production
IS_VERCEL = bool(os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-qfra=6k$-w(6x2++$tx4yjiet2w^y@(blnwda!=g^e+&s$hf1g'
)

# SECURITY WARNING: don't run with debug turned on in production!
if 'DEBUG' in os.environ:
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')
else:
    DEBUG = not IS_VERCEL

# ALLOWED_HOSTS
ALLOWED_HOSTS = [
    'atkgo-id.vercel.app',
    '.vercel.app',
    '127.0.0.1',
    'localhost',
    '[::1]',
    'testserver',
]
extra_hosts = os.environ.get('ALLOWED_HOSTS')
if extra_hosts:
    ALLOWED_HOSTS.extend([h.strip() for h in extra_hosts.split(',') if h.strip()])

# CSRF_TRUSTED_ORIGINS (wajib untuk domain HTTPS Vercel)
CSRF_TRUSTED_ORIGINS = [
    'https://atkgo-id.vercel.app',
    'https://*.vercel.app',
    'http://127.0.0.1',
    'http://localhost',
]
extra_csrf = os.environ.get('CSRF_TRUSTED_ORIGINS')
if extra_csrf:
    CSRF_TRUSTED_ORIGINS.extend([origin.strip() for origin in extra_csrf.split(',') if origin.strip()])

# Keamanan di balik reverse proxy Vercel
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'SAMEORIGIN'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app',
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

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates', BASE_DIR],
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

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# Fleksibel untuk Production Vercel (Remote MySQL / PostgreSQL / URL / SQLite Fallback)
# dan Local Development (MariaDB Docker port 3309)

if os.environ.get('DATABASE_URL'):
    db_url = urlparse(os.environ.get('DATABASE_URL'))
    engine = 'django.db.backends.mysql' if 'mysql' in db_url.scheme else 'django.db.backends.postgresql'
    DATABASES = {
        'default': {
            'ENGINE': engine,
            'NAME': db_url.path.lstrip('/'),
            'USER': db_url.username or '',
            'PASSWORD': db_url.password or '',
            'HOST': db_url.hostname or '',
            'PORT': str(db_url.port or (3306 if 'mysql' in engine else 5432)),
            'OPTIONS': {'charset': 'utf8mb4'} if 'mysql' in engine else {},
        }
    }
elif os.environ.get('DB_NAME') and (os.environ.get('DB_HOST') or IS_VERCEL):
    DATABASES = {
        'default': {
            'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.mysql'),
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {'charset': 'utf8mb4'},
        }
    }
elif IS_VERCEL:
    # Serverless runtime fallback jika remote database belum diatur di Vercel Dashboard
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(tempfile.gettempdir(), 'db.sqlite3'),
        }
    }
else:
    # Local Development Default (MariaDB Docker Port 3309)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'atkgo_db',
            'USER': 'root',
            'PASSWORD': 'rootpassword',
            'HOST': '127.0.0.1',
            'PORT': '3309',
            'OPTIONS': {
                'charset': 'utf8mb4',
            },
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'id-id'

TIME_ZONE = 'Asia/Jakarta'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Dukungan WhiteNoise untuk penyajian file statis langsung via WSGI di Vercel
WHITENOISE_USE_FINDERS = True

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'beranda'
LOGOUT_REDIRECT_URL = 'landing'

AUTHENTICATION_BACKENDS = [
    'app.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]


# =====================================
# KONFIGURASI EMAIL ATKGO.ID
# =====================================

if os.environ.get('EMAIL_HOST_USER'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_USE_SSL = False
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'no-reply@atkgo.id'
