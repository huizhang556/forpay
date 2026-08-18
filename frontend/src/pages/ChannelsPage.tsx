import { useEffect, useState } from 'react'
import { Button, Card, Empty, Form, Input, Modal, Select, Space, Table, Typography, Upload, message } from 'antd'
import { Plus, QrCode } from 'lucide-react'
import { createChannel, getChannels, uploadChannelQr } from '../lib/api'
import type { Channel } from '../types'

export function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([])
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()
  const load = () => getChannels().then(setChannels).catch(() => undefined)
  useEffect(() => { load() }, [])
  const submit = async (values: Omit<Channel, 'id' | 'enabled'>) => { await createChannel(values); message.success('收款通道已添加'); setOpen(false); form.resetFields(); load() }
  return <div><div className="page-heading compact"><div><Typography.Text className="eyebrow">PAYMENT CHANNELS</Typography.Text><Typography.Title>收款通道</Typography.Title></div><Button type="primary" icon={<Plus size={16} />} onClick={() => setOpen(true)}>添加二维码</Button></div><Card className="table-card"><Table rowKey="id" dataSource={channels} locale={{ emptyText: <Empty description="先添加一个微信或支付宝二维码" /> }} columns={[{ title: '通道', dataIndex: 'name', render: (v: string) => <Space><QrCode size={18} />{v}</Space> }, { title: '平台', dataIndex: 'channel_type', render: (v: string) => v === 'wechat' ? '微信收款' : '支付宝收款' }, { title: '收款账号', dataIndex: 'account_label' }, { title: '状态', dataIndex: 'enabled', render: (v: boolean) => v ? <span className="online">● 运行中</span> : '已停用' }, { title: '二维码', render: (_: unknown, record: Channel) => <Upload showUploadList={false} beforeUpload={async (file) => { await uploadChannelQr(record.id, file); message.success('二维码已上传'); load(); return false }}><Button size="small">上传图片</Button></Upload> }]} /></Card><Modal title="添加收款二维码" open={open} onCancel={() => setOpen(false)} onOk={() => form.submit()} okText="保存"><Form form={form} layout="vertical" onFinish={submit}><Form.Item name="name" label="通道名称" rules={[{ required: true }]}><Input placeholder="例如：我的微信收款码" /></Form.Item><Form.Item name="channel_type" label="平台" rules={[{ required: true }]}><Select options={[{ value: 'wechat', label: '微信' }, { value: 'alipay', label: '支付宝' }]} /></Form.Item><Form.Item name="account_label" label="收款账号备注" rules={[{ required: true }]}><Input placeholder="例如：个人微信主号" /></Form.Item></Form></Modal></div>
}
