#!/usr/bin/env sh
set -e

# Use base settings by default unless explicitly overridden
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-destroyer.settings}"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
