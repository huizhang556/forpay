#!/usr/bin/env sh
set -eu

cd /app
test -f /app/alembic.ini || { echo "缺少 /app/alembic.ini" >&2; exit 1; }
grep -q '^script_location[[:space:]]*=' /app/alembic.ini || { echo "alembic.ini 缺少 script_location" >&2; exit 1; }
python /app/scripts/migrate.py
exec uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port 8000
