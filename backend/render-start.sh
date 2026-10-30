#!/bin/sh
# Start-up on Render: update the database, create the admin account (and demo
# data if asked) on first run, then start the API + WebSocket server.
set -e

python manage.py migrate --noinput

if [ -n "$ADMIN_PASSWORD" ]; then
  python manage.py shell -c "
import os
from accounts.models import User
name = os.environ.get('ADMIN_USERNAME') or 'admin'
if not User.objects.filter(username=name).exists():
    User.objects.create_superuser(username=name, email=f'{name}@example.com', password=os.environ['ADMIN_PASSWORD'])
    print(f'Created admin account: {name}')
"
  if [ "$SEED_DEMO" = "true" ]; then
    if python manage.py shell -c "import sys; from tournaments.models import Tournament; sys.exit(0 if Tournament.objects.exists() else 1)"; then
      echo "Existing data found; skipping demo data."
    else
      echo "First start: loading demo data (demo accounts use ADMIN_PASSWORD)."
      python manage.py seed_demo --password "$ADMIN_PASSWORD"
    fi
  fi
else
  echo "ADMIN_PASSWORD is not set: no admin account or demo data created."
fi

exec daphne --bind 0.0.0.0 --port "${PORT:-10000}" --proxy-headers config.asgi:application
