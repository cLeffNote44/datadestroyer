#!/usr/bin/env sh
set -e

# Default to dev settings unless DJANGO_SETTINGS_MODULE is provided
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-destroyer.settings}"

python manage.py migrate --noinput

exec "$@"
