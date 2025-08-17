#!/usr/bin/env sh
set -e

# Use base settings by default unless explicitly overridden
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-destroyer.settings}"

# Ensure static and media directories exist and are writable
mkdir -p /app/staticfiles /app/media || true
chown -R appuser:appuser /app/staticfiles /app/media || true
chmod -R u+rwX /app/staticfiles /app/media || true

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
