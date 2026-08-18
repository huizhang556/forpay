import { useEffect, useState } from 'react'
import { Button, Card, Empty, Table, Typography } from 'antd'
import { RefreshCw } from 'lucide-react'
import { getOrders } from '../lib/api'
import type { Order } from '../types'
import { StatusTag } from '../components/StatusTag'
export function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const load = () => getOrders().then(setOrders).catch(() => undefined)
  useEffect(() => { load() }, [])
  return <div><div className="page-heading compact"><div><Typography.Text className="eyebrow">ORDER LEDGER</Typography.Text><Typography.Title>订单流水</Typography.Title></div><Button icon={<RefreshCw size={16} />} onClick={load}>刷新</Button></div><Card className="table-card"><Table rowKey="id" dataSource={orders} locale={{ emptyText: <Empty description="还没有订单" /> }} columns={[{ title: '商户订单号', dataIndex: 'out_trade_no', render: (v: string) => <Typography.Text copyable>{v}</Typography.Text> }, { title: '订单内容', dataIndex: 'subject' }, { title: '应付金额', dataIndex: 'amount', render: (v: string) => '¥ ' + v }, { title: '实际展示金额', dataIndex: 'display_amount', render: (v: string) => <b className="amount">¥ {v}</b> }, { title: '状态', dataIndex: 'status', render: (v: string) => <StatusTag status={v} /> }, { title: '创建时间', dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleString() }]} /></Card></div>
}
