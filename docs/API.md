# API 文档

ForPay API 默认前缀为 `/api`。生产环境必须通过 HTTPS 和 Nginx 访问。

## 管理端

- `POST /api/admin/login`：使用 `FORPAY_ADMIN_TOKEN` 创建 HttpOnly 管理会话。
- `GET /api/dashboard`：查看订单和收款汇总，需要管理员认证。
- `POST /api/channels`、`GET /api/channels`：管理收款通道。
- `POST /api/channels/{channel_id}/qr-upload`：上传收款二维码，服务端校验 MIME、文件头和大小。
- `POST /api/products`、`GET /api/products`：管理商品。

管理接口可使用 `X-ForPay-Admin-Token`，浏览器管理端也可使用登录 Cookie。令牌不能写入前端代码、日志或二维码。

## 下单

`POST /api/orders` 需要管理员认证；商户系统应优先使用 `POST /api/merchant/orders`，并携带：

```text
X-ForPay-Key
X-ForPay-Timestamp
X-ForPay-Signature
X-Idempotency-Key
```

签名原文为 `timestamp + "." + 原始请求体`，算法为 HMAC-SHA256。`X-Idempotency-Key` 应在同一业务订单中保持唯一。

## 支付页和二维码

- `GET /api/public/orders/{public_token}`：返回有效订单并签发短期 checkout Cookie。
- `GET /api/public/orders/{public_token}/qr`：需要 checkout Cookie，只在订单有效期内返回二维码。
- `GET /api/public/orders/{public_token}/checkout-qr`：需要 checkout Cookie，返回支付页二维码。

二维码接口禁止缓存和直接分享。Cookie 只能降低接口盗取，不能阻止用户拍照转发已经显示的二维码。

## 到账通知和回调

- `POST /api/monitor/notifications`：需要 `X-ForPay-Monitor-Token`，通知必须带唯一 `external_id`。
- `GET /api/notifications/unmatched`：管理员查看未匹配通知。
- `POST /api/notifications/{notification_id}/match`：管理员人工补单，必须匹配通道、展示金额和订单状态。
- `POST /api/callbacks/{attempt_id}/retry`：管理员重试失败回调。

## 运维接口

- `GET /api/health`：健康检查。
- `GET /metrics`：Prometheus 指标，需要 `X-ForPay-Admin-Token`，不能暴露到公网。
- `GET /api/admin/update/check`：检查 Ed25519 签名更新清单，不会自动执行远程代码。
