"""
Django settings for the brandextract project.

Extractions keep no state; the SQLite database exists only for the SSO user table.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

DEV_SECRET_KEY = 'dev-insecure-key-change-in-production'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', DEV_SECRET_KEY)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# De dev-sleutel ondertekent sessiecookies: wie hem kent, vervalst een sessie
# en komt zonder Google-login binnen. Buiten DEBUG dus weigeren te starten.
if not DEBUG and SECRET_KEY == DEV_SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY moet gezet zijn als DJANGO_DEBUG=False')

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

CSRF_TRUSTED_ORIGINS = [
    origin for origin in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if origin
]


# Aanzetten zodra HTTPS via certbot draait (zie DEPLOY.md stap 7).
if os.environ.get('DJANGO_SECURE_SSL') == 'True':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True


INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'rest_framework',
    'mozilla_django_oidc',
    'brandextract',
]

# Volgorde is dwingend: SessionMiddleware vóór AuthenticationMiddleware, en die vóór
# RequireLoginMiddleware — anders bestaat request.user nog niet bij de check.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'brandextract.middleware.RequireLoginMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Alleen voor django.contrib.auth: elke extractie draait in een temporary directory.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Uploads: DOCX/PDF are read straight into the extractor.

DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024


# Internationalization

LANGUAGE_CODE = 'nl-nl'

TIME_ZONE = 'Europe/Amsterdam'

USE_I18N = True

USE_TZ = True


# Static files

STATIC_URL = 'static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
}


# Google Workspace SSO

AUTHENTICATION_BACKENDS = ['brandextract.auth.WorkspaceOIDCBackend']

# Leeg domein weigert elke login — veilige kant om op te falen.
GOOGLE_WORKSPACE_DOMAIN = os.environ.get('GOOGLE_WORKSPACE_DOMAIN', '')

OIDC_RP_CLIENT_ID = os.environ.get('GOOGLE_OIDC_CLIENT_ID', '')
OIDC_RP_CLIENT_SECRET = os.environ.get('GOOGLE_OIDC_CLIENT_SECRET', '')

OIDC_OP_AUTHORIZATION_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
OIDC_OP_TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token'
OIDC_OP_USER_ENDPOINT = 'https://openidconnect.googleapis.com/v1/userinfo'
OIDC_OP_JWKS_ENDPOINT = 'https://www.googleapis.com/oauth2/v3/certs'

OIDC_RP_SIGN_ALGO = 'RS256'
OIDC_RP_SCOPES = 'openid email profile'

# Alleen een hint voor Google's accountkiezer; de echte check staat in verify_claims.
OIDC_AUTH_REQUEST_EXTRA_PARAMS = {'hd': GOOGLE_WORKSPACE_DOMAIN}

OIDC_CREATE_USER = True

LOGIN_URL = '/oidc/authenticate/'
LOGIN_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL_FAILURE = '/'
LOGOUT_REDIRECT_URL = '/'

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 12
