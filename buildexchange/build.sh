#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
# The demo database is a SQLite file created at build time, so the server can start straight away.
python manage.py migrate --no-input
python manage.py seed_demo
python manage.py seed_marketplace
