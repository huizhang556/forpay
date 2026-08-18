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

## 部署与文档索引

- [Linux 部署、源码部署和 Nginx 配置](docs/deployment-linux.md)
- [API 集成说明](docs/api.md)
- [安全模型与二维码防泄露措施](docs/security.md)
- [系统架构](docs/architecture.md)
- [运维、备份和监控](docs/operations.md)
- [路线图、上线前检查和已知短板](docs/roadmap.md)

## 本次版本包含的完整功能

本版本不是官方支付 API 的替代品，而是“收款二维码 + 唯一展示金额 + 到账通知确认”的过渡网关，具体包含：

1. 微信和支付宝收款二维码通道管理及上传校验，二维码文件不通过公开静态目录暴露。
2. 订单专属高熵 token、短期 checkout 会话 Cookie、二维码接口限流和禁止缓存，降低订单链接及二维码地址被盗用的风险。
3. PostgreSQL 金额精度、并发金额尾数分配、订单过期、通知去重、通道和金额精确匹配。
4. 管理员人工补单保护：通知状态、通道、展示金额和订单状态必须全部满足，补单写入审计事件并进入回调队列。
5. 商户 API Key、HMAC 时间戳签名、幂等键、回调签名、回调重试、SSRF 基础防护和 Redis 分布式限流。
6. 产品下单、公开支付页面、易支付兼容入口，以及为后续 Android 通知监控预留的独立令牌边界。
7. Docker Compose 的 API、worker、PostgreSQL、Redis 服务编排，Linux 源码部署方式和 Nginx 反向代理配置。
8. Ed25519 签名更新清单检查。在线更新只检查版本和摘要，不会在 API 进程中自动执行远程代码。

正式承载资金前，必须完成 `docs/roadmap.md` 中列出的 DNS 级 SSRF 防护、管理员 RBAC、Android 设备凭据、故障演练、备份恢复演练和人工补单双人审批。
