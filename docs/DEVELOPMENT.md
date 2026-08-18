# 开发指南

## 初始化

后端执行 `uv sync --extra dev`，前端执行 `cd frontend && npm ci`。本地数据库和 Redis 可以使用 Docker Compose 启动：`docker compose up -d postgres redis`。

## 常用命令

```bash
uv run ruff check backend
uv run pytest --cov=app --cov-report=term
cd frontend && npm run build
docker compose config --quiet
```

API 本地启动：`uv run uvicorn app.main:app --app-dir backend --reload`。前端开发服务器：`cd frontend && npm run dev`。

## 修改原则

- 金额使用 Decimal，不使用浮点数。
- 新的支付状态必须增加事件记录和回归测试。
- 任何外部 URL 都必须经过 SSRF 校验。
- 新增接口要明确认证方式、幂等策略、限流范围和日志字段。
- 测试不得提交真实二维码、密钥、数据库和到账通知。
- 每次版本修改都要在根目录 `VERSIONS.md` 追加具体功能、修复和验证结果。

## 提交流程

提交前运行 Ruff、Pytest、前端构建和 Compose 配置检查。提交信息使用中文，版本 tag 的主要更新内容必须与 `VERSIONS.md` 同步。
