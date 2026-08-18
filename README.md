# ForPay

ForPay 是一个面向个人和小团队的现代化二维码支付网关原型。它不调用微信或支付宝官方开放 API，而是通过收款二维码、唯一展示金额和到账通知匹配完成过渡性收款流程。

当前版本已经包含：

- React + TypeScript 管理工作台
- FastAPI 支付 API
- PostgreSQL 数据模型
- 静态微信 / 支付宝收款通道
- 并发订单金额尾数预占
- 模拟监控到账通知
- 易支付兼容提交入口
- 二维码图片上传与本地静态托管
- 商户 API Key 鉴权下单
- 回调任务排队、重试和状态记录
- 未匹配到账通知人工补单
- HMAC 时间戳商户签名、订单幂等键和请求频率限制
- 管理端令牌、监控端令牌和基础安全响应头
- Redis 分布式限流和独立回调 worker
- Docker Compose 开发环境

本项目仍处于开发阶段，个人收款码自动化处理可能受平台规则、通知延迟和账号风控影响，不应视为官方支付接口的替代品。

## 本地启动

复制 .env.example 为 .env，然后启动 PostgreSQL、Redis 和 API：

    docker compose up -d postgres redis
    uv sync --extra dev
    uv run uvicorn app.main:app --app-dir backend --reload

另开终端启动前端：

    cd frontend
    npm install
    npm run dev

访问 http://localhost:5173，API 文档位于 http://localhost:8000/docs。

也可以直接构建完整容器：

    docker compose up -d --build

## 当前测试流程

1. 在“收款通道”添加微信或支付宝通道。
2. 调用 POST /api/orders 创建订单。
3. 读取订单的 display_amount，它是用户实际需要支付的金额。
4. 调用 POST /api/monitor/notifications 模拟到账。
5. 在“订单流水”查看订单变成“已到账”。

后续版本将加入通知审计界面、自动回调 worker、完整商户控制台和 Android 监控端协议。

## 安全要求

生产环境必须修改 FORPAY_SESSION_SECRET、FORPAY_ADMIN_TOKEN 和 FORPAY_MONITOR_TOKEN。商户下单使用 X-ForPay-Key、X-ForPay-Timestamp、X-ForPay-Signature，并建议每个请求携带唯一的 X-Idempotency-Key。到账通知接口不接受匿名请求，未来 Android 监控端必须安全保存监控令牌。

Docker Compose 会单独启动 worker 处理待发送回调；API 可以横向扩展，限流计数存储在 Redis 中。
