import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR.parent / "data" / "web"

# True when running under pytest or when TESTING=1 is exported.
TESTING = bool(int(os.getenv("TESTING", "0"))) or "pytest" in sys.modules or any(
    arg.startswith("test") for arg in sys.argv
)


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")

# SECURITY WARNING: don't run with debug turned on in production!
# So vai funcionar se tiver a variavel de ambiente diferente de 0
DEBUG = bool(int(os.getenv("DEBUG", 0)))

# Pega o allowed hosts e cria uma lista dos itens que estao separados por virgula
# O strip remove os espaços e so adiciona se o valor nao for vazio
ALLOWED_HOSTS = [
    h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()
]

if DEBUG:
    ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "users",
    "rest_framework_simplejwt",
    "bbq_reservations",
    "hall_reservations",
    "visitor_access",
    "service_requests",
    "condo_payments",
    "delivery_notification",
    "sunny_vale_news",
    "households",
    "admin_dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# CORS — wide-open in dev so the front (any port/host on the LAN) talks to
# the API; tightened in prod by feeding a comma-separated CORS_ALLOWED_ORIGINS.
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = [
        h.strip()
        for h in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if h.strip()
    ]

ROOT_URLCONF = "sunnyValeConnect.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "sunnyValeConnect.wsgi.application"


if TESTING:
    # In-memory SQLite so tests run anywhere (CI, local, no Postgres needed).
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
            "NAME": os.getenv("POSTGRES_DB", "change-me"),
            "USER": os.getenv("POSTGRES_USER", "change-me"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "change-me"),
            "HOST": os.getenv("POSTGRES_HOST", "psql"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "TEST": {
                "NAME": "test_" + os.getenv("POSTGRES_DB", "change-me"),
                "MIRROR": None,
            },
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "/static/"
# /data/web/static
STATIC_ROOT = DATA_DIR / "static"

MEDIA_URL = "/media/"
# /data/web/media
MEDIA_ROOT = DATA_DIR / "media"


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "shared.exception_handler.custom_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SunnyvaleConnect API",
    "DESCRIPTION": "API of a condominium management system: users, reservations, "
    "visitor access, service requests, payments, deliveries and news.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
    },
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "CondoPaymentStatusEnum": "condo_payments.models.CondoPaymentModel.STATUS",
        "ServiceRequestStatusEnum": "service_requests.models.ServiceRequestModel.STATUS",
        # Priority levels happen to share (low/medium/high) across 3 apps; unify.
        "PriorityEnum": "service_requests.models.ServiceRequestModel.PRIORITY_LEVEL",
        "HouseholdStatusEnum": "households.models.Household.Status",
        "MembershipStatusEnum": "households.models.HouseholdMembership.Status",
        "MembershipRoleEnum": "households.models.HouseholdMembership.Role",
        "UserRoleEnum": "users.models.UserRole",
        "NewsKindEnum": "sunny_vale_news.models.SunnyValeNewsModel.Kind",
    },
}

from datetime import timedelta  # noqa: E402

...

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "BLACKLIST_AFTER_ROTATION": False,
    "SIGNING_KEY": os.getenv("SIGNING_KEY", "change-me"),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# settings.py
# Change from console to smtp when is not developer
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "pythondjango703@gmail.com"
EMAIL_HOST_PASSWORD = "Toszo0-qursoz-fatjif"
DEFAULT_FROM_EMAIL = "pythondjango703@gmail.com"

if TESTING:
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]
