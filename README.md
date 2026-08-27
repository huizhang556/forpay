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
| `FORPAY_ENCRYPTION_KEY` | 敏感数据加密密钥，生产必填且不能与其他密钥复用 |
| `FORPAY_ORDER_TTL_MINUTES` | 订单有效期，建议 10 至 15 分钟 |
| `FORPAY_AMOUNT_SUFFIX_CENTS` | 金额尾数步长 |
| `FORPAY_UPDATE_MANIFEST_URL` | 签名更新清单地址，留空关闭检查 |
| `FORPAY_UPDATE_PUBLIC_KEY` | 更新清单 Ed25519 公钥 |

生产环境会拒绝默认密钥。不要把 `.env`、数据库、二维码、备份和真实到账通知提交到 Git。

## 一键本地开发

本地开发只需要预先安装 Docker、uv 和 Node.js。脚本会自动创建 `.env`（不存在时）、启动 PostgreSQL/Redis、安装依赖、执行数据库迁移、启动 API 和前端，并尝试打开开发页面。开发日志写入被 Git 忽略的 `.local-notes/`，按 `Ctrl+C` 停止时不会删除数据库数据。

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

Linux：

```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

启动成功后访问 `http://localhost:5173`，API 文档访问 `http://127.0.0.1:7500/docs`。只有需要自定义端口、数据库或密钥时才需要提前编辑 `.env`。

## 部署总流程

无论选择哪种方式，生产部署都按以下顺序执行：

1. 准备 Linux 主机、域名和 HTTPS 证书，确认 PostgreSQL、Redis 与 API 端口不直接暴露公网。
2. 获取源码并复制 `.env.example` 为 `.env`，先填写所有必选配置和四个独立随机密钥。
3. 按部署方式启动 PostgreSQL、Redis、API 和 worker，并等待健康检查通过。
4. 使用 `/api/health`、管理员登录和会话探测接口验证服务，再通过 Nginx 对外提供 HTTPS。
5. 创建收款通道、上传二维码、创建商品并完成一笔测试订单，确认到账通知、金额匹配和回调链路。
6. 上线后定期备份 PostgreSQL 与 `data/`，升级前先停写、备份、迁移，再执行回归检查。

配置优先级：安全密钥、数据库、Redis、公开 HTTPS 地址和 CORS 是必选项；连接池、限流、WAF、指标和在线更新属于建议项；`FORPAY_API_PORT` 默认 7500，端口冲突时改为未占用端口；开发服务器和 API 文档仅限内网或本机使用。

### 上线前检查清单

- [ ] `FORPAY_ENVIRONMENT=production`，四个密钥均已替换且互不相同。
- [ ] `FORPAY_PUBLIC_BASE_URL` 使用最终 HTTPS 域名，`FORPAY_CORS_ORIGINS` 只填写明确来源。
- [ ] `.env` 权限为 `600`，运行用户不是 root；PostgreSQL、Redis 和 API 仅监听内网/回环地址。
- [ ] `docker compose ps` 或 systemd 状态显示 app、worker、PostgreSQL、Redis 均正常。
- [ ] 管理员登录、登出、会话过期、订单创建、二维码访问和到账通知均已实测。
- [ ] 已完成数据库和 `data/` 备份，并验证备份文件可读取。
- [ ] `FORPAY_API_PORT` 未被其他进程占用，Nginx upstream 与该端口一致。

## Docker Compose 部署（推荐）

### Docker Compose 配置示例

Compose 容器之间使用服务名通信，`FORPAY_DATABASE_URL` 中的主机必须是 `postgres`，`FORPAY_REDIS_URL` 中的主机必须是 `redis`。下面示例中的域名和所有密钥都必须替换：

```dotenv
FORPAY_APP_NAME=ForPay
POSTGRES_PASSWORD=替换为强随机数据库密码
FORPAY_ENVIRONMENT=production
FORPAY_PUBLIC_BASE_URL=https://pay.example.com
FORPAY_DATABASE_URL=postgresql+psycopg://forpay:${POSTGRES_PASSWORD}@postgres:5432/forpay
FORPAY_REDIS_URL=redis://redis:6379/0
FORPAY_CORS_ORIGINS=https://pay.example.com
FORPAY_SESSION_SECRET=替换为至少32位随机字符串
FORPAY_ADMIN_TOKEN=替换为至少24位管理员随机令牌
FORPAY_MONITOR_TOKEN=替换为至少24位监控随机令牌
FORPAY_ENCRYPTION_KEY=替换为独立加密随机密钥
FORPAY_ORDER_TTL_MINUTES=15
FORPAY_AMOUNT_SUFFIX_CENTS=1
FORPAY_MAX_BODY_MB=8
FORPAY_RATE_LIMIT_PER_MINUTE=60
FORPAY_DB_POOL_SIZE=10
FORPAY_DB_MAX_OVERFLOW=20
FORPAY_DB_POOL_TIMEOUT=30
FORPAY_METRICS_ENABLED=true
FORPAY_WAF_ENABLED=true
FORPAY_UPDATE_MANIFEST_URL=
FORPAY_UPDATE_PUBLIC_KEY=
```

`FORPAY_SESSION_SECRET`、`FORPAY_ADMIN_TOKEN`、`FORPAY_MONITOR_TOKEN` 和 `FORPAY_ENCRYPTION_KEY` 必须是四个不同的随机值。不要照抄示例中的占位文字；可以使用 `openssl rand -hex 32` 生成。

`POSTGRES_PASSWORD` 是 Compose PostgreSQL 的必选密码，必须替换为强随机值。Compose 会用它同时设置数据库容器密码和 API/worker 的连接串；不要在 `FORPAY_DATABASE_URL` 中写死默认密码。密码包含 `@`、`:`、`/` 等 URL 保留字符时，请先进行 URL 编码。

### 安装和启动

为降低首次部署门槛，项目提供三个 Linux 脚本。脚本只操作当前项目目录和 Docker Compose，不会自动推送 GitHub 或 Docker Hub。

首次安装（脚本会生成缺失的数据库密码和应用密钥，并自动启动服务）：

```bash
chmod +x scripts/install.sh scripts/update.sh scripts/uninstall.sh
./scripts/install.sh
```

在线更新（先备份 PostgreSQL 和二维码文件，再拉取 `latest` 镜像）：

```bash
./scripts/update.sh
```

普通卸载会保留数据卷；只有明确确认后才删除数据：

```bash
./scripts/uninstall.sh
./scripts/uninstall.sh --purge-data
```

`--purge-data` 会永久删除 PostgreSQL/Redis Docker 数据卷，执行前必须确认已有可用备份。

```bash
sudo apt update
sudo apt install -y git ca-certificates
sudo systemctl enable --now docker
git clone https://github.com/huizhang556/forpay.git
cd forpay
cp .env.example .env
nano .env
docker compose pull
docker compose config --images
docker compose up -d
docker compose ps
curl http://127.0.0.1:7500/api/health
```

如果启动时报 `Bind for 0.0.0.0:7500 failed: port is already allocated`，先执行 `docker ps --filter publish=7500` 和 `ss -ltnp | grep :7500` 定位占用者。确认是旧 ForPay 容器后再执行 `docker compose down`（不要加 `-v`）；如果是其他服务，在 `.env` 将 `FORPAY_API_PORT` 改为例如 `7501`，重新执行 `docker compose up -d`，并同步把 Nginx 的 upstream 改为 `127.0.0.1:7501`。

上面是 Docker Hub 远程镜像部署流程，不需要 `--build`。Compose 默认读取 `FORPAY_IMAGE=litehub/forpay:latest`，并从 Docker Hub 拉取远端最新版本。
执行 `docker compose config --images` 时，app 和 worker 应显示 `litehub/forpay:latest`；如果显示 `forpay:local` 或其他地址，请先修正 `.env` 中的 `FORPAY_IMAGE`。生产环境如需可复现部署，可将其改为具体版本或镜像 digest。

如果需要使用本地源码构建，先将 `.env` 中的 `FORPAY_IMAGE` 改为 `forpay:local`，不要执行 `docker compose pull`，再执行：

```bash
docker compose build
docker compose up -d
```

首次启动时 app 会先使用镜像内的 `/app/alembic.ini` 执行数据库迁移，再启动 API；如果 app 显示 unhealthy，先查看 `docker compose logs app` 中的迁移错误，不要直接删除数据库数据卷。

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

### Linux 源码部署配置示例

源码部署时 PostgreSQL 和 Redis 通常运行在本机，因此连接地址使用 `127.0.0.1`，不能继续使用 Compose 的 `postgres` 和 `redis` 服务名：

```dotenv
FORPAY_APP_NAME=ForPay
FORPAY_ENVIRONMENT=production
FORPAY_PUBLIC_BASE_URL=https://pay.example.com
FORPAY_DATABASE_URL=postgresql+psycopg://forpay:修改数据库密码@127.0.0.1:5432/forpay
FORPAY_REDIS_URL=redis://127.0.0.1:6379/0
FORPAY_CORS_ORIGINS=https://pay.example.com
FORPAY_SESSION_SECRET=替换为至少32位随机字符串
FORPAY_ADMIN_TOKEN=替换为至少24位管理员随机令牌
FORPAY_MONITOR_TOKEN=替换为至少24位监控随机令牌
FORPAY_ENCRYPTION_KEY=替换为独立加密随机密钥
FORPAY_ORDER_TTL_MINUTES=15
FORPAY_AMOUNT_SUFFIX_CENTS=1
FORPAY_MAX_BODY_MB=8
FORPAY_RATE_LIMIT_PER_MINUTE=60
FORPAY_DB_POOL_SIZE=10
FORPAY_DB_MAX_OVERFLOW=20
FORPAY_DB_POOL_TIMEOUT=30
FORPAY_METRICS_ENABLED=true
FORPAY_WAF_ENABLED=true
FORPAY_UPDATE_MANIFEST_URL=
FORPAY_UPDATE_PUBLIC_KEY=
```

源码部署必须先在 PostgreSQL 中创建 `forpay` 用户和数据库，再执行 Alembic 迁移。API 和 worker 使用同一个 `.env`，不要为 worker 创建另一套密钥。`.env` 文件应属于运行用户并设置为 `chmod 600`。

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
        proxy_pass http://127.0.0.1:7500;
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

## 文档索引

- [API 接口文档](docs/API.md)
- [系统设计文档](docs/ARCHITECTURE.md)
- [部署文档](docs/DEPLOYMENT.md)
- [安全模型](docs/SECURITY.md)
- [故障排查](docs/TROUBLESHOOTING.md)
- [开发指南](docs/DEVELOPMENT.md)

## 许可证

本项目处于开发和安全验证阶段。使用前请确认符合当地法律、支付平台规则和收款账户要求。软件按“原样”提供，不承诺规避平台风控或替代官方支付接口。
