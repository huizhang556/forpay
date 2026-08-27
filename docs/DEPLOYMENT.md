# 部署指南

ForPay 只支持 Linux。推荐 Docker Compose；需要二次开发时使用 Linux 源码部署。

## 配置优先级

必选配置：`FORPAY_ENVIRONMENT`、`FORPAY_PUBLIC_BASE_URL`、`FORPAY_DATABASE_URL`、`FORPAY_REDIS_URL`、`FORPAY_SESSION_SECRET`、`FORPAY_ADMIN_TOKEN`、`FORPAY_MONITOR_TOKEN`、`FORPAY_ENCRYPTION_KEY` 和准确的 `FORPAY_CORS_ORIGINS`。

建议配置：订单有效期、金额尾数、请求体限制、Redis 限流、数据库连接池、WAF 和 Prometheus 指标。在线更新地址和 Ed25519 公钥是可选配置。

## Docker Compose

```bash
cp .env.example .env
chmod 600 .env
nano .env
docker compose pull
docker compose config --images
docker compose up -d
docker compose ps
curl http://127.0.0.1:7500/api/health
```

Compose 中数据库主机必须是 `postgres`，Redis 主机必须是 `redis`。生产环境只把 API 绑定到回环地址，由 Nginx 提供 443。升级前使用 `pg_dump` 备份数据库和 `data/` 目录，不要执行 `docker compose down -v`。

上述命令使用 Docker Hub 远程镜像，app 和 worker 默认显示为 `litehub/forpay:latest`。API 默认绑定宿主机 `127.0.0.1:8000`，可通过 `.env` 的 `FORPAY_API_PORT` 修改。生产环境如需固定版本，可在 `.env` 中改为具体版本或 digest。源码构建时在 `.env` 设置 `FORPAY_IMAGE=forpay:local`，跳过 `docker compose pull`，执行 `docker compose build` 后再 `docker compose up -d`。

若出现端口已占用，使用 `docker ps --filter publish=8000` 或 `ss -ltnp | grep :8000` 查找占用者。确认是旧 ForPay 容器后执行 `docker compose down`（不要使用 `down -v`）；其他服务占用时，将 `FORPAY_API_PORT` 改为未占用端口，并同步修改 Nginx upstream。

启动时会先执行 `scripts/migrate.py`。如果数据库是早期版本通过 SQLAlchemy `create_all` 创建的完整表结构、但 `alembic_version` 为空，脚本会只写入当前版本标记，不删除或重建业务表；全新数据库仍会正常执行全部 Alembic migration。

## Linux 源码部署

创建非 root 用户，安装 Python 3.12、Node.js 20、PostgreSQL 16、Redis 7、Nginx 和 uv。源码部署的数据库和 Redis 通常使用 `127.0.0.1`，不能使用 Compose 服务名：

```dotenv
FORPAY_DATABASE_URL=postgresql+psycopg://forpay:数据库密码@127.0.0.1:5432/forpay
FORPAY_REDIS_URL=redis://127.0.0.1:6379/0
```

安装依赖、迁移数据库、构建前端后，用 systemd 分别运行 API 和 worker。服务必须使用非 root 用户、`NoNewPrivileges=true` 和最小 `ReadWritePaths`。

## Nginx

Nginx 负责 HTTPS、域名、8 MB 请求体限制和反向代理。不要缓存订单、二维码、管理端、监控端和 `/metrics`；必须保留 checkout Cookie 的 `Set-Cookie`。
