#!/usr/bin/env bash
set -o errexit
# Hosted defaults: debug off, and a random secret key if none is set (sessions reset on restart, which is fine for a demo).
export DEBUG="${DEBUG:-0}"
if [ -z "${SECRET_KEY:-}" ]; then
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
  export SECRET_KEY
fi
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 --timeout 120
