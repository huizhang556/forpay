#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PURGE=false
if [[ "${1:-}" == "--purge-data" ]]; then PURGE=true; fi

if [[ "$PURGE" == true ]]; then
    echo "警告：这将停止服务并永久删除 PostgreSQL、Redis 数据卷。"
    read -r -p "请输入 DELETE-FORPAY 确认：" answer
    [[ "$answer" == "DELETE-FORPAY" ]] || { echo "已取消，数据未删除。"; exit 1; }
    docker compose down -v
    echo "服务和数据卷已删除；.env、源码和 data 目录仍保留。"
else
    docker compose down
    echo "服务已停止并移除，数据卷已保留。需要删除数据时请执行：scripts/uninstall.sh --purge-data"
fi
