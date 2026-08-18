# ForPay

ForPay 是一个面向个人和小团队的本地收款码支付网关。它不调用微信或支付宝官方开放 API，而是通过人工上传收款二维码、订单唯一展示金额、手机到账通知和服务端严格匹配，解决暂时没有官方 API Key 时的过渡收款问题。

项目不伪造官方支付接口，也不承诺绕过平台风控。只有通道、金额、有效期和订单状态全部匹配时才会确认订单。

## 主要功能

- 微信和支付宝收款通道管理，支持 PNG、JPEG、WebP 二维码上传和文件内容校验。
- 二维码文件存放在私有目录，不通过公开静态目录直接暴露。
- 产品管理、商品结算、公开支付页面和订单专属高熵 `public_token`。
- Decimal 与 PostgreSQL NUMERIC 金额精度，以及并发订单金额尾数分配。
- 订单有效期、worker 自动过期和过期金额尾数释放。
- checkout 会话 HttpOnly Cookie、二维码接口鉴权、禁止缓存和 Redis 分布式限流。
- 到账通知 `external_id` 幂等去重，严格匹配通道、展示金额和有效期。
- 未匹配通知人工处理；人工补单校验通知状态、通道、金额和订单状态，并写入审计事件。
- 回调任务队列、失败重试、状态记录和商户回调 HMAC 签名。
- 商户 API Key、HMAC-SHA256 时间戳签名、五分钟防重放、幂等键和请求体限制。
- 管理端会话、独立监控端令牌、安全响应头和回调地址基础 SSRF 防护。
- 易支付兼容入口，方便后续接入独角数卡、Sub2API 或彩虹易支付适配层。
- 为未来 Android 通知监控预留独立认证边界，当前不包含 Android 客户端。
- Ed25519 签名更新清单检查，但不会自动执行远程代码。
- Docker Compose 编排 API、worker、PostgreSQL 和 Redis，支持 Linux 快速部署。

版本变更见 [VERSIONS.md](VERSIONS.md)，每个版本的具体功能、修复和验证结果都集中记录在这里。

## 技术栈

- 后端：Python 3.12、FastAPI、SQLAlchemy 2、Alembic、Pydantic。
- 数据库：PostgreSQL 16，金额字段使用 `NUMERIC`。
- 分布式组件：Redis 7，用于限流和多 API 实例共享状态。
- 前端：React 19、TypeScript、Vite、Ant Design。
- 安全：Argon2、Fernet、HMAC-SHA256、Ed25519、HttpOnly Cookie。
- 测试：Pytest、Ruff、TypeScript 构建检查。
- 部署：Linux Docker Compose，或 Linux 源码 + systemd + Nginx。

## 服务器要求

| 项目 | 最低要求 | 推荐配置 |
| --- | --- | --- |
| 操作系统 | Ubuntu 22.04 / Debian 12，64 位 | Ubuntu 24.04，64 位 |
| CPU | 2 核 | 4 核或更多 |
| 内存 | 2 GB，建议启用 2 GB swap | 4 GB 或更多 |
| 磁盘 | 10 GB 可用空间 | 20 GB 以上并定期备份 |
| 网络 | 可访问镜像仓库和更新清单地址 | 稳定公网连接 |

公网部署需要域名、HTTPS 证书和 Nginx。PostgreSQL、Redis 和应用端口不能直接暴露到公网。

## 部署前配置

完整的逐步部署教程、必选/建议/可选配置说明、systemd 服务和 Nginx 配置已写入本 README，生产部署不要跳过配置分级和上线检查清单。

```bash
cp .env.example .env
chmod 600 .env
```

| 配置项 | 用途 |
| --- | --- |
| `FORPAY_ENVIRONMENT` | 生产环境填写 `production` |
| `FORPAY_PUBLIC_BASE_URL` | 最终 HTTPS 订单地址 |
| `FORPAY_DATABASE_URL` | PostgreSQL 连接，多实例使用同一数据库 |
| `FORPAY_REDIS_URL` | Redis 连接，多实例必须使用同一个 Redis |
| `FORPAY_SESSION_SECRET` | 会话和敏感数据密钥 |
| `FORPAY_ADMIN_TOKEN` | 管理员登录令牌 |
| `FORPAY_MONITOR_TOKEN` | 到账监控令牌 |
| `FORPAY_ORDER_TTL_MINUTES` | 订单有效期，建议 10 至 15 分钟 |
| `FORPAY_AMOUNT_SUFFIX_CENTS` | 金额尾数步长 |
| `FORPAY_UPDATE_MANIFEST_URL` | 签名更新清单地址，留空关闭检查 |
| `FORPAY_UPDATE_PUBLIC_KEY` | 更新清单 Ed25519 公钥 |

生产环境会拒绝默认密钥。不要把 `.env`、数据库、二维码、备份和真实到账通知提交到 Git。

## Docker Compose 部署（推荐）

### 安装和启动

```bash
sudo apt update
sudo apt install -y git ca-certificates
sudo systemctl enable --now docker
git clone https://github.com/huizhang556/forpay.git
cd forpay
cp .env.example .env
nano .env
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/api/health
```

Compose 会启动 `app`、`worker`、`postgres` 和 `redis`。API、数据库和 Redis 默认只绑定回环地址；不要改成 `0.0.0.0`。

### 日常维护

```bash
docker compose logs -f app
docker compose logs -f worker
docker compose restart app worker
docker compose exec postgres pg_dump -U forpay -d forpay -Fc > forpay.dump
docker compose down
docker compose up -d
```

不要执行 `docker compose down -v`，除非确认要永久删除数据库和 Redis 数据卷。升级前必须备份数据库和 `data/` 目录。

## Linux 源码部署

源码部署适合需要审查和修改代码的场景，生产环境仍建议优先使用 Compose。安装 Python 3.12、Node.js 20、PostgreSQL 16、Redis 7、Nginx 和 uv，然后执行：

```bash
git clone https://github.com/huizhang556/forpay.git
cd forpay
cp .env.example .env
uv sync --extra dev
cd frontend && npm ci && npm run build && cd ..
uv run alembic -c alembic.ini upgrade head
```

使用专用非 root 用户分别运行 API 和 worker，配置 systemd 的 `Restart=on-failure`、`NoNewPrivileges=true` 和最小 `ReadWritePaths`。

## Nginx 反向代理

ForPay 不建议直接暴露 Uvicorn。Nginx 应负责 TLS、域名、请求体大小和反向代理：

```nginx
server {
    listen 443 ssl http2;
    server_name pay.example.com;
    client_max_body_size 8m;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_read_timeout 30s;
    }
}
```

不要缓存 `/api/public/orders/`、`/api/monitor/` 和管理端响应；必须保留 `Set-Cookie`。`FORPAY_CORS_ORIGINS` 只能填写明确来源，不能使用 `*`。

## 使用流程

1. 管理员创建微信或支付宝收款通道并上传真实二维码。
2. 创建产品或通过商户签名接口创建订单。
3. 将订单支付页地址交给用户，用户按照页面展示金额扫码支付。
4. 受保护的监控端提交到账通知，服务端校验通道、金额、有效期和通知编号。
5. 匹配成功后订单进入已支付和回调队列；无法匹配的通知进入人工复核。
6. 人工补单前必须确认手机账单、通道、金额和订单号。

没有官方 API 时，系统不能生成微信或支付宝官方指定金额收款码。当前展示的是人工上传的收款码，订单金额通过到账通知确认，不应把用户输入金额作为可信支付凭据。

## 安全边界

- 订单 token 是 bearer 凭据，不得放入日志、公开网页或分析平台。
- checkout Cookie 只能降低二维码接口盗取，不能阻止拍照或转发已经显示的二维码。
- 订单有效期应尽量短，到账通知必须幂等，人工补单必须保留审计记录。
- 管理令牌、监控令牌、商户密钥和数据库备份必须单独保管并定期轮换。
- 正式承载资金前必须完成 DNS 级 SSRF 防护、管理员 RBAC、Android 设备凭据、故障演练和备份恢复演练。

详细要求见本 README 的“安全边界”和“部署前配置”章节。

## 在线更新

管理员可以调用 `GET /api/admin/update/check` 检查签名更新清单。清单通过 HTTPS 获取，并使用 Ed25519 公钥验证；包地址和 SHA-256 摘要也会校验。ForPay 不会在 API 进程中自动下载、解压或执行远程代码。更新前应备份 PostgreSQL 和 `data/`，再通过审核后的镜像或源码流程升级。

## 测试和质量检查

```bash
uv run ruff check backend
uv run pytest
cd frontend && npm ci && npm run build && cd ..
docker compose config --quiet
```

## 版本记录

- [VERSIONS.md](VERSIONS.md)：每次版本的详细功能、修复、验证结果和已知限制。

## 许可证

本项目处于开发和安全验证阶段。使用前请确认符合当地法律、支付平台规则和收款账户要求。软件按“原样”提供，不承诺规避平台风控或替代官方支付接口。
