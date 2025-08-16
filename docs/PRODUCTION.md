# Production deployment guide

This project includes a dedicated production settings module at `destroyer/settings/production.py`.

## Environment variables
Set the following variables in your production environment (do not commit secrets):

- DJANGO_SETTINGS_MODULE=destroyer.settings.production
- DJANGO_SECRET_KEY=long_random_secret
- DJANGO_ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
- DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
- Optional:
  - DJANGO_SECURE_HSTS_SECONDS=31536000
  - DJANGO_SECURE_PROXY_SSL_HEADER=1 (if behind a proxy setting X-Forwarded-Proto)
  - DJANGO_CORS_ALLOWED_ORIGINS=https://yourfrontend.com

See `.env.production.example` for a template.

## Security defaults in production.py
- DEBUG=False
- SESSION_COOKIE_SECURE=True
- CSRF_COOKIE_SECURE=True
- SECURE_SSL_REDIRECT=True
- SECURE_HSTS_SECONDS (defaults to 31536000 if not overridden)
- SECURE_HSTS_INCLUDE_SUBDOMAINS=True
- SECURE_HSTS_PRELOAD=True
- SECURE_REFERRER_POLICY=same-origin
- SECURE_CONTENT_TYPE_NOSNIFF=True
- X_FRAME_OPTIONS=DENY

## Local smoke test with production settings
Only for testing; not for real prod:

Windows PowerShell example:

$env:DJANGO_SETTINGS_MODULE = "destroyer.settings.production"
$env:DJANGO_SECRET_KEY = "replace_me_with_random"
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost"
$env:DJANGO_CSRF_TRUSTED_ORIGINS = "http://127.0.0.1,http://localhost"
python manage.py runserver

Note: Avoid SECURE_SSL_REDIRECT locally unless you proxy HTTPS.
