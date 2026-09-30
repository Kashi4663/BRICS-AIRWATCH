#!/bin/sh
# Create the database and load the demo dataset on every container start, then serve.
set -e
python manage.py migrate --noinput
python manage.py seed_demo
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8080}" --workers 2 --threads 4 --timeout 90
