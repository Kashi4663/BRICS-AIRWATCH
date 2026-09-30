#!/usr/bin/env bash
set -e
python3 -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
python3 manage.py migrate
python3 manage.py seed_demo
python3 manage.py runserver
