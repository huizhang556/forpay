# ForPay 运维手册

## 启动

    Copy-Item .env.example .env
    docker compose up -d --build
    docker compose ps

应用容器会先执行 Alembic migration，再启动 API。worker 容器负责自动投递回调。

## 查看状态

    docker compose ps
    docker compose logs -f app
    docker compose logs -f worker
    docker compose exec postgres pg_isready -U forpay -d forpay
    docker compose exec redis redis-cli ping

## 升级

    docker compose pull
    docker compose up -d --build

升级前必须备份 PostgreSQL 和 data 目录。不要直接删除 PostgreSQL volume。

## 备份

    docker compose exec postgres pg_dump -U forpay -d forpay -Fc > forpay.dump
    docker run --rm -v forpay_forpay-postgres:/data -v /path/to/backup:/backup alpine tar czf /backup/forpay-data.tgz -C /data .

恢复前停止 app 和 worker，并先在临时数据库验证备份可用。

## 监控指标

至少监控：

- API health 状态
- PostgreSQL 连接和磁盘空间
- Redis 可用性和内存
- waiting_payment 数量
- unmatched 通知数量
- callback pending/failed 数量
- worker 重启次数
- 429、401、409 和 5xx 比例

## Prometheus 指标

`GET /metrics` 暴露请求计数和延迟直方图，必须通过 `X-ForPay-Admin-Token` 访问，并且只允许内网 Prometheus 抓取。不要把此路径发布到公网 Nginx。

应用使用有上限的 PostgreSQL 连接池（`FORPAY_DB_POOL_SIZE`、`FORPAY_DB_MAX_OVERFLOW`、`FORPAY_DB_POOL_TIMEOUT`）和 Redis 分布式限流。应监控连接池耗尽、Redis 异常、回调失败、未匹配通知、过期订单和 5xx 响应。

静态构建资源使用带哈希文件名和一年 immutable 缓存；API、订单数据、二维码、管理端和指标接口统一禁止缓存，避免支付状态或敏感数据被代理缓存。
