#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

command -v docker >/dev/null || { echo "未找到 docker。" >&2; exit 1; }
docker compose version >/dev/null || { echo "未找到 docker compose 插件。" >&2; exit 1; }
[[ -f .env ]] || { echo "缺少 .env，请先执行 scripts/install.sh。" >&2; exit 1; }

default_dir="${FORPAY_BACKUP_DIR:-$ROOT/data/backups}"
read -r -p "请选择操作：[1] 本机备份 [2] 异地迁移（默认 1）：" mode
mode="${mode:-1}"
[[ "$mode" == "1" || "$mode" == "2" ]] || { echo "无效选择。" >&2; exit 1; }

read -r -p "本机备份目录（默认 $default_dir）：" backup_dir
backup_dir="${backup_dir:-$default_dir}"
mkdir -p "$backup_dir"
backup_dir="$(cd "$backup_dir" && pwd)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
work_dir="$backup_dir/forpay-$stamp"
mkdir -p "$work_dir"

echo "正在导出 PostgreSQL 数据库..."
docker compose exec -T postgres pg_dump -U forpay -d forpay -Fc > "$work_dir/forpay.dump"
if [[ -d data/qr ]]; then
    cp -a data/qr "$work_dir/qr"
fi
cp .env "$work_dir/env.backup"
chmod 600 "$work_dir/env.backup" "$work_dir/forpay.dump"
archive="$backup_dir/forpay-$stamp.tar.gz"
tar -C "$backup_dir" -czf "$archive" "forpay-$stamp"
rm -rf "$work_dir"
chmod 600 "$archive"
echo "备份已生成：$archive"

if [[ "$mode" == "2" ]]; then
    command -v scp >/dev/null || { echo "未找到 scp，请安装 openssh-client。" >&2; exit 1; }
    read -r -p "目标服务器用户：" remote_user
    read -r -p "目标服务器 IP 或域名：" remote_host
    read -r -p "SSH 端口（默认 22）：" remote_port
    remote_port="${remote_port:-22}"
    read -r -p "目标数据存放路径：" remote_path
    [[ -n "$remote_user" && -n "$remote_host" && -n "$remote_path" ]] || { echo "目标用户、地址和路径均不能为空。" >&2; exit 1; }
    [[ "$remote_port" =~ ^[0-9]+$ && "$remote_port" -ge 1 && "$remote_port" -le 65535 ]] || { echo "SSH 端口无效。" >&2; exit 1; }
    [[ "$remote_path" == /* && "$remote_path" != *[^a-zA-Z0-9._/-]* ]] || { echo "目标路径必须是绝对路径，且只能包含字母、数字、点、下划线、短横线和斜杠。" >&2; exit 1; }
    ssh_target="${remote_user}@${remote_host}"
    ssh -p "$remote_port" "$ssh_target" "mkdir -p -- '$remote_path'"
    scp -P "$remote_port" "$archive" "$ssh_target:$remote_path/"
    echo "异地迁移文件已复制到：$ssh_target:$remote_path/"
fi
