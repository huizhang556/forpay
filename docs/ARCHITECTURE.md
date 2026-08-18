# 系统设计与数据流

## 分层结构

```text
浏览器 / 商户系统 / 监控端
          |
        Nginx
          |
 FastAPI API 实例 -- Redis（限流、共享状态）
          |
 PostgreSQL（订单、通知、事件、回调）
          |
 worker（过期订单、回调重试）
```

前端使用 React、TypeScript、Vite 和 Ant Design；后端使用 FastAPI、SQLAlchemy、Alembic 和 Pydantic；数据库使用 PostgreSQL NUMERIC 保存金额。

## 订单流程

1. 商户提交金额、通道、商品和幂等键。
2. API 锁定收款通道，分配未占用的展示金额尾数。
3. 订单生成高熵 `public_token` 和有效期。
4. 用户打开支付页，获得短期 checkout Cookie 后读取二维码。
5. 监控端提交手机到账通知。
6. 服务端以通道、展示金额、有效期和通知唯一编号匹配订单。
7. 匹配成功后记录支付事件并加入回调队列；无法匹配的通知进入人工复核。

## 一致性原则

- 金额使用 Decimal 和 PostgreSQL NUMERIC，禁止浮点金额比较。
- 订单创建和展示金额分配使用数据库锁。
- 到账通知以 `external_id` 幂等，重复通知不能重复入账。
- 人工补单不能绕过通道、金额和订单状态检查。
- 回调任务可重试，支付状态和回调状态分别记录。
