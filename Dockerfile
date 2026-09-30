# BRICS AIRWATCH — container for Google Cloud Run
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput && chmod +x entrypoint.sh
EXPOSE 8080
CMD ["./entrypoint.sh"]
