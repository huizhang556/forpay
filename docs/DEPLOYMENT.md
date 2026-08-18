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
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/api/health
```

Compose 中数据库主机必须是 `postgres`，Redis 主机必须是 `redis`。生产环境只把 API 绑定到回环地址，由 Nginx 提供 443。升级前使用 `pg_dump` 备份数据库和 `data/` 目录，不要执行 `docker compose down -v`。

## Linux 源码部署

创建非 root 用户，安装 Python 3.12、Node.js 20、PostgreSQL 16、Redis 7、Nginx 和 uv。源码部署的数据库和 Redis 通常使用 `127.0.0.1`，不能使用 Compose 服务名：

```dotenv
FORPAY_DATABASE_URL=postgresql+psycopg://forpay:数据库密码@127.0.0.1:5432/forpay
FORPAY_REDIS_URL=redis://127.0.0.1:6379/0
```

安装依赖、迁移数据库、构建前端后，用 systemd 分别运行 API 和 worker。服务必须使用非 root 用户、`NoNewPrivileges=true` 和最小 `ReadWritePaths`。

## Nginx

Nginx 负责 HTTPS、域名、8 MB 请求体限制和反向代理。不要缓存订单、二维码、管理端、监控端和 `/metrics`；必须保留 checkout Cookie 的 `Set-Cookie`。
