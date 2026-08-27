#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v docker >/dev/null || { echo "未找到 docker" >&2; exit 1; }
command -v uv >/dev/null || { echo "未找到 uv" >&2; exit 1; }
command -v npm >/dev/null || { echo "未找到 npm" >&2; exit 1; }
[[ -f .env ]] || cp .env.example .env
mkdir -p .local-notes
docker compose up -d postgres redis
uv sync --extra dev
uv run alembic -c alembic.ini upgrade head
[[ -d frontend/node_modules ]] || (cd frontend && npm ci)
uv run uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 7500 >.local-notes/dev-api.log 2>&1 &
API_PID=$!
(cd frontend && npm run dev -- --host 127.0.0.1) >.local-notes/dev-web.log 2>&1 &
WEB_PID=$!
cleanup() { kill "$API_PID" "$WEB_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
for _ in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:7500/api/health >/dev/null; then break; fi
    sleep 1
done
echo "前端：http://localhost:5173"
echo "API：http://127.0.0.1:7500/docs"
command -v xdg-open >/dev/null && xdg-open http://localhost:5173 >/dev/null 2>&1 || true
wait "$API_PID"
