#!/usr/bin/env bash
set -o errexit
# The demo database is SQLite on Render's temporary disk, so it is rebuilt and reseeded on every start.
python manage.py migrate --no-input
python manage.py seed_demo
python manage.py seed_marketplace
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 --timeout 120
