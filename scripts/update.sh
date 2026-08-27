#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v docker >/dev/null || { echo "未找到 docker。" >&2; exit 1; }
docker compose version >/dev/null || { echo "未找到 docker compose 插件。" >&2; exit 1; }
[[ -f .env ]] || { echo "缺少 .env，请先执行 scripts/install.sh。" >&2; exit 1; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="data/backups/$STAMP"
mkdir -p "$BACKUP_DIR"
echo "正在备份数据库和二维码文件到 $BACKUP_DIR ..."
docker compose exec -T postgres pg_dump -U forpay -d forpay -Fc > "$BACKUP_DIR/forpay.dump"
if [[ -d data/qr ]]; then
    cp -a data/qr "$BACKUP_DIR/qr"
fi

docker compose pull
docker compose config --quiet
docker compose up -d
docker compose ps
echo "更新完成，备份保存在 $BACKUP_DIR。"
