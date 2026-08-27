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
# 先校验变量和 Compose 文件，避免网络拉取完成后才发现配置错误。
docker compose config --quiet

check_registry() {
    local mirrors
    mirrors="$(docker info --format '{{json .RegistryConfig.Mirrors}}' 2>/dev/null || true)"
    if [[ -n "$mirrors" && "$mirrors" != "null" && "$mirrors" != "[]" ]]; then
        echo "检测到 Docker 已配置镜像加速：${mirrors}"
        echo "将通过 Docker 加速源拉取镜像，跳过 Docker Hub 直连预检。"
        return 0
    fi
    if ! command -v curl >/dev/null; then
        echo "未找到 curl，跳过 Docker Hub 连通性预检。"
        return 0
    fi
    local status
    status="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 10 --max-time 20 https://registry-1.docker.io/v2/ || true)"
    if [[ "$status" != "200" && "$status" != "401" ]]; then
        echo "警告：无法正常访问 Docker Hub（HTTP 状态：${status:-连接失败}）。镜像拉取可能因网络超时失败。" >&2
        echo "请检查 DNS、服务器公网出口、防火墙或 Docker 代理后重试。" >&2
    fi
}
check_registry

pull_images() {
    local attempt
    for attempt in 1 2 3; do
        if docker compose pull; then return 0; fi
        echo "镜像拉取失败，第 ${attempt}/3 次重试；请检查服务器 DNS、代理和 Docker Hub 出口。" >&2
        sleep $((attempt * 5))
    done
    echo "镜像拉取连续失败。可先配置 Docker 镜像加速或代理后重新执行本脚本。" >&2
    return 1
}
pull_images
docker compose up -d
docker compose ps
echo "安装完成。健康检查：curl http://127.0.0.1:${FORPAY_API_PORT:-7500}/api/health"
