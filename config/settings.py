from pathlib import Path
from decouple import config, Csv
from datetime import timedelta
import dj_database_url
import dj_database_url
import cloudinary
import cloudinary.uploader
import cloudinary.api



BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceros
    'rest_framework',
    'rest_framework_simplejwt',
    'crispy_forms',
    'crispy_tailwind',
    'widget_tweaks',
    'django_htmx',

    # Apps locales
    'usuarios',
    'alumnos',
    'salud',
    'pagos',
    'eventos',
    'asistencia',
    'reportes',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Para estáticos
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',    
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
                'usuarios.context_processors.alertas_globales',  # ← NUEVO (ajustado a tu app 'usuarios')
            ],
        },
    },
]


WSGI_APPLICATION = 'config.wsgi.application'

# ===== BASE DE DATOS =====
# DATABASES = {
#     'default': dj_database_url.config(
#         default=config('DATABASE_URL'),
#         conn_max_age=600
#     )
# }
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': config('DB_NAME'),
#         'USER': config('DB_USER'),
#         'PASSWORD': config('DB_PASSWORD'),
#         'HOST': config('DB_HOST'),
#         'PORT': config('DB_PORT', default='5432'),
#         'CONN_MAX_AGE': 0,  # Importante para Neon/Supabase por cierre de conexiones
#         'OPTIONS': {
#             'sslmode': 'require',  # Obligatorio en la nube
#         },
#     }
# }
# ============================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================================
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=0,
            ssl_require=True,
        )
    }
else:
    # Fallback local
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 0,
            'OPTIONS': {'sslmode': 'require'},
        }
    }
# ===== AUTENTICACIÓN PERSONALIZADA =====
AUTH_USER_MODEL = 'usuarios.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ===== JWT =====
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=config('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=60, cast=int)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=config('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7, cast=int)
    ),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ===== INTERNACIONALIZACIÓN =====
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Santiago'  # Ajusta a tu zona
USE_I18N = True
USE_TZ = True

# ===== ARCHIVOS ESTÁTICOS Y MEDIA =====
#STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
#STATICFILES_DIRS = [BASE_DIR / 'static']
#MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ============================================================
# ARCHIVOS ESTÁTICOS (WhiteNoise) Y MEDIA (Cloudinary)
# ============================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

# WhiteNoise en producción
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    # Nota: Como ya tienes WhiteNoiseMiddleware en tu lista de MIDDLEWARE, 
    # esta línea asegura el almacenamiento optimizado en producción.

# Cloudinary en producción para archivos media
CLOUDINARY_URL = config('CLOUDINARY_URL', default=None)

if CLOUDINARY_URL:
    cloudinary.config(
        cloudinary_url=CLOUDINARY_URL,
        secure=True,
    )
    
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
        'API_KEY': config('CLOUDINARY_API_KEY', default=''),
        'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
    }
    
    MEDIA_URL = '/media/'
else:
    # Local
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'



# ===== CRISPY FORMS =====
CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

# ===== LOGIN =====
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_global'
LOGOUT_REDIRECT_URL = 'login'

# Configuración de imágenes
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE

# ===== CONFIGURACIÓN DE PAGOS =====
DIA_VENCIMIENTO_MENSUALIDAD = 5  # Día del mes en que vence
DIAS_ALERTA_VENCIMIENTO = 2       # Alerta de vencimiento próximo
PREFIJO_RECIBO = 'AL'             # ArmyLokk → AL-2025-0001

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# SEGURIDAD EN PRODUCCIÓN
# ============================================================
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ============================================================
# EMAIL (Recuperación de contraseña)
# ============================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)