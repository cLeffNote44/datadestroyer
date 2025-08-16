import os
from pathlib import Path

from .settings import *  # noqa

# Production overrides
DEBUG = False

# Compute BASE_DIR locally to avoid F405 from star import
BASE_DIR = Path(__file__).resolve().parent.parent
# Static files (served by WhiteNoise or proxy)
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "static/"

# Secret key must come from environment in production
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY environment variable must be set in production")

# Allowed hosts and CSRF trusted origins via environment
# Comma-separated values, e.g. "example.com,api.example.com"
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()
]
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# Cookie and HTTPS security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000"))  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# If behind a reverse proxy that sets X-Forwarded-Proto
if os.environ.get("DJANGO_SECURE_PROXY_SSL_HEADER", "1") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CORS settings for production (if needed)
# Provide comma-separated list via env: https://<domain>,http://<domain>
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]

# Logging (basic console logging suitable for JSON collection)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
}

# Debug toolbar and other dev-only apps/middleware should not be added here.
# Base settings only append them when DEBUG is True.
