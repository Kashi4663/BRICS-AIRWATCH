@echo off
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
