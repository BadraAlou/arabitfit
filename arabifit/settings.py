import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)

# Hosts autorisés pour le développement
#ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '*']
ALLOWED_HOSTS = ['180.149.196.81', 'biodetoxmali.com', 'localhost', '127.0.0.1']


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_bootstrap5',
    'boutique',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'arabifit.urls'

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
                'boutique.context_processors.panier_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'arabifit.wsgi.application'

# Database - SQLite pour le développement
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'myproject',
        'USER': 'myprojectuser',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Password validation
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
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')
# STATICFILES_DIRS = [
#     BASE_DIR / "static",
# ]
# STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
# MEDIA_URL = '/media/'
# MEDIA_ROOT = BASE_DIR / 'media'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Stripe Settings - Mode Test pour le développement
STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY', default='pk_test_51234567890abcdef')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='sk_test_51234567890abcdef')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='whsec_test_1234567890abcdef')

# CinetPay Settings - Mode Test pour le développement
CINETPAY_API_KEY = config('CINETPAY_API_KEY', default='test_api_key_123456789')
CINETPAY_SITE_ID = config('CINETPAY_SITE_ID', default='test_site_id_123')

# Login/Logout URLs
LOGIN_URL = 'boutique:connexion'
LOGIN_REDIRECT_URL = 'boutique:accueil'
LOGOUT_REDIRECT_URL = 'boutique:accueil'

# Email Configuration pour le développement (console backend)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=1025, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@biodetoxmali.local')

# URL de base pour le développement
BASE_URL = config('BASE_URL', default='http://127.0.0.1:8000')

# Taux de conversion XOF vers EUR (pour Stripe)
from decimal import Decimal

TAUX_XOF_EUR = Decimal('0.00152449')  # 1 XOF = 0.00152449 EUR

# Logging pour le développement
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'biodetoxmali.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'boutique': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'boutique.payments': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Créer le dossier logs s'il n'existe pas
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Settings spécifiques au développement
if DEBUG:
    # Désactiver les redirections HTTPS en développement
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

    # Permettre les iframes pour les tests
    X_FRAME_OPTIONS = 'SAMEORIGIN'

    # Désactiver la protection HSTS en développement
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

    # Autoriser tous les hosts en développement (pour ngrok, etc.)
    ALLOWED_HOSTS = ['*']

    # Configuration pour les webhooks en développement local
    # Vous pouvez utiliser ngrok pour exposer votre serveur local
    WEBHOOK_BASE_URL = config('WEBHOOK_BASE_URL', default='http://127.0.0.1:8000')

    # Désactiver la vérification des webhooks en développement
    STRIPE_WEBHOOK_VERIFICATION = config('STRIPE_WEBHOOK_VERIFICATION', default=False, cast=bool)

    # Mode debug pour les templates
    TEMPLATES[0]['OPTIONS']['debug'] = True

# Configuration pour les tests
if 'test' in os.sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }


    # Désactiver les migrations pour les tests
    class DisableMigrations:
        def __contains__(self, item):
            return True

        def __getitem__(self, item):
            return None


    MIGRATION_MODULES = DisableMigrations()

    # Utiliser un backend email simple pour les tests
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

    # Désactiver les logs pendant les tests
    LOGGING_CONFIG = None

# Messages personnalisés
MESSAGE_TAGS = {
    50: 'danger',  # ERROR
    40: 'warning',  # WARNING
    30: 'warning',  # WARNING
    25: 'success',  # SUCCESS
    20: 'info',  # INFO
    10: 'debug',  # DEBUG
}

# Configuration des sessions
SESSION_COOKIE_AGE = 86400  # 24 heures
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Configuration du cache pour le développement
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'biodetoxmali-cache',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,
        }
    }
}

# Configuration pour les fichiers uploadés
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# Timezone pour les timestamps
USE_TZ = True

print("🚀 Django en mode DÉVELOPPEMENT")
print(f"📍 Base URL: {BASE_URL}")
print(f"🔧 Debug: {DEBUG}")
print(f"📧 Email Backend: {EMAIL_BACKEND}")