#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v docker >/dev/null || { echo "未找到 docker。" >&2; exit 1; }
docker compose version >/dev/null || { echo "未找到 docker compose 插件。" >&2; exit 1; }
[[ -f .env ]] || { echo "缺少 .env，请先执行 scripts/install.sh。" >&2; exit 1; }

check_registry() {
    local mirrors
    mirrors="$(docker info --format '{{json .RegistryConfig.Mirrors}}' 2>/dev/null || true)"
    if [[ -n "$mirrors" && "$mirrors" != "null" && "$mirrors" != "[]" ]]; then
        echo "检测到 Docker 镜像加速，将通过加速源拉取镜像。"
        return 0
    fi
    if command -v curl >/dev/null; then
        local status
        status="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 10 --max-time 20 https://registry-1.docker.io/v2/ || true)"
        if [[ "$status" != "200" && "$status" != "401" ]]; then
            echo "警告：Docker Hub 当前不可达（HTTP 状态：${status:-连接失败}），更新可能失败。" >&2
        fi
    fi
}
check_registry

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="data/backups/$STAMP"
mkdir -p "$BACKUP_DIR"
echo "正在备份数据库和二维码文件到 $BACKUP_DIR ..."
docker compose exec -T postgres pg_dump -U forpay -d forpay -Fc > "$BACKUP_DIR/forpay.dump"
if [[ -d data/qr ]]; then
    cp -a data/qr "$BACKUP_DIR/qr"
fi

pull_images() {
    local attempt
    for attempt in 1 2 3; do
        if docker compose pull; then return 0; fi
        echo "镜像拉取失败，第 ${attempt}/3 次重试；请检查服务器 DNS、代理和 Docker Hub 出口。" >&2
        sleep $((attempt * 5))
    done
    echo "镜像拉取连续失败，服务未更新。备份仍保留在 $BACKUP_DIR。" >&2
    return 1
}
pull_images
docker compose config --quiet
docker compose up -d
docker compose ps
echo "更新完成，备份保存在 $BACKUP_DIR。"
