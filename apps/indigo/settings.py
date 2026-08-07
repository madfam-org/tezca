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
# Cluster-internal service-mesh DNS is allowed alongside public hostnames so
# that consuming services (Karafiel, etc.) can reach tezca-api over
# `tezca-api.tezca.svc.cluster.local` without each consumer having to set a
# bespoke Host header. Per the "Integration Policy (Zero Touch)" — tezca is
# a generic multi-tenant platform; supporting the K8s service DNS is part of
# being a good citizen in the mesh.
_default_hosts = (
    "*"
    if DEBUG
    else "tezca.mx,api.tezca.mx,admin.tezca.mx,tezca-api.tezca.svc.cluster.local"
)
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", _default_hosts).split(",")

CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001"
).split(",")
CORS_ALLOW_CREDENTIALS = True

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
    "apps.api.middleware.usage_logger.UsageLoggingMiddleware",
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
    # Per FEATURE_PARITY_PLAN_2026-04-27 §3.2 / RFC 0012, the production
    # Postgres is migrating to a CloudNativePG cluster (postgres-ha-rw
    # service for writes, postgres-ha-ro for reads). The cutover requires
    # no client code change — only DB_HOST flips to the new Service. But
    # a few connection-pool knobs improve survival during the <60s
    # failover window:
    #
    # - connect_timeout=5: fail fast on a dead primary so PgBouncer's
    #   queue rotates rather than blocking on a TCP timeout that defaults
    #   to system-wide minutes.
    # - keepalives_idle=30: detect dropped connections faster than the
    #   Linux default ~2h, so stale conns don't outlive a failover.
    # - CONN_MAX_AGE: 0 means "no connection persistence" — Django opens
    #   and closes a fresh connection per request. Combined with
    #   PgBouncer transaction-pooling, this is the simplest configuration
    #   that survives primary promotion without a Django reload.
    _pg_options: dict = {
        "connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", "5")),
        "keepalives": 1,
        "keepalives_idle": int(os.environ.get("DB_KEEPALIVES_IDLE", "30")),
        "keepalives_interval": 10,
        "keepalives_count": 3,
    }

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "leyes_mx"),
            "USER": os.environ.get("DB_USER", "leyes_mx"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "0")),
            "OPTIONS": _pg_options,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

if not DEBUG and DATABASES["default"]["ENGINE"].endswith("sqlite3"):
    import warnings

    warnings.warn(
        "SQLite is not recommended for production. "
        "Set DATABASE_URL or DB_ENGINE=django.db.backends.postgresql",
        RuntimeWarning,
        stacklevel=1,
    )

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
    # Exempt the health endpoint from the HTTP→HTTPS redirect.
    #
    # Public traffic is unaffected: Cloudflare terminates TLS and cloudflared
    # forwards X-Forwarded-Proto: https, which SECURE_PROXY_SSL_HEADER below
    # already honours, so https://api.tezca.mx/health keeps working exactly as
    # it does now. But in-cluster callers speak plain HTTP to
    # tezca-api.tezca.svc.cluster.local:8000 and set no such header, so
    # SecurityMiddleware answers 301 → https://api.tezca.mx/health before the
    # view ever runs. Verified 2026-08-06 inside a tezca-api pod.
    #
    # The kubelet probes never surfaced this because kubelet treats any 2xx OR
    # 3xx as success — the pods report Ready on a redirect that proves only
    # that SecurityMiddleware is loaded. The cloudflared uptime probe requires
    # status 200, so the redirect is a hard failure for it.
    #
    # Anchored to the single root health route (apps/indigo/urls.py
    # `path("health", ...)`, matched without the leading slash per Django's
    # SECURE_REDIRECT_EXEMPT contract). Every other path still redirects.
    SECURE_REDIRECT_EXEMPT = [r"^health$"]
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ── Janua Auth ────────────────────────────────────────────────────────
JANUA_ISSUER_URL = os.environ.get("JANUA_ISSUER_URL", "") or os.environ.get(
    "JANUA_BASE_URL", ""
)
JANUA_BASE_URL = JANUA_ISSUER_URL  # backwards compat alias
JANUA_AUDIENCE = os.environ.get("JANUA_AUDIENCE", "tezca-api")

# ── Admin Access ─────────────────────────────────────────────────────
TEZCA_ADMIN_USER_IDS = set(
    filter(None, os.environ.get("TEZCA_ADMIN_USER_IDS", "").split(","))
)

# ── Deployment Mode ──────────────────────────────────────────────────
TEZCA_DEPLOYMENT = os.environ.get("TEZCA_DEPLOYMENT", "self-hosted")

# When true, the daily DOF check materializes detected new-law / reform
# publications through the ingestion pipeline (download → parse → index).
# Default OFF: DOF nota URLs point at HTML detail pages that don't always
# resolve to a direct PDF, so an operator should validate materialization in
# staging (and confirm celery-beat is actually running) before enabling in
# prod. With the flag off, the daily task detects + logs only (prior behavior).
DOF_AUTO_INGEST_ENABLED = os.environ.get(
    "DOF_AUTO_INGEST_ENABLED", "false"
).lower() in (
    "true",
    "1",
    "yes",
)

# ── CRM Sync (Phynd-CRM) ────────────────────────────────────────────
CRM_WEBHOOK_URL = os.environ.get("CRM_WEBHOOK_URL", "")
CRM_WEBHOOK_SECRET = os.environ.get("CRM_WEBHOOK_SECRET", "")

# ── Dhanam Billing ───────────────────────────────────────────────────
DHANAM_WEBHOOK_SECRET = os.environ.get("DHANAM_WEBHOOK_SECRET", "")
DHANAM_CHECKOUT_URL = os.environ.get(
    "DHANAM_CHECKOUT_URL", "https://app.dhan.am/checkout"
)

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

# ── Quality Quarantine ────────────────────────────────────────────────────
QUALITY_QUARANTINE_GRADES = os.environ.get("QUALITY_QUARANTINE_GRADES", "D,F").split(
    ","
)

# ── Trial Configuration ──────────────────────────────────────────────────
TRIAL_DURATION_NO_CC_DAYS = int(os.environ.get("TRIAL_DURATION_NO_CC_DAYS", "3"))
TRIAL_DURATION_WITH_CC_DAYS = int(os.environ.get("TRIAL_DURATION_WITH_CC_DAYS", "21"))
TRIAL_VALID_PLANS = {"essentials", "academic", "institutional"}

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
    # ── Billing event bus consumer ──────────────────────────────────────
    "poll-billing-stream": {
        "task": "apps.api.tasks.poll_billing_stream",
        "schedule": 30.0,  # Every 30 seconds
    },
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
    # ── Data acquisition tasks ────────────────────────────────────────
    "treaty-weekly-check": {
        "task": "dataops.run_treaty_scraper",
        "schedule": crontab(hour=2, minute=0, day_of_week="wednesday"),
        "kwargs": {"fetch_details": True, "max_details": 50},
    },
    # Ingest three hours after the weekly treaty scrape — the discovered
    # catalog previously had no scheduled consumer (wiring-gap class).
    "treaty-catalog-ingest-weekly": {
        "task": "dataops.ingest_treaty_catalog",
        "schedule": crontab(hour=5, minute=0, day_of_week="wednesday"),
    },
    "nom-catalog-ingest-weekly": {
        "task": "dataops.ingest_nom_catalog",
        "schedule": crontab(hour=6, minute=0, day_of_week="thursday"),
    },
    "nom-weekly-discovery": {
        "task": "dataops.run_nom_scraper",
        "schedule": crontab(hour=3, minute=0, day_of_week="thursday"),
        "kwargs": {"priority_only": True, "max_results": 5000},
    },
    "conamer-weekly-scrape": {
        "task": "dataops.run_conamer_scraper",
        "schedule": crontab(hour=1, minute=0, day_of_week="saturday"),
        "kwargs": {"max_pages": 100},
    },
    "coverage-report-weekly": {
        "task": "dataops.generate_coverage_report",
        "schedule": crontab(hour=6, minute=0, day_of_week="monday"),
    },
    "parser-weekly-run": {
        "task": "dataops.run_parser_pipeline",
        "schedule": crontab(hour=5, minute=0, day_of_week="saturday"),
        "kwargs": {"new_only": True},
    },
    "expire-trials-hourly": {
        "task": "apps.api.tasks.expire_trials",
        "schedule": crontab(minute=0),  # every hour at :00
    },
    # ── Phase 16: New state scrapers ──────────────────────────────────
    "state-guerrero-monthly": {
        "task": "dataops.run_state_scraper",
        "schedule": crontab(hour=2, minute=0, day_of_month="5"),
        "kwargs": {"state_key": "guerrero"},
    },
    "state-nuevo-leon-monthly": {
        "task": "dataops.run_state_scraper",
        "schedule": crontab(hour=2, minute=30, day_of_month="5"),
        "kwargs": {"state_key": "nuevo_leon"},
    },
    # Ingest a few hours after the monthly state scraper runs above — the
    # scraped catalogs previously had no scheduled consumer (wiring-gap
    # class; see ingest_conamer_catalog / ingest_nom_catalog).
    "state-catalog-ingest-monthly": {
        "task": "dataops.ingest_state_catalogs",
        "schedule": crontab(hour=5, minute=0, day_of_month="5"),
    },
    # ── Phase 16: SCJN judicial corpus ────────────────────────────────
    "scjn-weekly-scrape": {
        "task": "dataops.scrape_scjn",
        "schedule": crontab(hour=0, minute=0, day_of_week="sunday"),
        "kwargs": {"max_items": 5000, "epoca": 10},
    },
    # ── Phase 17: Total Legal Universe Capture ──────────────────────
    "scjn-playwright-weekly": {
        "task": "dataops.scrape_scjn_playwright",
        "schedule": crontab(hour=22, minute=0, day_of_week="saturday"),
        "kwargs": {"max_items": 5000, "epoca": 11, "tipo": "jurisprudencia"},
    },
    # DESCOPED from auto-ingest (2026-07-16 wiring audit): both recovery
    # scripts below write raw, unparsed files (PDF/DOC/HTML) — not a
    # structured catalog an existing ingest_* command can parse — and never
    # touch GapRecord. No text-extraction/official_id-derivation step exists
    # to bridge them into the Law table with MVP-sized glue, unlike the
    # CONAMER/NOM/RMF/treaty catalogs. Output is consumed manually; see the
    # task docstrings in apps/scraper/scheduling/tasks.py for details.
    "ojn-recovery-monthly": {
        "task": "dataops.run_ojn_recovery",
        "schedule": crontab(hour=3, minute=0, day_of_month="10"),
        "kwargs": {"paths": "ab", "limit": 500},
    },
    "wayback-recovery-monthly": {
        "task": "dataops.run_wayback_recovery",
        "schedule": crontab(hour=1, minute=0, day_of_month="20"),
        "kwargs": {"limit": 200},
    },
    "dof-historical-quarterly": {
        "task": "dataops.run_dof_historical",
        "schedule": crontab(
            hour=2, minute=0, day_of_month="1", month_of_year="1,4,7,10"
        ),
        "kwargs": {"mode": "noms"},
    },
    # SAT publishes RMF + quarterly modifications + annex revisions on a
    # roughly quarterly cadence, with the annual RMF dropping in late
    # December. Run the 8th of every quarter month at 03:00 to catch any
    # publication from the prior quarter without colliding with the DOF
    # 1st-of-quarter task above. Required by Karafiel's compliance feed
    # (FEATURE_PARITY_PLAN_2026-04-27 §3.6).
    "rmf-quarterly-scrape": {
        "task": "dataops.run_rmf_scraper",
        "schedule": crontab(
            hour=3, minute=0, day_of_month="8", month_of_year="1,4,7,10"
        ),
        "kwargs": {"include_annexes": True, "download_documents": True},
    },
    # Ingest the day after the quarterly scrape — without this the RMF
    # catalog only ever reached disk, never the Law table (wiring-gap
    # class; see ingest_conamer_catalog).
    "rmf-catalog-ingest-quarterly": {
        "task": "dataops.ingest_rmf_catalog",
        "schedule": crontab(
            hour=3, minute=0, day_of_month="9", month_of_year="1,4,7,10"
        ),
    },
    "conamer-playwright-weekly": {
        "task": "dataops.run_conamer_playwright",
        "schedule": crontab(hour=23, minute=0, day_of_week="friday"),
        "kwargs": {"max_pages": 200},
    },
    "check-scraper-health-daily": {
        "task": "dataops.check_scraper_health",
        "schedule": crontab(hour=8, minute=0),
    },
    "nom-monthly-full": {
        "task": "dataops.run_nom_scraper",
        "schedule": crontab(hour=2, minute=0, day_of_month="15"),
        "kwargs": {"priority_only": False, "max_results": 5000},
    },
    # ── Phase: Judicial auto-ingest + domain classification ──────────
    "judicial-ingest-weekly": {
        "task": "dataops.ingest_judicial_batches",
        "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
    },
    # Ingest the scraped CONAMER catalog into the DB. Runs after both weekly
    # scrapes land (Fri 23:00 playwright + Sat 01:00 http) so a scrape actually
    # reaches the Law table instead of sitting as JSON on disk.
    "conamer-ingest-weekly": {
        "task": "dataops.ingest_conamer_catalog",
        "schedule": crontab(hour=4, minute=0, day_of_week="saturday"),
    },
    "classify-domains-weekly": {
        "task": "dataops.classify_law_domains",
        "schedule": crontab(hour=5, minute=30, day_of_week="monday"),
    },
}
