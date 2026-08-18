# Linux 部署

ForPay 只提供 Linux 部署说明，包含 Docker Compose 和源码两种方式，不提供 Windows 部署方案。生产环境必须使用 HTTPS，并将 PostgreSQL、Redis 和应用端口限制在内网或回环地址。

## Docker Compose 部署

1. 安装 Docker Engine 和 Compose 插件。
2. 复制 `.env.example` 为 `.env`，并替换所有生产密钥。
3. 将 `FORPAY_PUBLIC_BASE_URL` 设置为 Nginx 对外提供的 HTTPS 地址。
4. 启动服务：`docker compose up -d --build`。
5. 检查状态：`docker compose ps`、`docker compose logs app`，并执行 `curl http://127.0.0.1:8000/api/health`。

Compose 文件默认只把 API、PostgreSQL 和 Redis 绑定到 `127.0.0.1`。使用 Nginx 时不要删除这个限制。升级前必须备份 PostgreSQL 数据卷和 `data/` 目录。

## 源码部署

安装 Python 3.12、PostgreSQL 16、Redis 7、Node.js 20 和 Nginx。创建专用的非 root 用户，执行 `uv sync --extra dev` 安装后端依赖，执行 `npm ci && npm run build` 构建前端，运行 Alembic 迁移后再启动 Uvicorn。Uvicorn 和 worker 应作为两个 systemd 服务运行，并用 `ReadWritePaths` 只允许写入 `data/`。任何应用进程都不能以 root 运行。

## Nginx 反向代理

使用 Certbot 等工具配置 HTTPS，只把前端和 API 代理到 ForPay：

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

不要缓存 `/api/public/orders/`、`/api/monitor/` 和管理端响应。PostgreSQL、Redis 和 8000 端口不能暴露到公网。`FORPAY_CORS_ORIGINS` 必须填写准确的前端来源，不能设置为 `*`。

## 签名在线更新

管理接口 `GET /api/admin/update/check` 只检查通过 HTTPS 获取并经 Ed25519 公钥验证的更新清单。清单签名覆盖除 `signature` 外的规范化 JSON，必须包含 `version`、`url`、`sha256`，可选 `notes`。ForPay 永不自动执行下载代码；管理员必须人工审核签名、校验摘要、备份数据库和 `data/`，再按正常发布流程升级。将更新配置留空即可关闭远程检查。
