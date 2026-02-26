import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-mock-key-for-dev")
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")

if not DEBUG and SECRET_KEY == "django-insecure-mock-key-for-dev":
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set in production (DEBUG=False)"
    )
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001"
).split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "apps.api",
    "apps.scraper.dataops",
    "django_celery_beat",
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.api.middleware.combined_auth.CombinedAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "apps.api.tier_throttles.TieredRateThrottle",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Tezca API",
    "DESCRIPTION": (
        "API for tezca.mx — Mexico's open law platform. "
        "Search, browse, and analyze 30,000+ federal and state laws in machine-readable format. "
        "Authenticate with API key (X-API-Key header) or Janua JWT (Bearer token)."
    ),
    "VERSION": "1.1.0",
    "CONTACT": {"name": "Tezca", "url": "https://tezca.mx"},
    "LICENSE": {"name": "AGPL-3.0"},
    "TAGS": [
        {
            "name": "Laws",
            "description": "Browse and retrieve law metadata and articles",
        },
        {
            "name": "Search",
            "description": "Full-text search across all indexed articles",
        },
        {
            "name": "Cross-References",
            "description": "Detect and browse inter-law references",
        },
        {
            "name": "Admin",
            "description": "System health, metrics, API key management, and ingestion",
        },
        {
            "name": "Export",
            "description": "Download laws in multiple formats (TXT, PDF, LaTeX, DOCX, EPUB, JSON) with tiered access",
        },
        {
            "name": "Bulk",
            "description": "Bulk data access and changelog feeds for data consumers",
        },
    ],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "Tezca API key (tzk_...)",
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Janua-issued JWT",
            },
        }
    },
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "apps.api.middleware.cors_apikey.APIKeyCORSMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

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

ROOT_URLCONF = "apps.indigo.urls"
WSGI_APPLICATION = "apps.indigo.wsgi.application"

if os.environ.get("DATABASE_URL") or os.environ.get("DB_ENGINE", "").startswith(
    "django.db.backends.postgresql"
):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "leyes_mx"),
            "USER": os.environ.get("DB_USER", "leyes_mx"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Production Security ───────────────────────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ── Janua Auth ────────────────────────────────────────────────────────
JANUA_BASE_URL = os.environ.get("JANUA_BASE_URL", "")
JANUA_AUDIENCE = os.environ.get("JANUA_AUDIENCE", "tezca-api")

# ── Logging ───────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "django.utils.log.ServerFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "apps.api": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ── Sentry Error Tracking ─────────────────────────────────────────────
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
            release=os.environ.get("SENTRY_RELEASE", ""),
            traces_sample_rate=float(
                os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")
            ),
            send_default_pii=False,
            integrations=[DjangoIntegration(), CeleryIntegration()],
        )
    except ImportError:
        pass  # sentry-sdk not installed (optional dependency)

# ── Celery ──────────────────────────────────────────────────────────────
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
)
# ── Cache ──────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": CELERY_BROKER_URL,
        "TIMEOUT": 300,  # 5 minutes default
        "KEY_PREFIX": "tezca",
    }
}

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True

# ── Celery Beat Schedule ────────────────────────────────────────────────
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "health-check-critical-daily": {
        "task": "dataops.run_health_checks",
        "schedule": crontab(hour=6, minute=0),
        "kwargs": {"sources": "critical"},
    },
    "health-check-all-weekly": {
        "task": "dataops.run_health_checks",
        "schedule": crontab(hour=3, minute=0, day_of_week="sunday"),
        "kwargs": {"sources": "all"},
    },
    "detect-staleness-weekly": {
        "task": "dataops.detect_staleness",
        "schedule": crontab(hour=4, minute=0, day_of_week="monday"),
    },
    "retry-transient-monthly": {
        "task": "dataops.retry_transient_failures",
        "schedule": crontab(hour=5, minute=0, day_of_month="1"),
    },
    "coverage-report-monthly": {
        "task": "dataops.generate_coverage_report",
        "schedule": crontab(hour=6, minute=0, day_of_month="1"),
    },
    "dof-daily-check": {
        "task": "dataops.check_dof_daily",
        "schedule": crontab(hour=7, minute=0),
    },
}
