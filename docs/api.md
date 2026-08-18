# ForPay API 集成

## 创建商户密钥

管理员登录后调用 POST /api/api-keys，secret 只返回一次。

## 创建订单

商户调用 POST /api/merchant/orders，并携带商户签名。建议每个业务订单使用稳定且唯一的 X-Idempotency-Key。

响应中的 display_amount 是用户实际支付金额，amount 是业务原始金额。

## 商品结账

管理员可以创建商品，用户通过 POST /api/checkout 根据 product_id 和 channel_id 创建订单。返回的 public_token 是高熵、短期订单令牌，支付页地址为 /pay/{public_token}。

ForPay 只在订单有效期内通过 /api/public/orders/{public_token}/qr 返回收款二维码，不再把二维码目录作为公开静态目录。订单链接和二维码不能发布到公开页面或日志。

## 到账通知

监控端调用 POST /api/monitor/notifications，并携带 X-ForPay-Monitor-Token。通知必须包含稳定且唯一的 external_id。

监控端不要直接提交已支付状态；服务端只根据通知、通道、金额和有效期匹配订单。

## 回调

回调发送 POST 表单，并带有 X-ForPay-Timestamp 和 X-ForPay-Signature。商户接收方应验证时间窗口、签名和 out_trade_no，并以幂等方式处理回调。

# Public checkout asset protection

`GET /api/public/orders/{public_token}` sets a short-lived `forpay_checkout` HttpOnly cookie. The browser must retain that cookie to read `/qr` or `/checkout-qr`; direct requests without the checkout session receive `403`. Clients embedding the checkout page must allow first-party cookies and must not cache these responses.
