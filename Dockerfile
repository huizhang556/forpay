FROM node:24-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl libpq5 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY alembic.ini ./alembic.ini
COPY backend/ ./backend/
COPY scripts/start-api.sh ./scripts/start-api.sh
COPY scripts/migrate.py ./scripts/migrate.py
COPY --from=frontend /build/frontend/dist ./frontend/dist
RUN pip install --no-cache-dir ".[dev]"
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1
CMD ["sh", "/app/scripts/start-api.sh"]
