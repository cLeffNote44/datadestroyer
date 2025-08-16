#!/usr/bin/env sh
set -e

# Require production settings unless explicitly overridden
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-destroyer.settings.production}"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
