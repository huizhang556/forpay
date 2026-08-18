# Linux deployment

ForPay supports Linux Docker Compose deployment and Linux source deployment. Windows deployment is intentionally out of scope.

## Docker Compose

1. Install Docker Engine and the Compose plugin.
2. Copy `.env.example` to `.env` and replace every production secret with random values.
3. Set `FORPAY_PUBLIC_BASE_URL` to the HTTPS URL exposed by Nginx.
4. Start the stack: `docker compose up -d --build`.
5. Verify with `docker compose ps`, `docker compose logs app`, and `curl http://127.0.0.1:8000/api/health`.

The compose file binds API, PostgreSQL, and Redis to loopback only. Do not remove those bindings when Nginx is used. Back up the PostgreSQL volume and `data/` before upgrades.

## Source deployment

Install Python 3.12+, PostgreSQL 16, Redis 7, Node.js 20+, and Nginx. Create a dedicated unprivileged `forpay` user, install backend dependencies with `uv sync --extra dev`, build the frontend with `npm ci && npm run build`, and run Alembic migrations before starting Uvicorn. Run Uvicorn and the worker as separate systemd services with restrictive `ReadWritePaths` for `data/` only. Never run either process as root.

## Nginx reverse proxy

Use HTTPS (for example, Certbot) and proxy only the API and frontend:

```nginx
server {
    listen 443 ssl http2;
    server_name pay.example.com;

    client_max_body_size 8m;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_read_timeout 30s;
        proxy_no_cache 1;
        add_header Cache-Control "no-store" always;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
    }
}
```

Do not cache `/api/public/orders/`, `/api/monitor/`, or admin responses. Keep PostgreSQL, Redis, and port 8000 unreachable from the public interface. Set `FORPAY_CORS_ORIGINS` to the exact frontend origin, not `*`.

## Signed online updates

The admin endpoint `GET /api/admin/update/check` only accepts a manifest fetched over HTTPS and verified with an Ed25519 public key. The manifest signature covers canonical JSON (all fields except `signature`) and must include `version`, `url`, `sha256`, and optional `notes`. ForPay never executes downloaded code automatically. Review the signed release, verify the package digest, back up the database and `data/`, then deploy the image or source through the normal release process and roll back if health checks fail. Leave update settings empty to disable remote checking.
