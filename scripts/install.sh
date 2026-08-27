#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

command -v docker >/dev/null || { echo "未找到 docker，请先安装 Docker Engine 和 Compose 插件。" >&2; exit 1; }
docker compose version >/dev/null || { echo "未找到 docker compose 插件。" >&2; exit 1; }
command -v openssl >/dev/null || { echo "未找到 openssl，无法安全生成密钥。" >&2; exit 1; }

if [[ ! -f .env ]]; then
    cp .env.example .env
fi

set_env() {
    local key="$1" value="$2"
    if grep -q "^${key}=" .env; then
        sed -i "s#^${key}=.*#${key}=${value}#" .env
    else
        printf '\n%s=%s\n' "$key" "$value" >> .env
    fi
}

set_env_if_placeholder() {
    local key="$1" value="$2" current
    current="$(grep -E "^${key}=" .env | head -n1 | cut -d= -f2- || true)"
    if [[ -z "$current" || "$current" == *"请替换"* || "$current" == change-this* || "$current" == local-* ]]; then
        set_env "$key" "$value"
    fi
}

set_env_if_placeholder POSTGRES_PASSWORD "$(openssl rand -hex 24)"
set_env_if_placeholder FORPAY_SESSION_SECRET "$(openssl rand -hex 32)"
set_env_if_placeholder FORPAY_ADMIN_TOKEN "$(openssl rand -hex 32)"
set_env_if_placeholder FORPAY_MONITOR_TOKEN "$(openssl rand -hex 32)"
set_env_if_placeholder FORPAY_ENCRYPTION_KEY "$(openssl rand -hex 32)"
chmod 600 .env

echo "配置已生成到 .env。请先确认 FORPAY_PUBLIC_BASE_URL、FORPAY_CORS_ORIGINS 和 FORPAY_ENVIRONMENT。"
docker compose pull
docker compose config --quiet
docker compose up -d
docker compose ps
echo "安装完成。健康检查：curl http://127.0.0.1:${FORPAY_API_PORT:-7500}/api/health"
