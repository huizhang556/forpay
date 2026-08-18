# 故障排查

## API 无法启动

先查看 `docker compose logs app` 或 `journalctl -u forpay-api`。生产环境重点检查密钥长度、`FORPAY_ENCRYPTION_KEY`、数据库连接和 Alembic 迁移。

## worker 反复重启

查看 worker 日志，确认 `FORPAY_DATABASE_URL`、`FORPAY_REDIS_URL` 与 API 使用同一套配置，并检查 Redis 是否能执行 `redis-cli ping`。

## 支付页打不开或 Cookie 丢失

确认 `FORPAY_PUBLIC_BASE_URL` 与实际 HTTPS 域名完全一致，Nginx 传递 `Host`、`X-Forwarded-Proto` 和 `Set-Cookie`，浏览器没有阻止 SameSite Cookie。

## 二维码返回 403

必须先访问 `/api/public/orders/{token}` 获取 checkout Cookie，再访问二维码接口。订单过期、token 错误、Cookie 缺失或跨域 Cookie 被阻止都会返回失败。

## 到账通知未匹配

检查通道 ID、展示金额、订单有效期和 `external_id`。金额必须与页面展示金额完全一致；无法确认时不要强行补单，应保留手机账单截图并走人工复核。

## 回调失败

检查回调地址是否为 HTTPS、DNS 是否解析到公网地址、目标服务是否返回 2xx，以及回调签名和重试记录。系统会关闭自动重定向，回调地址改变后需要重新审核。

## Docker 镜像拉取失败

单独执行 `docker pull python:3.12-slim` 和 `docker pull node:24-alpine`，检查服务器 DNS、代理、Docker Hub 授权和网络出口。不要为了绕过失败而使用来源不明的镜像。
