"""BRICS AIRWATCH — Django settings.

All credentials are read from environment variables (see .env.example).
Nothing sensitive is hard-coded and nothing secret is sent to the frontend.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

try:  # optional: load a local .env file
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
ON_CLOUD_RUN = bool(os.getenv("K_SERVICE"))  # set automatically by Google Cloud Run
ON_RENDER = bool(os.getenv("RENDER"))  # set automatically by Render
DEBUG = os.getenv("DJANGO_DEBUG", "False" if (ON_CLOUD_RUN or ON_RENDER) else "True").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

ALLOWED_HOSTS.extend([".run.app", ".onrender.com", ".trycloudflare.com", "*"])
CSRF_TRUSTED_ORIGINS.extend(["https://*.run.app", "https://*.onrender.com", "https://*.trycloudflare.com"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "dashboard",
    "pollution",
    "citizen_reports",
    "alerts",
    "ai_engine",
    "forecasting",
    "geospatial",
    "data_engine",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dashboard.context_processors.platform",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/overview/"
LOGOUT_REDIRECT_URL = "/"

# ---- Upload security -------------------------------------------------------
MAX_IMAGE_UPLOAD_MB = int(os.getenv("MAX_IMAGE_UPLOAD_MB", "5"))
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_IMAGE_UPLOAD_MB * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = (MAX_IMAGE_UPLOAD_MB + 2) * 1024 * 1024

# ---- Security headers ------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

try:  # whitenoise serves static files in production; optional for local dev
    import whitenoise  # noqa: F401
except ImportError:
    MIDDLEWARE.remove("whitenoise.middleware.WhiteNoiseMiddleware")
    STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}

# ---- REST framework (auth, CSRF via SessionAuthentication, rate limiting) --
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "240/min",
        "user": "600/min",
        "reports": "12/min",
        "ai": "30/min",
    },
}

# ---- Google ecosystem / external integrations (all optional) ---------------
INTEGRATIONS = {
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
    "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    "GOOGLE_MAPS_API_KEY": os.getenv("GOOGLE_MAPS_API_KEY", ""),
    "VERTEX_PROJECT_ID": os.getenv("VERTEX_PROJECT_ID", ""),
    "VERTEX_LOCATION": os.getenv("VERTEX_LOCATION", "asia-south1"),
    "VERTEX_ENDPOINT_ID": os.getenv("VERTEX_ENDPOINT_ID", ""),
    "EARTH_ENGINE_PROJECT": os.getenv("EARTH_ENGINE_PROJECT", ""),
    "BIGQUERY_PROJECT_ID": os.getenv("BIGQUERY_PROJECT_ID", ""),
    "BIGQUERY_DATASET": os.getenv("BIGQUERY_DATASET", "airwatch"),
    "FIREBASE_PROJECT_ID": os.getenv("FIREBASE_PROJECT_ID", ""),
    "GOOGLE_TRANSLATE_API_KEY": os.getenv("GOOGLE_TRANSLATE_API_KEY", ""),
    "DATA_GOV_IN_API_KEY": os.getenv("DATA_GOV_IN_API_KEY", ""),
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "loggers": {
        "airwatch": {"handlers": ["console"], "level": "INFO"},
        "airwatch.audit": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
