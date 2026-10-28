#!/bin/sh
# Container start-up: create a secret key once, wait for PostgreSQL, migrate,
# load the demo data on first run, then start the API + WebSocket server.
set -e

if [ -z "$DJANGO_SECRET_KEY" ]; then
  # Generated on first start and kept in the data volume (never in the image or repo).
  if [ ! -f /data/secret_key ]; then
    mkdir -p /data
    python -c "import secrets; print(secrets.token_urlsafe(50))" > /data/secret_key
  fi
  DJANGO_SECRET_KEY=$(cat /data/secret_key)
  export DJANGO_SECRET_KEY
fi

echo "Waiting for the database..."
until python -c "import psycopg, os; psycopg.connect(host=os.environ['POSTGRES_HOST'], dbname=os.environ['POSTGRES_DB'], user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD']).close()" 2>/dev/null; do
  sleep 1
done

python manage.py migrate --noinput

if python manage.py shell -c "import sys; from tournaments.models import Tournament; sys.exit(0 if Tournament.objects.exists() else 1)"; then
  echo "Existing data found; skipping demo data."
else
  echo "First start: loading demo data (4 live matches, password Cricket@123)."
  python manage.py seed_demo
fi

exec python manage.py runserver 0.0.0.0:8000
