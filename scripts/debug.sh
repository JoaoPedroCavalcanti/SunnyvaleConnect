#!/bin/sh

set -e

while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  echo "🟡 Waiting for Postgres Database Startup ($POSTGRES_HOST $POSTGRES_PORT) ..."
  sleep 2
done

echo "✅ Postgres Database Started Successfully ($POSTGRES_HOST:$POSTGRES_PORT)"

python manage.py collectstatic --noinput
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "🐛 Waiting for debugger to attach on 0.0.0.0:5678 ..."
exec python -Xfrozen_modules=off -m debugpy \
  --listen 0.0.0.0:5678 \
  --wait-for-client \
  manage.py runserver 0.0.0.0:8000 --noreload --nothreading
