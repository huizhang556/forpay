# ForPay Roadmap

## 必须完成

- Android 通知监听端及安全设备注册
- 真实二维码上传、删除和历史版本清理
- 商品、固定价格二维码和订单专属 checkout 页面
- 商户管理、角色权限和审计日志页面
- 自动过期订单任务
- 自动回调 worker 的管理和失败告警
- 对账页面：通知、订单、回调三方状态对比
- API 访问日志和敏感字段脱敏
- PostgreSQL 备份恢复演练
- 多实例压测和 Redis 故障演练

## 实用增强

- 多二维码轮询和通道健康评分
- 监控端在线状态和最后心跳
- 商户回调 URL 白名单
- 每个商户独立限流额度
- 订单导出和人工补单审批
- Telegram/邮件告警
- OpenTelemetry、Prometheus 指标
- 官方微信/支付宝通道适配器
# Project review and release gates

Before handling production funds, complete DNS-aware SSRF egress controls, admin RBAC with audit logs, Android per-device credentials and heartbeat, Redis/PostgreSQL failure drills, backup restore verification, and multi-instance load tests. Add a second-person approval for manual matching and monitor unmatched notifications.

The online update checker is intentionally read-only: it verifies an Ed25519-signed manifest and SHA-256 metadata but never executes downloaded code. Production releases must use an immutable image or reviewed source artifact, a database backup, a health check, and a documented rollback.
