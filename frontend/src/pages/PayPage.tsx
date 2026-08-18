import { useEffect, useState } from 'react'
import { Alert, Card, Spin, Typography } from 'antd'
import { getPublicOrder } from '../lib/api'
import type { Order } from '../types'

export function PayPage({ id }: { id: string }) {
  const [order, setOrder] = useState<Order>()
  useEffect(() => { getPublicOrder(id).then(setOrder).catch(() => undefined) }, [id])
  if (!order) return <div className="pay-shell"><Spin /></div>
  return <div className="pay-shell"><Card className="pay-card"><div className="pay-brand">FOR<span>PAY</span></div><Typography.Text type="secondary">{order.subject}</Typography.Text><div className="pay-price">¥ {order.display_amount}</div><div className="pay-tip">请按展示金额完成支付</div><img className="qr-image" src={'/api/public/orders/' + id + '/qr'} alt="收款二维码" /><Alert type="warning" showIcon message="二维码仅在订单有效期内可访问，请勿转发订单链接。" /></Card></div>
}
