# ForPay 本地开发指南

本文档仅供项目维护者和二次开发者使用，不是面向最终用户的部署教程。生产环境请按照 [README.md](README.md) 选择三种 Linux 部署方式。

## 环境要求

- Python 3.12
- `uv`
- Node.js 20 或更高版本
- Docker Engine 和 Docker Compose 插件
- Git

## 获取源码

```bash
git clone https://github.com/huizhang556/forpay.git
cd forpay
```

## 初始化依赖

```bash
uv sync --extra dev
cd frontend
npm ci
cd ..
```

开发依赖只用于本地检查，不应安装到生产镜像。不要提交 `.env`、`data/`、二维码、数据库备份或真实到账通知。

## 配置开发环境

```bash
cp .env.example .env
```

开发环境至少确认以下配置：

```dotenv
FORPAY_ENVIRONMENT=development
FORPAY_API_PORT=7500
FORPAY_DATABASE_URL=postgresql+psycopg://forpay:forpay@localhost:5432/forpay
FORPAY_REDIS_URL=redis://localhost:6379/0
FORPAY_PUBLIC_BASE_URL=http://localhost:7500
FORPAY_CORS_ORIGINS=http://localhost:5173
```

开发环境可以使用示例密钥，生产环境必须全部替换为独立随机值。

## 启动基础服务

```bash
docker compose up -d postgres redis
uv run alembic -c alembic.ini upgrade head
```

## 启动后端和前端

后端终端：

```bash
uv run uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 7500
```

前端终端：

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

访问 `http://localhost:5173`，API 文档访问 `http://127.0.0.1:7500/docs`。

也可以使用仓库内的 `scripts/dev.sh` 同时启动基础服务、后端和前端；该脚本仅供维护者使用，不属于用户部署流程。

## 测试与质量检查

```bash
uv run pytest
uv run pytest --cov=backend/app --cov-report=term-missing
uv run ruff check backend
cd frontend && npm run build && cd ..
docker compose config --quiet
bash -n scripts/install.sh scripts/update.sh scripts/uninstall.sh
```

涉及支付通知、订单状态、金额分配、回调和鉴权的修改，必须增加回归测试。覆盖率数字不能替代 PostgreSQL、Redis 和并发场景测试。

## 数据库迁移

修改模型后创建迁移：

```bash
uv run alembic -c alembic.ini revision --autogenerate -m "说明迁移内容"
uv run alembic -c alembic.ini upgrade head
```

提交迁移文件前检查 `upgrade` 和 `downgrade`，不要在开发环境使用 `stamp head` 绕过未知结构。

## 开发约定

- 金额统一使用 `Decimal` 和 PostgreSQL `NUMERIC`，禁止浮点金额。
- 所有支付状态变化必须写入 `PaymentEvent`。
- 通知、订单和回调必须设计幂等键及并发测试。
- 外部 URL 必须经过 SSRF 校验，日志不得记录密钥、Cookie、订单 token 或完整通知原文。
- 新接口必须明确认证、限流、幂等、错误响应和审计字段。
- 提交信息使用中文；版本发布前同步更新 `VERSIONS.md`，并逐项核对同名 tag 内容。

## 停止与清理

停止本地进程后可执行：

```bash
docker compose stop
```

不要在日常开发中执行 `docker compose down -v`，否则会删除数据库和 Redis 数据卷。需要彻底清理时，先确认已有备份，再使用用户可见的卸载脚本并按提示选择数据处理方式。
