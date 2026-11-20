#!/bin/bash
set -e

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Celery worker..."
celery -A config worker --loglevel=info --concurrency=1 &
CELERY_PID=$!

echo "Starting Gunicorn..."
gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-10000} \
    --workers 1 \
    --timeout 120 &
GUNICORN_PID=$!

cleanup() {
    echo "Stopping application processes..."
    kill "$CELERY_PID" "$GUNICORN_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

wait -n "$CELERY_PID" "$GUNICORN_PID"
