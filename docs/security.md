# ForPay 安全模型

## 密钥分层

- FORPAY_SESSION_SECRET：加密商户 API secret，必须长期固定并妥善备份。
- FORPAY_ADMIN_TOKEN：只用于管理员登录，不得写入前端代码、二维码或日志。
- FORPAY_MONITOR_TOKEN：只用于 Android/监控端发送到账通知，不得暴露给普通浏览器。
- 商户 API secret：创建后只返回一次，数据库保存加密值和哈希值。

生产环境启动时会拒绝默认密钥。修改 session secret 会导致已保存的商户 secret 无法解密。

## 商户签名

签名原文：

    timestamp + "." + raw_request_body

签名算法：

    HMAC-SHA256(secret, signing_text).hexdigest()

请求头：

    X-ForPay-Key
    X-ForPay-Timestamp
    X-ForPay-Signature
    X-Idempotency-Key

时间戳允许偏差五分钟。生产客户端必须使用原始请求体计算签名，不能对 JSON 重新排序后再签名。

## 订单安全

- 金额使用 Decimal 和 PostgreSQL NUMERIC。
- 活跃订单按收款通道锁定唯一展示金额。
- 幂等键按 merchant_id + idempotency_key 唯一。
- 支付通知按 external_id 幂等。
- 只有匹配通道、金额和有效期的通知才会自动入账。
- 无法匹配的通知只能进入人工处理，不能自动猜测。
- 收款二维码文件不通过公开静态目录暴露，只能通过有效订单令牌临时读取。
- 订单令牌使用高熵随机值并设置有效期，不能使用自增订单 ID 作为公开支付地址。

## 部署检查

1. 使用 HTTPS。
2. PostgreSQL、Redis 不开放公网。
3. 反向代理只转发必要 API 路径。
4. 不信任用户提交的 X-Forwarded-For，需在受信代理层正确配置。
5. 定期备份数据库、data 目录和所有密钥。
6. 日志中禁止打印 API secret、管理令牌、监控令牌和完整通知原文。

## QR leakage controls

- The uploaded payment QR files live outside the public static directory and are served only by the order QR endpoint.
- Opening the public order endpoint issues a short-lived `forpay_checkout` HttpOnly, SameSite cookie bound to that order's high-entropy `public_token`.
- Both payment QR endpoints require this cookie, return `403` without it, send `Cache-Control: no-store`, and are covered by the Redis distributed request limiter.
- The cookie reduces direct URL scraping and replay after a URL leak. It cannot prevent a person from photographing or forwarding a QR image that is already visible on a trusted checkout screen; use short order TTLs, exact display-amount matching, and notification deduplication as the financial controls.
- Do not put QR images in logs, analytics, screenshots, public documentation, or CDN caches. Configure the reverse proxy to preserve `Set-Cookie` and avoid caching `/api/public/orders/*`.
- Production encryption uses a dedicated `FORPAY_ENCRYPTION_KEY`; changing it requires a planned key migration. Default or short secrets are rejected outside development.
- Callback hosts are resolved before use, private/reserved results are rejected, and callback redirects are disabled. DNS-level egress policy is still recommended at the host or network layer.
- The built-in WAF middleware is a low-cost request filter, not a replacement for a managed WAF. Put Nginx, a cloud WAF, or equivalent rules in front of the service.
